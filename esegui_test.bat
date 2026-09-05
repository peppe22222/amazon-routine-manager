@echo off
title Test e Schermature Amazon Routine Manager
cd /d "%~dp0"
echo Esecuzione suite completa test e verifiche di sicurezza...
python -m unittest discover -s backend/tests -v
echo.
pause
