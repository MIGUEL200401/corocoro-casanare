@echo off
title Corocoro - lanzador
cd /d "%~dp0"

echo =============================================
echo   COROCORO DEL CASANARE - arrancando todo
echo =============================================
echo.

cd backend
start "BOT-Corocoro-Backend" /min cmd /c python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..\telegram_bot
start "BOT-Corocoro-Telegram" /min cmd /c python bot.py
cd ..

timeout /t 10 /nobreak >nul
start "" "http://localhost:8000/"

echo.
echo  LISTO! Panel abierto en tu navegador.
echo  (backend y bot quedaron corriendo en segundo plano)