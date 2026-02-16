"""
Comprehensive Feature Audit for Valora 2025 v2.5
Checks all modules, APIs, and capabilities
"""
import sys
from pathlib import Path
import importlib.util
import ast
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

BACKEND_DIR = Path(__file__).parent.parent / "backend"
SRC_DIR = Path(__file__).parent.parent / "src"

def get_functions_and_classes(filepath: Path):
    """Extract functions and classes from Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        return functions, classes
    except:
        return [], []

def audit_backend_modules():
    """Audit all backend modules."""
    print("\n" + "="*70)
    print("BACKEND MODULE AUDIT")
    print("="*70)
    
    modules = {}
    for py_file in BACKEND_DIR.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        funcs, classes = get_functions_and_classes(py_file)
        modules[py_file.name] = {
            "functions": len(funcs),
            "classes": len(classes),
            "size_kb": round(py_file.stat().st_size / 1024, 1)
        }
    
    # Sort by size
    sorted_modules = sorted(modules.items(), key=lambda x: x[1]['size_kb'], reverse=True)
    
    print(f"\n{'Module':<35} {'Size(KB)':<10} {'Functions':<12} {'Classes'}")
    print("-" * 70)
    for name, info in sorted_modules:
        print(f"{name:<35} {info['size_kb']:<10} {info['functions']:<12} {info['classes']}")
    
    return modules

def audit_api_endpoints():
    """Check API endpoints in server.py."""
    print("\n" + "="*70)
    print("API ENDPOINT AUDIT")
    print("="*70)
    
    server_path = BACKEND_DIR / "server.py"
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count endpoints by type
    import re
    get_endpoints = len(re.findall(r'@app\.get\(["\']', content))
    post_endpoints = len(re.findall(r'@app\.post\(["\']', content))
    put_endpoints = len(re.findall(r'@app\.put\(["\']', content))
    delete_endpoints = len(re.findall(r'@app\.delete\(["\']', content))
    
    print(f"\n  GET endpoints:    {get_endpoints}")
    print(f"  POST endpoints:   {post_endpoints}")
    print(f"  PUT endpoints:    {put_endpoints}")
    print(f"  DELETE endpoints: {delete_endpoints}")
    print(f"  TOTAL:            {get_endpoints + post_endpoints + put_endpoints + delete_endpoints}")
    
    # Find all endpoint paths
    all_endpoints = re.findall(r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']', content)
    
    # Group by category
    categories = {
        "chat": [], "admin": [], "rag": [], "valuation": [], "simulate": [],
        "building": [], "insights": [], "database": [], "scrape": [],
        "tileset": [], "viewport": [], "location": [], "city": [], "other": []
    }
    
    for method, path in all_endpoints:
        categorized = False
        for cat in categories:
            if cat in path.lower():
                categories[cat].append(f"{method.upper()} {path}")
                categorized = True
                break
        if not categorized:
            categories["other"].append(f"{method.upper()} {path}")
    
    print("\n  Endpoints by category:")
    for cat, endpoints in sorted(categories.items()):
        if endpoints:
            print(f"    {cat}: {len(endpoints)}")
    
    return categories

def audit_frontend_components():
    """Audit frontend React components."""
    print("\n" + "="*70)
    print("FRONTEND COMPONENT AUDIT")
    print("="*70)
    
    components_dir = SRC_DIR / "components"
    if not components_dir.exists():
        print("  Components directory not found")
        return {}
    
    components = {}
    for jsx_file in components_dir.glob("*.jsx"):
        size = jsx_file.stat().st_size
        components[jsx_file.name] = {"size_kb": round(size / 1024, 1)}
    
    sorted_components = sorted(components.items(), key=lambda x: x[1]['size_kb'], reverse=True)
    
    print(f"\n{'Component':<40} {'Size(KB)'}")
    print("-" * 50)
    for name, info in sorted_components[:15]:  # Top 15
        print(f"{name:<40} {info['size_kb']}")
    
    print(f"\n  Total components: {len(components)}")
    return components

def check_missing_features():
    """Check for missing or incomplete features."""
    print("\n" + "="*70)
    print("MISSING/INCOMPLETE FEATURES")
    print("="*70)
    
    issues = []
    
    # Check empty database tables
    import sqlite3
    db_path = Path(__file__).parent.parent / "storage" / "valora.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    empty_tables = []
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (table,) in cursor.fetchall():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        if cursor.fetchone()[0] == 0:
            empty_tables.append(table)
    conn.close()
    
    if empty_tables:
        issues.append(f"Empty database tables: {', '.join(empty_tables)}")
    
    # Check for TODO/FIXME comments
    todo_count = 0
    for py_file in BACKEND_DIR.glob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            todo_count += content.lower().count("todo")
            todo_count += content.lower().count("fixme")
        except:
            pass
    
    if todo_count > 0:
        issues.append(f"TODO/FIXME comments in backend: {todo_count}")
    
    # Print issues
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    return issues

def generate_recommendations():
    """Generate recommendations for v2.5."""
    print("\n" + "="*70)
    print("RECOMMENDATIONS FOR VALORA 2025 v2.5")
    print("="*70)
    
    recommendations = [
        "1. CITY EXPANSION: Add city_id column to all tables for multi-city support",
        "2. DATA QUALITY: Fill empty tables (ward_boundaries, cadastral_parcels, crime_stats)",
        "3. INCREMENTAL UPDATES: Implement upsert logic for all data ingestion",
        "4. VERSION TRACKING: Add data_version and last_updated columns",
        "5. API VERSIONING: Add /api/v2/ prefix for new endpoints",
        "6. CACHING: Implement Redis/file caching for expensive queries",
        "7. MONITORING: Add API response time logging",
        "8. TESTING: Add integration tests for all API endpoints",
        "9. DOCUMENTATION: Generate OpenAPI spec from FastAPI",
        "10. OFFLINE: Ensure all features work without internet"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")

def main():
    print("\n" + "="*70)
    print("VALORA 2025 v2.5 - COMPREHENSIVE FEATURE AUDIT")
    print("="*70)
    
    audit_backend_modules()
    audit_api_endpoints()
    audit_frontend_components()
    check_missing_features()
    generate_recommendations()
    
    print("\n" + "="*70)
    print("AUDIT COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
