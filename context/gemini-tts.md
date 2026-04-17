     1	# Gemini TTS — All-Purpose Cloud TTS
     2	
     3	**Use this for:** presentations, reading text aloud, demos, narration, notifications, and
     4	any general content where you want high-quality speech fast — without a local model or GPU.
     5	30 curated prebuilt voices cover every tone from bright and upbeat to gravelly and warm.
     6	
     7	`gemini_generate_speech` generates speech via the **Google Gemini TTS cloud API**.
     8	Fast, no GPU required. Requires `GOOGLE_API_KEY` environment variable.
     9	
    10	## Tool: `gemini_generate_speech`
    11	
    12	| Parameter | Required | Description |
    13	|-----------|----------|-------------|
    14	| `text` | ✓ | Text to synthesize. Embed style inline or use the `style` parameter. |
    15	| `voice` | | Prebuilt voice name (default: `Kore`). See voice table below. |
    16	| `style` | | Style instruction prepended to the text. Not used in multi-speaker mode. |
    17	| `speakers` | | Multi-speaker list (max 2). See multi-speaker usage below. |
    18	| `model` | | TTS model (default: `gemini-3.1-flash-tts-preview`). See models below. |
    19	| `output_path` | | Save path. Auto-named in CWD if omitted. |
    20	
    21	Returns the absolute path to the saved WAV file (24000 Hz, 16-bit mono).
    22	
    23	## Style Guidance
    24	
    25	Style can be embedded directly in the text, or passed as the `style` parameter:
    26	
    27	```python
    28	# Inline
    29	gemini_generate_speech(text="Say cheerfully: Have a wonderful day!")
    30	
    31	# Via style parameter
    32	gemini_generate_speech(
    33	    text="We need to talk about the deployment.",
    34	    style="Style: Frustrated and exhausted engineer at 2am."
    35	)
    36	```
    37	
    38	Inline tags are also supported: `[whispers]`, `[laughs]`, `[sighs]`, `[gasp]`, `[cough]`,
    39	`[excited]`, `[shouting]`, `[tired]`, `[crying]`, `[amazed]`, `[curious]`, `[giggles]`,
    40	`[mischievously]`, `[panicked]`, `[sarcastic]`, `[serious]`, `[trembling]`.
    41	Tags are not exhaustive — experiment freely with any emotion or expression.
    42	
    43	## Advanced Prompting — Build a Full Scene
    44	
    45	For maximum expressiveness, go beyond a simple style hint and give the model a full performance brief.
    46	Think of it as a director's packet for a voice actor. The model reads the whole thing and uses it
    47	to make subtle, coherent choices about delivery — even in parts you haven't tagged explicitly.
    48	
    49	### The Five Elements
    50	
    51	| Element | What it does |
    52	|---------|-------------|
    53	| **Audio Profile** | Names the character and anchors their identity |
    54	| **Scene** | Sets the physical and emotional environment |
    55	| **Director's Notes** | Gives specific style, pacing, and accent guidance |
    56	| **Sample Context** | Tells the model *why* the character is speaking (backstory, stakes) |
    57	| **Transcript** | The actual words, with optional inline `[tags]` |
    58	
    59	You don't need all five every time — Director's Notes alone goes a long way.
    60	But the more coherent the brief, the more natural and consistent the result.
    61	
    62	### Template
    63	
    64	```
    65	# AUDIO PROFILE: [Character name]
    66	## "[Character tagline or role]"
    67	
    68	## THE SCENE: [Location name]
    69	[2–4 sentences. Describe the physical space, the time of day, the mood.
    70	What is happening around the character? How does the environment affect them?]
    71	
    72	### DIRECTOR'S NOTES
    73	Style: [Tone and emotional vibe — be specific. "Infectious enthusiasm" beats "energetic".]
    74	Pacing: [Fast/slow/variable — describe rhythm, not just speed.]
    75	Accent: [Be precise. "South London, Brixton" beats "British".]
    76	
    77	### SAMPLE CONTEXT
    78	[1–3 sentences. Why is the character speaking right now? What are the stakes?
    79	What do they want the listener to feel?]
    80	
    81	#### TRANSCRIPT
    82	[The words. Use inline tags like [whispers] or [shouting] for specific moments.]
    83	```
    84	
    85	### Worked Example
    86	
    87	```
    88	# AUDIO PROFILE: Dr. Mira S.
    89	## "The Late-Night Lab"
    90	
    91	## THE SCENE: Basement Research Lab, 2:47 AM
    92	Flickering fluorescent lights hum over a cluttered bench. Coffee cups ring-stain
    93	a stack of printed papers. Dr. Mira has been awake for nineteen hours and just
    94	watched the assay results come back — positive, against all probability.
    95	The lab is empty. She is talking to a recorder, not a person.
    96	
    97	### DIRECTOR'S NOTES
    98	Style: Measured disbelief tipping into quiet elation. She is too tired and too
    99	careful to celebrate out loud, but the wonder keeps breaking through.
   100	Pacing: Slow and deliberate at first, then picking up speed mid-paragraph as
   101	the implications land. Brief pauses after key words.
   102	Accent: Standard American academic — no strong regional markers.
   103	
   104	### SAMPLE CONTEXT
   105	This is a personal log entry. Dr. Mira is recording her thoughts before she
   106	lets herself believe what she is seeing. She does not want to jinx it.
   107	
   108	#### TRANSCRIPT
   109	[sighs] Okay. So. [pause] The results are in and I'm... I don't want to say it yet.
   110	[whispers] It worked. [normal voice] Three years of dead ends and it actually —
   111	[laughs softly] I should call someone. I'm not going to call anyone. Not until
   112	I run it twice more. But [excited] oh, this is something.
   113	```
   114	
   115	When you pass a scene like this to `gemini_generate_speech`, put the entire block in `text`
   116	and leave `style` empty — the model reads the full brief:
   117	
   118	```python
   119	gemini_generate_speech(
   120	    text=SCENE_PROMPT,   # the full multi-section block above
   121	    voice="Achernar",    # Soft — matches the exhausted-but-elated register
   122	    model="gemini-3.1-flash-tts-preview",
   123	    output_path="mira_log.wav",
   124	)
   125	```
   126	
   127	> **Tip:** Match your voice choice to the scene. A Breathy or Soft voice fits
   128	> intimacy and exhaustion; an Upbeat or Bright voice fits energy and excitement.
   129	> The voice and the brief reinforce each other.
   130	
   131	## Prebuilt Voices (30)
   132	
   133	| Voice | Style | Voice | Style | Voice | Style |
   134	|-------|-------|-------|-------|-------|-------|
   135	| Zephyr | Bright | Puck | Upbeat | Charon | Informative |
   136	| Kore | Firm | Fenrir | Excitable | Leda | Youthful |
   137	| Orus | Firm | Aoede | Breezy | Callirrhoe | Easy-going |
   138	| Autonoe | Bright | Enceladus | Breathy | Iapetus | Clear |
   139	| Umbriel | Easy-going | Algieba | Smooth | Despina | Smooth |
   140	| Erinome | Clear | Algenib | Gravelly | Rasalgethi | Informative |
   141	| Laomedeia | Upbeat | Achernar | Soft | Alnilam | Firm |
   142	| Schedar | Even | Gacrux | Mature | Pulcherrima | Forward |
   143	| Achird | Friendly | Zubenelgenubi | Casual | Vindemiatrix | Gentle |
   144	| Sadachbia | Lively | Sadaltager | Knowledgeable | Sulafat | Warm |
   145	
   146	## Multi-Speaker Mode
   147	
   148	Up to 2 speakers. The text must reference each speaker by their configured name:
   149	
   150	```python
   151	gemini_generate_speech(
   152	    text="Alice: Did the deploy work?\nBob: First try. [laughs] I know, shocking.",
   153	    speakers=[
   154	        {"speaker": "Alice", "voice": "Aoede"},
   155	        {"speaker": "Bob",   "voice": "Charon"},
   156	    ]
   157	)
   158	```
   159	
   160	## Models
   161	
   162	| Model | Speed | Quality |
   163	|-------|-------|---------|
   164	| `gemini-3.1-flash-tts-preview` | Fastest | Good (default) |
   165	| `gemini-2.5-flash-preview-tts` | Fast | Better |
   166	| `gemini-2.5-pro-preview-tts` | Slower | Best |
   167	
   168	## Notes
   169	
   170	- Requires `GOOGLE_API_KEY` — get one free at [aistudio.google.com](https://aistudio.google.com)
   171	- Auto-detects input language (78 languages supported)
   172	- Output: 24 kHz, 16-bit, mono WAV