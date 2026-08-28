import httpx, pathlib, json, os
from app.config import settings

# Servicio Instagram Graph API — genera y publica si hay token, sino modo DEMO

async def publicar_instagram(caption: str, image_url: str = None):
    token = os.getenv("IG_ACCESS_TOKEN","")
    ig_id = os.getenv("IG_USER_ID","")
    # Si no hay credenciales, modo DEMO (no falla el MVP)
    if not token or not ig_id:
        log = pathlib.Path("static/instagram_demo.json")
        log.write_text(json.dumps({"caption": caption, "image_url": image_url, "estado":"DEMO - pendiente token"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "modo":"DEMO", "mensaje":"Post generado y guardado (DEMO). Para publicar real configura IG_ACCESS_TOKEN + IG_USER_ID (cuenta Profesional + Meta App)", "caption": caption, "archivo": str(log)}

    # Flujo real Instagram Graph API
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            # 1. Crear contenedor
            r = await c.post(f"https://graph.facebook.com/v18.0/{ig_id}/media", data={
                "image_url": image_url, "caption": caption, "access_token": token
            })
            if r.status_code!=200:
                return {"ok": False, "error": r.text}
            creation_id = r.json().get("id")
            # 2. Publicar
            r2 = await c.post(f"https://graph.facebook.com/v18.0/{ig_id}/media_publish", data={
                "creation_id": creation_id, "access_token": token
            })
            return {"ok": r2.status_code==200, "response": r2.json(), "caption": caption}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def instruccion_instagram():
    return """
Para activar Instagram real:
1. Convierte tu Instagram a Cuenta Profesional (Empresa)
2. Crea App en developers.facebook.com → añade Instagram Graph API
3. Genera Token de acceso + consigue IG_USER_ID
4. Pon en .env: IG_ACCESS_TOKEN=... y IG_USER_ID=...
5. image_url debe ser pública (sube a tu backend /static o S3)
Más: https://developers.facebook.com/docs/instagram-api/
"""
