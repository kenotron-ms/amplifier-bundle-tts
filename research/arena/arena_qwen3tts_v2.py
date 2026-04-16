#!/usr/bin/env python3
"""
Arena v2 — Qwen3-TTS Voice Clone
Uses Qwen3-TTS-Base model to clone from the VoiceDesign seeds.
"Design then Clone" workflow: consistent character voice across all clips.
Run: .venv/bin/python arena_qwen3tts_v2.py
"""
import traceback
import torch
import soundfile as sf
from pathlib import Path

SEEDS = Path(__file__).parent / "voices" / "seeds"
OUT   = Path(__file__).parent / "audio" / "arena" / "qwen3tts_v2"
OUT.mkdir(parents=True, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
DTYPE  = torch.float16 if DEVICE != "cpu" else torch.float32
print(f"Device: {DEVICE}  dtype: {DTYPE}", flush=True)

from qwen_tts import Qwen3TTSModel  # noqa: E402

print("Loading Qwen3-TTS-Base (clone model)...", flush=True)
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map=DEVICE,
    dtype=DTYPE,
    attn_implementation="eager",
)
print("Loaded.\n", flush=True)

# Seed texts MUST match what make_seeds.py generated exactly
SEED_TEXTS = {
    "NARRATOR":
        "In a city like this, you learn real quick that silence is just another "
        "kind of noise. The night never really sleeps -- it just changes its face.",
    "CHASE":
        "Look, I didn't get into this because I wanted to. Nobody does. You tell "
        "yourself it's temporary, and then one day you look up and realize it just isn't anymore.",
    "LIA":
        "I'm not asking you to be someone you're not. I just need you to come home. "
        "That's all. Just come home to us at the end of the day.",
    "JACK":
        "Can you tell me another story, dad? I like the one about the hero. "
        "He's my favorite. Does he ever get scared? I think I would get scared.",
    "BLAZE":
        "Let me be very clear about something. When I give an instruction, I expect "
        "it followed. Not almost. Not with excuses or caveats. Followed. Completely.",
    "CRUM":
        "I swear it wasn't my fault. I did everything right, every single step. "
        "Please, just give me another chance. I know I can fix this. I promise.",
    "GANG_MEMBER":
        "The sweep is complete. No contacts, no resistance. The item was recovered "
        "from the third floor apartment. We are awaiting your instructions on how to proceed.",
}


def fix_text(text: str) -> str:
    return (
        text.replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u2026", "...").replace("\u2014", "--").replace("\u2013", "-")
        .replace("Yayy", "Yaaay").replace("yayy", "yaaay")
    )


# Build clone prompts once per character — reuse for all lines of that character
print("Building clone prompts from seeds...", flush=True)
prompts: dict = {}
for char, seed_text in SEED_TEXTS.items():
    seed_path = SEEDS / f"{char}.wav"
    if not seed_path.exists():
        print(f"  [WARN] seed missing for {char} — run make_seeds.py first", flush=True)
        continue
    try:
        prompts[char] = model.create_voice_clone_prompt(
            ref_audio=str(seed_path),
            ref_text=fix_text(seed_text),
        )
        print(f"  [ok]   {char} prompt built", flush=True)
    except Exception as e:
        print(f"  [ERR]  {char} prompt failed: {e}", flush=True)

print(f"\n{len(prompts)}/7 prompts ready — generating clips...\n", flush=True)

CLIPS = [
    ("01_narrator.wav",
     "The city was quiet at night, or it should be at least. "
     "Occasional gunshots pierced the silence. Chase ignored them -- "
     "they were par for the course anyway.",
     "NARRATOR"),
    ("02_chase_heavy.wav",    "I've killed people, Lia.",              "CHASE"),
    ("03_chase_resigned.wav", "Maybe this is a conversation for tomorrow... "
                              "I'll stay home to figure it out.",      "CHASE"),
    ("04_lia.wav",            "It does matter Chase, I don't want you to put "
                              "yourself in danger for us.",             "LIA"),
    ("05_jack_question.wav",  "Are we in trouble? But you and momma were too loud, "
                              "and I lost my bear.",                    "JACK"),
    ("06_jack_yay.wav",       "Yayy!",                                 "JACK"),
    ("07_blaze_where.wav",    "Where.",                                "BLAZE"),
    ("08_blaze_eight.wav",    "She was only eight years old.",         "BLAZE"),
    ("09_blaze_mine.wav",     "Lock down the building but don't mess with the Daemon. "
                              "He's all mine.",                         "BLAZE"),
]

for fname, text, char in CLIPS:
    out = OUT / fname
    if out.exists():
        print(f"  [skip] {fname}", flush=True)
        continue
    if char not in prompts:
        print(f"  [skip] {fname}: no prompt for {char}", flush=True)
        continue
    print(f"  [gen]  {fname}  [{char}]", flush=True)
    try:
        wavs, sr = model.generate_voice_clone(
            text=fix_text(text),
            language="English",
            voice_clone_prompt=prompts[char],
        )
        sf.write(str(out), wavs[0], sr)
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {fname}  ({kb:.0f} KB)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {fname}: {e}", flush=True)
        traceback.print_exc()

print("\nQwen3-TTS v2 arena complete.", flush=True)
