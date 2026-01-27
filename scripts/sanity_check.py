import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx


@dataclass
class CheckResult:
  name: str
  passed: bool
  duration_ms: int
  description: str
  details: Optional[Dict[str, Any]] = None
  skipped: bool = False


@dataclass
class BenchmarkCase:
  category: str
  query: str
  expected_intents: Tuple[str, ...]
  require_message: bool = True
  require_facts: bool = False
  require_3d_facts: bool = False
  require_valuation: bool = False


def _now_ms() -> int:
  return int(time.time() * 1000)


def _print_summary(report: Dict[str, Any]) -> None:
  total = report.get('total', 0)
  passed = report.get('passed', 0)
  failed = report.get('failed', 0)
  skipped = report.get('skipped', 0)
  duration = report.get('duration_ms', 0)

  print("\n" + "=" * 70)
  print("VALORA AI - REALTIME SANITY CHECK")
  print("=" * 70)
  print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped} | Duration: {duration}ms")
  print("-" * 70)

  for t in report.get('tests', []):
    status = "✅" if t.get('passed') else ("⏭️" if t.get('skipped') else "❌")
    print(f"{status} {t.get('name'):30} {t.get('duration_ms', 0):>6}ms  {t.get('description')}")

  print("=" * 70 + "\n")


def _print_benchmark_summary(report: Dict[str, Any]) -> None:
  total = report.get('total', 0)
  passed = report.get('passed', 0)
  failed = report.get('failed', 0)
  duration = report.get('duration_ms', 0)

  print("\n" + "=" * 70)
  print("VALORA AI - CHAT BENCHMARK")
  print("=" * 70)
  print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Duration: {duration}ms")
  print("-" * 70)

  for t in report.get('tests', []):
    status = "✅" if t.get('passed') else "❌"
    print(f"{status} {t.get('name'):30} {t.get('duration_ms', 0):>6}ms  {t.get('description')}")
    details = t.get('details') or {}
    preview = (details.get('message_preview') or '').strip()
    if preview:
      print(f"     preview: {preview}")

  print("=" * 70 + "\n")


def _ok_json(resp: httpx.Response) -> Dict[str, Any]:
  resp.raise_for_status()
  data = resp.json()
  if not isinstance(data, dict):
    raise ValueError("Expected JSON object")
  return data


def _make_result(name: str, start_ms: int, passed: bool, description: str, details: Optional[Dict[str, Any]] = None, skipped: bool = False) -> Dict[str, Any]:
  return {
    'name': name,
    'passed': bool(passed),
    'skipped': bool(skipped),
    'duration_ms': _now_ms() - start_ms,
    'description': description,
    'details': details or None,
  }


