@echo off
title Amazon Routine Manager Server
cd /d "%~dp0"
echo Avvio del server Amazon Routine Manager...
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
pause
