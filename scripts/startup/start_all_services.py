#!/usr/bin/env python
"""
Start all services with complete functionality
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path

print("Starting Advanced Real Estate AI Platform...")
print("-"*60)

# Set Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
os.environ['PYTHONPATH'] = str(project_root)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

env = os.environ.copy()
env.setdefault("VALORA_BACKEND_RELOAD", "0")

# Kill existing processes on ports
def kill_port(port):
    """Kill process on port using Windows netstat and taskkill"""
    try:
        # For Windows
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
                        print(f"Killed process on port {port}")
                        break
    except Exception as e:
        print(f"Warning: Could not kill port {port}: {e}")

# Clear ports
for port in [8000, 3001, 3000]:
    kill_port(port)

time.sleep(2)

# Start FastAPI with the existing main.py
print("\nStarting FastAPI backend...")
fastapi_cmd = [
    sys.executable,
    str(project_root / "backend" / "start_backend.py")
]

fastapi_process = subprocess.Popen(
    fastapi_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True,
    cwd=str(project_root),
    env=env
)

# Start Node.js backend
print("Starting Node.js backend...")
node_process = subprocess.Popen(
    ["npm", "start"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True,
    shell=True,
    cwd=str(project_root),
    env=env
)

# Start Vite frontend
print("Starting Vite frontend...")
vite_process = subprocess.Popen(
    ["npm", "run", "dev"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True,
    shell=True,
    cwd=str(project_root),
    env=env
)

print("\nWaiting for services to start...")
time.sleep(10)

# Test services
print("\nTesting services...")
import requests

services_status = {}

# Test FastAPI
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        services_status["FastAPI"] = "OK"
    else:
        services_status["FastAPI"] = f"Status {response.status_code}"
except:
    services_status["FastAPI"] = "Not responding"

# Test Node.js
try:
    response = requests.get("http://localhost:3001/api/health", timeout=5)
    if response.status_code == 200:
        services_status["Node.js"] = "OK"
    else:
        services_status["Node.js"] = f"Status {response.status_code}"
except:
    services_status["Node.js"] = "Not responding"

# Test Frontend
try:
    response = requests.get("http://localhost:3000", timeout=5)
    if response.status_code == 200:
        services_status["Frontend"] = "OK"
    else:
        services_status["Frontend"] = f"Status {response.status_code}"
except:
    services_status["Frontend"] = "Not responding"

print("\n" + "="*60)
print("SERVICE STATUS:")
print("="*60)
for service, status in services_status.items():
    icon = "[OK]" if status == "OK" else "[!!]"
    print(f"{icon} {service}: {status}")

print("\n" + "="*60)
print("SYSTEM READY!")
print("="*60)
print("\nAccess Points:")
print("  Frontend:  http://localhost:3000")
print("  API Docs:  http://localhost:8000/docs")
print("  Health:    http://localhost:8000/health")

print("\nPress Ctrl+C to stop all services")
print("-"*60)

# Monitor output
def monitor_process(name, process):
    """Monitor process output"""
    while True:
        line = process.stdout.readline()
        if line:
            print(f"[{name}] {line.strip()}")
        elif process.poll() is not None:
            break

# Start monitoring threads
threading.Thread(target=monitor_process, args=("FastAPI", fastapi_process), daemon=True).start()
threading.Thread(target=monitor_process, args=("Node.js", node_process), daemon=True).start()
threading.Thread(target=monitor_process, args=("Vite", vite_process), daemon=True).start()

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nShutting down services...")
    fastapi_process.terminate()
    node_process.terminate()
    vite_process.terminate()
    time.sleep(2)
    print("All services stopped.")
