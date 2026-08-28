import re, json, asyncio
from app.agent.prompts import SYSTEM_PROMPT
from app.agent import tools
from app.config import settings

# LLM abstraction: tries Groq (con reintentos) -> OpenAI -> fallback rule-based
import pathlib as _pathlib

def _log_llm(tag, txt):
    try:
        p = _pathlib.Path("static/llm.log")
        p.parent.mkdir(exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(f"[{tag}] {txt}\n")
    except Exception:
        pass

async def call_llm(prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 700) -> str:
    if settings.GROQ_API_KEY:
        import httpx, asyncio
        for intento in range(3):
            try:
                async with httpx.AsyncClient(timeout=90) as c:
                    r = await c.post("https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type":"application/json"},
                        json={"model": settings.GROQ_MODEL or "openai/gpt-oss-20b",
                              "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
                              "temperature":0.7,"max_tokens":max_tokens})
                    if r.status_code==200:
                        contenido = r.json()["choices"][0]["message"]["content"]
                        # modelos de razonamiento pueden gastar tokens en "reasoning" y dejar el content corto
                        if contenido:
                            return contenido
                    _log_llm(f"groq-{intento}", f"{r.status_code} {r.text[:200]}")
                    if r.status_code==429:
                        await asyncio.sleep(1.5)
            except Exception as e:
                _log_llm(f"groq-err-{intento}", repr(e))
                await asyncio.sleep(1)
    if settings.OPENAI_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=45) as c:
                r = await c.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type":"application/json"},
                    json={"model":"gpt-4o-mini","messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1200})
                if r.status_code==200:
                    return r.json()["choices"][0]["message"]["content"]
                _log_llm("openai", f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            _log_llm("openai-err", repr(e))
    return ""  # fallback

SCRIPT_SYSTEM = """Eres el guionista de COROCORO, la influencer llanera (un pájaro corocoro rojo con sombrero y poncho).
Debes crear TÚ todo el contenido del video, sin que el usuario te dé el tema: idea original, situación, diálogo, acciones, escena y final.
Corocoro es un creador de contenido / influencer del Casanare: carismática, divertida, espontánea y cercana. Habla a cámara como en selfie/vlog, mirando a sus seguidores.
Temas: Casanare, cultura llanera, costumbres, comida (mamona, arepas), humor, lugares, personajes y situaciones cotidianas que puedan ser virales en TikTok.
Estilo: formato vertical 9:16, ritmo rápido, gancho desde los primeros segundos, nada comercial ni artificial. Cada video debe ser una idea NUEVA y original.
Devuelve SOLO JSON válido (sin texto extra, sin comillas de marca):
{"tema": "Título corto del video", "gancho": "Frase de los primeros segundos para enganchar", "dialogo": "Lo que Corocoro dice mirando a cámara (máximo 220 caracteres, coloquial)", "escena": "Descripción del escenario/fondo (ej: frente a un hato, mercado de Yopal, un caño)", "hashtags": "#Casanare #Llano #TikTok ..."}"""

VIDEO_IDEAS = [
    {"tema":"El secreto de la mejor mamona de Yopal","gancho":"¡Pilas! Que nadie se quede con la mamona fría.","dialogo":"¡Ajá, cómo andamos! Latas, la mamona no es solo carne: es cultura. Aquí en Yopal la hacen con leña, paciencia y mucho corazón. Venga a que le muestre cómo se hace de verdad.","escena":"Asadero llanero bajo palma, humo de leña, mesas de madera y casco de yegua colgado.","hashtags":"#Casanare #Mamona #Yopal #Llano #ComidaLlanera"},
    {"tema":"Así amanece en la sabana","gancho":"Esto no se ve en ningún lado del mundo.","dialogo":"¡Buenos días! A las 5 de la mañana la sabana despierta con neblina y el canto del corocoro. Aquí el que madruga, de verdad, se gana el mejor paisaje.","escena":"Amanecer dorado en sabana abierta, neblina baja, ganado pastando a lo lejos.","hashtags":"#Sabana #Amanecer #Casanare #Naturaleza"},
    {"tema":"Sobreviviendo a la temporada de calor","gancho":"¿Quién más ya está achicharradito?","dialogo":"¡De una! 40 grados a la sombra y el que diga que no es de aquí, que se aguante. Limonada, sombrero y el río rico. Eso me da el aguante pa' contarle más del llano.","escena":"Paisaje soleado, sombrero llanero en primer plano, río cristalino al fondo.","hashtags":"#Calor #Casanare #Verano #Llano"},
]


async def generar_script_video() -> dict:
    if settings.GROQ_API_KEY or settings.OPENAI_API_KEY:
        raw = await call_llm("Inventa AHORA una idea nueva y original para un video de la corocora influencer en TikTok (puede ser un lugar, comida, costumbre o situación graciosa del Casanare).", system=SCRIPT_SYSTEM, max_tokens=1200)
        try:
            txt = raw.strip()
            if txt.startswith("```"):
                txt = txt.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            a, b = txt.find("{"), txt.rfind("}")
            if a != -1 and b > a:
                txt = txt[a:b+1]
            j = json.loads(txt)
            for k in ("tema","gancho","dialogo","escena","hashtags"):
                j[k] = str(j.get(k,""))[:240]
            if j.get("tema"):
                return j
        except Exception:
            pass
    import random
    return dict(random.choice(VIDEO_IDEAS))

def detect_intent(text: str) -> str:
    import unicodedata
    def n(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
    t=n(text)
    if any(k in t for k in ["quiero un video","hazme un video","haz un video","crea un video","crear un video","genera un video","generar un video","un video pa","un video para","deja un video","reel","video de la corocora","video corocoro"]): return "video"
    if any(k in t for k in ["tiktok","tik tok","video corto"]): return "tiktok"
    if any(k in t for k in ["plan recio","que ocasion","ocasion","itinerario","aguazul 4","4 dias","cuantos dias","visitar aguazul"]): return "itinerario"
    if any(k in t for k in ["plan","itinerario"]): return "itinerario"
    if any(k in t for k in ["noticia","que paso","hoy en casanare","actualidad"]): return "noticias"
    if any(k in t for k in ["evento","fin de semana","sabado","domingo","festival","palpita"]): return "eventos"
    if any(k in t for k in ["comer","comida","restaurante","mamona","lechona","tamal","carne","parrilla","pizza","hamburguesa","pollo","asado","sancocho","pescado","donde como","hambre"]): return "restaurantes"
    if any(k in t for k in ["dormir","hotel","hospedaje","hospedarme","alojamiento","alojarme","quedarme","donde quedarme","donde puedo quedar"]): return "hospedajes"
    if any(k in t for k in ["visitar","lugar","turismo","conocer","finca","hato","safari","rio","naturaleza","paseo","banarme","diferente","distinto","aventura","que hacer","puedo hacer","quiero hacer","hacer hoy","hacer manana"]): return "lugares"
    if any(k in t for k in ["contacto","telegram","contactar","hablar con"]): return "general"
    if "quiero ir" in t or "a donde voy" in t: return "lugares"
    return "general"

async def agent_chat(user_msg: str, history: list = None):
    intent = detect_intent(user_msg)
    tool_results = {}
    fuentes = []

    # DECISION: qué herramienta usar
    if intent=="video":
        tool_results["video"] = {"auto": True}
    elif intent=="noticias":
        data = await tools.buscar_noticias(q="")
        if not data.get("datos"):
            data = await tools.buscar_web(user_msg)
        # si filtro no dio, trae todas
        if not data.get("datos"):
            data = await tools.buscar_noticias(q="")
        tool_results["noticias"]= data
        fuentes += [d.get("url") for d in data.get("datos",[])[:3] if d.get("url")]
    elif intent=="restaurantes":
        qlow = user_msg.lower()
        # Si es vago: "quiero comida" / "quiero comer" sin tipo -> preguntar
        vago = qlow.strip() in ["quiero comida","quiero comer","tengo hambre","quiero comer algo","donde comer"] or (len(qlow.split())<=3 and not any(k in qlow for k in ["pizza","mamona","carne","parrilla","tamal","lechona","hamburguesa","pollo","sushi","asadero"]))
        if vago:
            tool_results["restaurantes"] = {"pregunta": True}
            # no busca aún, responde preguntando
        else:
            muni = tools.detectar_municipio(qlow)
            # tipos clásicos que tenemos verificados en la base local
            tipos_local = {"pollo": ["pollo"],
                           "mamona": ["mamona","mamantona","asadero"],
                           "carne": ["carne","parrilla","choncho","yopo"],
                           "tamal": ["tamal"],
                           "lechona": ["lechona"]}
            tipo_pedido = None
            for label, keys in tipos_local.items():
                if any(k in qlow for k in keys):
                    tipo_pedido = label
                    break
            if tipo_pedido is None and any(k in qlow for k in ["pizza","hamburguesa","sushi","pescado","mariscos","arepa","empanada","perro","salchipapa","alitas","pastas"]):
                tipo_pedido = next(k for k in ["pizza","hamburguesa","sushi","pescado","mariscos","arepa","empanada","perro","salchipapa","alitas","pastas"] if k in qlow)
            if tipo_pedido is None:
                tipo_pedido = "restaurantes"
            # negocio real SIEMPRE se resuelve por Google Maps (empresas existentes)
            # primero intenta base local para los clásicos llaneros en Yopal
            if tipo_pedido in ["mamona","carne","tamal","lechona"] and (muni is None or muni=="yopal"):
                data = await tools.buscar_restaurantes(q="", municipio="Yopal")
                if data.get("datos"):
                    filtrados = [d for d in data["datos"] if any(v in (d.get("nombre","")+d.get("tipo","")).lower() for v in tipos_local[tipo_pedido])]
                    if filtrados:
                        data["datos"] = sorted(filtrados, key=lambda x: x.get("calificacion",0), reverse=True)
                        data["maps"] = tools.maps_url(f"{tipo_pedido} {muni or 'Yopal'} Casanare")
                        tool_results["restaurantes"] = data
                        fuentes += [d.get("url") for d in data["datos"][:3] if d.get("url")]
            if "restaurantes" not in tool_results:
                if muni is None:
                    tool_results["restaurantes"] = {"pregunta_municipio": True, "pedido": user_msg, "pedido_tipo": tipo_pedido}
                else:
                    query_maps = f"{tipo_pedido} {muni} Casanare"
                    tool_results["restaurantes"] = {"maps": tools.maps_url(query_maps), "pedido_tipo": tipo_pedido, "municipio": muni}
    elif intent=="hospedajes":
        muni = tools.detectar_municipio(user_msg.lower())
        if muni is None:
            tool_results["hospedajes"] = {"pregunta_municipio": True, "pedido": user_msg, "pedido_tipo": "hospedajes"}
        else:
            data = await tools.buscar_hospedajes(q="", municipio=muni)
            if data.get("datos"):
                data["maps"] = tools.maps_url(f"hospedajes {muni} Casanare")
                tool_results["hospedajes"] = data
            else:
                tool_results["hospedajes"] = {"maps": tools.maps_url(f"hospedajes {muni} Casanare"), "pedido_tipo": "hospedajes", "municipio": muni}
    elif intent=="tiktok":
        data = await tools.buscar_tiktok(user_msg)
        tool_results["tiktok"]=data
        fuentes += [r.get("url") for r in data.get("results",[])[:2] if r.get("url")]
    elif intent=="itinerario":
        # si solo dice "plan recio" sin detalle -> pregunta ocasión
        if user_msg.lower().strip() in ["un plan recio","plan recio","plan","quiero un plan recio"]:
            tool_results["itinerario"] = {"pregunta": True}
        else:
            import re
            dias = 4
            m = re.search(r"(\d+)\s*dias", user_msg.lower())
            if m: dias = int(m.group(1))
            muni = "Aguazul" if "aguazul" in user_msg.lower() else "Casanare"
            lugares = await tools.buscar_lugares(q=muni)
            if not lugares.get("datos"):
                lugares = await tools.buscar_lugares(q="")
            noticias = await tools.buscar_noticias(q=muni)
            tool_results["itinerario"] = {"dias": dias, "municipio": muni, "lugares": lugares, "noticias": noticias}
    elif intent=="lugares" or intent=="eventos":
        # Detecta municipio mencionado (Pore, Monterrey, etc)
        import unicodedata
        def nrm(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c)!='Mn')
        qn = nrm(user_msg)
        municipios = ["pore","yopal","aguazul","monterrey","tauramena","mani","orocue","paz de ariporo","nunchia","trinidad","san luis"]
        muni_detect = next((m for m in municipios if m in qn), None)
        qlow2 = user_msg.lower()
        is_rio = "rio" in qlow2 or "río" in qlow2
        if muni_detect:
            # busca primero en DB local, si no hay usa web
            data = await tools.buscar_lugares(q=muni_detect)
            if not data.get("datos"):
                web = await tools.buscar_web(user_msg + " Casanare turismo")
                if web.get("results"):
                    tool_results["lugares"]=web
                    fuentes += [r.get("url") for r in web["results"][:2] if r.get("url")]
                else:
                    data = await tools.buscar_lugares(q="")
                    tool_results["lugares"]=data
            else:
                tool_results["lugares"]=data
        elif is_rio:
            web = await tools.buscar_web(user_msg + " Casanare rio balneario")
            if web.get("results"):
                tool_results["lugares"]=web
                fuentes += [r.get("url") for r in web["results"][:2] if r.get("url")]
            else:
                data = await tools.buscar_lugares(q="rio")
                tool_results["lugares"]=data
        else:
            data = await tools.buscar_lugares(q="")
            if not data.get("datos"):
                data = await tools.buscar_todo(q="")
            tool_results["lugares"]=data
        if intent=="eventos":
            n = await tools.buscar_noticias(q="")
            tool_results["eventos_noticia"]=n
            fuentes += [d.get("url") for d in n.get("datos",[])[:2] if d.get("url")]
    elif intent=="general":
        data = await tools.buscar_todo(q=user_msg)
        tool_results["general"]=data

    # Generación de respuesta con LLM o fallback
    context = json.dumps(tool_results, ensure_ascii=False, indent=2)[:3000]
    prompt = f"""Usuario dice: "{user_msg}"
Intención detectada: {intent}
Datos encontrados (JSON): {context}

Responde como COROCORO:
- Si la pregunta NO es de Casanare ni hay datos útiles arriba, respóndela con tu propio conocimiento (eres una IA general). Ejemplos: cultura general, historia, cómo hacer algo, definiciones, recomendaciones.
- Si es de Casanare, usa SOLO los datos del JSON (son reales). Muestra las opciones con su URL.
- Si el JSON tiene un campo "maps", incluye en tu respuesta: "Te llevé a Google Maps (negocios reales): [ese enlace maps]".
- Si "pregunta_municipio" aparece, pregunta amable en qué municipio quiere buscar.
- Respuesta corta (3-5 líneas) y siempre ofrece un siguiente paso.
"""
    llm_resp = await call_llm(prompt) if intent != "video" else ""
    if llm_resp:
        respuesta = llm_resp
    else:
        # fallback rule-based chimba (siempre con sabor llanero)
        respuesta = fallback_response(intent, user_msg, tool_results)
        import random as _rnd
        abrir = ["¡Pilas, parce!", "¡Aja, qué más!", "¡De una!", "¡Mi pariente!", "¡Pues mire!"]
        if not any(w in respuesta.lower() for w in ["parce", "pariente", "pilas", "de una", "llano", "cómo andamos", "qué más", "venga le cuento"]):
            respuesta = _rnd.choice(abrir) + " " + respuesta

    # pedir video = respuesta rápida + bandera para que el bot lo genere y envíe
    if intent == "video":
        respuesta = "🎬 ¡De una, parce! Ya estoy armando tu video del Casanare: la corocora inventa la idea, el diálogo y la escena. Dame un momentico..."

    # añade fuentes
    if fuentes:
        respuesta += "\n\n🔗 *Fuentes:* " + " | ".join(fuentes[:3])

    # si es contenido, añade generación
    contenido = None
    if intent=="contenido" or "hazme" in user_msg.lower():
        # usar primer dato disponible
        first = None
        for v in tool_results.values():
            if isinstance(v, dict) and v.get("datos"):
                first = v["datos"][0]; break
        if first:
            contenido = tools.generar_contenido("post", first.get("titulo") or first.get("nombre") or user_msg[:30], first)

    return {"respuesta": respuesta, "intent": intent, "tool_results": tool_results, "contenido": contenido, "fuentes": fuentes}

def fallback_response(intent, msg, data):
    # Todas cortas: "te podría interesar esto" + "quieres saber más?"
    if intent=="tiktok":
        res = data.get("tiktok",{}).get("results",[])[:1]
        if not res: return "🔍 Te podría interesar esto — TikTok Casanare\n🔗 https://www.tiktok.com/search?q=Casanare\n\n¿Quieres ver videos de joropo o turismo?"
        return f"🔥 Te podría interesar esto:\n• {res[0].get('title','Video')[:55]}\n🔗 {res[0].get('url','')}\n\n¿Quieres ver más de TikTok Casanare?"
    if intent=="noticias":
        datos = data.get("noticias",{}).get("datos",[])[:1]
        if not datos: return "📰 No hay noticias ahora."
        d=datos[0]
        return f"📰 Te podría interesar esto:\n• {d['titulo'][:65]}\n🔗 {d['url']}\n\n¿Quieres ver otra noticia?"
    if intent=="restaurantes":
        r = data.get("restaurantes",{})
        if r.get("pregunta"):
            return "¿Qué te provoca? Mamona, pizza, pollo...\nEj: Quiero pizza en Yopal, quiero mamona"
        if r.get("pregunta_municipio"):
            return "¿En qué municipio? (ej: Yopal, Aguazul, Pore, Tauramena)\nTe llevo directo a Google Maps con negocios reales."
        if r.get("maps"):
            mapa = r.get("maps")
            if r.get("datos"):
                d = r["datos"][0]
                return f"🍽️ Te podría interesar esto:\n• {d['nombre']} — {d['tipo'][:25]}\n🔗 {d.get('url')}\n\n📍 Negocios reales en Google Maps:\n🔗 {mapa}\n\n¿Te sirvió? Busco otro municipio si quieres."
            tipo = r.get("pedido_tipo","negocio") or "negocio"
            mun = r.get("municipio","Casanare")
            return f"🍽️ Te podría interesar esto:\n• {tipo.capitalize()} en {mun.capitalize()}\n\n📍 Te llevé a Google Maps (solo negocios reales y verificados):\n🔗 {mapa}\n\n¿Quieres verlo en otro municipio?"
        if "results" in r:
            res = r["results"][0]
            return f"🍽️ Te podría interesar esto:\n• {res.get('title','Lugar')[:50]}\n🔗 {res.get('url','')}\n\n¿Quieres ver otro restaurante?"
        datos = r.get("datos",[])[:1]
        if not datos: return "🍽️ Prueba: mamona, pizza o pollo."
        d=datos[0]
        return f"🍽️ Te podría interesar esto:\n• {d['nombre']} — {d['tipo'][:25]}\n🔗 {d['url']}\n\n¿Quieres ver otro lugar para comer?"
    if intent=="hospedajes":
        r = data.get("hospedajes",{})
        if r.get("pregunta_municipio"):
            return "¿En qué municipio? (ej: Yopal, Aguazul, Pore, Tauramena)\nTe llevo a Google Maps con hospedajes reales."
        if r.get("maps"):
            mapa = r.get("maps")
            mun = r.get("municipio","Casanare")
            if r.get("datos"):
                d = r["datos"][0]
                return f"🏨 Te podría interesar esto:\n• {d['nombre']}\n🔗 {d['url']}\n\n📍 Más hospedajes reales en Google Maps:\n🔗 {mapa}\n\n¿Quieres verlo en otro municipio?"
            return f"🏨 Hospedajes en {mun.capitalize()}:\n📍 Te llevé a Google Maps (solo hospedajes reales y verificados):\n🔗 {mapa}\n\n¿Quieres otro municipio?"
        datos = r.get("datos",[])[:1]
        if not datos: return "🏨 No tengo hospedajes verificados ahora. ¿Buscamos juntos en Google Maps?"
        d=datos[0]
        return f"🏨 Te podría interesar esto:\n• {d['nombre']}\n🔗 {d['url']}\n\n¿Quieres ver el detalle o en otro municipio?"
    if intent=="itinerario":
        if data.get("itinerario",{}).get("pregunta"):
            return "🤠 ¿Qué ocasión?\n1️⃣ Aventura 2️⃣ Familia 3️⃣ Romance 4️⃣ Cultura\nEj: *plan aventura 2 días*"
        info = data.get("itinerario",{})
        muni = info.get("municipio","Aguazul")
        lugares = info.get("lugares",{}).get("datos",[])[:1]
        d=lugares[0] if lugares else {"nombre":"Pore colonial","tipo":"Cultura"}
        return f"🗺️ Te podría interesar esto:\n• {d['nombre']} en {muni}\n🔗 {d.get('url','')}\n\n¿Quieres que arme tu plan completo con hoteles?"
    if intent in ["lugares","eventos"]:
        if "results" in data.get("lugares",{}):
            r=data["lugares"]["results"][0]
            return f"🏞️ Te podría interesar esto:\n• {r.get('title','Río')[:50]}\n🔗 {r.get('url','')}\n\n¿Quieres ver otro río/lugar?"
        datos = data.get("lugares",{}).get("datos",[])[:1] or []
        if not datos: return "🏞️ Te podría interesar: Guanapalo (safari).\n¿Quieres ver otro?"
        d=datos[0]
        return f"🏞️ Te podría interesar esto:\n• {d['nombre']} ({d['municipio']})\n🔗 {d['url']}\n\n¿Quieres ver otro lugar?"
    # general
    return "¡Ajá, mi gente! 🤠 Soy *Corocoro, la voz digital del Llano*. Puedo ayudarte con:\n• 📰 Noticias de Casanare\n• 🍽️ Restaurantes\n• 🏨 Hospedajes\n• 🏞️ Lugares turísticos y eventos\n• 🎬 Generar posts/videos\n\nEjemplos:\n- '¿Qué puedo hacer este fin de semana en Yopal?'\n- '¿Dónde puedo comer mamona?'\n- 'Hazme un post sobre ese lugar'\n\n¡Venga, dime qué quieres conocer hoy!"
