"""
Complete startup script for Valora AI with multi-agent map integration
Ensures all services are running and properly connected
"""

import subprocess
import time
import sys
import os
import logging
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValoraStartup:
    """Manages startup of all Valora AI services"""
    
    def __init__(self):
        self.backend_port = 8000
        self.frontend_port = 5173
        self.processes = []
        self.project_root = Path(__file__).parent
    
    def check_port(self, port: int) -> bool:
        """Check if a port is available"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0
    
    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=1)
                if response.status_code < 500:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def start_backend(self):
        """Start the FastAPI backend"""
        logger.info("Starting backend server...")
        
        if not self.check_port(self.backend_port):
            logger.warning(f"Port {self.backend_port} is already in use. Backend might be running.")
            return True
        
        backend_cmd = [
            sys.executable,
            "-m", "uvicorn",
            "backend.api.main:app",
            "--reload",
            "--port", str(self.backend_port),
            "--host", "0.0.0.0"
        ]
        
        process = subprocess.Popen(
            backend_cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        self.processes.append(process)
        
        # Wait for backend to start
        if self.wait_for_service(f"http://localhost:{self.backend_port}/docs"):
            logger.info("✅ Backend started successfully")
            return True
        else:
            logger.error("❌ Backend failed to start")
            return False
    
    def start_frontend(self):
        """Start the Vite frontend"""
        logger.info("Starting frontend server...")
        
        if not self.check_port(self.frontend_port):
            logger.warning(f"Port {self.frontend_port} is already in use. Frontend might be running.")
            return True
        
        # Check if npm is available
        try:
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
        except:
            logger.error("npm is not installed. Please install Node.js first.")
            return False
        
        # Install dependencies if needed
        if not (self.project_root / "node_modules").exists():
            logger.info("Installing frontend dependencies...")
            subprocess.run(["npm", "install"], cwd=self.project_root, check=True)
        
        frontend_cmd = ["npm", "run", "dev"]
        
        process = subprocess.Popen(
            frontend_cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        self.processes.append(process)
        
        # Wait for frontend to start
        time.sleep(5)  # Vite takes a bit longer to start
        logger.info("✅ Frontend started successfully")
        return True
    
    def test_integration(self):
        """Test that all components are integrated properly"""
        logger.info("Testing integration...")
        
        tests = []
        
        # Test backend API
        try:
            response = requests.get(f"http://localhost:{self.backend_port}/api/health")
            tests.append(("Backend API", response.status_code == 200))
        except:
            tests.append(("Backend API", False))
        
        # Test geocoding endpoint
        try:
            response = requests.get(
                f"http://localhost:{self.backend_port}/api/maps/geocode",
                params={"address": "whitefield"}
            )
            data = response.json()
            tests.append(("Geocoding", data.get("status") == "success"))
        except:
            tests.append(("Geocoding", False))
        
        # Test multi-agent endpoint
        try:
            response = requests.post(
                f"http://localhost:{self.backend_port}/api/agent/plan",
                json={
                    "user_id": "test",
                    "intent": "show me whitefield",
                    "context": {}
                }
            )
            tests.append(("Multi-Agent", response.status_code == 200))
        except:
            tests.append(("Multi-Agent", False))
        
        # Print test results
        logger.info("\n" + "="*50)
        logger.info("INTEGRATION TEST RESULTS")
        logger.info("="*50)
        for test_name, passed in tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
        logger.info("="*50)
        
        return all(passed for _, passed in tests)
    
    def print_instructions(self):
        """Print usage instructions"""
        print("\n" + "="*60)
        print("VALORA AI MULTI-AGENT SYSTEM STARTED")
        print("="*60)
        print(f"🌐 Frontend: http://localhost:{self.frontend_port}")
        print(f"🔧 Backend API: http://localhost:{self.backend_port}")
        print(f"📚 API Docs: http://localhost:{self.backend_port}/docs")
        print("\n📝 TEST PROMPTS TO TRY:")
        print("  1. 'show me whitefield'")
        print("  2. 'navigate to koramangala'")
        print("  3. 'find 3bhk apartments in whitefield under 1.5 crore'")
        print("  4. 'compare whitefield with electronic city'")
        print("  5. 'draw 2km radius around manyata tech park'")
        print("\n🎯 FEATURES:")
        print("  • Natural language map navigation")
        print("  • Property search and filtering")
        print("  • Investment analysis and forecasting")
        print("  • Area comparisons and buffer zones")
        print("  • Multi-agent collaboration")
        print("\n⚡ TIPS:")
        print("  • The multi-agent panel is on the right")
        print("  • Map commands will automatically update the map")
        print("  • Analysis results appear in the left panel")
        print("  • Try the test prompts above to see all features")
        print("\n🛑 Press Ctrl+C to stop all services")
        print("="*60 + "\n")
    
    def run(self):
        """Run the complete startup sequence"""
        try:
            logger.info("Starting Valora AI services...")
            
            # Start services
            if not self.start_backend():
                logger.error("Failed to start backend")
                return False
            
            time.sleep(2)
            
            if not self.start_frontend():
                logger.error("Failed to start frontend")
                return False
            
            time.sleep(3)
            
            # Test integration
            if self.test_integration():
                logger.info("✅ All services started and integrated successfully!")
            else:
                logger.warning("⚠️ Some integration tests failed, but services are running")
            
            # Print instructions
            self.print_instructions()
            
            # Keep running
            logger.info("Services are running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\nShutting down services...")
            self.shutdown()
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            self.shutdown()
            return False
    
    def shutdown(self):
        """Shutdown all services"""
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        logger.info("All services stopped")


if __name__ == "__main__":
    startup = ValoraStartup()
    startup.run()
