#!/usr/bin/env python3
"""
Full Qwen3-TTS Audiobook Generator — Voice Cloning Edition
Narrator : narrator_D_low-knowing-leaning-in.wav  (the chosen voice)
Others   : voices/seeds/{CHARACTER}.wav

Usage:
  .venv/bin/python generate_audiobook_qwen.py          # all 8 scenes + stitch
  .venv/bin/python generate_audiobook_qwen.py 1         # scene 1 only
  .venv/bin/python generate_audiobook_qwen.py 1 2 3     # scenes 1-3
  .venv/bin/python generate_audiobook_qwen.py stitch    # stitch existing clips only
"""
import re
import sys
import signal
import numpy as np
import soundfile as sf
import torch
from pathlib import Path

# ── Per-clip generation timeout ────────────────────────────────────────────────
# Normal clips: 60-90s.  Long narrator passages: up to 2min.
# Anything past TIMEOUT_SEC is stuck — kill and retry.
TIMEOUT_SEC = 240   # 4 minutes

def _alarm_handler(signum, frame):
    raise TimeoutError(f"Generation timed out after {TIMEOUT_SEC}s")

def generate_with_timeout(model, text, language, prompt, **kwargs):
    """Call generate_voice_clone with a hard timeout via SIGALRM."""
    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(TIMEOUT_SEC)
    try:
        result = model.generate_voice_clone(
            text=text, language=language, voice_clone_prompt=prompt, **kwargs
        )
        signal.alarm(0)   # cancel alarm
        return result
    except TimeoutError:
        signal.alarm(0)
        raise
    except Exception:
        signal.alarm(0)
        raise

BASE   = Path(__file__).parent
SCRIPT = BASE / "audiobook_script.md"
SEGS   = BASE / "audio" / "segments_qwen"
OUT    = BASE / "audio"
SEGS.mkdir(parents=True, exist_ok=True)

SR = 24_000

# ── Reference audio files for voice cloning ─────────────────────────────────
# NARRATOR uses the auditioned Variant D — all others use the character seeds.
CHAR_REFS = {
    "NARRATOR":    BASE / "audio"  / "narrator_variants" / "narrator_D_low-knowing-leaning-in.wav",
    "CHASE":       BASE / "voices" / "seeds" / "CHASE.wav",
    "LIA":         BASE / "voices" / "seeds" / "LIA.wav",
    "JACK":        BASE / "voices" / "seeds" / "JACK.wav",
    "BLAZE":       BASE / "voices" / "seeds" / "BLAZE.wav",
    "CRUM":        BASE / "voices" / "seeds" / "CRUM.wav",
    "GANG_MEMBER": BASE / "voices" / "seeds" / "GANG_MEMBER.wav",
}

# ── Transcripts of each reference clip (must match exactly) ─────────────────
# These are the texts spoken in the reference audio files used for cloning.
CHAR_TEXTS = {
    # Variant D was generated with the narrator_variants.py TEXT:
    "NARRATOR": (
        "The city was quiet at night, or it should be at least. "
        "Occasional gunshots pierced the silence. "
        "Chase ignored them -- they were par for the course anyway. "
        "He opened the fridge and rummaged around for some food, "
        "finally deciding on some ready-to-eat noodles."
    ),
    "CHASE": (
        "I know what I am. I know what I've done to keep this family going. "
        "You think I don't see what it costs? I see it every day. "
        "But a man does what he has to, and I'd do it all again "
        "if it meant keeping them safe."
    ),
    "LIA": (
        "I'm not asking you to be someone you're not. I just need you to "
        "come home. That's all. Just come home to us at the end of the day."
    ),
    "JACK": (
        "Can you tell me another story, dad? I like the one about the hero. "
        "He's my favorite. Does he ever get scared? I think I would get scared."
    ),
    "BLAZE": (
        "Let me be very clear about something. When I give an instruction, "
        "I expect it followed. Not almost. Not with excuses or caveats. "
        "Followed. Completely."
    ),
    "CRUM": (
        "I swear it wasn't my fault. I did everything right, every single step. "
        "Please, just give me another chance. I know I can fix this. I promise."
    ),
    "GANG_MEMBER": (
        "The sweep is complete. No contacts, no resistance. The item was "
        "recovered from the third floor apartment. We are awaiting your "
        "instructions on how to proceed."
    ),
}

