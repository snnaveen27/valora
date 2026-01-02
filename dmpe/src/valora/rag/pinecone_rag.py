"""
Pinecone RAG utilities for Valora DMPE.
- Builds an embeddings index from processed property datasets
- Supports semantic query with optional filters (city, property_type)
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd
import hashlib

from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from .vector_cache import VectorCache

logger = logging.getLogger(__name__)

_EMBEDDER: Optional[SentenceTransformer] = None
_PC: Optional[Pinecone] = None
_INDEX = None

DEFAULT_MODEL = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_DIM = 384 if "MiniLM-L6-v2" in DEFAULT_MODEL else 768


def _get_embedder() -> SentenceTransformer:
    global _EMBEDDER
    if _EMBEDDER is None:
        logger.info(f"Loading embeddings model: {DEFAULT_MODEL}")
        _EMBEDDER = SentenceTransformer(DEFAULT_MODEL)
    return _EMBEDDER


def _init_pinecone() -> Pinecone:
    global _PC
    if _PC is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY not set")
        _PC = Pinecone(api_key=api_key)
    return _PC


def ensure_index(index_name: str, dimension: int = DEFAULT_DIM, wait_timeout: int = 120) -> None:
    pc = _init_pinecone()
    try:
        if not pc.has_index(index_name):
            logger.info(f"Creating Pinecone index: {index_name}")
            cloud = os.getenv("PINECONE_CLOUD", "aws")
            region = os.getenv("PINECONE_REGION", "us-east-1")
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=cloud, region=region)
            )

        # Wait for the index to be ready (serverless usually fast, but guard anyway)
        start_time = time.time()
        while True:
            try:
                desc = pc.describe_index(index_name)
                status = getattr(desc, "status", None)
                ready = False
                if status is None:
                    ready = True
                else:
                    ready = getattr(status, "ready", None)
                    if ready is None:
                        state = getattr(status, "state", None)
                        if state is None and isinstance(status, dict):
                            ready = status.get("ready") or status.get("state") == "ready"
                        else:
                            ready = state == "ready"

                if ready:
                    break
            except Exception as wait_err:
                logger.debug(f"Waiting for Pinecone index readiness: {wait_err}")

            if time.time() - start_time > wait_timeout:
                raise TimeoutError(f"Timed out waiting for Pinecone index '{index_name}' to be ready")

            time.sleep(2)
    except Exception as e:
        logger.error(f"Failed to ensure Pinecone index: {e}")
        raise


def connect_index(index_name: str):
    pc = _init_pinecone()
    return pc.Index(index_name)


def _row_to_text(row: pd.Series) -> str:
    parts = []
    for col in ("name", "description", "seo_description", "address", "locality"):
        val = row.get(col)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    # Amenities as text
    am = row.get("amenities")
    if isinstance(am, list) and am:
        parts.append("Amenities: " + ", ".join([str(x) for x in am[:20]]))
    return " \n".join(parts)[:5000]


def build_index_from_datasets(index_name: str, datasets: Dict[str, pd.DataFrame], namespace: Optional[str] = None, batch_size: int = 128) -> int:
    """Build (upsert) vectors into Pinecone from processed datasets.
    Returns number of upserted vectors.
    """
    ensure_index(index_name, DEFAULT_DIM)
    index = connect_index(index_name)
    embedder = _get_embedder()
    cache = VectorCache()
    
    # Prepare all items and populate cache
    all_items = []
    for key, df in datasets.items():
        if df is None or len(df) == 0:
            continue
        # Ensure text fields exist
        for col in ("name", "description", "seo_description", "address", "locality"):
            if col not in df.columns:
                df[col] = None

        # Prepare rows
        for idx, row in df.iterrows():
            # Build a deterministic content hash for deduplication across runs
            base_id = str(row.get("id") or "").strip()
            row_url = str(row.get("url") or "").strip()
            # Legacy pid for reference
            if base_id:
                legacy_pid = f"{key}:{base_id}"
            elif row_url:
                legacy_pid = f"{key}:{row_url[:200]}"
            else:
                legacy_pid = f"{key}:{key}_{idx}"

            text = _row_to_text(row)
            if not text:
                continue
            # Compute content hash from key attributes and text
            hash_input = f"{key}|{base_id}|{row_url}|{str(row.get('city') or '')}|{str(row.get('property_type') or '')}|{text[:500]}"
            content_hash = hashlib.sha256(hash_input.encode('utf-8', errors='ignore')).hexdigest()
            # Use content hash as vector ID to ensure idempotent upserts
            pid = content_hash

            meta = {
                "city": str(row.get("city") or "Unknown"),
                "property_type": str(row.get("property_type") or "unknown"),
                "listing_type": str(row.get("listing_type") or "sale"),
                "price": float(row.get("price") or 0.0),
                "price_per_sqft": float(row.get("price_per_sq_ft") or 0.0),
                "bedrooms": float(row.get("bedrooms") or 0.0),
                "area_sqft": float(row.get("area_sqft") or 0.0),
                "investment_score": float(row.get("investment_score") or 0.0),
                "latitude": float(row.get("latitude") or 0.0),
                "longitude": float(row.get("longitude") or 0.0),
                "id": legacy_pid,
                "url": str(row.get("url") or "")[:512],
                "locality": str(row.get("locality") or "")[:256],
                "key": key,
                "content_hash": content_hash,
                "legacy_id": legacy_pid,
            }
            
            # Get or create embedding (this populates cache)
            embedding = cache.get_or_create_embedding(pid, text, meta, embedder)
            all_items.append((pid, text, meta))
    
    logger.info(f"Prepared {len(all_items)} items for indexing")
    
    # Get cache stats
    stats = cache.get_stats()
    logger.info(f"Cache stats: {stats}")
    
    # Get pending vectors (need upload to Pinecone)
    pending_vectors = cache.get_pending_vectors()
    logger.info(f"Vectors pending upload: {len(pending_vectors)}")
    
    if len(pending_vectors) == 0:
        logger.info("All vectors already synced to Pinecone")
        cache._save_cache()
        return len(all_items)
    
    # Process in batches
    total_upserted = 0
    for i in range(0, len(pending_vectors), batch_size):
        batch = pending_vectors[i:i + batch_size]
        
        # Prepare upsert batch
        to_upsert = []
        for vector_id, embedding, metadata in batch:
            # Sanitize metadata
            clean_meta = {}
            for k, val in metadata.items():
                if isinstance(val, float):
                    if np.isnan(val) or np.isinf(val):
                        clean_meta[k] = 0.0
                    else:
                        clean_meta[k] = float(val)
                elif pd.isna(val):
                    clean_meta[k] = None if isinstance(val, str) else 0.0
                else:
                    clean_meta[k] = val
            
            # Mark uploaded using content hash (vector_id is the content hash)
            try:
                cache.mark_uploaded(vector_id, vector_id)
            except Exception:
                pass
            
            to_upsert.append({
                "id": vector_id,
                "values": embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding),
                "metadata": clean_meta
            })
        
        # Upsert to Pinecone
        try:
            if namespace:
                index.upsert(vectors=to_upsert, namespace=namespace)
            else:
                index.upsert(vectors=to_upsert)
            total_upserted += len(to_upsert)
            logger.info(f"Upserted batch {i//batch_size + 1}: {len(to_upsert)} vectors (total: {total_upserted})")
        except Exception as e:
            logger.error(f"Failed to upsert batch: {e}")
            # Continue with next batch
            continue
        
        # Save cache periodically
        if i % (batch_size * 5) == 0:
            cache._save_cache()
    
    # Final cache save
    cache._save_cache()
    
    logger.info(f"Upserted {total_upserted} vectors to Pinecone index '{index_name}'")
    return total_upserted


def _flush(index, embedder, items: List, namespace: Optional[str]):
    ids = [it[0] for it in items]
    texts = [it[1] for it in items]
    meta = [it[2] for it in items]
    # Check which legacy IDs already exist to avoid duplicates
    existing_ids = set()
    try:
        legacy_ids = [m.get("legacy_id") for m in meta if m.get("legacy_id")]
        if legacy_ids:
            if namespace:
                fetched = index.fetch(ids=legacy_ids, namespace=namespace)
            else:
                fetched = index.fetch(ids=legacy_ids)
            records = None
            try:
                records = getattr(fetched, 'vectors', None) or getattr(fetched, 'records', None)
            except Exception:
                records = None
            if records is None and isinstance(fetched, dict):
                records = fetched.get('vectors') or fetched.get('records')
            if isinstance(records, dict):
                existing_ids = set(records.keys())
    except Exception:
        existing_ids = set()
    vectors = embedder.encode(texts, normalize_embeddings=True)
    to_upsert = []
    for i, v in enumerate(vectors):
        legacy_id = meta[i].get("legacy_id")
        if legacy_id and legacy_id in existing_ids:
            continue
        # Sanitize metadata: replace NaN with None/0 and ensure JSON-serializable
        clean_meta = {}
        for k, val in meta[i].items():
            if k == 'legacy_id':
                continue
            if isinstance(val, float):
                if np.isnan(val) or np.isinf(val):
                    clean_meta[k] = 0.0
                else:
                    clean_meta[k] = float(val)
            elif pd.isna(val):
                clean_meta[k] = None if isinstance(val, str) else 0.0
            else:
                clean_meta[k] = val
        
        to_upsert.append({
            "id": ids[i],
            "values": v.tolist() if isinstance(v, np.ndarray) else list(v),
            "metadata": clean_meta
        })
    # Only pass namespace if provided
    if namespace:
        index.upsert(vectors=to_upsert, namespace=namespace)
    else:
        index.upsert(vectors=to_upsert)


def rag_query(index_name: str, query: str, top_k: int = 5, city: Optional[str] = None, property_type: Optional[str] = None, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query Pinecone index for most relevant properties."""
    index = connect_index(index_name)
    embedder = _get_embedder()
    qv = embedder.encode([query], normalize_embeddings=True)[0]

    flt: Dict[str, Any] = {}
    if city:
        flt["city"] = {"$eq": city}
    if property_type:
        flt["property_type"] = {"$eq": property_type}

    if namespace:
        res = index.query(vector=qv.tolist(), top_k=top_k, include_metadata=True, filter=flt or None, namespace=namespace)
    else:
        res = index.query(vector=qv.tolist(), top_k=top_k, include_metadata=True, filter=flt or None)

    results = []
    try:
        matches = getattr(res, 'matches', []) or res.get('matches', [])
    except Exception:
        matches = []
    for m in matches:
        score = float(getattr(m, 'score', 0.0) or m.get('score', 0.0))
        md = getattr(m, 'metadata', None) or m.get('metadata', {})
        pid = getattr(m, 'id', None) or m.get('id')
        results.append({
            "id": pid,
            "score": score,
            "metadata": md
        })
    return results
