#!/usr/bin/env python
"""
Main entry point for starting the Valora Real Estate AI Platform
This script starts all required services
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Main function to start all services"""
    print("Starting Valora Real Estate AI Platform...")
    print("-" * 60)

    project_root = Path(__file__).resolve().parent
    startup_script = project_root / "scripts" / "startup" / "start_all_services.py"

    if not startup_script.exists():
        print(f"Error: Could not find startup script at {startup_script}")
        return 1

    print(f"Delegating startup to {startup_script}")
    try:
        subprocess.run([sys.executable, str(startup_script)], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Error starting services: {exc}")
        return exc.returncode or 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
