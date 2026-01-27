"""Test intent classification for improved agent responses."""
from gis_agents import IntentRouter, Intent

tests = [
    ('hi', 'greeting'),
    ('hello', 'greeting'),
    ('help', 'help'),
    ('what can you do', 'help'),
    ('thanks', 'thanks'),
    ('bye', 'farewell'),
    ('find apartments in koramangala', 'property_search'),
    ('is hebbal good for investment', 'investment'),
    ('analyze whitefield', 'analyze_area'),
    ('compare koramangala vs indiranagar', 'comparison'),
    ('market trends', 'market_trend'),
    ('show me properties under 1 cr', 'property_search'),
    ('what if metro comes to sarjapur', 'simulate'),
    ('tell me about this area', 'analyze_area'),
    ('good morning', 'greeting'),
    ('where should i buy for families', 'recommendation'),
]

passed = 0
failed = 0

print("=" * 60)
print("INTENT CLASSIFICATION TEST")
print("=" * 60)

for q, expected in tests:
    result = IntentRouter.classify(q).value
    status = '✓' if result == expected else '✗'
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f'{status} "{q}" → {result} (expected: {expected})')

print("=" * 60)
print(f'Passed: {passed}/{len(tests)} | Failed: {failed}')
print("=" * 60)
