import argparse
import os
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
import json

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
TESTS_DIR = ROOT / "tests"

MOVE_RULES: List[Tuple[str, Path]] = [
    # Move root-level docs into docs/
    ("*_COMPLETE.md", DOCS_DIR),
    ("*_SUMMARY.md", DOCS_DIR),
    ("*_STATUS.md", DOCS_DIR),
    ("*_WORKFLOW.md", DOCS_DIR),
    ("*_QUICKSTART.md", DOCS_DIR),
    ("UNIFIED_ENVIRONMENT_SETUP.md", DOCS_DIR),
    ("AIRFLOW_INTEGRATION_COMPLETE.md", DOCS_DIR),
    ("APIFY_AIRFLOW_COMPLETE.md", DOCS_DIR),
    ("MODEL_RETRAINING_COMPLETE.md", DOCS_DIR),
    ("PROJECT_CLEANUP_SUMMARY.md", DOCS_DIR),
    ("RETRAINING_IMPLEMENTATION_SUMMARY.md", DOCS_DIR),
    ("RETRAINING_QUICKSTART.md", DOCS_DIR),
    ("PINECONE_RAG_STATUS.md", DOCS_DIR),
    ("INDEXING_STATUS.md", DOCS_DIR),
    ("README.md", ROOT),  # keep readme at root (rule no-op)

    # Move root tests to tests/
    ("test_*.py", TESTS_DIR),
]

# Deletion rules kept empty for safety by default
DELETE_RULES: List[str] = [
    # Example candidates (disabled): "*.tmp", "*.bak"
]

EXCLUDES = {
    str(DOCS_DIR),
    str(TESTS_DIR),
    str(ROOT / ".venv"),
    str(ROOT / "node_modules"),
}


def should_exclude(p: Path) -> bool:
    try:
        for ex in EXCLUDES:
            if str(p).startswith(ex):
                return True
    except Exception:
        pass
    return False


def collect_moves() -> List[Tuple[Path, Path]]:
    actions: List[Tuple[Path, Path]] = []
    for pattern, dest in MOVE_RULES:
        for src in ROOT.glob(pattern):
            if not src.is_file():
                continue
            if should_exclude(src):
                continue
            if dest == ROOT:
                # no-op rule (e.g., keep README.md at root)
                continue
            target_dir = dest
            target_dir.mkdir(parents=True, exist_ok=True)
            dst = target_dir / src.name
            if src.resolve() == dst.resolve():
                continue
            actions.append((src, dst))
    return actions


def collect_deletes() -> List[Path]:
    actions: List[Path] = []
    for pattern in DELETE_RULES:
        for src in ROOT.glob(pattern):
            if not src.exists():
                continue
            if should_exclude(src):
                continue
            actions.append(src)
    return actions


def run(dry_run: bool = True) -> Dict:
    moves = collect_moves()
    deletes = collect_deletes()

    summary = {
        "root": str(ROOT),
        "dry_run": dry_run,
        "moves": [{"src": str(s), "dst": str(d)} for s, d in moves],
        "deletes": [str(p) for p in deletes],
    }

    if dry_run:
        print(json.dumps(summary, indent=2))
        return summary

    # Apply moves with robust error handling
    moved = []
    failed = []
    for src, dst in moves:
        try:
            if not src.exists():
                failed.append({"src": str(src), "dst": str(dst), "error": "source_missing"})
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved.append({"src": str(src), "dst": str(dst)})
        except Exception as e:
            failed.append({"src": str(src), "dst": str(dst), "error": str(e)})

    # Apply deletes
    for p in deletes:
        if p.is_file():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

    applied = {
        "root": str(ROOT),
        "dry_run": False,
        "moved_count": len(moved),
        "failed_count": len(failed),
        "moved": moved,
        "failed": failed,
        "deleted": [str(p) for p in deletes],
    }
    print(json.dumps(applied, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Project cleanup organizer")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    args = parser.parse_args()
    run(dry_run=not args.apply)
