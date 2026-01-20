"""
Valora AI - Development Startup Script
Automatically starts backend server when running npm run dev
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    if not backend_dir.exists():
        print(f"ERROR: Backend directory not found: {backend_dir}")
        return None
    
    print("Starting Valora AI Backend (FastAPI)...")
    
    # Start backend in a new process
    if sys.platform == "win32":
        # Windows
        backend_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "server:app", "--port", "8000", "--reload"],
            cwd=str(backend_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # Unix/Linux/Mac
        backend_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "server:app", "--port", "8000", "--reload"],
            cwd=str(backend_dir)
        )
    
    print(f"Backend started (PID: {backend_process.pid})")
    print("Backend running at: http://localhost:8000")
    return backend_process

def main():
    print("=" * 60)
    print("VALORA AI - Development Environment")
    print("=" * 60)
    
    # Start backend
    backend_process = start_backend()
    
    if backend_process:
        print("\nAll services started successfully!")
        print("\nServices:")
        print("   - Backend API: http://localhost:8000")
        print("   - Frontend: http://localhost:3000 (starting...)")
        print("\nPress Ctrl+C to stop all services")
    else:
        print("\nERROR: Failed to start services")
        sys.exit(1)

if __name__ == "__main__":
    main()
