"""
Runtime validation for production readiness.
"""

from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List


CRITICAL_DEPENDENCIES = {
    "scikit-learn": "1.4.0",
    "h3": "3.7.6",
}


def _is_strict_startup_enabled() -> bool:
    if os.getenv("VALORA_STRICT_STARTUP", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True

    env_markers = [
        os.getenv("VALORA_ENV", ""),
        os.getenv("APP_ENV", ""),
        os.getenv("ENV", ""),
        os.getenv("ENVIRONMENT", ""),
    ]
    return any(marker.strip().lower() in {"prod", "production"} for marker in env_markers)


def _check_dependency(package_name: str, expected_version: str) -> Dict[str, Any]:
    try:
        installed_version = metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return {
            "name": package_name,
            "expected": expected_version,
            "installed": None,
            "status": "missing",
            "message": f"{package_name} is not installed",
        }

    if installed_version != expected_version:
        return {
            "name": package_name,
            "expected": expected_version,
            "installed": installed_version,
            "status": "mismatch",
            "message": (
                f"{package_name} version mismatch: expected {expected_version}, "
                f"found {installed_version}"
            ),
        }

    return {
        "name": package_name,
        "expected": expected_version,
        "installed": installed_version,
        "status": "ok",
        "message": f"{package_name} version matches",
    }


def _check_valuation_artifacts(models_dir: Path) -> Dict[str, Any]:
    model_path = models_dir / "valuation_model.pkl"
    scaler_path = models_dir / "valuation_scaler.pkl"
    features_path = models_dir / "valuation_features.json"
    metadata_path = models_dir / "valuation_metadata.json"

    if not any(path.exists() for path in [model_path, scaler_path, features_path, metadata_path]):
        return {
            "status": "missing",
            "message": "No valuation artifacts present; heuristic fallback will be used",
        }

    missing_required = [
        path.name for path in [model_path, scaler_path, features_path] if not path.exists()
    ]
    if missing_required:
        return {
            "status": "invalid",
            "message": f"Incomplete valuation artifacts: missing {', '.join(missing_required)}",
        }

    if not metadata_path.exists():
        return {
            "status": "legacy",
            "message": "Valuation artifacts exist but have no metadata; retrain to record build versions",
        }

    try:
        import json

        with open(metadata_path, "r", encoding="utf-8") as f:
            artifact_metadata = json.load(f)
    except Exception as exc:
        return {
            "status": "invalid",
            "message": f"Unable to read valuation metadata: {exc}",
        }

    expected_sklearn = CRITICAL_DEPENDENCIES["scikit-learn"]
    trained_sklearn = artifact_metadata.get("sklearn_version")
    if trained_sklearn != expected_sklearn:
        return {
            "status": "incompatible",
            "message": (
                "Valuation artifacts were trained with sklearn "
                f"{trained_sklearn or 'unknown'}, expected {expected_sklearn}"
            ),
        }

    return {
        "status": "ok",
        "message": f"Valuation artifacts match sklearn {trained_sklearn}",
    }


def validate_runtime(models_dir: Path) -> Dict[str, Any]:
    dependency_checks = [
        _check_dependency(package_name, expected_version)
        for package_name, expected_version in CRITICAL_DEPENDENCIES.items()
    ]
    valuation_check = _check_valuation_artifacts(models_dir)

    errors: List[str] = []
    warnings: List[str] = []

    for check in dependency_checks:
        if check["status"] in {"missing", "mismatch"}:
            errors.append(check["message"])

    if valuation_check["status"] in {"invalid", "incompatible"}:
        errors.append(valuation_check["message"])
    elif valuation_check["status"] in {"legacy", "missing"}:
        warnings.append(valuation_check["message"])

    status = "healthy"
    if errors:
        status = "unhealthy"
    elif warnings:
        status = "degraded"

    return {
        "status": status,
        "strict_startup": _is_strict_startup_enabled(),
        "dependencies": dependency_checks,
        "valuation_artifacts": valuation_check,
        "errors": errors,
        "warnings": warnings,
    }


def enforce_runtime_requirements(models_dir: Path) -> Dict[str, Any]:
    validation = validate_runtime(models_dir)
    if validation["strict_startup"] and validation["errors"]:
        raise RuntimeError("Production startup validation failed: " + "; ".join(validation["errors"]))
    return validation
