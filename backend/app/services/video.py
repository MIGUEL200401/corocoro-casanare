import pathlib, textwrap, os
from app.services.tts import text_to_speech

# Generador de video corto tipo reel (9:16, 8-30s) con avatar + voz + captions.
# Usa moviepy 2.x + Pillow (texto dibujado en la imagen, sin ImageMagick).

_FONT_B = r"C:\Windows\Fonts\segoeuib.ttf"
_FONT_R = r"C:\Windows\Fonts\segoeui.ttf"
for _p in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\ariblk.ttf"]:
    if not pathlib.Path(_FONT_B).exists() and pathlib.Path(_p).exists():
        _FONT_B = _p
if not pathlib.Path(_FONT_R).exists():
    _FONT_R = "C:\Windows\Fonts\segoeui.ttf"


def _grabar_texto(draw, xy, texto, font, fill, shadow=True):
    x, y = xy
    if shadow:
        draw.text((x+3, y+3), texto, font=font, fill=(0,0,0,90))
    draw.text((x, y), texto, font=font, fill=fill)


def _make_frame(tema: str, guion: str, avatar_path: str):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 720, 1280
    # fondo con degradado llanero (crema -> dorado)
    base = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(base)
    for y in range(H):
        t = y / H
        r = int(254 - t*34); g = int(248 - t*56); b = int(225 - t*40)
        d.line([(0,y),(W,y)], fill=(r,g,b))
    draw = ImageDraw.Draw(base, "RGBA")

    # sombra bajo el avatar
    d.ellipse([140, 660, 580, 700], fill=(0,0,0,40))

    # avatar redondeado
    av = Image.open(avatar_path).convert("RGBA")
    size = 480
    av = av.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,size-1,size-1], radius=48, fill=255)
    av.putalpha(mask)
    base.paste(av, ( (W-size)//2, 120 ), av)

    # franja verde inferior (estilo marca)
    d.rectangle([0, H-96, W, H], fill=(88,204,2))
    d.rectangle([0, H-96, W, H-90], fill=(64,150,0))

    try:
        f_titulo = ImageFont.truetype(_FONT_B, 52)
        f_guion = ImageFont.truetype(_FONT_R, 30)
        f_pie = ImageFont.truetype(_FONT_B, 26)
    except Exception:
        f_titulo = f_guion = f_pie = ImageFont.load_default()

    # titulo grande (rojo llanero)
    lineas = textwrap.wrap(tema or "", width=24) or [""]
    ty = 700
    for ln in lineas[:2]:
        w = draw.textlength(ln, font=f_titulo)
        _grabar_texto(draw, ((W-w)//2, ty), ln, f_titulo, (183,28,28))
        ty += 62

    # guion (corto)
    ty += 12
    for ln in textwrap.wrap(guion or "", width=44)[:4]:
        w = draw.textlength(ln, font=f_guion)
        _grabar_texto(draw, ((W-w)//2, ty), ln, f_guion, (63,63,63))
        ty += 40

    # pie
    pie = "Corocoro del Casanare • Habla conmigo por Telegram"
    w = draw.textlength(pie, font=f_pie)
    _grabar_texto(draw, ((W-w)//2, H-64), pie, f_pie, (255,255,255), shadow=False)
    return base


async def generar_video_corto(tema: str, guion: str, avatar_path: str = "static/corocoro.png"):
    out_mp4 = "static/corocoro_reel.mp4"
    out_audio = "static/corocoro_voz.mp3"
    pathlib.Path("static").mkdir(exist_ok=True)

    # 1. Voz
    audio = await text_to_speech(guion or "", out_audio)
    if not audio or not pathlib.Path(audio).exists():
        pathlib.Path(out_audio).write_bytes(b"")

    # 2. Video real con moviepy 2 + Pillow
    try:
        import numpy as np
        from moviepy import ImageClip, AudioFileClip

        if not pathlib.Path(avatar_path).exists():
            for p in ["static/corocoro.png","avatar/corocoro.png","../avatar/corocoro.png"]:
                if pathlib.Path(p).exists():
                    avatar_path = p; break
            else:
                from PIL import Image
                img0 = Image.new("RGB", (480,480), (254,249,231))
                img0.save("static/corocoro.png")
                avatar_path = "static/corocoro.png"

        foto = _make_frame(tema, (guion or "")[:240], avatar_path)
        arr = np.asarray(foto)

        dur = 12
        audio_clip = None
        if pathlib.Path(out_audio).stat().st_size > 1000:
            audio_clip = AudioFileClip(out_audio)
            dur = max(8, min(audio_clip.duration, 30))

        clip = ImageClip(arr, duration=dur)
        if audio_clip:
            clip = clip.with_audio(audio_clip)
        clip.write_videofile(out_mp4, fps=24, codec="libx264", audio_codec="aac",
                             preset="medium", threads=2, logger=None)
        if audio_clip:
            audio_clip.close()
        return {"ok": True, "video": out_mp4, "audio": out_audio, "duracion": round(dur,1),
                "guion": guion, "modo": "moviepy", "formato": "720x1280 9:16"}

    except Exception as e:
        print("Video fallback:", repr(e)[:200])
        return {
            "ok": True, "video": None,
            "audio": out_audio if pathlib.Path(out_audio).exists() else None,
            "imagen": None, "guion": guion, "tema": tema, "modo": "DEMO",
            "error": repr(e)[:200],
            "nota": "Instala Pillow/moviepy bien o revisa el log.",
        }


def generar_post_instagram(tema: str, guion: str, datos: dict = None):
    datos = datos or {}
    hashtags = "#Casanare #Llano #Yopal #OrgulloCasanareño #PasoFino #TurismoCasanare #Colombia"
    if "gastron" in tema.lower() or "mamona" in tema.lower():
        hashtags += " #ComidaLlanera #Mamona"
    if "festival" in tema.lower() or "evento" in tema.lower():
        hashtags += " #EventosCasanare #CasanarePalpita"
    if "safari" in tema.lower() or "guanapalo" in tema.lower():
        hashtags += " #SafariLlanero #Naturaleza"
    caption = f"🤠 {tema}\n\n{guion}\n\n📍 {datos.get('municipio','Casanare')} | 🔗 {datos.get('url','')}\n\n{hashtags}\n\n— Corocoro, la voz digital del Llano"
    caption = caption[:2150]
    return {
        "titulo": tema,
        "caption": caption,
        "hashtags": hashtags,
        "imagen_sugerida": "Usa avatar corocoro.png + foto del lugar",
        "cta": "¿Te gustó? Habla con Corocoro por Telegram: @Corocoro_casanare_bot"
    }