import os
from pathlib import Path

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
    
    def __getattr__(self, name):
        if name in os.environ:
            return os.environ[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

config = Config()
