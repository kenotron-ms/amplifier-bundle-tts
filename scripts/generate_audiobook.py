#!/usr/bin/env python3
"""
Audiobook Generator — reads audiobook_script.md, voices exact original text.

Usage:
  .venv/bin/python generate_audiobook.py           # full run: all 8 scenes + stitch
  .venv/bin/python generate_audiobook.py 1          # generate only scene 1
  .venv/bin/python generate_audiobook.py 1 2 3      # generate scenes 1, 2, 3
  .venv/bin/python generate_audiobook.py stitch     # stitch all existing segments
"""

import sys
import re
import numpy as np
import soundfile as sf
from pathlib import Path
import torch

# ─── Directories ──────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
SCRIPT = BASE / "audiobook_script.md"
SEGS   = BASE / "audio" / "segments"
OUT    = BASE / "audio"
SEGS.mkdir(parents=True, exist_ok=True)

# ─── Model singleton ──────────────────────────────────────────────────────────
MODEL = None


def load_model():
    global MODEL
    if MODEL is not None:
        return
    from omnivoice import OmniVoice  # type: ignore
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype  = torch.float32 if device == "cpu" else torch.float16
    print(f"\n{'='*60}")
    print(f"  Loading OmniVoice on {device}...")
    print(f"{'='*60}\n", flush=True)
    MODEL = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device, dtype=dtype)
    if device == "mps":
        print("  Warming up MPS Metal shaders (~3 min first run)...", flush=True)
        MODEL.generate(text="warming up the voice model.", num_step=32)
        torch.mps.synchronize()
        print("  Warmup done ✓\n", flush=True)


def for_tts(text: str) -> str:
    """Normalise smart/curly quotes → ASCII before passing to the TTS model.
    The OmniVoice tokenizer mishandles Unicode quote chars and produces clicks."""
    return (
        text
        .replace("\u201c", '"').replace("\u201d", '"')   # curly double → "
        .replace("\u2018", "'").replace("\u2019", "'")   # curly single → '
        .replace("\u2026", "...").replace("\u2014", "--").replace("\u2013", "-")
    )


def gen(filename: str, text: str, instruct: str, speed: float = 1.0) -> Path:
    """Generate one WAV segment. Skips if the file already exists."""
    out = SEGS / filename
    if out.exists():
        kb = out.stat().st_size / 1024
        print(f"  [skip] {filename}  ({kb:.0f} KB)", flush=True)
        return out
    load_model()
    print(f"  [gen]  {filename}", flush=True)
    tensors = MODEL.generate(text=for_tts(text), instruct=instruct, num_step=32, speed=speed)
    if torch.backends.mps.is_available():
        torch.mps.synchronize()
    audio = tensors[0].squeeze(0).cpu().float().numpy()
    sf.write(str(out), audio, 24000)
    kb = out.stat().st_size / 1024
    print(f"  [ok]   {filename}  ({kb:.0f} KB)", flush=True)
    return out


# ─── Voice profiles ───────────────────────────────────────────────────────────
# (instruct_string, speed)
# Adopted from chase_audiobook.py — already tested and produced working audio.
#
#  Speed guide:  0.82 = deliberate/menacing   0.88 = measured/noir
#                0.94 = world-weary           1.00 = natural
#                1.06 = eager/child           1.10 = nervous/fearful
#
VOICES = {
    "NARRATOR":            ("male, middle-aged, low pitch, american accent",        0.88),
    "CHASE":               ("male, middle-aged, moderate pitch, american accent",   0.94),
    "LIA":                 ("female, young adult, moderate pitch, american accent", 1.00),
    "JACK":                ("male, child, high pitch, american accent",             1.06),
    "BLAZE":               ("male, middle-aged, very low pitch, american accent",   0.82),
    "CRUM":                ("male, young adult, high pitch, american accent",       1.10),
    "GANG_MEMBER":         ("male, young adult, low pitch, american accent",        0.95),
    # Whisper variant for S05-025 ("How old was she?")
    "GANG_MEMBER_WHISPER": ("male, middle-aged, low pitch, american accent",        0.90),
}

# Segment IDs that use the whisper voice variant
WHISPER_SEGS = {"S05-025"}

# ─── Silence ──────────────────────────────────────────────────────────────────
SR = 24_000


def silence(sec: float) -> "np.ndarray":
    return np.zeros(int(SR * sec), dtype=np.float32)


# ─── Parse audiobook_script.md ────────────────────────────────────────────────
SEGMENT_RE   = re.compile(r"^(S(\d{2})-(\d{3})) \[(\w+)\] (.+)$")
EXPRESSIVE_RE = re.compile(r"\[[\w][\w-]*\]")   # strips [laughter], [sigh], etc.


