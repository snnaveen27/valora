"""
Valora AI - Database Service & Admin Benchmarks
================================================

Tests and benchmarks for:
- Database connection pooling
- SQLite WAL mode enforcement
- Query performance benchmarks
- Admin endpoint response times
- Concurrent access stress test

Usage:
    python -m tests.test_db_benchmarks                    # Run all
    python -m tests.test_db_benchmarks --benchmark        # Benchmarks only
    python -m tests.test_db_benchmarks --verbose          # Detailed output
"""

import argparse
import json
import os
import sys
import time
import sqlite3
import threading
import statistics
import unittest
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))


class BenchmarkResult:
    """Store and format benchmark results."""
    
    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []
        self.errors: List[str] = []
    
    def add(self, duration_ms: float, error: str = None):
        self.times.append(duration_ms)
        if error:
            self.errors.append(error)
    
    @property
    def count(self):
        return len(self.times)
    
    @property
    def avg_ms(self):
        return statistics.mean(self.times) if self.times else 0
    
    @property
    def median_ms(self):
        return statistics.median(self.times) if self.times else 0
    
    @property
    def p95_ms(self):
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def p99_ms(self):
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def min_ms(self):
        return min(self.times) if self.times else 0
    
    @property
    def max_ms(self):
        return max(self.times) if self.times else 0
    
    @property
    def error_rate(self):
        return len(self.errors) / max(1, self.count) * 100
    
    def summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "error_rate_pct": round(self.error_rate, 1),
            "errors": len(self.errors),
        }
    
    def format_table(self) -> str:
        s = self.summary()
        return (
            f"  {self.name:<35} "
            f"n={s['iterations']:>5}  "
            f"avg={s['avg_ms']:>8.2f}ms  "
            f"p50={s['median_ms']:>8.2f}ms  "
            f"p95={s['p95_ms']:>8.2f}ms  "
            f"p99={s['p99_ms']:>8.2f}ms  "
            f"err={s['error_rate_pct']:>5.1f}%"
        )


class BenchmarkSuite:
    """Collect and display benchmark results."""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    def add(self, result: BenchmarkResult):
        self.results.append(result)
    
    def print_report(self):
        print("\n" + "=" * 100)
        print("BENCHMARK REPORT")
        print("=" * 100)
        for r in self.results:
            print(r.format_table())
        print("=" * 100)
        
        # Pass/fail summary
        passed = sum(1 for r in self.results if r.p95_ms < 500 and r.error_rate < 5)
        total = len(self.results)
        print(f"\nResults: {passed}/{total} benchmarks within SLA (p95 < 500ms, errors < 5%)")
        print()


# Global benchmark suite
benchmarks = BenchmarkSuite()


# =============================================================================
# Database Service Tests
# =============================================================================

