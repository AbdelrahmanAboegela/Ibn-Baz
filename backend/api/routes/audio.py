"""
routes/audio.py
Speech-to-text proxy using Fanar-Aura-STT-1.

Note: This endpoint requires additional Fanar authorization.
Contact support@fanar.qa to enable /v1/audio/transcriptions for your API key.
Rate limit: 20 requests/day (Fanar-Aura-STT-1) or 10/day (Fanar-Aura-STT-LF-1).

The frontend uses the browser Web Speech API as the primary voice input path.
This backend endpoint serves as fallback / for non-browser environments.
"""
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from openai import AsyncOpenAI, APIStatusError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import settings

router = APIRouter(prefix="/api/audio", tags=["Audio"])

_client = AsyncOpenAI(
    api_key=settings.fanar_api_key,
    base_url="https://api.fanar.qa/v1",
)

# Models available for STT
_STT_MODEL = "Fanar-Aura-STT-1"        # 20 req/day — standard Arabic STT
# _STT_MODEL = "Fanar-Aura-STT-LF-1"  # 10 req/day — long-form (>30s audio)


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe uploaded audio to Arabic text via Fanar-Aura-STT-1.
    Accepts: audio/webm, audio/wav, audio/mp4, audio/mpeg (from MediaRecorder).
    Returns: { "text": "..." }
    """
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="صيغة الملف غير مدعومة — أرسل ملف صوتي")

    audio_bytes = await file.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="الملف الصوتي صغير جداً أو فارغ")

    try:
        response = await _client.audio.transcriptions.create(
            model=_STT_MODEL,
            file=(file.filename or "recording.webm", audio_bytes, file.content_type),
            language="ar",
        )
        return {"text": response.text.strip()}

    except APIStatusError as e:
        if e.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="تحويل الصوت إلى نص يتطلب تفويضاً إضافياً من Fanar — تواصل مع support@fanar.qa",
            )
        if e.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="تجاوزت الحد اليومي لتحويل الصوت (20 طلباً/يوم)",
            )
        raise HTTPException(status_code=502, detail=f"خطأ من خادم Fanar: {e.message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل تحويل الصوت: {str(e)}")
