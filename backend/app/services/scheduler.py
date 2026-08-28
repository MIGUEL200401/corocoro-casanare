from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.agent.corocoro_agent import agent_chat
import datetime, json, pathlib, os
scheduler = AsyncIOScheduler()

def get_admin_chat_id():
    admin = os.getenv("ADMIN_CHAT_ID","").strip()
    if admin:
        return admin
    for p in [pathlib.Path("admin_id.txt"),
              pathlib.Path("../../telegram_bot/admin_id.txt"),
              pathlib.Path("../telegram_bot/admin_id.txt")]:
        if p.exists():
            txt = p.read_text(encoding="utf-8-sig", errors="ignore")
            for linea in txt.splitlines():
                linea = linea.strip().lstrip("\ufeff").strip()
                if linea:
                    return linea
    return ""

async def enviar_propuesta_admin(marcar_objetivo: bool = False):
    from app.services.propuestas import generar_propuesta_diaria
    data = await generar_propuesta_diaria()
    p = data.get("propuesta", {})
    pathlib.Path("static/propuesta_diaria.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    admin_id = get_admin_chat_id()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not (admin_id and token and p):
        print("⚠️ Propuesta lista pero sin admin/token para enviar")
        return False
    def limpio(s): return (s or "").replace("*", " ")
    texto = (
        "🌅 ¡Buenos días Yeferson! 🤠\n\n"
        "💥 HOY voy a crear contenido pa' tus redes y quiero que TÚ me digas sobre qué.\n"
        "Puedes pedirme por ejemplo: 'crea una noticia sobre lo que quieras' y yo misma decido el tema del día. 🔥\n\n"
        "Mientras tanto, esta es la idea de EMPRENDIMIENTO que investigué en las redes:\n\n"
        f"💡 {limpio(p.get('titulo'))}\n\n"
        f"{limpio(p.get('descripcion'))}\n\n"
        f"🔥 Por qué: {limpio(p.get('por_que'))}\n"
        f"🚀 Para empezar hoy: {limpio(p.get('pasos'))}\n"
        f"📈 Demanda: {limpio(p.get('demanda'))}\n\n"
        "🎬 PROMPT PA' LA IA DE VIDEO (cópialo, pégalo en HeyGen/Runway/Kling):\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{limpio(p.get('prompt_video'))}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 Caption pa' redes (Instagram/TikTok):\n"
        f"{limpio(p.get('caption_redes'))}\n\n"
        f"🔗 Fuente: {limpio(p.get('fuente'))}\n\n"
        "🎨 Diseña la portada con tu Canva Premium (ya la tienes).\n\n"
        "¿Apruebas para publicarla?"
    )
    kb = {"inline_keyboard": [[
        {"text": "✅ Aprobar", "callback_data": "admin_aprobar"},
        {"text": "❌ Descartar", "callback_data": "admin_rechazar"}
    ]]}
    import httpx
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": admin_id, "text": texto, "reply_markup": kb})
    if r.status_code != 200:
        print("⚠️ Telegram rechazó la propuesta:", r.text[:200])
        return False
    print(f"✅ Propuesta enviada: {p.get('titulo')}")
    # la idea del día SOLO se marca cuando es la 5:00 am (job diario), no por pedidos manuales
    if marcar_objetivo and p.get("titulo"):
        from app.services import stats
        stats.registrar_propuesta(p.get("titulo", ""))
    return True


async def job_diario():
    print(f"[{datetime.datetime.now()}] 🤠 Corocoro 5am: investigando idea de emprendimiento en redes...")
    try:
        await enviar_propuesta_admin(marcar_objetivo=True)
    except Exception as e:
        print("auto emprendimiento error", e)

def start_scheduler():
    scheduler.add_job(job_diario, 'cron', hour=5, minute=0)  # 05:00 para Yeferson
    scheduler.start()
    print("⏰ Scheduler Corocoro 05:00 diario (emprendimiento) para admin")
