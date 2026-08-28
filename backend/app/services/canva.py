import httpx, os, pathlib, json
from app.config import settings

# Canva Connect API — genera post gratis. Si no hay token, usa IA de imagen gratis (pollinations)

async def generar_imagen_post(tema: str):
    # 1. Intenta Canva si hay token
    canva_token = os.getenv("CANVA_TOKEN","")
    if canva_token:
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post("https://api.canva.com/rest/v1/autofill",
                    headers={"Authorization": f"Bearer {canva_token}"},
                    json={"title": tema})
                if r.status_code==200:
                    return {"provider":"canva","data": r.json()}
        except Exception as e: print("canva",e)
    # 2. Fallback gratis: genera imagen vía pollinations.ai (sin key)
    try:
        prompt = f"llanos colombianos Casanare, {tema}, vibrant, tourism poster, paso fino, corocoro bird"
        import urllib.parse
        url = f"https://image.pollinations.ai/p/{urllib.parse.quote(prompt)}?width=1080&height=1080&model=flux"
        # descarga
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url)
            if r.status_code==200:
                p = pathlib.Path("static/post_canva.jpg")
                p.write_bytes(r.content)
                return {"provider":"pollinations","image": str(p), "url": "/static/post_canva.jpg", "prompt": prompt}
    except Exception as e: print(e)
    return {"provider":"demo","image": None, "nota":"Crea en Canva manualmente con el caption generado"}
