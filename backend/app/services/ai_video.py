import httpx, os, time, pathlib, json, asyncio
from app.config import settings
from app.services.tts import text_to_speech

# === IA VIDEO REAL ===
# Prioridad: 1) PiAPI Hunyuan (créditos gratis) 2) Replicate 3) HeyGen 4) D-ID 5) DEMO


def _prompt_video(tema: str, guion: str) -> str:
    g = (guion or "")[:220].strip().replace("\n"," ")
    return (f"Cinematic vertical 9:16 video for TikTok about {tema}. "
            f"Golden hour light over Colombian llanos savanna, tall grass waving in the wind, documentary look. "
            f"Voice-over narration says: {g}. Natural sound design, calm warm tones.")


async def _piapi_video(tema: str, guion: str):
    prompt = _prompt_video(tema, guion)
    payload = {
        "model": "Qubico/hunyuan",
        "task_type": "fast-txt2video",
        "input": {"prompt": prompt, "aspect_ratio": "9:16"}
    }
    headers = {"x-api-key": settings.PIAPI_API_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=50) as c:
            r = await c.post("https://api.piapi.ai/api/v1/task", headers=headers, json=payload)
            if r.status_code != 200:
                return {"ok": False, "provider": "piapi", "error": f"HTTP {r.status_code}: {r.text[:300]}"}
            j = r.json()
        if j.get("code") not in (200, 0):
            return {"ok": False, "provider": "piapi", "error": str(j.get("message") or j)[:300]}
        data = j.get("data", {})
        tid = data.get("task_id")
        url = (data.get("output") or {}).get("video_url")
        if not url and tid:
            for _ in range(90):
                await asyncio.sleep(5)
                async with httpx.AsyncClient(timeout=40) as c:
                    s = await c.get(f"https://api.piapi.ai/api/v1/task/{tid}", headers=headers)
                sj = s.json(); st = (sj.get("data") or {}).get("status")
                out = (sj.get("data") or {}).get("output") or {}
                if out.get("video_url"):
                    url = out["video_url"]; break
                if str(st).lower() in ("failed", "error"):
                    return {"ok": False, "provider": "piapi", "error": str(sj)[:200]}
        if url:
            async with httpx.AsyncClient(timeout=240) as c:
                dd = await c.get(url)
            pathlib.Path("static").mkdir(exist_ok=True)
            pathlib.Path("static/corocoro_ia.mp4").write_bytes(dd.content)
            return {"ok": True, "provider": "piapi/hunyuan", "modo": "AI video (texto->video)",
                    "video": "static/corocoro_ia.mp4", "video_url": url, "guion": guion}
        return {"ok": False, "provider": "piapi", "error": "sin output URL"}
    except Exception as e:
        return {"ok": False, "provider": "piapi", "error": repr(e)[:200]}


