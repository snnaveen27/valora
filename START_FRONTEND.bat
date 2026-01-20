@echo off
title Valora Frontend - Port 3000
color 0A
cd /d "%~dp0"
echo Starting Valora Frontend on http://localhost:3000
echo.
npm run dev
pause
