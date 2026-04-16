"""Amplifier tool module — Qwen3-TTS.

Two tools backed by two model variants:
  qwen3_design_speech — voice design via natural-language instruct string (VoiceDesign model)
  qwen3_clone_speech  — voice cloning from reference audio (Base model)
"""

import asyncio
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from amplifier_core import ToolResult

_INFERENCE_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="qwen3-infer"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Two model singletons — loaded lazily on first use of each tool
# ---------------------------------------------------------------------------
_design_model = None
_clone_model = None
_model_lock = threading.Lock()
_design_error: str | None = None
_clone_error: str | None = None

_DESIGN_CHECKPOINT = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
_CLONE_CHECKPOINT = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def _detect_device() -> tuple[str, Any]:
    import torch  # type: ignore

    if torch.backends.mps.is_available():
        return "mps", torch.float16
    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def _load_design_sync() -> None:
    global _design_model, _design_error
    if _design_model is not None:
        return
    with _model_lock:
        if _design_model is not None:
            return
        try:
            from qwen_tts import Qwen3TTSModel  # type: ignore

            device, dtype = _detect_device()
            logger.info("Qwen3-TTS: loading VoiceDesign model on %s …", device)
            _m = Qwen3TTSModel.from_pretrained(
                _DESIGN_CHECKPOINT,
                device_map=device,
                dtype=dtype,
                attn_implementation="eager",
            )
            _design_model = _m
            logger.info("Qwen3-TTS: VoiceDesign ready ✓")
        except Exception as exc:
            _design_error = str(exc)
            logger.error("Qwen3-TTS: VoiceDesign load failed: %s", exc)


def _load_clone_sync() -> None:
    global _clone_model, _clone_error
    if _clone_model is not None:
        return
    with _model_lock:
        if _clone_model is not None:
            return
        try:
            from qwen_tts import Qwen3TTSModel  # type: ignore

            device, dtype = _detect_device()
            logger.info("Qwen3-TTS: loading Base (clone) model on %s …", device)
            _m = Qwen3TTSModel.from_pretrained(
                _CLONE_CHECKPOINT,
                device_map=device,
                dtype=dtype,
                attn_implementation="eager",
            )
            _clone_model = _m
            logger.info("Qwen3-TTS: Base (clone) ready ✓")
        except Exception as exc:
            _clone_error = str(exc)
            logger.error("Qwen3-TTS: Base load failed: %s", exc)


async def _ensure_design() -> tuple[Any, str | None]:
    global _design_model, _design_error
    if _design_model is not None:
        return _design_model, None
    if _design_error:
        return None, _design_error
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_INFERENCE_EXECUTOR, _load_design_sync)
    return _design_model, _design_error


async def _ensure_clone() -> tuple[Any, str | None]:
    global _clone_model, _clone_error
    if _clone_model is not None:
        return _clone_model, None
    if _clone_error:
        return None, _clone_error
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_INFERENCE_EXECUTOR, _load_clone_sync)
    return _clone_model, _clone_error


def _fix_text(text: str) -> str:
    """Normalize smart quotes and typography that Qwen3-TTS can stumble on."""
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2026", "...")
        .replace("\u2014", "--")
        .replace("\u2013", "-")
    )


# ---------------------------------------------------------------------------
# qwen3_design_speech
# ---------------------------------------------------------------------------


