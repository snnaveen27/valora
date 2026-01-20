@echo off
title Valora Backend - Port 8000
color 0B
cd /d "%~dp0\backend"
echo Starting Valora Backend on http://localhost:8000
echo.
echo Make sure Nominatim is running (docker-compose up -d)
echo.
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
pause
