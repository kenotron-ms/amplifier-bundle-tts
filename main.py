"""
OmniVoice Studio — FastAPI wrapper for k2-fsa/OmniVoice
"""

import asyncio
import json
import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("omnivoice-studio")

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent
STATIC_DIR = BASE / "static"
VOICES_DIR = BASE / "voices"
AUDIO_DIR = BASE / "audio_output"
VOICES_JSON = VOICES_DIR / "library.json"

for _d in (STATIC_DIR, VOICES_DIR, AUDIO_DIR):
    _d.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Model state (loaded in background at startup)
# ---------------------------------------------------------------------------
_model = None
_model_status: dict = {
    "ready": False,
    "loading": False,
    "error": None,
    "device": None,
}


def _detect_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def _load_model_sync() -> None:
    global _model
    from omnivoice import OmniVoice  # type: ignore

    device = _detect_device()
    dtype = torch.float32 if device == "cpu" else torch.float16
    _model_status["device"] = device
    logger.info("Loading OmniVoice on %s …", device)
    _model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map=device,
        dtype=dtype,
    )

    # Warmup pass — compiles MPS Metal shaders before the first real request.
    # Without this, the very first generate call returns clicky noise because
    # the JIT shader compilation isn't finished when we read the output tensor.
    if device == "mps":
        logger.info("Warming up MPS shaders…")
        try:
            _model.generate(text="warmup", num_step=4)
            torch.mps.synchronize()
            logger.info("Warmup done ✓")
        except Exception as exc:
            logger.warning("Warmup failed (non-fatal): %s", exc)

    _model_status["ready"] = True
    _model_status["loading"] = False
    logger.info("OmniVoice ready ✓")


async def _load_model_async() -> None:
    _model_status["loading"] = True
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _load_model_sync)
    except Exception as exc:
        _model_status["loading"] = False
        _model_status["error"] = str(exc)
        logger.error("Model load failed: %s", exc)


# ---------------------------------------------------------------------------
# Voice library helpers
# ---------------------------------------------------------------------------

def _load_voices() -> dict:
    if VOICES_JSON.exists():
        return json.loads(VOICES_JSON.read_text())
    return {}


def _save_voices(voices: dict) -> None:
    VOICES_JSON.write_text(json.dumps(voices, indent=2))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_load_model_async())
    yield


app = FastAPI(title="OmniVoice Studio", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return _model_status


# ---------------------------------------------------------------------------
# Voice library
# ---------------------------------------------------------------------------

@app.get("/voices")
def list_voices():
    voices = _load_voices()
    result = []
    for v in voices.values():
        entry = {
            "id": v["id"],
            "name": v["name"],
            "mode": v["mode"],
            "instruct": v.get("instruct", ""),
            "ref_text": v.get("ref_text", ""),
            "created_at": v.get("created_at", ""),
            "has_ref_audio": bool(v.get("ref_audio_path")),
        }
        result.append(entry)
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result


@app.post("/voices")
async def create_voice(
    name: str = Form(...),
    mode: str = Form(...),  # "design" | "clone" | "auto"
    instruct: Optional[str] = Form(None),
    ref_text: Optional[str] = Form(None),
    ref_audio: Optional[UploadFile] = File(None),
):
    voice_id = uuid.uuid4().hex[:8]
    ref_audio_path = None

    if mode == "clone" and ref_audio and ref_audio.filename:
        ext = Path(ref_audio.filename).suffix or ".wav"
        save_path = VOICES_DIR / f"{voice_id}_ref{ext}"
        with open(save_path, "wb") as fh:
            shutil.copyfileobj(ref_audio.file, fh)
        ref_audio_path = str(save_path)

    voice = {
        "id": voice_id,
        "name": name,
        "mode": mode,
        "instruct": instruct or "",
        "ref_text": ref_text or "",
        "ref_audio_path": ref_audio_path,
        "created_at": datetime.now().isoformat(),
    }
    voices = _load_voices()
    voices[voice_id] = voice
    _save_voices(voices)
    logger.info("Saved voice '%s' (%s)", name, voice_id)
    return {"id": voice_id, "name": name}


@app.delete("/voices/{voice_id}")
def delete_voice(voice_id: str):
    voices = _load_voices()
    if voice_id not in voices:
        raise HTTPException(404, "Voice not found")
    v = voices.pop(voice_id)
    if v.get("ref_audio_path"):
        Path(v["ref_audio_path"]).unlink(missing_ok=True)
    _save_voices(voices)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

@app.post("/generate")
async def generate(
    text: str = Form(...),
    # Saved voice (optional)
    voice_id: Optional[str] = Form(None),
    # Inline overrides (used when voice_id is absent or mode="custom")
    mode: Optional[str] = Form("auto"),       # "auto" | "design" | "clone"
    instruct: Optional[str] = Form(None),
    ref_text: Optional[str] = Form(None),
    ref_audio: Optional[UploadFile] = File(None),
    # Generation knobs
    speed: Optional[float] = Form(None),
    num_step: int = Form(32),
    guidance_scale: float = Form(2.0),
):
    if not _model_status["ready"]:
        detail = (
            _model_status.get("error")
            or ("Model is still loading — check /health" if _model_status.get("loading") else "Model not available")
        )
        raise HTTPException(503, detail)

    gen_kwargs: dict = {
        "text": text,
        "num_step": num_step,
        "guidance_scale": guidance_scale,
    }
    if speed is not None:
        gen_kwargs["speed"] = speed

    # Temp file for inline clone uploads
    tmp_path: Optional[Path] = None

    try:
        if voice_id:
            # --- Use saved voice ---
            voices = _load_voices()
            if voice_id not in voices:
                raise HTTPException(404, "Voice not found")
            v = voices[voice_id]
            if v["mode"] == "design" and v.get("instruct"):
                gen_kwargs["instruct"] = v["instruct"]
            elif v["mode"] == "clone" and v.get("ref_audio_path"):
                gen_kwargs["ref_audio"] = v["ref_audio_path"]
                if v.get("ref_text"):
                    gen_kwargs["ref_text"] = v["ref_text"]
        else:
            # --- Inline params ---
            if mode == "design" and instruct:
                gen_kwargs["instruct"] = instruct
            elif mode == "clone" and ref_audio and ref_audio.filename:
                tmp_path = AUDIO_DIR / f"tmp_{uuid.uuid4().hex}.wav"
                with open(tmp_path, "wb") as fh:
                    shutil.copyfileobj(ref_audio.file, fh)
                gen_kwargs["ref_audio"] = str(tmp_path)
                if ref_text:
                    gen_kwargs["ref_text"] = ref_text

        logger.info("Generating: mode=%s len=%d step=%d", mode, len(text), num_step)
        loop = asyncio.get_event_loop()
        tensors = await loop.run_in_executor(
            None, lambda: _model.generate(**gen_kwargs)
        )

        # Ensure MPS has flushed all pending ops before we read the tensor.
        if torch.backends.mps.is_available():
            torch.mps.synchronize()

        out_name = f"{uuid.uuid4().hex[:12]}.wav"
        out_path = AUDIO_DIR / out_name
        # torchaudio.save requires the optional `torchcodec` on newer builds;
        # soundfile is already installed (via omnivoice deps) and works fine.
        # .float() ensures float32 regardless of model dtype (avoids float16 WAVs).
        sf.write(str(out_path), tensors[0].squeeze(0).cpu().float().numpy(), 24000)
        logger.info("Saved audio → %s", out_name)

        return {"audio_url": f"/audio/{out_name}"}

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Static mounts — audio before the HTML catch-all
# ---------------------------------------------------------------------------
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