# ── Per-character generation kwargs ─────────────────────────────────────────
# Lower temperature for NARRATOR → less clip-to-clip vocal drift.
CHAR_KWARGS = {
    "NARRATOR": {"temperature": 0.7},
}

# ── Text normalisation ────────────────────────────────────────────────────────
def fix(text: str) -> str:
    return (
        text
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u2026", "...").replace("\u2014", "--").replace("\u2013", "-")
        .replace("Yayy", "Yaaay").replace("yayy", "yaaay")
        # "Awww." → "Awww," — period stops the TTS; comma flows into the sentence
        .replace("Awww.", "Awww,").replace("Aww.", "Aww,")
    )

# ── Script parser ─────────────────────────────────────────────────────────────
SEG_RE = re.compile(r"^(S(\d{2})-(\d{3})) \[(\w+)\] (.+)$")
EXPR_RE = re.compile(r"\[[\w][\w-]*\]")

def parse_script() -> list:
    segments, pending = [], 0.15
    with open(SCRIPT, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if   line == "[SCENE-BREAK]":   pending = max(pending, 2.0)
            elif line == "[SECTION-BREAK]": pending = max(pending, 1.5)
            elif line == "[SHORT-PAUSE]":   pending = max(pending, 0.4)
            elif line.startswith("S"):
                m = SEG_RE.match(line)
                if m:
                    text = EXPR_RE.sub("", m.group(5)).strip()
                    segments.append({
                        "id":      m.group(1),
                        "scene":   int(m.group(2)),
                        "speaker": m.group(4),
                        "text":    text,
                        "pause":   pending,
                    })
                    pending = 0.15
    return segments

# ── Silence ───────────────────────────────────────────────────────────────────
def silence(sec: float) -> np.ndarray:
    return np.zeros(int(SR * sec), dtype=np.float32)

# ── RMS quality check ─────────────────────────────────────────────────────────
RMS_MIN = 0.01

# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    args = sys.argv[1:]
    segments = parse_script()
    print(f"Parsed {len(segments)} segments from {SCRIPT.name}", flush=True)

    # ── stitch-only ───────────────────────────────────────────────────────
    if args == ["stitch"]:
        wav_files = sorted(SEGS.glob("S*.wav"))
        if not wav_files:
            print("No segment files found. Generate scenes first.", flush=True)
            sys.exit(1)
        pause_map = {
            f"{s['id'].replace('-', '_')}_{s['speaker']}.wav": s["pause"]
            for s in segments
        }
        stitch([(f, pause_map.get(f.name, 0.4)) for f in wav_files])
        return

    # ── scene selection ───────────────────────────────────────────────────
    if args and all(a.isdigit() for a in args):
        scene_filter = [int(a) for a in args]
        full_run = False
    else:
        scene_filter = list(range(1, 9))
        full_run = True

    target = [s for s in segments if s["scene"] in scene_filter]
    print(f"Scenes {scene_filter}: {len(target)} segments", flush=True)
    if not target:
        return

    # ── verify reference files exist ─────────────────────────────────────
    needed_chars = {s["speaker"] for s in target} & set(CHAR_REFS)
    print("\nChecking reference files:", flush=True)
    missing = []
    for char in sorted(needed_chars):
        ref = CHAR_REFS[char]
        if ref.exists():
            kb = ref.stat().st_size // 1024
            print(f"  ✓ {char:15} {ref.name}  ({kb} KB)", flush=True)
        else:
            print(f"  ✗ {char:15} MISSING: {ref}", flush=True)
            missing.append(char)
    if missing:
        print(f"\nAbort: {len(missing)} reference file(s) missing.", flush=True)
        sys.exit(1)

    # ── load model ────────────────────────────────────────────────────────
    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
    DTYPE  = torch.float16 if DEVICE != "cpu" else torch.float32
    print(f"\nDevice: {DEVICE}  dtype: {DTYPE}", flush=True)

    from qwen_tts import Qwen3TTSModel  # type: ignore
    print("Loading Qwen3-TTS-Base (clone model)...", flush=True)
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=DEVICE,
        dtype=DTYPE,
        attn_implementation="eager",
    )
    print("Loaded.\n", flush=True)

    # ── build clone prompts ───────────────────────────────────────────────
    print("Building clone prompts...", flush=True)
    prompts: dict = {}
    for char in sorted(needed_chars):
        ref_path = CHAR_REFS[char]
        ref_text = fix(CHAR_TEXTS[char])
        try:
            prompts[char] = model.create_voice_clone_prompt(
                ref_audio=str(ref_path),
                ref_text=ref_text,
            )
            print(f"  ✓ {char}", flush=True)
        except Exception as e:
            print(f"  ✗ {char}: {e}", flush=True)

    print(f"\n{len(prompts)}/{len(needed_chars)} prompts ready\n", flush=True)

    # ── generate clips ────────────────────────────────────────────────────
    generated = skipped = 0
    errors: list = []

    for seg in target:
        char  = seg["speaker"]
        fname = f"{seg['id'].replace('-', '_')}_{char}.wav"
        dest  = SEGS / fname

        if dest.exists():
            skipped += 1
            print(f"  [skip] {fname}", flush=True)
            continue

        if char not in prompts:
            print(f"  [skip] {fname}  (no prompt for {char})", flush=True)
            errors.append(fname)
            continue

        text_in    = fix(seg["text"])
        gen_kwargs = CHAR_KWARGS.get(char, {})
        print(f"  [gen]  {fname}", flush=True)

        ok = False
        for attempt in range(1, 4):
            try:
                wavs, sr = generate_with_timeout(
                    model, text_in, "English", prompts[char], **gen_kwargs,
                )
                audio = wavs[0]
                rms   = float(np.sqrt(np.mean(audio ** 2)))
                dur   = len(audio) / sr
                if rms < RMS_MIN:
                    print(f"  [retry {attempt}] rms={rms:.4f} too low", flush=True)
                    continue
                sf.write(str(dest), audio, sr)
                kb = dest.stat().st_size / 1024
                print(f"  [ok]   {fname}  ({kb:.0f} KB  {dur:.1f}s  rms={rms:.3f})",
                      flush=True)
                generated += 1
                ok = True
                break
            except TimeoutError:
                print(f"  [timeout attempt {attempt}] {fname} — exceeded {TIMEOUT_SEC}s, retrying",
                      flush=True)
            except Exception as e:
                print(f"  [err attempt {attempt}] {fname}: {e}", flush=True)

        if not ok:
            errors.append(fname)

    # ── summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*55}", flush=True)
    print(f"  Generated : {generated}", flush=True)
    print(f"  Skipped   : {skipped}", flush=True)
    print(f"  Errors    : {len(errors)}", flush=True)
    for e in errors:
        print(f"    ✗ {e}", flush=True)

    # ── auto-stitch on full run ───────────────────────────────────────────
    if full_run:
        total = len(list(SEGS.glob("S*.wav")))
        if total >= len(segments) * 0.95:
            pause_map = {
                f"{s['id'].replace('-', '_')}_{s['speaker']}.wav": s["pause"]
                for s in segments
            }
            stitch([(f, pause_map.get(f.name, 0.4))
                    for f in sorted(SEGS.glob("S*.wav"))])


def stitch(files: list) -> None:
    out_path = OUT / "audiobook_FINAL.wav"
    print(f"\nStitching {len(files)} clips → {out_path.name}", flush=True)
    chunks = [silence(1.0)]
    for path, pause_before in files:
        chunks.append(silence(pause_before))
        audio, _ = sf.read(str(path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        chunks.append(audio)
    chunks.append(silence(2.0))
    full = np.concatenate(chunks)
    sf.write(str(out_path), full, SR)
    dur = len(full) / SR
    mb  = out_path.stat().st_size / 1_048_576
    print(f"  ✓ {out_path.name}  —  {int(dur//60)}m {int(dur%60)}s  ({mb:.1f} MB)",
          flush=True)


if __name__ == "__main__":
    main()