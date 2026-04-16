"""Amplifier tool module — OmniVoice TTS (direct inference, no server required)."""

import asyncio
import json
import logging
import os
import shutil
import threading
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import soundfile as sf
import torch
from amplifier_core import ToolResult

# ---------------------------------------------------------------------------
# Dedicated single-threaded executor for ALL model operations.
#
# MPS (Apple Silicon Metal) has a thread-local context — all tensor ops must
# happen on the SAME OS thread or PyTorch segfaults.  A 1-worker pool pins
# every call (load, warmup, generate) to one persistent thread.
# ---------------------------------------------------------------------------
_INFERENCE_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="omnivoice-infer"
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice library  (~/.amplifier/omnivoice/)
# ---------------------------------------------------------------------------
DATA_DIR = Path.home() / ".amplifier" / "omnivoice"
VOICES_FILE = DATA_DIR / "voices.json"
REF_AUDIO_DIR = DATA_DIR / "ref_audio"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REF_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _load_voices() -> dict:
    if VOICES_FILE.exists():
        return json.loads(VOICES_FILE.read_text())
    return {}


def _persist_voices(voices: dict) -> None:
    _ensure_dirs()
    VOICES_FILE.write_text(json.dumps(voices, indent=2))


# ---------------------------------------------------------------------------
# Model singleton — loaded once per process, reused across all tool calls
# ---------------------------------------------------------------------------
_model = None
_model_lock = threading.Lock()
_model_error: str | None = None
_model_device: str | None = None


def _detect_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def _load_model_sync() -> None:
    """Thread-safe sync model load. Called from executor — never call directly in async code."""
    global _model, _model_error, _model_device

    if _model is not None:
        return

    with _model_lock:
        if _model is not None:
            return
        try:
            from omnivoice import OmniVoice  # type: ignore

            device = _detect_device()
            _model_device = device
            dtype = torch.float32 if device == "cpu" else torch.float16

            logger.info("OmniVoice: loading on %s…", device)
            # Use a local var — _model stays None until warmup is fully done.
            # If we assigned _model here, _ensure_model() could return it
            # before shaders are compiled and every first real call would be
            # gibberish.
            _m = OmniVoice.from_pretrained(
                "k2-fsa/OmniVoice",
                device_map=device,
                dtype=dtype,
            )

            # Warmup: compiles MPS Metal shaders before any real request.
            # Must use num_step=32 (the actual default) — Metal compiles shader
            # variants per diffusion step, so num_step=4 leaves steps 5–32
            # uncompiled and the first real call at the default step count is
            # still garbage.
            if device == "mps":
                logger.info("OmniVoice: warming up MPS shaders (num_step=32)…")
                _m.generate(text="warming up the voice model.", num_step=32)
                torch.mps.synchronize()
                logger.info("OmniVoice: warmup done ✓")

            # Assign last — nothing can use the model until warmup is complete.
            _model = _m
            logger.info("OmniVoice: ready on %s ✓", device)
        except Exception as exc:
            _model_error = str(exc)
            logger.error("OmniVoice: load failed: %s", exc)


async def _ensure_model() -> tuple[Any, str | None]:
    """Return (model, error). Loads the model if not yet loaded."""
    global _model, _model_error
    if _model is not None:
        return _model, None
    if _model_error:
        return None, _model_error
    loop = asyncio.get_running_loop()
    # Always submit to the dedicated 1-worker executor so model load and
    # inference share the same OS thread (required for MPS thread-local state).
    await loop.run_in_executor(_INFERENCE_EXECUTOR, _load_model_sync)
    return _model, _model_error


# ---------------------------------------------------------------------------
# Shared generation helper
# ---------------------------------------------------------------------------


