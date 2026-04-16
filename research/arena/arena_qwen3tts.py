#!/usr/bin/env python3
"""
Arena test — Qwen3-TTS VoiceDesign
Each character described in natural language — INCLUDING a 6-year-old child for Jack.
Uses MPS (Apple Silicon) with eager attention (no FlashAttention2 required).
Run: .venv/bin/python arena_qwen3tts.py
"""
import torch
import soundfile as sf
from pathlib import Path

OUT = Path(__file__).parent / "audio" / "arena" / "qwen3tts"
OUT.mkdir(parents=True, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
DTYPE  = torch.float16 if DEVICE != "cpu" else torch.float32
print(f"Device: {DEVICE}  dtype: {DTYPE}", flush=True)

from qwen_tts import Qwen3TTSModel  # pip install qwen-tts

print("Loading Qwen3-TTS-VoiceDesign (1.7B)...", flush=True)
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map=DEVICE,
    dtype=DTYPE,
    attn_implementation="eager",   # works on MPS without FlashAttn
)
print("Loaded.", flush=True)


def gen(fname: str, text: str, instruct: str):
    out = OUT / fname
    if out.exists():
        print(f"  [skip] {fname}", flush=True)
        return
    print(f"  [gen]  {fname}", flush=True)
    print(f"         » {instruct[:90]}...", flush=True)
    try:
        wavs, sr = model.generate_voice_design(
            text=text,
            language="English",
            instruct=instruct,
        )
        sf.write(str(out), wavs[0], sr)
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {fname}  ({kb:.0f} KB)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {fname}: {e}", flush=True)
        import traceback
        traceback.print_exc()


gen(
    "01_narrator.wav",
    "The city was quiet at night, or it should be at least. "
    "Occasional gunshots pierced the silence. Chase ignored them — "
    "they were par for the course anyway.",
    "Male, 40s, low pitch, measured authoritative voice, slightly gravelly, "
    "noir storytelling quality, American, deliberate unhurried pace",
)

gen(
    "02_chase_heavy.wav",
    "I've killed people, Lia.",
    "Male, early 30s, world-weary, moderate pitch, American, "
    "speaking with deep guilt and shame, voice barely above a murmur, heavy and tired",
)

gen(
    "03_chase_resigned.wav",
    "Maybe this is a conversation for tomorrow... I'll stay home to figure it out.",
    "Male, early 30s, world-weary, moderate pitch, American, "
    "resigned and exhausted, trailing off into quiet resolve",
)

gen(
    "04_lia.wav",
    "It does matter Chase, I don't want you to put yourself in danger for us.",
    "Female, 30s, warm caring voice, moderate pitch, American, "
    "worried undertone, firm but gentle, genuine concern",
)

# KEY DIFFERENTIATOR: Qwen3-TTS can describe a 6-year-old child voice
gen(
    "05_jack_question.wav",
    "Are we in trouble? But you and momma were too loud, and I lost my bear.",
    "Child, approximately 6 years old, young American boy, "
    "innocent and slightly confused, sleepy, high bright voice",
)

gen(
    "06_jack_yay.wav",
    "Yayy!",
    "Child, approximately 6 years old, young American boy, "
    "pure excitement and joy, high bright enthusiastic voice",
)

gen(
    "07_blaze_where.wav",
    "Where.",
    "Male, mid 40s, very deep voice, cold and controlled, American, "
    "single word delivered with quiet menace, completely flat affect, dangerous",
)

gen(
    "08_blaze_eight.wav",
    "She was only eight years old.",
    "Male, mid 40s, very deep voice, American, "
    "eerily flat tone concealing volcanic rage, devastatingly quiet, slow and precise",
)

gen(
    "09_blaze_mine.wav",
    "Lock down the building but don't mess with the Daemon. He's all mine.",
    "Male, mid 40s, very deep voice, cold controlled rage, American, "
    "low and deliberate, proprietary menace, each word chosen carefully",
)

print("\nQwen3-TTS arena complete.", flush=True)
