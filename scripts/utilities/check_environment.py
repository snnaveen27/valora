"""
Check environment and dependencies for REALTY-GPT
"""

import sys
import importlib
from pathlib import Path

def check_dependencies():
    """Check all required dependencies"""
    
    dependencies = {
        "Core": ["fastapi", "uvicorn", "pydantic", "pandas", "numpy"],
        "ML": ["sklearn", "xgboost", "joblib"],
        "Vector DB": ["pinecone", "sentence_transformers"],
        "Geo": ["geopy"],
        "API": ["requests", "httpx"]
    }
    
    print("\n🔍 Checking Dependencies...")
    print("-" * 50)
    
    all_good = True
    for category, packages in dependencies.items():
        print(f"\n{category}:")
        for package in packages:
            try:
                importlib.import_module(package.replace("-", "_"))
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package} - Not installed")
                all_good = False
    
    # Check DMPE
    print("\nDMPE Integration:")
    dmpe_path = Path(__file__).parent / "dmpe" / "src"
    if dmpe_path.exists():
        print(f"  ✅ DMPE directory found")
        try:
            sys.path.insert(0, str(dmpe_path))
            from valora.data.real_estate_processor import UnifiedRealEstateProcessor
            print(f"  ✅ DMPE modules accessible")
        except ImportError as e:
            print(f"  ⚠️ DMPE modules not importable: {e}")
    else:
        print(f"  ❌ DMPE directory not found")
    
    # Check environment variables
    print("\nEnvironment Variables:")
    import os
    env_vars = [
        "PINECONE_API_KEY",
        "MAPPLS_API_KEY",
        "OPENROUTER_API_KEY"
    ]
    
    for var in env_vars:
        if os.getenv(var):
            print(f"  ✅ {var} is set")
        else:
            print(f"  ⚠️ {var} not set")
    
    print("\n" + "-" * 50)
    if all_good:
        print("✅ All core dependencies are installed!")
    else:
        print("⚠️ Some dependencies are missing. Run: pip install -r backend/requirements.txt")
    
    return all_good

if __name__ == "__main__":
    check_dependencies()