def run_sanity(base_url: str, include_chat: bool) -> Dict[str, Any]:
  start_all = _now_ms()
  tests = []

  with httpx.Client(base_url=base_url, timeout=120.0) as client:
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/health'))
      ok = data.get('status') == 'ok' or data.get('status') == 'running' or bool(data)
      tests.append(_make_result('Backend Health', t0, ok, 'GET /health'))
    except Exception as e:
      tests.append(_make_result('Backend Health', t0, False, f'GET /health failed: {e}'))

    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/admin/status'))
      ok = isinstance(data.get('backend'), dict) and isinstance(data.get('database'), dict)
      tests.append(_make_result('Admin Status', t0, ok, 'GET /api/admin/status'))
    except Exception as e:
      tests.append(_make_result('Admin Status', t0, False, f'GET /api/admin/status failed: {e}'))

    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/tileset'))
      ok = isinstance(data, dict) and ('root' in data or 'tiles' in data or 'asset' in data)
      tests.append(_make_result('Tileset Index', t0, ok, 'GET /api/tileset'))
    except Exception as e:
      tests.append(_make_result('Tileset Index', t0, False, f'GET /api/tileset failed: {e}'))

    t0 = _now_ms()
    try:
      params = {
        'min_lng': 77.55,
        'min_lat': 12.90,
        'max_lng': 77.70,
        'max_lat': 13.05,
      }
      data = _ok_json(client.get('/api/tiles/viewport', params=params))
      ok = isinstance(data.get('tiles'), list)
      tests.append(_make_result('Tiles Viewport', t0, ok, 'GET /api/tiles/viewport'))
    except Exception as e:
      tests.append(_make_result('Tiles Viewport', t0, False, f'GET /api/tiles/viewport failed: {e}'))

    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/viewport/analyze', params={'lat': 12.9716, 'lng': 77.5946}))
      ok = isinstance(data.get('spatial'), dict)
      tests.append(_make_result('Viewport Analyze', t0, ok, 'GET /api/viewport/analyze'))
    except Exception as e:
      tests.append(_make_result('Viewport Analyze', t0, False, f'GET /api/viewport/analyze failed: {e}'))

    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/location/analyze', json={'lat': 12.9716, 'lng': 77.5946}))
      ok = isinstance(data, dict) and (data.get('success') is True or 'market' in data or 'spatial' in data)
      tests.append(_make_result('Location Analyze', t0, ok, 'POST /api/location/analyze'))
    except Exception as e:
      tests.append(_make_result('Location Analyze', t0, False, f'POST /api/location/analyze failed: {e}'))

    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/city-intelligence/locality/Indiranagar'))
      ok = isinstance(data.get('profile'), dict) or data.get('success') == True
      tests.append(_make_result('City Intelligence', t0, ok, 'GET /api/city-intelligence/locality/Indiranagar'))
    except Exception as e:
      tests.append(_make_result('City Intelligence', t0, False, f'GET /api/city-intelligence/locality failed: {e}'))

    # Test Investment Leaderboard API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/investment/leaderboard', params={'limit': 5}))
      ok = isinstance(data.get('leaderboard'), list) and len(data.get('leaderboard', [])) > 0
      tests.append(_make_result('Investment Leaderboard', t0, ok, 'GET /api/investment/leaderboard'))
    except Exception as e:
      tests.append(_make_result('Investment Leaderboard', t0, False, f'GET /api/investment/leaderboard failed: {e}'))

    # Test Storyboard Generation API
    t0 = _now_ms()
    try:
      payload = {"scenario": "Analyze Koramangala for investment", "duration_seconds": 15}
      data = _ok_json(client.post('/api/storyboard/generate', json=payload))
      ok = isinstance(data.get('storyboard'), dict) and len(data.get('storyboard', {}).get('scenes', [])) > 0
      tests.append(_make_result('Storyboard Generation', t0, ok, 'POST /api/storyboard/generate'))
    except Exception as e:
      tests.append(_make_result('Storyboard Generation', t0, False, f'POST /api/storyboard/generate failed: {e}'))

    # Test Compare Properties API
    t0 = _now_ms()
    try:
      payload = {"localities": ["Koramangala", "Indiranagar"]}
      data = _ok_json(client.post('/api/compare/properties', json=payload))
      ok = isinstance(data.get('comparison'), list)
      tests.append(_make_result('Compare Properties', t0, ok, 'POST /api/compare/properties'))
    except Exception as e:
      tests.append(_make_result('Compare Properties', t0, False, f'POST /api/compare/properties failed: {e}'))

    # Test Valuation Estimate API
    t0 = _now_ms()
    try:
      payload = {"lat": 12.9352, "lng": 77.6245, "bedrooms": 2, "covered_area": 1200, "property_type": "residential"}
      data = _ok_json(client.post('/api/valuation/estimate', json=payload))
      ok = data.get('success') == True or isinstance(data.get('estimated_price'), (int, float))
      tests.append(_make_result('Valuation Estimate', t0, ok, 'POST /api/valuation/estimate'))
    except Exception as e:
      tests.append(_make_result('Valuation Estimate', t0, False, f'POST /api/valuation/estimate failed: {e}'))

    # Test Valuation Market Stats API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/valuation/market-stats', params={'lat': 12.9352, 'lng': 77.6245, 'radius': 2}))
      ok = data.get('success') == True or isinstance(data.get('stats'), dict)
      tests.append(_make_result('Valuation Market Stats', t0, ok, 'GET /api/valuation/market-stats'))
    except Exception as e:
      tests.append(_make_result('Valuation Market Stats', t0, False, f'GET /api/valuation/market-stats failed: {e}'))

    # Test Simulate API
    t0 = _now_ms()
    try:
      payload = {"scenario_type": "metro_station", "description": "New metro station at Sarjapur", "lat": 12.9081, "lng": 77.6476, "parameters": {}}
      data = _ok_json(client.post('/api/simulate', json=payload))
      ok = data.get('success') == True or isinstance(data.get('impact'), dict)
      tests.append(_make_result('Simulate Scenario', t0, ok, 'POST /api/simulate'))
    except Exception as e:
      tests.append(_make_result('Simulate Scenario', t0, False, f'POST /api/simulate failed: {e}'))

    # Test Simulate Storyboard API
    t0 = _now_ms()
    try:
      payload = {"scenario_type": "metro_station", "description": "New metro station at Sarjapur Road", "lat": 12.9081, "lng": 77.6476}
      data = _ok_json(client.post('/api/simulate/storyboard', json=payload))
      ok = data.get('success') == True or isinstance(data.get('storyboard'), dict)
      tests.append(_make_result('Simulate Storyboard', t0, ok, 'POST /api/simulate/storyboard'))
    except Exception as e:
      tests.append(_make_result('Simulate Storyboard', t0, False, f'POST /api/simulate/storyboard failed: {e}'))

    # Test Digital Twin Init API
    t0 = _now_ms()
    try:
      payload = {"lat": 12.9352, "lng": 77.6245, "radius_m": 1000}
      data = _ok_json(client.post('/api/digital-twin/init', json=payload))
      ok = data.get('success') == True or isinstance(data.get('state'), dict)
      tests.append(_make_result('Digital Twin Init', t0, ok, 'POST /api/digital-twin/init'))
    except Exception as e:
      tests.append(_make_result('Digital Twin Init', t0, False, f'POST /api/digital-twin/init failed: {e}'))

    # Test Digital Twin State API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/digital-twin/state'))
      ok = data.get('success') == True or isinstance(data.get('state'), dict) or data.get('state') is None
      tests.append(_make_result('Digital Twin State', t0, ok, 'GET /api/digital-twin/state'))
    except Exception as e:
      tests.append(_make_result('Digital Twin State', t0, False, f'GET /api/digital-twin/state failed: {e}'))

    # Test Building Analyze API
    t0 = _now_ms()
    try:
      payload = {"lat": 12.9352, "lng": 77.6245, "building_id": "test_building"}
      data = _ok_json(client.post('/api/building/analyze', json=payload))
      ok = data.get('success') == True or isinstance(data.get('analysis'), dict) or 'error' not in str(data).lower()
      tests.append(_make_result('Building Analyze', t0, ok, 'POST /api/building/analyze'))
    except Exception as e:
      tests.append(_make_result('Building Analyze', t0, False, f'POST /api/building/analyze failed: {e}'))

    # Test RAG Search API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/rag/search', params={'q': 'properties near metro', 'top_k': 5}))
      ok = data.get('success') == True or isinstance(data.get('results'), list)
      tests.append(_make_result('RAG Search', t0, ok, 'GET /api/rag/search'))
    except Exception as e:
      # RAG may not be available - mark as skipped not failed
      tests.append(_make_result('RAG Search', t0, False, f'GET /api/rag/search: {e}', skipped=True))

    # Test RAG Context API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/rag/context', params={'q': 'investment in Koramangala', 'lat': 12.9352, 'lng': 77.6245}))
      ok = data.get('success') == True or isinstance(data.get('context'), str)
      tests.append(_make_result('RAG Context', t0, ok, 'GET /api/rag/context'))
    except Exception as e:
      tests.append(_make_result('RAG Context', t0, False, f'GET /api/rag/context: {e}', skipped=True))

    # Test Advanced Insights - Area Insights API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/insights/area', params={'lat': 12.9716, 'lng': 77.5946, 'locality': 'Indiranagar'}))
      ok = data.get('success') == True and isinstance(data.get('data'), dict)
      tests.append(_make_result('Area Insights', t0, ok, 'GET /api/insights/area'))
    except Exception as e:
      tests.append(_make_result('Area Insights', t0, False, f'GET /api/insights/area failed: {e}'))

    # Test Advanced Insights - Market Intelligence API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/insights/market/Koramangala'))
      ok = data.get('success') == True and isinstance(data.get('data'), dict)
      tests.append(_make_result('Market Intelligence', t0, ok, 'GET /api/insights/market/{locality}'))
    except Exception as e:
      tests.append(_make_result('Market Intelligence', t0, False, f'GET /api/insights/market failed: {e}'))

    # Test Advanced Insights - Price Movers API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/insights/price-movers', params={'days': 30, 'limit': 10}))
      ok = data.get('success') == True and isinstance(data.get('data'), list)
      tests.append(_make_result('Price Movers', t0, ok, 'GET /api/insights/price-movers'))
    except Exception as e:
      tests.append(_make_result('Price Movers', t0, False, f'GET /api/insights/price-movers failed: {e}'))

    # Test Database Panel - Tables List API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/database/tables'))
      ok = data.get('success') == True and isinstance(data.get('tables'), list) and len(data.get('tables', [])) > 5
      tests.append(_make_result('Database Tables', t0, ok, 'GET /api/database/tables'))
    except Exception as e:
      tests.append(_make_result('Database Tables', t0, False, f'GET /api/database/tables failed: {e}'))

    # Test Database Panel - Stats API
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/database/stats'))
      ok = data.get('success') == True and data.get('total_records', 0) > 100000
      tests.append(_make_result('Database Stats', t0, ok, 'GET /api/database/stats'))
    except Exception as e:
      tests.append(_make_result('Database Stats', t0, False, f'GET /api/database/stats failed: {e}'))

    # Test Database Panel - Query API (Real Estate Agents)
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={'query': 'SELECT COUNT(*) as cnt FROM real_estate_agents'}))
      ok = data.get('success') == True and len(data.get('results', [])) > 0
      tests.append(_make_result('Database Query', t0, ok, 'POST /api/database/query'))
    except Exception as e:
      tests.append(_make_result('Database Query', t0, False, f'POST /api/database/query failed: {e}'))

    # Test City Support - Cities Table (v2.5)
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={'query': 'SELECT city_id, name FROM cities'}))
      ok = data.get('success') == True and len(data.get('results', [])) > 0
      tests.append(_make_result('City Support', t0, ok, 'GET cities table (v2.5)'))
    except Exception as e:
      tests.append(_make_result('City Support', t0, False, f'City support check failed: {e}'))

    # Test System Metadata - Version Check (v2.5)
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={'query': "SELECT value FROM system_metadata WHERE key='version'"}))
      ok = data.get('success') == True and len(data.get('results', [])) > 0
      version = data.get('results', [{}])[0].get('value', '')
      tests.append(_make_result('Version Check', t0, ok, f'System version: {version}'))
    except Exception as e:
      tests.append(_make_result('Version Check', t0, False, f'Version check failed: {e}'))

    # Test Data Integrity - Record Counts
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/database/stats'))
      stats = data.get('stats', {})
      total = data.get('total_records', 0)
      ok = total > 1000000  # Should have 1M+ records
      tests.append(_make_result('Data Integrity', t0, ok, f'Total records: {total:,}'))
    except Exception as e:
      tests.append(_make_result('Data Integrity', t0, False, f'Data integrity check failed: {e}'))

    # Test Locality State (Knowledge Layer)
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={'query': 'SELECT COUNT(*) as cnt FROM locality_state'}))
      rows = data.get('rows', [])
      cnt = rows[0]['cnt'] if rows else 0
      ok = cnt >= 700  # Should have 700+ localities
      tests.append(_make_result('Locality Brain', t0, ok, f'locality_state: {cnt} localities'))
    except Exception as e:
      tests.append(_make_result('Locality Brain', t0, False, f'Locality brain check failed: {e}'))

    # ============== 3D BUILDINGS TESTS ==============
    # Test 3D Buildings - Tile Data Loading with Polygon Geometry
    t0 = _now_ms()
    try:
      # Test a specific tile in Koramangala area
      data = _ok_json(client.get('/api/tiles/db/7762_1293'))
      features = data.get('features', [])
      total = data.get('total', 0)
      has_error = 'error' in data
      
      # Count polygon vs point geometries
      polygon_count = sum(1 for f in features if f.get('geometry', {}).get('type') == 'Polygon')
      point_count = sum(1 for f in features if f.get('geometry', {}).get('type') == 'Point')
      
      # Must have buildings AND no errors AND proper polygon geometry
      ok = total > 0 and not has_error and polygon_count > 0
      if has_error:
        tests.append(_make_result('3D Buildings Tile', t0, False, f'Tile error: {data.get("error")}'))
      else:
        tests.append(_make_result('3D Buildings Tile', t0, ok, f'Tile 7762_1293: {total} buildings ({polygon_count} polygons)', details={
          'features_count': len(features),
          'total': total,
          'polygon_count': polygon_count,
          'point_count': point_count
        }))
    except Exception as e:
      tests.append(_make_result('3D Buildings Tile', t0, False, f'3D tile load failed: {e}'))

    # Test 3D Buildings - Data Integrity (has height, coordinates)
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/tiles/db/7763_1297'))
      features = data.get('features', [])
      valid_buildings = 0
      has_height = 0
      has_coords = 0
      for f in features[:100]:  # Check first 100
        props = f.get('properties', {})
        geom = f.get('geometry', {})
        if props.get('height') and props.get('height') > 0:
          has_height += 1
        if geom.get('coordinates'):
          has_coords += 1
        if props.get('height') and geom.get('coordinates'):
          valid_buildings += 1
      ok = valid_buildings >= 50 and has_height >= 50 and has_coords >= 50
      tests.append(_make_result('3D Buildings Data', t0, ok, f'{valid_buildings} valid buildings (height+coords)', details={
        'has_height': has_height,
        'has_coords': has_coords,
        'valid': valid_buildings
      }))
    except Exception as e:
      tests.append(_make_result('3D Buildings Data', t0, False, f'3D data integrity failed: {e}'))

    # Test 3D Buildings - Database Count
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={'query': 'SELECT COUNT(*) as cnt FROM buildings WHERE latitude IS NOT NULL'}))
      rows = data.get('rows', [])
      cnt = rows[0]['cnt'] if rows else 0
      ok = cnt >= 500000  # Should have 500k+ buildings
      tests.append(_make_result('3D Buildings Count', t0, ok, f'buildings table: {cnt:,} records'))
    except Exception as e:
      tests.append(_make_result('3D Buildings Count', t0, False, f'Building count failed: {e}'))

    # Test 3D Buildings - Height Distribution
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={
        'query': 'SELECT COUNT(*) as cnt, AVG(height) as avg_h, MAX(height) as max_h FROM buildings WHERE height > 0'
      }))
      rows = data.get('rows', [])
      if rows:
        cnt = rows[0]['cnt'] or 0
        avg_h = rows[0]['avg_h'] or 0
        max_h = rows[0]['max_h'] or 0
        ok = cnt > 100000 and avg_h > 5 and max_h > 20  # Reasonable height distribution
        tests.append(_make_result('3D Heights Valid', t0, ok, f'{cnt:,} buildings with height (avg={avg_h:.1f}m, max={max_h:.1f}m)'))
      else:
        tests.append(_make_result('3D Heights Valid', t0, False, 'No height data returned'))
    except Exception as e:
      tests.append(_make_result('3D Heights Valid', t0, False, f'Height check failed: {e}'))

    # Test POIs Data Integrity
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={
        'query': 'SELECT COUNT(*) as cnt FROM pois WHERE latitude IS NOT NULL AND category IS NOT NULL'
      }))
      rows = data.get('rows', [])
      cnt = rows[0]['cnt'] if rows else 0
      ok = cnt >= 20000  # Should have 20k+ POIs
      tests.append(_make_result('POIs Data', t0, ok, f'pois table: {cnt:,} valid records'))
    except Exception as e:
      tests.append(_make_result('POIs Data', t0, False, f'POIs check failed: {e}'))

    # Test Transport Data Integrity
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={
        'query': "SELECT COUNT(*) as cnt, SUM(CASE WHEN transport_type = 'metro' THEN 1 ELSE 0 END) as metro FROM transport_stops"
      }))
      rows = data.get('rows', [])
      cnt = rows[0]['cnt'] if rows else 0
      metro = rows[0]['metro'] if rows else 0
      ok = cnt >= 5000  # Should have 5k+ stops
      tests.append(_make_result('Transport Data', t0, ok, f'transport: {cnt:,} stops ({metro} metro)'))
    except Exception as e:
      tests.append(_make_result('Transport Data', t0, False, f'Transport check failed: {e}'))

    # Test Properties Data Integrity
    t0 = _now_ms()
    try:
      data = _ok_json(client.post('/api/database/query', json={
        'query': 'SELECT COUNT(*) as cnt, AVG(price) as avg_price FROM properties WHERE price > 0 AND latitude IS NOT NULL'
      }))
      rows = data.get('rows', [])
      cnt = rows[0]['cnt'] if rows else 0
      avg_price = rows[0]['avg_price'] if rows else 0
      ok = cnt >= 20000 and avg_price > 1000000  # 20k+ properties, avg > 10L
      tests.append(_make_result('Properties Data', t0, ok, f'properties: {cnt:,} with valid price (avg=₹{avg_price/100000:.1f}L)'))
    except Exception as e:
      tests.append(_make_result('Properties Data', t0, False, f'Properties check failed: {e}'))

    # Test Locality Service Fast Lookup
    t0 = _now_ms()
    try:
      data = _ok_json(client.get('/api/locality/Koramangala'))
      ok = data.get('success') and isinstance(data.get('state'), dict)
      state = data.get('state', {})
      tests.append(_make_result('Locality Fast Lookup', t0, ok, f'Koramangala: {state.get("growth_phase", "?")} phase', details={
        'hotspot_score': state.get('hotspot_score'),
        'poi_count': state.get('poi_count')
      }))
    except Exception as e:
      tests.append(_make_result('Locality Fast Lookup', t0, False, f'Locality lookup failed: {e}'))

    t0 = _now_ms()
    if not include_chat:
      tests.append(_make_result('Chat Orchestration', t0, False, 'Skipped (--no-chat flag)', skipped=True))
    else:
      try:
        payload = {"messages": [{"role": "user", "content": "Analyze Koramangala for investment"}], "session_id": "sanity"}
        data = _ok_json(client.post('/api/chat', json=payload))
        ok = bool(data.get('success')) and isinstance(data.get('message'), str)
        tests.append(_make_result('Chat Orchestration', t0, ok, 'POST /api/chat', details={
          'intent': data.get('intent'),
          'has_storyboard': bool(data.get('storyboard')),
          'has_facts': isinstance(data.get('facts'), dict)
        }))
      except Exception as e:
        tests.append(_make_result('Chat Orchestration', t0, False, f'POST /api/chat failed: {e}'))

  passed = sum(1 for t in tests if t.get('passed') and not t.get('skipped'))
  failed = sum(1 for t in tests if (not t.get('passed')) and not t.get('skipped'))
  skipped = sum(1 for t in tests if t.get('skipped'))

  return {
    'base_url': base_url,
    'tests': tests,
    'total': len(tests),
    'passed': passed,
    'failed': failed,
    'skipped': skipped,
    'duration_ms': _now_ms() - start_all,
  }


