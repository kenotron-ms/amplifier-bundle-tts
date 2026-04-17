     1	"""Amplifier tool module — Gemini TTS (Google AI cloud API).
     2	
     3	Provides gemini_generate_speech with 30 prebuilt voices,
     4	single-speaker and multi-speaker (2-speaker) modes.
     5	Requires GOOGLE_API_KEY environment variable.
     6	"""
     7	
     8	import asyncio
     9	import logging
    10	import os
    11	import uuid
    12	import wave
    13	from pathlib import Path
    14	from typing import Any
    15	
    16	from amplifier_core import ToolResult
    17	
    18	logger = logging.getLogger(__name__)
    19	
    20	# ---------------------------------------------------------------------------
    21	# 30 prebuilt Gemini voices
    22	# ---------------------------------------------------------------------------
    23	GEMINI_VOICES = {
    24	    "Zephyr": "Bright",
    25	    "Puck": "Upbeat",
    26	    "Charon": "Informative",
    27	    "Kore": "Firm",
    28	    "Fenrir": "Excitable",
    29	    "Leda": "Youthful",
    30	    "Orus": "Firm",
    31	    "Aoede": "Breezy",
    32	    "Callirrhoe": "Easy-going",
    33	    "Autonoe": "Bright",
    34	    "Enceladus": "Breathy",
    35	    "Iapetus": "Clear",
    36	    "Umbriel": "Easy-going",
    37	    "Algieba": "Smooth",
    38	    "Despina": "Smooth",
    39	    "Erinome": "Clear",
    40	    "Algenib": "Gravelly",
    41	    "Rasalgethi": "Informative",
    42	    "Laomedeia": "Upbeat",
    43	    "Achernar": "Soft",
    44	    "Alnilam": "Firm",
    45	    "Schedar": "Even",
    46	    "Gacrux": "Mature",
    47	    "Pulcherrima": "Forward",
    48	    "Achird": "Friendly",
    49	    "Zubenelgenubi": "Casual",
    50	    "Vindemiatrix": "Gentle",
    51	    "Sadachbia": "Lively",
    52	    "Sadaltager": "Knowledgeable",
    53	    "Sulafat": "Warm",
    54	}
    55	
    56	_VOICE_LIST = ", ".join(f"{k} ({v})" for k, v in GEMINI_VOICES.items())
    57	
    58	
    59	# ---------------------------------------------------------------------------
    60	# gemini_generate_speech
    61	# ---------------------------------------------------------------------------
    62	
    63	
    64	class GeminiGenerateSpeechTool:
    65	    @property
    66	    def name(self) -> str:
    67	        return "gemini_generate_speech"
    68	
    69	    @property
    70	    def description(self) -> str:
    71	        return (
    72	            "Generate speech via Google Gemini TTS (cloud API, requires GOOGLE_API_KEY). "
    73	            "30 expressive prebuilt voices. Fast, no GPU required. "
    74	            "Supports single-speaker and multi-speaker (up to 2) modes. "
    75	            "Style can be embedded in text or passed via the style parameter. "
    76	            "Inline tags like [whispers], [laughs], [sighs], [gasp], [cough], [excited], "
    77	            "[shouting], [tired], [crying], [amazed], [curious], [giggles], [mischievously], "
    78	            "[panicked], [sarcastic], [serious], [trembling] are supported. "
    79	            "Tags are not exhaustive — experiment freely with any emotion or expression. "
    80	            "Returns absolute path to the saved WAV file."
    81	        )
    82	
    83	    @property
    84	    def input_schema(self) -> dict:
    85	        return {
    86	            "type": "object",
    87	            "properties": {
    88	                "text": {
    89	                    "type": "string",
    90	                    "description": (
    91	                        "Text to synthesize. Embed style inline: 'Say cheerfully: Have a wonderful day!' "
    92	                        "Supports tags: [whispers], [laughs], [sighs], [gasp], [cough], etc."
    93	                    ),
    94	                },
    95	                "voice": {
    96	                    "type": "string",
    97	                    "description": f"Prebuilt voice name. Options: {_VOICE_LIST}. Default: Kore.",
    98	                },
    99	                "style": {
   100	                    "type": "string",
   101	                    "description": (
   102	                        "Optional style instruction prepended to the text. "
   103	                        "E.g. 'Read like a warm audiobook narrator.' Not used in multi-speaker mode."
   104	                    ),
   105	                },
   106	                "speakers": {
   107	                    "type": "array",
   108	                    "description": (
   109	                        "Multi-speaker mode (max 2 speakers). "
   110	                        'Each item: {"speaker": "Name", "voice": "VoiceName"}. '
   111	                        "The text must reference each speaker by name, e.g. "
   112	                        "'Joe: Hello there.\\nJane: Hi, how are you?'"
   113	                    ),
   114	                    "items": {
   115	                        "type": "object",
   116	                        "properties": {
   117	                            "speaker": {"type": "string"},
   118	                            "voice": {"type": "string"},
   119	                        },
   120	                        "required": ["speaker", "voice"],
   121	                    },
   122	                },
   123	                "model": {
   124	                    "type": "string",
   125	                    "description": (
   126	                        "Gemini TTS model. "
   127	                        "gemini-3.1-flash-tts-preview (default, fastest), "
   128	                        "gemini-2.5-flash-preview-tts, "
   129	                        "gemini-2.5-pro-preview-tts (highest quality)."
   130	                    ),
   131	                },
   132	                "output_path": {
   133	                    "type": "string",
   134	                    "description": "Where to save the WAV. Auto-named in CWD if omitted.",
   135	                },
   136	            },
   137	            "required": ["text"],
   138	        }
   139	
   140	    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
   141	        api_key = os.environ.get("GOOGLE_API_KEY")
   142	        if not api_key:
   143	            return ToolResult(
   144	                success=False,
   145	                output="GOOGLE_API_KEY not set. Gemini TTS requires a Google AI API key.",
   146	            )
   147	
   148	        try:
   149	            from google import genai  # type: ignore
   150	            from google.genai import types  # type: ignore
   151	        except ImportError:
   152	            return ToolResult(
   153	                success=False,
   154	                output="google-genai not installed. Run: pip install google-genai",
   155	            )
   156	
   157	        text: str = input_data["text"]
   158	        voice: str = input_data.get("voice", "Kore")
   159	        style: str | None = input_data.get("style")
   160	        speakers: list[dict] | None = input_data.get("speakers")
   161	        model: str = input_data.get("model", "gemini-3.1-flash-tts-preview")
   162	        out_str: str | None = input_data.get("output_path")
   163	        output_path = (
   164	            Path(out_str) if out_str else Path(f"gemini_{uuid.uuid4().hex[:8]}.wav")
   165	        )
   166	
   167	        contents = text
   168	        if style and not speakers:
   169	            contents = f"{style}\n\n{text}"
   170	
   171	        if speakers:
   172	            if len(speakers) > 2:
   173	                return ToolResult(
   174	                    success=False,
   175	                    output="Gemini multi-speaker supports at most 2 speakers.",
   176	                )
   177	            speaker_configs = [
   178	                types.SpeakerVoiceConfig(
   179	                    speaker=s["speaker"],
   180	                    voice_config=types.VoiceConfig(
   181	                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
   182	                            voice_name=s["voice"]
   183	                        )
   184	                    ),
   185	                )
   186	                for s in speakers
   187	            ]
   188	            speech_config = types.SpeechConfig(
   189	                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
   190	                    speaker_voice_configs=speaker_configs
   191	                )
   192	            )
   193	        else:
   194	            speech_config = types.SpeechConfig(
   195	                voice_config=types.VoiceConfig(
   196	                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
   197	                )
   198	            )
   199	
   200	        def _sync() -> bytes:
   201	            client = genai.Client(api_key=api_key)
   202	            response = client.models.generate_content(
   203	                model=model,
   204	                contents=contents,
   205	                config=types.GenerateContentConfig(
   206	                    response_modalities=["AUDIO"],
   207	                    speech_config=speech_config,
   208	                ),
   209	            )
   210	            return response.candidates[0].content.parts[0].inline_data.data
   211	
   212	        # Gemini TTS occasionally returns text tokens instead of audio tokens,
   213	        # causing a 500 error. The docs recommend retry logic for this.
   214	        max_attempts = 3
   215	        loop = asyncio.get_running_loop()
   216	        last_exc: Exception | None = None
   217	        for attempt in range(1, max_attempts + 1):
   218	            try:
   219	                pcm_data = await loop.run_in_executor(None, _sync)
   220	                break
   221	            except Exception as exc:
   222	                last_exc = exc
   223	                if attempt < max_attempts:
   224	                    logger.warning(
   225	                        "Gemini TTS attempt %d/%d failed: %s — retrying",
   226	                        attempt,
   227	                        max_attempts,
   228	                        exc,
   229	                    )
   230	                    await asyncio.sleep(1.0 * attempt)
   231	        else:
   232	            return ToolResult(
   233	                success=False,
   234	                output=f"Gemini TTS failed after {max_attempts} attempts: {last_exc}",
   235	            )
   236	
   237	        # Gemini returns 24 kHz, 16-bit, mono PCM
   238	        output_path.parent.mkdir(parents=True, exist_ok=True)
   239	        with wave.open(str(output_path), "wb") as wf:
   240	            wf.setnchannels(1)
   241	            wf.setsampwidth(2)
   242	            wf.setframerate(24000)
   243	            wf.writeframes(pcm_data)
   244	
   245	        size_kb = output_path.stat().st_size / 1024
   246	        return ToolResult(
   247	            success=True, output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}"
   248	        )
   249	
   250	
   251	# ---------------------------------------------------------------------------
   252	# mount
   253	# ---------------------------------------------------------------------------
   254	
   255	
   256	async def mount(
   257	    coordinator: Any, config: dict[str, Any] | None = None
   258	) -> dict[str, Any]:  # noqa: ARG001
   259	    """Mount Gemini TTS tool. No background loading — cloud API, no local model."""
   260	    tools = [GeminiGenerateSpeechTool()]
   261	    for t in tools:
   262	        await coordinator.mount("tools", t, name=t.name)
   263	
   264	    logger.info("tool-gemini-tts mounted: %s", [t.name for t in tools])
   265	    return {
   266	        "name": "tool-gemini-tts",
   267	        "version": "1.0.0",
   268	        "provides": [t.name for t in tools],
   269	    }