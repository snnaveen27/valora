@echo off
title Extract 3D Buildings from PBF
color 0E
echo ========================================
echo  Valora - Extract 3D Buildings from PBF
echo ========================================
echo.
echo This will extract building footprints and heights
echo from bengaluru.osm.pbf and save to buildings.geojson
echo.

cd /d "%~dp0"

echo Installing dependencies...
pip install osmium

echo.
echo Starting extraction...
python scripts\extract_buildings_from_pbf.py

echo.
echo ========================================
echo  Extraction complete!
echo ========================================
echo.
echo Next steps:
echo 1. Restart backend: START_BACKEND.bat
echo 2. Start frontend: npm run dev
echo 3. Type "show me tin factory" in chat
echo.
pause
