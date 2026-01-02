"""
City Intelligence Repository
Production-ready database operations for city intelligence and prediction feedback.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import uuid

from sqlalchemy import text, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class CityIntelRepository:
    """
    Repository for city intelligence database operations.
    Provides clean interface for CRUD operations with proper error handling.
    """
    
    def __init__(self, db_manager=None):
        """Initialize with database manager"""
        self.db_manager = db_manager
        self._session = None
    
    @contextmanager
    def get_session(self):
        """Get database session with proper error handling"""
        if self.db_manager:
            with self.db_manager.get_session() as session:
                yield session
        else:
            # Fallback to direct connection
            from backend.database.connection import SessionLocal
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                session.close()
    
    # =====================================================
    # LOCALITY OPERATIONS
    # =====================================================
    
    async def get_localities(self, city: str = "bangalore") -> List[Dict[str, Any]]:
        """Get all localities for a city with current state"""
        try:
            with self.get_session() as session:
                result = session.execute(text("""
                    SELECT 
                        l.id, l.name, l.city, l.zone, l.pincode,
                        ls.avg_price_sqft, ls.price_change_12m, ls.growth_phase,
                        ls.risk_index_overall, ls.active_listings
                    FROM localities l
                    LEFT JOIN locality_state ls ON l.id = ls.locality_id
                    WHERE LOWER(l.city) = LOWER(:city)
                    ORDER BY l.name
                """), {"city": city})
                
                localities = []
                for row in result:
                    localities.append({
                        "id": str(row.id),
                        "name": row.name,
                        "city": row.city,
                        "zone": row.zone,
                        "avg_price_sqft": float(row.avg_price_sqft) if row.avg_price_sqft else None,
                        "price_change_12m": float(row.price_change_12m) if row.price_change_12m else None,
                        "growth_phase": row.growth_phase,
                        "risk_score": float(row.risk_index_overall) if row.risk_index_overall else None,
                        "active_listings": row.active_listings
                    })
                return localities
        except SQLAlchemyError as e:
            logger.error(f"Error getting localities: {e}")
            return []
    
    async def get_locality_state(self, locality: str, city: str = "bangalore") -> Optional[Dict[str, Any]]:
        """Get detailed state for a specific locality"""
        try:
            with self.get_session() as session:
                result = session.execute(text("""
                    SELECT 
                        l.id, l.name, l.city, l.zone, l.pincode,
                        ls.*
                    FROM localities l
                    LEFT JOIN locality_state ls ON l.id = ls.locality_id
                    WHERE LOWER(l.name) = LOWER(:locality) AND LOWER(l.city) = LOWER(:city)
                    LIMIT 1
                """), {"locality": locality, "city": city})
                
                row = result.fetchone()
                if not row:
                    return None
                
                return {
                    "locality": row.name,
                    "city": row.city,
                    "zone": row.zone,
                    "market_metrics": {
                        "avg_price_sqft": float(row.avg_price_sqft) if row.avg_price_sqft else None,
                        "median_price": float(row.median_price) if row.median_price else None,
                        "price_change_1m": float(row.price_change_1m) if row.price_change_1m else None,
                        "price_change_3m": float(row.price_change_3m) if row.price_change_3m else None,
                        "price_change_6m": float(row.price_change_6m) if row.price_change_6m else None,
                        "price_change_12m": float(row.price_change_12m) if row.price_change_12m else None
                    },
                    "supply_demand": {
                        "active_listings": row.active_listings,
                        "absorption_rate": float(row.absorption_rate) if row.absorption_rate else None,
                        "days_on_market_avg": float(row.days_on_market_avg) if row.days_on_market_avg else None,
                        "inventory_months": float(row.inventory_months) if row.inventory_months else None
                    },
                    "growth_phase": row.growth_phase,
                    "risk_metrics": {
                        "flood": float(row.risk_index_flood) if row.risk_index_flood else None,
                        "infrastructure": float(row.risk_index_infra) if row.risk_index_infra else None,
                        "liquidity": float(row.risk_index_liquidity) if row.risk_index_liquidity else None,
                        "regulatory": float(row.risk_index_regulatory) if row.risk_index_regulatory else None,
                        "market": float(row.risk_index_market) if row.risk_index_market else None,
                        "overall": float(row.risk_index_overall) if row.risk_index_overall else None
                    },
                    "forecasts": {
                        "price_6m": float(row.price_forecast_6m) if row.price_forecast_6m else None,
                        "price_1y": float(row.price_forecast_1y) if row.price_forecast_1y else None,
                        "price_3y": float(row.price_forecast_3y) if row.price_forecast_3y else None,
                        "confidence": float(row.forecast_confidence) if row.forecast_confidence else None
                    },
                    "computed_at": row.computed_at.isoformat() if row.computed_at else None
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting locality state: {e}")
            return None
    
    async def update_locality_state(
        self, 
        locality: str, 
        city: str,
        state_data: Dict[str, Any]
    ) -> bool:
        """Update locality state with new market data"""
        try:
            with self.get_session() as session:
                # Get locality ID
                result = session.execute(text("""
                    SELECT id FROM localities 
                    WHERE LOWER(name) = LOWER(:locality) AND LOWER(city) = LOWER(:city)
                """), {"locality": locality, "city": city})
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"Locality not found: {locality}, {city}")
                    return False
                
                locality_id = row.id
                
                # Upsert locality state
                session.execute(text("""
                    INSERT INTO locality_state (
                        locality_id, avg_price_sqft, median_price, 
                        price_change_1m, price_change_3m, price_change_6m, price_change_12m,
                        active_listings, growth_phase, risk_index_overall, computed_at
                    ) VALUES (
                        :locality_id, :avg_price, :median_price,
                        :change_1m, :change_3m, :change_6m, :change_12m,
                        :listings, :growth_phase, :risk_score, NOW()
                    )
                    ON CONFLICT (locality_id) DO UPDATE SET
                        avg_price_sqft = EXCLUDED.avg_price_sqft,
                        median_price = EXCLUDED.median_price,
                        price_change_1m = EXCLUDED.price_change_1m,
                        price_change_3m = EXCLUDED.price_change_3m,
                        price_change_6m = EXCLUDED.price_change_6m,
                        price_change_12m = EXCLUDED.price_change_12m,
                        active_listings = EXCLUDED.active_listings,
                        growth_phase = EXCLUDED.growth_phase,
                        risk_index_overall = EXCLUDED.risk_index_overall,
                        computed_at = NOW()
                """), {
                    "locality_id": locality_id,
                    "avg_price": state_data.get("avg_price_sqft"),
                    "median_price": state_data.get("median_price"),
                    "change_1m": state_data.get("price_change_1m"),
                    "change_3m": state_data.get("price_change_3m"),
                    "change_6m": state_data.get("price_change_6m"),
                    "change_12m": state_data.get("price_change_12m"),
                    "listings": state_data.get("active_listings"),
                    "growth_phase": state_data.get("growth_phase"),
                    "risk_score": state_data.get("risk_score")
                })
                
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating locality state: {e}")
            return False
    
    # =====================================================
    # PREDICTION OPERATIONS
    # =====================================================
    
    async def log_prediction(
        self,
        prediction_type: str,
        predicted_value: float,
        locality: str,
        city: str = "bangalore",
        property_id: Optional[str] = None,
        confidence: float = 0.85,
        model_version: str = "v2.1",
        features_used: Dict[str, Any] = None,
        target_date: Optional[datetime] = None
    ) -> str:
        """Log a new prediction for tracking"""
        prediction_id = f"pred_{uuid.uuid4().hex[:12]}"
        
        if target_date is None:
            if prediction_type == "price":
                target_date = datetime.now() + timedelta(days=90)
            elif prediction_type == "rental_yield":
                target_date = datetime.now() + timedelta(days=365)
            else:
                target_date = datetime.now() + timedelta(days=30)
        
        try:
            with self.get_session() as session:
                session.execute(text("""
                    INSERT INTO predictions (
                        prediction_id, prediction_type, property_id,
                        locality_name, city, predicted_value,
                        prediction_date, target_date, confidence,
                        model_version, features_used, feedback_status
                    ) VALUES (
                        :pred_id, :pred_type, :prop_id,
                        :locality, :city, :value,
                        NOW(), :target_date, :confidence,
                        :model_ver, :features, 'pending'
                    )
                """), {
                    "pred_id": prediction_id,
                    "pred_type": prediction_type,
                    "prop_id": property_id,
                    "locality": locality,
                    "city": city,
                    "value": predicted_value,
                    "target_date": target_date,
                    "confidence": confidence,
                    "model_ver": model_version,
                    "features": str(features_used) if features_used else None
                })
                
                logger.info(f"Logged prediction {prediction_id}")
                return prediction_id
        except SQLAlchemyError as e:
            logger.error(f"Error logging prediction: {e}")
            return ""
    
    async def submit_feedback(
        self,
        prediction_id: str,
        actual_value: float,
        feedback_source: str = "user"
    ) -> Dict[str, Any]:
        """Submit actual value feedback for a prediction"""
        try:
            with self.get_session() as session:
                # Get prediction
                result = session.execute(text("""
                    SELECT predicted_value FROM predictions
                    WHERE prediction_id = :pred_id
                """), {"pred_id": prediction_id})
                
                row = result.fetchone()
                if not row:
                    return {"success": False, "error": "Prediction not found"}
                
                predicted_value = float(row.predicted_value)
                error_pct = ((actual_value - predicted_value) / predicted_value) * 100 if predicted_value != 0 else 0
                
                # Update prediction
                session.execute(text("""
                    UPDATE predictions SET
                        actual_value = :actual,
                        error_percentage = :error_pct,
                        feedback_status = 'verified',
                        verified_date = NOW(),
                        feedback_source = :source,
                        updated_at = NOW()
                    WHERE prediction_id = :pred_id
                """), {
                    "actual": actual_value,
                    "error_pct": error_pct,
                    "source": feedback_source,
                    "pred_id": prediction_id
                })
                
                return {
                    "success": True,
                    "prediction_id": prediction_id,
                    "predicted_value": predicted_value,
                    "actual_value": actual_value,
                    "error_percentage": round(error_pct, 2)
                }
        except SQLAlchemyError as e:
            logger.error(f"Error submitting feedback: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_model_performance(
        self,
        model_version: Optional[str] = None,
        prediction_type: Optional[str] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """Get aggregated model performance metrics"""
        try:
            with self.get_session() as session:
                conditions = ["feedback_status = 'verified'"]
                params = {"days": days}
                
                if model_version:
                    conditions.append("model_version = :model_ver")
                    params["model_ver"] = model_version
                
                if prediction_type:
                    conditions.append("prediction_type = :pred_type")
                    params["pred_type"] = prediction_type
                
                where_clause = " AND ".join(conditions)
                
                result = session.execute(text(f"""
                    SELECT 
                        COUNT(*) as total,
                        AVG(ABS(error_percentage)) as mean_abs_error,
                        AVG(error_percentage) as bias,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ABS(error_percentage)) as median_error,
                        COUNT(*) FILTER (WHERE ABS(error_percentage) <= 5) * 100.0 / NULLIF(COUNT(*), 0) as acc_5pct,
                        COUNT(*) FILTER (WHERE ABS(error_percentage) <= 10) * 100.0 / NULLIF(COUNT(*), 0) as acc_10pct,
                        COUNT(*) FILTER (WHERE ABS(error_percentage) <= 20) * 100.0 / NULLIF(COUNT(*), 0) as acc_20pct
                    FROM predictions
                    WHERE {where_clause}
                        AND verified_date >= NOW() - INTERVAL '{days} days'
                """), params)
                
                row = result.fetchone()
                
                # Get total predictions count
                total_result = session.execute(text("""
                    SELECT COUNT(*) as total FROM predictions
                """))
                total_all = total_result.fetchone().total
                
                return {
                    "total_predictions": total_all,
                    "verified_predictions": row.total or 0,
                    "mean_percentage_error": round(float(row.mean_abs_error or 0), 2),
                    "median_error": round(float(row.median_error or 0), 2),
                    "bias": round(float(row.bias or 0), 2),
                    "accuracy_within_5_percent": round(float(row.acc_5pct or 0), 1),
                    "accuracy_within_10_percent": round(float(row.acc_10pct or 0), 1),
                    "accuracy_within_20_percent": round(float(row.acc_20pct or 0), 1),
                    "model_health": "good" if (row.acc_10pct or 0) > 75 else "needs_attention"
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting model performance: {e}")
            return {}
    
    async def get_locality_performance(self, city: str = "bangalore") -> List[Dict[str, Any]]:
        """Get prediction performance breakdown by locality"""
        try:
            with self.get_session() as session:
                result = session.execute(text("""
                    SELECT 
                        locality_name,
                        COUNT(*) as total,
                        AVG(ABS(error_percentage)) as mean_error,
                        COUNT(*) FILTER (WHERE ABS(error_percentage) <= 10) * 100.0 / NULLIF(COUNT(*), 0) as acc_10pct
                    FROM predictions
                    WHERE feedback_status = 'verified'
                        AND LOWER(city) = LOWER(:city)
                    GROUP BY locality_name
                    ORDER BY acc_10pct DESC
                """), {"city": city})
                
                localities = []
                for row in result:
                    localities.append({
                        "locality": row.locality_name,
                        "total_predictions": row.total,
                        "mean_error": round(float(row.mean_error or 0), 2),
                        "accuracy_10pct": round(float(row.acc_10pct or 0), 1)
                    })
                return localities
        except SQLAlchemyError as e:
            logger.error(f"Error getting locality performance: {e}")
            return []
    
    async def get_calibration_suggestions(self) -> List[Dict[str, Any]]:
        """Get open calibration suggestions"""
        try:
            with self.get_session() as session:
                result = session.execute(text("""
                    SELECT 
                        suggestion_id, model_version, prediction_type,
                        issue_type, severity, description, suggested_action,
                        affected_localities, sample_size, created_at
                    FROM calibration_suggestions
                    WHERE status = 'open'
                    ORDER BY 
                        CASE severity 
                            WHEN 'critical' THEN 1 
                            WHEN 'high' THEN 2 
                            WHEN 'medium' THEN 3 
                            ELSE 4 
                        END,
                        created_at DESC
                """))
                
                suggestions = []
                for row in result:
                    suggestions.append({
                        "suggestion_id": row.suggestion_id,
                        "model_version": row.model_version,
                        "prediction_type": row.prediction_type,
                        "issue_type": row.issue_type,
                        "severity": row.severity,
                        "description": row.description,
                        "suggested_action": row.suggested_action,
                        "affected_localities": row.affected_localities or [],
                        "sample_size": row.sample_size,
                        "created_at": row.created_at.isoformat() if row.created_at else None
                    })
                return suggestions
        except SQLAlchemyError as e:
            logger.error(f"Error getting calibration suggestions: {e}")
            return []
    
    # =====================================================
    # SCENARIO SIMULATION OPERATIONS
    # =====================================================
    
    async def log_scenario_simulation(
        self,
        locality: str,
        infrastructure_event: str,
        distance_km: float,
        timeline_months: int,
        results: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Log a scenario simulation for analytics"""
        try:
            with self.get_session() as session:
                sim_id = str(uuid.uuid4())
                
                # Get locality ID
                loc_result = session.execute(text("""
                    SELECT id FROM localities WHERE LOWER(name) = LOWER(:locality)
                    LIMIT 1
                """), {"locality": locality})
                loc_row = loc_result.fetchone()
                locality_id = loc_row.id if loc_row else None
                
                session.execute(text("""
                    INSERT INTO scenario_simulations (
                        id, user_id, locality_id,
                        distance_km, timeline_months,
                        projected_price_impact_pct,
                        projected_rental_impact_pct,
                        projected_demand_impact_pct,
                        confidence, timeline_breakdown
                    ) VALUES (
                        :id, :user_id, :locality_id,
                        :distance, :timeline,
                        :price_impact, :rental_impact, :demand_impact,
                        :confidence, :breakdown
                    )
                """), {
                    "id": sim_id,
                    "user_id": user_id,
                    "locality_id": locality_id,
                    "distance": distance_km,
                    "timeline": timeline_months,
                    "price_impact": results.get("price_appreciation_pct"),
                    "rental_impact": results.get("rental_yield_change_pct"),
                    "demand_impact": results.get("demand_increase_pct"),
                    "confidence": results.get("confidence", 0.75),
                    "breakdown": str(results.get("timeline_breakdown", []))
                })
                
                return sim_id
        except SQLAlchemyError as e:
            logger.error(f"Error logging simulation: {e}")
            return ""
    
    async def get_infrastructure_events(
        self,
        city: str = "bangalore",
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get infrastructure events for impact analysis"""
        try:
            with self.get_session() as session:
                conditions = []
                params = {}
                
                if status:
                    conditions.append("status = :status")
                    params["status"] = status
                
                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                
                result = session.execute(text(f"""
                    SELECT 
                        id, event_type, name, description,
                        ST_X(location::geometry) as lng, ST_Y(location::geometry) as lat,
                        impact_radius_km, status,
                        announcement_date, expected_completion,
                        base_price_impact_pct
                    FROM infrastructure_events
                    {where_clause}
                    ORDER BY expected_completion
                """), params)
                
                events = []
                for row in result:
                    events.append({
                        "id": str(row.id),
                        "type": row.event_type,
                        "name": row.name,
                        "description": row.description,
                        "location": {"lat": row.lat, "lng": row.lng} if row.lat else None,
                        "impact_radius_km": float(row.impact_radius_km) if row.impact_radius_km else None,
                        "status": row.status,
                        "expected_completion": row.expected_completion.isoformat() if row.expected_completion else None,
                        "price_impact_pct": float(row.base_price_impact_pct) if row.base_price_impact_pct else None
                    })
                return events
        except SQLAlchemyError as e:
            logger.error(f"Error getting infrastructure events: {e}")
            return []


# Singleton instance
city_intel_repo = CityIntelRepository()
