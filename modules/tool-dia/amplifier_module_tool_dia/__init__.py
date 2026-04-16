"""Amplifier tool module — Dia TTS (nari-labs/Dia-1.6B-0626).

Generates ultra-realistic two-speaker dialogue using [S1] / [S2] tags.
Supports nonverbal actions and optional voice conditioning via audio prompt.
"""

import asyncio
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from amplifier_core import ToolResult

_INFERENCE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dia-infer")
logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
_model_error: str | None = None


def _load_model_sync() -> None:
    """Load Dia model once. Pinned to the single-worker executor for MPS safety."""
    global _model, _model_error
    if _model is not None:
        return
    with _model_lock:
        if _model is not None:
            return
        try:
            from dia.model import Dia  # type: ignore

            logger.info("Dia: loading nari-labs/Dia-1.6B-0626 …")
            _m = Dia.from_pretrained("nari-labs/Dia-1.6B-0626", compute_dtype="float16")
            _model = _m
            logger.info("Dia: ready ✓")
        except Exception as exc:
            _model_error = str(exc)
            logger.error("Dia: load failed: %s", exc)


async def _ensure_model() -> tuple[Any, str | None]:
    global _model, _model_error
    if _model is not None:
        return _model, None
    if _model_error:
        return None, _model_error
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_INFERENCE_EXECUTOR, _load_model_sync)
    return _model, _model_error


# ---------------------------------------------------------------------------
# dia_generate_speech
# ---------------------------------------------------------------------------


class DiaGenerateSpeechTool:
    @property
    def name(self) -> str:
        return "dia_generate_speech"

    @property
    def description(self) -> str:
        return (
            "Generate podcast-style two-speaker dialogue using Dia 1.6B (nari-labs). "
            "Uses [S1] and [S2] speaker tags. Supports nonverbal actions like (laughs), "
            "(sighs), (coughs). Optionally pass audio_prompt_path + audio_prompt_transcript "
            "to condition voice style/identity (5-10s WAV). "
            "Returns absolute path to the saved WAV file."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": (
                        "Dialogue script with [S1] and [S2] speaker tags. "
                        "Always start with [S1]. Alternate speakers — never repeat the same tag. "
                        "Keep to ~5-20 seconds of audio for best quality. "
                        "Nonverbal actions: (laughs), (sighs), (coughs), (gasps), (clears throat), "
                        "(mumbles), (groans), (chuckle), (whistles), (screams), (inhales), (exhales), "
                        "(applause), (humming), (sneezes). "
                        "Example: '[S1] So this shipped last week. [S2] Yeah, and it actually worked! (laughs) [S1] First try?'"
                    ),
                },
                "audio_prompt_path": {
                    "type": "string",
                    "description": (
                        "Optional path to a WAV/MP3 file (5-10s) to condition voice identity. "
                        "Must also provide audio_prompt_transcript."
                    ),
                },
                "audio_prompt_transcript": {
                    "type": "string",
                    "description": (
                        "Transcript of the audio_prompt_path file, with correct [S1]/[S2] tags. "
                        "Required when audio_prompt_path is provided."
                    ),
                },
                "output_path": {
                    "type": "string",
                    "description": "Where to save the WAV. Auto-named in CWD if omitted.",
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed for reproducible voice generation. Omit for random.",
                },
                "cfg_scale": {
                    "type": "number",
                    "description": "Classifier-free guidance scale. Default 3.0. Higher = more faithful to script.",
                    "default": 3.0,
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature. Default 1.8.",
                    "default": 1.8,
                },
            },
            "required": ["script"],
        }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        script: str = input_data["script"]
        audio_prompt_path: str | None = input_data.get("audio_prompt_path")
        audio_prompt_transcript: str | None = input_data.get("audio_prompt_transcript")
        output_path_str: str | None = input_data.get("output_path")
        seed: int | None = input_data.get("seed")
        cfg_scale: float = input_data.get("cfg_scale", 3.0)
        temperature: float = input_data.get("temperature", 1.8)

        output_path = (
            Path(output_path_str)
            if output_path_str
            else Path(f"dia_{uuid.uuid4().hex[:8]}.wav")
        )

        if audio_prompt_path and not audio_prompt_transcript:
            return ToolResult(
                success=False,
                output="audio_prompt_transcript is required when audio_prompt_path is provided.",
            )
        if audio_prompt_path and not Path(audio_prompt_path).exists():
            return ToolResult(
                success=False,
                output=f"Audio prompt file not found: {audio_prompt_path}",
            )

        model, err = await _ensure_model()
        if err:
            return ToolResult(success=False, output=f"Model load failed: {err}")

        loop = asyncio.get_running_loop()

        def _sync() -> float:
            import soundfile as sf  # type: ignore

            # For voice cloning: prepend transcript so the model knows the voice
            gen_text = script
            if audio_prompt_path and audio_prompt_transcript:
                gen_text = audio_prompt_transcript + script

            gen_kwargs: dict[str, Any] = {
                "text": gen_text,
                "use_torch_compile": False,
                "verbose": False,
                "cfg_scale": cfg_scale,
                "temperature": temperature,
                "top_p": 0.90,
                "cfg_filter_top_k": 45,
            }
            if audio_prompt_path:
                gen_kwargs["audio_prompt"] = audio_prompt_path
            if seed is not None:
                gen_kwargs["seed"] = seed

            output = model.generate(**gen_kwargs)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), output, 44100)
            return output_path.stat().st_size / 1024

        try:
            size_kb = await loop.run_in_executor(_INFERENCE_EXECUTOR, _sync)
            return ToolResult(
                success=True,
                output=f"Saved {size_kb:.0f} KB → {output_path.resolve()}",
            )
        except Exception as exc:
            return ToolResult(success=False, output=f"Generation failed: {exc}")


# ---------------------------------------------------------------------------
# mount
# ---------------------------------------------------------------------------


async def mount(
    coordinator: Any, config: dict[str, Any] | None = None
) -> dict[str, Any]:  # noqa: ARG001
    """Mount Dia tool and kick off background model loading."""
    tools = [DiaGenerateSpeechTool()]
    for t in tools:
        await coordinator.mount("tools", t, name=t.name)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(_INFERENCE_EXECUTOR, _load_model_sync)

    logger.info("tool-dia mounted: %s", [t.name for t in tools])
    return {
        "name": "tool-dia",
        "version": "1.0.0",
        "provides": [t.name for t in tools],
    }
