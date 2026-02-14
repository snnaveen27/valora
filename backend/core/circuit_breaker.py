"""
Circuit Breaker Pattern for LLM Calls
Prevents cascading failures when LLM service is down
"""

import logging
import time
import asyncio
from enum import Enum
from typing import Callable, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("valora.circuit_breaker")

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3          # Failures before opening
    recovery_timeout: int = 30          # Seconds before trying again
    half_open_max_calls: int = 1      # Max calls in half-open state
    success_threshold: int = 2          # Successes to close circuit

class CircuitBreaker:
    """
    Circuit breaker for external service calls (LLM, APIs)
    
    Usage:
        breaker = CircuitBreaker("ollama", failure_threshold=3)
        
        @breaker
        async def call_llm(prompt):
            return await ollama.generate(prompt)
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if circuit allows execution"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"[CircuitBreaker:{self.name}] Transition to HALF_OPEN")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.half_open_max_calls:
                return True
            return False
        
        return True
    
    def record_success(self):
        """Record successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        else:
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed in half-open, go back to open
            self._open_circuit()
        elif self.failure_count >= self.config.failure_threshold:
            # Too many failures, open circuit
            self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit"""
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        logger.warning(f"[CircuitBreaker:{self.name}] Circuit OPENED (failures: {self.failure_count})")
    
    def _close_circuit(self):
        """Close the circuit"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info(f"[CircuitBreaker:{self.name}] Circuit CLOSED")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker pattern"""
        async def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise e
        
        return wrapper
    
    def get_status(self) -> dict:
        """Get current circuit status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": datetime.fromtimestamp(self.last_failure_time).isoformat() \
                          if self.last_failure_time else None
        }

class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


# Global circuit breakers for services
_circuit_breakers: dict = {}

def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create circuit breaker"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]

def get_all_circuit_status() -> dict:
    """Get status of all circuits"""
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


# Pre-configured breakers for Valora services
OLLAMA_BREAKER = lambda: get_circuit_breaker(
    "ollama",
    CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30)
)

OPENROUTER_BREAKER = lambda: get_circuit_breaker(
    "openrouter",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
)
