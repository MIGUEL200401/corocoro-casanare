import os, pathlib, httpx, re
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API = os.getenv("COROCORO_API","http://localhost:8000")
ADMIN_FILE = pathlib.Path(__file__).with_name("admin_id.txt")

if not TOKEN:
    print("Falta TELEGRAM_BOT_TOKEN en .env — consigue uno con @BotFather")
    raise SystemExit

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

def clean(t):
    # sin Markdown: quitamos asteriscos para que no se vean raro en Telegram
    return (t or "").replace("*", "")

def get_admin_id():
    if ADMIN_FILE.exists():
        txt = ADMIN_FILE.read_text(encoding="utf-8-sig", errors="ignore")
        for line in txt.splitlines():
            line = line.strip().lstrip("\ufeff").strip()
            if line:
                return line
    return os.getenv("ADMIN_CHAT_ID","").strip()

MUNICIPIOS = ["Yopal","Aguazul","Pore","Tauramena","Paz de Ariporo","Orocue","Monterrey","Trinidad","Nunchia","San Luis de Palenque"]

def botones_municipio():
    filas = []
    fila = []
    for m in MUNICIPIOS:
        fila.append(InlineKeyboardButton(m, callback_data="municipio:" + m))
        if len(fila) == 3:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila)
    return InlineKeyboardMarkup(filas)

def capturar_noticia(msg):
    """Si el admin pide crear video/post/noticia, devuelve (tipo, tema)."""
    m = re.search(
        r"(?:quiero|voy a|vamos a|hoy\s+voy a|hay que|necesito|puedes|quieres|te pido)\s+(?:crear|hacer|armar|generar|preparar|subir|publicar|inventar)\w*\s+(?:un|una|el|la|este)\s+(\w+)\s*(?:de|sobre|:|\-)?\s*(.*)$",
        msg, re.I)
    if m and m.group(1):
        palabra = m.group(1).lower()
        if re.search(r"video|reel|clip", palabra):
            tipo = "video"
        elif re.search(r"post|publicacion|imagen|historia|contenido", palabra):
            tipo = "post"
        elif re.search(r"noticia|info|evento|novedad|cosa", palabra):
            tipo = "noticia"
        else:
            return "", ""
        return tipo, m.group(2).strip()
    return "", ""

LIBRE = re.compile(
    r"sobre\s+lo\s+que\s+(?:quieras|quiera|tu\s+quieras)|lo\s+que\s+tu\s+quieras|t[uú]\s+decides|"
    r"eliges\s+t[uú]|elige\s+t[uú]|como\s+(?:quieras|t[uú])|inventa|sorpr[eé]ndeme|"
    r"algo\s+viral|algo\s+del\s+llano|algo\s+q\s+se\s+te\s+ocurra|a\s+tu\s+criterio|"
    r"deja\s+la\s+creatividad|tu\s+sabes|dame\s+una\s+idea", re.I)

def es_admin(user_id: str) -> bool:
    aid = get_admin_id()
    return bool(aid) and str(user_id) == str(aid)

