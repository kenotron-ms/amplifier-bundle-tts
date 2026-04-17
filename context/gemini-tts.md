# Gemini TTS — All-Purpose Cloud TTS

**Use this for:** presentations, reading text aloud, demos, narration, notifications, and
any general content where you want high-quality speech fast — without a local model or GPU.
30 curated prebuilt voices cover every tone from bright and upbeat to gravelly and warm.

`gemini_generate_speech` generates speech via the **Google Gemini TTS cloud API**.
Fast, no GPU required. Requires `GOOGLE_API_KEY` environment variable.

## Tool: `gemini_generate_speech`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `text` | ✓ | Text to synthesize. Embed style inline or use the `style` parameter. |
| `voice` | | Prebuilt voice name (default: `Kore`). See voice table below. |
| `style` | | Style instruction prepended to the text. Not used in multi-speaker mode. |
| `speakers` | | Multi-speaker list (max 2). See multi-speaker usage below. |
| `model` | | TTS model (default: `gemini-3.1-flash-tts-preview`). See models below. |
| `output_path` | | Save path. Auto-named in CWD if omitted. |

Returns the absolute path to the saved WAV file (24000 Hz, 16-bit mono).

## Style Guidance

Style can be embedded directly in the text, or passed as the `style` parameter:

```python
# Inline
gemini_generate_speech(text="Say cheerfully: Have a wonderful day!")

# Via style parameter
gemini_generate_speech(
    text="We need to talk about the deployment.",
    style="Style: Frustrated and exhausted engineer at 2am."
)
```

Inline tags are also supported: `[whispers]`, `[laughs]`, `[sighs]`, `[gasp]`, `[cough]`,
`[excited]`, `[shouting]`, `[tired]`, `[crying]`, `[amazed]`, `[curious]`, `[giggles]`,
`[mischievously]`, `[panicked]`, `[sarcastic]`, `[serious]`, `[trembling]`.
Tags are not exhaustive — experiment freely with any emotion or expression.

## Prebuilt Voices (30)

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

## Multi-Speaker Mode

Up to 2 speakers. The text must reference each speaker by their configured name:

```python
gemini_generate_speech(
    text="Alice: Did the deploy work?\nBob: First try. [laughs] I know, shocking.",
    speakers=[
        {"speaker": "Alice", "voice": "Aoede"},
        {"speaker": "Bob",   "voice": "Charon"},
    ]
)
```

## Models

| Model | Speed | Quality |
|-------|-------|---------|
| `gemini-3.1-flash-tts-preview` | Fastest | Good (default) |
| `gemini-2.5-flash-preview-tts` | Fast | Better |
| `gemini-2.5-pro-preview-tts` | Slower | Best |

## Notes

- Requires `GOOGLE_API_KEY` — get one free at [aistudio.google.com](https://aistudio.google.com)
- Auto-detects input language (78 languages supported)
- Output: 24 kHz, 16-bit, mono WAV
