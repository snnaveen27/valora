"""
Import and track external Apify runs started manually on Apify website.
"""
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import threading
import time

from multi_source_scraper import (
    APIFY_TOKEN, APIFY_BASE_URL, ACTORS,
    job_states, job_states_lock, ScrapeJobState,
    make_job_id, update_job_status, fetch_dataset_items,
    normalize_property_item, save_history, update_manifest,
    PROPERTIES_DIR, RAW_DATA_DIR, BASE_DIR, _safe_slug,
    scrape_threads, stop_flags
)


def import_apify_run(run_id: str, platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Import an external Apify run by run_id.
    Creates a job state and starts tracking/downloading it.
    """
    if not APIFY_TOKEN:
        return {"success": False, "error": "APIFY_API_TOKEN not configured"}
    
    if platform not in ACTORS:
        return {"success": False, "error": f"Unknown platform: {platform}"}
    
    # Fetch run details from Apify
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    try:
        status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
        response = requests.get(status_url, headers=headers, timeout=30)
        response.raise_for_status()
        run_data = response.json()["data"]
        
        actor_id = run_data.get("actId")
        dataset_id = run_data.get("defaultDatasetId")
        actor_status = run_data.get("status")
        
        # Verify this run belongs to the expected platform
        expected_actor_id = ACTORS[platform]["id"]
        if actor_id != expected_actor_id:
            return {
                "success": False, 
                "error": f"Run belongs to different actor. Expected {expected_actor_id}, got {actor_id}"
            }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch run details: {str(e)}"}
    
    # Create job ID
    job_id = make_job_id(
        platform,
        config.get("property_category", "residential"),
        config.get("search_type", "buy"),
        config.get("property_type", "imported")
    )
    
    # Add timestamp to make it unique for imported runs
    job_id = f"{job_id}_import_{int(time.time())}"
    
    # Check if already tracking
    with job_states_lock:
        if job_id in job_states:
            return {"success": False, "error": "Already tracking this run", "job_id": job_id}
    
    # Start tracking thread
    thread = threading.Thread(
        target=track_imported_run,
        args=(job_id, run_id, dataset_id, platform, config, actor_status),
        daemon=True
    )
    thread.start()
    scrape_threads[job_id] = thread
    
    return {
        "success": True,
        "message": f"Imported run {run_id}. Status: {actor_status}",
        "job_id": job_id,
        "run_id": run_id,
        "status": actor_status
    }


def track_imported_run(
    job_id: str, 
    run_id: str, 
    dataset_id: str, 
    platform: str, 
    config: Dict[str, Any],
    initial_status: str
):
    """Track an imported Apify run until completion and download results."""
    try:
        # Initialize job state
        with job_states_lock:
            job_states[job_id] = ScrapeJobState(
                job_id=job_id,
                platform=platform,
                status="running" if initial_status == "RUNNING" else "starting",
                run_id=run_id,
                dataset_id=dataset_id,
                started_at=datetime.now(timezone.utc).isoformat(),
                location=config.get("location", "Unknown"),
                search_type=config.get("search_type", "buy"),
                property_category=config.get("property_category", "residential"),
                property_type=config.get("property_type", "imported"),
                message=f"Tracking imported run (Status: {initial_status})",
                errors=[]
            )
        
        update_job_status(job_id)
        
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        actor_status = initial_status
        start_time = time.time()
        
        # Poll until completion (if not already finished)
        if actor_status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            update_job_status(job_id, message=f"Waiting for run to complete (current: {actor_status})...")
            
            while not stop_flags.get(job_id, False):
                time.sleep(5)
                
                # Check run status
                status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
                status_response = requests.get(status_url, headers=headers, timeout=30)
                status_response.raise_for_status()
                
                run_status = status_response.json()["data"]
                actor_status = run_status["status"]
                
                # Get item count
                dataset_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}"
                dataset_response = requests.get(dataset_url, headers=headers, timeout=30)
                if dataset_response.ok:
                    dataset_info = dataset_response.json()["data"]
                    item_count = dataset_info.get("itemCount", 0)
                    
                    update_job_status(
                        job_id,
                        message=f"Tracking... {item_count} items found ({actor_status})",
                        items_found=item_count
                    )
                
                if actor_status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    break
        
        # Download results
        if actor_status == "SUCCEEDED":
            update_job_status(job_id, message="Downloading results from imported run...", progress_percent=95)
        else:
            update_job_status(job_id, message=f"Run ended: {actor_status}. Downloading available results...", progress_percent=95)
        
        all_items = []
        try:
            all_items = fetch_dataset_items(dataset_id, headers, job_id)
        except Exception as e:
            update_job_status(job_id, message=f"Failed to download: {e}")
            all_items = []
        
        # Save raw data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_file = RAW_DATA_DIR / f"{platform}_imported_{timestamp}.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            import json
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        # Normalize
        update_job_status(job_id, message="Normalizing imported data...", progress_percent=97)
        
        normalized = []
        skipped_no_coords = 0
        for item in all_items:
            norm = normalize_property_item(item, platform)
            if norm:
                normalized.append(norm)
            else:
                skipped_no_coords += 1
        
        update_job_status(job_id, items_processed=len(all_items), items_valid=len(normalized))
        
        # Save normalized data
        location_slug = _safe_slug(config.get("location", "imported"))
        search_type = _safe_slug(config.get("search_type", "buy"))
        category = _safe_slug(config.get("property_category", "residential"))
        property_type = _safe_slug(config.get("property_type", "imported"))
        
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        dataset_name = f"{location_slug}_{search_type}_{category}_{property_type}"
        
        dataset_dir = PROPERTIES_DIR / _safe_slug(platform) / scrape_date / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        run_file = dataset_dir / f"data_imported_{timestamp}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            import json
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        
        # Merge with existing
        source_dir = PROPERTIES_DIR / _safe_slug(platform)
        main_file = source_dir / f"{dataset_name}_latest.json"
        existing = []
        if main_file.exists():
            with open(main_file, "r", encoding="utf-8") as f:
                import json
                existing = json.load(f)
        
        existing_ids = {item.get("id") for item in existing}
        new_items = [item for item in normalized if item.get("id") not in existing_ids]
        merged = existing + new_items
        
        with open(main_file, "w", encoding="utf-8") as f:
            import json
            json.dump(merged, f, ensure_ascii=False, indent=2)
        
        # Save metadata
        import json
        meta = {
            "schema_version": 1,
            "job_id": job_id,
            "platform": platform,
            "imported": True,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "scrape_date": scrape_date,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "items_scraped": len(all_items),
            "items_valid": len(normalized),
            "items_new": len(new_items),
            "total_in_dataset": len(merged),
            "paths": {
                "data_file": str(run_file.relative_to(BASE_DIR)).replace("\\", "/"),
                "latest_file": str(main_file.relative_to(BASE_DIR)).replace("\\", "/"),
                "raw_file": str(raw_file.relative_to(BASE_DIR)).replace("\\", "/")
            }
        }
        
        meta_file = dataset_dir / f"metadata_imported_{timestamp}.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # Update history
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "platform": platform,
            "imported": True,
            "run_id": run_id,
            "items_scraped": len(all_items),
            "items_valid": len(normalized),
            "items_new": len(new_items),
            "total_in_db": len(merged),
            "elapsed_seconds": int(time.time() - start_time),
            "paths": meta.get("paths")
        }
        save_history(history_entry)
        update_manifest(meta)
        
        # Final status
        if actor_status == "SUCCEEDED":
            final_msg = f"Imported! {len(normalized)} valid items, {len(new_items)} new"
            final_status = "completed"
        else:
            final_msg = f"Import ended: {actor_status}. {len(normalized)} valid items"
            final_status = "failed"
        
        if skipped_no_coords:
            final_msg = f"{final_msg} (skipped {skipped_no_coords} without coords)"
        
        update_job_status(
            job_id,
            status=final_status,
            message=final_msg,
            progress_percent=100,
            items_new=len(new_items)
        )
        
    except Exception as e:
        update_job_status(job_id, status="failed", message=f"Import error: {str(e)}", error=str(e))
        print(f"[{job_id}] Import error: {e}")
