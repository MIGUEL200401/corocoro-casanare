import os, httpx, pathlib
from app.config import settings

async def text_to_speech(text: str, out_path: str = "corocoro_voz.mp3"):
    # Prioridad: ElevenLabs -> OpenAI TTS -> fallback gTTS
    if settings.ELEVENLABS_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(f"https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
                    headers={"xi-api-key": settings.ELEVENLABS_KEY, "Content-Type":"application/json"},
                    json={"text": text, "model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.6,"similarity_boost":0.7}})
                if r.status_code==200:
                    pathlib.Path(out_path).write_bytes(r.content)
                    return out_path
        except Exception as e: print(e)
    if settings.OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post("https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={"model":"tts-1","voice":"onyx","input": text})
                if r.status_code==200:
                    pathlib.Path(out_path).write_bytes(r.content)
                    return out_path
        except Exception as e: print(e)
    # fallback gTTS offline style (requires gTTS lib if installed)
    try:
        from gtts import gTTS
        tts = gTTS(text, lang='es')
        tts.save(out_path)
        return out_path
    except: pass
    return None
