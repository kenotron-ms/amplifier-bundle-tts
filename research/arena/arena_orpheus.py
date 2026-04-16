#!/usr/bin/env python3
"""
Arena test — Orpheus TTS (orpheus-cpp + Metal GPU on Apple Silicon)
Named voices: same voice_id = identical voice every call.
Run: .venv/bin/python arena_orpheus.py
"""
import numpy as np
from pathlib import Path
from scipy.io.wavfile import write as wav_write

OUT = Path(__file__).parent / "audio" / "arena" / "orpheus"
OUT.mkdir(parents=True, exist_ok=True)
SR = 24_000

from orpheus_cpp import OrpheusCpp

print("Loading Orpheus (orpheus-cpp + Metal)...", flush=True)
orpheus = OrpheusCpp(verbose=False, lang="en")
print("Loaded.", flush=True)


def gen(fname: str, text: str, voice: str):
    out = OUT / fname
    if out.exists():
        print(f"  [skip] {fname}", flush=True)
        return
    print(f"  [gen]  {fname}  voice={voice}", flush=True)
    try:
        chunks = []
        for _, (sr, chunk) in enumerate(
            orpheus.stream_tts_sync(text, options={"voice_id": voice})
        ):
            chunks.append(chunk)
        if not chunks:
            print(f"  [ERR]  {fname}: no chunks generated", flush=True)
            return
        audio = np.concatenate(chunks, axis=-1).flatten()
        wav_write(str(out), SR, audio.astype(np.int16))
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {fname}  ({kb:.0f} KB)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {fname}: {e}", flush=True)
        import traceback
        traceback.print_exc()


# Voice map — using the 8 named presets
# leo = deep/authoritative male    dan = warm/world-weary male
# tara = warm female (best overall)  mia = lighter female
# zac = younger male               zoe = softer female
# NOTE: no child voice exists in Orpheus — mia is used for Jack (limitation)

gen("01_narrator.wav",
    "The city was quiet at night, or it should be at least. "
    "Occasional gunshots pierced the silence. Chase ignored them — "
    "they were par for the course anyway.",
    "leo")

gen("02_chase_heavy.wav",
    "<sigh> I've killed people, Lia.",
    "dan")

gen("03_chase_resigned.wav",
    "Maybe this is a conversation for tomorrow... "
    "I'll stay home to figure it out.",
    "dan")

gen("04_lia.wav",
    "It does matter Chase, I don't want you to put yourself in danger for us.",
    "tara")

# Jack — no child preset; mia is the lightest voice available
# This demonstrates Orpheus's child voice gap vs Qwen3-TTS
gen("05_jack_question.wav",
    "Are we in trouble? But you and momma were too loud, and I lost my bear.",
    "mia")

gen("06_jack_yay.wav",
    "<giggle> Yayy!",
    "mia")

gen("07_blaze_where.wav",
    "Where.",
    "zac")

gen("08_blaze_eight.wav",
    "She was only eight years old.",
    "zac")

gen("09_blaze_mine.wav",
    "Lock down the building but don't mess with the Daemon. He's all mine.",
    "zac")

print("\nOrpheus arena complete.", flush=True)
