# OmniVoice TTS

    You have four tools for generating speech audio directly. Local OmniVoice runs on-device from the HuggingFace cache (no server needed). Gemini TTS uses the Google AI cloud API for fast, high-quality speech with 30 prebuilt voices.

    ## `generate_speech` — Local OmniVoice

    Generates a WAV file from text using the local k2-fsa/OmniVoice model. Returns the absolute path to the saved file.

    **Parameters:**

    | Parameter | Required | Description |
    |-----------|----------|-------------|
    | `text` | ✓ | Text to synthesize. Expressive tags supported inline (see below). |
    | `voice_id` | | ID from `list_voices` — uses a saved named voice. |
    | `instruct` | | Describe the voice on the fly: `"female, british accent, high pitch"`. |
    | `ref_audio_path` | | Path to 3–10 s audio file to clone that speaker's voice. |
    | `ref_text` | | Transcript of the reference audio (optional; auto-transcribed if absent). |
    | `output_path` | | Where to save the WAV. Auto-named in the current directory if omitted. |
    | `num_step` | | Diffusion steps. Default 32. Use 16 for fast previews. |
    | `speed` | | Speed multiplier. 1.0 = normal, 0.8 = slower, 1.3 = faster. |

    **Voice priority:** `voice_id` → `ref_audio_path` → `instruct` → auto (random).

    ### Expressive tags (insert anywhere in text)

    | Tag | Sound |
    |-----|-------|
    | `[laughter]` | Laughter |
    | `[sigh]` | Sigh |
    | `[confirmation-en]` | Confirmation (uh-huh) |
    | `[question-en]` | Question intonation |
    | `[question-ah]` `[question-oh]` | Question variants |
    | `[surprise-ah]` `[surprise-oh]` `[surprise-wa]` `[surprise-yo]` | Surprise |
    | `[dissatisfaction-hnn]` | Dissatisfied grunt |

    **Example:**
    ```
    [laughter] Alright, so this week we shipped something wild. [surprise-oh]
    It actually worked on the first try.
    ```

    ### Voice design `instruct` attributes

    Comma-separate any of:
    - **Gender:** `male`, `female`
    - **Age:** `child`, `teenager`, `young adult`, `middle-aged`, `elderly`
    - **Pitch:** `very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch`
    - **Style:** `whisper`
    - **Accent:** `american`, `british`, `australian`, `canadian`, `indian`, `chinese`, `korean`, `japanese`

    ---

    ## `gemini_generate_speech` — Google Gemini TTS

    Generates a WAV file via the Gemini TTS cloud API. Fast, no GPU required. Requires `GOOGLE_API_KEY`.

    **Parameters:**

    | Parameter | Required | Description |
    |-----------|----------|-------------|
    | `text` | ✓ | Text to synthesize. Style can be embedded inline, e.g. `"Say cheerfully: Have a wonderful day!"`. Supports tags like `[whispers]`, `[laughs]`, `[sighs]`, `[gasp]`, `[cough]`. |
    | `voice` | | Prebuilt voice name (default: `Kore`). See voice list below. |
    | `style` | | Style instruction prepended to the text, e.g. `"Read like a warm audiobook narrator."` Not used in multi-speaker mode. |
    | `speakers` | | Multi-speaker mode (max 2): list of `{"speaker": "Name", "voice": "VoiceName"}`. The text must reference each speaker by name. |
    | `model` | | TTS model: `gemini-3.1-flash-tts-preview` (default), `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`. |
    | `output_path` | | Where to save the WAV. Auto-named in the current directory if omitted. |

    ### Prebuilt voices (30 options)

    | Voice | Style | Voice | Style |
    |-------|-------|-------|-------|
    | Zephyr | Bright | Puck | Upbeat |
    | Charon | Informative | Kore | Firm |
    | Fenrir | Excitable | Leda | Youthful |
    | Orus | Firm | Aoede | Breezy |
    | Callirrhoe | Easy-going | Autonoe | Bright |
    | Enceladus | Breathy | Iapetus | Clear |
    | Umbriel | Easy-going | Algieba | Smooth |
    | Despina | Smooth | Erinome | Clear |
    | Algenib | Gravelly | Rasalgethi | Informative |
    | Laomedeia | Upbeat | Achernar | Soft |
    | Alnilam | Firm | Schedar | Even |
    | Gacrux | Mature | Pulcherrima | Forward |
    | Achird | Friendly | Zubenelgenubi | Casual |
    | Vindemiatrix | Gentle | Sadachbia | Lively |
    | Sadaltager | Knowledgeable | Sulafat | Warm |

    ### Multi-speaker example

    ```python
    gemini_generate_speech(
        text="Joe: How's it going today?\nJane: Not too bad, how about you?",
        speakers=[
            {"speaker": "Joe", "voice": "Charon"},
            {"speaker": "Jane", "voice": "Aoede"}
        ]
    )
    ```

    ---

    ## `save_voice` — Save a named OmniVoice voice

    Save a named voice to `~/.amplifier/omnivoice/voices.json` for reuse with `generate_speech`.

    | Parameter | Required | Description |
    |-----------|----------|-------------|
    | `name` | ✓ | Friendly name, e.g. `"Demo Host"`. |
    | `instruct` | | Voice design string. |
    | `ref_audio_path` | | Path to reference audio for cloning. |
    | `ref_text` | | Transcript of the reference audio (optional). |

    Returns the `voice_id` to use in future `generate_speech` calls.

    ---

    ## `list_voices` — List saved OmniVoice voices

    Lists all saved voices with their IDs. Call this when the user refers to a voice by name.

    ---

    ## Notes

    - **OmniVoice** loads from `~/.cache/huggingface/hub/` on first use — no internet needed after that.
    - **Gemini TTS** requires `GOOGLE_API_KEY` and an internet connection. No local GPU needed.
    - OmniVoice voice library persists at `~/.amplifier/omnivoice/voices.json`.
    - The web UI (`./run.sh` in the omnivoice project) is still available for browsing and auditioning OmniVoice voices visually.
    