async def enviar_chat(chat_id, ctx, msg, user_id, nombre=""):
    await ctx.bot.send_chat_action(chat_id, "typing")
    # ✨ Admin (Yeferson): modo creación -> muestra que va a crear para Instagram/TikTok
    if es_admin(user_id):
        tipo, tema = capturar_noticia(msg)
        if not tipo and LIBRE.search(msg):
            tipo = "noticia"
        if tipo:
            if LIBRE.search(msg + " " + tema):
                await ctx.bot.send_chat_action(chat_id, "typing")
                try:
                    async with httpx.AsyncClient(timeout=90) as c:
                        r = await c.post(f"{API}/crear-libre", json={"tipo": tipo})
                        r.raise_for_status()
                        j = r.json()
                    cc = j.get("creacion") or {}
                    if j.get("ok") and cc:
                        armar = {"video": "Voy a armar ese video", "post": "Voy a armar el post", "noticia": "Voy a armar esa noticia"}[tipo]
                        kb = None
                        if tipo == "post":
                            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Aprueba y dame la imagen", callback_data="admin_aprobar")]])
                        txt = (
                            f"🔥 Decidí yo hoy, Jefe {nombre}. {armar} sobre:\n\n"
                            f"⭐ {cc.get('tema','')}\n\n"
                            f"{cc.get('texto','')}\n\n"
                            f"📣 Por qué lo elegí: {cc.get('motivo','')}\n\n"
                            f"📱 Caption pa' redes:\n{cc.get('caption','')}"
                        )
                        if kb:
                            await ctx.bot.send_message(chat_id, clean(txt), reply_markup=kb)
                        else:
                            await ctx.bot.send_message(chat_id, clean(txt))
                        return
                except Exception as e:
                    await ctx.bot.send_message(chat_id, f"Uy Jefe, no alcancé a inventar ({e}).")
                    return
            txt = {
                "video": (f"🎬 ¡Listo Jefe! Hoy voy a crear ese video y lo subo a tus redes: Instagram y TikTok.\n\n"
                          f"📷 Tema: {tema or 'lo que hablamos'}\n"
                          "Déjame armarlo con toda la identidad llanera... 🔥"),
                "post": (f"📸 ¡Listo Jefe! Hoy voy a crear ese post y lo subo a tus redes: Instagram y TikTok.\n\n"
                         f"📷 Tema: {tema or 'lo que hablamos'}\n"
                         "Déjame armarlo con toda la identidad llanera... 🔥"),
                "noticia": (f"🗞️ ¡Listo Jefe! Hoy voy a armar esa noticia y creo el video/post pa' tus redes: Instagram y TikTok.\n\n"
                            f"📷 Tema: {tema or 'lo que hablamos'}\n"
                            "Déjame armarla con toda la identidad llanera... 🔥"),
            }[tipo]
            await ctx.bot.send_message(chat_id, txt)
            return
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.post(f"{API}/chat", json={"message": msg, "user_id": user_id, "nombre": nombre})
        j = r.json()
    resp = j.get("corocoro") or j.get("respuesta") or "¡Ajá! No pude consultar ahora, intenta de nuevo."
    # pedido de video: la IA genera todo y el bot envía el archivo mp4
    if j.get("intent") == "video":
        await ctx.bot.send_message(chat_id, clean(resp))
        await ctx.bot.send_message(chat_id, "⏳ Generando tu video (la corocoro inventa idea, diálogo y escena)...")
        try:
            async with httpx.AsyncClient(timeout=300) as c:
                rv = await c.post(f"{API}/video-auto")
                rv.raise_for_status()
                vj = rv.json()
                video_rel = (vj.get("video") or {}).get("video") or "static/corocoro_reel.mp4"
                vb = await c.get(f"{API}/static/{pathlib.Path(video_rel).name}")
            if vb.status_code == 200 and vb.content and len(vb.content) > 1000:
                cap = clean(vj.get("caption") or "🎬 Corocoro 🤠")[:1000]
                await ctx.bot.send_video(chat_id, vb.content, caption=cap)
                await ctx.bot.send_message(chat_id, "✨ Listo. Descárgalo y súbelo a TikTok cuando quieras. ¿Quieres otro?")
            else:
                await ctx.bot.send_message(chat_id, "Uy, no alcancé a terminar el video 😅 Intenta en un momento.")
        except Exception as e:
            await ctx.bot.send_message(chat_id, f"Uy, no alcancé a crear el video ({e}). Intenta en un momento.")
        return
    # Telegram limita a 4096 chars
    for i in range(0, len(resp), 4000):
        await ctx.bot.send_message(chat_id, clean(resp[i:i+4000]))
    # si hace falta el municipio, preguntamos con botones
    if "pregunta_municipio" in j.get("tool_results",{}).get("restaurantes",{}) or "pregunta_municipio" in j.get("tool_results",{}).get("hospedajes",{}):
        ctx.user_data["pedido"] = msg
        await ctx.bot.send_message(chat_id, "Toca el municipio y te llevo a Google Maps:", reply_markup=botones_municipio())
    # si hay contenido generado, mostrarlo
    if j.get("contenido"):
        cc = j["contenido"]
        await ctx.bot.send_message(chat_id,
            "Contenido generado\n\n"
            f"Titulo: {cc.get('titulo','')}\n"
            f"Guion: {cc.get('guion','')}\n\n"
            f"Caption:\n{cc.get('caption','')}\n\n"
            "Revisa y publica cuando quieras. Pilas!")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    # el PRIMERO que escriba /start queda como administrador (Yeferson)
    if not get_admin_id():
        ADMIN_FILE.write_text(uid, encoding="utf-8")
        print(f"ADMIN capturado: {uid} ({update.effective_user.first_name})")
        await update.message.reply_text(
            "Listo Yeferson, te guardé como administrador.\n"
            "Todos los días a las 5:00 AM te enviaré una idea nueva de emprendimiento que investigué en las redes, con tus botones de aprobar/descartar.")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Noticias", callback_data="noticias"), InlineKeyboardButton("Donde comer", callback_data="restaurantes")],
        [InlineKeyboardButton("Turismo", callback_data="lugares"), InlineKeyboardButton("Hospedaje", callback_data="hospedajes")],
        [InlineKeyboardButton("TikTok", callback_data="tiktok"), InlineKeyboardButton("Un plan recio", callback_data="plan_recio")]
    ])
    await update.message.reply_text(
        "¡Ajá, cómo andamos! Soy Corocoro, la voz digital del Llano.\n\n"
        "Puedo ayudarte a descubrir Casanare: noticias, eventos, restaurantes, hoteles y lugares turisticos.\n"
        "Venga, contame qué quieres conocer hoy, parce!",
        reply_markup=kb)
    if es_admin(str(update.effective_user.id)):
        await update.message.reply_text(
            "🔥 Oye Jefe (tú eres el administrador): dime qué quieres crear pa' tus redes, así → "
            "'hoy voy a crear un video de las Fiestas del Hato', o déjame decidir: "
            "'crea una noticia sobre lo que quieras' y yo escojo el tema del día pa' Instagram y TikTok.")
    for p in ["../avatar/corocoro.png","avatar/corocoro.png","corocoro-ia/avatar/corocoro.png","../backend/static/corocoro.png"]:
        if os.path.exists(p):
            try:
                await update.message.reply_photo(open(p, "rb"), caption="Mireme pues, con sombrero y poncho bien llanero!")
            except Exception:
                pass
            break

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    nombre = update.effective_user.first_name or ""
    try:
        await enviar_chat(update.effective_chat.id, ctx, msg, str(update.effective_user.id), nombre)
    except Exception as e:
        await update.message.reply_text(f"Uy, parce! No pude consultar ahora ({e}). Intenta en unos segundos.")

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    if q.data == "admin_aprobar":
        await q.edit_message_text("✅ Aprobado! Corocoro está diseñando el post... ⏳")
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(f"{API}/post")
                r.raise_for_status()
                j = r.json()
                ib = await c.get(f"{API}/static/{pathlib.Path(j['imagen']).name}")
            if ib.status_code == 200 and ib.content:
                await q.message.reply_photo(
                    ib.content,
                    caption=clean((j.get("caption") or "Post Corocoro 🤠"))[:950])
                await q.message.reply_text(
                    "✨ Post listo. Guárdalo desde aquí o retoca la portada a tu gusto en Canva. ")
            else:
                await q.message.reply_text("Uy, no encontré la imagen generada.")
        except Exception as e:
            await q.message.reply_text(f"Uy, falló el post ({e}).")
        return
    if q.data == "admin_rechazar":
        await q.edit_message_text("❌ Descartada. Mañana te investigo otra idea nueva y real.")
        return
    if q.data.startswith("municipio:"):
        mun = q.data.split(":", 1)[1]
        # usa la petición anterior ("pedido") y agrega el municipio elegido
        base = (ctx.user_data.get("pedido") or "quiero buscar restaurantes")
        nueva = f"{base} {mun}"
        await q.message.reply_text(f"Buscando en {mun}...")
        nombre = q.from_user.first_name or ""
        try:
            await enviar_chat(q.message.chat.id, ctx, nueva, str(q.from_user.id), nombre)
        except Exception as e:
            await q.message.reply_text(f"Uy, parce! No pude consultar ahora ({e}). Intenta en unos segundos.")
        return
    mapping = {
        "noticias": "Que paso hoy en Casanare?",
        "restaurantes": "Donde puedo comer carne llanera en Yopal?",
        "lugares": "Que lugares turisticos me recomiendas en Casanare?",
        "hospedajes": "Donde puedo hospedarme en Yopal?",
        "tiktok": "busca en TikTok Casanare turismo",
        "plan_recio": "Un plan recio"
    }
    msg = mapping.get(q.data, q.data)
    nombre = q.from_user.first_name or ""
    await q.message.reply_text(f"Buscando: {msg}")
    try:
        await enviar_chat(q.message.chat.id, ctx, msg, str(q.from_user.id), nombre)
    except Exception as e:
        await q.message.reply_text(f"Uy, parce! No pude consultar ahora ({e}). Intenta en unos segundos.")

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    aid = get_admin_id()
    await update.message.reply_text(f"Admin actual = {aid if aid else 'Ninguno (escribe la primera persona que haga /start)'}")

