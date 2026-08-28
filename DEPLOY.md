# Deploy público (jurado)

## Opción recomendada: Render (plan gratis)

1. Sube este repositorio a **GitHub** (repo `corocoro-casanare`).
2. Crea cuenta gratis en **render.com** (con el botón de "GitHub").
3. En Render: **New → Web Service** → conecta el repo. Render detecta solito el `Dockerfile` de la raíz (build automático).
4. Pon las variables de entorno en Render (Dashboard → Environment):
   - `GROQ_API_KEY` (obligatoria pa' que el chat/posts funcionen)
   - `GROQ_MODEL=openai/gpt-oss-20b`
   - `TELEGRAM_BOT_TOKEN` (para el envío de propuestas)
   - `ADMIN_CHAT_ID=6484885576`
   - `CASANARE_API` (la que uses)
   - `PIAPI_API_KEY` (opcional, solo videos IA)
5. Listo: te da un link tipo `https://corocoro-casanare.onrender.com`.

Verificación: `/health` y `/docs` (Swagger).

## Bot Telegram (local o worker)

Si quieres que el bot responda desde la nube, súbelo como worker y pon:
- `COROCORO_API=https://tu-backend.onrender.com`
- En local el bot usa `http://localhost:8000` por defecto.

⚠️ El plan gratis de Render hiberna el servicio a los 15 min sin uso (el primer load tarda ~1 min). Ideal para el demo del jurado.

## Alternativa instantánea (sin cuenta)

`cloudflared tunnel --url http://localhost:8000` → te da un https://…trycloudflare.com público al momento (no fijo).