class Qwen3DesignSpeechTool:
    @property
    def name(self) -> str:
        return "qwen3_design_speech"

    @property
    def description(self) -> str:
        return (
            "Generate speech using Qwen3-TTS VoiceDesign. "
            "Describe the voice you want in natural language via the instruct parameter — "
            "gender, age, accent, pitch, style. No reference audio needed. "
            "Returns absolute path to the saved WAV file."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to synthesize.",
                },
                "instruct": {
                    "type": "string",
                    "description": (
                        "Natural-language voice description. Combine any of: "
                        "gender (male/female), age (child/teenager/young adult/middle-aged/elderly), "
                        "pitch (very low/low/moderate/high/very high pitch), accent "
                        "(american/british/australian/canadian/indian/chinese/korean/japanese), "
                        "style (whisper, gravelly, warm, energetic, etc). "
                        "Example: 'Male, 50s, deep gravelly warmth, American, experienced audiobook narrator — "
                        "unhurried and knowing.'"
                    ),
                },
                "language": {
                    "type": "string",
                    "description": "Language name. Default 'English'.",
                    "default": "English",
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the WAV. Auto-named in CWD if omitted.",
                },
            },
            "required": ["text", "instruct"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        text: str = _fix_text(input_data["text"])
        instruct: str = input_data["instruct"]
        language: str = input_data.get("language", "English")
        out_str: str | None = input_data.get("output_path")
        output_path = (
            Path(out_str)
            if out_str
            else Path(f"qwen3_design_{uuid.uuid4().hex[:8]}.wav")
        )

        model, err = await _ensure_design()
        if err:
            return ToolResult(
                success=False, output=f"VoiceDesign model load failed: {err}"
            )

        loop = asyncio.get_running_loop()

        def _sync() -> float:
            import soundfile as sf  # type: ignore

            wavs, sr = model.generate_voice_design(
                text=text, language=language, instruct=instruct
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), wavs[0], sr)
            return output_path.stat().st_size / 1024

        try:
            size_kb = await loop.run_in_executor(_INFERENCE_EXECUTOR, _sync)
            return ToolResult(
                success=True, output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}"
            )
        except Exception as exc:
            return ToolResult(success=False, output=f"Generation failed: {exc}")


# ---------------------------------------------------------------------------
# qwen3_clone_speech
# ---------------------------------------------------------------------------


class Qwen3CloneSpeechTool:
    @property
    def name(self) -> str:
        return "qwen3_clone_speech"

    @property
    def description(self) -> str:
        return (
            "Generate speech using Qwen3-TTS voice cloning. "
            "Provide a reference audio file (5-15s) and its transcript to clone that speaker's voice. "
            "Produces highly consistent voice identity across multiple calls with the same reference. "
            "Returns absolute path to the saved WAV file."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to synthesize in the cloned voice.",
                },
                "ref_audio_path": {
                    "type": "string",
                    "description": "Path to a reference WAV file (5-15s) of the voice to clone.",
                },
                "ref_text": {
                    "type": "string",
                    "description": "Exact transcript of what is spoken in the reference audio.",
                },
                "language": {
                    "type": "string",
                    "description": "Language name. Default 'English'.",
                    "default": "English",
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the WAV. Auto-named in CWD if omitted.",
                },
            },
            "required": ["text", "ref_audio_path", "ref_text"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        text: str = _fix_text(input_data["text"])
        ref_audio_path: str = input_data["ref_audio_path"]
        ref_text: str = _fix_text(input_data["ref_text"])
        language: str = input_data.get("language", "English")
        out_str: str | None = input_data.get("output_path")
        output_path = (
            Path(out_str)
            if out_str
            else Path(f"qwen3_clone_{uuid.uuid4().hex[:8]}.wav")
        )

        if not Path(ref_audio_path).exists():
            return ToolResult(
                success=False, output=f"Reference audio not found: {ref_audio_path}"
            )

        model, err = await _ensure_clone()
        if err:
            return ToolResult(success=False, output=f"Clone model load failed: {err}")

        loop = asyncio.get_running_loop()

        def _sync() -> float:
            import soundfile as sf  # type: ignore

            prompt = model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text=ref_text,
            )
            wavs, sr = model.generate_voice_clone(
                text=text,
                language=language,
                voice_clone_prompt=prompt,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), wavs[0], sr)
            return output_path.stat().st_size / 1024

        try:
            size_kb = await loop.run_in_executor(_INFERENCE_EXECUTOR, _sync)
            return ToolResult(
                success=True, output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}"
            )
        except Exception as exc:
            return ToolResult(success=False, output=f"Generation failed: {exc}")


# ---------------------------------------------------------------------------
# mount
# ---------------------------------------------------------------------------


async def mount(
    coordinator: Any, config: dict[str, Any] | None = None
) -> dict[str, Any]:  # noqa: ARG001
    """Mount Qwen3-TTS tools. Models load lazily on first tool call."""
    tools = [Qwen3DesignSpeechTool(), Qwen3CloneSpeechTool()]
    for t in tools:
        await coordinator.mount("tools", t, name=t.name)

    logger.info("tool-qwen3-tts mounted: %s", [t.name for t in tools])
    return {
        "name": "tool-qwen3-tts",
        "version": "1.0.0",
        "provides": [t.name for t in tools],
    }
