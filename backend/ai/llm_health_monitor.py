"""
Valora Local LLM Health Monitor & Auto-Recovery
Ensures offline reliability with automatic restarts and graceful degradation
"""

import asyncio
import time
import subprocess
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class LLMStatus(Enum):
    """Status of local LLM."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Slow but working
    UNRESPONSIVE = "unresponsive"  # Not responding
    CRASHED = "crashed"  # Confirmed crash
    RECOVERING = "recovering"  # Attempting restart
    OFFLINE = "offline"  # Recovery failed


@dataclass
class HealthCheckResult:
    """Result of health check."""
    status: LLMStatus
    response_time_ms: float
    last_successful_check: float
    consecutive_failures: int
    error_message: Optional[str] = None
    model_loaded: Optional[str] = None


class LocalLLMHealthMonitor:
    """
    Monitors local LLM health and auto-recovers from crashes.
    Implements graceful degradation for offline reliability.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        check_interval_seconds: float = 30.0,
        max_consecutive_failures: int = 3,
        auto_restart: bool = True
    ):
        self.ollama_url = ollama_url
        self.check_interval = check_interval_seconds
        self.max_failures = max_consecutive_failures
        self.auto_restart = auto_restart
        
        self.last_health: Optional[HealthCheckResult] = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.total_failures = 0
        self.recovery_attempts = 0
        self.is_running = False
        
        # Queued requests for graceful degradation
        self.request_queue: List[Dict[str, Any]] = []
        self.max_queue_size = 100
        
        # Status change callbacks
        self.status_callbacks: List[callable] = []
    
    def add_status_callback(self, callback: callable):
        """Add callback for status changes."""
        self.status_callbacks.append(callback)
    
    def _notify_status_change(self, old_status: LLMStatus, new_status: LLMStatus):
        """Notify all callbacks of status change."""
        for callback in self.status_callbacks:
            try:
                callback(old_status, new_status, self.last_health)
            except Exception as e:
                print(f"[HealthMonitor] Callback error: {e}")
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        self.is_running = True
        print("[HealthMonitor] Started monitoring local LLM")
        
        while self.is_running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"[HealthMonitor] Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Short sleep on error
    
    def stop_monitoring(self):
        """Stop health monitoring."""
        self.is_running = False
        print("[HealthMonitor] Stopped monitoring")
    
    async def _perform_health_check(self):
        """Perform single health check."""
        start_time = time.time()
        self.total_checks += 1
        
        try:
            # Quick check if Ollama is responding
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Healthy response
                data = response.json()
                models = data.get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                # Determine status based on response time
                if response_time > 5000:  # > 5 seconds
                    status = LLMStatus.DEGRADED
                else:
                    status = LLMStatus.HEALTHY
                
                old_status = self.last_health.status if self.last_health else None
                
                self.last_health = HealthCheckResult(
                    status=status,
                    response_time_ms=response_time,
                    last_successful_check=time.time(),
                    consecutive_failures=0,
                    model_loaded=model_names[0] if model_names else None
                )
                
                self.consecutive_failures = 0
                
                if old_status != status and old_status is not None:
                    self._notify_status_change(old_status, status)
                
                if status == LLMStatus.DEGRADED:
                    print(f"[HealthMonitor] LLM responding slowly ({response_time:.0f}ms)")
                
            else:
                # Unhealthy response
                await self._handle_failure(
                    f"HTTP {response.status_code}",
                    response_time
                )
                
        except requests.exceptions.Timeout:
            await self._handle_failure("Timeout", (time.time() - start_time) * 1000)
        except requests.exceptions.ConnectionError:
            await self._handle_failure("Connection refused", 0)
        except Exception as e:
            await self._handle_failure(str(e), 0)
    
    async def _handle_failure(self, error_message: str, response_time: float):
        """Handle failed health check."""
        self.consecutive_failures += 1
        self.total_failures += 1
        
        old_status = self.last_health.status if self.last_health else None
        
        if self.consecutive_failures >= self.max_failures:
            # Max failures reached - consider crashed
            new_status = LLMStatus.CRASHED
            self.last_health = HealthCheckResult(
                status=new_status,
                response_time_ms=response_time,
                last_successful_check=self.last_health.last_successful_check if self.last_health else 0,
                consecutive_failures=self.consecutive_failures,
                error_message=error_message
            )
            
            if old_status != new_status:
                self._notify_status_change(old_status or LLMStatus.HEALTHY, new_status)
            
            # Attempt recovery
            if self.auto_restart:
                await self._attempt_recovery()
        else:
            # Still within failure tolerance
            new_status = LLMStatus.UNRESPONSIVE
            self.last_health = HealthCheckResult(
                status=new_status,
                response_time_ms=response_time,
                last_successful_check=self.last_health.last_successful_check if self.last_health else 0,
                consecutive_failures=self.consecutive_failures,
                error_message=error_message
            )
            
            if old_status != new_status:
                self._notify_status_change(old_status or LLMStatus.HEALTHY, new_status)
            
            print(f"[HealthMonitor] Failure {self.consecutive_failures}/{self.max_failures}: {error_message}")
    
    async def _attempt_recovery(self):
        """Attempt to restart Ollama."""
        old_status = self.last_health.status if self.last_health else None
        new_status = LLMStatus.RECOVERING
        
        self.last_health = HealthCheckResult(
            status=new_status,
            response_time_ms=0,
            last_successful_check=self.last_health.last_successful_check if self.last_health else 0,
            consecutive_failures=self.consecutive_failures,
            error_message="Attempting recovery..."
        )
        
        if old_status != new_status:
            self._notify_status_change(old_status, new_status)
        
        self.recovery_attempts += 1
        print(f"[HealthMonitor] Recovery attempt #{self.recovery_attempts}")
        
        try:
            # Platform-specific restart commands
            restart_commands = [
                # Windows
                ["powershell", "-Command", "Start-Process ollama -WindowStyle Hidden"],
                # Linux/Mac
                ["ollama", "serve"],
                # Alternative: systemd
                ["systemctl", "restart", "ollama"]
            ]
            
            success = False
            for cmd in restart_commands:
                try:
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    success = True
                    print(f"[HealthMonitor] Executed: {' '.join(cmd)}")
                    break
                except Exception as e:
                    continue
            
            if success:
                # Wait for restart
                print("[HealthMonitor] Waiting for Ollama to restart...")
                await asyncio.sleep(10)
                
                # Verify recovery
                for attempt in range(5):
                    try:
                        response = requests.get(
                            f"{self.ollama_url}/api/tags",
                            timeout=5
                        )
                        if response.status_code == 200:
                            print("[HealthMonitor] Recovery successful!")
                            self.consecutive_failures = 0
                            
                            # Process queued requests
                            await self._process_queued_requests()
                            return
                    except:
                        pass
                    await asyncio.sleep(5)
                
                # Recovery failed
                print("[HealthMonitor] Recovery failed - Ollama not responding")
                old_status = self.last_health.status
                new_status = LLMStatus.OFFLINE
                
                self.last_health = HealthCheckResult(
                    status=new_status,
                    response_time_ms=0,
                    last_successful_check=0,
                    consecutive_failures=self.max_failures,
                    error_message="Recovery failed - manual restart required"
                )
                
                if old_status != new_status:
                    self._notify_status_change(old_status, new_status)
            else:
                print("[HealthMonitor] Failed to execute restart command")
                
        except Exception as e:
            print(f"[HealthMonitor] Recovery error: {e}")
    
    async def _process_queued_requests(self):
        """Process queued requests after recovery."""
        if not self.request_queue:
            return
        
        print(f"[HealthMonitor] Processing {len(self.request_queue)} queued requests")
        
        # Process up to 10 queued requests
        to_process = self.request_queue[:10]
        self.request_queue = self.request_queue[10:]
        
        for request in to_process:
            try:
                # Notify that request is being processed
                if 'callback' in request:
                    request['callback']({
                        'status': 'processing',
                        'message': 'LLM recovered - processing queued request'
                    })
            except Exception as e:
                print(f"[HealthMonitor] Error processing queued request: {e}")
    
    def queue_request(self, request_data: Dict[str, Any]) -> bool:
        """Queue a request for later processing when LLM recovers."""
        if len(self.request_queue) >= self.max_queue_size:
            return False
        
        self.request_queue.append({
            'data': request_data,
            'timestamp': time.time(),
            'callback': request_data.get('callback')
        })
        return True
    
    def get_health(self) -> Dict[str, Any]:
        """Get current health status."""
        if not self.last_health:
            return {
                'status': 'unknown',
                'is_healthy': False,
                'message': 'Health check not performed yet'
            }
        
        return {
            'status': self.last_health.status.value,
            'is_healthy': self.last_health.status in [LLMStatus.HEALTHY, LLMStatus.DEGRADED],
            'response_time_ms': round(self.last_health.response_time_ms, 2),
            'consecutive_failures': self.last_health.consecutive_failures,
            'total_checks': self.total_checks,
            'total_failures': self.total_failures,
            'recovery_attempts': self.recovery_attempts,
            'model_loaded': self.last_health.model_loaded,
            'last_successful_check': self.last_health.last_successful_check,
            'error_message': self.last_health.error_message,
            'queued_requests': len(self.request_queue)
        }
    
    def is_available(self) -> bool:
        """Quick check if LLM is available for requests."""
        if not self.last_health:
            return False
        return self.last_health.status in [LLMStatus.HEALTHY, LLMStatus.DEGRADED]


