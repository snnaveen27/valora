import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    @property
    def DATA_DIR(self):
        return self.BASE_DIR / 'src' / 'data'
    
    @property
    def DB_PATH(self):
        return self.DATA_DIR / 'valora.db'
    
    @property
    def OSM_DATA_DIR(self):
        return self.DATA_DIR / 'osm_extracted'
    
    @property
    def TERRAIN_DIR(self):
        return self.DATA_DIR / 'terrain'
    
    def __getattr__(self, name):
        if name in os.environ:
            return os.environ[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

config = Config()
