"""
Analyze scripts directory to identify redundant and duplicate scripts.
"""
from pathlib import Path
import os

def analyze_scripts():
    scripts_dir = Path(__file__).parent
    
    print("=" * 70)
    print("SCRIPT ANALYSIS - Redundant & Duplicate Detection")
    print("=" * 70)
    
    # Categorize scripts
    categories = {
        'essential': [],      # Keep - core functionality
        'redundant': [],      # Can be removed - duplicates
        'debug_temp': [],     # Can be removed - temporary debug scripts
        'one_time': [],       # Can be archived - one-time setup scripts
        'utility': []         # Keep - useful utilities
    }
    
    scripts = list(scripts_dir.glob('*.py'))
    
    # Define categorization
    script_analysis = {
        # ESSENTIAL - Core functionality
        'sanity_check.py': ('essential', 'Core testing - keep'),
        'track_price_changes.py': ('essential', 'Price tracking - keep'),
        'update_faiss_indexes.py': ('essential', 'FAISS indexing - keep'),
        'init_db.py': ('essential', 'Database initialization - keep'),
        'start_dev.py': ('essential', 'Development startup - keep'),
        'build_faiss_index.py': ('essential', 'FAISS building - keep'),
        
        # REDUNDANT - Duplicates or superseded
        'check_database.py': ('redundant', 'Superseded by check_db.py'),
        'check_db.py': ('essential', 'Keep this one'),
        'extract_roads_from_pbf.py': ('redundant', 'Superseded by extract_roads_python.py'),
        'extract_roads_python.py': ('essential', 'Keep - uses osmium library'),
        'ingest_backup_buildings.py': ('redundant', 'Superseded by process_all_backup.py'),
        'ingest_backup_spatial.py': ('redundant', 'Superseded by process_all_backup.py'),
        'ingest_all_backup_data.py': ('redundant', 'Superseded by process_all_backup.py'),
        'process_all_backup.py': ('one_time', 'One-time backup processing'),
        
        # DEBUG/TEMP - Created for debugging, can be removed
        'find_real_data.py': ('debug_temp', 'Debug script - can remove'),
        'test_db_direct.py': ('debug_temp', 'Debug script - can remove'),
        'test_query_service.py': ('debug_temp', 'Debug script - can remove'),
        'quick_test.py': ('debug_temp', 'Debug script - can remove'),
        
        # ONE-TIME - Setup scripts, archive after use
        'create_terrain_grid.py': ('one_time', 'One-time terrain setup'),
        'download_apify_datasets.py': ('utility', 'Apify download utility'),
        'ingest_posted_properties.py': ('utility', 'Property ingestion utility'),
        'ingest_price_history.py': ('utility', 'CSV price ingestion'),
        
        # UTILITY - Keep for ongoing use
        'benchmark.py': ('utility', 'Performance benchmarking'),
        'check_system_status.py': ('utility', 'System health check'),
        'verify_system.py': ('utility', 'System verification'),
        'analyze_backup.py': ('one_time', 'Backup analysis - one time'),
    }
    
    print("\n📊 SCRIPT CATEGORIZATION\n")
    
    for script in sorted(scripts):
        name = script.name
        if name == 'analyze_scripts.py':
            continue
            
        info = script_analysis.get(name, ('unknown', 'Not categorized'))
        category, reason = info
        categories.get(category, categories['utility']).append((name, reason))
    
    # Print by category
    print("✅ ESSENTIAL (Keep):")
    for name, reason in sorted(categories['essential']):
        print(f"   {name:40} - {reason}")
    
    print("\n🔧 UTILITY (Keep):")
    for name, reason in sorted(categories['utility']):
        print(f"   {name:40} - {reason}")
    
    print("\n📦 ONE-TIME (Can archive after use):")
    for name, reason in sorted(categories['one_time']):
        print(f"   {name:40} - {reason}")
    
    print("\n⚠️  REDUNDANT (Safe to remove):")
    for name, reason in sorted(categories['redundant']):
        print(f"   {name:40} - {reason}")
    
    print("\n🗑️  DEBUG/TEMP (Safe to remove):")
    for name, reason in sorted(categories['debug_temp']):
        print(f"   {name:40} - {reason}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Essential:   {len(categories['essential'])} scripts")
    print(f"  Utility:     {len(categories['utility'])} scripts")
    print(f"  One-time:    {len(categories['one_time'])} scripts")
    print(f"  Redundant:   {len(categories['redundant'])} scripts (can remove)")
    print(f"  Debug/Temp:  {len(categories['debug_temp'])} scripts (can remove)")
    
    removable = categories['redundant'] + categories['debug_temp']
    print(f"\n  Total removable: {len(removable)} scripts")
    
    if removable:
        print("\n  Scripts safe to remove:")
        for name, reason in sorted(removable):
            print(f"    - {name}")
    
    return categories

if __name__ == '__main__':
    analyze_scripts()
