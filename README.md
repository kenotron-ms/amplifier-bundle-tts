# OmniVoice — TTS for Amplifier

**Two speech backends, one Amplifier tool module.** Generate audio from text with either:

- **OmniVoice** — local, free, no API key, runs on Apple Silicon / CUDA / CPU
- **Gemini TTS** — Google cloud API, 30 expressive voices, fast, no GPU needed

---

## As an Amplifier Bundle

Add to your Amplifier session by including this bundle:

```yaml
# In your bundle.md
includes:
  - bundle: file:///path/to/omnivoice
```

Or point Amplifier at it in `.amplifier/settings.yaml`:

```yaml
bundle:
  active: omnivoice
  sources:
    omnivoice: file:///path/to/omnivoice
```

### Install the tool module

The tool module must be installed into your Amplifier Python environment:

```bash
# From this repo
uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
  -e ./modules/tool-omnivoice
```

---

## Tools

### `generate_speech` — OmniVoice (local)

Generates a WAV file using the local [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) model.
No API key, no internet, no server. Model downloads automatically (~4 GB) on first use.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize. Supports expressive inline tags (see below). |
| `voice_id` | | ID from `list_voices` — reuse a saved named voice. |
| `instruct` | | Free-form voice design: `"female, british accent, high pitch"` |
| `ref_audio_path` | | 3–10 s WAV to clone that speaker's voice. |
| `ref_text` | | Transcript of the reference audio (auto-transcribed if omitted). |
| `output_path` | | Save path. Auto-named in CWD if omitted. |
| `num_step` | | Diffusion steps. Default `32`. Use `16` for fast previews. |
| `speed` | | Speed multiplier. `1.0` = normal. |

**Voice priority:** `voice_id` → `ref_audio_path` → `instruct` → random auto voice

**Expressive inline tags:**

| Tag | Effect |
|-----|--------|
| `[laughter]` | Natural laughter |
| `[sigh]` | Audible sigh |
| `[surprise-oh]` `[surprise-ah]` `[surprise-wa]` `[surprise-yo]` | Surprise variants |
| `[question-en]` `[question-ah]` `[question-oh]` | Question intonation |
| `[confirmation-en]` | Affirmative (uh-huh) |
| `[dissatisfaction-hnn]` | Dissatisfied grunt |

**Voice `instruct` attributes** (comma-separate any combination):

| Dimension | Options |
|-----------|---------|
| Gender | `male`, `female` |
| Age | `child`, `teenager`, `young adult`, `middle-aged`, `elderly` |
| Pitch | `very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch` |
| Style | `whisper` |
| Accent | `american`, `british`, `australian`, `canadian`, `indian`, `chinese`, `korean`, `japanese` |

---

### `gemini_generate_speech` — Gemini TTS (cloud)

Generates a WAV file via the [Google Gemini TTS API](https://ai.google.dev/gemini-api/docs/speech-generation).
Requires `GOOGLE_API_KEY`. No GPU needed.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize. Embed style inline: `"Say cheerfully: Have a wonderful day!"` Supports tags: `[whispers]`, `[laughs]`, `[sighs]`, `[gasp]`, `[cough]`. |
| `voice` | | Prebuilt voice name (default: `Kore`). See table below. |
| `style` | | Style instruction prepended to the text, e.g. `"Read like a warm audiobook narrator."` |
| `speakers` | | Multi-speaker list: `[{"speaker": "Joe", "voice": "Charon"}, ...]`. Max 2. |
| `model` | | `gemini-3.1-flash-tts-preview` (default), `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts` |
| `output_path` | | Save path. Auto-named in CWD if omitted. |

**30 prebuilt voices:**

| Voice | Style | Voice | Style | Voice | Style |
|-------|-------|-------|-------|-------|-------|
| Zephyr | Bright | Puck | Upbeat | Charon | Informative |
| Kore | Firm | Fenrir | Excitable | Leda | Youthful |
| Orus | Firm | Aoede | Breezy | Callirrhoe | Easy-going |
| Autonoe | Bright | Enceladus | Breathy | Iapetus | Clear |
| Umbriel | Easy-going | Algieba | Smooth | Despina | Smooth |
| Erinome | Clear | Algenib | Gravelly | Rasalgethi | Informative |
| Laomedeia | Upbeat | Achernar | Soft | Alnilam | Firm |
| Schedar | Even | Gacrux | Mature | Pulcherrima | Forward |
| Achird | Friendly | Zubenelgenubi | Casual | Vindemiatrix | Gentle |
| Sadachbia | Lively | Sadaltager | Knowledgeable | Sulafat | Warm |

**Multi-speaker example:**

```python
gemini_generate_speech(
    text="Alice: Did the deploy work?\nBob: First try. [laughs]",
    speakers=[
        {"speaker": "Alice", "voice": "Aoede"},
        {"speaker": "Bob",   "voice": "Charon"},
    ]
)
```

---

### `save_voice` — Save a named OmniVoice voice

Saves a voice to `~/.amplifier/omnivoice/voices.json` for future reuse with `generate_speech`.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | ✓ | Friendly name, e.g. `"Narrator"`. |
| `instruct` | | Voice design string. |
| `ref_audio_path` | | Path to reference audio for cloning (3–10 s). |
| `ref_text` | | Transcript of the reference audio (optional). |

Returns the `voice_id` to pass to `generate_speech`.

---

### `list_voices` — List saved OmniVoice voices

Lists all voices saved with `save_voice`, showing their IDs, names, modes, and configurations.

---

## OmniVoice Studio (Web UI)

A local web UI for auditioning voices and generating audio interactively.

```bash
# macOS Apple Silicon
pip install torch torchaudio

# Linux + CUDA 12.4
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# Start the studio
pip install -r requirements.txt
./run.sh
# → http://localhost:8000
```

**Features:** Voice library sidebar · Auto/Design/Clone voice modes · Expressive tag toolbar ·
Diffusion step and speed controls · In-browser playback and download

---

## Platform Support

### OmniVoice (local inference)

| Platform | Acceleration | PyTorch source |
|----------|-------------|----------------|
| macOS Apple Silicon | MPS (Metal) | `pip install torch torchaudio` |
| macOS Intel | CPU | `pip install torch torchaudio` |
| Linux x86_64 + NVIDIA | CUDA | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124` |
| Linux / Windows CPU | CPU | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu` |

### Gemini TTS (cloud)

Set `GOOGLE_API_KEY` (get one free at [aistudio.google.com](https://aistudio.google.com)):

```bash
export GOOGLE_API_KEY=your_key_here
```

---

## Repository Layout

```
omnivoice/
├── bundle.md                    # Amplifier bundle definition
├── behaviors/omnivoice.yaml     # Registers the tool module
├── context/omnivoice.md         # Context injected into agent sessions
├── modules/
│   └── tool-omnivoice/          # pip-installable Amplifier tool module
│       ├── pyproject.toml
│       └── amplifier_module_tool_omnivoice/__init__.py
├── main.py                      # FastAPI web UI server
├── static/index.html            # Web UI (single-page app)
├── run.sh                       # Start the web UI
├── requirements.txt             # Web UI Python deps
├── scripts/                     # Audiobook production scripts
├── content/                     # Story source and production script
├── research/arena/              # TTS model evaluation (scripts + output)
└── voices/seeds/                # Character reference audio files
```

---

## Voice persistence

OmniVoice named voices persist to `~/.amplifier/omnivoice/voices.json`.
Reference audio is copied to `~/.amplifier/omnivoice/ref_audio/` so voice clones
survive file moves.