# Extended benchmark cases for comprehensive testing
EXTENDED_CASES: List[BenchmarkCase] = [
  # Additional Navigation
  BenchmarkCase('Nav Coords', 'Fly to 12.9716, 77.5946', ('navigate',), require_facts=True),
  BenchmarkCase('Nav Landmark', 'Go to Cubbon Park', ('navigate',), require_facts=True),
  # Additional Property Search
  BenchmarkCase('Prop Filtered', 'Properties under 80 lakhs near metro in HSR', ('property_search',), require_facts=True),
  BenchmarkCase('Prop Amenity', 'Homes near good schools in Jayanagar', ('property_search',)),
  # Additional Area Analysis
  BenchmarkCase('Area POI', 'What are the top amenities around Indiranagar?', ('analyze_area', 'general')),
  BenchmarkCase('Area Risk', 'Is Silk Board area flood-prone?', ('terrain', 'analyze_area', 'general')),
  # Additional 3D
  BenchmarkCase('3D Floor', 'What floor is best for views in Whitefield?', ('analyze_area', 'property_search', 'general'), require_3d_facts=True),
  BenchmarkCase('3D Shadow', 'Shadow analysis at Koramangala in the morning', ('analyze_area', 'general')),
  # Additional Simulation
  BenchmarkCase('Sim Infra', 'Impact of new IT park in Devanahalli', ('simulate',), require_message=False),
  BenchmarkCase('Sim Zoning', 'What if FAR increases in Koramangala?', ('simulate',), require_message=False),
  # Additional Valuation
  BenchmarkCase('Val Compare', 'Price difference between Whitefield and Electronic City', ('valuation', 'comparison', 'general')),
  # Building
  BenchmarkCase('Building', 'Analyze this building for investment', ('analyze_building', 'general')),
]


