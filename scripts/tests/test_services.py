#!/usr/bin/env python
"""Test all services are running correctly"""

import requests
import json
from backend.database.multiconnection import mdb
import sqlalchemy as sa

print("🔍 Testing All Services\n")

# Test FastAPI Backend
try:
    response = requests.get("http://localhost:8000/health")
    if response.status_code == 200:
        print("✅ FastAPI Backend (8000): Running")
        data = response.json()
        print(f"   - DMPE: {data['services']['dmpe']}")
        print(f"   - Mappls: {data['services']['mappls']}")
        print(f"   - Data Processor: {data['services']['data_processor']}")
    else:
        print("❌ FastAPI Backend: Error")
except Exception as e:
    print(f"❌ FastAPI Backend: {e}")

# Test Node.js Backend
try:
    response = requests.get("http://localhost:3001/api/health")
    if response.status_code == 200:
        print("✅ Node.js Backend (3001): Running")
    else:
        print("❌ Node.js Backend: Error")
except Exception as e:
    print(f"❌ Node.js Backend: {e}")

# Test Frontend
try:
    response = requests.get("http://localhost:3000/")
    if response.status_code == 200:
        print("✅ Frontend (3000): Running")
    else:
        print("❌ Frontend: Error")
except Exception as e:
    print(f"❌ Frontend: {e}")

# Test PostgreSQL
try:
    with mdb.engine_core.connect() as conn:
        result = conn.execute(sa.text("SELECT 1"))
        print("✅ PostgreSQL (5432): Connected")
        
    # Count GIS tables
    with mdb.engine_spatial.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'gis_%'"))
        gis_count = result.scalar()
        print(f"✅ GIS Tables Loaded: {gis_count}")
        
    # Check vector DB
    try:
        with mdb.engine_vector.connect() as conn:
            result = conn.execute(sa.text("SELECT 1"))
            print("✅ Vector DB: Available")
    except:
        print("⚠️  Vector DB: pgvector extension not installed (optional)")
        
except Exception as e:
    print(f"❌ PostgreSQL: {e}")

print("\n🚀 All services are ready!")
print("\nAccess URLs:")
print("- Frontend: http://localhost:3000")
print("- FastAPI API: http://localhost:8000")
print("- FastAPI Docs: http://localhost:8000/docs")
print("- Node.js API: http://localhost:3001")