async def cmd_propuesta(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # solo el admin recibe la propuesta del día (prompt pa' IA de video + caption redes)
    if str(update.effective_user.id) != get_admin_id():
        await update.message.reply_text("Esta opción es solo para el administrador 😉")
        return
    await update.message.reply_text("🔍 Investigando las redes y armando el prompt de hoy... un momentico ⏳")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aprobar", callback_data="admin_aprobar"),
         InlineKeyboardButton("❌ Descartar", callback_data="admin_rechazar")]
    ])
    try:
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(f"{API}/propuesta")
            r.raise_for_status()
            j = r.json()
        p = j.get("propuesta") or {}
        if not p:
            await update.message.reply_text("Hoy no encontré idea 😅 Intenta más tarde.")
            return
        texto = (
            "🌅 ¡Buenos días, pariente! 🤠\n\n"
            "Hoy quiero publicar lo siguiente (según lo que está pasando en las redes):\n\n"
            f"💡 {p.get('titulo','')}\n\n"
            f"{p.get('descripcion','')}\n\n"
            f"🔥 Por qué: {p.get('por_que','')}\n"
            f"🚀 Para empezar hoy: {p.get('pasos','')}\n"
            f"📈 Demanda: {p.get('demanda','')}\n\n"
            "🎬 PROMPT PA' LA IA DE VIDEO (cópialo, pégalo en HeyGen/Runway/Kling):\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{p.get('prompt_video','')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📱 Caption pa' redes (Instagram/TikTok):\n"
            f"{p.get('caption_redes','')}\n\n"
            f"🔗 Fuente: {p.get('fuente','')}\n\n"
            "🎨 Diseña la portada con tu Canva Premium.\n\n"
            "¿Apruebas para publicarla?"
        )
        await update.message.reply_text(clean(texto), reply_markup=kb)
    except Exception as e:
        await update.message.reply_text(f"Uy, no pude armar la propuesta ({e}).")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("propuesta", cmd_propuesta))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Corocoro Telegram BOT iniciado - esperando mensajes...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()