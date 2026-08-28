from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.agent.corocoro_agent import agent_chat
from app.services import stats
from app.services.tts import text_to_speech
from app.services.video import generar_video_corto, generar_post_instagram
from app.services.instagram import publicar_instagram
from app.services.ai_video import crear_video_ia
from app.services.scheduler import start_scheduler
from app.services.propuestas import generar_propuesta_diaria
from app.config import settings
import pathlib, os, json, time, datetime

app = FastAPI(title="🤠 Corocoro IA del Casanare - API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    message: str
    user_id: str = "anon"
    nombre: str = ""

async def registrar(inp: ChatIn):
    stats.registrar_mensaje(inp.user_id, inp.nombre)

@app.get("/", include_in_schema=False)
async def index():
    p = pathlib.Path("static/index.html")
    if p.exists():
        return FileResponse(p)
    return {"ok": True, "corocoro": "¡Ajá, cómo andamos! 🤠 Voz digital del Llano"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    p = pathlib.Path("static/favicon.png")
    if p.exists():
        return FileResponse(p, media_type="image/png")
    return {"ok": False}

@app.get("/health")
async def health():
    return {"status":"ok", "casanare_api": settings.CASANARE_API, "telegram": bool(settings.TELEGRAM_TOKEN), "video": "moviepy + gTTS", "instagram": "DEMO / Graph API", "video_ia": bool(settings.PIAPI_API_KEY or settings.REPLICATE_API_KEY), "piapi": bool(settings.PIAPI_API_KEY)}

@app.post("/chat")
async def chat(inp: ChatIn):
    await registrar(inp)
    res = await agent_chat(inp.message)
    if res.get("contenido"):
        stats.registrar_evento("contenido")
    return {"corocoro": res["respuesta"], **res}

@app.get("/chat")
async def chat_get(q: str):
    await registrar(ChatIn(message=q, user_id="web"))
    res = await agent_chat(q)
    return {"corocoro": res["respuesta"], **res}

@app.get("/stats")
async def stats_public():
    return stats.resumen()

@app.get("/config")
async def config():
    return {
        "telegram": "https://t.me/" + os.getenv("TELEGRAM_USERNAME","Corocoro_casanare_bot").lstrip("@"),
        "tiktok_handle": os.getenv("TIKTOK_HANDLE",""),
        "tiktok_url": "https://www.tiktok.com/@/" + os.getenv("TIKTOK_HANDLE","").replace("@","") if os.getenv("TIKTOK_HANDLE","") else "",
        "instagram": os.getenv("INSTAGRAM_USER","").replace("@",""),
    }

@app.post("/contenido")
async def contenido(tema: str = Query(...), tipo: str="post"):
    from app.agent.tools import generar_contenido
    c = generar_contenido(tipo, tema, {"municipio":"Casanare"})
    post = generar_post_instagram(c["titulo"], c["guion"], {"municipio":"Casanare"})
    stats.registrar_evento("contenido")
    return {**c, "instagram": post}

@app.post("/video")
async def video(tema: str = Query(...), guion: str = Query(None)):
    if not guion:
        guion = f"¡Ajá, cómo andamos! 🤠 Venga le cuento sobre {tema} en Casanare. ¡Un plan que no se puede perder, de una!"
    res = await generar_video_corto(tema, guion)
    post = generar_post_instagram(tema, guion)
    stats.registrar_evento("video")
    return {"video": res, "instagram": post}

@app.post("/instagram")
async def instagram_post(caption: str, image_url: str = None):
    res = await publicar_instagram(caption, image_url)
    return res

@app.post("/video-ia")
async def video_ia(tema: str = Query(...), guion: str = Query(None)):
    if not guion:
        guion = f"¡Ajá, cómo andamos! Venga le cuento sobre {tema} en Casanare. ¡Un plan que no se puede perder, pues!"
    guion = guion[:300]  # corto para video
    res = await crear_video_ia(tema, guion)
    post = generar_post_instagram(tema, guion)
    stats.registrar_evento("video")
    return {"video_ia": res, "instagram": post}

@app.post("/video-auto")
async def video_auto():
    """La IA inventa TODO el contenido (idea, diálogo, escena) y arma el video con el avatar."""
    from app.agent.corocoro_agent import generar_script_video
    script = await generar_script_video()
    tema = script.get("tema") or "Casanare"
    dialogo = script.get("dialogo") or f"¡Ajá, cómo andamos! Venga le cuento sobre {tema}."
    res = await generar_video_corto(tema, dialogo)
    caption = (f"{script.get('gancho','')}\n\n{tema}\n\n"
               f"{script.get('hashtags','#Casanare #Llano #TikTok')}\n\n"
               "— Corocoro, la voz del Llano 🤠")[:1000]
    stats.registrar_evento("video")
    return {"ok": True, "script": script, "video": res, "caption": caption}

@app.post("/propuesta")
async def propuesta_manual():
    return await generar_propuesta_diaria()

@app.get("/propuesta")
async def propuesta_get():
    return await generar_propuesta_diaria()

@app.post("/avatar")
async def avatar(data: bytes = Body(...)):
    """Sube la foto oficial de la corocora (reemplaza static/corocoro.png)."""
    if len(data) < 100:
        return {"ok": False, "error": "Archivo muy pequeño"}
    try:
        from PIL import Image
        img = Image.open(__import__("io").BytesIO(data)).convert("RGBA")
        # Aplana la transparencia sobre blanco para que SIEMPRE se vea (evita fotos fantasma)
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        if max(img.size) > 1024:
            r = 1024 / max(img.size)
            bg = bg.resize((int(img.size[0]*r), int(img.size[1]*r)), Image.LANCZOS)
        buf = __import__("io").BytesIO()
        bg.convert("RGB").save(buf, "PNG")
        data = buf.getvalue()
    except Exception as e:
        return {"ok": False, "error": f"No es una imagen válida: {e}"}
    pathlib.Path("static/corocoro.png").write_bytes(data)
    return {"ok": True, "msg": "Foto de Corocoro actualizada. Ya se usa en el panel, videos y posts."}

@app.post("/objetivo/demo")
async def objetivo_demo(tipo: str = Query("video")):
    """Demo: marca un objetivo como realizado (video/post) pa' la presentación. La idea SOLO sube a las 5 AM."""
    if tipo not in ("video", "contenido"):
        return {"ok": False, "error": "tipo debe ser video o contenido (la idea sube sola a las 5 AM)"}
    stats.marcar_objetivo(tipo)
    return {"ok": True, "objetivos": (stats.resumen().get("objetivos") or {})}

@app.post("/propuesta/enviar")
async def propuesta_enviar():
    """Envía YA la propuesta del día al admin (igual que a las 5:00 am, sin marcar el objetivo)."""
    from app.services.scheduler import enviar_propuesta_admin
    ok = await enviar_propuesta_admin()  # marcar_objetivo=False: la idea sube solo a las 5 AM
    return {"ok": ok, "msg": "Propuesta enviada a tu Telegram (revisa el bot)."}

@app.post("/propuesta-video")
async def propuesta_video():
    """Propuesta del día + video de la corocora presentándola (para /propuesta y 5am)."""
    data = await generar_propuesta_diaria()
    p = data.get("propuesta", {})
    titulo = p.get("titulo") or "Emprendimiento del día"
    guion = (p.get("descripcion") or f"Idea de emprendimiento: {titulo}. {p.get('por_que','')}")[:280]
    res = await generar_video_corto(titulo, guion)
    cap = (f"🌅 ¡Buenos días Yeferson! 🤠 Emprendimiento del día:\n\n"
           f"💡 {titulo}\n\n{p.get('descripcion','')}\n\n"
           f"📈 Demanda: {p.get('demanda','')}\n\n{p.get('hashtags','')}")[:950]
    stats.registrar_evento("video")
    return {"ok": True, "propuesta": p, "video": res, "caption": cap}

@app.get("/video-ia/instruccion")
async def video_ia_help():
    from app.services.ai_video import instruccion
    return {"instruccion": instruccion()}

@app.post("/tts")
async def tts(text: str):
    path = await text_to_speech(text, "static/voz.mp3")
    return {"audio": path, "text": text}

doc_n = pathlib.Path("static/noticias.json")
def _leer_noticias():
    if doc_n.exists():
        try:
            return json.loads(doc_n.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

@app.get("/noticias")
async def noticias_get():
    return _leer_noticias()

@app.post("/noticias")
async def noticias_post(payload: dict = Body(...)):
    """El admin publica una noticia/evento del Llano desde Telegram."""
    texto = (payload.get("texto") or "").strip()
    if not texto:
        return {"ok": False, "error": "Texto requerido"}
    lis = _leer_noticias()
    lis.insert(0, {"id": int(time.time()), "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "texto": texto[:1000], "autor": (payload.get("autor") or "Admin")})
    doc_n.parent.mkdir(exist_ok=True)
    doc_n.write_text(json.dumps(lis[:30], ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "noticia": lis[0]}

@app.post("/crear-libre")
async def crear_libre(payload: dict = Body(...)):
    """La IA elige el tema y crea contenido (noticia/video/post) como influencer."""
    from app.agent.corocoro_agent import call_llm
    from app.services.propuestas import _extraer_json
    tipo = (payload.get("tipo") or "noticia").lower()
    if tipo not in ("video", "post", "noticia"):
        tipo = "noticia"
    system = (
        "Eres COROCORO, la influencer llanera (pájaro corocoro rojo, sombrero y poncho). "
        "Elige TÚ libremente un tema 100% real y de moda en Casanare/Colombia HOY "
        "(evento, negocio, comida, cabalgata, música llanera, turismo, clima, deportes, noticia del Llano). "
        "Con ese tema crea contenido tipo " + tipo.upper() + " de la corocora influencer. "
        "Devuelve SOLO JSON válido, sin texto extra. Ejemplo: "
        '{"tipo": "' + tipo + '", "tema": "tema elegido", "texto": "la noticia", '
        '"caption": "caption con emojis y hashtags", "motivo": "por que lo elegiste"}'
    )
    try:
        raw = await call_llm("Inventa un tema libre y crea ese contenido (sobre lo que quieras).", system=system, max_tokens=1200)
        data = _extraer_json(raw) or {}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if not data.get("tema"):
        return {"ok": False, "error": "La IA no respondió bien", "raw": raw[:300]}
    data.setdefault("tipo", tipo)
    return {"ok": True, "creacion": data}

@app.get("/metrics")
async def metrics():
    return stats.resumen()

# ===== Post de imagen (generado localmente, sin necesitar cuentas) =====
@app.post("/post")
async def post():
    """Genera la imagen del post (PIL local) a partir de la propuesta del día."""
    data = await generar_propuesta_diaria()
    p = data.get("propuesta", {})
    titulo = p.get("titulo") or "Post Corocoro"
    path_img = await _render_post_local(titulo, p)
    stats.registrar_evento("contenido")
    return {"ok": True, "imagen": path_img, "titulo": titulo,
            "caption": (p.get("caption_redes") or "")[:2150]}

async def _render_post_local(titulo: str, p: dict):
    from PIL import Image, ImageDraw, ImageFont
    import textwrap
    from app.services.imagen_ia import descargar_fondo
    W, H = 1080, 1350

    # 1) Fondo generado por IA (gratis). Si falla, usa degradado verde.
    base = None
    try:
        fondo_p = (
            "fondo vertical para post de emprendimiento colombiano, sabana llanera de Casanare "
            "al amanecer, cielo dorado y verde esmeralda, rio y ganado y vegetacion, "
            "estilo minimalista profesional, luz suave, zona central limpia y oscura para "
            "sobreponer texto, fotografia realista de alta calidad, sin texto, sin letras, sin personas"
        )
        fp = await descargar_fondo(fondo_p)
        base = Image.open(fp).convert("RGB").resize((W, H), Image.LANCZOS)
    except Exception as e:
        print("Fondo IA fallo, uso degradado:", e)
    if base is None:
        base = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(base)
        for y in range(H):
            t = y / H
            d.line([(0, y), (W, y)], fill=(int(7 - t*8), int(44 + t*40), int(32 + t*23)))
    draw = ImageDraw.Draw(base, "RGBA")
    GOLD = (255, 209, 102)
    GOLD_D = (209, 150, 43)
    CREAM = (239, 229, 203)

    # Velo oscuro suave + panel detrás del texto para legibilidad
    draw.rectangle([0, 0, W, H], fill=(7, 20, 15, 80))
    draw.rounded_rectangle([60, 692, 1020, 1134], radius=48,
                           fill=(6, 28, 20, 180), outline=(180, 140, 60, 210), width=3)
    draw.ellipse([800, -180, 1280, 300], outline=(209, 150, 43, 60), width=30)

    # --- Chip superior ---
    f_chip = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 32)
    chip_w = draw.textlength("IDEA DE EMPRENDIMIENTO", font=f_chip) + 90
    x0, y0, x1 = (W-chip_w)//2, 98, (W+chip_w)//2
    draw.rounded_rectangle([x0, y0, x1, y0+76], radius=38, fill=GOLD, outline=GOLD_D, width=3)
    dawg = draw.textlength("IDEA DE EMPRENDIMIENTO", font=f_chip)
    draw.text(((W-dawg)//2, y0+16), "IDEA DE EMPRENDIMIENTO", font=f_chip, fill=(14, 43, 32))
    draw.line([(150, y0+38), (x0-30, y0+38)], fill=(209, 150, 43, 200), width=3)
    draw.line([(x1+30, y0+38), (W-150, y0+38)], fill=(209, 150, 43, 200), width=3)

    # --- Avatar circular con anillo dorado + sombra ---
    cx, cy, r = 540, 462, 186
    draw.ellipse([cx-r-14, cy-r+16, cx+r+14, cy+r+16], fill=(0, 0, 0, 80))
    draw.ellipse([cx-r-4, cy-r-4, cx+r+4, cy+r+4], outline=GOLD, width=12)
    draw.ellipse([cx-r+6, cy-r+6, cx+r-6, cy+r-6], outline=(255, 255, 255, 70), width=2)
    inner = r - 18
    try:
        av = Image.open("static/corocoro.png").convert("RGBA")
        av = av.resize((inner*2, inner*2), Image.LANCZOS)
        mask = Image.new("L", (inner*2, inner*2), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, inner*2-1, inner*2-1], fill=255)
        base.paste(av, (cx-inner, cy-inner), mask)
    except Exception:
        draw.ellipse([cx-inner, cy-inner, cx+inner, cy+inner], fill=(14, 43, 32), outline=GOLD, width=5)

    # --- Título grande en mayúsculas ---
    f_title = None
    for fp in (r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\segoeuib.ttf"):
        try:
            f_title = ImageFont.truetype(fp, 78)
            break
        except Exception:
            continue
    if not f_title:
        f_title = ImageFont.load_default()
    def txt(xy, s, font, fill=GOLD):
        x, y = xy
        draw.text((x+4, y+4), s, font=font, fill=(0, 0, 0, 110))
        draw.text((x, y), s, font=font, fill=fill)
    ty = 726
    for ln in textwrap.wrap((titulo or "Post Corocoro").upper(), width=15)[:2]:
        w = draw.textlength(ln, font=f_title)
        txt(((W-w)//2, ty), ln, f_title); ty += 88
    # --- Divisor con rombo ---
    draw.line([(310, ty+8), (W-310, ty+8)], fill=GOLD_D+(140,), width=3)
    draw.polygon([(540, ty-8), (552, ty+8), (540, ty+24), (528, ty+8)], fill=GOLD)

    # --- Descripción (itálica crema) ---
    f_desc = None
    for fp in (r"C:\Windows\Fonts\segoeuii.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        try:
            f_desc = ImageFont.truetype(fp, 40)
            break
        except Exception:
            continue
    ty += 42
    for ln in textwrap.wrap((p.get("descripcion") or ""), width=36)[:3]:
        w = draw.textlength(ln, font=f_desc)
        draw.text(((W-w)//2, ty), ln, font=f_desc, fill=CREAM); ty += 52

    # --- Tarjeta de pasos ---
    pasos = [s.strip() for s in (p.get("pasos") or "").split(".") if s.strip()][:3]
    f_ct = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 30)
    f_c = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 30)
    card_top = ty + 30
    cfg_h = 66 + len(pasos)*48
    draw.rounded_rectangle([90, card_top, W-90, card_top+cfg_h], radius=40,
                           fill=(6, 32, 23, 220), outline=(255, 209, 102, 255), width=3)
    ctw = draw.textlength("3 PASOS PA' EMPEZAR HOY", font=f_ct)
    draw.text(((W-ctw)//2, card_top+18), "3 PASOS PA' EMPEZAR HOY", font=f_ct, fill=GOLD)
    yy = card_top + 82
    for st in pasos[:3]:
        draw.ellipse([130, yy+12, 142, yy+24], fill=GOLD)
        seg = textwrap.wrap(st, width=52)[:1]
        draw.text((170, yy), seg[0] if seg else st, font=f_c, fill=CREAM)
        yy += 48

    # --- Footer ---
    fy = card_top + cfg_h + 36
    draw.line([(150, fy), (W-150, fy)], fill=(255, 209, 102, 160), width=2)
    f_f1 = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)
    f_f2 = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
    t1 = "COROCORO DEL CASANARE"
    t2 = "@Corocoro_casanare_bot"
    w1 = draw.textlength(t1, font=f_f1); w2 = draw.textlength(t2, font=f_f2)
    draw.text(((W-w1)//2, fy+16), t1, font=f_f1, fill=GOLD)
    draw.text(((W-w2)//2, fy+66), t2, font=f_f2, fill=(199, 191, 168))

    out = "static/post_corocoro.png"
    base.save(out)
    return out

pathlib.Path("static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    try: start_scheduler()
    except: pass
