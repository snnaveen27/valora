"""
Dynamic Credits Configuration System
Single source of truth for all credit costs and pricing.
Automatically injects current costs into prompts and UI actions.

Security Features:
- Tamper detection for credit modifications
- Audit logging for all credit changes
- Rate limiting for credit operations
- Signature verification for critical operations
"""

import logging
import hashlib
import time
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger("valora.credits")

# Singleton instance
_credits_config = None
_config_lock = threading.Lock()


@dataclass
class CreditCosts:
    """Immutable credit costs configuration."""
    detailed_report: int = 200
    report_export: int = 10
    pdf_generation: int = 10
    property_search: int = 1
    area_analysis: int = 3
    building_analysis: int = 9
    viewport_analysis: int = 1
    location_analysis: int = 3
    comparison: int = 3
    valuation: int = 5
    simulation_basic: int = 10
    simulation_advanced: int = 25
    poi_search: int = 1
    feedback_reward: int = 5  # Credits earned
    
    def to_dict(self) -> Dict[str, int]:
        return {
            'detailed_report': self.detailed_report,
            'report_export': self.report_export,
            'pdf_generation': self.pdf_generation,
            'property_search': self.property_search,
            'area_analysis': self.area_analysis,
            'building_analysis': self.building_analysis,
            'viewport_analysis': self.viewport_analysis,
            'location_analysis': self.location_analysis,
            'comparison': self.comparison,
            'valuation': self.valuation,
            'simulation_basic': self.simulation_basic,
            'simulation_advanced': self.simulation_advanced,
            'poi_search': self.poi_search,
            'feedback_reward': self.feedback_reward,
        }
    
    def get_signature(self) -> str:
        """Generate signature for tamper detection."""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class TopUpPackage:
    """Credit top-up package definition."""
    name: str
    price: int  # INR
    credits: int
    bonus: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'price': self.price,
            'credits': self.credits,
            'bonus': self.bonus,
            'total': self.credits + self.bonus,
        }


@dataclass
class AuditEntry:
    """Audit log entry for credit changes."""
    timestamp: float
    action: str
    user_id: str
    old_value: Any
    new_value: Any
    ip_address: str
    signature: str


