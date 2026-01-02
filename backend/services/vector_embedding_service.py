"""
Vector Embedding Service for PostgreSQL with pgvector
Handles property embeddings for similarity search and recommendations
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
import json

try:
    from backend.database.multiconnection import mdb as db_manager_multi
except Exception:
    db_manager_multi = None
from backend.database.connection import db_manager
from backend.services.external_apis import ExternalAPIService
from backend.utils.logger import LoggerMixin

logger = logging.getLogger(__name__)


class VectorEmbeddingService(LoggerMixin):
    """
    Service for managing vector embeddings in PostgreSQL
    Uses pgvector for similarity search without external vector DB
    """
    
    def __init__(self):
        self.external_api = ExternalAPIService()
        self.embedding_dimension = 1536  # OpenAI ada-002 dimension
        self.log_info("Vector Embedding Service initialized")
    
    def generate_property_embeddings(self, property_data: Dict[str, Any]) -> Dict[str, List[float]]:
        """
        Generate embeddings for a property using various text features
        
        Returns:
            Dict with embedding vectors for different aspects
        """
        embeddings = {}
        
        try:
            # 1. Description embedding (main property description)
            description_text = self._create_description_text(property_data)
            if description_text:
                embeddings['description'] = self._get_embedding(description_text)
            
            # 2. Amenities embedding (from amenities list)
            amenities_text = self._create_amenities_text(property_data)
            if amenities_text:
                embeddings['amenities'] = self._get_embedding(amenities_text)
            
            # 3. Location embedding (semantic location description)
            location_text = self._create_location_text(property_data)
            if location_text:
                embeddings['location'] = self._get_embedding(location_text)
            
            # 4. Combined embedding (all features together)
            combined_text = self._create_combined_text(property_data)
            if combined_text:
                embeddings['combined'] = self._get_embedding(combined_text)
            
            self.log_info(f"Generated {len(embeddings)} embeddings for property")
            
        except Exception as e:
            self.log_error(f"Failed to generate embeddings: {e}")
        
        return embeddings
    
    def _create_description_text(self, property_data: Dict[str, Any]) -> str:
        """Create descriptive text for embedding"""
        parts = []
        
        # Basic property description
        if property_data.get('property_type'):
            parts.append(f"{property_data['property_type']}")
        
        if property_data.get('property_subtype'):
            parts.append(f"{property_data['property_subtype']}")
        
        if property_data.get('bedrooms'):
            parts.append(f"{property_data['bedrooms']} bedroom")
        
        if property_data.get('bathrooms'):
            parts.append(f"{property_data['bathrooms']} bathroom")
        
        if property_data.get('area_sqft'):
            parts.append(f"{property_data['area_sqft']} sqft")
        
        # Location context
        if property_data.get('locality'):
            parts.append(f"in {property_data['locality']}")
        
        if property_data.get('city'):
            parts.append(f"{property_data['city']}")
        
        # Furnishing and features
        if property_data.get('furnishing'):
            parts.append(f"{property_data['furnishing']}")
        
        if property_data.get('parking_spaces'):
            parts.append(f"{property_data['parking_spaces']} parking")
        
        # Price range (normalized for embedding)
        if property_data.get('price'):
            price = property_data['price']
            if price < 3000000:
                parts.append("budget friendly")
            elif price < 8000000:
                parts.append("mid range")
            elif price < 20000000:
                parts.append("premium")
            else:
                parts.append("luxury")
        
        return ". ".join(parts)
    
    def _create_amenities_text(self, property_data: Dict[str, Any]) -> str:
        """Create text from amenities list"""
        amenities = property_data.get('amenities', [])
        
        if isinstance(amenities, str):
            try:
                amenities = json.loads(amenities)
            except:
                amenities = []
        
        if not amenities:
            return ""
        
        return "Amenities: " + ", ".join(amenities)
    
    def _create_location_text(self, property_data: Dict[str, Any]) -> str:
        """Create semantic location description"""
        parts = []
        
        if property_data.get('city'):
            parts.append(f"City: {property_data['city']}")
        
        if property_data.get('locality'):
            parts.append(f"Locality: {property_data['locality']}")
        
        if property_data.get('sub_locality'):
            parts.append(f"Area: {property_data['sub_locality']}")
        
        # Add location type inference
        locality = property_data.get('locality', '').lower()
        city = property_data.get('city', '').lower()
        
        # Bangalore localities
        if 'bangalore' in city or 'bengaluru' in city:
            if any(x in locality for x in ['koramangala', 'indiranagar', 'hsr']):
                parts.append("upscale residential area")
            elif any(x in locality for x in ['whitefield', 'marathahalli', 'bellandur']):
                parts.append("tech hub area")
            elif any(x in locality for x in ['jayanagar', 'basavanagudi', 'malleswaram']):
                parts.append("traditional residential")
        
        # Mumbai localities
        elif 'mumbai' in city or 'bombay' in city:
            if any(x in locality for x in ['bandra', 'juhu', 'worli']):
                parts.append("prime location")
            elif any(x in locality for x in ['andheri', 'powai', 'goregaon']):
                parts.append("commercial residential mix")
        
        return ". ".join(parts)
    
    def _create_combined_text(self, property_data: Dict[str, Any]) -> str:
        """Create comprehensive text for combined embedding"""
        texts = []
        
        # Add all individual texts
        desc = self._create_description_text(property_data)
        if desc:
            texts.append(desc)
        
        amenities = self._create_amenities_text(property_data)
        if amenities:
            texts.append(amenities)
        
        location = self._create_location_text(property_data)
        if location:
            texts.append(location)
        
        # Add additional metadata
        metadata = property_data.get('metadata', {})
        if isinstance(metadata, dict):
            if metadata.get('description'):
                texts.append(metadata['description'])
            if metadata.get('features'):
                texts.append(f"Features: {metadata['features']}")
        
        return " | ".join(texts)
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using external API or fallback"""
        try:
            # Try OpenRouter/OpenAI first
            embedding = self.external_api.get_embedding(text)
            if embedding:
                return embedding
        except Exception as e:
            self.log_warning(f"External API embedding failed: {e}")
        
        # Fallback: Create mock embedding based on text hash
        return self._create_fallback_embedding(text)
    
    def _create_fallback_embedding(self, text: str) -> List[float]:
        """Create deterministic fallback embedding based on text hash"""
        # Use text hash to create pseudo-random but consistent embedding
        hash_val = hash(text)
        np.random.seed(hash_val)
        
        # Create embedding with some structure based on text characteristics
        base_embedding = np.random.normal(0, 0.1, self.embedding_dimension)
        
        # Add some bias based on text length and content
        text_features = [
            len(text) / 1000.0,  # Normalized length
            text.count(' ') / 100.0,  # Word count proxy
            text.count(',') / 10.0,  # List indicator
            1.0 if 'luxury' in text.lower() else 0.0,
            1.0 if 'budget' in text.lower() else 0.0,
            1.0 if 'bedroom' in text.lower() else 0.0,
            1.0 if 'apartment' in text.lower() else 0.0,
            1.0 if 'house' in text.lower() else 0.0,
        ]
        
        # Spread text features across embedding
        for i, feature in enumerate(text_features[:min(len(text_features), 50)]):
            pos = i * (self.embedding_dimension // len(text_features))
            base_embedding[pos] += feature
        
        return base_embedding.tolist()
    
    def update_property_embeddings(self, property_id: str, embeddings: Dict[str, List[float]]) -> bool:
        """Update embeddings for a property.
        - If multi-DB available: upsert into vector DB table property_embeddings
        - Else: fallback to legacy single-DB function update_property_embeddings()
        """
        try:
            # Preferred: vector DB
            if db_manager_multi:
                # Build pgvector literal strings like '[0.1,0.2,...]'
                def vec_str(key):
                    v = embeddings.get(key)
                    if not v:
                        return None
                    return '[' + ','.join(str(float(x)) for x in v) + ']'

                params = {
                    "pid": property_id,
                    "desc": vec_str('description'),
                    "amen": vec_str('amenities'),
                    "loc": vec_str('location'),
                    "comb": vec_str('combined'),
                }
                with db_manager_multi.vector() as v_sess:
                    v_sess.execute(
                        text(
                            """
                            INSERT INTO property_embeddings (
                                property_id, description_embedding, amenities_embedding, 
                                location_embedding, combined_embedding, created_at, updated_at
                            ) VALUES (
                                :pid,
                                CASE WHEN :desc IS NULL THEN NULL ELSE (:desc)::vector(1536) END,
                                CASE WHEN :amen IS NULL THEN NULL ELSE (:amen)::vector(1536) END,
                                CASE WHEN :loc IS NULL THEN NULL ELSE (:loc)::vector(1536) END,
                                CASE WHEN :comb IS NULL THEN NULL ELSE (:comb)::vector(1536) END,
                                NOW(), NOW()
                            )
                            ON CONFLICT (property_id) DO UPDATE SET
                                description_embedding = EXCLUDED.description_embedding,
                                amenities_embedding = EXCLUDED.amenities_embedding,
                                location_embedding = EXCLUDED.location_embedding,
                                combined_embedding = EXCLUDED.combined_embedding,
                                updated_at = NOW()
                            """
                        ),
                        params,
                    )
                self.log_info(f"Upserted embeddings in vector DB for {property_id}")
                return True

            # Fallback: legacy single-DB function
            with db_manager.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT update_property_embeddings(
                            :property_id,
                            :description_vec,
                            :amenities_vec,
                            :location_vec,
                            :combined_vec
                        )
                        """
                    ),
                    {
                        "property_id": property_id,
                        "description_vec": embeddings.get('description'),
                        "amenities_vec": embeddings.get('amenities'),
                        "location_vec": embeddings.get('location'),
                        "combined_vec": embeddings.get('combined'),
                    },
                )
                return bool(result.scalar())
        except Exception as e:
            self.log_error(f"Failed to update embeddings: {e}")
            return False
    
    def find_similar_properties(
        self,
        property_id: str,
        similarity_threshold: float = 0.7,
        limit: int = 10,
        city_filter: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Find similar properties using vector similarity"""
        try:
            # Multi-DB: retrieve from vector DB by comparing to target property's combined embedding
            if db_manager_multi:
                # Get target embedding
                with (db_manager_multi.vector()) as v_sess:
                    target = v_sess.execute(
                        text("SELECT combined_embedding FROM property_embeddings WHERE property_id = :pid"),
                        {"pid": property_id},
                    ).fetchone()
                    if not target or not target[0]:
                        return []
                    # Similarity search in vector DB (top N ids)
                    sim_rows = v_sess.execute(
                        text(
                            """
                            SELECT property_id,
                                   1 - (combined_embedding <=> :target) AS similarity
                            FROM property_embeddings
                            WHERE property_id <> :pid
                            ORDER BY similarity DESC
                            LIMIT :lim
                            """
                        ),
                        {"target": target[0], "pid": property_id, "lim": limit},
                    ).fetchall()

                if not sim_rows:
                    return []

                # Fetch details from core DB and filter by optional constraints
                ids = [str(r[0]) for r in sim_rows]
                with db_manager_multi.core() as c_sess:
                    rows = c_sess.execute(
                        text(
                            "SELECT id, city, locality, price, area_sqft, bedrooms FROM properties WHERE id = ANY(:ids)"
                        ),
                        {"ids": ids},
                    ).fetchall()
                details = {str(r[0]): {"city": r[1], "locality": r[2], "price": r[3], "area_sqft": r[4], "bedrooms": r[5]} for r in rows}

                out = []
                for pid, sim in [(str(r[0]), float(r[1])) for r in sim_rows]:
                    d = details.get(pid)
                    if not d:
                        continue
                    if city_filter and d.get("city") != city_filter:
                        continue
                    if price_min and d.get("price") and d["price"] < price_min:
                        continue
                    if price_max and d.get("price") and d["price"] > price_max:
                        continue
                    out.append({
                        "property_id": pid,
                        "city": d.get("city"),
                        "locality": d.get("locality"),
                        "price": d.get("price"),
                        "area_sqft": d.get("area_sqft"),
                        "bedrooms": d.get("bedrooms"),
                        "similarity_score": sim,
                    })
                self.log_info(f"Found {len(out)} similar properties (vector DB)")
                return out

            # Fallback: single-DB function
            with db_manager.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT * FROM find_similar_properties_combined(
                            :property_id,
                            :city_filter,
                            :price_min,
                            :price_max,
                            :similarity_threshold,
                            :limit_count
                        )
                        """
                    ),
                    {
                        "property_id": property_id,
                        "city_filter": city_filter,
                        "price_min": price_min,
                        "price_max": price_max,
                        "similarity_threshold": similarity_threshold,
                        "limit_count": limit,
                    },
                )
                columns = result.keys()
                return [
                    {
                        k: (str(v) if hasattr(v, 'hex') else v)
                        for k, v in dict(zip(columns, row)).items()
                    }
                    for row in result.fetchall()
                ]
                
        except Exception as e:
            self.log_error(f"Failed to find similar properties: {e}")
            return []
    
    def semantic_search(
        self,
        query_text: str,
        city: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using natural language query"""
        try:
            # Get embedding for query text
            query_embedding = self._get_embedding(query_text)
            if not query_embedding:
                return []
            
            if db_manager_multi:
                # Get top matches from vector DB against query embedding
                qvec = '[' + ','.join(str(float(x)) for x in query_embedding) + ']'
                with db_manager_multi.vector() as v_sess:
                    sim_rows = v_sess.execute(
                        text(
                            """
                            SELECT property_id, 1 - (combined_embedding <=> (:qvec)::vector(1536)) AS similarity
                            FROM property_embeddings
                            ORDER BY similarity DESC
                            LIMIT :lim
                            """
                        ),
                        {"qvec": qvec, "lim": limit},
                    ).fetchall()
                if not sim_rows:
                    return []
                ids = [str(r[0]) for r in sim_rows]
                with db_manager_multi.core() as c_sess:
                    rows = c_sess.execute(
                        text(
                            "SELECT id, city, locality, property_type, price, area_sqft, bedrooms FROM properties WHERE id = ANY(:ids)"
                        ),
                        {"ids": ids},
                    ).fetchall()
                details = {
                    str(r[0]): {
                        "city": r[1],
                        "locality": r[2],
                        "property_type": r[3],
                        "price": r[4],
                        "area_sqft": r[5],
                        "bedrooms": r[6],
                    }
                    for r in rows
                }
                out = []
                for pid, sim in [(str(r[0]), float(r[1])) for r in sim_rows]:
                    d = details.get(pid)
                    if not d:
                        continue
                    if city and d.get("city") != city:
                        continue
                    if property_type and d.get("property_type") != property_type:
                        continue
                    if min_price and d.get("price") and d["price"] < min_price:
                        continue
                    if max_price and d.get("price") and d["price"] > max_price:
                        continue
                    item = {"property_id": pid, **d, "similarity_score": sim}
                    out.append(item)
                self.log_info(f"Semantic search returned {len(out)} results (vector DB)")
                return out

            # Fallback: single-DB function
            with db_manager.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT * FROM semantic_property_search(
                            :query_embedding,
                            :city_filter,
                            :property_type_filter,
                            :min_price,
                            :max_price,
                            :limit_count
                        )
                        """
                    ),
                    {
                        "query_embedding": query_embedding,
                        "city_filter": city,
                        "property_type_filter": property_type,
                        "min_price": min_price,
                        "max_price": max_price,
                        "limit_count": limit,
                    },
                )
                columns = result.keys()
                return [
                    {
                        k: (str(v) if hasattr(v, 'hex') else v)
                        for k, v in dict(zip(columns, row)).items()
                    }
                    for row in result.fetchall()
                ]
                
        except Exception as e:
            self.log_error(f"Failed semantic search: {e}")
            return []
    
    def batch_update_embeddings(self, limit: int = 100) -> int:
        """Update embeddings for properties without them.
        - Multi-DB: read from core DB, skip those already present in vector DB
        - Single-DB: try properties table's combined_embedding if available
        """
        try:
            updated = 0
            if db_manager_multi:
                # Fetch recent properties from core DB
                with db_manager_multi.core() as c_sess:
                    rows = c_sess.execute(
                        text(
                            """
                            SELECT id, city, locality, property_type, bedrooms,
                                   area_sqft, price, furnishing, parking_spaces,
                                   amenities, metadata
                            FROM properties
                            ORDER BY updated_at DESC
                            LIMIT :lim
                            """
                        ),
                        {"lim": limit * 2},
                    ).fetchall()
                if not rows:
                    return 0
                # Filter out ones with embeddings in vector DB
                candidates = []
                with db_manager_multi.vector() as v_sess:
                    for r in rows:
                        pid = str(r[0])
                        exists = v_sess.execute(
                            text("SELECT 1 FROM property_embeddings WHERE property_id=:pid"),
                            {"pid": pid},
                        ).fetchone()
                        if not exists:
                            candidates.append(r)
                            if len(candidates) >= limit:
                                break
                # Generate and upsert
                for r in candidates:
                    prop_data = {
                        "id": str(r[0]),
                        "city": r[1],
                        "locality": r[2],
                        "property_type": r[3],
                        "bedrooms": r[4],
                        "area_sqft": r[5],
                        "price": r[6],
                        "furnishing": r[7],
                        "parking_spaces": r[8],
                        "amenities": r[9],
                        "metadata": r[10],
                    }
                    embeddings = self.generate_property_embeddings(prop_data)
                    if embeddings and self.update_property_embeddings(prop_data["id"], embeddings):
                        updated += 1
                self.log_info(f"Batch updated embeddings for {updated} properties (vector DB)")
                return updated

            # Single-DB fallback: expect columns on properties
            with db_manager.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT id, city, locality, property_type, bedrooms,
                               area_sqft, price, furnishing, parking_spaces,
                               amenities, metadata
                        FROM properties
                        WHERE combined_embedding IS NULL
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                )
                for row in result.fetchall():
                    prop_data = dict(
                        id=str(row[0]),
                        city=row[1],
                        locality=row[2],
                        property_type=row[3],
                        bedrooms=row[4],
                        area_sqft=row[5],
                        price=row[6],
                        furnishing=row[7],
                        parking_spaces=row[8],
                        amenities=row[9],
                        metadata=row[10],
                    )
                    embeddings = self.generate_property_embeddings(prop_data)
                    if embeddings and self.update_property_embeddings(prop_data["id"], embeddings):
                        updated += 1
            self.log_info(f"Batch updated embeddings for {updated} properties (single DB)")
            return updated
        except Exception as e:
            self.log_error(f"Failed batch update: {e}")
            return 0
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about embeddings in database"""
        try:
            with db_manager.get_session() as session:
                stats = {}
                
                # Total properties
                result = session.execute(text("SELECT COUNT(*) FROM properties")).scalar()
                stats['total_properties'] = result
                
                # Properties with embeddings
                for embedding_type in ['description', 'amenities', 'location', 'combined']:
                    result = session.execute(
                        text(f"SELECT COUNT(*) FROM properties WHERE {embedding_type}_embedding IS NOT NULL")
                    ).scalar()
                    stats[f'with_{embedding_type}_embedding'] = result
                
                # Coverage percentages
                for embedding_type in ['description', 'amenities', 'location', 'combined']:
                    key = f'with_{embedding_type}_embedding'
                    if stats['total_properties'] > 0:
                        stats[f'{embedding_type}_coverage_pct'] = round(
                            (stats[key] / stats['total_properties']) * 100, 2
                        )
                    else:
                        stats[f'{embedding_type}_coverage_pct'] = 0
                
                return stats
                
        except Exception as e:
            self.log_error(f"Failed to get embedding stats: {e}")
            return {}
