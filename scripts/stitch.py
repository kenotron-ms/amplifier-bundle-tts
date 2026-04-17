#!/usr/bin/env python3
"""
Stitch audio segments into scene files, then scene files into a full audiobook.

Usage:
  # Stitch one scene
  python scripts/stitch.py --scene 01-kitchen

  # Stitch all scenes into full audiobook
  python scripts/stitch.py --all

  # List what would be stitched (dry run)
  python scripts/stitch.py --all --dry-run
"""

import argparse
import glob
import os
import wave
from pathlib import Path

AUDIO_DIR = Path("audio_output")
SCENES_ORDER = [
    "01-kitchen",
    "02-bear",
    "03-blaze",
    "04-search",
    "05-bedtime",
    "06-discovery",
    "07-midnight",
    "08-reckoning",
]


def stitch_wavs(input_paths: list[Path], output_path: Path, dry_run=False) -> int:
    """Concatenate WAV files. Returns total frame count."""
    if not input_paths:
        print(f"  [skip] no segments found for {output_path.name}")
        return 0

    print(f"  → {output_path.name}  ({len(input_paths)} segments)")
    for p in input_paths:
        print(f"       {p.name}")

    if dry_run:
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    params = None
    chunks = []

    for path in input_paths:
        with wave.open(str(path), "rb") as wf:
            if params is None:
                params = wf.getparams()
            chunks.append(wf.readframes(wf.getnframes()))

    with wave.open(str(output_path), "wb") as out:
        out.setparams(params)
        for chunk in chunks:
            out.writeframes(chunk)

    size_kb = output_path.stat().st_size // 1024
    total_frames = sum(len(c) // (params.sampwidth * params.nchannels) for c in chunks)
    duration_s = total_frames / params.framerate
    print(f"       ✅ {size_kb} KB — {duration_s:.1f}s")
    return total_frames


def stitch_scene(scene_slug: str, dry_run=False):
    """Stitch all segments for a single scene."""
    pattern = str(AUDIO_DIR / f"{scene_slug}-*.wav")
    segments = sorted(Path(p) for p in glob.glob(pattern))
    output = AUDIO_DIR / f"{scene_slug}-FULL.wav"
    stitch_wavs(segments, output, dry_run=dry_run)


def stitch_all(dry_run=False):
    """Stitch all scenes, then stitch scenes into full audiobook."""
    print("\n── Stitching scenes ──")
    scene_fulls = []
    for slug in SCENES_ORDER:
        stitch_scene(slug, dry_run=dry_run)
        full = AUDIO_DIR / f"{slug}-FULL.wav"
        if full.exists() or dry_run:
            scene_fulls.append(full)

    print("\n── Stitching full audiobook ──")
    stitch_wavs(scene_fulls, AUDIO_DIR / "AUDIOBOOK-FULL.wav", dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description="Stitch TTS audio segments")
    parser.add_argument("--scene", help="Stitch one scene (e.g. 01-kitchen)")
    parser.add_argument("--all", action="store_true", help="Stitch all scenes + full audiobook")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be stitched")
    args = parser.parse_args()

    if args.dry_run:
        print("[dry-run mode — no files written]")

    if args.scene:
        print(f"\n── Stitching scene: {args.scene} ──")
        stitch_scene(args.scene, dry_run=args.dry_run)
    elif args.all:
        stitch_all(dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
