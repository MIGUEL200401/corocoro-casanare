import json, pathlib, random, datetime
from app.agent import tools
from app.agent.corocoro_agent import call_llm

SYSTEM_PROPUESTA = """Eres COROCORO, la voz digital del Llano. Cada mañana investigas las redes (TikTok, noticias, tendencias en Colombia) y le propones a tu administrador una idea NUEVA de EMPRENDIMIENTO real para Casanare, distinta a la de ayer.
REGLAS DE REALIDAD (obligatorias):
- Solo ideas 100% aplicables HOY en Casanare/Colombia: ganadería, agro, turismo, gastronomía, música llanera, artesanías, fincas, comercio, economía digital, servicios para el campo.
- Inversión inicial baja (menos de 3 millones COP), que un emprendedor común pueda arrancar esta semana.
- Negocio real y viable con clientes reales; nada de ciencia ficción, cripto, farm fantasy ni ideas imposibles.
- Debe sonar a algo que se está viendo viral en redes y que le deje plata al negocio local.
Devuelve SOLO JSON válido, sin texto extra, sin comillas de marca:
{"titulo": "Nombre corto y llamativo del emprendimiento", "descripcion": "2-3 líneas: qué es y cómo se viraliza en redes", "por_que": "Por qué está funcionando (tendencias que lo respaldan)", "pasos": "3 pasos concretos y reales para empezar HOY (separados por punto)", "demanda": "Qué tan buscado está (ej: tendencia alta en TikTok, 50k+ vistas)", "fuente": "URL de una buena fuente", "hashtags": "#...", "prompt_video": "PROMPT listo de 250-350 caracteres para pegar en una IA de video (HeyGen/Runway/Kling/PiAPI): protagonista = COROCORO (pájaro corocoro rojo con sombrero y poncho llanero), estilo selfie de influencer conversando a cámara, formato vertical 9:16, describe escenario, qué dice, qué hace y el cierre", "caption_redes": "Texto con emojis + hashtags listo para publicar en Instagram y TikTok"}"""

FALLBACK_IDEAS = [
    {"titulo": "Mamona express a domicilio en Yopal",
     "descripcion": "Servicio de mamona al punto por encargo para domingos y eventos, pedidos por WhatsApp/TikTok, con toque de influencer probando cada corte.",
     "por_que": "La mamona es el plato insignia del Llano y cada vez se pide más a domicilio; los videos de comida llanera reciben miles de vistas.",
     "pasos": "1. Habla con 2 asaderos de Yopal y arma menú de domingo. 2. Crea cuenta comercial en Instagram/TikTok con videos de la preparación. 3. Lanza pedidos por WhatsApp con reserva de 1 día de anticipación.",
     "demanda": "Alta: búsquedas de 'mamona en Yopal' y comida llanera crecen en redes cada fin de semana.",
     "fuente": "https://www.tiktok.com/search?q=mamona%20llanera",
     "hashtags": "#Emprendimiento #Mamona #Yopal #ComidaLlanera",
     "prompt_video": "Video vertical 9:16 tipo selfie de influencer: COROCORO, un pájaro rojo con sombrero y poncho llanero, habla a cámara sonriendo frente a un asadero llanero bajo palma con humo de leña. Dice: '¡Ajá mi gente! La mamona no es carne, es cultura' mientras señala una mesa de madera con carne y metralleta, y cierra guiñando el ojo.",
     "caption_redes": "🤠 La mamona ya llega a tu casa en Yopal. ¿Este domingo reservas la tuya?\n🔥 Pedidos por WhatsApp, reserva con 1 día.\n\n#Mamona #Yopal #Casanare #ComidaLlanera #Emprendimiento #Llano"},
    {"titulo": "Safari llanero 4x4 + fotos con dron",
     "descripcion": "Ruta de avistamiento de fauna y paisajes en Guanapalo y sabana, con dron para fotos de recuerdo y video corto para cada turista.",
     "por_que": "El turismo de naturaleza y los videos aéreos están en crecimiento; los influencers viajan al Llano a crear contenido.",
     "pasos": "1. Alíate con un hato o guía local de Guanapalo. 2. Consigue o alquila un dron y define las rutas 4x4. 3. Publica 1 reel semanal mostrando las rutas y vende el paquete por WhatsApp.",
     "demanda": "Tendencia estable: 'safari llanero' y 'Guanapalo' son buscados todo el año.",
     "fuente": "https://www.google.com/maps/search/safari+Guanapalo+Casanare",
     "hashtags": "#Safari #Casanare #Turismo #Dron",
     "prompt_video": "Video vertical 9:16 estilo vlog de aventura: COROCORO, un pájaro corocoro rojo con sombrero y poncho, va en un 4x4 por la sabana de Casanare al amanecer, con ganado y niebla baja; se detiene, mira a cámara y dice 'Esto no lo ves en ninguna ciudad' mientras un dron sobrevuela el paisaje y cierra con el río al fondo.",
     "caption_redes": "🏞️ El Llano de verdad: safari 4x4, fauna y fotos con dron en Guanapalo.\n📸 Paquete con video aéreo de recuerdo.\n\n#SafariLlanero #Casanare #Naturaleza #Dron #Turismo"},
    {"titulo": "Aprende a tocar arpa y cuatro desde cero (online)",
     "descripcion": "Curso virtual en video corto para aprender joropo: arpa, cuatro y maracas, con retos semanales virales en TikTok.",
     "por_que": "La música llanera gusta en todo el país y a nadie le queda tiempo para clases presenciales; los tutoriales cortos se replican.",
     "pasos": "1. Graba 10 lecciones de 60 seg en tu celular. 2. Arma comunidad en TikTok/Instagram con el reto '#YoAprendoJoropo'. 3. Vende el curso digital completo con material (partituras, videos).",
     "demanda": "Media-alta: crece el interés por música tradicional y los retos culturales en TikTok.",
     "fuente": "https://www.tiktok.com/search?q=aprender+joropo",
     "hashtags": "#Joropo #ArpaLlanera #MúsicaLlanera #CursosOnline",
     "prompt_video": "Video vertical 9:16 tutorial de música: COROCORO, pájaro corocoro rojo salón llanero, toca un cuatro y canta una venao; mira a cámara y dice 'Pa' que aprendas joropo desde cero', muestra los acordes cerca a la cámara y cierra invitando al reto #YoAprendoJoropo.",
     "caption_redes": "🎶 ¿Sueñas con tocar el arpa o el cuatro? Empieza HOY online.\n🔥 Reto semanal #YoAprendoJoropo\n\n#Joropo #ArpaLlanera #MúsicaLlanera #CursosOnline"},
]

