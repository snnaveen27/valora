"""
Test script for model retraining pipeline
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_retraining_check():
    """Test checking if retraining is needed"""
    print("=" * 60)
    print("TEST 1: Check if Retraining Needed")
    print("=" * 60)
    
    response = requests.post(f"{BASE_URL}/api/models/retraining/check")
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Retraining needed: {result.get('retraining_needed')}")
    print(f"Reason: {result.get('reason')}")
    print()

def test_retraining_status():
    """Test getting retraining status"""
    print("=" * 60)
    print("TEST 2: Get Retraining Status")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/models/retraining/status")
    result = response.json()
    
    print(f"Status: {response.status_code}")
    status = result.get("retraining_status", {})
    print(f"Last retrain: {status.get('last_retrain', 'Never')}")
    print(f"Total retrains: {status.get('total_retrains', 0)}")
    print(f"Status: {status.get('status', 'unknown')}")
    
    if status.get('last_metrics'):
        print("\nLast Metrics:")
        for model, metrics in status['last_metrics'].items():
            if metrics:
                print(f"  {model}:")
                for key, value in metrics.items():
                    print(f"    {key}: {value:.4f}" if isinstance(value, float) else f"    {key}: {value}")
    print()

def test_trigger_retraining_async():
    """Test triggering async retraining"""
    print("=" * 60)
    print("TEST 3: Trigger Async Retraining")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/api/models/retrain",
        params={"force": True, "run_async": True}
    )
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Message: {result.get('message')}")
    print(f"Forced: {result.get('forced')}")
    print(f"Check status at: {result.get('check_status_at')}")
    print("\nWaiting 5 seconds for background job...")
    time.sleep(5)
    print()

def test_retraining_history():
    """Test getting retraining history"""
    print("=" * 60)
    print("TEST 4: Get Retraining History")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/models/retraining/history?limit=5")
    result = response.json()
    
    print(f"Status: {response.status_code}")
    history = result.get("history", [])
    print(f"History entries: {len(history)}")
    
    for i, entry in enumerate(history[:3], 1):
        print(f"\nEntry {i}:")
        print(f"  Timestamp: {entry.get('timestamp')}")
        print(f"  Status: {entry.get('overall_status')}")
        if 'training_samples' in entry:
            print(f"  Training samples: {entry['training_samples']}")
    print()

def test_model_metrics():
    """Test getting current model metrics"""
    print("=" * 60)
    print("TEST 5: Get Model Metrics")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/models/metrics")
    result = response.json()
    
    print(f"Status: {response.status_code}")
    metrics = result.get("metrics", {})
    print(f"Last retrain: {result.get('last_retrain', 'Never')}")
    
    if metrics:
        print("\nCurrent Metrics:")
        for model, model_metrics in metrics.items():
            if model_metrics:
                print(f"  {model}:")
                for key, value in model_metrics.items():
                    if isinstance(value, float):
                        print(f"    {key}: {value:.4f}")
                    else:
                        print(f"    {key}: {value}")
    else:
        print("No metrics available yet")
    print()

def test_scheduler_status():
    """Test getting scheduler status"""
    print("=" * 60)
    print("TEST 6: Get Scheduler Status")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/models/scheduler/status")
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Scheduler running: {result.get('scheduler_running')}")
    
    jobs = result.get("scheduled_jobs", [])
    print(f"Scheduled jobs: {len(jobs)}")
    
    for job in jobs:
        print(f"\n  Job: {job.get('name')}")
        print(f"  ID: {job.get('id')}")
        print(f"  Next run: {job.get('next_run_time')}")
        print(f"  Trigger: {job.get('trigger')}")
    print()

def test_start_scheduler():
    """Test starting the scheduler"""
    print("=" * 60)
    print("TEST 7: Start Scheduler (Optional)")
    print("=" * 60)
    
    print("Do you want to start the scheduler? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        response = requests.post(
            f"{BASE_URL}/api/models/scheduler/start",
            params={
                "schedule_type": "interval",
                "interval_hours": 1  # Test with 1 hour interval
            }
        )
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Message: {result.get('message')}")
        print(f"Schedule: {result.get('schedule')}")
        print("\nScheduler started successfully!")
        print("Note: This will run retraining every hour for testing")
        print("To stop: curl -X POST http://localhost:8000/api/models/scheduler/stop")
    else:
        print("Scheduler not started (skipped)")
    print()

def run_all_tests():
    """Run all tests"""
    print("\n🧪 REALTY-GPT Model Retraining Pipeline Tests")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    print()
    
    try:
        # Check if backend is running
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend is not healthy")
            return
        print("✅ Backend is running\n")
        
        # Run tests
        test_retraining_check()
        test_retraining_status()
        test_model_metrics()
        test_retraining_history()
        test_scheduler_status()
        test_trigger_retraining_async()
        test_start_scheduler()
        
        print("=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        print("\n📚 Next Steps:")
        print("1. Check retraining status: curl http://localhost:8000/api/models/retraining/status")
        print("2. View metrics: curl http://localhost:8000/api/models/metrics")
        print("3. API docs: http://localhost:8000/docs#/models")
        print()
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend at", BASE_URL)
        print("   Make sure backend is running: python backend/start_backend.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    run_all_tests()
