# Valora AI Test Suite Report

## Run Information
- **Run ID**: run_20260316_191333
- **Timestamp**: 2026-03-16T19:13:33.708380
- **Total Tests**: 105

## Summary
- **Passed**: 75
- **Failed**: 30
- **Errors**: 0
- **Skipped**: 0
- **Pass Rate**: 71.4%
- **Average Latency**: 0.0ms

## Tier Breakdown

### Tier 1 (Critical)
- **Total**: 74
- **Passed**: 46
- **Failed**: 28
- **Errors**: 0
- **Pass Rate**: 62.2%

### Tier 2 (Functional)
- **Total**: 13
- **Passed**: 13
- **Failed**: 0
- **Errors**: 0
- **Pass Rate**: 100.0%

### Tier 3 (Quality)
- **Total**: 18
- **Passed**: 16
- **Failed**: 2
- **Errors**: 0
- **Pass Rate**: 88.9%

## Test Categories

| Category | Status | Count |
|----------|--------|-------|
| api_endpoints | PASS | 4 |
| business_logic | PASS | 5 |
| database | PASS | 4 |
| intent_classification | FAIL | 50 |
| llm_health | PASS | 1 |
| model_routing | FAIL | 8 |
| regression | PASS | 4 |
| response_quality | PASS | 5 |
| self_learning | PASS | 4 |
| slot_extraction | FAIL | 10 |
| tool_execution | PASS | 5 |
| user_feedback | FAIL | 5 |

## Detailed Results

### LLM Health Check
- **ID**: llm_health_001
- **Tier**: 1
- **Category**: llm_health
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: LLM is healthy and responsive

### Intent: property_search
- **ID**: intent_000
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'property_search'

### Intent: property_search
- **ID**: intent_001
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'property_search'

### Intent: property_search
- **ID**: intent_002
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'property_search'

### Intent: property_search
- **ID**: intent_003
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'property_search'

### Intent: property_search
- **ID**: intent_004
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'property_search', got 'general_info'

### Intent: view_analysis
- **ID**: intent_005
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'view_analysis'

### Intent: view_analysis
- **ID**: intent_006
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'view_analysis'

### Intent: view_analysis
- **ID**: intent_007
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'view_analysis'

### Intent: view_analysis
- **ID**: intent_008
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'view_analysis', got 'general_info'

### Intent: view_analysis
- **ID**: intent_009
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'view_analysis'

### Intent: price_analysis
- **ID**: intent_010
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'price_analysis'

### Intent: price_analysis
- **ID**: intent_011
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'price_analysis'

### Intent: price_analysis
- **ID**: intent_012
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'price_analysis'

### Intent: price_analysis
- **ID**: intent_013
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'price_analysis'

### Intent: price_analysis
- **ID**: intent_014
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'price_analysis', got 'general_info'

### Intent: locality_intelligence
- **ID**: intent_015
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'locality_intelligence'

### Intent: locality_intelligence
- **ID**: intent_016
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'locality_intelligence', got 'comparison'

### Intent: locality_intelligence
- **ID**: intent_017
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'locality_intelligence'

### Intent: locality_intelligence
- **ID**: intent_018
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'locality_intelligence', got 'general_info'

### Intent: locality_intelligence
- **ID**: intent_019
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'locality_intelligence', got 'general_info'

### Intent: simulation
- **ID**: intent_020
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'simulation'

### Intent: simulation
- **ID**: intent_021
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'simulation', got 'view_analysis'

### Intent: simulation
- **ID**: intent_022
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'simulation', got 'general_info'

### Intent: simulation
- **ID**: intent_023
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'simulation', got 'price_analysis'

### Intent: simulation
- **ID**: intent_024
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'simulation'

### Intent: regulatory
- **ID**: intent_025
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'regulatory'

### Intent: regulatory
- **ID**: intent_026
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'regulatory', got 'locality_intelligence'

### Intent: regulatory
- **ID**: intent_027
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'regulatory', got 'general_info'

### Intent: regulatory
- **ID**: intent_028
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'regulatory', got 'view_analysis'

### Intent: regulatory
- **ID**: intent_029
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'regulatory', got 'general_info'

### Intent: comparison
- **ID**: intent_030
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'comparison'

### Intent: comparison
- **ID**: intent_031
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'comparison', got 'general_info'

### Intent: comparison
- **ID**: intent_032
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'comparison'

### Intent: comparison
- **ID**: intent_033
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'comparison'

### Intent: comparison
- **ID**: intent_034
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'comparison'

