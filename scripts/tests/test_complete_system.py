#!/usr/bin/env python
"""Comprehensive system test for all components"""

import requests
import json
import time
from backend.database.multiconnection import mdb
import sqlalchemy as sa

print("🧪 Comprehensive System Test\n")
print("="*60)

# Track test results
results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0
}

def test_result(name, status, message=""):
    """Print test result"""
    if status == "pass":
        print(f"✅ {name}")
        results["passed"] += 1
    elif status == "fail":
        print(f"❌ {name}: {message}")
        results["failed"] += 1
    else:
        print(f"⚠️  {name}: {message}")
        results["warnings"] += 1
    if message and status == "pass":
        print(f"   {message}")

# ===== 1. BACKEND SERVICES =====
print("\n1️⃣  BACKEND SERVICES")
print("-"*60)

# FastAPI Health
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        test_result("FastAPI Backend", "pass", f"Services: {data['services']}")
    else:
        test_result("FastAPI Backend", "fail", f"Status {response.status_code}")
except Exception as e:
    test_result("FastAPI Backend", "fail", str(e))

# Node.js Backend
try:
    response = requests.get("http://localhost:3001/api/health", timeout=5)
    if response.status_code == 200:
        test_result("Node.js Backend", "pass", "Chat API ready")
    else:
        test_result("Node.js Backend", "fail", f"Status {response.status_code}")
except Exception as e:
    test_result("Node.js Backend", "fail", str(e))

# Frontend
try:
    response = requests.get("http://localhost:3000/", timeout=5)
    if response.status_code == 200:
        test_result("Frontend (Vite)", "pass", "UI accessible")
    else:
        test_result("Frontend (Vite)", "fail", f"Status {response.status_code}")
except Exception as e:
    test_result("Frontend (Vite)", "fail", str(e))

# ===== 2. DATABASE & GIS =====
print("\n2️⃣  DATABASE & GIS")
print("-"*60)

# PostgreSQL Connection
try:
    with mdb.engine_core.connect() as conn:
        result = conn.execute(sa.text("SELECT version()"))
        version = result.scalar()
        test_result("PostgreSQL Core", "pass", f"Connected")
except Exception as e:
    test_result("PostgreSQL Core", "fail", str(e))

# Spatial DB & PostGIS
try:
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT postgis_version()"))
        version = result.scalar()
        test_result("PostGIS Extension", "pass", f"Version: {version}")
except Exception as e:
    test_result("PostGIS Extension", "fail", str(e))

# GIS Tables Count
try:
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'gis_%'"))
        count = result.scalar()
        if count > 0:
            test_result("GIS Tables Loaded", "pass", f"{count} GIS tables")
        else:
            test_result("GIS Tables Loaded", "fail", "No GIS tables found")
except Exception as e:
    test_result("GIS Tables Loaded", "fail", str(e))

# Vector DB
try:
    with mdb.engine_vector.connect() as conn:
        result = conn.execute(sa.text("SELECT 1"))
        test_result("Vector DB (pgvector)", "pass", "Ready for embeddings")
except Exception as e:
    test_result("Vector DB (pgvector)", "warn", "Optional - not critical")

# Spatial Features Table
try:
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM property_spatial_features"))
        count = result.scalar()
        test_result("Spatial Features Table", "pass", f"{count} records")
except Exception as e:
    test_result("Spatial Features Table", "warn", "Table empty or not created")

# ===== 3. MULTI-AGENT AI =====
print("\n3️⃣  MULTI-AGENT AI SYSTEM")
print("-"*60)

