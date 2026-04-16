# Qwen3-TTS — Creative TTS with Voice Design & Cloning

**Use this for:** audiobooks, character narration, bespoke voice personas, and any creative work
where you need precise control — either by describing the exact voice you want, or cloning one
from a reference clip.

Two tools backed by two model variants from Alibaba's Qwen3-TTS family.
Both run locally — no API key, no server.

| Tool | Model | When to use |
|------|-------|-------------|
| `qwen3_design_speech` | Qwen3-TTS-12Hz-1.7B-VoiceDesign | You want to describe a voice in words |
| `qwen3_clone_speech` | Qwen3-TTS-12Hz-1.7B-Base | You have a reference audio file to clone |

Models download from HuggingFace on first use (~3 GB each).

---

## `qwen3_design_speech` — Voice Design

Generate speech by describing the voice you want.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize. |
| `instruct` | ✓ | Natural-language voice description. |
| `language` | | Language name (default: `English`). |
| `output_path` | | Save path. Auto-named in CWD if omitted. |

### `instruct` design guide

Combine any of these attributes, separated by commas:

| Dimension | Options |
|-----------|---------|
| Gender | `male`, `female` |
| Age | `child`, `teenager`, `young adult`, `middle-aged`, `elderly` |
| Pitch | `very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch` |
| Accent | `american`, `british`, `australian`, `canadian`, `indian`, `chinese`, `korean`, `japanese` |
| Style | `whisper`, `gravelly`, `warm`, `energetic`, `breathy`, `professional`, `intimate` |

Free-form descriptions work too — the model understands natural prose:

```python
qwen3_design_speech(
    text="The city never really sleeps. It just changes its face.",
    instruct="Male, 50s, deep gravelly warmth, American, experienced audiobook narrator — "
             "unhurried and knowing, measured pace, the kind of voice you trust implicitly."
)
```

---

## `qwen3_clone_speech` — Voice Cloning

Clone a voice from a reference audio file.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize in the cloned voice. |
| `ref_audio_path` | ✓ | Path to a WAV file of the voice to clone (5-15s). |
| `ref_text` | ✓ | Exact transcript of what is spoken in the reference audio. |
| `language` | | Language name (default: `English`). |
| `output_path` | | Save path. Auto-named in CWD if omitted. |

### Tips for best clone quality

- Reference audio should be **5-15 seconds** of clean, clear speech
- `ref_text` must match the audio **exactly** — typos reduce quality
- The reference audio establishes voice identity; the model generates new content in that voice
- Multiple calls with the same `ref_audio_path` + `ref_text` produce consistent voice identity

```python
qwen3_clone_speech(
    text="Welcome to the show. Tonight we have a very special guest.",
    ref_audio_path="/path/to/narrator.wav",
    ref_text="The city was quiet at night, or it should have been.",
)
```

---

## Notes

- Both tools use a **single-threaded executor** to ensure MPS thread-local safety on Apple Silicon
- The VoiceDesign and Base models are loaded **lazily** — only when first called
- Both models run on **MPS (Apple Silicon)**, **CUDA**, or **CPU**
- Smart quotes and em-dashes are automatically normalized before synthesis