def _hoy():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).strftime("%Y-%m-%d")

def _sanit(s):
    return (s or "").replace("*", "").strip()

def _extraer_json(texto):
    if not texto:
        return None
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b > a:
        t = t[a:b+1]
    return json.loads(t)

async def generar_propuesta_diaria():
    fecha = _hoy()
    cache = pathlib.Path("static/propuesta_diaria.json")
    try:
        if cache.exists() and cache.read_text(encoding="utf-8").strip():
            j = json.loads(cache.read_text(encoding="utf-8"))
            if j.get("fecha") == fecha and j.get("propuesta"):
                return j
    except Exception:
        pass

    contexto = {}
    try:
        web = await tools.buscar_web("ideas de negocio y emprendimientos virales 2026 en redes sociales")
        contexto["web"] = web.get("results", [])[:5]
        contexto["answer"] = web.get("answer", "")
    except Exception:
        pass
    try:
        ttt = await tools.buscar_tiktok("ideas de emprendimiento negocio viral")
        contexto["tiktok"] = ttt.get("results", [])[:3]
    except Exception:
        pass
    try:
        n = await tools.buscar_noticias(q="emprendimiento economia negocio")
        contexto["noticias"] = n.get("datos", [])[:3]
    except Exception:
        pass

    p = None
    raw = await call_llm(
        "Esto encontré hoy investigando las redes:\n\n" + json.dumps(contexto, ensure_ascii=False, indent=1)[:2600]
        + "\n\nInventa AHORA la idea de emprendimiento del día, una distinta a la de ayer.",
        system=SYSTEM_PROPUESTA, max_tokens=1200,
    )
    if raw:
        try:
            j_idea = _extraer_json(raw)
            if j_idea and j_idea.get("titulo"):
                p = {k: _sanit(j_idea.get(k)) for k in ("titulo", "descripcion", "por_que", "pasos", "demanda", "fuente", "hashtags", "prompt_video", "caption_redes")}
                p["prompt_video"] = p.get("prompt_video", "")[:450]
                p["caption_redes"] = p.get("caption_redes", "")[:500]
        except Exception:
            pass

    if not p:
        p = dict(random.choice(FALLBACK_IDEAS))
        p = {k: _sanit(v) for k, v in p.items()}

    data = {"ok": True, "fecha": fecha, "propuesta": p}
    try:
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return data