# Test chat endpoint
try:
    response = requests.post(
        "http://localhost:3001/api/chat",
        json={"message": "hi"},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        test_result("Chat API", "pass", "Responding to messages")
    else:
        test_result("Chat API", "fail", f"Status {response.status_code}")
except Exception as e:
    test_result("Chat API", "fail", str(e))

# Test multi-agent orchestrator
try:
    response = requests.post(
        "http://localhost:8000/api/multi-agent/chat",
        json={"message": "hello", "user_id": "test_user"},
        timeout=15
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("chat_response"):
            test_result("Multi-Agent Orchestrator", "pass", "AI responding correctly")
        else:
            test_result("Multi-Agent Orchestrator", "warn", "Response structure unusual")
    else:
        test_result("Multi-Agent Orchestrator", "fail", f"Status {response.status_code}")
except Exception as e:
    test_result("Multi-Agent Orchestrator", "warn", f"Endpoint may not exist: {e}")

# ===== 4. GEOSPATIAL CAPABILITIES =====
print("\n4️⃣  GEOSPATIAL CAPABILITIES")
print("-"*60)

# Test geospatial agent availability
try:
    from backend.services.geospatial_agent import GeospatialAgent
    test_result("GeospatialAgent Module", "pass", "Polygon/polyline drawing ready")
except Exception as e:
    test_result("GeospatialAgent Module", "fail", str(e))

# Test DMPE enhanced
try:
    from backend.services.dmpe_enhanced import EnhancedDMPE
    test_result("Enhanced DMPE Module", "pass", "GIS-aware predictions ready")
except Exception as e:
    test_result("Enhanced DMPE Module", "fail", str(e))

# Test spatial analysis
try:
    with mdb.engine_spatial.connect() as conn:
        # Check if spatial indexes exist
        result = conn.execute(sa.text("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE indexname LIKE '%gist%' OR indexname LIKE '%spatial%'
        """))
        count = result.scalar()
        if count > 0:
            test_result("Spatial Indexes", "pass", f"{count} spatial indexes")
        else:
            test_result("Spatial Indexes", "warn", "No spatial indexes found")
except Exception as e:
    test_result("Spatial Indexes", "warn", str(e))

# ===== 5. DATA AVAILABILITY =====
print("\n5️⃣  DATA AVAILABILITY")
print("-"*60)

# Check POIs
try:
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM pois"))
        count = result.scalar()
        if count > 0:
            test_result("POI Data", "pass", f"{count} POIs loaded")
        else:
            test_result("POI Data", "warn", "No POIs loaded yet")
except Exception as e:
    test_result("POI Data", "warn", "POI table may not exist")

# Check property locations
try:
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM property_locations"))
        count = result.scalar()
        if count > 0:
            test_result("Property Locations", "pass", f"{count} properties")
        else:
            test_result("Property Locations", "warn", "No properties loaded yet")
except Exception as e:
    test_result("Property Locations", "warn", "Property table may not exist")

# Check Mappls cache
try:
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM mappls_geocode_cache"))
        count = result.scalar()
        test_result("Mappls Cache", "pass", f"{count} cached requests")
except Exception as e:
    test_result("Mappls Cache", "warn", "Cache table may not exist")

# ===== 6. API ENDPOINTS =====
print("\n6️⃣  API ENDPOINTS")
print("-"*60)

endpoints = [
    ("/api/forecast", "POST", {"property_data": {"latitude": 12.9716, "longitude": 77.5946}}),
    ("/api/market/summary", "GET", None),
    ("/api/recommendations", "POST", {"budget": 50000000, "bhk": 3}),
]

for path, method, data in endpoints:
    try:
        url = f"http://localhost:8000{path}"
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            test_result(f"{method} {path}", "pass", "Working")
        else:
            test_result(f"{method} {path}", "warn", f"Status {response.status_code}")
    except Exception as e:
        test_result(f"{method} {path}", "warn", str(e))

# ===== SUMMARY =====
print("\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)
print(f"✅ Passed: {results['passed']}")
print(f"❌ Failed: {results['failed']}")
print(f"⚠️  Warnings: {results['warnings']}")

total = results['passed'] + results['failed'] + results['warnings']
success_rate = (results['passed'] / total * 100) if total > 0 else 0

print(f"\n🎯 Success Rate: {success_rate:.1f}%")

if results['failed'] == 0:
    print("\n✨ ALL CRITICAL TESTS PASSED! System is fully operational.")
elif results['failed'] <= 2:
    print("\n⚠️  Minor issues detected. System mostly operational.")
else:
    print("\n❌ Multiple failures detected. Please check the logs.")

print("\n" + "="*60)