async def _generate(gen_kwargs: dict) -> tuple[Any, str | None]:
    """Run model.generate() in the dedicated 1-worker executor."""
    model, err = await _ensure_model()
    if err:
        return None, err

    loop = asyncio.get_running_loop()

    def _sync() -> Any:
        tensors = model.generate(**gen_kwargs)
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        return tensors[0].squeeze(0).cpu().float().numpy()

    try:
        # _INFERENCE_EXECUTOR has max_workers=1 — same thread as model load,
        # which is required for MPS thread-local tensor state.
        audio = await loop.run_in_executor(_INFERENCE_EXECUTOR, _sync)
        return audio, None
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# generate_speech
# ---------------------------------------------------------------------------


class GenerateSpeechTool:
    @property
    def name(self) -> str:
        return "generate_speech"

    @property
    def description(self) -> str:
        return (
            "Generate speech audio directly from text using OmniVoice (no server needed). "
            "Supports expressive inline tags: [laughter], [sigh], [surprise-oh], etc. "
            "Voice options (pick one): voice_id from the library, instruct string for voice "
            "design, ref_audio_path for voice cloning, or omit all for a random voice. "
            "Returns the absolute path to the saved WAV file."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Text to synthesize. Inline expressive tags: "
                        "[laughter], [sigh], [confirmation-en], [question-en], "
                        "[surprise-ah], [surprise-oh], [surprise-wa], [surprise-yo], "
                        "[dissatisfaction-hnn]."
                    ),
                },
                "voice_id": {
                    "type": "string",
                    "description": "ID of a saved voice (from list_voices or save_voice).",
                },
                "instruct": {
                    "type": "string",
                    "description": (
                        "Voice design string. "
                        "Combine: male/female; child/teenager/young adult/middle-aged/elderly; "
                        "very low/low/moderate/high/very high pitch; whisper; "
                        "american/british/australian/canadian/indian accent. "
                        "Example: 'female, young adult, british accent, high pitch'."
                    ),
                },
                "ref_audio_path": {
                    "type": "string",
                    "description": "Path to a 3–10 second audio file to clone that speaker's voice.",
                },
                "ref_text": {
                    "type": "string",
                    "description": "Transcript of the reference audio (optional, auto-transcribed if absent).",
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the WAV. Auto-named in the current directory if omitted.",
                },
                "num_step": {
                    "type": "integer",
                    "description": "Diffusion steps. Default 32. Use 16 for fast previews.",
                    "default": 32,
                },
                "speed": {
                    "type": "number",
                    "description": "Speed multiplier. 1.0 = normal, 0.8 = slower, 1.3 = faster.",
                },
            },
            "required": ["text"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        text = input_data["text"]
        voice_id = input_data.get("voice_id")
        instruct = input_data.get("instruct")
        ref_audio_path = input_data.get("ref_audio_path")
        ref_text = input_data.get("ref_text")
        num_step = input_data.get("num_step", 32)
        speed = input_data.get("speed")
        out_str = input_data.get("output_path")

        output_path = (
            Path(out_str) if out_str else Path(f"speech_{uuid.uuid4().hex[:8]}.wav")
        )

        gen_kwargs: dict[str, Any] = {"text": text, "num_step": num_step}
        if speed is not None:
            gen_kwargs["speed"] = speed

        # Resolve voice — priority: voice_id > ref_audio_path > instruct > auto
        if voice_id:
            voices = _load_voices()
            if voice_id not in voices:
                return ToolResult(
                    success=False,
                    output=f"Voice '{voice_id}' not found. Run list_voices to see available IDs.",
                )
            v = voices[voice_id]
            if v["mode"] == "design" and v.get("instruct"):
                gen_kwargs["instruct"] = v["instruct"]
            elif v["mode"] == "clone" and v.get("ref_audio_path"):
                gen_kwargs["ref_audio"] = v["ref_audio_path"]
                if v.get("ref_text"):
                    gen_kwargs["ref_text"] = v["ref_text"]
        elif ref_audio_path:
            if not Path(ref_audio_path).exists():
                return ToolResult(
                    success=False, output=f"Reference audio not found: {ref_audio_path}"
                )
            gen_kwargs["ref_audio"] = ref_audio_path
            if ref_text:
                gen_kwargs["ref_text"] = ref_text
        elif instruct:
            gen_kwargs["instruct"] = instruct
        # else: auto mode

        audio, err = await _generate(gen_kwargs)
        if err:
            return ToolResult(success=False, output=f"Generation failed: {err}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, 24000)
        size_kb = output_path.stat().st_size / 1024

        return ToolResult(
            success=True,
            output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}",
        )


# ---------------------------------------------------------------------------
# list_voices
# ---------------------------------------------------------------------------


class ListVoicesTool:
    @property
    def name(self) -> str:
        return "list_voices"

    @property
    def description(self) -> str:
        return (
            "List saved voices from the local voice library with their IDs, names, and details. "
            "Call before generate_speech when the user refers to a voice by name."
        )

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:  # noqa: ARG002
        voices = _load_voices()
        if not voices:
            return ToolResult(
                success=True,
                output=(
                    "No saved voices yet.\n"
                    "Create one with save_voice, or pass instruct/ref_audio_path directly to generate_speech."
                ),
            )
        lines = ["Saved voices:\n"]
        for v in voices.values():
            detail = v.get("instruct") or (
                "has reference audio" if v.get("ref_audio_path") else ""
            )
            line = f"  {v['id']}  {v['name']}  [{v['mode']}]"
            if detail:
                line += f"  — {detail}"
            lines.append(line)
        lines.append(f"\nTotal: {len(voices)}")
        return ToolResult(success=True, output="\n".join(lines))


# ---------------------------------------------------------------------------
# save_voice
# ---------------------------------------------------------------------------


class SaveVoiceTool:
    @property
    def name(self) -> str:
        return "save_voice"

    @property
    def description(self) -> str:
        return (
            "Save a named voice to the local library for reuse in generate_speech. "
            "For a design voice provide an instruct string; "
            "for a clone voice provide a path to a reference audio file (3–10 s). "
            "Returns the voice_id to pass to generate_speech."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Friendly name, e.g. 'Demo Host' or 'Ken Clone'.",
                },
                "instruct": {
                    "type": "string",
                    "description": "Voice design string, e.g. 'female, young adult, british accent'.",
                },
                "ref_audio_path": {
                    "type": "string",
                    "description": "Path to reference audio for voice cloning (3–10 seconds).",
                },
                "ref_text": {
                    "type": "string",
                    "description": "Transcript of the reference audio (optional).",
                },
            },
            "required": ["name"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        name = input_data["name"]
        instruct = input_data.get("instruct")
        ref_audio_path = input_data.get("ref_audio_path")
        ref_text = input_data.get("ref_text")

        _ensure_dirs()
        voice_id = uuid.uuid4().hex[:8]
        saved_ref: str | None = None
        mode = "auto"

        if ref_audio_path:
            src = Path(ref_audio_path)
            if not src.exists():
                return ToolResult(
                    success=False, output=f"Reference audio not found: {ref_audio_path}"
                )
            dest = REF_AUDIO_DIR / f"{voice_id}_ref{src.suffix}"
            shutil.copy2(src, dest)
            saved_ref = str(dest)
            mode = "clone"
        elif instruct:
            mode = "design"

        voice = {
            "id": voice_id,
            "name": name,
            "mode": mode,
            "instruct": instruct or "",
            "ref_audio_path": saved_ref,
            "ref_text": ref_text or "",
            "created_at": datetime.now().isoformat(),
        }
        voices = _load_voices()
        voices[voice_id] = voice
        _persist_voices(voices)

        return ToolResult(
            success=True,
            output=f'Saved \'{name}\' as voice_id: {voice_id}\nUse it: generate_speech(text="...", voice_id="{voice_id}")',
        )


# ---------------------------------------------------------------------------
# Gemini TTS voices (30 prebuilt options)
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

_GEMINI_VOICE_LIST = ", ".join(f"{k} ({v})" for k, v in GEMINI_VOICES.items())


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
            "Style can be embedded in the text or passed separately. "
            "Inline tags like [whispers], [laughs], [sighs], [gasp], [cough] are supported. "
            "Returns the absolute path to the saved WAV file."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Text to synthesize. Embed style inline, e.g. 'Say cheerfully: Have a wonderful day!' "
                        "Supports tags: [whispers], [laughs], [sighs], [gasp], [cough], etc."
                    ),
                },
                "voice": {
                    "type": "string",
                    "description": (
                        f"Prebuilt voice name. Options: {_GEMINI_VOICE_LIST}. Default: Kore."
                    ),
                },
                "style": {
                    "type": "string",
                    "description": (
                        "Optional style instruction prepended to the text. "
                        "E.g. 'Read like a warm audiobook narrator.' or "
                        "'Style: Frustrated developer who can\\'t get the build to run.' "
                        "Not used in multi-speaker mode."
                    ),
                },
                "speakers": {
                    "type": "array",
                    "description": (
                        "Multi-speaker mode (max 2 speakers). "
                        'Each item: {"speaker": "Name", "voice": "VoiceName"}. '
                        "The text must reference each speaker by their name, e.g. "
                        "'Joe: Hello there.\\nJane: Hi, how are you?'"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {
                                "type": "string",
                                "description": "Speaker name as used in the text.",
                            },
                            "voice": {
                                "type": "string",
                                "description": "Gemini prebuilt voice name for this speaker.",
                            },
                        },
                        "required": ["speaker", "voice"],
                    },
                },
                "model": {
                    "type": "string",
                    "description": (
                        "Gemini TTS model. Options: "
                        "gemini-3.1-flash-tts-preview (default, fastest), "
                        "gemini-2.5-flash-preview-tts, "
                        "gemini-2.5-pro-preview-tts (highest quality)."
                    ),
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the WAV. Auto-named in the current directory if omitted.",
                },
            },
            "required": ["text"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return ToolResult(
                success=False,
                output="GOOGLE_API_KEY environment variable not set. Gemini TTS requires a Google AI API key.",
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
            Path(out_str)
            if out_str
            else Path(f"gemini_speech_{uuid.uuid4().hex[:8]}.wav")
        )

        # Build prompt contents
        contents = text
        if style and not speakers:
            contents = f"{style}\n\n{text}"

        # Build speech config
        if speakers:
            if len(speakers) > 2:
                return ToolResult(
                    success=False,
                    output="Gemini multi-speaker mode supports at most 2 speakers.",
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

        loop = asyncio.get_running_loop()
        try:
            pcm_data = await loop.run_in_executor(None, _sync)
        except Exception as exc:
            return ToolResult(success=False, output=f"Gemini TTS failed: {exc}")

        # Save as WAV — Gemini TTS outputs 24 kHz, 16-bit, mono PCM
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes per sample
            wf.setframerate(24000)
            wf.writeframes(pcm_data)

        size_kb = output_path.stat().st_size / 1024
        return ToolResult(
            success=True,
            output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}",
        )


# ---------------------------------------------------------------------------
# mount — Iron Law: must call coordinator.mount() and return a dict
# ---------------------------------------------------------------------------


async def mount(
    coordinator: Any, config: dict[str, Any] | None = None
) -> dict[str, Any]:  # noqa: ARG001
    """Mount all OmniVoice tools and kick off background model loading."""
    tools = [
        GenerateSpeechTool(),
        ListVoicesTool(),
        SaveVoiceTool(),
        GeminiGenerateSpeechTool(),
    ]
    for t in tools:
        await coordinator.mount("tools", t, name=t.name)

    # Start loading the OmniVoice model in the background so it's warm before the first call.
    # Must use _INFERENCE_EXECUTOR so model load + warmup + every generate call
    # all run on the same OS thread (MPS thread-local state requirement).
    loop = asyncio.get_running_loop()
    loop.run_in_executor(_INFERENCE_EXECUTOR, _load_model_sync)

    logger.info("tool-omnivoice mounted: %s", [t.name for t in tools])
    return {
        "name": "tool-omnivoice",
        "version": "0.3.0",
        "provides": [t.name for t in tools],
    }