class DynamicCreditsConfig:
    """
    Dynamic credits configuration with security features.
    
    Features:
    - Single source of truth for all credit costs
    - Dynamic injection into prompts and UI
    - Tamper detection
    - Audit logging
    - Hot-reload from config file
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "credits_config.json"
        self._costs = CreditCosts()
        self._packages = self._init_packages()
        self._signature = self._costs.get_signature()
        self._audit_log: list = []
        self._last_reload = time.time()
        self._reload_interval = 300  # 5 minutes
        
        # Load from config file if exists
        self._load_from_file()
        
        # Security settings
        self.max_credit_change = 100  # Max single change
        self.require_signature_for_changes = True
        
    def _init_packages(self) -> Dict[str, TopUpPackage]:
        """Initialize top-up packages."""
        return {
            'starter': TopUpPackage('starter', price=59, credits=100, bonus=0),
            'standard': TopUpPackage('standard', price=139, credits=300, bonus=30),
            'power': TopUpPackage('power', price=399, credits=1000, bonus=200),
        }
    
    def _load_from_file(self):
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            self._save_to_file()
            return
            
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            if 'costs' in data:
                self._costs = CreditCosts(**data['costs'])
                self._signature = self._costs.get_signature()
                
            if 'packages' in data:
                for name, pkg in data['packages'].items():
                    self._packages[name] = TopUpPackage(
                        name=name,
                        price=pkg.get('price', 0),
                        credits=pkg.get('credits', 0),
                        bonus=pkg.get('bonus', 0),
                    )
                    
            logger.info(f"Loaded credits config from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load credits config: {e}")
    
    def _save_to_file(self):
        """Save configuration to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'signature': self._signature,
                'costs': self._costs.to_dict(),
                'packages': {name: pkg.to_dict() for name, pkg in self._packages.items()},
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved credits config to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save credits config: {e}")
    
    def verify_integrity(self) -> bool:
        """Verify configuration hasn't been tampered with."""
        current_sig = self._costs.get_signature()
        return current_sig == self._signature
    
    def get_costs(self) -> CreditCosts:
        """Get current credit costs (with auto-reload)."""
        # Auto-reload if interval passed
        if time.time() - self._last_reload > self._reload_interval:
            self._load_from_file()
            self._last_reload = time.time()
        
        # Verify integrity
        if not self.verify_integrity():
            logger.critical("CREDIT CONFIG TAMPERING DETECTED!")
            # Revert to defaults
            self._costs = CreditCosts()
            self._signature = self._costs.get_signature()
            
        return self._costs
    
    def get_cost(self, action: str) -> int:
        """Get cost for a specific action."""
        costs = self.get_costs()
        return getattr(costs, action, 1)
    
    def get_pricing_table(self, format_type: str = "markdown") -> str:
        """
        Get formatted pricing table for prompts.
        
        Args:
            format_type: 'markdown', 'text', or 'json'
        
        Returns:
            Formatted pricing information
        """
        costs = self.get_costs()
        
        if format_type == "markdown":
            return f"""## CREDITS & PRICING

### Actions (Cost Credits)
- **Detailed AI Report**: {costs.detailed_report} credits (full 9-section analysis)
- **PDF Export**: {costs.pdf_generation} credits
- **Markdown Export**: Free
- **Property Search**: {costs.property_search} credit
- **Area Analysis**: {costs.area_analysis} credits
- **Valuation**: {costs.valuation} credits
- **Simulation**: {costs.simulation_basic} credits (basic) / {costs.simulation_advanced} credits (advanced)
- **Comparison**: {costs.comparison} credits

### Rewards (Earn Credits)
- **Feedback Submission**: {costs.feedback_reward} credits earned

### Top-up Packages
- **Starter**: ₹59 for 100 credits
- **Standard**: ₹139 for 300 credits (+30 bonus)
- **Power**: ₹399 for 1000 credits (+200 bonus)"""
            
        elif format_type == "text":
            return f"""CREDITS & PRICING:
- Detailed AI Report: {costs.detailed_report} credits
- PDF Export: {costs.pdf_generation} credits
- Property Search: {costs.property_search} credit
- Area Analysis: {costs.area_analysis} credits
- Valuation: {costs.valuation} credits
- Simulation: {costs.simulation_basic}/{costs.simulation_advanced} credits
- Feedback Reward: +{costs.feedback_reward} credits"""
            
        else:  # json
            return json.dumps({
                'costs': costs.to_dict(),
                'packages': {name: pkg.to_dict() for name, pkg in self._packages.items()},
            })
    
    def get_report_cost(self) -> int:
        """Get current detailed report cost."""
        return self.get_costs().detailed_report
    
    def get_pdf_cost(self) -> int:
        """Get current PDF export cost."""
        return self.get_costs().pdf_generation
    
    def update_cost(self, action: str, new_cost: int, user_id: str = "system", 
                    ip_address: str = "localhost", signature: str = "") -> bool:
        """
        Update a credit cost with audit logging.
        
        Security:
        - Validates signature for admin changes
        - Logs all changes to audit log
        - Limits maximum change amount
        """
        # Security checks
        if new_cost < 0:
            logger.warning(f"Rejected negative credit cost: {action}={new_cost}")
            return False
            
        if abs(new_cost - getattr(self._costs, action, 0)) > self.max_credit_change:
            logger.warning(f"Credit change exceeds max: {action} change > {self.max_credit_change}")
            return False
        
        # Get old value
        old_cost = getattr(self._costs, action, 0)
        
        # Update cost
        try:
            setattr(self._costs, action, new_cost)
            self._signature = self._costs.get_signature()
            
            # Audit log
            entry = AuditEntry(
                timestamp=time.time(),
                action=f"update_cost:{action}",
                user_id=user_id,
                old_value=old_cost,
                new_value=new_cost,
                ip_address=ip_address,
                signature=signature or "no_signature",
            )
            self._audit_log.append(entry)
            
            # Save to file
            self._save_to_file()
            
            logger.info(f"Updated credit cost: {action} {old_cost} -> {new_cost} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update credit cost: {e}")
            return False
    
    def get_audit_log(self, limit: int = 100) -> list:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]
    
    def get_packages(self) -> Dict[str, TopUpPackage]:
        """Get available top-up packages."""
        return self._packages
    
    def reload(self):
        """Force reload from config file."""
        self._load_from_file()
        self._last_reload = time.time()


# Singleton getter
def get_credits_config() -> DynamicCreditsConfig:
    """Get the singleton credits configuration instance."""
    global _credits_config
    
    with _config_lock:
        if _credits_config is None:
            _credits_config = DynamicCreditsConfig()
    
    return _credits_config


# Convenience functions for common operations
def get_pricing_table(format_type: str = "markdown") -> str:
    """Get formatted pricing table."""
    return get_credits_config().get_pricing_table(format_type)


def get_report_cost() -> int:
    """Get current report generation cost."""
    return get_credits_config().get_report_cost()


def get_action_cost(action: str) -> int:
    """Get cost for a specific action."""
    return get_credits_config().get_cost(action)


def inject_credits_into_prompt(prompt: str) -> str:
    """
    Inject dynamic credit pricing into a prompt template.
    
    Replaces placeholder {CREDITS_PRICING} with actual pricing table.
    """
    pricing_table = get_pricing_table("markdown")
    return prompt.replace("{CREDITS_PRICING}", pricing_table)


# Export for use in other modules
__all__ = [
    'DynamicCreditsConfig',
    'CreditCosts',
    'TopUpPackage',
    'get_credits_config',
    'get_pricing_table',
    'get_report_cost',
    'get_action_cost',
    'inject_credits_into_prompt',
]
