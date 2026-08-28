@echo off
title COROCORO DEL CASANARE - Panel de control
cd /d "%~dp0"

echo ============================================
echo   COROCORO DEL CASANARE - INICIANDO
echo   1) Backend (puerto 8000)
echo   2) Bot de Telegram
echo   3) Panel web (navegador)
echo ============================================
echo.

cd backend
start "Corocoro Backend" cmd /k python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..

timeout /t 6 /nobreak >nul

cd telegram_bot
start "Corocoro Bot Telegram" cmd /k python bot.py
cd ..

timeout /t 4 /nobreak >nul
start "" "http://localhost:8000/"

echo.
echo Listo. El panel se abrio en tu navegador (http://localhost:8000/)
echo Ventanas: "Corocoro Backend" y "Corocoro Bot Telegram".
echo Cierra esas ventanas para apagar todo.
pause