async def _replicate_video(tema: str, guion: str):
    prompt = _prompt_video(tema, guion)
    try:
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post(
                "https://api.replicate.com/v1/models/wan-video/wan-2.6-t2v/predictions",
                headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}", "Content-Type": "application/json"},
                json={"input": {"prompt": prompt}})
            if r.status_code not in (200, 201):
                return {"ok": False, "provider": "replicate", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
            pred = r.json()
        rid = pred.get("id")
        for _ in range(95):
            await asyncio.sleep(6)
            async with httpx.AsyncClient(timeout=40) as c:
                s = await c.get(f"https://api.replicate.com/v1/predictions/{rid}",
                                headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}"})
            j = s.json(); st = j.get("status")
            if st == "succeeded":
                out = j.get("output")
                url = out if isinstance(out, str) else (out[0] if isinstance(out, list) and out else None)
                if url:
                    async with httpx.AsyncClient(timeout=240) as c:
                        dd = await c.get(url)
                    pathlib.Path("static").mkdir(exist_ok=True)
                    pathlib.Path("static/corocoro_ia.mp4").write_bytes(dd.content)
                    return {"ok": True, "provider": "replicate/wan-2.6", "modo": "AI video (texto->video)",
                            "video": "static/corocoro_ia.mp4", "video_url": url, "guion": guion}
                return {"ok": False, "provider": "replicate", "error": "sin output"}
            if st == "failed":
                return {"ok": False, "provider": "replicate", "error": str(j.get("error") or "failed")}
        return {"ok": False, "provider": "replicate", "error": "timeout"}
    except Exception as e:
        return {"ok": False, "provider": "replicate", "error": repr(e)[:200]}


async def crear_video_ia(tema: str, guion: str, avatar_url: str = None):
    try:
        await text_to_speech(guion[:280], "static/corocoro_voz.mp3")
    except Exception:
        pass

    # 1. PiAPI Hunyuan (créditos gratis)
    if settings.PIAPI_API_KEY:
        res = await _piapi_video(tema, guion)
        if res.get("ok"):
            return res
        print("PiAPI fallback:", (res or {}).get("error"))

    # 2. Replicate Wan 2.6 (si tiene créditos)
    if settings.REPLICATE_API_KEY:
        res = await _replicate_video(tema, guion)
        if res.get("ok"):
            return res
        print("Replicate fallback:", (res or {}).get("error"))

    # 3. HeyGen
    HEYGEN_KEY = os.getenv("HEYGEN_API_KEY","")
    if HEYGEN_KEY:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                payload = {
                    "video_inputs": [{
                        "character": {"type": "avatar", "avatar_id": os.getenv("HEYGEN_AVATAR_ID",""), "avatar_style": "normal"},
                        "voice": {"type": "text", "input_text": guion[:240], "voice_id": os.getenv("HEYGEN_VOICE_ID","")},
                        "background": {"type": "color", "value": "#fef9e7"}
                    }],
                    "dimension": {"width": 720, "height": 1280}, "caption": False
                }
                r = await c.post("https://api.heygen.com/v2/video/generate",
                    headers={"X-Api-Key": HEYGEN_KEY, "Content-Type":"application/json"}, json=payload)
                if r.status_code==200:
                    vid = r.json()["data"]["video_id"]
                    for _ in range(20):
                        await asyncio.sleep(6)
                        s = await c.get(f"https://api.heygen.com/v1/video_status.get?video_id={vid}", headers={"X-Api-Key": HEYGEN_KEY})
                        if s.json().get("data",{}).get("status")=="completed":
                            url = s.json()["data"]["video_url"]
                            async with httpx.AsyncClient(timeout=120) as cc:
                                dd = await cc.get(url)
                            pathlib.Path("static/corocoro_heygen.mp4").write_bytes(dd.content)
                            return {"ok": True, "provider":"heygen", "video":"static/corocoro_heygen.mp4", "guion": guion}
                    return {"ok": True, "provider":"heygen", "video_id": vid, "status":"processing", "guion": guion}
                return {"ok": False, "provider":"heygen", "error": r.text[:200]}
        except Exception as e:
            print("HeyGen error", e)

    # 4. DEMO / instrucciones
    return {
        "ok": True,
        "provider": "DEMO",
        "modo": "SIN API KEY de PiAPI",
        "guion": guion,
        "audio": "static/corocoro_voz.mp3",
        "instruccion": "Para video IA real gratis: 1) entra a piapi.ai -> regístrate gratis -> 2) copia tu API Key -> 3) en backend/.env pon PIAPI_API_KEY=... -> 4) llama /video-ia",
        "nota": "El modelo Hunyuan de PiAPI genera video 9:16 (TikTok) con texto->video. Créditos gratis incluidos al registrarte."
    }


def instruccion():
    return """
🎬 VIDEO IA REAL (PiAPI + Hunyuan) — GRATIS con créditos de prueba:
1. Entra a https://piapi.ai -> Sign Up gratis (sin tarjeta)
2. En tu dashboard -> API Key -> copiar
3. En corocoro-ia/backend/.env: PIAPI_API_KEY=tu_llave
4. Reinicia el backend y llama: POST http://localhost:8000/video-ia?tema=Safari Guanapalo

Créditos: los de prueba alcanzan para ~30 videos. Luego se paga $0.03-0.09/video.

Alternativas: Replicate (Wan 2.6, $0.03-0.60), HeyGen (3 gratis/mes avatar que habla).
"""