     1	# OmniVoice
     2	
     3	Speech generation for [Amplifier](https://github.com/microsoft/amplifier) — three backends,
     4	each optimised for a different job.
     5	
     6	```
     7	Podcast dialogue    →  Dia          (local, two-speaker, naturalistic)
     8	Creative narration  →  Qwen3-TTS   (local, voice design or cloning)
     9	Everything else     →  Gemini TTS  (cloud, 30 voices, instant, no GPU)
    10	```
    11	
    12	---
    13	
    14	## Which backend should I use?
    15	
    16	| I want to… | Use |
    17	|-----------|-----|
    18	| Generate a two-person podcast, interview, or dialogue scene | **Dia** |
    19	| Narrate an audiobook with a specific character voice | **Qwen3-TTS** (clone) |
    20	| Design a voice from scratch — age, accent, tone | **Qwen3-TTS** (design) |
    21	| Read a slide deck or document aloud | **Gemini TTS** |
    22	| Generate speech right now with no model download | **Gemini TTS** |
    23	| Produce multi-language content without extra setup | **Gemini TTS** |
    24	| Need full control over voice identity across many clips | **Qwen3-TTS** (clone) |
    25	
    26	---
    27	
    28	## Setup
    29	
    30	### 1. Point Amplifier at this bundle
    31	
    32	In `.amplifier/settings.yaml`:
    33	
    34	```yaml
    35	bundle:
    36	  active: omnivoice
    37	  sources:
    38	    omnivoice: file:///path/to/omnivoice
    39	```
    40	
    41	### 2. Install the modules you need
    42	
    43	Each backend is its own pip package. Install only what you'll use.
    44	
    45	```bash
    46	# Gemini only — no GPU, works anywhere
    47	uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
    48	  -e ./modules/tool-gemini-tts
    49	
    50	# Local models (Dia + Qwen3-TTS)
    51	uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
    52	  -e ./modules/tool-dia \
    53	  -e ./modules/tool-qwen3-tts
    54	
    55	# All three
    56	uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python \
    57	  -e ./modules/tool-dia \
    58	  -e ./modules/tool-qwen3-tts \
    59	  -e ./modules/tool-gemini-tts
    60	```
    61	
    62	### 3. Gemini API key (if using Gemini)
    63	
    64	Get a free key at [aistudio.google.com](https://aistudio.google.com) and export it:
    65	
    66	```bash
    67	export GOOGLE_API_KEY=your_key_here
    68	```
    69	
    70	### 4. PyTorch (if using Dia or Qwen3-TTS)
    71	
    72	| Platform | Command |
    73	|----------|---------|
    74	| macOS Apple Silicon | `pip install torch torchaudio` |
    75	| Linux + NVIDIA GPU | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124` |
    76	| CPU only | `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu` |
    77	
    78	Model weights download automatically on first use (~3 GB per model).
    79	
    80	---
    81	
    82	## Dia — Podcast & Dialogue
    83	
    84	Two speakers, one pass. Dia generates naturalistic conversation including laughter,
    85	sighs, and other nonverbal sounds. The voices vary per run unless you fix a seed.
    86	
    87	**Best for:** podcast episodes, interviews, two-character scenes, explainer dialogue.
    88	
    89	```python
    90	dia_generate_speech(
    91	    script="""
    92	    [S1] So we shipped the new inference pipeline on Friday.
    93	    [S2] Friday afternoon deploy. Bold move. (laughs)
    94	    [S1] I know, I know. But it actually worked first try.
    95	    [S2] No way. What was different this time?
    96	    [S1] Honestly? We just wrote better tests.
    97	    """
    98	)
    99	```
   100	
   101	Scripts always start with `[S1]` and alternate — never repeat the same speaker tag.
   102	Target 5–20 seconds of audio per generation; very short inputs sound unnatural,
   103	very long ones rush the delivery.
   104	
   105	### Voice conditioning
   106	
   107	Pass a 5–10s audio clip to nudge the voice style:
   108	
   109	```python
   110	dia_generate_speech(
   111	    script="[S1] Welcome back to the show. [S2] Great to be here.",
   112	    audio_prompt_path="reference.wav",
   113	    audio_prompt_transcript="[S1] This is the reference clip transcript."
   114	)
   115	```
   116	
   117	### Nonverbal sounds
   118	
   119	Insert anywhere in the script:
   120	`(laughs)` `(sighs)` `(coughs)` `(gasps)` `(clears throat)` `(chuckle)` `(mumbles)`
   121	`(groans)` `(whistles)` `(humming)` `(sneezes)` `(applause)` `(inhales)` `(exhales)`
   122	
   123	### Parameters
   124	
   125	| Parameter | Default | Description |
   126	|-----------|---------|-------------|
   127	| `script` | required | Dialogue text with `[S1]`/`[S2]` tags |
   128	| `audio_prompt_path` | — | WAV/MP3 for voice conditioning (5–10s) |
   129	| `audio_prompt_transcript` | — | Transcript of prompt audio (required with above) |
   130	| `output_path` | auto-named | Where to save the WAV |
   131	| `seed` | random | Fix for reproducible voices |
   132	| `cfg_scale` | `3.0` | Higher = more faithful to script |
   133	| `temperature` | `1.8` | Sampling temperature |
   134	
   135	---
   136	
   137	## Qwen3-TTS — Creative Voice Design & Cloning
   138	
   139	Two tools, two models. Design voices from a text description, or clone a voice
   140	from a short reference clip. Full control over who speaks.
   141	
   142	**Best for:** audiobooks, character narration, bespoke voice personas, any project
   143	where voice consistency or a specific sound identity matters.
   144	
   145	### Voice design — describe the voice you want
   146	
   147	```python
   148	qwen3_design_speech(
   149	    text="The city never really sleeps. It just changes its face.",
   150	    instruct="Male, 50s, deep gravelly warmth, American, experienced audiobook "
   151	             "narrator — unhurried and knowing, the kind of voice you trust."
   152	)
   153	```
   154	
   155	```python
   156	qwen3_design_speech(
   157	    text="Warning: this action cannot be undone.",
   158	    instruct="Female, young adult, clear and neutral, British accent, slight urgency."
   159	)
   160	```
   161	
   162	**`instruct` vocabulary** — mix and match freely:
   163	
   164	| Dimension | Options |
   165	|-----------|---------|
   166	| Gender | `male`, `female` |
   167	| Age | `child`, `teenager`, `young adult`, `middle-aged`, `elderly` |
   168	| Pitch | `very low`, `low`, `moderate`, `high`, `very high pitch` |
   169	| Accent | `american`, `british`, `australian`, `canadian`, `indian`, `chinese`, `korean`, `japanese` |
   170	| Style | `whisper`, `gravelly`, `warm`, `breathy`, `energetic`, + free-form prose |
   171	
   172	### Voice cloning — match an existing voice
   173	
   174	```python
   175	qwen3_clone_speech(
   176	    text="Chapter three. The rain had not stopped in three days.",
   177	    ref_audio_path="narrator.wav",           # 5–15s of clean speech
   178	    ref_text="The city was quiet at night."  # exact transcript of the clip
   179	)
   180	```
   181	
   182	The same `ref_audio_path` + `ref_text` pair produces a consistent voice identity
   183	across every call — useful for generating entire audiobooks character-by-character.
   184	
   185	### Parameters
   186	
   187	**`qwen3_design_speech`**
   188	
   189	| Parameter | Default | Description |
   190	|-----------|---------|-------------|
   191	| `text` | required | Text to synthesize |
   192	| `instruct` | required | Natural-language voice description |
   193	| `language` | `English` | Language name |
   194	| `output_path` | auto-named | Where to save the WAV |
   195	
   196	**`qwen3_clone_speech`**
   197	
   198	| Parameter | Default | Description |
   199	|-----------|---------|-------------|
   200	| `text` | required | Text to synthesize |
   201	| `ref_audio_path` | required | Reference WAV (5–15s) |
   202	| `ref_text` | required | Exact transcript of the reference clip |
   203	| `language` | `English` | Language name |
   204	| `output_path` | auto-named | Where to save the WAV |
   205	
   206	---
   207	
   208	## Gemini TTS — All-Purpose Cloud Speech
   209	
   210	30 curated prebuilt voices ranging from gravelly and warm to bright and upbeat.
   211	No local model, no GPU, no setup beyond an API key. Works in any language Gemini supports.
   212	
   213	**Best for:** presentations, reading documents or slides aloud, demos, notifications,
   214	quick prototypes, any content where fast and flexible matters more than custom voice control.
   215	
   216	```python
   217	# Reading a slide
   218	gemini_generate_speech(
   219	    text="Q3 revenue grew 18% year over year, driven by expansion in APAC markets.",
   220	    voice="Charon",     # Informative
   221	    style="Read like a confident presenter, measured and clear."
   222	)
   223	```
   224	
   225	```python
   226	# Two-person exchange
   227	gemini_generate_speech(
   228	    text="Host: What made you decide to start the company?\n"
   229	         "Guest: Honestly, I got tired of waiting for someone else to build it.",
   230	    speakers=[
   231	        {"speaker": "Host",  "voice": "Aoede"},    # Breezy
   232	        {"speaker": "Guest", "voice": "Fenrir"},   # Excitable
   233	    ]
   234	)
   235	```
   236	
   237	```python
   238	# Inline style control
   239	gemini_generate_speech(
   240	    text="[whispers] The results are in. [laughs] We actually did it.",
   241	    voice="Sulafat"     # Warm
   242	)
   243	```
   244	
   245	### Voice reference
   246	
   247	| Voice | Character | Voice | Character | Voice | Character |
   248	|-------|-----------|-------|-----------|-------|-----------|
   249	| Zephyr | Bright | Puck | Upbeat | Charon | Informative |
   250	| **Kore** | **Firm** *(default)* | Fenrir | Excitable | Leda | Youthful |
   251	| Orus | Firm | Aoede | Breezy | Callirrhoe | Easy-going |
   252	| Autonoe | Bright | Enceladus | Breathy | Iapetus | Clear |
   253	| Umbriel | Easy-going | Algieba | Smooth | Despina | Smooth |
   254	| Erinome | Clear | Algenib | Gravelly | Rasalgethi | Informative |
   255	| Laomedeia | Upbeat | Achernar | Soft | Alnilam | Firm |
   256	| Schedar | Even | Gacrux | Mature | Pulcherrima | Forward |
   257	| Achird | Friendly | Zubenelgenubi | Casual | Vindemiatrix | Gentle |
   258	| Sadachbia | Lively | Sadaltager | Knowledgeable | Sulafat | Warm |
   259	
   260	### Models
   261	
   262	| Model | Speed | Notes |
   263	|-------|-------|-------|
   264	| `gemini-3.1-flash-tts-preview` | Fastest | Default |
   265	| `gemini-2.5-flash-preview-tts` | Fast | — |
   266	| `gemini-2.5-pro-preview-tts` | Slower | Highest quality |
   267	
   268	### Parameters
   269	
   270	| Parameter | Default | Description |
   271	|-----------|---------|-------------|
   272	| `text` | required | Text to synthesize. Supports `[whispers]` `[laughs]` `[sighs]` `[gasp]` `[cough]` |
   273	| `voice` | `Kore` | Prebuilt voice name |
   274	| `style` | — | Style instruction prepended to the text |
   275	| `speakers` | — | Multi-speaker list: `[{"speaker": "Name", "voice": "Voice"}, ...]` (max 2) |
   276	| `model` | `gemini-3.1-flash-tts-preview` | TTS model |
   277	| `output_path` | auto-named | Where to save the WAV |
   278	
   279	---
   280	
   281	## Repository layout
   282	
   283	```
   284	omnivoice/
   285	├── bundle.md                    # Amplifier bundle — includes all three behaviors
   286	├── behaviors/
   287	│   ├── dia.yaml                 # Mounts tool-dia, includes context
   288	│   ├── qwen3-tts.yaml           # Mounts tool-qwen3-tts, includes context
   289	│   └── gemini-tts.yaml          # Mounts tool-gemini-tts, includes context
   290	├── context/
   291	│   ├── dia.md                   # Dia reference (injected into agent sessions)
   292	│   ├── qwen3-tts.md             # Qwen3-TTS reference
   293	│   └── gemini-tts.md            # Gemini TTS reference
   294	├── modules/
   295	│   ├── tool-dia/                # pip: amplifier-module-tool-dia
   296	│   ├── tool-qwen3-tts/          # pip: amplifier-module-tool-qwen3-tts
   297	│   └── tool-gemini-tts/         # pip: amplifier-module-tool-gemini-tts
   298	├── scripts/                     # Audiobook production scripts
   299	├── content/                     # Story source and production script
   300	├── voices/seeds/                # Character reference audio files
   301	└── docs/                        # Project notes
   302	```