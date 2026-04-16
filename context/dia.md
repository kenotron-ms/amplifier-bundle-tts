# Dia TTS — Multi-Speaker Podcast & Dialogue

**Use this for:** podcast episodes, interviews, two-character scenes, explainer dialogue —
any content that needs two naturalistic voices talking to each other.

`dia_generate_speech` generates two-speaker audio in a single pass using **nari-labs/Dia-1.6B-0626**.
Local inference — no API key, no server. Downloads ~3 GB from HuggingFace on first use.

## Tool: `dia_generate_speech`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `script` | ✓ | Dialogue with `[S1]`/`[S2]` speaker tags. See format rules below. |
| `audio_prompt_path` | | WAV/MP3 file (5-10s) to condition voice identity. Requires `audio_prompt_transcript`. |
| `audio_prompt_transcript` | | Transcript of the prompt audio (with `[S1]`/`[S2]` tags). |
| `output_path` | | Save path. Auto-named in CWD if omitted. |
| `seed` | | Integer seed for reproducible voices. |
| `cfg_scale` | | Guidance scale (default 3.0). Higher = more faithful to script. |
| `temperature` | | Sampling temperature (default 1.8). |

Returns the absolute path to the saved WAV file (44100 Hz).

## Script Format

- **Always start with `[S1]`**
- **Alternate** between `[S1]` and `[S2]` — never repeat the same tag twice in a row
- Keep total script to **5-20 seconds** of audio for best quality
- Short inputs (<5s) sound unnatural; very long inputs (>20s) rush the speech

```
[S1] So the deploy went out Friday afternoon. [S2] Classic. (laughs) [S1] Right? And of course that's when everything broke. [S2] What happened? [S1] The migration ran fine in staging but somehow dropped half the prod tables.
```

## Nonverbal Actions

Insert naturally in the flow:

| Action | Tag |
|--------|-----|
| Laughing | `(laughs)` |
| Clearing throat | `(clears throat)` |
| Sighing | `(sighs)` |
| Gasping | `(gasps)` |
| Coughing | `(coughs)` |
| Chuckling | `(chuckle)` |
| Mumbling | `(mumbles)` |
| Whistling | `(whistles)` |
| Groaning | `(groans)` |
| Humming | `(humming)` |
| Inhaling/exhaling | `(inhales)` `(exhales)` |
| Sneezing | `(sneezes)` |
| Applause | `(applause)` |

Use sparingly — overuse degrades quality.

## Voice Conditioning (Voice Cloning)

Pass a 5-10s audio file as an audio prompt to condition the voice:

```python
dia_generate_speech(
    script="[S1] This is the cloned voice. [S2] And this is S2.",
    audio_prompt_path="/path/to/reference.wav",
    audio_prompt_transcript="[S1] Original words from the reference file."
)
```

- The prompt transcript must use the same `[S1]`/`[S2]` tags as the reference audio
- The model will attempt to match the voice style, not clone it perfectly
- Providing a seed fixes the non-prompted speaker's voice for consistent multi-call sessions

## Notes

- Dia generates **two distinct voices** even without conditioning — they vary across calls unless you use a seed
- The model runs on **MPS (Apple Silicon)**, **CUDA**, or **CPU**
- First run downloads the Dia model and the Descript Audio Codec (~3 GB total)
