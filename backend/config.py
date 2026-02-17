import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TaskConfig:
    """Configuration for the task orchestration system"""
    
    # Parallel execution settings
    MAX_CONCURRENT_TASKS: int = 4
    TASK_TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 2
    RETRY_DELAY_SECONDS: float = 1.0
    
    # Decomposition settings
    DECOMPOSITION_CONFIDENCE_THRESHOLD: float = 0.7
    MAX_TASKS_PER_QUERY: int = 10
    
    # Template learning settings
    TEMPLATE_MIN_SUCCESS_RATE: float = 0.8
    TEMPLATE_MIN_EXECUTIONS: int = 5
    
    # Monitoring settings
    TASK_METRICS_RETENTION_DAYS: int = 30
    ENABLE_TELEMETRY: bool = True
    
    # Feature flags
    FEATURE_FLAGS: Dict[str, bool] = field(default_factory=lambda: {
        "nlp_task_decomposition": True,   # Enable NLP decomposition
        "parallel_task_execution": True,  # Enable parallel execution
        "auto_template_generation": True, # Enable auto templates
        "task_monitoring": True,          # Enable task monitoring
        "streaming_progress": True        # Enable streaming progress events
    })
    
    def is_enabled(self, feature: str) -> bool:
        """Check if a feature flag is enabled"""
        return self.FEATURE_FLAGS.get(feature, False)


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    STORAGE_DIR = BASE_DIR / 'storage'
    
    @property
    def DATA_DIR(self):
        return self.STORAGE_DIR
    
    @property
    def DB_PATH(self):
        return self.STORAGE_DIR / 'database' / 'valora.db'
    
    @property
    def FAISS_DIR(self):
        return self.STORAGE_DIR / 'faiss'
    
    @property
    def SCHEMA_DIR(self):
        return self.STORAGE_DIR / 'schemas'
    
    @property
    def PRICING_DB_PATH(self):
        return self.STORAGE_DIR / 'database' / 'pricing.db'
    
    @property
    def MODELS_DIR(self):
        return self.STORAGE_DIR / 'models'
    
    @property
    def OSM_DATA_DIR(self):
        return self.DATA_DIR / 'osm_extracted'
    
    @property
    def POSTED_PROPERTIES_DIR(self):
        return self.DATA_DIR / 'posted_properties'
    
    @property
    def TERRAIN_DIR(self):
        return self.DATA_DIR / 'terrain'
    
    @property
    def TASK_CONFIG(self) -> TaskConfig:
        """Get task orchestration configuration"""
        return TaskConfig()
    
    @property
    def TASK_DB_PATH(self) -> Path:
        """Path to task patterns database"""
        return self.STORAGE_DIR / 'database' / 'valora_tasks.db'
    
    @property
    def TEMPLATE_DB_PATH(self) -> Path:
        """Path to task templates database"""
        return self.STORAGE_DIR / 'database' / 'valora_templates.db'
    
    @property
    def MONITORING_DB_PATH(self) -> Path:
        """Path to task monitoring database"""
        return self.STORAGE_DIR / 'database' / 'valora_monitoring.db'
    
    def __getattr__(self, name):
        if name in os.environ:
            return os.environ[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

config = Config()
