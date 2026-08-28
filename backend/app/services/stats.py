import json, pathlib, threading, datetime
from datetime import timedelta

_lock = threading.Lock()
STATS_FILE = pathlib.Path("static/stats.json")


def _default():
    return {
        "total_mensajes": 0,
        "usuarios": {},
        "por_dia": {},
        "por_hora": {},
        "contenidos_generados": 0,
        "videos_generados": 0,
        "desde": None,
        "feed": [],
        "log": {},
    }


def _load():
    s = _default()
    if STATS_FILE.exists():
        try:
            j = json.loads(STATS_FILE.read_text(encoding="utf-8"))
            if isinstance(j, dict):
                s.update(j)
        except Exception:
            pass
    s.setdefault("por_hora", {})
    s.setdefault("feed", [])
    s.setdefault("usuarios", {})
    s.setdefault("por_dia", {})
    s.setdefault("log", {})
    return s


def _log_hoy(s):
    """Registro de objetivos del día (lo que Corocoro hace hoy)."""
    hoy = datetime.date.today().isoformat()
    log = s.get("log", {})
    d = log.setdefault(hoy, {"contenido": 0, "video": 0, "propuesta": False, "propuesta_titulo": "", "propuesta_hora": ""})
    return d


def _save(s):
    STATS_FILE.parent.mkdir(exist_ok=True)
    STATS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar_mensaje(user_id: str = "anon", nombre: str = ""):
    with _lock:
        s = _load()
        ahora = datetime.datetime.now()
        hoy = ahora.date().isoformat()
        hora = ahora.hour
        s["total_mensajes"] = s.get("total_mensajes", 0) + 1
        s["por_dia"][hoy] = s.get("por_dia", {}).get(hoy, 0) + 1
        s["por_hora"][str(hora)] = s.get("por_hora", {}).get(str(hora), 0) + 1
        uid = str(user_id or "anon")
        u = s.get("usuarios", {}).get(uid, {"nombre": nombre, "chats": 0, "primera_vez": hoy, "ultimo": hoy})
        u["chats"] = u.get("chats", 0) + 1
        u["ultimo"] = hoy
        u["ultimo_hora"] = hora
        if nombre:
            u["nombre"] = nombre
        if not s.get("desde"):
            s["desde"] = hoy
        s["usuarios"][uid] = u
        # feed de últimos mensajes (para ver a qué hora escriben)
        feed = s.get("feed", [])
        feed.insert(0, {"nombre": nombre or (u["nombre"] or "Anónimo"), "hora": hora,
                        "fecha": hoy, "uid": uid, "mensajes": u["chats"]})
        s["feed"] = feed[:40]
        _save(s)


def registrar_evento(tipo: str):
    with _lock:
        s = _load()
        key = "contenidos_generados" if tipo == "contenido" else "videos_generados"
        s[key] = s.get(key, 0) + 1
        _log_hoy(s)["contenido" if tipo == "contenido" else "video"] += 1
        _save(s)


def registrar_propuesta(titulo: str = ""):
    with _lock:
        s = _load()
        d = _log_hoy(s)
        d["propuesta"] = True
        if titulo:
            d["propuesta_titulo"] = titulo
        if not d.get("propuesta_hora"):
            d["propuesta_hora"] = datetime.datetime.now().strftime("%H:%M")
        _save(s)


def marcar_objetivo(tipo: str):
    """Para el demo: marca un objetivo del día como realizado (sin tocar totales)."""
    with _lock:
        s = _load()
        d = _log_hoy(s)
        if tipo == "propuesta":
            d["propuesta"] = True
            d["propuesta_hora"] = d.get("propuesta_hora") or datetime.datetime.now().strftime("%H:%M")
        elif tipo == "contenido":
            d["contenido"] = max(d.get("contenido", 0), 1)
        elif tipo == "video":
            d["video"] = max(d.get("video", 0), 1)
        _save(s)


def resumen():
    s = _load()
    usuarios = s.get("usuarios", {})
    por_dia = s.get("por_dia", {})
    hoy = datetime.date.today().isoformat()
    ultimos7 = []
    for i in range(6, -1, -1):
        d = (datetime.date.today() - timedelta(days=i)).isoformat()
        ultimos7.append({"fecha": d, "mensajes": por_dia.get(d, 0)})
    recientes = sorted(usuarios.values(), key=lambda x: x.get("ultimo", ""), reverse=True)[:10]
    horas = []
    ph = s.get("por_hora", {})
    for h in range(24):
        horas.append({"hora": h, "mensajes": ph.get(str(h), 0)})
    logh = s.get("log", {}).get(hoy, {}) or {}
    return {
        "total_mensajes": s.get("total_mensajes", 0),
        "usuarios_unicos": len(usuarios),
        "mensajes_hoy": por_dia.get(hoy, 0),
        "contenidos_generados": s.get("contenidos_generados", 0),
        "videos_generados": s.get("videos_generados", 0),
        "objetivos": {
            "propuesta": bool(logh.get("propuesta")),
            "propuesta_titulo": logh.get("propuesta_titulo", ""),
            "propuesta_hora": logh.get("propuesta_hora", ""),
            "contenido_hoy": logh.get("contenido", 0),
            "video_hoy": logh.get("video", 0),
        },
        "ultimos_7_dias": ultimos7,
        "desde": s.get("desde"),
        "por_hora": horas,
        "feed": s.get("feed", [])[:20],
        "usuarios_recientes": recientes,
    }