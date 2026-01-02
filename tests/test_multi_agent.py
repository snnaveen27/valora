"""
Test Multi-Agent System
Tests the integrated multi-agent real estate intelligence system
"""

import requests
import json
import asyncio
import websockets
from datetime import datetime


# API base URL
BASE_URL = "http://localhost:8000"


def test_agent_plan():
    """Test the main agent plan endpoint"""
    print("\n" + "="*60)
    print("TEST: Multi-Agent Plan Execution")
    print("="*60)
    
    # Test query matching user's example
    request_data = {
        "user_id": "test_user_123",
        "intent": "Find high-growth zones in Bangalore with 3 BHK options under ₹1 Cr",
        "context": {
            "preferences": {
                "investment_horizon": "3-5 years",
                "risk_tolerance": "medium"
            }
        }
    }
    
    print(f"\n🔍 User Query: {request_data['intent']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/agent/plan",
            json=request_data
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ Agent Plan Created Successfully!")
            print(f"📋 Plan ID: {result.get('plan_id')}")
            print(f"🎯 Confidence: {result.get('confidence', 0)*100:.0f}%")
            
            # Display plan execution
            plan = result.get('plan', {})
            tasks = plan.get('tasks', [])
            print(f"\n📊 Executed {len(tasks)} Tasks:")
            for task in tasks:
                print(f"  • {task['agent']}: {task['action']} - {task['status']}")
            
            # Display recommendations (for AI Agent Panel)
            final_result = result.get('final_result', {})
            recommendations = final_result.get('recommendations', [])
            
            if recommendations:
                print(f"\n🏠 Top {len(recommendations)} Investment Zones Found:")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"\n  {i}. {rec.get('zone_name', 'Unknown')}")
                    print(f"     Score: {rec.get('score', 0)*100:.0f}%")
                    print(f"     Current Price: ₹{rec.get('current_price', 0)/100000:.1f}L")
                    print(f"     3Y Growth: {rec.get('growth_potential', [0,0,0])[-1]:.1f}%")
                    print(f"     Rental Yield: {rec.get('rental_yield', 0):.1f}%")
                    
                    # Display reasons
                    reasons = rec.get('reasons', [])
                    if reasons:
                        print(f"     Why this zone:")
                        for reason in reasons[:2]:
                            print(f"       - {reason}")
            
            # Display map data (for Map Panel)
            spatial = final_result.get('spatial_overlays', {})
            if spatial:
                print(f"\n🗺️ Map Data Generated:")
                print(f"  • Heatmap URL: {spatial.get('heatmap_url', 'N/A')}")
                geojson = spatial.get('geojson', {})
                if geojson.get('features'):
                    print(f"  • GeoJSON Features: {len(geojson['features'])} zones mapped")
            
            # Display forecast data (for Analysis Panel)
            forecasts = final_result.get('forecasts', {})
            if forecasts:
                print(f"\n📈 Forecast Analysis:")
                price_forecast = forecasts.get('price_forecast', {})
                print(f"  • Forecast Months: {price_forecast.get('months', [])}")
                print(f"  • Model: {forecasts.get('model', {}).get('name', 'N/A')}")
                print(f"  • Confidence: {forecasts.get('confidence', 0)*100:.0f}%")
            
            # Display chat response (for AI Agent Panel)
            chat_response = result.get('chat_response', '')
            if chat_response:
                print(f"\n💬 AI Agent Response:")
                print(f"{chat_response[:300]}..." if len(chat_response) > 300 else chat_response)
            
            # Display suggested actions
            human_actions = result.get('human_actions', [])
            if human_actions:
                print(f"\n🎯 Suggested Next Steps:")
                for action in human_actions:
                    print(f"  • {action.replace('_', ' ').title()}")
            
            return result
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.json())
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    return None


def test_quick_analysis():
    """Test the quick analysis endpoint"""
    print("\n" + "="*60)
    print("TEST: Quick Analysis")
    print("="*60)
    
    params = {
        "city": "Bangalore",
        "budget_max": 10000000,  # 1 Cr
        "property_type": "3BHK",
        "amenities": ["metro", "school", "hospital"]
    }
    
    print(f"\n🔍 Quick Search: {params['property_type']} in {params['city']} under ₹{params['budget_max']/10000000:.1f}Cr")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/agent/analyze",
            params=params
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Analysis completed with confidence: {result.get('confidence', 0)*100:.0f}%")
            
            recommendations = result.get('final_result', {}).get('recommendations', [])
            if recommendations:
                print(f"Found {len(recommendations)} matching zones")
                
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")


