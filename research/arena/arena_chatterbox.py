#!/usr/bin/env python3
"""
Arena test — Chatterbox TTS
No reference audio: shows default voice quality + emotion exaggeration range.
Run: .venv/bin/python arena_chatterbox.py
"""
import sys
import torch
import soundfile as sf
from pathlib import Path

OUT = Path(__file__).parent / "audio" / "arena" / "chatterbox"
OUT.mkdir(parents=True, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {DEVICE}", flush=True)

from chatterbox.tts import ChatterboxTTS
model = ChatterboxTTS.from_pretrained(device=DEVICE)
SR = getattr(model, "sr", 24000)
print(f"Sample rate: {SR}", flush=True)

# (filename, text, exaggeration, cfg_weight)
# exaggeration: 0.2=flat/cold  0.4=neutral  0.6=expressive  0.8=dramatic
# cfg_weight:   0.3=fast/urgent  0.5=normal  0.7=slow/deliberate
CLIPS = [
    ("01_narrator.wav",
     "The city was quiet at night, or it should be at least. "
     "Occasional gunshots pierced the silence. Chase ignored them — "
     "they were par for the course anyway.",
     0.30, 0.60),

    ("02_chase_heavy.wav",
     "I've killed people, Lia.",
     0.45, 0.42),

    ("03_chase_resigned.wav",
     "Maybe this is a conversation for tomorrow... "
     "I'll stay home to figure it out.",
     0.40, 0.48),

    ("04_lia.wav",
     "It does matter Chase, I don't want you to put yourself in danger for us.",
     0.45, 0.50),

    ("05_jack_question.wav",
     "Are we in trouble? But you and momma were too loud, and I lost my bear.",
     0.60, 0.42),

    ("06_jack_yay.wav",
     "Yayy!",
     0.70, 0.38),

    ("07_blaze_where.wav",
     "Where.",
     0.20, 0.70),

    ("08_blaze_eight.wav",
     "She was only eight years old.",
     0.22, 0.68),

    ("09_blaze_mine.wav",
     "Lock down the building but don't mess with the Daemon. He's all mine.",
     0.25, 0.65),
]

torch.manual_seed(42)

for fname, text, exag, cfg in CLIPS:
    out = OUT / fname
    if out.exists():
        print(f"  [skip] {fname}", flush=True)
        continue
    print(f"  [gen]  {fname}  exag={exag}  cfg={cfg}", flush=True)
    try:
        wav = model.generate(text, exaggeration=exag, cfg_weight=cfg)
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        if hasattr(wav, "numpy"):
            audio = wav.squeeze(0).cpu().float().numpy()
        else:
            import torchaudio
            audio = wav.squeeze(0).cpu().float().numpy()
        sf.write(str(out), audio, SR)
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {fname}  ({kb:.0f} KB)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {fname}: {e}", flush=True)
        import traceback; traceback.print_exc()

print("\nChatterbox arena complete.", flush=True)
