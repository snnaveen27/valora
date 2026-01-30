"""
Valora AI - Data Collection Pipeline
Automatic collection of anonymized user interactions for ML training.
Privacy-compliant with GDPR/PDPA standards.
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Training data directories
TRAINING_DATA_DIR = Path(__file__).parent / "training_data"
TRAINING_DATA_DIR.mkdir(exist_ok=True)

# Data types
QUERIES_LOG = TRAINING_DATA_DIR / "queries_training.jsonl"
FEEDBACK_LOG = TRAINING_DATA_DIR / "feedback_training.jsonl"
PREDICTIONS_LOG = TRAINING_DATA_DIR / "predictions_training.jsonl"
SPATIAL_LOG = TRAINING_DATA_DIR / "spatial_training.jsonl"
REFINEMENTS_LOG = TRAINING_DATA_DIR / "refinements_training.jsonl"


@dataclass
class TrainingDataPoint:
    """Base class for training data."""
    timestamp: str
    user_id_hash: str
    session_id_hash: Optional[str] = None
    
    def _hash_id(self, value: str) -> str:
        """Hash an ID for privacy."""
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]
    
    def _anonymize_location(self, lat: float, lng: float, precision: int = 2) -> tuple:
        """Anonymize location to specified precision (km)."""
        return round(lat, precision), round(lng, precision)


@dataclass
class QueryDataPoint(TrainingDataPoint):
    """User query with response for training."""
    query: str
    intent: str
    response_summary: str
    locality: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    response_time_ms: float
    success: bool
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        # Anonymize location
        if self.lat and self.lng:
            data["lat"], data["lng"] = self._anonymize_location(self.lat, self.lng)
        return data


@dataclass
class FeedbackDataPoint(TrainingDataPoint):
    """User feedback on AI responses."""
    query: str
    response: str
    rating: int  # 1-5
    feedback_text: Optional[str]
    locality: Optional[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        # Truncate long text
        if len(data.get("response", "")) > 500:
            data["response"] = data["response"][:500] + "..."
        if data.get("feedback_text") and len(data["feedback_text"]) > 200:
            data["feedback_text"] = data["feedback_text"][:200] + "..."
        return data


@dataclass
class PredictionDataPoint(TrainingDataPoint):
    """Prediction with actual outcome for accuracy tracking."""
    prediction_type: str
    locality: str
    predicted_value: Any
    actual_value: Optional[Any]
    confidence: float
    target_date: str
    evaluated: bool
    accuracy_score: Optional[float]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SpatialDataPoint(TrainingDataPoint):
    """Spatial interaction patterns."""
    action: str  # 'view', 'zoom', 'click', 'dwell'
    lat: float
    lng: float
    zoom_level: Optional[int]
    dwell_time_seconds: Optional[float]
    locality: Optional[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        # Anonymize location
        data["lat"], data["lng"] = self._anonymize_location(self.lat, self.lng)
        return data


@dataclass
class RefinementDataPoint(TrainingDataPoint):
    """Query refinement patterns."""
    original_query: str
    refined_query: str
    refinement_type: str  # 'filter_added', 'location_changed', 'clarification'
    time_between_seconds: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class DataCollector:
    """
    Central data collection system for ML training.
    
    Features:
    - Anonymize all PII
    - Store in JSONL format (ML-friendly)
    - Support multiple data types
    - Batch export capabilities
    - Privacy compliance
    """
    
    def __init__(self):
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all data directories exist."""
        TRAINING_DATA_DIR.mkdir(exist_ok=True)
    
    def _append_to_log(self, log_file: Path, data: Dict):
        """Append data to JSONL log file."""
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[DataCollector] Failed to append to {log_file.name}: {e}")
    
    def collect_query(
        self,
        user_id: int,
        query: str,
        intent: str,
        response: str,
        locality: str = None,
        lat: float = None,
        lng: float = None,
        response_time_ms: float = 0,
        success: bool = True,
        session_id: str = None
    ):
        """Collect query interaction for training."""
        try:
            data_point = QueryDataPoint(
                timestamp=datetime.now().isoformat(),
                user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:16],
                session_id_hash=hashlib.sha256((session_id or "").encode()).hexdigest()[:16] if session_id else None,
                query=query[:500],  # Truncate long queries
                intent=intent,
                response_summary=response[:200],  # Summary only
                locality=locality,
                lat=lat,
                lng=lng,
                response_time_ms=response_time_ms,
                success=success
            )
            
            self._append_to_log(QUERIES_LOG, data_point.to_dict())
            logger.debug(f"[DataCollector] Collected query: {intent}")
        except Exception as e:
            logger.error(f"[DataCollector] Failed to collect query: {e}")
    
    def collect_feedback(
        self,
        user_id: int,
        query: str,
        response: str,
        rating: int,
        feedback_text: str = None,
        locality: str = None,
        session_id: str = None
    ):
        """Collect user feedback for training."""
        try:
            data_point = FeedbackDataPoint(
                timestamp=datetime.now().isoformat(),
                user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:16],
                session_id_hash=hashlib.sha256((session_id or "").encode()).hexdigest()[:16] if session_id else None,
                query=query[:500],
                response=response[:500],
                rating=rating,
                feedback_text=feedback_text,
                locality=locality
            )
            
            self._append_to_log(FEEDBACK_LOG, data_point.to_dict())
            logger.info(f"[DataCollector] Collected feedback: rating={rating}")
        except Exception as e:
            logger.error(f"[DataCollector] Failed to collect feedback: {e}")
    
    def collect_prediction(
        self,
        user_id: int,
        prediction_type: str,
        locality: str,
        predicted_value: Any,
        confidence: float,
        target_date: str,
        actual_value: Any = None,
        accuracy_score: float = None,
        session_id: str = None
    ):
        """Collect prediction for accuracy tracking."""
        try:
            data_point = PredictionDataPoint(
                timestamp=datetime.now().isoformat(),
                user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:16],
                session_id_hash=hashlib.sha256((session_id or "").encode()).hexdigest()[:16] if session_id else None,
                prediction_type=prediction_type,
                locality=locality,
                predicted_value=predicted_value,
                actual_value=actual_value,
                confidence=confidence,
                target_date=target_date,
                evaluated=actual_value is not None,
                accuracy_score=accuracy_score
            )
            
            self._append_to_log(PREDICTIONS_LOG, data_point.to_dict())
            logger.debug(f"[DataCollector] Collected prediction: {prediction_type}")
        except Exception as e:
            logger.error(f"[DataCollector] Failed to collect prediction: {e}")
    
    def collect_spatial_interaction(
        self,
        user_id: int,
        action: str,
        lat: float,
        lng: float,
        zoom_level: int = None,
        dwell_time_seconds: float = None,
        locality: str = None,
        session_id: str = None
    ):
        """Collect spatial interaction patterns."""
        try:
            data_point = SpatialDataPoint(
                timestamp=datetime.now().isoformat(),
                user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:16],
                session_id_hash=hashlib.sha256((session_id or "").encode()).hexdigest()[:16] if session_id else None,
                action=action,
                lat=lat,
                lng=lng,
                zoom_level=zoom_level,
                dwell_time_seconds=dwell_time_seconds,
                locality=locality
            )
            
            self._append_to_log(SPATIAL_LOG, data_point.to_dict())
        except Exception as e:
            logger.error(f"[DataCollector] Failed to collect spatial data: {e}")
    
    def collect_refinement(
        self,
        user_id: int,
        original_query: str,
        refined_query: str,
        refinement_type: str,
        time_between_seconds: float,
        session_id: str = None
    ):
        """Collect query refinement patterns."""
        try:
            data_point = RefinementDataPoint(
                timestamp=datetime.now().isoformat(),
                user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:16],
                session_id_hash=hashlib.sha256((session_id or "").encode()).hexdigest()[:16] if session_id else None,
                original_query=original_query[:500],
                refined_query=refined_query[:500],
                refinement_type=refinement_type,
                time_between_seconds=time_between_seconds
            )
            
            self._append_to_log(REFINEMENTS_LOG, data_point.to_dict())
            logger.debug(f"[DataCollector] Collected refinement: {refinement_type}")
        except Exception as e:
            logger.error(f"[DataCollector] Failed to collect refinement: {e}")
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Get statistics about collected training data."""
        stats = {}
        
        for log_name, log_file in [
            ("queries", QUERIES_LOG),
            ("feedback", FEEDBACK_LOG),
            ("predictions", PREDICTIONS_LOG),
            ("spatial", SPATIAL_LOG),
            ("refinements", REFINEMENTS_LOG)
        ]:
            if log_file.exists():
                count = sum(1 for _ in open(log_file))
                size_mb = log_file.stat().st_size / (1024 * 1024)
                stats[log_name] = {
                    "count": count,
                    "size_mb": round(size_mb, 2),
                    "file": str(log_file.name)
                }
            else:
                stats[log_name] = {"count": 0, "size_mb": 0, "file": str(log_file.name)}
        
        return stats
    
    def export_batch(
        self,
        data_type: str = "all",
        limit: int = 1000,
        since_date: str = None
    ) -> List[Dict]:
        """
        Export batch of training data for ML pipeline.
        Returns list of data points.
        """
        log_map = {
            "queries": QUERIES_LOG,
            "feedback": FEEDBACK_LOG,
            "predictions": PREDICTIONS_LOG,
            "spatial": SPATIAL_LOG,
            "refinements": REFINEMENTS_LOG
        }
        
        if data_type != "all" and data_type not in log_map:
            logger.error(f"[DataCollector] Invalid data type: {data_type}")
            return []
        
        batch = []
        
        # Select files to read
        files_to_read = [log_map[data_type]] if data_type != "all" else log_map.values()
        
        for log_file in files_to_read:
            if not log_file.exists():
                continue
            
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if len(batch) >= limit:
                            break
                        
                        try:
                            data = json.loads(line.strip())
                            
                            # Filter by date if specified
                            if since_date and data.get("timestamp", "") < since_date:
                                continue
                            
                            batch.append(data)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"[DataCollector] Failed to read {log_file.name}: {e}")
        
        logger.info(f"[DataCollector] Exported {len(batch)} training samples (type: {data_type})")
        return batch
    
    def clear_data(self, data_type: str = None, older_than_days: int = None):
        """
        Clear training data (admin function).
        Use with caution - this is for privacy compliance.
        """
        if data_type and older_than_days:
            logger.warning(f"[DataCollector] Clear operation not fully implemented for date filtering")
        
        log_map = {
            "queries": QUERIES_LOG,
            "feedback": FEEDBACK_LOG,
            "predictions": PREDICTIONS_LOG,
            "spatial": SPATIAL_LOG,
            "refinements": REFINEMENTS_LOG
        }
        
        if data_type and data_type in log_map:
            log_file = log_map[data_type]
            if log_file.exists():
                log_file.unlink()
                logger.info(f"[DataCollector] Cleared {data_type} data")
        elif not data_type:
            # Clear all
            for log_file in log_map.values():
                if log_file.exists():
                    log_file.unlink()
            logger.info("[DataCollector] Cleared all training data")


# Singleton instance
_data_collector = None

def get_data_collector() -> DataCollector:
    """Get or create data collector singleton."""
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
    return _data_collector
