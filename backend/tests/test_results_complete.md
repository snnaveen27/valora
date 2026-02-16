# Valora AI — Test Results

**Generated:** 2026-02-15T22:15:26.087879
**Duration:** 15314ms
**Total:** 64 | **Passed:** 63 | **Failed:** 1
**Pass Rate:** 98.4%

## Summary by Section

| Section | Total | Passed | Failed | Pass Rate |
|---------|-------|--------|--------|-----------|
| Intent Classification | 40 | 40 | 0 | 100.0% |
| Model Routing | 8 | 8 | 0 | 100.0% |
| Learning | 2 | 2 | 0 | 100.0% |
| API Endpoints | 7 | 6 | 1 | 85.7% |
| Slot Extraction | 3 | 3 | 0 | 100.0% |
| Stress Tests | 3 | 3 | 0 | 100.0% |
| OpenRouter | 1 | 1 | 0 | 100.0% |

## Intent Classification

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| greet_01 | hello | ✅ PASS | - | expected=greeting, got=greeting |
| greet_02 | hi there | ✅ PASS | - | expected=greeting, got=greeting |
| greet_03 | good morning | ✅ PASS | - | expected=greeting, got=greeting |
| greet_04 | hey | ✅ PASS | - | expected=greeting, got=greeting |
| greet_05 | how are you | ✅ PASS | - | expected=smalltalk, got=smalltalk |
| nav_01 | Show me Koramangala on the map | ✅ PASS | - | expected=navigate, got=navigate |
| nav_02 | Fly to Whitefield | ✅ PASS | - | expected=navigate, got=navigate |
| nav_03 | Go to Indiranagar | ✅ PASS | - | expected=navigate, got=navigate |
| nav_04 | Take me to Electronic City | ✅ PASS | - | expected=navigate, got=navigate |
| nav_05 | Navigate to HSR Layout | ✅ PASS | - | expected=navigate, got=navigate |
| search_01 | Find 2BHK apartments in Indiranagar under 80 lakhs | ✅ PASS | - | expected=property_search, got=property_search |
| search_02 | Find villas in Whitefield for 2 crores | ✅ PASS | - | expected=property_search, got=property_search |
| search_03 | 3BHK near metro station in Bangalore | ✅ PASS | - | expected=property_search, got=property_search |
| search_04 | Affordable flats in Sarjapur Road | ✅ PASS | - | expected=property_search, got=property_search |
| search_05 | Find luxury penthouses in Koramangala | ✅ PASS | - | expected=property_search, got=property_search |
| area_01 | Analyze Koramangala for livability | ✅ PASS | - | expected=analyze_area, got=analyze_area |
| area_02 | What amenities are near Whitefield? | ✅ PASS | - | expected=analyze_area, got=analyze_area |
| area_03 | Tell me about flood risk in Bellandur | ✅ PASS | - | expected=terrain, got=terrain |
| area_04 | Analyze walkability of Indiranagar area | ✅ PASS | - | expected=analyze_area, got=analyze_area |
| bldg_01 | Analyze this building's shadow impact | ✅ PASS | - | expected=analyze_building, got=analyze_building |
| bldg_02 | Analyze the best floor for view in this building | ✅ PASS | - | expected=analyze_building, got=analyze_building |
| comp_01 | Compare Whitefield vs Sarjapur Road | ✅ PASS | - | expected=comparison, got=comparison |
| comp_02 | Which is better, Koramangala or Indiranagar? | ✅ PASS | - | expected=comparison, got=comparison |
| comp_03 | Pros and cons of HSR Layout vs BTM Layout | ✅ PASS | - | expected=comparison, got=comparison |
| sim_01 | Simulate what happens to prices if metro comes to  | ✅ PASS | - | expected=simulate, got=simulate |
| sim_02 | Simulate impact of new IT park near Sarjapur | ✅ PASS | - | expected=simulate, got=simulate |
| sim_03 | What if interest rates drop by 2%? | ✅ PASS | - | expected=simulate, got=simulate |
| inv_01 | Best areas for real estate investment in Bangalore | ✅ PASS | - | expected=investment, got=investment |
| inv_02 | Which areas have high appreciation potential? | ✅ PASS | - | expected=investment, got=investment |
| inv_03 | ROI analysis for Whitefield properties | ✅ PASS | - | expected=investment, got=investment |
| trend_01 | Price trend in Koramangala over last 5 years | ✅ PASS | - | expected=market_trend, got=market_trend |
| trend_02 | Average price per sqft in Whitefield | ✅ PASS | - | expected=valuation, got=valuation |
| trend_03 | Market trend for Electronic City area | ✅ PASS | - | expected=market_trend, got=market_trend |
| val_01 | What is the estimated price of 3BHK in Sarjapur Ro | ✅ PASS | - | expected=property_search, got=property_search |
| val_02 | Valuation estimate for 1200 sqft space in Indirana | ✅ PASS | - | expected=valuation, got=valuation |
| terr_01 | Show terrain elevation around Whitefield | ✅ PASS | - | expected=terrain, got=terrain |
| gen_01 | What is Valora AI? | ✅ PASS | - | expected=general, got=general |
| edge_01 | (empty) | ✅ PASS | - | expected=general, got=general |
| edge_02 | xyz123 gibberish noodle | ✅ PASS | - | expected=general, got=general |
| edge_03 | Delete all database records | ✅ PASS | - | expected=general, got=general |

