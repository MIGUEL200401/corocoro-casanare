# 🤠 COROCORO IA DEL CASANARE — Voz digital del Llano

**Stack MVP chimba:** Node (casanare-api) + Python FastAPI (agente) + Telegram Bot + APScheduler + TTS

## Arquitectura
```
Usuario → Telegram → Bot (polling) → FastAPI /chat → Agente Corocoro → Herramientas → casanare-api / Tavily / Google Maps → Respuesta + Fuentes + Contenido
                                               ↓
                                    Scheduler 05:00 → propuesta al admin → aprobar/descartar
                                               ↓
                                    Panel web /stats → estadísticas en vivo + contacto Telegram
```

## Instalación rápida (Windows)

1. **casanare-api** (datos):
```powershell
cd casanare-api
node server.js
# http://localhost:4000
```

2. **Corocoro FastAPI**:
```powershell
cd corocoro-ia\backend
pip install -r requirements.txt
copy ..\..\\.env.example .env  # y edita TELEGRAM_BOT_TOKEN
# edita .env: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY o GROQ_API_KEY (opcional), TAVILY_API_KEY (opcional)
uvicorn app.main:app --reload --port 8000
# http://localhost:8000  docs: http://localhost:8000/docs
```

3. **Telegram Bot**:
```powershell
cd corocoro-ia\telegram_bot
# asegúrate que .env en backend tenga el token
python bot.py
```
Habla con tu bot en Telegram: `/start` → "¿Qué puedo hacer este fin de semana en Yopal?"

## Sin API keys funciona igual
Si no pones OPENAI/TAVILY, Corocoro usa fallback rule-based 100% funcional con datos reales de `casanare-api`.

## Voz llanera
`POST /tts?text=¡Ajá mi gente!` → genera `static/voz.mp3` (ElevenLabs → OpenAI TTS → gTTS fallback)

## Avatar
Guarda la imagen del corocoro rojo en `corocoro-ia/avatar/corocoro.png` — el bot la envía en /start.

## Demo para jurado (5 casos)
1. "¿Qué puedo hacer este fin de semana en Yopal?" → buscar_lugares + noticias evento Casanare Palpita
2. "¿Dónde puedo comer?" → buscar_restaurantes La Mamantona, La Cascada
3. "¿Qué pasó hoy en Casanare?" → buscar_noticias con fuente
4. "Hazme una publicación sobre ese evento" → generar_contenido título/guion/caption/hashtags
5. "¿Cómo contacto ese negocio?" → link de Google Maps (negocios reales) o Telegram @Corocoro_casanare_bot

## Despliegue
- FastAPI → Render/Railway (Docker)
- casanare-api → Render
- Bot → mismo Render como worker (polling) o webhook
- Env vars en dashboard, no en código.

¡Pilas, mi gente! 🚀
