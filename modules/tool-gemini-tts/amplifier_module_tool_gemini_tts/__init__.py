"""Amplifier tool module — Gemini TTS (Google AI cloud API).

Provides gemini_generate_speech with 30 prebuilt voices,
single-speaker and multi-speaker (2-speaker) modes.
Requires GOOGLE_API_KEY environment variable.
"""

import asyncio
import logging
import os
import uuid
import wave
from pathlib import Path
from typing import Any

from amplifier_core import ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 30 prebuilt Gemini voices
# ---------------------------------------------------------------------------
GEMINI_VOICES = {
    "Zephyr": "Bright",
    "Puck": "Upbeat",
    "Charon": "Informative",
    "Kore": "Firm",
    "Fenrir": "Excitable",
    "Leda": "Youthful",
    "Orus": "Firm",
    "Aoede": "Breezy",
    "Callirrhoe": "Easy-going",
    "Autonoe": "Bright",
    "Enceladus": "Breathy",
    "Iapetus": "Clear",
    "Umbriel": "Easy-going",
    "Algieba": "Smooth",
    "Despina": "Smooth",
    "Erinome": "Clear",
    "Algenib": "Gravelly",
    "Rasalgethi": "Informative",
    "Laomedeia": "Upbeat",
    "Achernar": "Soft",
    "Alnilam": "Firm",
    "Schedar": "Even",
    "Gacrux": "Mature",
    "Pulcherrima": "Forward",
    "Achird": "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat": "Warm",
}

_VOICE_LIST = ", ".join(f"{k} ({v})" for k, v in GEMINI_VOICES.items())


# ---------------------------------------------------------------------------
# gemini_generate_speech
# ---------------------------------------------------------------------------


class GeminiGenerateSpeechTool:
    @property
    def name(self) -> str:
        return "gemini_generate_speech"

    @property
    def description(self) -> str:
        return (
            "Generate speech via Google Gemini TTS (cloud API, requires GOOGLE_API_KEY). "
            "30 expressive prebuilt voices. Fast, no GPU required. "
            "Supports single-speaker and multi-speaker (up to 2) modes. "
            "Style can be embedded in text or passed via the style parameter. "
            "Inline tags like [whispers], [laughs], [sighs], [gasp], [cough], [excited], "
            "[shouting], [tired], [crying], [amazed], [curious], [giggles], [mischievously], "
            "[panicked], [sarcastic], [serious], [trembling] are supported. "
            "Tags are not exhaustive — experiment freely with any emotion or expression. "
            "Returns absolute path to the saved WAV file."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Text to synthesize. Embed style inline: 'Say cheerfully: Have a wonderful day!' "
                        "Supports tags: [whispers], [laughs], [sighs], [gasp], [cough], etc."
                    ),
                },
                "voice": {
                    "type": "string",
                    "description": f"Prebuilt voice name. Options: {_VOICE_LIST}. Default: Kore.",
                },
                "style": {
                    "type": "string",
                    "description": (
                        "Optional style instruction prepended to the text. "
                        "E.g. 'Read like a warm audiobook narrator.' Not used in multi-speaker mode."
                    ),
                },
                "speakers": {
                    "type": "array",
                    "description": (
                        "Multi-speaker mode (max 2 speakers). "
                        'Each item: {"speaker": "Name", "voice": "VoiceName"}. '
                        "The text must reference each speaker by name, e.g. "
                        "'Joe: Hello there.\\nJane: Hi, how are you?'"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {"type": "string"},
                            "voice": {"type": "string"},
                        },
                        "required": ["speaker", "voice"],
                    },
                },
                "model": {
                    "type": "string",
                    "description": (
                        "Gemini TTS model. "
                        "gemini-3.1-flash-tts-preview (default, fastest), "
                        "gemini-2.5-flash-preview-tts, "
                        "gemini-2.5-pro-preview-tts (highest quality)."
                    ),
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the WAV. Auto-named in CWD if omitted.",
                },
            },
            "required": ["text"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return ToolResult(
                success=False,
                output="GOOGLE_API_KEY not set. Gemini TTS requires a Google AI API key.",
            )

        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore
        except ImportError:
            return ToolResult(
                success=False,
                output="google-genai not installed. Run: pip install google-genai",
            )

        text: str = input_data["text"]
        voice: str = input_data.get("voice", "Kore")
        style: str | None = input_data.get("style")
        speakers: list[dict] | None = input_data.get("speakers")
        model: str = input_data.get("model", "gemini-3.1-flash-tts-preview")
        out_str: str | None = input_data.get("output_path")
        output_path = (
            Path(out_str) if out_str else Path(f"gemini_{uuid.uuid4().hex[:8]}.wav")
        )

        contents = text
        if style and not speakers:
            contents = f"{style}\n\n{text}"

        if speakers:
            if len(speakers) > 2:
                return ToolResult(
                    success=False,
                    output="Gemini multi-speaker supports at most 2 speakers.",
                )
            speaker_configs = [
                types.SpeakerVoiceConfig(
                    speaker=s["speaker"],
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=s["voice"]
                        )
                    ),
                )
                for s in speakers
            ]
            speech_config = types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=speaker_configs
                )
            )
        else:
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )

        def _sync() -> bytes:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=speech_config,
                ),
            )
            return response.candidates[0].content.parts[0].inline_data.data

        # Gemini TTS occasionally returns text tokens instead of audio tokens,
        # causing a 500 error. The docs recommend retry logic for this.
        max_attempts = 3
        loop = asyncio.get_running_loop()
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                pcm_data = await loop.run_in_executor(None, _sync)
                break
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts:
                    logger.warning(
                        "Gemini TTS attempt %d/%d failed: %s — retrying",
                        attempt,
                        max_attempts,
                        exc,
                    )
                    await asyncio.sleep(1.0 * attempt)
        else:
            return ToolResult(
                success=False,
                output=f"Gemini TTS failed after {max_attempts} attempts: {last_exc}",
            )

        # Gemini returns 24 kHz, 16-bit, mono PCM
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)

        size_kb = output_path.stat().st_size / 1024
        return ToolResult(
            success=True, output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}"
        )


# ---------------------------------------------------------------------------
# mount
# ---------------------------------------------------------------------------


async def mount(
    coordinator: Any, config: dict[str, Any] | None = None
) -> dict[str, Any]:  # noqa: ARG001
    """Mount Gemini TTS tool. No background loading — cloud API, no local model."""
    tools = [GeminiGenerateSpeechTool()]
    for t in tools:
        await coordinator.mount("tools", t, name=t.name)

    logger.info("tool-gemini-tts mounted: %s", [t.name for t in tools])
    return {
        "name": "tool-gemini-tts",
        "version": "1.0.0",
        "provides": [t.name for t in tools],
    }
