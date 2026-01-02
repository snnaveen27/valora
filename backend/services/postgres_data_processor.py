"""
PostgreSQL-based Data Processor for DMPE
Replaces CSV-based processor with database-backed operations
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text

try:
    from backend.database.multiconnection import mdb as db_manager_multi
except Exception:
    db_manager_multi = None
from backend.database.connection import db_manager
from backend.utils.logger import LoggerMixin

logger = logging.getLogger(__name__)


class PostgresDataProcessor(LoggerMixin):
    """
    Database-backed data processor for DMPE training and predictions
    """
    
    def __init__(self):
        self.log_info("PostgreSQL Data Processor initialized")
    
    def load_training_data(
        self,
        city: Optional[str] = None,
        property_type: Optional[str] = None,
        min_quality_score: float = 0.5,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load training data from PostgreSQL for DMPE models
        
        Args:
            city: Filter by city
            property_type: Filter by property type
            min_quality_score: Minimum data quality score (0-1)
            limit: Maximum number of records
        
        Returns:
            DataFrame ready for DMPE training
        """
        try:
            # 1) Fetch properties from core DB
            base_query = (
                "SELECT id, city, locality, property_type, bedrooms, area_sqft, price, listing_date, "
                "data_quality_score FROM properties WHERE data_quality_score >= :min_quality_score "
                "AND price IS NOT NULL AND area_sqft IS NOT NULL AND area_sqft > 0"
            )
            params = {"min_quality_score": min_quality_score}
            if city:
                base_query += " AND city = :city"
                params["city"] = city
            if property_type:
                base_query += " AND property_type = :property_type"
                params["property_type"] = property_type
            base_query += " ORDER BY listing_date DESC"
            if limit:
                base_query += " LIMIT :limit"
                params["limit"] = limit

            if db_manager_multi:
                with db_manager_multi.core() as c_sess:
                    core_rows = c_sess.execute(text(base_query), params).fetchall()
                    core_cols = ["id","city","locality","property_type","bedrooms","area_sqft","price","listing_date","data_quality_score"]
            else:
                with db_manager.get_session() as session:
                    result = session.execute(text(base_query), params)
                    core_rows = result.fetchall()
                    core_cols = result.keys()

            if not core_rows:
                return pd.DataFrame(columns=list(core_cols))

            df_core = pd.DataFrame(core_rows, columns=core_cols)

            # 2) Fetch latest market stats per (city, locality) from core DB
            if db_manager_multi:
                with db_manager_multi.core() as c_sess:
                    ms_rows = c_sess.execute(text(
                        "SELECT DISTINCT ON (city, locality) city, locality, avg_price, avg_price_per_sqft, "
                        "price_growth_3m, price_growth_6m, price_growth_12m, listings_count, avg_days_on_market, absorption_rate, period_end "
                        "FROM market_statistics ORDER BY city, locality, period_end DESC"
                    )).fetchall()
            else:
                with db_manager.get_session() as session:
                    ms_rows = session.execute(text(
                        "SELECT DISTINCT ON (city, locality) city, locality, avg_price, avg_price_per_sqft, "
                        "price_growth_3m, price_growth_6m, price_growth_12m, listings_count, avg_days_on_market, absorption_rate, period_end "
                        "FROM market_statistics ORDER BY city, locality, period_end DESC"
                    )).fetchall()
            df_ms = pd.DataFrame(ms_rows, columns=[
                "city","locality","avg_price_locality","avg_price_per_sqft_locality",
                "price_growth_3m","price_growth_6m","price_growth_12m","listings_count","days_on_market","absorption_rate","period_end"
            ]) if ms_rows else pd.DataFrame(columns=["city","locality"])

            # 3) Fetch spatial features for these properties from spatial DB (if available)
            df = df_core
            if db_manager_multi and not df_core.empty:
                ids = list(df_core["id"].astype(str).values)
                with db_manager_multi.spatial() as s_sess:
                    sf_rows = s_sess.execute(text(
                        "SELECT property_id, distance_to_metro, distance_to_hospital, distance_to_school, distance_to_mall, "
                        "distance_to_airport, distance_to_railway, poi_density_1km, poi_density_3km, infrastructure_score, connectivity_score, lifestyle_score "
                        "FROM property_spatial_features WHERE property_id = ANY(:ids)"
                    ), {"ids": ids}).fetchall()
                df_sf = pd.DataFrame(sf_rows, columns=[
                    "id","distance_to_metro","distance_to_hospital","distance_to_school","distance_to_mall","distance_to_airport","distance_to_railway","poi_density_1km","poi_density_3km","infrastructure_score","connectivity_score","lifestyle_score"
                ]) if sf_rows else pd.DataFrame(columns=["id"])
                if not df_sf.empty:
                    df = df.merge(df_sf, how="left", on="id")

            # 4) Join market stats
            if not df_ms.empty:
                df = df.merge(df_ms.drop(columns=["period_end"]), how="left", on=["city","locality"]) 

            self.log_info(f"Loaded {len(df)} records for training (multi-DB={bool(db_manager_multi)})")
            return df
        except Exception as e:
            self.log_error(f"Failed to load training data: {e}")
            return pd.DataFrame()
    
    def query_properties(
        self,
        city: Optional[str] = None,
        locality: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        bedrooms: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        include_spatial: bool = True
    ) -> List[Dict[str, Any]]:
        """Query properties with filters"""
        
        try:
            # Query core properties
            query = "SELECT * FROM properties WHERE 1=1"
            params = {}
            if city:
                query += " AND city = :city"; params["city"] = city
            if locality:
                query += " AND locality ILIKE :locality"; params["locality"] = f"%{locality}%"
            if property_type:
                query += " AND property_type = :ptype"; params["ptype"] = property_type
            if min_price:
                query += " AND price >= :pmin"; params["pmin"] = min_price
            if max_price:
                query += " AND price <= :pmax"; params["pmax"] = max_price
            if min_area:
                query += " AND area_sqft >= :amin"; params["amin"] = min_area
            if max_area:
                query += " AND area_sqft <= :amax"; params["amax"] = max_area
            if bedrooms:
                query += " AND bedrooms = :beds"; params["beds"] = bedrooms
            query += " ORDER BY listing_date DESC LIMIT :lim OFFSET :off"
            params.update({"lim": limit, "off": offset})

            if db_manager_multi:
                with db_manager_multi.core() as c_sess:
                    result = c_sess.execute(text(query), params)
                    columns = result.keys(); data = result.fetchall()
            else:
                with db_manager.get_session() as session:
                    result = session.execute(text(query), params)
                    columns = result.keys(); data = result.fetchall()

            properties = [
                {
                    k: (v.isoformat() if isinstance(v, datetime) else (str(v) if hasattr(v, 'hex') else v))
                    for k, v in dict(zip(columns, row)).items()
                }
                for row in data
            ]

            # Optionally attach spatial features from spatial DB
            if include_spatial and db_manager_multi and properties:
                ids = [p["id"] for p in properties]
                with db_manager_multi.spatial() as s_sess:
                    sf = s_sess.execute(text(
                        "SELECT property_id, distance_to_metro, distance_to_hospital, distance_to_school, distance_to_mall, "
                        "distance_to_airport, distance_to_railway, poi_density_1km, poi_density_3km, infrastructure_score, connectivity_score, lifestyle_score "
                        "FROM property_spatial_features WHERE property_id = ANY(:ids)"
                    ), {"ids": ids}).fetchall()
                sf_map = {
                    str(r[0]): {
                        "distance_to_metro": r[1], "distance_to_hospital": r[2], "distance_to_school": r[3], "distance_to_mall": r[4],
                        "distance_to_airport": r[5], "distance_to_railway": r[6], "poi_density_1km": r[7], "poi_density_3km": r[8],
                        "infrastructure_score": r[9], "connectivity_score": r[10], "lifestyle_score": r[11]
                    }
                    for r in sf
                }
                for p in properties:
                    if p["id"] in sf_map:
                        p.update(sf_map[p["id"]])

            return properties
        except Exception as e:
            self.log_error(f"Failed to query properties: {e}")
            return []
    
    def get_market_statistics(
        self,
        city: str,
        locality: Optional[str] = None,
        property_type: Optional[str] = None,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """Get market statistics for a location"""
        
        try:
            query = """
                SELECT 
                    AVG(price) as avg_price,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price,
                    AVG(price_per_sqft) as avg_price_per_sqft,
                    COUNT(*) as listings_count,
                    AVG(EXTRACT(EPOCH FROM (NOW() - listing_date))/86400) as avg_days_on_market,
                    STDDEV(price) as price_std
                FROM properties
                WHERE city = :city
                AND listing_date >= :date_from
            """
            
            params = {
                "city": city,
                "date_from": datetime.now() - timedelta(days=days_back)
            }
            
            if locality:
                query += " AND locality = :locality"
                params["locality"] = locality
            
            if property_type:
                query += " AND property_type = :property_type"
                params["property_type"] = property_type
            
            with db_manager.get_session() as session:
                result = session.execute(text(query), params).fetchone()
            
            if result:
                return {
                    "avg_price": float(result[0]) if result[0] else 0,
                    "median_price": float(result[1]) if result[1] else 0,
                    "avg_price_per_sqft": float(result[2]) if result[2] else 0,
                    "listings_count": int(result[3]) if result[3] else 0,
                    "avg_days_on_market": float(result[4]) if result[4] else 0,
                    "price_std": float(result[5]) if result[5] else 0,
                }
            
            return {}
            
        except Exception as e:
            self.log_error(f"Failed to get market statistics: {e}")
            return {}
    
    def get_investment_hotspots(
        self,
        city: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get investment hotspots using the view"""
        
        try:
            query = """
                SELECT * FROM investment_hotspots
            """
            
            params = {}
            
            if city:
                query += " WHERE city = :city"
                params["city"] = city
            
            query += " LIMIT :limit"
            params["limit"] = limit
            
            with db_manager.get_session() as session:
                result = session.execute(text(query), params)
                columns = result.keys()
                data = result.fetchall()
            
            hotspots = []
            for row in data:
                hotspot = dict(zip(columns, row))
                # Convert to JSON-serializable types
                for key, value in hotspot.items():
                    if isinstance(value, (np.integer, np.floating)):
                        hotspot[key] = float(value)
                hotspots.append(hotspot)
            
            return hotspots
            
        except Exception as e:
            self.log_error(f"Failed to get hotspots: {e}")
            return []
    
    def get_comparable_properties(
        self,
        property_id: str,
        radius_km: float = 2.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find comparable properties within radius"""
        
        try:
            if db_manager_multi:
                # Fetch target details from core
                with db_manager_multi.core() as c_sess:
                    tgt = c_sess.execute(text(
                        "SELECT id, city, property_type, bedrooms, area_sqft, price FROM properties WHERE id = :pid"
                    ), {"pid": property_id}).fetchone()
                if not tgt:
                    return []
                tgt_city, tgt_ptype, tgt_beds, tgt_area, tgt_price = tgt[1], tgt[2], tgt[3], tgt[4], tgt[5]

                # Get nearby property_ids from spatial DB using property_locations table
                with db_manager_multi.spatial() as s_sess:
                    # Get target location
                    loc = s_sess.execute(text(
                        "SELECT location FROM property_locations WHERE property_id = :pid"
                    ), {"pid": property_id}).fetchone()
                    if not loc or not loc[0]:
                        return []
                    # Find neighbors within radius
                    nbrs = s_sess.execute(text(
                        """
                        SELECT property_id, ST_Distance(location, :p) / 1000 AS distance_km
                        FROM property_locations
                        WHERE property_id <> :pid AND ST_DWithin(location, :p, :radius_m)
                        ORDER BY distance_km ASC
                        LIMIT :lim
                        """
                    ), {"p": loc[0], "pid": property_id, "radius_m": radius_km * 1000, "lim": limit * 5}).fetchall()

                if not nbrs:
                    return []
                nbr_ids = [str(r[0]) for r in nbrs]
                dist_map = {str(r[0]): float(r[1]) for r in nbrs}

                # Fetch details from core and filter by type/bedrooms
                with db_manager_multi.core() as c_sess:
                    rows = c_sess.execute(text(
                        "SELECT id, city, locality, property_type, bedrooms, area_sqft, price FROM properties WHERE id = ANY(:ids)"
                    ), {"ids": nbr_ids}).fetchall()
                out = []
                for r in rows:
                    pid = str(r[0])
                    if r[1] != tgt_city or r[3] != tgt_ptype or r[4] != tgt_beds:
                        continue
                    price_diff = abs((r[6] or 0) - (tgt_price or 0)) / max(tgt_price or 1, 1)
                    area_diff = abs((r[5] or 0) - (tgt_area or 0)) / max(tgt_area or 1, 1)
                    out.append({
                        "id": pid,
                        "city": r[1],
                        "locality": r[2],
                        "property_type": r[3],
                        "bedrooms": r[4],
                        "area_sqft": float(r[5]) if r[5] is not None else None,
                        "price": float(r[6]) if r[6] is not None else None,
                        "distance_km": dist_map.get(pid),
                        "price_diff_pct": float(price_diff),
                        "area_diff_pct": float(area_diff),
                    })
                out = sorted(out, key=lambda x: (x["distance_km"], x["price_diff_pct"], x["area_diff_pct"]))[:limit]
                return out

            # Single-DB fallback: original spatial join
            query = """
                WITH target AS (
                    SELECT location, city, property_type, bedrooms, area_sqft, price
                    FROM properties
                    WHERE id = :property_id
                )
                SELECT 
                    p.*,
                    ST_Distance(p.location, target.location) / 1000 as distance_km,
                    ABS(p.price - target.price) / target.price as price_diff_pct,
                    ABS(p.area_sqft - target.area_sqft) / target.area_sqft as area_diff_pct
                FROM properties p, target
                WHERE p.id != :property_id
                AND p.city = target.city
                AND p.property_type = target.property_type
                AND p.bedrooms = target.bedrooms
                AND ST_DWithin(p.location, target.location, :radius_m)
                ORDER BY 
                    distance_km ASC,
                    price_diff_pct ASC,
                    area_diff_pct ASC
                LIMIT :limit
            """
            params = {"property_id": property_id, "radius_m": radius_km * 1000, "limit": limit}
            with db_manager.get_session() as session:
                result = session.execute(text(query), params)
                columns = result.keys(); data = result.fetchall()
            out = []
            for row in data:
                comp = dict(zip(columns, row))
                for k, v in comp.items():
                    if isinstance(v, datetime): comp[k] = v.isoformat()
                    elif hasattr(v, 'hex'): comp[k] = str(v)
                    elif isinstance(v, (np.integer, np.floating)): comp[k] = float(v)
                out.append(comp)
            return out
        except Exception as e:
            self.log_error(f"Failed to get comparable properties: {e}")
            return []
    
    def get_pois_near_property(
        self,
        property_id: str,
        radius_km: float = 3.0,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get POIs near a property"""
        
        try:
            if db_manager_multi:
                q = (
                    "SELECT poi.id, poi.name, poi.category, poi.metadata, "
                    "ST_Distance(poi.location, pl.location) / 1000 as distance_km "
                    "FROM pois poi, property_locations pl "
                    "WHERE pl.property_id = :pid AND ST_DWithin(poi.location, pl.location, :r)"
                )
                params = {"pid": property_id, "r": radius_km * 1000}
                if category:
                    q += " AND poi.category = :cat"; params["cat"] = category
                q += " ORDER BY distance_km LIMIT 50"
                with db_manager_multi.spatial() as s_sess:
                    res = s_sess.execute(text(q), params)
                    cols = res.keys(); data = res.fetchall()
                return [
                    {k: (v.isoformat() if isinstance(v, datetime) else (str(v) if hasattr(v, 'hex') else v)) for k, v in dict(zip(cols, row)).items()}
                    for row in data
                ]

            # Single-DB fallback using properties.location
            query = """
                SELECT 
                    poi.*,
                    ST_Distance(poi.location, p.location) / 1000 as distance_km
                FROM pois poi, properties p
                WHERE p.id = :property_id
                AND ST_DWithin(poi.location, p.location, :radius_m)
            """
            params = {"property_id": property_id, "radius_m": radius_km * 1000}
            if category:
                query += " AND poi.category = :category"; params["category"] = category
            query += " ORDER BY distance_km LIMIT 50"
            with db_manager.get_session() as session:
                result = session.execute(text(query), params)
                columns = result.keys(); data = result.fetchall()
            return [
                {k: (v.isoformat() if isinstance(v, datetime) else (str(v) if hasattr(v, 'hex') else v)) for k, v in dict(zip(columns, row)).items()}
                for row in data
            ]
        except Exception as e:
            self.log_error(f"Failed to get POIs: {e}")
            return []
    
    def cache_market_statistics(self, city: str, force_refresh: bool = False):
        """Cache market statistics for a city"""
        
        try:
            # Check if recent statistics exist
            if not force_refresh:
                with db_manager.get_session() as session:
                    result = session.execute(
                        text("""
                            SELECT COUNT(*) FROM market_statistics
                            WHERE city = :city
                            AND created_at >= NOW() - INTERVAL '1 day'
                        """),
                        {"city": city}
                    ).scalar()
                    
                    if result > 0:
                        self.log_info(f"Recent market statistics exist for {city}")
                        return
            
            # Calculate and insert statistics
            with db_manager.get_session() as session:
                # Get distinct localities
                localities = session.execute(
                    text("SELECT DISTINCT locality FROM properties WHERE city = :city"),
                    {"city": city}
                ).fetchall()
                
                for (locality,) in localities:
                    if not locality:
                        continue
                    
                    # Calculate statistics
                    stats = self.get_market_statistics(city, locality)
                    
                    if stats.get('listings_count', 0) > 0:
                        session.execute(
                            text("""
                                INSERT INTO market_statistics
                                (city, locality, period_start, period_end, 
                                 avg_price, median_price, avg_price_per_sqft,
                                 listings_count, avg_days_on_market, sample_size)
                                VALUES
                                (:city, :locality, :period_start, :period_end,
                                 :avg_price, :median_price, :avg_price_per_sqft,
                                 :listings_count, :avg_days_on_market, :sample_size)
                            """),
                            {
                                "city": city,
                                "locality": locality,
                                "period_start": datetime.now() - timedelta(days=90),
                                "period_end": datetime.now(),
                                "avg_price": stats['avg_price'],
                                "median_price": stats['median_price'],
                                "avg_price_per_sqft": stats['avg_price_per_sqft'],
                                "listings_count": stats['listings_count'],
                                "avg_days_on_market": stats['avg_days_on_market'],
                                "sample_size": stats['listings_count']
                            }
                        )
                
                session.commit()
            
            self.log_info(f"Market statistics cached for {city}")
            
        except Exception as e:
            self.log_error(f"Failed to cache market statistics: {e}")
