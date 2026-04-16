# OmniVoice — TTS for Amplifier

Three TTS backends as separate, independently-installable Amplifier tool modules:

| Module | Tool(s) | Backend | Key strength |
|--------|---------|---------|-------------|
| `tool-dia` | `dia_generate_speech` | nari-labs/Dia-1.6B | Podcast/dialogue, two-speaker, nonverbals |
| `tool-qwen3-tts` | `qwen3_design_speech` `qwen3_clone_speech` | Qwen3-TTS | Voice design by instruct, or voice cloning |
| `tool-gemini-tts` | `gemini_generate_speech` | Google Gemini TTS | 30 prebuilt voices, cloud, fastest, multi-speaker |

---

## As an Amplifier Bundle

Point Amplifier at this repo in `.amplifier/settings.yaml`:

```yaml
bundle:
  active: omnivoice
  sources:
    omnivoice: file:///path/to/omnivoice
```

Or include it from another bundle:

```yaml
includes:
  - bundle: file:///path/to/omnivoice
```

### Install the tool modules

Each module is a separate pip package. Install the ones you want:

```bash
# All three
uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
  -e ./modules/tool-dia \
  -e ./modules/tool-qwen3-tts \
  -e ./modules/tool-gemini-tts

# Just the cloud one (no GPU needed)
uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
  -e ./modules/tool-gemini-tts
```

---

## Tool Reference

### `dia_generate_speech`

Generates two-speaker podcast/dialogue audio using [Dia 1.6B](https://github.com/nari-labs/dia).
Local inference. Downloads ~3 GB on first use.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `script` | ✓ | Text with `[S1]`/`[S2]` tags. Always start with `[S1]`, alternate speakers. |
| `audio_prompt_path` | | WAV (5-10s) to condition voice style. Requires `audio_prompt_transcript`. |
| `audio_prompt_transcript` | | Transcript of the voice prompt (with `[S1]`/`[S2]` tags). |
| `output_path` | | Save path. Auto-named if omitted. |
| `seed` | | Integer for reproducible voices. |
| `cfg_scale` | | Guidance scale. Default 3.0. |
| `temperature` | | Sampling temperature. Default 1.8. |

**Script format:** `[S1] line one. [S2] line two. [S1] line three.`

**Nonverbals:** `(laughs)` `(sighs)` `(coughs)` `(gasps)` `(clears throat)` `(chuckle)` `(mumbles)` `(whistles)` `(groans)` `(humming)` `(sneezes)` `(applause)` `(inhales)` `(exhales)`

**Best for:** Podcast episodes, interviews, explainer dialogue, two-character scenes

---

### `qwen3_design_speech`

Design a voice on the fly with a natural-language description. Uses [Qwen3-TTS-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize. |
| `instruct` | ✓ | Natural-language voice description. |
| `language` | | Language name. Default `English`. |
| `output_path` | | Save path. Auto-named if omitted. |

**`instruct` attributes** (combine freely): `male`/`female` · `child`/`teenager`/`young adult`/`middle-aged`/`elderly` · `very low`/`low`/`moderate`/`high`/`very high pitch` · `american`/`british`/`australian`/`canadian`/`indian`/`chinese`/`korean`/`japanese` · `whisper` · and any free-form style prose

**Best for:** Narration, explainers, characters without a reference file

---

### `qwen3_clone_speech`

Clone a voice from a reference audio file. Uses [Qwen3-TTS-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize in the cloned voice. |
| `ref_audio_path` | ✓ | Path to a WAV of the voice to clone (5-15s). |
| `ref_text` | ✓ | Exact transcript of the reference audio. |
| `language` | | Language name. Default `English`. |
| `output_path` | | Save path. Auto-named if omitted. |

**Best for:** Character audiobooks, consistent voices across many clips, personalisation

---

### `gemini_generate_speech`

Cloud TTS via the [Google Gemini TTS API](https://ai.google.dev/gemini-api/docs/speech-generation).
Requires `GOOGLE_API_KEY`. No GPU needed.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize. Supports tags: `[whispers]` `[laughs]` `[sighs]` `[gasp]` `[cough]`. |
| `voice` | | Prebuilt voice (default: `Kore`). 30 options — see below. |
| `style` | | Style instruction prepended to text, e.g. `"Read like a warm audiobook narrator."` |
| `speakers` | | Multi-speaker: `[{"speaker": "Joe", "voice": "Charon"}, ...]`. Max 2. |
| `model` | | `gemini-3.1-flash-tts-preview` (default) · `gemini-2.5-flash-preview-tts` · `gemini-2.5-pro-preview-tts` |
| `output_path` | | Save path. Auto-named if omitted. |

**30 prebuilt voices:**
Zephyr (Bright) · Puck (Upbeat) · Charon (Informative) · Kore (Firm) · Fenrir (Excitable) ·
Leda (Youthful) · Orus (Firm) · Aoede (Breezy) · Callirrhoe (Easy-going) · Autonoe (Bright) ·
Enceladus (Breathy) · Iapetus (Clear) · Umbriel (Easy-going) · Algieba (Smooth) · Despina (Smooth) ·
Erinome (Clear) · Algenib (Gravelly) · Rasalgethi (Informative) · Laomedeia (Upbeat) · Achernar (Soft) ·
Alnilam (Firm) · Schedar (Even) · Gacrux (Mature) · Pulcherrima (Forward) · Achird (Friendly) ·
Zubenelgenubi (Casual) · Vindemiatrix (Gentle) · Sadachbia (Lively) · Sadaltager (Knowledgeable) · Sulafat (Warm)

**Best for:** Quick generation, structured voice selection, multi-language content, no-GPU setups

---

## Platform Requirements

### Local models (Dia, Qwen3-TTS)

| Platform | Acceleration | PyTorch |
|----------|-------------|---------|
| macOS Apple Silicon | MPS (Metal) | `pip install torch torchaudio` |
| macOS Intel | CPU | `pip install torch torchaudio` |
| Linux x86_64 + NVIDIA | CUDA | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124` |
| Linux / Windows CPU | CPU | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu` |

First run for each model downloads weights from HuggingFace (~3 GB per model).

### Gemini TTS

```bash
export GOOGLE_API_KEY=your_key_here  # free at aistudio.google.com
```

---

## OmniVoice Studio (Web UI)

A local web UI for auditioning OmniVoice (legacy) voices interactively.

```bash
pip install -r requirements.txt
./run.sh  # → http://localhost:8000
```

---

## Repository Layout

```
omnivoice/
├── bundle.md                        # Amplifier bundle (includes all 3 behaviors)
├── behaviors/
│   ├── dia.yaml                     # Mounts tool-dia
│   ├── qwen3-tts.yaml               # Mounts tool-qwen3-tts
│   └── gemini-tts.yaml              # Mounts tool-gemini-tts
├── context/
│   ├── dia.md                       # Dia tool docs (injected into sessions)
│   ├── qwen3-tts.md                 # Qwen3-TTS tool docs
│   └── gemini-tts.md                # Gemini TTS tool docs
├── modules/
│   ├── tool-dia/                    # pip package: amplifier-module-tool-dia
│   ├── tool-qwen3-tts/              # pip package: amplifier-module-tool-qwen3-tts
│   └── tool-gemini-tts/             # pip package: amplifier-module-tool-gemini-tts
├── main.py                          # FastAPI web UI (legacy)
├── static/index.html                # Web UI SPA
├── scripts/                         # Audiobook production scripts
├── content/                         # Story source and production script
├── research/arena/                  # TTS model evaluation
└── voices/seeds/                    # Character reference audio files
```