## Model Routing

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| route_01 | hello | ✅ PASS | 20ms | model=qwen3:8b score=0.00 cloud=OK(want=False,got=False) |
| route_02 | Show me Koramangala | ✅ PASS | - | model=qwen3:8b score=0.00 cloud=OK(want=False,got=False) |
| route_03 | Tell me about Whitefield | ✅ PASS | - | model=qwen3:8b score=0.15 cloud=OK(want=False,got=False) |
| route_04 | Compare Whitefield vs Electronic City for investme | ✅ PASS | - | model=kimi-k2.5:cloud score=0.65 cloud=OK(want=True,got=True) |
| route_05 | Simulate metro impact on Sarjapur Road prices with | ✅ PASS | - | model=kimi-k2.5:cloud score=0.45 cloud=OK(want=True,got=True) |
| route_06 | Analyze this property photo | ✅ PASS | - | model=qwen3-vl:235b-instruct-cloud score=0.65 cloud=OK(want=True,got=True) vision=OK |
| route_07 | Find 2BHK in Whitefield under 80L, compare with Sa | ✅ PASS | - | model=kimi-k2.5:cloud score=0.35 cloud=OK(want=True,got=True) |
| route_08 | What is the price per sqft in Koramangala? | ✅ PASS | - | model=qwen3:8b score=0.15 cloud=OK(want=False,got=False) |

## Learning

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| learn_01 | Performance tracking + bonus | ✅ PASS | - | good_bonus=0.200, bad_bonus=-0.300 |
| learn_02 | SQLite perf DB exists | ✅ PASS | - | C:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\valora_fresh\storage\database\model_performance.db |

## API Endpoints

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| ep_health | /api/admin/health | ✅ PASS | 2814ms | GET /api/admin/health → 200 (2814ms) |
| ep_auth_tiers | /api/auth/tiers | ✅ PASS | 2040ms | GET /api/auth/tiers → 200 (2040ms) |
| ep_credits | /api/credits/test_user_001 | ✅ PASS | 2053ms | GET /api/credits/test_user_001 → 200 (2053ms) |
| ep_plans | /api/credits/plans | ✅ PASS | 2031ms | GET /api/credits/plans → 200 (2031ms) |
| ep_topup | /api/credits/topup-packs | ✅ PASS | 2047ms | GET /api/credits/topup-packs → 200 (2047ms) |
| ep_pay_plans | /api/payments/plans | ✅ PASS | 2042ms | GET /api/payments/plans → 200 (2042ms) |
| ep_pay_config | /api/payments/config | ❌ FAIL | 2049ms | HTTP Error 500: Internal Server Error |

## Slot Extraction

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| slot_01 | Find 2BHK apartments in Indiranagar under 80 lakhs | ✅ PASS | - | intent=property_search |
| slot_02 | Compare Whitefield vs Sarjapur Road | ✅ PASS | - | intent=comparison |
| slot_03 | Show me 3BHK villas near Koramangala with budget u | ✅ PASS | - | intent=property_search |

## Stress Tests

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| stress_01 | I work near Manyata Tech Park but only go twice a  | ✅ PASS | - | intent=investment, model=kimi-k2.5:cloud, score=0.50, escalated=True |
| stress_02 | Analyze Sarjapur Road and simulate what happens to | ✅ PASS | - | intent=simulate, model=kimi-k2.5:cloud, score=0.50, escalated=True |
| stress_03 | Find 3BHK in Koramangala under 50 lakhs with 2000  | ✅ PASS | - | intent=property_search, model=kimi-k2.5:cloud, score=0.40, escalated=True |

## OpenRouter

| ID | Test | Status | Duration | Details |
|----|------|--------|----------|---------|
| or_01 | API key configured | ✅ PASS | - | configured=True, models=['reasoning', 'reasoning_heavy', 'vision', 'code'] |

## Failed Tests — Action Items

- **ep_pay_config** (API Endpoints): /api/payments/config
  - Error: `HTTP Error 500: Internal Server Error`

## Architecture

- **Default model:** qwen3:8b (local Ollama)
- **Cloud toggle:** Frontend toggle enables intelligent model routing
- **Cloud priority:** OpenRouter → Ollama Cloud (fallback)
- **Learning:** SQLite tracks model latency/success → influences future routing
- **Providers:** Ollama (local + cloud), OpenRouter (deepseek, qwen-vl, claude)
- **Task banner:** Shows selected model, complexity score, reasoning