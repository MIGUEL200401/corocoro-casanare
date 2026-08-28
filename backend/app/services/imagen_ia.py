import pathlib, urllib.parse
import httpx


def _fondo_url(prompt: str) -> str:
    fp = (
        "https://image.pollinations.ai/p/"
        f"{urllib.parse.quote(prompt)}"
        "?width=1080&height=1350&model=flux&nologo=true&enhance=true"
    )
    return fp


async def descargar_fondo(prompt: str) -> str:
    """Descarga un fondo vertical de alta calidad generado por IA (gratis, sin key)."""
    url = _fondo_url(prompt)
    p = pathlib.Path("static/fondo_ia.jpg")
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as c:
        r = await c.get(url)
        if r.status_code == 200 and len(r.content) > 3000:
            p.write_bytes(r.content)
            return str(p)
    raise RuntimeError("no se pudo generar el fondo IA")