def parse_script(path: Path) -> list:
    """Return list of dicts: {id, scene, speaker, text, pause_before}."""
    segments    = []
    pending_pause = 0.15   # minimum breath between any two clips

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()

            if line == "[SCENE-BREAK]":
                pending_pause = max(pending_pause, 2.0)
            elif line == "[SECTION-BREAK]":
                pending_pause = max(pending_pause, 1.5)
            elif line == "[SHORT-PAUSE]":
                pending_pause = max(pending_pause, 0.4)
            elif line.startswith("S"):
                m = SEGMENT_RE.match(line)
                if m:
                    seg_id, scene_num, seq, speaker, text = (
                        m.group(1), int(m.group(2)), int(m.group(3)),
                        m.group(4), m.group(5),
                    )
                    # Remove inline expressive tags before sending to TTS
                    text = EXPRESSIVE_RE.sub("", text).strip()
                    segments.append({
                        "id":           seg_id,
                        "scene":        scene_num,
                        "seq":          seq,
                        "speaker":      speaker,
                        "text":         text,
                        "pause_before": pending_pause,
                    })
                    pending_pause = 0.15   # reset to minimum

    return segments


# ─── Generate one scene ───────────────────────────────────────────────────────
def generate_scene(scene: int, segments: list) -> list:
    """
    Generate all WAV files for `scene`. Returns [(Path, pause_before), ...].
    """
    scene_segs = [s for s in segments if s["scene"] == scene]
    if not scene_segs:
        print(f"  ⚠  No segments found for scene {scene}", flush=True)
        return []

    print(f"\n── Scene {scene}  ({len(scene_segs)} segments) "
          + "─" * max(0, 50 - len(str(scene))), flush=True)

    files = []
    for seg in scene_segs:
        speaker   = "GANG_MEMBER_WHISPER" if seg["id"] in WHISPER_SEGS else seg["speaker"]
        voice_key = speaker if speaker in VOICES else "NARRATOR"
        instruct, speed = VOICES[voice_key]

        filename = f"{seg['id'].replace('-', '_')}_{seg['speaker']}.wav"
        path     = gen(filename, seg["text"], instruct, speed)
        files.append((path, seg["pause_before"]))

    return files


# ─── Stitch ───────────────────────────────────────────────────────────────────
def stitch(files: list, out_path: Path) -> None:
    print(f"\n{'='*60}", flush=True)
    print(f"  Stitching {len(files)} segments → {out_path.name}", flush=True)
    print(f"{'='*60}", flush=True)

    chunks = [silence(1.0)]   # 1 s opening silence

    for path, pause_before in files:
        chunks.append(silence(pause_before))
        audio, _ = sf.read(str(path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        chunks.append(audio)

    chunks.append(silence(2.0))   # 2 s closing silence

    full = np.concatenate(chunks)
    sf.write(str(out_path), full, SR)

    dur = len(full) / SR
    mb  = out_path.stat().st_size / 1_048_576
    print(f"\n  ✓ {out_path}", flush=True)
    print(f"    Duration : {int(dur // 60)}m {int(dur % 60)}s", flush=True)
    print(f"    Size     : {mb:.1f} MB\n", flush=True)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    args = sys.argv[1:]

    segments = parse_script(SCRIPT)
    print(f"Parsed {len(segments)} segments from {SCRIPT.name}")

    # ── stitch-only mode ──────────────────────────────────────────────────────
    if args == ["stitch"]:
        wav_files = sorted(SEGS.glob("S*.wav"))
        if not wav_files:
            print("No segment files found. Generate scenes first.")
            sys.exit(1)
        seg_map = {
            f"{s['id'].replace('-', '_')}_{s['speaker']}.wav": s["pause_before"]
            for s in segments
        }
        files = [(f, seg_map.get(f.name, 0.4)) for f in wav_files]
        stitch(files, OUT / "audiobook_FINAL.wav")
        return

    # ── per-scene mode ────────────────────────────────────────────────────────
    if args and all(a.isdigit() for a in args):
        scenes    = [int(a) for a in args]
        all_files = []
        for scene in scenes:
            all_files.extend(generate_scene(scene, segments))
        print(f"\n  Scene(s) {scenes} complete — {len(all_files)} clips in {SEGS}")
        print(f"  Run with 'stitch' to merge into final audiobook.")
        return

    # ── full run ──────────────────────────────────────────────────────────────
    print("\n>>> Full audiobook — scenes 1–8\n", flush=True)
    all_files = []
    for scene in range(1, 9):
        all_files.extend(generate_scene(scene, segments))
    stitch(all_files, OUT / "audiobook_FINAL.wav")


if __name__ == "__main__":
    main()
