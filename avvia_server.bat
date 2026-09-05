@echo off
title Amazon Routine Manager Server
cd /d "%~dp0"
echo Verifica automatica test e schermature di sicurezza...
python -m unittest discover -s backend/tests
if %errorlevel% neq 0 (
    echo [ERRORE] Uno o piu test sono falliti! Correggi gli errori prima di avviare il server.
    pause
    exit /b %errorlevel%
)
echo [OK] Tutti i test superati! Avvio del server in corso...
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
pause