### Intent: general_info
- **ID**: intent_035
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'general_info'

### Intent: general_info
- **ID**: intent_036
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'general_info'

### Intent: general_info
- **ID**: intent_037
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'general_info'

### Intent: general_info
- **ID**: intent_038
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'general_info'

### Intent: general_info
- **ID**: intent_039
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'general_info'

### Intent: follow_up
- **ID**: intent_040
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'follow_up', got 'property_search'

### Intent: follow_up
- **ID**: intent_041
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'follow_up', got 'general_info'

### Intent: property_search
- **ID**: intent_042
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'property_search'

### Intent: property_search
- **ID**: intent_043
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'property_search', got 'general_info'

### Intent: clarification
- **ID**: intent_044
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'clarification', got 'price_analysis'

### Intent: property_search
- **ID**: intent_045
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.6ms
- **Message**: Correctly classified as 'property_search'

### Intent: property_search
- **ID**: intent_046
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'property_search'

### Intent: error_handling
- **ID**: intent_047
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'error_handling', got 'locality_intelligence'

### Intent: empty_query
- **ID**: intent_048
- **Tier**: 1
- **Category**: intent_classification
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly classified as 'empty_query'

### Intent: incomplete_query
- **ID**: intent_049
- **Tier**: 1
- **Category**: intent_classification
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected 'incomplete_query', got 'property_search'

### Slot: Find 3BHK apartment in Koraman...
- **ID**: slot_000
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 3/4 slots correct

### Slot: 2BHK villa in Whitefield with ...
- **ID**: slot_001
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Extracted 4/4 slots correctly

### Slot: PG near Manyata Tech Park...
- **ID**: slot_002
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 1/2 slots correct

### Slot: Commercial property in CBD...
- **ID**: slot_003
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 1/2 slots correct

### Slot: 1Cr budget in HSR Layout...
- **ID**: slot_004
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 0/2 slots correct

### Slot: Penthouse in Indiranagar...
- **ID**: slot_005
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Extracted 2/2 slots correctly

### Slot: Flat above 10th floor...
- **ID**: slot_006
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 0/2 slots correct

### Slot: Property near metro station...
- **ID**: slot_007
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Extracted 1/1 slots correctly

### Slot: Furnished apartment...
- **ID**: slot_008
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 0/1 slots correct

### Slot: Under construction property...
- **ID**: slot_009
- **Tier**: 1
- **Category**: slot_extraction
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Only 0/1 slots correct

### Tool: view_analysis
- **ID**: tool_000
- **Tier**: 1
- **Category**: tool_execution
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Tool 'view_analysis' executed successfully with all expected fields

### Tool: viewshed_analysis
- **ID**: tool_001
- **Tier**: 1
- **Category**: tool_execution
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Tool 'viewshed_analysis' executed successfully with all expected fields

### Tool: sun_path_analysis
- **ID**: tool_002
- **Tier**: 1
- **Category**: tool_execution
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Tool 'sun_path_analysis' executed successfully with all expected fields

### Tool: shadows_analysis
- **ID**: tool_003
- **Tier**: 1
- **Category**: tool_execution
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Tool 'shadows_analysis' executed successfully with all expected fields

### Tool: distance_calculator
- **ID**: tool_004
- **Tier**: 1
- **Category**: tool_execution
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Tool 'distance_calculator' executed successfully with all expected fields

### Route: What is 2BHK?...
- **ID**: route_000
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to ollama

### Route: Show apartments in Korama...
- **ID**: route_001
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to ollama

### Route: Compare prices...
- **ID**: route_002
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to ollama

### Route: Analyze the investment po...
- **ID**: route_003
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to openrouter

### Route: Simulate view obstruction...
- **ID**: route_004
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to openrouter

### Route: Analyze this property ima...
- **ID**: route_005
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to vision

### Route: Find properties with good...
- **ID**: route_006
- **Tier**: 1
- **Category**: model_routing
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly routed to openrouter

### Route: What is the FAR calculati...
- **ID**: route_007
- **Tier**: 1
- **Category**: model_routing
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected openrouter, got ollama

### API: POST /api/chat
- **ID**: api_000
- **Tier**: 2
- **Category**: api_endpoints
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Endpoint /api/chat responded with 200

### API: POST /api/chat/stream
- **ID**: api_001
- **Tier**: 2
- **Category**: api_endpoints
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Endpoint /api/chat/stream responded with 200

### API: GET /api/health
- **ID**: api_002
- **Tier**: 2
- **Category**: api_endpoints
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Endpoint /api/health responded with 200