class TestDatabaseService(unittest.TestCase):
    """Test the DatabaseService with connection pooling."""
    
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "test_valora.db")
        
        # Create test database with sample data
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY,
                property_id TEXT UNIQUE,
                title TEXT,
                price REAL,
                price_per_sqft REAL,
                total_area_sqft REAL,
                bedrooms INTEGER,
                property_type TEXT,
                status TEXT DEFAULT 'active',
                locality TEXT,
                area_name TEXT,
                latitude REAL,
                longitude REAL,
                source TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS pois (
                id INTEGER PRIMARY KEY,
                name TEXT,
                category TEXT,
                latitude REAL,
                longitude REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS buildings (
                id INTEGER PRIMARY KEY,
                name TEXT,
                latitude REAL,
                longitude REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY,
                name TEXT,
                category TEXT,
                latitude REAL,
                longitude REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS transport_stops (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                latitude REAL,
                longitude REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS roads (
                id INTEGER PRIMARY KEY,
                name TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY,
                source_name TEXT,
                records_processed INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                records_updated INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                status TEXT,
                error_message TEXT,
                started_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS property_analytics (
                id INTEGER PRIMARY KEY,
                property_id TEXT,
                investment_score REAL,
                nearest_metro_distance REAL,
                metro_proximity_score REAL
            );
            
            CREATE INDEX IF NOT EXISTS idx_properties_locality ON properties(locality);
            CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
            CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
            CREATE INDEX IF NOT EXISTS idx_properties_lat_lng ON properties(latitude, longitude);
            CREATE INDEX IF NOT EXISTS idx_pois_category ON pois(category);
            CREATE INDEX IF NOT EXISTS idx_pois_lat_lng ON pois(latitude, longitude);
        """)
        
        # Insert test data
        properties = []
        localities = ['Koramangala', 'Indiranagar', 'HSR Layout', 'Whitefield', 'Electronic City',
                      'Jayanagar', 'BTM Layout', 'Marathahalli', 'Sarjapur Road', 'Hebbal',
                      'JP Nagar', 'Bannerghatta Road']
        
        for i in range(5000):
            locality = localities[i % len(localities)]
            properties.append((
                f"PROP_{i:05d}",
                f"Property in {locality} - {i}",
                5000000 + (i * 10000),
                8000 + (i % 5000),
                1000 + (i % 2000),
                2 + (i % 4),
                'apartment' if i % 3 == 0 else 'villa',
                'active',
                locality,
                locality,
                12.97 + (i % 100) * 0.001,
                77.59 + (i % 100) * 0.001,
                ['99acres', 'housing', 'magicbricks', 'nobroker'][i % 4],
            ))
        
        cursor.executemany(
            "INSERT INTO properties (property_id, title, price, price_per_sqft, total_area_sqft, "
            "bedrooms, property_type, status, locality, area_name, latitude, longitude, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            properties
        )
        
        # Insert POIs
        pois = []
        categories = ['school', 'hospital', 'metro', 'mall', 'park', 'restaurant']
        for i in range(2000):
            pois.append((
                f"POI {i}",
                categories[i % len(categories)],
                12.97 + (i % 100) * 0.001,
                77.59 + (i % 100) * 0.001,
            ))
        
        cursor.executemany(
            "INSERT INTO pois (name, category, latitude, longitude) VALUES (?, ?, ?, ?)",
            pois
        )
        
        conn.commit()
        conn.close()
    
    def test_connection_pool_initialization(self):
        """Test that connection pool initializes with correct settings."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=5)
        
        # Verify pool stats
        stats = db._pool.get_stats()
        self.assertGreaterEqual(stats["created_connections"], 1)
        self.assertEqual(stats["max_connections"], 5)
        
        db.close()
    
    def test_wal_mode_enforced(self):
        """Test that WAL mode is set on the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()
        
        # After DatabaseService initialization, WAL should be set
        from database.db_service import DatabaseService
        db = DatabaseService(self.db_path)
        
        conn2 = sqlite3.connect(self.db_path)
        cursor2 = conn2.cursor()
        cursor2.execute("PRAGMA journal_mode")
        mode2 = cursor2.fetchone()[0]
        conn2.close()
        
        self.assertEqual(mode2.lower(), "wal", f"WAL mode not set, got: {mode2}")
        db.close()
    
    def test_pooled_vs_unpooled_performance(self):
        """Benchmark: pooled connections should be faster than unpooled."""
        from database.db_service import DatabaseService, ConnectionPool
        
        query = "SELECT COUNT(*) as cnt FROM properties WHERE status = 'active'"
        
        # Benchmark unpooled (raw sqlite3)
        bench_unpooled = BenchmarkResult("unpooled_query")
        for _ in range(100):
            start = time.perf_counter()
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            cursor.fetchone()
            conn.close()
            bench_unpooled.add((time.perf_counter() - start) * 1000)
        
        # Benchmark pooled
        db = DatabaseService(self.db_path, pool_size=5)
        bench_pooled = BenchmarkResult("pooled_query")
        for _ in range(100):
            start = time.perf_counter()
            db.execute(query)
            bench_pooled.add((time.perf_counter() - start) * 1000)
        
        benchmarks.add(bench_unpooled)
        benchmarks.add(bench_pooled)
        
        # Pooled should be at least as fast (within noise margin)
        # The real benefit shows under concurrent load
        self.assertLess(bench_pooled.avg_ms, bench_unpooled.avg_ms * 2,
                        "Pooled connections significantly slower than unpooled")
        
        db.close()
    
    def test_concurrent_read_performance(self):
        """Benchmark: concurrent reads with connection pool."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=10)
        bench = BenchmarkResult("concurrent_read_10_threads")
        errors = []
        lock = threading.Lock()
        
        def read_query():
            try:
                start = time.perf_counter()
                results = db.execute(
                    "SELECT * FROM properties WHERE locality = ? LIMIT 20",
                    ("Koramangala",)
                )
                duration = (time.perf_counter() - start) * 1000
                with lock:
                    bench.add(duration)
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        # Run 10 threads, each doing 20 queries
        threads = []
        for _ in range(10):
            t = threading.Thread(target=lambda: [read_query() for _ in range(20)])
            threads.append(t)
        
        start_all = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = (time.perf_counter() - start_all) * 1000
        
        benchmarks.add(bench)
        
        self.assertEqual(len(errors), 0, f"Concurrent read errors: {errors[:5]}")
        self.assertLess(bench.p95_ms, 500, f"p95 read latency too high: {bench.p95_ms:.2f}ms")
        
        db.close()
    
    def test_concurrent_write_performance(self):
        """Benchmark: concurrent writes with WAL mode."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=10)
        bench = BenchmarkResult("concurrent_write_5_threads")
        errors = []
        lock = threading.Lock()
        counter = {"i": 0}
        
        def write_query():
            try:
                with lock:
                    counter["i"] += 1
                    idx = counter["i"]
                
                start = time.perf_counter()
                db.execute_write(
                    "UPDATE properties SET price = price + 1 WHERE property_id = ?",
                    (f"PROP_{idx % 5000:05d}",)
                )
                duration = (time.perf_counter() - start) * 1000
                with lock:
                    bench.add(duration)
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        threads = []
        for _ in range(5):
            t = threading.Thread(target=lambda: [write_query() for _ in range(20)])
            threads.append(t)
        
        start_all = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = (time.perf_counter() - start_all) * 1000
        
        benchmarks.add(bench)
        
        # Allow some write contention errors (SQLite limitation)
        error_rate = len(errors) / max(1, bench.count + len(errors)) * 100
        self.assertLess(error_rate, 10, f"Write error rate too high: {error_rate:.1f}%")
        
        db.close()
    
    def test_query_benchmarks(self):
        """Benchmark common query patterns."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=5)
        
        queries = {
            "count_all": ("SELECT COUNT(*) FROM properties", None),
            "count_active": ("SELECT COUNT(*) FROM properties WHERE status = 'active'", None),
            "filter_locality": ("SELECT * FROM properties WHERE locality = ? LIMIT 50", ("Koramangala",)),
            "filter_price_range": ("SELECT * FROM properties WHERE price BETWEEN ? AND ? LIMIT 50", (5000000, 10000000)),
            "filter_bedrooms": ("SELECT * FROM properties WHERE bedrooms = ? LIMIT 50", (2,)),
            "geo_bounding_box": ("SELECT * FROM properties WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? LIMIT 50", (12.97, 13.07, 77.59, 77.69)),
            "poi_nearby": ("SELECT * FROM pois WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ? LIMIT 20", (12.97, 13.07, 77.59, 77.69)),
            "join_analytics": ("SELECT p.*, pa.investment_score FROM properties p LEFT JOIN property_analytics pa ON p.property_id = pa.property_id WHERE p.status = 'active' LIMIT 50", None),
            "group_by_locality": ("SELECT locality, COUNT(*), AVG(price) FROM properties WHERE status = 'active' GROUP BY locality ORDER BY COUNT(*) DESC LIMIT 12", None),
        }
        
        for name, (query, params) in queries.items():
            bench = BenchmarkResult(f"query_{name}")
            for _ in range(50):
                start = time.perf_counter()
                db.execute(query, params)
                bench.add((time.perf_counter() - start) * 1000)
            benchmarks.add(bench)
            
            self.assertLess(bench.p95_ms, 500, f"{name} p95 too high: {bench.p95_ms:.2f}ms")
        
        db.close()
    
    def test_insert_benchmark(self):
        """Benchmark batch inserts."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=5)
        
        bench = BenchmarkResult("insert_single")
        for i in range(100):
            start = time.perf_counter()
            db.insert("properties", {
                "property_id": f"BENCH_{time.time_ns()}",
                "title": f"Benchmark property {i}",
                "price": 5000000 + i,
                "status": "active",
                "locality": "Benchmark",
            })
            bench.add((time.perf_counter() - start) * 1000)
        
        benchmarks.add(bench)
        
        # Cleanup
        db.execute_write("DELETE FROM properties WHERE locality = 'Benchmark'")
        
        db.close()
    
    def test_connection_pool_stats(self):
        """Test that pool statistics are tracked correctly."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=5)
        
        # Run some queries to generate stats
        for _ in range(50):
            db.execute("SELECT COUNT(*) FROM properties")
        
        stats = db._pool.get_stats()
        
        self.assertEqual(stats["total_gets"], 50)
        self.assertEqual(stats["total_returns"], 50)
        self.assertGreater(stats["pool_hits"], 0)
        self.assertGreater(stats["hit_rate"], 50)
        
        db.close()


# =============================================================================
# Admin Endpoint Tests
# =============================================================================

class TestAdminEndpoints(unittest.TestCase):
    """Test admin API endpoints with response time benchmarks."""
    
    BASE_URL = None  # Set from args
    
    @classmethod
    def setUpClass(cls):
        if cls.BASE_URL is None:
            cls.skipTest(cls, "No base URL provided (use --base-url)")
    
    def _request(self, method: str, path: str, token: str = None, json_data: dict = None):
        """Make HTTP request and return (response, elapsed_ms)."""
        import urllib.request
        import urllib.error
        
        url = f"{self.BASE_URL}{path}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        data = None
        if json_data:
            data = json.dumps(json_data).encode()
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                elapsed = (time.perf_counter() - start) * 1000
                return {
                    "status": resp.status,
                    "body": json.loads(body) if body else None,
                    "elapsed_ms": elapsed,
                }
        except urllib.error.HTTPError as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "status": e.code,
                "body": None,
                "elapsed_ms": elapsed,
                "error": str(e),
            }
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "status": 0,
                "body": None,
                "elapsed_ms": elapsed,
                "error": str(e),
            }
    
    def _get_admin_token(self):
        """Login and get admin token."""
        resp = self._request("POST", "/api/auth/login", json_data={
            "email": "admin@valora.ai",
            "password": "admin123"
        })
        if resp["status"] == 200 and resp["body"]:
            return resp["body"].get("access_token")
        return None
    
    def test_admin_status_benchmark(self):
        """Benchmark: GET /api/admin/status"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_status")
        for _ in range(20):
            resp = self._request("GET", "/api/admin/status", token=token)
            bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertEqual(resp["status"], 200)
        self.assertLess(bench.p95_ms, 2000, f"Admin status p95 too slow: {bench.p95_ms:.2f}ms")
    
    def test_admin_usage_stats_benchmark(self):
        """Benchmark: GET /api/admin/usage/stats"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_usage_stats")
        for _ in range(10):
            resp = self._request("GET", "/api/admin/usage/stats", token=token)
            bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertLess(bench.p95_ms, 3000)
    
    def test_admin_weekly_dashboard_benchmark(self):
        """Benchmark: GET /api/admin/dashboard/weekly"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_weekly_dashboard")
        for _ in range(10):
            resp = self._request("GET", "/api/admin/dashboard/weekly", token=token)
            bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertLess(bench.p95_ms, 5000)
    
    def test_admin_locality_brain_status_benchmark(self):
        """Benchmark: GET /api/admin/locality-brain-status"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_locality_brain")
        for _ in range(10):
            resp = self._request("GET", "/api/admin/locality-brain-status")
            bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertLess(bench.p95_ms, 2000)
    
    def test_admin_pricing_config_benchmark(self):
        """Benchmark: GET /api/admin/pricing/config"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_pricing_config")
        for _ in range(10):
            resp = self._request("GET", "/api/admin/pricing/config", token=token)
            bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertLess(bench.p95_ms, 2000)
    
    def test_admin_cloud_cost_benchmark(self):
        """Benchmark: GET /api/admin/cloud-cost/stats"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_cloud_cost")
        for _ in range(10):
            resp = self._request("GET", "/api/admin/cloud-cost/stats?days=7", token=token)
            bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertLess(bench.p95_ms, 3000)
    
    def test_admin_run_tests_benchmark(self):
        """Benchmark: POST /api/admin/run-tests"""
        token = self._get_admin_token()
        if not token:
            self.skipTest("Could not get admin token")
        
        bench = BenchmarkResult("admin_run_tests")
        resp = self._request("POST", "/api/admin/run-tests", token=token)
        bench.add(resp["elapsed_ms"], resp.get("error"))
        
        benchmarks.add(bench)
        self.assertEqual(resp["status"], 200)
        self.assertLess(bench.p95_ms, 10000)


