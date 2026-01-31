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
    python_exe = sys.executable or "python"
    uvicorn_cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "server:app",
        "--app-dir",
        str(backend_dir),
        "--port",
        "8000",
        "--reload",
    ]

    if sys.platform == "win32":
        # Windows
        backend_process = subprocess.Popen(
            uvicorn_cmd,
            cwd=str(backend_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # Unix/Linux/Mac
        backend_process = subprocess.Popen(
            uvicorn_cmd,
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
        try:
            while True:
                exit_code = backend_process.poll()
                if exit_code is not None:
                    print(f"\nBackend process exited with code: {exit_code}")
                    sys.exit(exit_code)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping backend...")
            try:
                backend_process.terminate()
                time.sleep(1)
            except Exception:
                pass
            try:
                backend_process.kill()
            except Exception:
                pass
    else:
        print("\nERROR: Failed to start services")
        sys.exit(1)

if __name__ == "__main__":
    main()
