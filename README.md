# OmniVoice

Speech generation for [Amplifier](https://github.com/microsoft/amplifier) — three backends,
each optimised for a different job.

```
Podcast dialogue    →  Dia          (local, two-speaker, naturalistic)
Creative narration  →  Qwen3-TTS   (local, voice design or cloning)
Everything else     →  Gemini TTS  (cloud, 30 voices, instant, no GPU)
```

---

## Which backend should I use?

| I want to… | Use |
|-----------|-----|
| Generate a two-person podcast, interview, or dialogue scene | **Dia** |
| Narrate an audiobook with a specific character voice | **Qwen3-TTS** (clone) |
| Design a voice from scratch — age, accent, tone | **Qwen3-TTS** (design) |
| Read a slide deck or document aloud | **Gemini TTS** |
| Generate speech right now with no model download | **Gemini TTS** |
| Produce multi-language content without extra setup | **Gemini TTS** |
| Need full control over voice identity across many clips | **Qwen3-TTS** (clone) |

---

## Setup

### 1. Point Amplifier at this bundle

In `.amplifier/settings.yaml`:

```yaml
bundle:
  active: omnivoice
  sources:
    omnivoice: file:///path/to/omnivoice
```

### 2. Install the modules you need

Each backend is its own pip package. Install only what you'll use.

```bash
# Gemini only — no GPU, works anywhere
uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
  -e ./modules/tool-gemini-tts

# Local models (Dia + Qwen3-TTS)
uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
  -e ./modules/tool-dia \
  -e ./modules/tool-qwen3-tts

# All three
uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
  -e ./modules/tool-dia \
  -e ./modules/tool-qwen3-tts \
  -e ./modules/tool-gemini-tts
```

### 3. Gemini API key (if using Gemini)

Get a free key at [aistudio.google.com](https://aistudio.google.com) and export it:

```bash
export GOOGLE_API_KEY=your_key_here
```

### 4. PyTorch (if using Dia or Qwen3-TTS)

| Platform | Command |
|----------|---------|
| macOS Apple Silicon | `pip install torch torchaudio` |
| Linux + NVIDIA GPU | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124` |
| CPU only | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu` |

Model weights download automatically on first use (~3 GB per model).

---

## Dia — Podcast & Dialogue

Two speakers, one pass. Dia generates naturalistic conversation including laughter,
sighs, and other nonverbal sounds. The voices vary per run unless you fix a seed.

**Best for:** podcast episodes, interviews, two-character scenes, explainer dialogue.

```python
dia_generate_speech(
    script="""
    [S1] So we shipped the new inference pipeline on Friday.
    [S2] Friday afternoon deploy. Bold move. (laughs)
    [S1] I know, I know. But it actually worked first try.
    [S2] No way. What was different this time?
    [S1] Honestly? We just wrote better tests.
    """
)
```

Scripts always start with `[S1]` and alternate — never repeat the same speaker tag.
Target 5–20 seconds of audio per generation; very short inputs sound unnatural,
very long ones rush the delivery.

### Voice conditioning

Pass a 5–10s audio clip to nudge the voice style:

```python
dia_generate_speech(
    script="[S1] Welcome back to the show. [S2] Great to be here.",
    audio_prompt_path="reference.wav",
    audio_prompt_transcript="[S1] This is the reference clip transcript."
)
```

### Nonverbal sounds

Insert anywhere in the script:
`(laughs)` `(sighs)` `(coughs)` `(gasps)` `(clears throat)` `(chuckle)` `(mumbles)`
`(groans)` `(whistles)` `(humming)` `(sneezes)` `(applause)` `(inhales)` `(exhales)`

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `script` | required | Dialogue text with `[S1]`/`[S2]` tags |
| `audio_prompt_path` | — | WAV/MP3 for voice conditioning (5–10s) |
| `audio_prompt_transcript` | — | Transcript of prompt audio (required with above) |
| `output_path` | auto-named | Where to save the WAV |
| `seed` | random | Fix for reproducible voices |
| `cfg_scale` | `3.0` | Higher = more faithful to script |
| `temperature` | `1.8` | Sampling temperature |

---

## Qwen3-TTS — Creative Voice Design & Cloning

Two tools, two models. Design voices from a text description, or clone a voice
from a short reference clip. Full control over who speaks.

**Best for:** audiobooks, character narration, bespoke voice personas, any project
where voice consistency or a specific sound identity matters.

### Voice design — describe the voice you want

```python
qwen3_design_speech(
    text="The city never really sleeps. It just changes its face.",
    instruct="Male, 50s, deep gravelly warmth, American, experienced audiobook "
             "narrator — unhurried and knowing, the kind of voice you trust."
)
```

```python
qwen3_design_speech(
    text="Warning: this action cannot be undone.",
    instruct="Female, young adult, clear and neutral, British accent, slight urgency."
)
```

**`instruct` vocabulary** — mix and match freely:

| Dimension | Options |
|-----------|---------|
| Gender | `male`, `female` |
| Age | `child`, `teenager`, `young adult`, `middle-aged`, `elderly` |
| Pitch | `very low`, `low`, `moderate`, `high`, `very high pitch` |
| Accent | `american`, `british`, `australian`, `canadian`, `indian`, `chinese`, `korean`, `japanese` |
| Style | `whisper`, `gravelly`, `warm`, `breathy`, `energetic`, + free-form prose |

### Voice cloning — match an existing voice

```python
qwen3_clone_speech(
    text="Chapter three. The rain had not stopped in three days.",
    ref_audio_path="narrator.wav",           # 5–15s of clean speech
    ref_text="The city was quiet at night."  # exact transcript of the clip
)
```

The same `ref_audio_path` + `ref_text` pair produces a consistent voice identity
across every call — useful for generating entire audiobooks character-by-character.

### Parameters

**`qwen3_design_speech`**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `text` | required | Text to synthesize |
| `instruct` | required | Natural-language voice description |
| `language` | `English` | Language name |
| `output_path` | auto-named | Where to save the WAV |

**`qwen3_clone_speech`**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `text` | required | Text to synthesize |
| `ref_audio_path` | required | Reference WAV (5–15s) |
| `ref_text` | required | Exact transcript of the reference clip |
| `language` | `English` | Language name |
| `output_path` | auto-named | Where to save the WAV |

---

## Gemini TTS — All-Purpose Cloud Speech

30 curated prebuilt voices ranging from gravelly and warm to bright and upbeat.
No local model, no GPU, no setup beyond an API key. Works in any language Gemini supports.

**Best for:** presentations, reading documents or slides aloud, demos, notifications,
quick prototypes, any content where fast and flexible matters more than custom voice control.

```python
# Reading a slide
gemini_generate_speech(
    text="Q3 revenue grew 18% year over year, driven by expansion in APAC markets.",
    voice="Charon",     # Informative
    style="Read like a confident presenter, measured and clear."
)
```

```python
# Two-person exchange
gemini_generate_speech(
    text="Host: What made you decide to start the company?\n"
         "Guest: Honestly, I got tired of waiting for someone else to build it.",
    speakers=[
        {"speaker": "Host",  "voice": "Aoede"},    # Breezy
        {"speaker": "Guest", "voice": "Fenrir"},   # Excitable
    ]
)
```

```python
# Inline style control
gemini_generate_speech(
    text="[whispers] The results are in. [laughs] We actually did it.",
    voice="Sulafat"     # Warm
)
```

### Voice reference

| Voice | Character | Voice | Character | Voice | Character |
|-------|-----------|-------|-----------|-------|-----------|
| Zephyr | Bright | Puck | Upbeat | Charon | Informative |
| **Kore** | **Firm** *(default)* | Fenrir | Excitable | Leda | Youthful |
| Orus | Firm | Aoede | Breezy | Callirrhoe | Easy-going |
| Autonoe | Bright | Enceladus | Breathy | Iapetus | Clear |
| Umbriel | Easy-going | Algieba | Smooth | Despina | Smooth |
| Erinome | Clear | Algenib | Gravelly | Rasalgethi | Informative |
| Laomedeia | Upbeat | Achernar | Soft | Alnilam | Firm |
| Schedar | Even | Gacrux | Mature | Pulcherrima | Forward |
| Achird | Friendly | Zubenelgenubi | Casual | Vindemiatrix | Gentle |
| Sadachbia | Lively | Sadaltager | Knowledgeable | Sulafat | Warm |

### Models

| Model | Speed | Notes |
|-------|-------|-------|
| `gemini-3.1-flash-tts-preview` | Fastest | Default |
| `gemini-2.5-flash-preview-tts` | Fast | — |
| `gemini-2.5-pro-preview-tts` | Slower | Highest quality |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `text` | required | Text to synthesize. Supports `[whispers]` `[laughs]` `[sighs]` `[gasp]` `[cough]` |
| `voice` | `Kore` | Prebuilt voice name |
| `style` | — | Style instruction prepended to the text |
| `speakers` | — | Multi-speaker list: `[{"speaker": "Name", "voice": "Voice"}, ...]` (max 2) |
| `model` | `gemini-3.1-flash-tts-preview` | TTS model |
| `output_path` | auto-named | Where to save the WAV |

---

## Repository layout

```
omnivoice/
├── bundle.md                    # Amplifier bundle — includes all three behaviors
├── behaviors/
│   ├── dia.yaml                 # Mounts tool-dia, includes context
│   ├── qwen3-tts.yaml           # Mounts tool-qwen3-tts, includes context
│   └── gemini-tts.yaml          # Mounts tool-gemini-tts, includes context
├── context/
│   ├── dia.md                   # Dia reference (injected into agent sessions)
│   ├── qwen3-tts.md             # Qwen3-TTS reference
│   └── gemini-tts.md            # Gemini TTS reference
├── modules/
│   ├── tool-dia/                # pip: amplifier-module-tool-dia
│   ├── tool-qwen3-tts/          # pip: amplifier-module-tool-qwen3-tts
│   └── tool-gemini-tts/         # pip: amplifier-module-tool-gemini-tts
├── scripts/                     # Audiobook production scripts
├── content/                     # Story source and production script
├── voices/seeds/                # Character reference audio files
└── docs/                        # Project notes
```
