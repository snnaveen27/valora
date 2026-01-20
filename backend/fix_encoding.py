"""
Fix Unicode emoji encoding issues for Windows console
Replaces all emoji characters with ASCII-safe alternatives
"""

import os
from pathlib import Path

# Emoji replacements
REPLACEMENTS = {
    '✅': '[OK]',
    '⚠️': '[WARNING]',
    '❌': '[ERROR]',
    '📦': '[INFO]',
}

def fix_file(filepath):
    """Fix emoji encoding in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        for emoji, replacement in REPLACEMENTS.items():
            content = content.replace(emoji, replacement)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Fixed: {filepath.name}")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] Failed to fix {filepath.name}: {e}")
        return False

def main():
    backend_dir = Path(__file__).parent
    python_files = list(backend_dir.glob('*.py'))
    
    fixed_count = 0
    for filepath in python_files:
        if filepath.name == 'fix_encoding.py':
            continue
        if fix_file(filepath):
            fixed_count += 1
    
    print(f"\n[OK] Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