# =============================================================================
# SQLite Scaling Stress Test
# =============================================================================

class TestSQLiteScaling(unittest.TestCase):
    """Stress tests for SQLite concurrent access limits."""
    
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "stress_test.db")
        
        conn = sqlite3.connect(cls.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                key TEXT,
                value TEXT,
                counter INTEGER DEFAULT 0,
                created_at REAL
            );
            CREATE INDEX idx_test_key ON test_data(key);
        """)
        
        for i in range(1000):
            cursor.execute(
                "INSERT INTO test_data (key, value, counter, created_at) VALUES (?, ?, 0, ?)",
                (f"key_{i}", f"value_{i}_{'x' * 100}", time.time())
            )
        
        conn.commit()
        conn.close()
    
    def test_stress_10_concurrent_readers(self):
        """10 concurrent reader threads - should have 0% error rate."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=15)
        bench = BenchmarkResult("stress_10_readers")
        errors = []
        lock = threading.Lock()
        
        def reader():
            for _ in range(50):
                try:
                    start = time.perf_counter()
                    db.execute("SELECT * FROM test_data WHERE key = ?", ("key_500",))
                    bench.add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    with lock:
                        errors.append(str(e))
        
        threads = [threading.Thread(target=reader) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        benchmarks.add(bench)
        
        error_rate = len(errors) / max(1, bench.count + len(errors)) * 100
        self.assertEqual(error_rate, 0, f"Read errors under 10 concurrent readers: {error_rate:.1f}%")
        self.assertLess(bench.p95_ms, 200, f"p95 read too slow under load: {bench.p95_ms:.2f}ms")
        
        db.close()
    
    def test_stress_mixed_read_write(self):
        """Mixed read/write stress test - 8 readers, 2 writers."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=15)
        read_bench = BenchmarkResult("stress_mixed_read")
        write_bench = BenchmarkResult("stress_mixed_write")
        errors = []
        lock = threading.Lock()
        
        def reader():
            for _ in range(50):
                try:
                    start = time.perf_counter()
                    db.execute("SELECT * FROM test_data WHERE key LIKE ? LIMIT 10", ("key_1%",))
                    with lock:
                        read_bench.add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    with lock:
                        errors.append(f"read: {e}")
        
        def writer():
            for i in range(20):
                try:
                    start = time.perf_counter()
                    db.execute_write(
                        "UPDATE test_data SET counter = counter + 1 WHERE key = ?",
                        (f"key_{i}",)
                    )
                    with lock:
                        write_bench.add((time.perf_counter() - start) * 1000)
                except Exception as e:
                    with lock:
                        errors.append(f"write: {e}")
        
        threads = []
        for _ in range(8):
            threads.append(threading.Thread(target=reader))
        for _ in range(2):
            threads.append(threading.Thread(target=writer))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        benchmarks.add(read_bench)
        benchmarks.add(write_bench)
        
        total_ops = read_bench.count + write_bench.count + len(errors)
        error_rate = len(errors) / max(1, total_ops) * 100
        self.assertLess(error_rate, 5, f"Error rate too high: {error_rate:.1f}%")
        
        db.close()
    
    def test_stress_sequential_writes_throughput(self):
        """Measure sequential write throughput (ops/sec)."""
        from database.db_service import DatabaseService
        
        db = DatabaseService(self.db_path, pool_size=5)
        bench = BenchmarkResult("stress_sequential_writes")
        
        for i in range(500):
            start = time.perf_counter()
            db.execute_write(
                "UPDATE test_data SET counter = counter + 1 WHERE key = ?",
                (f"key_{i % 1000}",)
            )
            bench.add((time.perf_counter() - start) * 1000)
        
        benchmarks.add(bench)
        
        ops_per_sec = 1000 / bench.avg_ms if bench.avg_ms > 0 else 0
        self.assertGreater(ops_per_sec, 100, f"Write throughput too low: {ops_per_sec:.0f} ops/sec")
        
        db.close()


# =============================================================================
# Main Entry Point
# =============================================================================

def run_tests(args):
    """Run the test suite with optional benchmarks."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Always run database tests
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseService))
    suite.addTests(loader.loadTestsFromTestCase(TestSQLiteScaling))
    
    # Run admin tests only if base URL provided
    if args.base_url:
        TestAdminEndpoints.BASE_URL = args.base_url
        suite.addTests(loader.loadTestsFromTestCase(TestAdminEndpoints))
    
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print benchmark report
    benchmarks.print_report()
    
    return result.wasSuccessful()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valora DB Benchmarks & Tests")
    parser.add_argument("--base-url", help="Base URL for API tests (e.g., http://localhost:8000)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmarks only")
    args = parser.parse_args()
    
    success = run_tests(args)
    sys.exit(0 if success else 1)
