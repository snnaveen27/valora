import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class CheckResult:
  name: str
  passed: bool
  duration_ms: int
  description: str
  details: Optional[Dict[str, Any]] = None
  skipped: bool = False


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

  with httpx.Client(base_url=base_url, timeout=20.0) as client:
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

    t0 = _now_ms()
    if not include_chat:
      tests.append(_make_result('Chat Orchestration', t0, True, 'Skipped (include_chat=false)', skipped=True))
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


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument('--base-url', default='http://localhost:8000')
  parser.add_argument('--include-chat', action='store_true', default=False)
  parser.add_argument('--json', action='store_true', default=False)
  args = parser.parse_args()

  report = run_sanity(args.base_url, include_chat=args.include_chat)

  if args.json:
    print(json.dumps(report, indent=2))
  else:
    _print_summary(report)

  return 0 if report.get('failed', 0) == 0 else 1


if __name__ == '__main__':
  raise SystemExit(main())
