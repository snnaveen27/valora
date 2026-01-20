"""Quick test for GIS Multi-Agent System."""

from gis_agents import IntentRouter, Intent, AgentFacts

def test_intent_router():
    """Test intent classification."""
    tests = [
        ("Show me Whitefield", Intent.NAVIGATE),
        ("Go to Koramangala", Intent.NAVIGATE),
        ("What is this area like?", Intent.ANALYZE_AREA),
        ("Find apartments under 1 crore", Intent.PROPERTY_SEARCH),
        ("What is the price of this building?", Intent.VALUATION),
        ("Is this area flood-prone?", Intent.TERRAIN),
        ("Compare Whitefield and Indiranagar", Intent.COMPARISON),
        ("Hello", Intent.GENERAL),
        ("Navigate to Hebbal", Intent.NAVIGATE),
        ("Analyze amenities here", Intent.ANALYZE_AREA),
        ("3 BHK flats for rent", Intent.PROPERTY_SEARCH),
    ]
    
    print("Intent Router Tests:")
    passed = 0
    for query, expected in tests:
        result = IntentRouter.classify(query)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        print(f"  [{status}] '{query}' -> {result.value} (expected: {expected.value})")
    
    print(f"\nPassed: {passed}/{len(tests)}")
    assert passed == len(tests), f"Intent router failed {len(tests) - passed} tests"


def test_place_extraction():
    """Test place name extraction from navigation queries."""
    tests = [
        ("Show me Whitefield", "Whitefield"),
        ("Go to Koramangala", "Koramangala"),
        ("Take me to Indiranagar", "Indiranagar"),
        ("Navigate to Hebbal", "Hebbal"),
    ]
    
    print("\nPlace Extraction Tests:")
    passed = 0
    for query, expected in tests:
        result = IntentRouter.extract_place_name(query)
        status = "PASS" if result and expected.lower() in result.lower() else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"  [{status}] '{query}' -> '{result}' (expected: '{expected}')")
    
    print(f"\nPassed: {passed}/{len(tests)}")
    assert passed == len(tests), f"Place extraction failed {len(tests) - passed} tests"


def test_facts_context_string():
    """Test AgentFacts to context string conversion."""
    facts = AgentFacts(
        location_name="Whitefield",
        lat=12.9698,
        lng=77.7500,
        poi_count=45,
        transport_count=8,
        accessibility_score=72,
        walkability_score=65,
        avg_price_per_sqft=8500.0,
        active_listings=150,
        demand_level="High",
    )
    
    context = facts.to_context_string()
    print("\nFacts Context String:")
    print(context)
    
    # Check key elements are present
    checks = [
        "Whitefield" in context,
        "45" in context,  # POI count
        "72/100" in context,  # Accessibility
        "8,500" in context,  # Price
        "High" in context,  # Demand
    ]
    
    assert all(checks), "Facts context string missing expected elements"


def test_facts_dashboard():
    """Test AgentFacts to dashboard conversion."""
    facts = AgentFacts(
        location_name="Koramangala",
        poi_count=60,
        transport_count=12,
        accessibility_score=85,
        walkability_score=78,
        avg_price_per_sqft=12000.0,
        price_trend_pct=8.5,
        active_listings=200,
        demand_level="High",
    )
    
    dashboard = facts.to_dashboard(title="Koramangala Analysis")
    print("\nDashboard Output:")
    print(f"  Title: {dashboard.get('title')}")
    print(f"  Cards: {len(dashboard.get('cards', []))}")
    
    market = dashboard.get("market", {})
    print(f"  Market avgPricePerSqft: {market.get('avgPricePerSqft')}")
    print(f"  Market growth1y: {market.get('growth1y')}")
    print(f"  Market demandIndex: {market.get('demandIndex')}")
    
    assert dashboard.get("title") == "Koramangala Analysis", "Dashboard title mismatch"
    assert market.get("demandIndex") == "High", "Dashboard demand index mismatch"


if __name__ == "__main__":
    print("=" * 60)
    print("GIS Multi-Agent System Tests")
    print("=" * 60)
    
    results = []
    results.append(("Intent Router", test_intent_router()))
    results.append(("Place Extraction", test_place_extraction()))
    results.append(("Facts Context", test_facts_context_string()))
    results.append(("Facts Dashboard", test_facts_dashboard()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
