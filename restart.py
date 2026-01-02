#!/usr/bin/env python
"""
Restart the Valora Real Estate AI Platform
This script restarts all services
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main function to restart all services"""
    print("Restarting Valora Real Estate AI Platform...")
    print("-" * 60)
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Stop any running services first
    try:
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], check=False)
        subprocess.run(["taskkill", "/F", "/IM", "node.exe", "/T"], check=False)
    except Exception as e:
        print(f"Warning: {e}")
    
    # Start the services using the main start script
    try:
        subprocess.run([sys.executable, str(project_root / "start.py")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error restarting services: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
