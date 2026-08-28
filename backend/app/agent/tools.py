import httpx, asyncio, os
from app.config import settings

CASANARE = settings.CASANARE_API.rstrip("/")

MUNICIPIOS = ["yopal","aguazul","pore","tauramena","monterrey","paz de ariporo","orocue",
              "mani","trinidad","nunchia","san luis de palenque","sabanalarga","tamara"]

def maps_url(query: str) -> str:
    q = " ".join(str(query).split())
    import urllib.parse
    return "https://www.google.com/maps/search/" + urllib.parse.quote(q)

def detectar_municipio(texto: str):
    import unicodedata
    def n(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
    t = n(texto)
    for mun in MUNICIPIOS:
        if mun in t:
            return mun
    return None

async def buscar_noticias(q: str = "", municipio: str = ""):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{CASANARE}/noticias", params={"q": q, "municipio": municipio})
        return r.json() if r.status_code==200 else {"error": r.text}

async def buscar_restaurantes(q: str = "", municipio: str = "Yopal"):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{CASANARE}/restaurantes", params={"q": q, "municipio": municipio})
        return r.json() if r.status_code==200 else {"error": r.text}

async def buscar_hospedajes(q: str = "", municipio: str = "Yopal"):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{CASANARE}/hospedajes", params={"q": q, "municipio": municipio})
        return r.json() if r.status_code==200 else {"error": r.text}

async def buscar_lugares(q: str = "", municipio: str = ""):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{CASANARE}/lugares-turisticos", params={"q": q, "municipio": municipio})
        return r.json() if r.status_code==200 else {"error": r.text}

async def buscar_todo(q: str = "", municipio: str = ""):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{CASANARE}/buscar", params={"q": q, "municipio": municipio})
        return r.json() if r.status_code==200 else {"error": r.text}

# Palabras que indican que un resultado es de la región (para ordenar mejor)
_LOCAL_KEYS = ["casanare","yopal","pore","aguazul","tauramena","orocue","monterrey","nunchia",
               "paz de ariporo","trinidad","san luis de palenque","mani","sabanalarga","tamara",
               "llanero","llanera","llanos","sabana"]

def _score_result(r):
    texto = ((r.get("title") or "") + " " + (r.get("content") or "") + " " + (r.get("url") or "")).lower()
    url = (r.get("url") or "").lower()
    score = 0
    for k in _LOCAL_KEYS:
        if k in url:
            score += 3
        elif k in texto:
            score += 1
    return score

async def buscar_web(query: str):
    if settings.TAVILY_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post("https://api.tavily.com/search",
                    json={"api_key": settings.TAVILY_API_KEY, "query": query + " Casanare Colombia", "max_results": 6, "include_answer": True})
                if r.status_code==200:
                    j=r.json()
                    results = j.get("results", [])
                    # ordena dando prioridad a resultados de la región
                    results.sort(key=_score_result, reverse=True)
                    return {"fuente": "Tavily", "results": results[:4], "answer": j.get("answer")}
        except Exception:
            pass
    return await buscar_todo(query)

async def buscar_tiktok(query: str):
    if settings.TAVILY_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post("https://api.tavily.com/search",
                    json={"api_key": settings.TAVILY_API_KEY, "query": query + " Casanare site:tiktok.com", "max_results": 3, "include_domains":["tiktok.com"]})
                if r.status_code==200:
                    j=r.json()
                    return {"fuente": "TikTok", "results": j.get("results",[])}
        except: pass
    # fallback
    return {"fuente":"TikTok","results":[{"title":"TikTok Casanare","content":f"Busca en TikTok: {query} Casanare","url":"https://www.tiktok.com/search?q=" + query.replace(" ","%20") + "%20Casanare"}]}

def generar_contenido(tipo: str, tema: str, datos: dict):
    hashtags = "#Casanare #Llano #Yopal #TurismoCasanare #OrgulloCasanareño #PasoFino"
    tl = tema.lower()
    if any(k in tl for k in ["mamona","carne","asadero","parrilla","gastron"]): hashtags += " #ComidaLlanera #Mamona #CarneALaLlanera"
    if "evento" in tipo.lower() or "palpita" in tl: hashtags += " #EventosCasanare #CasanarePalpita"
    if "safari" in tl or "guanapalo" in tl: hashtags += " #SafariLlanero"
    # guion corto para video (15 seg) - pensado para HeyGen
    guion = f"¡Ajá, mi gente! Soy Corocoro, la voz del Llano. Hoy les traigo {tema}: {datos.get('descripcion', datos.get('resumen','Una joya de Casanare que no se pueden perder'))[:120]} ¡Pilas, los esperamos en {datos.get('municipio','Casanare')}!"
    # caption para Canva (copiar/pegar)
    caption = f"🤠 {tema.upper()}\n\n{guion}\n\n📍 {datos.get('municipio','Casanare')}\n🔗 {datos.get('url','')}\n\n{hashtags}\n\n— Corocoro, voz digital del Llano"
    return {"titulo": tema, "guion": guion, "caption": caption, "hashtags": hashtags, "uso": "Copia el GUION para HeyGen y el CAPTION para Canva/Instagram"}

TOOLS_SCHEMA = [
    {"name":"buscar_noticias","description":"Buscar noticias actuales de Casanare","params":["q","municipio"]},
    {"name":"buscar_restaurantes","description":"Buscar restaurantes en Casanare","params":["q","municipio"]},
    {"name":"buscar_hospedajes","description":"Buscar hoteles/hospedajes","params":["q","municipio"]},
    {"name":"buscar_lugares","description":"Buscar lugares turisticos, fincas, experiencias","params":["q","municipio"]},
    {"name":"buscar_todo","description":"Buscar en todas las categorías","params":["q","municipio"]},
    {"name":"buscar_web","description":"Búsqueda web externa para info actual","params":["query"]},
    {"name":"maps_url","description":"Generar enlace de Google Maps para negocios reales","params":["query"]},
    {"name":"generar_contenido","description":"Generar guion/caption/hashtags para post/video","params":["tipo","tema","datos"]},
]
