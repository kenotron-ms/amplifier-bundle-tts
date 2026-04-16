#!/usr/bin/env python3
"""
Generate one 8-12s seed WAV per character using Qwen3-TTS VoiceDesign.
Seeds are used as reference audio for cloning in all three arena models.
Run: .venv/bin/python make_seeds.py
"""
import torch
import soundfile as sf
from pathlib import Path

OUT = Path(__file__).parent / "voices" / "seeds"
OUT.mkdir(parents=True, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
DTYPE  = torch.float16 if DEVICE != "cpu" else torch.float32
print(f"Device: {DEVICE}  dtype: {DTYPE}", flush=True)

from qwen_tts import Qwen3TTSModel
print("Loading Qwen3-TTS VoiceDesign...", flush=True)
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map=DEVICE,
    dtype=DTYPE,
    attn_implementation="eager",
)
print("Loaded.\n", flush=True)

# Each seed: ~20-25 words of in-character neutral speech (~8-10 seconds)
# Establishes voice identity — not performing the story
SEEDS = {
    "NARRATOR": {
        "text": "The city was quiet at night, or it should have been. Occasional gunshots pierced the silence. Chase ignored them — they were par for the course. He opened the fridge, rummaged around, and finally settled on some noodles. Somewhere in the building below, a door clicked shut. Nobody noticed. Nobody ever did.",
        "instruct": "Male, 50s, deep voice, slightly gravelly warmth, American, experienced audiobook narrator — unhurried and knowing, measured pace with a slight breath between thoughts. The kind of voice you trust implicitly.",
    },
    "CHASE": {
        "text": "I know what I am. I know what I've done to keep this family going. You think I don't see what it costs? I see it every day. But a man does what he has to, and I'd do it all again if it meant keeping them safe.",
        "instruct": "Male, early 30s, natural American baritone — a working man's voice, tired but intelligent, someone who carries more than he lets on. Genuine warmth when speaking about his family, quiet resignation about his choices. Natural human speech with subtle emotional color — never flat, never robotic, never theatrical.",
    },
    "LIA": {
        "text": "I'm not asking you to be someone you're not. I just need you to come home. That's all. Just come home to us at the end of the day.",
        "instruct": "Female, 30s, warm caring voice, moderate pitch, American, gentle firmness, genuine love and worry behind every word",
    },
    "JACK": {
        "text": "Can you tell me another story, dad? I like the one about the hero. He's my favorite. Does he ever get scared? I think I would get scared.",
        "instruct": "Child, approximately 6 years old, young American boy, innocent and curious, slightly breathless with excitement, high clear voice, natural child speech patterns",
    },
    "BLAZE": {
        "text": "Let me be very clear about something. When I give an instruction, I expect it followed. Not almost. Not with excuses or caveats. Followed. Completely.",
        "instruct": "Male, mid 40s, very deep voice, cold and controlled, American, each word chosen and placed with precision, dangerous quiet menace",
    },
    "CRUM": {
        "text": "I swear it wasn't my fault. I did everything right, every single step. Please, just give me another chance. I know I can fix this. I promise.",
        "instruct": "Male, young adult, high pitch, American, nervous energy, speaks too fast when frightened, voice cracks under pressure, desperate",
    },
    "GANG_MEMBER": {
        "text": "The sweep is complete. No contacts, no resistance. The item was recovered from the third floor apartment. We are awaiting your instructions on how to proceed.",
        "instruct": "Male, mid 30s, low moderate pitch, American, flat professional tone, delivers information without emotion, subordinate but competent",
    },
}

for name, cfg in SEEDS.items():
    out = OUT / f"{name}.wav"
    if out.exists():
        print(f"  [skip] {name}.wav", flush=True)
        continue
    print(f"  [gen]  {name}.wav", flush=True)
    print(f"         {cfg['instruct'][:70]}...", flush=True)
    try:
        wavs, sr = model.generate_voice_design(
            text=cfg["text"],
            language="English",
            instruct=cfg["instruct"],
        )
        sf.write(str(out), wavs[0], sr)
        duration = len(wavs[0]) / sr
        kb = out.stat().st_size / 1024
        print(f"  [ok]   {name}.wav  ({kb:.0f} KB  {duration:.1f}s)", flush=True)
    except Exception as e:
        print(f"  [ERR]  {name}: {e}", flush=True)
        import traceback
        traceback.print_exc()

print("\nAll seeds complete.", flush=True)