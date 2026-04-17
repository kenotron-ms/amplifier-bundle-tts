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

## Advanced Prompting — Build a Full Scene

For maximum expressiveness, go beyond a simple style hint and give the model a full performance brief.
Think of it as a director's packet for a voice actor. The model reads the whole thing and uses it
to make subtle, coherent choices about delivery — even in parts you haven't tagged explicitly.

### The Five Elements

| Element | What it does |
|---------|-------------|
| **Audio Profile** | Names the character and anchors their identity |
| **Scene** | Sets the physical and emotional environment |
| **Director's Notes** | Gives specific style, pacing, and accent guidance |
| **Sample Context** | Tells the model *why* the character is speaking (backstory, stakes) |
| **Transcript** | The actual words, with optional inline `[tags]` |

You don't need all five every time — Director's Notes alone goes a long way.
But the more coherent the brief, the more natural and consistent the result.

### Template

```
# AUDIO PROFILE: [Character name]
## "[Character tagline or role]"

## THE SCENE: [Location name]
[2–4 sentences. Describe the physical space, the time of day, the mood.
What is happening around the character? How does the environment affect them?]

### DIRECTOR'S NOTES
Style: [Tone and emotional vibe — be specific. "Infectious enthusiasm" beats "energetic".]
Pacing: [Fast/slow/variable — describe rhythm, not just speed.]
Accent: [Be precise. "South London, Brixton" beats "British".]

### SAMPLE CONTEXT
[1–3 sentences. Why is the character speaking right now? What are the stakes?
What do they want the listener to feel?]

#### TRANSCRIPT
[The words. Use inline tags like [whispers] or [shouting] for specific moments.]
```

### Worked Example

```
# AUDIO PROFILE: Dr. Mira S.
## "The Late-Night Lab"

## THE SCENE: Basement Research Lab, 2:47 AM
Flickering fluorescent lights hum over a cluttered bench. Coffee cups ring-stain
a stack of printed papers. Dr. Mira has been awake for nineteen hours and just
watched the assay results come back — positive, against all probability.
The lab is empty. She is talking to a recorder, not a person.

### DIRECTOR'S NOTES
Style: Measured disbelief tipping into quiet elation. She is too tired and too
careful to celebrate out loud, but the wonder keeps breaking through.
Pacing: Slow and deliberate at first, then picking up speed mid-paragraph as
the implications land. Brief pauses after key words.
Accent: Standard American academic — no strong regional markers.

### SAMPLE CONTEXT
This is a personal log entry. Dr. Mira is recording her thoughts before she
lets herself believe what she is seeing. She does not want to jinx it.

#### TRANSCRIPT
[sighs] Okay. So. [pause] The results are in and I'm... I don't want to say it yet.
[whispers] It worked. [normal voice] Three years of dead ends and it actually —
[laughs softly] I should call someone. I'm not going to call anyone. Not until
I run it twice more. But [excited] oh, this is something.
```

When you pass a scene like this to `gemini_generate_speech`, put the entire block in `text`
and leave `style` empty — the model reads the full brief:

```python
gemini_generate_speech(
    text=SCENE_PROMPT,   # the full multi-section block above
    voice="Achernar",    # Soft — matches the exhausted-but-elated register
    model="gemini-2.5-pro-preview-tts",  # use Pro for complex scene work
    output_path="mira_log.wav",
)
```

> **Tip:** Match your voice choice to the scene. A Breathy or Soft voice fits
> intimacy and exhaustion; an Upbeat or Bright voice fits energy and excitement.
> The voice and the brief reinforce each other.

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