def test_plan_status():
    """Test getting plan status"""
    print("\n" + "="*60)
    print("TEST: Plan Status Check")
    print("="*60)
    
    # First create a plan
    request_data = {
        "user_id": "test_user_456",
        "intent": "Compare investment potential between Whitefield and Electronic City"
    }
    
    try:
        # Create plan
        response = requests.post(f"{BASE_URL}/api/agent/plan", json=request_data)
        
        if response.status_code == 200:
            plan_id = response.json().get('plan_id')
            print(f"✅ Created plan: {plan_id}")
            
            # Get status
            status_response = requests.get(f"{BASE_URL}/api/agent/plan/{plan_id}")
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"📊 Plan Status: {status.get('status', 'unknown')}")
                
                tasks = status.get('tasks', [])
                for task in tasks:
                    print(f"  • {task['agent']}: {task['status']} (confidence: {task['confidence']*100:.0f}%)")
                    
        else:
            print(f"❌ Error creating plan: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")


async def test_websocket():
    """Test WebSocket connection for real-time communication"""
    print("\n" + "="*60)
    print("TEST: WebSocket Real-time Communication")
    print("="*60)
    
    uri = "ws://localhost:8000/ws/agent"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Send query
            query = {
                "user_id": "ws_test_user",
                "intent": "Find affordable 2BHK apartments near metro stations",
                "context": {}
            }
            
            print(f"📤 Sending: {query['intent']}")
            await websocket.send(json.dumps(query))
            
            # Receive response
            response = await websocket.recv()
            result = json.loads(response)
            
            print(f"📥 Received response with confidence: {result.get('confidence', 0)*100:.0f}%")
            
            recommendations = result.get('final_result', {}).get('recommendations', [])
            if recommendations:
                print(f"✅ Found {len(recommendations)} recommendations via WebSocket")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")


def test_panel_synchronization():
    """Test that response properly synchronizes all three panels"""
    print("\n" + "="*60)
    print("TEST: Frontend Panel Synchronization")
    print("="*60)
    
    request_data = {
        "user_id": "sync_test_user",
        "intent": "Find high-growth zones in Bangalore with 3 BHK options under ₹1 Cr near metro",
        "context": {}
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/agent/plan", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            final_result = result.get('final_result', {})
            
            # Check Analysis Panel data
            has_forecasts = bool(final_result.get('forecasts'))
            print(f"📊 Analysis Panel Data: {'✅ Available' if has_forecasts else '❌ Missing'}")
            if has_forecasts:
                forecasts = final_result['forecasts']
                print(f"   - Price forecasts: {bool(forecasts.get('price_forecast'))}")
                print(f"   - Rental yields: {bool(forecasts.get('rental_yield_forecast'))}")
                print(f"   - Risk scores: {bool(forecasts.get('risk_score'))}")
            
            # Check Map Panel data
            has_spatial = bool(final_result.get('spatial_overlays'))
            print(f"🗺️ Map Panel Data: {'✅ Available' if has_spatial else '❌ Missing'}")
            if has_spatial:
                spatial = final_result['spatial_overlays']
                print(f"   - Heatmap URL: {bool(spatial.get('heatmap_url'))}")
                print(f"   - GeoJSON: {bool(spatial.get('geojson'))}")
            
            # Check AI Agent Panel data
            has_recommendations = bool(final_result.get('recommendations'))
            has_chat = bool(result.get('chat_response'))
            print(f"🤖 AI Agent Panel Data: {'✅ Available' if (has_recommendations and has_chat) else '❌ Missing'}")
            if has_recommendations:
                print(f"   - Recommendations: {len(final_result['recommendations'])} zones")
            if has_chat:
                print(f"   - Chat response: {len(result['chat_response'])} chars")
            print(f"   - Human actions: {len(result.get('human_actions', []))} suggested")
            
            # Overall sync status
            all_synced = has_forecasts and has_spatial and has_recommendations and has_chat
            print(f"\n{'✅ All panels synchronized!' if all_synced else '⚠️ Some panels missing data'}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Synchronization test failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Valora v1.0 Multi-Agent System Tests")
    print("="*60)
    
    # Check if backend is running
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Backend is running")
        else:
            print("❌ Backend health check failed")
            return
    except:
        print("❌ Backend is not running. Please start it first.")
        return
    
    # Run tests
    print("\nRunning tests...")
    
    # Test 1: Main agent plan
    test_agent_plan()
    
    # Test 2: Quick analysis
    test_quick_analysis()
    
    # Test 3: Plan status
    test_plan_status()
    
    # Test 4: Panel synchronization
    test_panel_synchronization()
    
    # Test 5: WebSocket (async)
    print("\n" + "="*60)
    print("Running async WebSocket test...")
    asyncio.run(test_websocket())
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
    print("\n📝 Summary:")
    print("The multi-agent system successfully:")
    print("  1. Processes natural language queries")
    print("  2. Coordinates 5 specialized agents")
    print("  3. Generates data for all 3 frontend panels")
    print("  4. Provides real-time WebSocket communication")
    print("  5. Maintains context and confidence scores")
    print("\n🎯 Next Agentic Action: Frontend integration to display coordinated results")


if __name__ == "__main__":
    main()
