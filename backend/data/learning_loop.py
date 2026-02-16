"""
Valora AI - Learning Loop Module
Foundation for prediction logging, evaluation, and continuous improvement.
Supports future city expansion and accuracy tracking.
"""

import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

# Database path
DB_PATH = Path(__file__).parent.parent / "storage" / "valora.db"


@dataclass
class Prediction:
    """A prediction record for tracking accuracy."""
    prediction_id: str
    locality_id: str
    city_id: str
    prediction_type: str  # 'price_change', 'growth_phase', 'risk_level', etc.
    predicted_value: Any
    confidence: float
    target_date: str
    created_at: str
    actual_value: Optional[Any] = None
    evaluated_at: Optional[str] = None
    accuracy_score: Optional[float] = None


class LearningLoop:
    """
    Learning loop for continuous model improvement.
    
    Features:
    - Log predictions with confidence scores
    - Evaluate predictions when target date arrives
    - Calculate accuracy metrics by locality, city, prediction type
    - Support for city expansion (multi-city architecture)
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def log_prediction(
        self,
        locality_id: str,
        city_id: str,
        prediction_type: str,
        predicted_value: Any,
        confidence: float,
        target_date: str,
        metadata: Dict = None
    ) -> str:
        """
        Log a prediction for future evaluation.
        
        Args:
            locality_id: ID of the locality
            city_id: City identifier (e.g., 'BLR', 'HYD', 'CHN')
            prediction_type: Type of prediction (price_change, growth_phase, etc.)
            predicted_value: The predicted value
            confidence: Confidence score (0-100)
            target_date: Date when prediction should be evaluated
            metadata: Additional context
        
        Returns:
            prediction_id: Unique ID for the prediction
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        prediction_id = f"{locality_id}_{prediction_type}_{target_date}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO prediction_logs 
            (prediction_id, locality_id, city_id, prediction_type, predicted_value, 
             confidence, target_date, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_id,
            locality_id,
            city_id,
            prediction_type,
            json.dumps(predicted_value) if isinstance(predicted_value, (dict, list)) else str(predicted_value),
            confidence,
            target_date,
            json.dumps(metadata) if metadata else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return prediction_id
    
    def evaluate_prediction(
        self,
        prediction_id: str,
        actual_value: Any
    ) -> Dict[str, Any]:
        """
        Evaluate a prediction against actual value.
        
        Args:
            prediction_id: ID of the prediction
            actual_value: The actual observed value
        
        Returns:
            Evaluation result with accuracy score
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM prediction_logs WHERE prediction_id = ?
        """, (prediction_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "message": "Prediction not found"}
        
        predicted = row['predicted_value']
        prediction_type = row['prediction_type']
        
        # Calculate accuracy based on prediction type
        if prediction_type in ['price_change', 'growth_rate']:
            # Numeric comparison
            try:
                predicted_num = float(predicted)
                actual_num = float(actual_value)
                error = abs(predicted_num - actual_num)
                accuracy = max(0, 100 - (error * 10))  # 10% error = 0% accuracy
            except:
                accuracy = 0
        elif prediction_type in ['growth_phase', 'risk_level', 'archetype']:
            # Categorical comparison
            accuracy = 100 if str(predicted).lower() == str(actual_value).lower() else 0
        else:
            # Default: exact match
            accuracy = 100 if str(predicted) == str(actual_value) else 50
        
        # Update prediction with actual value and accuracy
        cursor.execute("""
            UPDATE prediction_logs 
            SET actual_value = ?, accuracy_score = ?, evaluated_at = ?
            WHERE prediction_id = ?
        """, (
            json.dumps(actual_value) if isinstance(actual_value, (dict, list)) else str(actual_value),
            accuracy,
            datetime.now().isoformat(),
            prediction_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "prediction_id": prediction_id,
            "predicted": predicted,
            "actual": actual_value,
            "accuracy_score": accuracy
        }
    
    def get_accuracy_metrics(self, city_id: str = None, prediction_type: str = None) -> Dict[str, Any]:
        """
        Get accuracy metrics for evaluated predictions.
        
        Args:
            city_id: Filter by city (optional)
            prediction_type: Filter by prediction type (optional)
        
        Returns:
            Accuracy metrics and statistics
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN actual_value IS NOT NULL THEN 1 END) as evaluated,
                AVG(CASE WHEN accuracy_score IS NOT NULL THEN accuracy_score END) as avg_accuracy,
                MIN(accuracy_score) as min_accuracy,
                MAX(accuracy_score) as max_accuracy
            FROM prediction_logs
            WHERE 1=1
        """
        params = []
        
        if city_id:
            query += " AND city_id = ?"
            params.append(city_id)
        if prediction_type:
            query += " AND prediction_type = ?"
            params.append(prediction_type)
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        # Get breakdown by prediction type
        cursor.execute("""
            SELECT prediction_type, 
                   COUNT(*) as count,
                   AVG(accuracy_score) as avg_accuracy
            FROM prediction_logs
            WHERE accuracy_score IS NOT NULL
            GROUP BY prediction_type
        """)
        
        by_type = {r['prediction_type']: {
            'count': r['count'],
            'avg_accuracy': round(r['avg_accuracy'], 1) if r['avg_accuracy'] else None
        } for r in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_predictions": row['total_predictions'],
            "evaluated": row['evaluated'],
            "pending": row['total_predictions'] - (row['evaluated'] or 0),
            "avg_accuracy": round(row['avg_accuracy'], 1) if row['avg_accuracy'] else None,
            "min_accuracy": row['min_accuracy'],
            "max_accuracy": row['max_accuracy'],
            "by_type": by_type
        }
    
    def get_pending_evaluations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get predictions that are due for evaluation."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT prediction_id, locality_id, city_id, prediction_type, 
                   predicted_value, confidence, target_date, created_at
            FROM prediction_logs
            WHERE actual_value IS NULL AND target_date <= ?
            ORDER BY target_date ASC
            LIMIT ?
        """, (today, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def log_query_feedback(
        self,
        session_id: str,
        query: str,
        response: str,
        intent: str,
        locality: str = None,
        rating: int = None,
        feedback: str = None
    ):
        """
        Log user feedback on query responses for future improvement.
        
        Args:
            session_id: User session ID
            query: The user's query
            response: AI response
            intent: Classified intent
            locality: Related locality (if any)
            rating: User rating (1-5)
            feedback: Text feedback
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Use ai_feedback table if it exists
        try:
            cursor.execute("""
                INSERT INTO ai_feedback 
                (session_id, query, response, intent, locality, rating, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                query[:1000],  # Truncate long queries
                response[:2000],  # Truncate long responses
                intent,
                locality,
                rating,
                feedback,
                datetime.now().isoformat()
            ))
            conn.commit()
        except sqlite3.OperationalError:
            # Table doesn't exist - ignore silently
            pass
        
        conn.close()


# City expansion helper
class CityManager:
    """
    Manager for multi-city expansion.
    
    Supports adding new cities with their own:
    - Locality states
    - Property data
    - POIs and transport
    - Market metrics
    """
    
    SUPPORTED_CITIES = {
        'BLR': {'name': 'Bangalore', 'state': 'Karnataka', 'lat': 12.9716, 'lng': 77.5946},
        'HYD': {'name': 'Hyderabad', 'state': 'Telangana', 'lat': 17.3850, 'lng': 78.4867},
        'CHN': {'name': 'Chennai', 'state': 'Tamil Nadu', 'lat': 13.0827, 'lng': 80.2707},
        'PNE': {'name': 'Pune', 'state': 'Maharashtra', 'lat': 18.5204, 'lng': 73.8567},
        'MUM': {'name': 'Mumbai', 'state': 'Maharashtra', 'lat': 19.0760, 'lng': 72.8777},
        'DEL': {'name': 'Delhi', 'state': 'Delhi', 'lat': 28.6139, 'lng': 77.2090},
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_active_cities(self) -> List[Dict[str, Any]]:
        """Get cities with data in the system."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT city_id, city_name, state, latitude, longitude, 
                       property_count, poi_count, locality_count, is_active
                FROM cities
                WHERE is_active = 1
            """)
            cities = [dict(row) for row in cursor.fetchall()]
        except:
            # Fallback to default
            cities = [self.SUPPORTED_CITIES['BLR']]
        
        conn.close()
        return cities
    
    def get_city_stats(self, city_id: str) -> Dict[str, Any]:
        """Get statistics for a specific city."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        stats = {}
        
        # Property count
        cursor.execute("SELECT COUNT(*) FROM properties WHERE city_id = ?", (city_id,))
        stats['properties'] = cursor.fetchone()[0]
        
        # Locality count
        cursor.execute("SELECT COUNT(*) FROM locality_state WHERE city_id = ?", (city_id,))
        stats['localities'] = cursor.fetchone()[0]
        
        # POI count
        cursor.execute("SELECT COUNT(*) FROM pois WHERE city_id = ?", (city_id,))
        stats['pois'] = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "city_id": city_id,
            "city_info": self.SUPPORTED_CITIES.get(city_id, {}),
            "stats": stats
        }


# Singleton instances
_learning_loop = None
_city_manager = None

def get_learning_loop() -> LearningLoop:
    """Get or create learning loop singleton."""
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = LearningLoop()
    return _learning_loop

def get_city_manager() -> CityManager:
    """Get or create city manager singleton."""
    global _city_manager
    if _city_manager is None:
        _city_manager = CityManager()
    return _city_manager