class GracefulDegradationHandler:
    """
    Handles graceful degradation when local LLM is unavailable.
    Falls back to simplified responses or queues for later processing.
    """
    
    def __init__(self, health_monitor: LocalLLMHealthMonitor):
        self.health = health_monitor
        self.fallback_enabled = True
    
    async def handle_request(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle request with graceful degradation.
        
        Returns:
            Response or fallback message
        """
        if self.health.is_available():
            # Normal processing - pass to actual LLM
            return {'status': 'process', 'query': query, 'context': context}
        
        # LLM unavailable - provide graceful fallback
        if self.fallback_enabled:
            if self.health.last_health and self.health.last_health.status == LLMStatus.RECOVERING:
                # Currently recovering - queue the request
                queued = self.health.queue_request({
                    'query': query,
                    'context': context
                })
                
                if queued:
                    return {
                        'status': 'queued',
                        'message': 'Local LLM is restarting. Your request has been queued and will be processed shortly.',
                        'queue_position': len(self.health.request_queue)
                    }
                else:
                    return {
                        'status': 'unavailable',
                        'message': 'Request queue is full. Please try again in a few moments.'
                    }
            
            elif self.health.last_health and self.health.last_health.status == LLMStatus.OFFLINE:
                # Recovery failed - provide static fallback
                return {
                    'status': 'fallback',
                    'message': self._generate_fallback_response(query),
                    'note': 'Local AI is temporarily offline. Showing simplified response based on available data.'
                }
            
            else:
                # Other degraded state
                return {
                    'status': 'degraded',
                    'message': 'AI response may be delayed. Processing your request...',
                    'query': query
                }
        
        # Fallback disabled
        return {
            'status': 'unavailable',
            'message': 'Local AI is currently unavailable. Please try again later.'
        }
    
    def _generate_fallback_response(self, query: str) -> str:
        """Generate simple fallback response based on query keywords."""
        query_lower = query.lower()
        
        # Simple keyword-based responses
        if 'price' in query_lower or 'cost' in query_lower:
            return "Price information is available in the property details. Please check the listings panel."
        
        if 'location' in query_lower or 'area' in query_lower:
            return "This area has various amenities and transport options. Check the map for nearby facilities."
        
        if 'view' in query_lower or 'sunlight' in query_lower:
            return "3D view analysis requires AI processing. The map shows building heights and shadows."
        
        if 'compare' in query_lower or 'vs' in query_lower:
            return "Property comparison is available. Select multiple properties to compare."
        
        if 'invest' in query_lower or 'roi' in query_lower:
            return "Investment analysis is based on historical price trends and market data."
        
        # Generic fallback
        return "I'm currently running in simplified mode. For detailed analysis, please wait for the AI to restart or refresh the page."


# Singleton instances
_health_monitor = None
_degradation_handler = None

def get_health_monitor() -> LocalLLMHealthMonitor:
    """Get singleton health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = LocalLLMHealthMonitor()
    return _health_monitor

def get_degradation_handler() -> GracefulDegradationHandler:
    """Get singleton degradation handler."""
    global _degradation_handler
    if _degradation_handler is None:
        _degradation_handler = GracefulDegradationHandler(get_health_monitor())
    return _degradation_handler

async def start_health_monitoring():
    """Start health monitoring in background."""
    monitor = get_health_monitor()
    asyncio.create_task(monitor.start_monitoring())
    print("[HealthMonitor] Background monitoring started")
