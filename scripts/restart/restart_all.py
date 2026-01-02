#!/usr/bin/env python
"""
Complete Application Restart Script
Stops all services and restarts everything fresh
"""

import subprocess
import sys
import time
import os
from pathlib import Path

print("="*70)
print("🔄 COMPLETE APPLICATION RESTART")
print("="*70)
print()

# Step 1: Kill all existing services
print("Step 1: Stopping all services...")

def kill_service(process_name):
    """Kill a service by process name"""
    try:
        # Windows
        subprocess.run(f'taskkill /F /IM {process_name}.exe', shell=True, capture_output=True)
        print(f"   ✅ Killed {process_name} processes")
    except:
        pass

# Kill all services
kill_service("python")
kill_service("node")
time.sleep(3)

print("\nStep 2: Clearing ports...")
for port in [8000, 3001, 3000]:
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    if pid and pid.isdigit():
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                        print(f"   ✅ Cleared port {port}")
    except:
        pass

time.sleep(2)

# Step 3: Set environment
print("\nStep 3: Setting up environment...")
project_root = Path(__file__).parent
os.environ['PYTHONPATH'] = str(project_root)
print(f"   ✅ PYTHONPATH: {project_root}")

# Step 4: Start FastAPI Backend
print("\nStep 4: Starting FastAPI Backend...")
fastapi_cmd = [sys.executable, "-m", "uvicorn", "complete_app:app", "--host", "0.0.0.0", "--port", "8000"]
fastapi_process = subprocess.Popen(
    fastapi_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=str(project_root)
)
print("   ✅ FastAPI starting on port 8000...")

# Step 5: Start Node.js Backend
print("\nStep 5: Starting Node.js Backend...")
node_process = subprocess.Popen(
    ["npm", "start"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=str(project_root)
)
print("   ✅ Node.js starting on port 3001...")

# Step 6: Start Frontend
print("\nStep 6: Starting Vite Frontend...")
vite_process = subprocess.Popen(
    ["npm", "run", "dev"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=str(project_root)
)
print("   ✅ Frontend starting on port 3000...")

# Step 7: Wait and test
print("\nStep 7: Waiting for services to initialize...")
time.sleep(15)

print("\n" + "="*70)
print("Testing Services...")
print("="*70)

import requests

services = [
    ("FastAPI", "http://localhost:8000/health"),
    ("Node.js", "http://localhost:3001/api/health"),
    ("Frontend", "http://localhost:3000")
]

all_good = True
for name, url in services:
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ {name}: RUNNING")
        else:
            print(f"   ⚠️  {name}: Status {response.status_code}")
            all_good = False
    except Exception as e:
        print(f"   ❌ {name}: Failed ({str(e)[:50]})")
        all_good = False

print("\n" + "="*70)
print("🚀 APPLICATION RESTARTED!")
print("="*70)

if all_good:
    print("\n✅ ALL SERVICES RUNNING SUCCESSFULLY!")
    print("\n📱 Access Points:")
    print("   Frontend: http://localhost:3000")
    print("   API Docs: http://localhost:8000/docs")
    print("   Health:   http://localhost:8000/health")
    print("\n✨ Ready to use!")
else:
    print("\n⚠️  Some services may still be starting...")
    print("   Wait 30 seconds and check again")

print("\n" + "="*70)
print("📋 What to test:")
print("   1. Open http://localhost:3000")
print("   2. Check if map loads")
print("   3. Try clicking property markers")
print("   4. Test chat: 'Find properties in Whitefield'")
print("   5. Right-click map for analysis")
print("="*70)

print("\nPress Ctrl+C to stop all services")
print("-"*70)

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping all services...")
    fastapi_process.terminate()
    node_process.terminate()
    vite_process.terminate()
    print("All services stopped.")
