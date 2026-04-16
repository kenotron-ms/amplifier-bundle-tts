#!/usr/bin/env python3
"""
Arena v2 — Orpheus TTS (orpheus-cpp + Metal)
NOTE: orpheus-cpp finetuned model uses fixed named voices — no ref audio cloning.
Named voices are perfectly consistent across calls by design.
Run: .venv/bin/python arena_orpheus_v2.py
"""
import traceback
import numpy as np
from pathlib import Path
from scipy.io.wavfile import write as wav_write

OUT = Path(__file__).parent / "audio" / "arena" / "orpheus_v2"
OUT.mkdir(parents=True, exist_ok=True)
SR = 24_000

from orpheus_cpp import OrpheusCpp  # noqa: E402

print("Loading Orpheus (orpheus-cpp)...", flush=True)
orpheus = OrpheusCpp(verbose=False, lang="en")
print("Loaded.", flush=True)


def fix_text(text: str) -> str:
    return (
        text.replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u2026", "...").replace("\u2014", "--").replace("\u2013", "-")
        .replace("Yayy", "Yaaay").replace("yayy", "yaaay")
    )


def gen(fname: str, text: str, voice: str, tag_text: str = None):
    out = OUT / fname
    if out.exists():
        print(f"  [skip] {fname}", flush=True)
        return
    tts_in = fix_text(tag_text if tag_text else text)
    print(f"  [gen]  {fname}  voice={voice}", flush=True)
    try:
        chunks = []
        for _, (sr, chunk) in enumerate(
            orpheus.stream_tts_sync(tts_in, options={"voice_id": voice})
        ):
            chunks.append(chunk)
        if not chunks:
            print(f"  [ERR]  {fname}: no output generated", flush=True)
            return
        audio = np.concatenate(chunks, axis=-1).flatten()
        wav_write(str(out), SR, audio.astype(np.int16))
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {fname}  ({kb:.0f} KB)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {fname}: {e}", flush=True)
        traceback.print_exc()


# Voice map:  leo=deep/authoritative  dan=world-weary  tara=warm female
#             mia=lightest (Jack — not a child, Orpheus limitation)  zac=intense male
gen("01_narrator.wav",
    "The city was quiet at night, or it should be at least. "
    "Occasional gunshots pierced the silence. Chase ignored them -- "
    "they were par for the course anyway.",
    "leo")

gen("02_chase_heavy.wav",
    "I've killed people, Lia.",
    "dan",
    tag_text="<sigh> I've killed people, Lia.")

gen("03_chase_resigned.wav",
    "Maybe this is a conversation for tomorrow... I'll stay home to figure it out.",
    "dan")

gen("04_lia.wav",
    "It does matter Chase, I don't want you to put yourself in danger for us.",
    "tara")

gen("05_jack_question.wav",
    "Are we in trouble? But you and momma were too loud, and I lost my bear.",
    "mia")

gen("06_jack_yay.wav",
    "Yayy!",
    "mia",
    tag_text="<giggle> Yaaay!")

gen("07_blaze_where.wav",
    "Where.",
    "zac")

gen("08_blaze_eight.wav",
    "She was only eight years old.",
    "zac")

gen("09_blaze_mine.wav",
    "Lock down the building but don't mess with the Daemon. He's all mine.",
    "zac")

print("\nOrpheus v2 arena complete.", flush=True)
