@echo off
echo ========================================
echo  OSM Data Extraction for Bengaluru
echo ========================================
echo.
echo This will extract all features from bengaluru.osm.pbf
echo and organize them into structured folders.
echo.
echo Output: src/data/osm_extracted/
echo.
pause

cd scripts
python extract_all_osm_data.py

echo.
echo ========================================
echo  Extraction Complete!
echo ========================================
echo.
echo Check src/data/osm_extracted/ for results
echo.
pause