### API: GET /api/credits/balance
- **ID**: api_003
- **Tier**: 2
- **Category**: api_endpoints
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Endpoint /api/credits/balance responded with 200

### Business: emi_calculation
- **ID**: biz_000
- **Tier**: 2
- **Category**: business_logic
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Business logic 'emi_calculation' calculated correctly

### Business: price_per_sqft
- **ID**: biz_001
- **Tier**: 2
- **Category**: business_logic
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Business logic 'price_per_sqft' calculated correctly

### Business: stamp_duty_calculation
- **ID**: biz_002
- **Tier**: 2
- **Category**: business_logic
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Business logic 'stamp_duty_calculation' calculated correctly

### Business: rental_yield
- **ID**: biz_003
- **Tier**: 2
- **Category**: business_logic
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Business logic 'rental_yield' calculated correctly

### Business: appreciation_calculation
- **ID**: biz_004
- **Tier**: 2
- **Category**: business_logic
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Business logic 'appreciation_calculation' calculated correctly

### DB: connection
- **ID**: db_000
- **Tier**: 2
- **Category**: database
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Database operation 'connection' executed successfully

### DB: property_query
- **ID**: db_001
- **Tier**: 2
- **Category**: database
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Database operation 'property_query' executed successfully

### DB: user_data
- **ID**: db_002
- **Tier**: 2
- **Category**: database
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Database operation 'user_data' executed successfully

### DB: conversation_history
- **ID**: db_003
- **Tier**: 2
- **Category**: database
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Database operation 'conversation_history' executed successfully

### Quality: has_facts
- **ID**: quality_000
- **Tier**: 3
- **Category**: response_quality
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Quality criterion 'has_facts' met

### Quality: has_citations
- **ID**: quality_001
- **Tier**: 3
- **Category**: response_quality
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Quality criterion 'has_citations' met

### Quality: no_hallucination
- **ID**: quality_002
- **Tier**: 3
- **Category**: response_quality
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Quality criterion 'no_hallucination' met

### Quality: appropriate_length
- **ID**: quality_003
- **Tier**: 3
- **Category**: response_quality
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Quality criterion 'appropriate_length' met

### Quality: relevant
- **ID**: quality_004
- **Tier**: 3
- **Category**: response_quality
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Quality criterion 'relevant' met

### Feedback: This was very helpfu...
- **ID**: feedback_000
- **Tier**: 3
- **Category**: user_feedback
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly analyzed feedback

### Feedback: The price estimate w...
- **ID**: feedback_001
- **Tier**: 3
- **Category**: user_feedback
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly analyzed feedback

### Feedback: Could be better...
- **ID**: feedback_002
- **Tier**: 3
- **Category**: user_feedback
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Correctly analyzed feedback

### Feedback: Love the view analys...
- **ID**: feedback_003
- **Tier**: 3
- **Category**: user_feedback
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected positive/feature_praise, got positive/satisfaction

### Feedback: Taking too long to r...
- **ID**: feedback_004
- **Tier**: 3
- **Category**: user_feedback
- **Status**: fail
- **Latency**: 0.0ms
- **Message**: Expected negative/performance, got neutral/improvement

### Regression: view_analysis_format
- **ID**: regression_000
- **Tier**: 3
- **Category**: regression
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Regression test 'view_analysis_format' passed - no regression detected

### Regression: intent_classification_accuracy
- **ID**: regression_001
- **Tier**: 3
- **Category**: regression
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Regression test 'intent_classification_accuracy' passed - no regression detected

### Regression: response_time
- **ID**: regression_002
- **Tier**: 3
- **Category**: regression
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Regression test 'response_time' passed - no regression detected

### Regression: api_availability
- **ID**: regression_003
- **Tier**: 3
- **Category**: regression
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Regression test 'api_availability' passed - no regression detected

### Learning: pattern_accuracy
- **ID**: learn_000
- **Tier**: 3
- **Category**: self_learning
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Self-learning metric 'pattern_accuracy' is improving

### Learning: feedback_integration
- **ID**: learn_001
- **Tier**: 3
- **Category**: self_learning
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Self-learning metric 'feedback_integration' is improving

### Learning: adaptation_speed
- **ID**: learn_002
- **Tier**: 3
- **Category**: self_learning
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Self-learning metric 'adaptation_speed' is improving

### Learning: error_reduction
- **ID**: learn_003
- **Tier**: 3
- **Category**: self_learning
- **Status**: pass
- **Latency**: 0.0ms
- **Message**: Self-learning metric 'error_reduction' is improving