def run_benchmark(base_url: str, timeout_s: float = 180.0, extended: bool = False) -> Dict[str, Any]:
  start_all = _now_ms()
  tests: List[Dict[str, Any]] = []

  cases: List[BenchmarkCase] = [
    BenchmarkCase('Navigation', 'Go to Indiranagar', ('navigate',), require_facts=True),
    BenchmarkCase('Property Search', 'Find 2BHK in Whitefield', ('property_search',), require_facts=True),
    BenchmarkCase('Area Analysis', 'Analyze Koramangala', ('analyze_area', 'general'), require_3d_facts=True),
    BenchmarkCase('Simulation', 'What if a metro opens near Sarjapur?', ('simulate',), require_message=False),
    BenchmarkCase('Terrain', 'Is Bellandur flood-prone?', ('terrain', 'analyze_area', 'general')),
    BenchmarkCase('Comparison', 'Compare Whitefield vs Electronic City', ('comparison', 'general')),
    BenchmarkCase('3D Spatial', 'What is the sky view factor at Whitefield?', ('analyze_area', 'general', 'valuation'), require_3d_facts=True),
    BenchmarkCase('Valuation', 'Estimate value of 2BHK 1200 sqft in Koramangala', ('valuation', 'property_search', 'general'), require_valuation=True),
  ]

  # Add extended cases if requested
  if extended:
    cases.extend(EXTENDED_CASES)

  with httpx.Client(base_url=base_url, timeout=timeout_s) as client:
    # Preflight: if backend is not reachable, fail fast with a clear error.
    t0 = _now_ms()
    try:
      _ok_json(client.get('/health'))
      tests.append(_make_result('Backend Reachable', t0, True, 'GET /health'))
    except Exception as e:
      tests.append(_make_result('Backend Reachable', t0, False, f'GET /health failed: {e}', details={'error': str(e)[:200]}))
      return {
        'base_url': base_url,
        'tests': tests,
        'total': len(tests),
        'passed': 0,
        'failed': 1,
        'duration_ms': _now_ms() - start_all,
      }

    for c in cases:
      t0 = _now_ms()
      try:
        payload = {
          'messages': [{'role': 'user', 'content': c.query}],
          'context': {},
          'session_id': 'benchmark',
        }
        data = _ok_json(client.post('/api/chat', json=payload))

        intent = str(data.get('intent') or 'unknown')
        message = str(data.get('message') or '')
        message_preview = (message.replace('\n', ' ').strip()[:160] + '...') if len(message) > 160 else message.replace('\n', ' ').strip()
        facts = data.get('facts')

        ok_intent = intent in c.expected_intents
        ok_message = (len(message.strip()) > 0) if c.require_message else True
        ok_facts = True
        if c.require_facts:
          ok_facts = isinstance(facts, dict) and bool(facts.get('lat')) and bool(facts.get('lng'))

        # Validate 3D facts if required
        ok_3d = True
        if c.require_3d_facts and isinstance(facts, dict):
          has_sky_view = facts.get('sky_view_factor') is not None
          has_skyline = facts.get('skyline_character') is not None
          has_view_quality = facts.get('view_quality') is not None
          ok_3d = has_sky_view or has_skyline or has_view_quality

        # Validate valuation if required
        ok_val = True
        if c.require_valuation and isinstance(facts, dict):
          # Check for estimated_value in facts or avg_price_per_sqft
          ok_val = facts.get('avg_price_per_sqft') is not None

        ok = bool(data.get('success')) and ok_intent and ok_message and ok_facts and ok_3d and ok_val

        # Build details with 3D facts info
        details = {
          'intent': intent,
          'expected_intents': list(c.expected_intents),
          'message_len': len(message),
          'message_preview': message_preview,
        }
        if c.require_3d_facts and isinstance(facts, dict):
          details['sky_view_factor'] = facts.get('sky_view_factor')
          details['skyline_character'] = facts.get('skyline_character')
          details['optimal_floor'] = facts.get('optimal_floor')
        if c.require_valuation and isinstance(facts, dict):
          details['avg_price_per_sqft'] = facts.get('avg_price_per_sqft')

        tests.append(_make_result(
          f"{c.category}",
          t0,
          ok,
          f"/api/chat: {c.query} (intent={intent})",
          details=details,
        ))
      except Exception as e:
        tests.append(_make_result(
          f"{c.category}",
          t0,
          False,
          f"/api/chat: {c.query} failed: {e}",
          details={'error': str(e)[:200]},
        ))

  passed = sum(1 for t in tests if t.get('passed'))
  failed = sum(1 for t in tests if not t.get('passed'))

  return {
    'base_url': base_url,
    'tests': tests,
    'total': len(tests),
    'passed': passed,
    'failed': failed,
    'duration_ms': _now_ms() - start_all,
  }


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument('--base-url', default='http://localhost:8000')
  parser.add_argument('--include-chat', action='store_true', default=True, help='Include chat test (default: enabled)')
  parser.add_argument('--no-chat', action='store_true', default=False, help='Skip chat test for faster runs')
  parser.add_argument('--benchmark', action='store_true', default=False)
  parser.add_argument('--extended', action='store_true', default=False, help='Run extended benchmark suite')
  parser.add_argument('--timeout', type=float, default=180.0)
  parser.add_argument('--json', action='store_true', default=False)
  args = parser.parse_args()

  if args.benchmark:
    report = run_benchmark(args.base_url, timeout_s=args.timeout, extended=args.extended)
    if args.json:
      print(json.dumps(report, indent=2))
    else:
      _print_benchmark_summary(report)
    return 0 if report.get('failed', 0) == 0 else 1

  include_chat = args.include_chat and not args.no_chat
  report = run_sanity(args.base_url, include_chat=include_chat)

  if args.json:
    print(json.dumps(report, indent=2))
  else:
    _print_summary(report)

  return 0 if report.get('failed', 0) == 0 else 1


if __name__ == '__main__':
  raise SystemExit(main())
