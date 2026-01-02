"""
Model Retraining Service
Handles incremental and safe model retraining with validation
"""

import os
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import json

from backend.services.dmpe_engine import DMPEEngine
from backend.services.data_processor import DataProcessor
from backend.utils.logger import LoggerMixin

logger = logging.getLogger(__name__)

class ModelRetrainingService(LoggerMixin):
    """Service for automated model retraining"""
    
    def __init__(self, models_dir: str = "data/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.backup_dir = self.models_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.metrics_dir = self.models_dir / "metrics"
        self.metrics_dir.mkdir(exist_ok=True)
        
        self.dmpe_engine = DMPEEngine(str(self.models_dir))
        self.data_processor = DataProcessor()
        
        # Retraining configuration
        self.min_samples_for_retrain = 100
        self.min_improvement_threshold = 0.02  # 2% improvement required
        self.max_degradation_threshold = 0.05  # Max 5% degradation allowed
        
        self.log_info("ModelRetrainingService initialized")
    
    def get_retraining_status(self) -> Dict[str, Any]:
        """Get current retraining status and history"""
        status_file = self.models_dir / "retraining_status.json"
        
        if status_file.exists():
            with open(status_file, 'r') as f:
                return json.load(f)
        
        return {
            "last_retrain": None,
            "next_scheduled": None,
            "total_retrains": 0,
            "last_metrics": {},
            "status": "never_trained"
        }
    
    def update_retraining_status(self, status_update: Dict[str, Any]):
        """Update retraining status file"""
        status_file = self.models_dir / "retraining_status.json"
        
        current_status = self.get_retraining_status()
        current_status.update(status_update)
        current_status["last_updated"] = datetime.now().isoformat()
        
        with open(status_file, 'w') as f:
            json.dump(current_status, f, indent=2)
    
    def check_if_retraining_needed(self) -> Tuple[bool, str]:
        """
        Check if retraining is needed based on various criteria
        Returns: (should_retrain, reason)
        """
        status = self.get_retraining_status()
        
        # Check 1: Never trained
        if not status.get("last_retrain"):
            return True, "Models never trained"
        
        # Check 2: Time-based - retrain every 7 days
        last_retrain = datetime.fromisoformat(status["last_retrain"])
        days_since_retrain = (datetime.now() - last_retrain).days
        
        if days_since_retrain >= 7:
            return True, f"Time-based: {days_since_retrain} days since last retrain"
        
        # Check 3: Data drift - check if new data available
        # This would check database for new records
        # For now, we'll use a placeholder
        
        # Check 4: Performance degradation
        # This would monitor production predictions vs actuals
        # For now, we'll skip this check
        
        return False, "No retraining needed"
    
    def backup_current_models(self) -> Dict[str, str]:
        """Backup current models before retraining"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_paths = {}
        
        model_files = [
            "price_model.pkl",
            "rental_yield_model.pkl",
            "demand_model.pkl",
            "scalers.pkl"
        ]
        
        for model_file in model_files:
            src_path = self.models_dir / model_file
            if src_path.exists():
                dst_path = self.backup_dir / f"{model_file.replace('.pkl', '')}_{timestamp}.pkl"
                joblib.dump(joblib.load(src_path), dst_path)
                backup_paths[model_file] = str(dst_path)
                self.log_info(f"Backed up {model_file} to {dst_path}")
        
        return backup_paths
    
    def restore_models_from_backup(self, backup_paths: Dict[str, str]) -> bool:
        """Restore models from backup if new models fail validation"""
        try:
            for model_file, backup_path in backup_paths.items():
                src_path = Path(backup_path)
                dst_path = self.models_dir / model_file
                
                if src_path.exists():
                    model = joblib.load(src_path)
                    joblib.dump(model, dst_path)
                    self.log_info(f"Restored {model_file} from backup")
            
            return True
        except Exception as e:
            self.log_error(f"Failed to restore from backup: {e}", exc_info=True)
            return False
    
    def validate_model_performance(
        self, 
        model, 
        X_test: pd.DataFrame, 
        y_test: pd.Series,
        previous_metrics: Dict[str, float]
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Validate new model performance against previous version
        Returns: (is_valid, new_metrics)
        """
        try:
            # Get predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            new_metrics = {
                "mae": mean_absolute_error(y_test, y_pred),
                "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
                "r2": r2_score(y_test, y_pred),
                "mape": np.mean(np.abs((y_test - y_pred) / y_test)) * 100 if hasattr(y_test, '__len__') else 0
            }
            
            # If no previous metrics, accept new model
            if not previous_metrics or "r2" not in previous_metrics:
                self.log_info("No previous metrics found, accepting new model")
                return True, new_metrics
            
            # Check for improvement or acceptable degradation
            r2_change = new_metrics["r2"] - previous_metrics["r2"]
            
            if r2_change >= self.min_improvement_threshold:
                self.log_info(f"Model improved by {r2_change:.4f}")
                return True, new_metrics
            elif r2_change >= -self.max_degradation_threshold:
                self.log_info(f"Model performance acceptable (R² change: {r2_change:.4f})")
                return True, new_metrics
            else:
                self.log_warning(f"Model degraded significantly (R² change: {r2_change:.4f})")
                return False, new_metrics
            
        except Exception as e:
            self.log_error(f"Model validation failed: {e}", exc_info=True)
            return False, {}
    
    def retrain_price_model(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Retrain price prediction model"""
        self.log_info("Starting price model retraining...")
        
        try:
            # Get previous metrics
            status = self.get_retraining_status()
            previous_metrics = status.get("last_metrics", {}).get("price_model", {})
            
            # Train new model
            new_metrics = self.dmpe_engine.train_price_model(data)
            
            # Load and validate new model
            if self.dmpe_engine.price_model:
                # Prepare test data
                features = self.dmpe_engine._engineer_features(data)
                X = features[self.dmpe_engine.property_features + 
                           self.dmpe_engine.spatial_features + 
                           self.dmpe_engine.market_features]
                y = data['price']
                X = X.fillna(X.median())
                
                _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                if 'price' in self.dmpe_engine.scalers:
                    X_test_scaled = self.dmpe_engine.scalers['price'].transform(X_test)
                    is_valid, validation_metrics = self.validate_model_performance(
                        self.dmpe_engine.price_model,
                        X_test_scaled,
                        y_test,
                        previous_metrics
                    )
                    
                    if is_valid:
                        self.log_info("Price model validation passed")
                        return {
                            "status": "success",
                            "model": "price_model",
                            "metrics": new_metrics,
                            "validation_metrics": validation_metrics
                        }
                    else:
                        self.log_warning("Price model validation failed")
                        return {
                            "status": "validation_failed",
                            "model": "price_model",
                            "metrics": new_metrics
                        }
            
            return {
                "status": "training_failed",
                "model": "price_model"
            }
            
        except Exception as e:
            self.log_error(f"Price model retraining failed: {e}", exc_info=True)
            return {
                "status": "error",
                "model": "price_model",
                "error": str(e)
            }
    
    def retrain_rental_yield_model(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Retrain rental yield model"""
        self.log_info("Starting rental yield model retraining...")
        
        try:
            # Get previous metrics
            status = self.get_retraining_status()
            previous_metrics = status.get("last_metrics", {}).get("rental_yield_model", {})
            
            # Train new model
            new_metrics = self.dmpe_engine.train_rental_yield_model(data)
            
            if new_metrics:
                self.log_info("Rental yield model retrained successfully")
                return {
                    "status": "success",
                    "model": "rental_yield_model",
                    "metrics": new_metrics
                }
            else:
                return {
                    "status": "training_failed",
                    "model": "rental_yield_model"
                }
            
        except Exception as e:
            self.log_error(f"Rental yield model retraining failed: {e}", exc_info=True)
            return {
                "status": "error",
                "model": "rental_yield_model",
                "error": str(e)
            }
    
    def retrain_demand_model(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Retrain demand index model"""
        self.log_info("Starting demand model retraining...")
        
        try:
            # Get previous metrics
            status = self.get_retraining_status()
            previous_metrics = status.get("last_metrics", {}).get("demand_model", {})
            
            # Train new model
            new_metrics = self.dmpe_engine.train_demand_model(data)
            
            if new_metrics:
                self.log_info("Demand model retrained successfully")
                return {
                    "status": "success",
                    "model": "demand_model",
                    "metrics": new_metrics
                }
            else:
                return {
                    "status": "training_failed",
                    "model": "demand_model"
                }
            
        except Exception as e:
            self.log_error(f"Demand model retraining failed: {e}", exc_info=True)
            return {
                "status": "error",
                "model": "demand_model",
                "error": str(e)
            }
    
    def perform_full_retraining(self, force: bool = False) -> Dict[str, Any]:
        """
        Perform full retraining of all models
        
        Args:
            force: Force retraining even if not needed
        
        Returns:
            Dictionary with retraining results
        """
        self.log_info("=" * 60)
        self.log_info("Starting full model retraining pipeline")
        self.log_info("=" * 60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "forced": force,
            "models": {},
            "overall_status": "success"
        }
        
        try:
            # Step 1: Check if retraining needed
            if not force:
                should_retrain, reason = self.check_if_retraining_needed()
                if not should_retrain:
                    self.log_info(f"Retraining not needed: {reason}")
                    results["overall_status"] = "skipped"
                    results["reason"] = reason
                    return results
                else:
                    self.log_info(f"Retraining triggered: {reason}")
                    results["reason"] = reason
            
            # Step 2: Load fresh training data
            self.log_info("Loading training data...")
            data = self.data_processor.load_training_data()
            
            if len(data) < self.min_samples_for_retrain:
                self.log_warning(f"Insufficient data: {len(data)} < {self.min_samples_for_retrain}")
                results["overall_status"] = "insufficient_data"
                return results
            
            self.log_info(f"Loaded {len(data)} training samples")
            results["training_samples"] = len(data)
            
            # Step 3: Validate data quality
            self.log_info("Validating data quality...")
            data = self.data_processor.validate_data(data)
            self.log_info(f"Data validation passed: {len(data)} valid samples")
            
            # Step 4: Backup current models
            self.log_info("Backing up current models...")
            backup_paths = self.backup_current_models()
            results["backups"] = backup_paths
            
            # Step 5: Retrain each model
            all_success = True
            
            # Price model
            self.log_info("\n" + "=" * 40)
            price_result = self.retrain_price_model(data)
            results["models"]["price_model"] = price_result
            if price_result["status"] != "success":
                all_success = False
            
            # Rental yield model
            self.log_info("\n" + "=" * 40)
            rental_result = self.retrain_rental_yield_model(data)
            results["models"]["rental_yield_model"] = rental_result
            if rental_result["status"] != "success":
                all_success = False
            
            # Demand model
            self.log_info("\n" + "=" * 40)
            demand_result = self.retrain_demand_model(data)
            results["models"]["demand_model"] = demand_result
            if demand_result["status"] != "success":
                all_success = False
            
            # Step 6: Save models if all successful
            if all_success:
                self.log_info("\n" + "=" * 40)
                self.log_info("All models retrained successfully, saving...")
                self.dmpe_engine.save_all_models()
                
                # Update retraining status
                self.update_retraining_status({
                    "last_retrain": datetime.now().isoformat(),
                    "total_retrains": self.get_retraining_status().get("total_retrains", 0) + 1,
                    "last_metrics": {
                        "price_model": price_result.get("metrics", {}),
                        "rental_yield_model": rental_result.get("metrics", {}),
                        "demand_model": demand_result.get("metrics", {})
                    },
                    "status": "success"
                })
                
                results["overall_status"] = "success"
            else:
                self.log_error("Some models failed retraining, restoring from backup...")
                self.restore_models_from_backup(backup_paths)
                results["overall_status"] = "partial_failure"
                
                self.update_retraining_status({
                    "status": "failed",
                    "last_attempt": datetime.now().isoformat()
                })
            
            # Step 7: Save metrics
            self.save_retraining_metrics(results)
            
            self.log_info("\n" + "=" * 60)
            self.log_info(f"Retraining pipeline completed: {results['overall_status']}")
            self.log_info("=" * 60)
            
            return results
            
        except Exception as e:
            self.log_error(f"Retraining pipeline failed: {e}", exc_info=True)
            results["overall_status"] = "error"
            results["error"] = str(e)
            
            # Try to restore from backup
            if results.get("backups"):
                self.restore_models_from_backup(results["backups"])
            
            return results
    
    def save_retraining_metrics(self, results: Dict[str, Any]):
        """Save retraining metrics to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.metrics_dir / f"retraining_metrics_{timestamp}.json"
        
        with open(metrics_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.log_info(f"Saved retraining metrics to {metrics_file}")
    
    def get_retraining_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get retraining history"""
        metrics_files = sorted(self.metrics_dir.glob("retraining_metrics_*.json"), reverse=True)
        
        history = []
        for metrics_file in metrics_files[:limit]:
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    history.append(data)
            except Exception as e:
                self.log_error(f"Failed to load {metrics_file}: {e}")
        
        return history
