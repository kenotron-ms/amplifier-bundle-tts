#!/usr/bin/env python3
"""
Arena v2 — Chatterbox TTS with voice cloning
Clones each character from their Qwen3-TTS seed WAV.
Run: .venv/bin/python arena_chatterbox_v2.py
"""
import traceback
import torch
import soundfile as sf
from pathlib import Path

SEEDS = Path(__file__).parent / "voices" / "seeds"
OUT   = Path(__file__).parent / "audio" / "arena" / "chatterbox_v2"
OUT.mkdir(parents=True, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {DEVICE}", flush=True)

from chatterbox.tts import ChatterboxTTS  # noqa: E402

model = ChatterboxTTS.from_pretrained(device=DEVICE)
SR = getattr(model, "sr", 24000)
torch.manual_seed(42)


def fix_text(text: str) -> str:
    """Normalise Unicode punctuation and fix TTS-unfriendly tokens."""
    return (
        text.replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u2026", "...").replace("\u2014", "--").replace("\u2013", "-")
        .replace("Yayy", "Yaaay").replace("yayy", "yaaay")
    )


# (filename, text, character_seed, exaggeration, cfg_weight)
CLIPS = [
    ("01_narrator.wav",
     "The city was quiet at night, or it should be at least. "
     "Occasional gunshots pierced the silence. Chase ignored them -- "
     "they were par for the course anyway.",
     "NARRATOR", 0.38, 0.57),  # cfg=0.57 — teeny bit slower than 0.52

    ("02_chase_heavy.wav",
     "I've killed people, Lia.",
     "CHASE", 0.45, 0.42),

    ("03_chase_resigned.wav",
     "Maybe this is a conversation for tomorrow... I'll stay home to figure it out.",
     "CHASE", 0.40, 0.48),

    ("04_lia.wav",
     "It does matter Chase, I don't want you to put yourself in danger for us.",
     "LIA", 0.45, 0.50),

    ("05_jack_question.wav",
     "Are we in trouble? But you and momma were too loud, and I lost my bear.",
     "JACK", 0.60, 0.42),

    ("06_jack_yay.wav",
     "Yayy!",          # fixed to Yaaay! by fix_text()
     "JACK", 0.70, 0.38),

    ("07_blaze_where.wav",
     "Where.",
     "BLAZE", 0.20, 0.70),

    ("08_blaze_eight.wav",
     "She was only eight years old.",
     "BLAZE", 0.22, 0.68),

    ("09_blaze_mine.wav",
     "Lock down the building but don't mess with the Daemon. He's all mine.",
     "BLAZE", 0.25, 0.65),
]

for fname, text, char, exag, cfg in CLIPS:
    out = OUT / fname
    if out.exists():
        print(f"  [skip] {fname}", flush=True)
        continue
    seed = SEEDS / f"{char}.wav"
    if not seed.exists():
        print(f"  [ERR]  {fname}: seed missing ({seed}) — run make_seeds.py first", flush=True)
        continue
    print(f"  [gen]  {fname}  [{char}]  exag={exag}  cfg={cfg}", flush=True)
    try:
        wav = model.generate(
            fix_text(text),
            audio_prompt_path=str(seed),
            exaggeration=exag,
            cfg_weight=cfg,
        )
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        audio = wav.squeeze(0).cpu().float().numpy()
        sf.write(str(out), audio, SR)
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {fname}  ({kb:.0f} KB)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {fname}: {e}", flush=True)
        traceback.print_exc()

print("\nChatterbox v2 arena complete.", flush=True)
