"""
Valora Multi-Agent Orchestrator - Coordinates all agents and provides unified interface
"""

import json
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.services.multi_agent_system import (
    PlannerAgent, CriticAgent, Plan, Task, TaskStatus, AgentType
)
from backend.services.agent_implementations import (
    ForecastAgent, MapAgent, RecommenderAgent
)
from backend.services.external_apis import external_api_service
from backend.services.map_command_processor import MapCommandProcessor

# Import specialized agents
try:
    from backend.services.agents import (
        AVMAgent, GraphAgent, RasterAgent,
        MarketRiskAgent, LiquidityRiskAgent, RegulatoryRiskAgent,
        SHAPAgent, PDPAgent, CounterfactualAgent,
        ProphetAgent, EnsembleForecaster
    )
    SPECIALIZED_AGENTS_AVAILABLE = True
except ImportError as e:
    SPECIALIZED_AGENTS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Specialized agents not available: {e}")

# Import city intelligence services
try:
    from backend.services.city_intel import (
        LocalityStateService, GrowthPhaseClassifier,
        RiskIndexCalculator, ScenarioSimulator, NarrativeGenerator
    )
    CITY_INTEL_AVAILABLE = True
except ImportError:
    CITY_INTEL_AVAILABLE = False

# Import geospatial agent for polygon/polyline drawing
try:
    from backend.services.geospatial_agent import GeospatialAgent
    from backend.services.advanced_prediction_engine import AdvancedPredictionEngine
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    
# Import database for geospatial
try:
    from backend.database.multiconnection import mdb
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)


class ValoraOrchestrator:
    """
    Valora - Main orchestrator that coordinates all agents and provides unified interface
    Now with full geospatial awareness and polygon/polyline drawing capabilities
    """
    
    def __init__(self, dmpe_service=None, mappls_service=None, db_service=None):
        """Initialize orchestrator with all agents including geospatial"""
        # Core agents
        self.planner = PlannerAgent()
        self.forecaster = ForecastAgent(dmpe_service, db_service)
        self.map_agent = MapAgent(mappls_service)
        self.recommender = RecommenderAgent()
        self.critic = CriticAgent()
        self.map_processor = MapCommandProcessor()
        
        # Initialize specialized agents if available
        self.avm_agent = None
        self.graph_agent = None
        self.raster_agent = None
        self.risk_agents = {}
        self.explainability_agents = {}
        self.forecasting_agents = {}
        
        if SPECIALIZED_AGENTS_AVAILABLE:
            try:
                self.avm_agent = AVMAgent()
                self.graph_agent = GraphAgent()
                self.raster_agent = RasterAgent()
                self.risk_agents = {
                    'market': MarketRiskAgent(),
                    'liquidity': LiquidityRiskAgent(),
                    'regulatory': RegulatoryRiskAgent()
                }
                self.explainability_agents = {
                    'shap': SHAPAgent(),
                    'pdp': PDPAgent(),
                    'counterfactual': CounterfactualAgent()
                }
                self.forecasting_agents = {
                    'prophet': ProphetAgent(),
                    'ensemble': EnsembleForecaster()
                }
                logger.info("Specialized agents initialized: AVM, Graph, Raster, Risk, Explainability")
            except Exception as e:
                logger.warning(f"Could not initialize specialized agents: {e}")
        
        # Initialize city intelligence services if available
        self.city_intel = {}
        if CITY_INTEL_AVAILABLE:
            try:
                self.city_intel = {
                    'locality_state': LocalityStateService(),
                    'growth_phase': GrowthPhaseClassifier(),
                    'risk_index': RiskIndexCalculator(),
                    'scenario': ScenarioSimulator(),
                    'narrative': NarrativeGenerator()
                }
                logger.info("City Intelligence services initialized")
            except Exception as e:
                logger.warning(f"Could not initialize city intelligence: {e}")
        
        # Initialize geospatial agent if available
        self.geospatial_agent = None
        self.prediction_engine = None
        if GEOSPATIAL_AVAILABLE and DB_AVAILABLE:
            try:
                self.geospatial_agent = GeospatialAgent(mdb.engine_spatial)
                self.prediction_engine = AdvancedPredictionEngine()
                logger.info("GeospatialAgent and AdvancedPredictionEngine initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize advanced agents: {e}")
        
        self.active_plans = {}
        self.execution_history = []
    
    async def process_request(self, user_id: str, intent: str, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for processing user requests
        """
        if context is None:
            context = {}
        
        try:
            # Check for geospatial/drawing commands first
            if self.geospatial_agent and any(word in intent.lower() for word in [
                "draw", "polygon", "polyline", "buffer", "zone", "catchment", 
                "boundary", "circle", "around", "compare zones", "optimal zone"
            ]):
                return await self._handle_geospatial_command(user_id, intent, context)
            
            # Handle simple greetings without running the full pipeline
            if self._is_greeting(intent):
                return self._build_greeting_response(intent)
            
            # Step 0: Parse map intent if present
            map_intent = self.map_processor.parse_intent(intent)
            logger.info(f"🔍 Parsed map intent: {map_intent}")
            
            map_action = None
            if map_intent and map_intent.get("command"):
                map_action = self.map_processor.generate_map_action(map_intent)
                context["map_intent"] = map_intent
                context["map_action"] = map_action
                logger.info(f"✅ Detected map command: {map_intent['command']} with confidence {map_intent.get('confidence', 0)}")
                logger.info(f"🗺️ Generated map action: {map_action}")
                
                # For pure map commands (high confidence, no property search), return immediately
                if map_intent.get("confidence", 0) > 0.7 and map_intent["command"] in ["navigate", "draw_buffer", "draw_polygon", "add_marker", "draw_circle", "draw_rectangle", "draw_property", "draw_catchment", "draw_investment", "compare"]:
                    logger.info(f"⚡ Short-circuiting for pure map command: {map_intent['command']}")
                    return {
                        "plan_id": str(uuid.uuid4()),
                        "plan": {"user_intent": intent, "tasks": []},
                        "final_result": {"map_action": map_action},
                        "map_action": map_action,
                        "provenance": [],
                        "confidence": map_intent.get("confidence", 0.9),
                        "human_actions": ["view_map", "refine_search"],
                        "validation": {"status": "pass", "errors": [], "warnings": [], "confidence": 1.0, "validation_timestamp": datetime.now().isoformat()},
                        "timestamp": datetime.now().isoformat(),
                        "chat_response": self._generate_map_command_response(map_action)
                    }
            else:
                logger.info(f"❌ No map command detected in: {intent}")
            
            # Step 1: Create plan
            plan = await self.planner.create_plan(intent, context)
            self.active_plans[plan.id] = plan
            
            # Step 2: Execute tasks
            final_result = await self._execute_plan(plan)
            
            # Add map action to final result if present
            if map_action:
                final_result["map_action"] = map_action
            
            # Direct LLM fallback for general prompts (no domain results)
            if not final_result.get("recommendations") and not map_action:
                try:
                    # Use LLM for friendly general conversation
                    reply = await external_api_service.simple_chat(
                        intent,
                        system="You are Valora, a friendly AI assistant specializing in real estate, but also happy to have general conversations. Be warm, helpful, and conversational."
                    )
                except Exception as e:
                    logger.warning(f"LLM fallback failed: {e}, using default response")
                    # Friendly default responses based on intent
                    intent_lower = intent.lower()
                    if any(word in intent_lower for word in ["how are you", "what's up", "how's it going"]):
                        reply = "I'm doing great, thank you for asking! I'm here to help you with real estate queries in Bangalore. Is there anything specific you'd like to know about properties, investments, or neighborhoods?"
                    elif any(word in intent_lower for word in ["thank", "thanks"]):
                        reply = "You're welcome! Feel free to ask me anything about real estate or just chat. I'm here to help! 😊"
                    elif any(word in intent_lower for word in ["joke", "funny", "laugh"]):
                        reply = "Why don't real estate agents ever get lost? Because they always know the best route to close a deal! 😄 But seriously, how can I help you with properties today?"
                    elif any(word in intent_lower for word in ["who are you", "what are you", "tell me about yourself"]):
                        reply = "I'm Valora, your AI-powered real estate assistant for Bangalore! I can help you find properties, analyze investment opportunities, compare neighborhoods, and navigate the map. I also enjoy a good chat! What would you like to explore?"
                    else:
                        reply = "I'm here and ready to help! While I specialize in Bangalore real estate, I'm happy to chat about anything. What's on your mind?"
                
                return {
                    "plan_id": plan.id,
                    "plan": {"user_intent": intent, "tasks": []},
                    "final_result": {},
                    "map_action": None,
                    "provenance": [],
                    "confidence": 0.0,
                    "human_actions": ["try_sample_queries", "ask_for_help"],
                    "validation": {"status": "pass", "errors": [], "warnings": [], "confidence": 1.0, "validation_timestamp": datetime.now().isoformat()},
                    "timestamp": datetime.now().isoformat(),
                    "chat_response": reply
                }
            
            # Step 3: Validate results
            validation = await self.critic.validate_results([final_result])
            
            # Step 4: Build response
            response = self._build_response(plan, final_result, validation)
            
            # Step 5: Log execution
            self._log_execution(user_id, plan, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            
            # Provide a better error response with actual error info
            return {
                "plan_id": str(uuid.uuid4()),
                "plan": {"user_intent": intent, "tasks": []},
                "final_result": {
                    "recommendations": [],
                    "forecasts": {},
                    "spatial_overlays": {},
                    "rag_matches": []
                },
                "map_action": None,
                "provenance": [],
                "confidence": 0.0,
                "human_actions": ["check_logs", "try_again"],
                "validation": {
                    "status": "error",
                    "errors": [str(e)],
                    "warnings": [],
                    "confidence": 0.0,
                    "validation_timestamp": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat(),
                "chat_response": f"Sorry, I encountered an error: {str(e)[:200]}. Please try a different query or check the backend logs."
            }
    
    async def _execute_plan(self, plan: Plan) -> Dict[str, Any]:
        """Execute all tasks in the plan"""
        task_outputs = {}
        
        for task in plan.tasks:
            try:
                # Update task status
                task.status = TaskStatus.IN_PROGRESS
                
                # Resolve input dependencies
                resolved_input = self._resolve_dependencies(task.input_schema, task_outputs)
                
                # Execute task based on agent type
                if task.agent == AgentType.MAP_AGENT:
                    output = await self._execute_map_task(task, resolved_input)
                elif task.agent == AgentType.FORECASTER:
                    output = await self._execute_forecast_task(task, resolved_input, task_outputs)
                elif task.agent == AgentType.RECOMMENDER:
                    output = await self._execute_recommender_task(task, task_outputs)
                elif task.agent == AgentType.CRITIC:
                    output = await self._execute_critic_task(task, task_outputs)
                else:
                    raise ValueError(f"Unknown agent type: {task.agent}")
                
                # Store output
                task.output = output
                task.status = TaskStatus.COMPLETED
                task.confidence = output.get("confidence", 0.8)
                task_outputs[task.id] = output
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.errors.append(str(e))
                logger.error(f"Task {task.id} failed: {str(e)}")
                # Provide default output to continue execution
                task.output = {"error": str(e), "status": "failed"}
                task_outputs[task.id] = task.output
        
        # Aggregate outputs into final result
        return self._aggregate_results(plan, task_outputs)
    
    async def _execute_map_task(self, task: Task, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute map agent task with real Mappls data"""
        city = input_data.get("city", "Bangalore")
        
        # Get real location data from Mappls API
        location_data = await external_api_service.get_mappls_data(city)
        
        # Get base zone analysis
        zone_analysis = await self.map_agent.analyze_zones(
            city=city,
            budget=input_data.get("budget", {"min": 5000000, "max": 15000000}),
            property_type=input_data.get("property_type", "3BHK"),
            amenities=input_data.get("amenities", ["metro", "school", "hospital"])
        )
        
        # Enhance with real POI data for each zone
        for zone in zone_analysis.get("zones", []):
            if "centroid" in zone:
                lat, lon = zone["centroid"]
                
                # Get real POIs from Mappls
                schools = await external_api_service.get_nearby_pois(lat, lon, "SCHOOL")
                hospitals = await external_api_service.get_nearby_pois(lat, lon, "HOSPITAL") 
                zone["real_pois"] = {
                    "schools": schools[:3],
                    "hospitals": hospitals[:2]
                }
        
        # Add real location metadata
        zone_analysis["location_metadata"] = location_data
        
        return zone_analysis
    
    async def _execute_forecast_task(self, task: Task, input_data: Dict[str, Any], 
                                    task_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute forecast agent task"""
        # Get zones from previous map task
        zones = []
        for output in task_outputs.values():
            if "zones" in output:
                zones = output["zones"]
                break
        
        # Ensure we have zones to forecast
        if not zones:
            # Create default zones if none found
            zones = [{"id": "default", "name": "Default Zone", "base_price": 7500000}]
        
        return await self.forecaster.forecast_zones(
            zones=zones,
            months=input_data.get("forecast_months", [3, 12, 36])
        )
    
    async def _execute_recommender_task(self, task: Task, 
                                       task_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recommender agent task"""
        # Find map and forecast outputs
        map_data = None
        forecast_data = None
        
        for output in task_outputs.values():
            if "zones" in output and "geo_features" in output:
                map_data = output
            if "price_forecast" in output:
                forecast_data = output
        
        rec = await self.recommender.rank_zones(
            map_data=map_data or {},
            forecast_data=forecast_data or {},
            preferences={}
        )
        # Fetch RAG matches (Pinecone) to enrich results
        try:
            query_embedding = [0.1] * 64
            rag_matches = await external_api_service.search_similar_properties(query_embedding, filters=None, top_k=5)
            rec["rag_matches"] = rag_matches
        except Exception:
            rec["rag_matches"] = []
        return rec
    
    async def _execute_critic_task(self, task: Task, 
                                  task_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute critic agent task"""
        return await self.critic.validate_results(list(task_outputs.values()))
    
    def _resolve_dependencies(self, input_schema: Dict[str, Any], 
                            task_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve input dependencies from previous task outputs"""
        resolved = {}
        
        for key, value in input_schema.items():
            if isinstance(value, str) and value.startswith("from_"):
                # This is a dependency, skip for now
                continue
            else:
                resolved[key] = value
        
        return resolved
    
    def _aggregate_results(self, plan: Plan, task_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate task outputs into final result"""
        
        try:
            # Find key outputs
            recommendations = None
            forecasts = None
            spatial_overlays = None
            map_center = None  # [lat, lon]
            rag_matches = None
            
            logger.info(f"Aggregating task_outputs type={type(task_outputs)}, len={len(task_outputs) if task_outputs else 0}")
            
            # Ensure task_outputs is a dict
            if not isinstance(task_outputs, dict):
                logger.error(f"task_outputs is not a dict, it's {type(task_outputs)}: {task_outputs}")
                task_outputs = {}
            
            for task_id, output in task_outputs.items():
                logger.info(f"Task {task_id} output keys: {output.keys()}")
                
                if "recommendations" in output:
                    recommendations = output["recommendations"]
                    logger.info(f"Found {len(recommendations)} recommendations")
                if "price_forecast" in output:
                    forecasts = output
                    logger.info("Found forecast data")
                if "heatmap_url" in output or "geojson" in output:
                    # Try to compute a reasonable center from geo_features or location metadata
                    if not map_center:
                        geo_features = output.get("geo_features", {})
                        centroid = geo_features.get("centroid") or geo_features.get("city_center")
                        if centroid and isinstance(centroid, (list, tuple)) and len(centroid) == 2:
                            map_center = centroid
                        else:
                            loc_meta = output.get("location_metadata", {})
                            lat = loc_meta.get("latitude")
                            lon = loc_meta.get("longitude")
                            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                                map_center = [lat, lon]

                    spatial_overlays = {
                        "heatmap_url": output.get("heatmap_url", ""),
                        "geojson": output.get("geojson", {}),
                        "center": {"lat": map_center[0], "lon": map_center[1]} if map_center else None
                    }
                    logger.info("Found spatial overlay data")
                if "rag_matches" in output and rag_matches is None:
                    rag_matches = output.get("rag_matches", [])
                    logger.info(f"Found {len(rag_matches)} RAG matches")
            
            final_result = {
                "recommendations": recommendations or [],
                "forecasts": forecasts or {},
                "spatial_overlays": spatial_overlays or {},
                "rag_matches": rag_matches or []
            }
            
            logger.info(f"Final result has {len(final_result['recommendations'])} recommendations")
            return final_result
        except Exception as e:
            logger.error(f"Error in _aggregate_results: {e}", exc_info=True)
            return {
                "recommendations": [],
                "forecasts": {},
                "spatial_overlays": {},
                "rag_matches": []
            }
    
    def _build_response(self, plan: Plan, final_result: Dict[str, Any], 
                       validation: Dict[str, Any]) -> Dict[str, Any]:
        """Build final response for frontend"""
        
        # Calculate overall confidence
        task_confidences = [t.confidence for t in plan.tasks if t.confidence > 0]
        overall_confidence = sum(task_confidences) / len(task_confidences) if task_confidences else 0.5
        
        # Build provenance
        provenance = []
        for task in plan.tasks:
            provenance.append({
                "task_id": task.id,
                "agent": task.agent.value,
                "action": task.action,
                "status": task.status.value,
                "confidence": task.confidence
            })
        
        # Determine human actions
        human_actions = []
        if overall_confidence > 0.7 and validation["status"] == "pass":
            human_actions = ["review_recommendations", "schedule_visits", "save_search"]
        else:
            human_actions = ["refine_criteria", "request_more_data", "speak_to_expert"]
        
        # Include map action in response if present
        map_action = final_result.get("map_action")
        
        # Generate chat response with fallback
        try:
            chat_response = self._generate_chat_response(final_result, overall_confidence)
            if not chat_response or chat_response.strip() == "":
                chat_response = "I've analyzed your request. Please check the panels for detailed results."
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            chat_response = "I've completed the analysis. Please check the panels for details."
        
        response = {
            "plan_id": plan.id,
            "plan": {
                "user_intent": plan.user_intent,
                "tasks": [
                    {
                        "id": t.id,
                        "agent": t.agent.value,
                        "action": t.action,
                        "status": t.status.value
                    }
                    for t in plan.tasks
                ]
            },
            "final_result": final_result,
            "map_action": map_action,  # Add map action for frontend
            "provenance": provenance,
            "confidence": round(overall_confidence, 2),
            "human_actions": human_actions,
            "validation": validation,
            "timestamp": datetime.now().isoformat(),
            "chat_response": chat_response
        }
        
        return response
    
    async def _generate_chat_response_async(self, final_result: Dict[str, Any], confidence: float, plan: Plan) -> str:
        """Generate natural language response using LLM for chat panel"""
        recommendations = final_result.get("recommendations", [])
        map_action = final_result.get("map_action")
        
        # If there's a map action, prioritize describing it
        if map_action:
            action_type = map_action.get("action", "")
            location = map_action.get("location", "the location")
            
            if action_type == "center":
                return f"📍 Navigating to {location} on the map. The map will smoothly pan to show you this area."
            
            elif action_type == "drawBuffer":
                radius = map_action.get("radius", 2)
                return f"⭕ Drawing a {radius}km radius around {location} on the map. This will help you visualize the area coverage and nearby zones."
            
            elif action_type == "drawPolygon":
                return f"✏️ Activating polygon drawing mode around {location}. Click on the map to create boundary points."
            
            elif action_type == "addMarker":
                return f"📍 Adding a marker at {location} on the map to highlight this area."
            
            elif action_type == "compareAreas":
                areas = map_action.get("areas", [])
                area_names = ", ".join(areas) if areas else "these areas"
                return f"⚖️ Comparing {area_names} on the map. I'll highlight both zones so you can see the differences."
            
            # If recommendations exist alongside map action, mention both
            if recommendations:
                top_rec = recommendations[0]
                return f"🗺️ I've navigated to {location} and found {len(recommendations)} investment opportunities. Top pick: **{top_rec.get('zone_name', 'Unknown')}** with {top_rec.get('score', 0)*100:.0f}% score."
        
        if not recommendations:
            return "I couldn't find suitable properties matching your criteria. Would you like to adjust your search parameters?"
        
        # Build context for LLM
        context = f"""
        User Query: {plan.user_intent}
        Found {len(recommendations)} properties
        Top Zone: {recommendations[0].get('zone_name') if recommendations else 'N/A'}
        Confidence: {confidence*100:.0f}%
        """
        
        # Generate insights using LLM
        if recommendations:
            property_data = recommendations[0]
            insights = await external_api_service.generate_property_insights(property_data)
        else:
            insights = "Limited data available for analysis."
        
        # Build structured response
        top_rec = recommendations[0] if recommendations else {}
        
        response = f"""I'm Valora, your AI real estate advisor. Based on your requirements, I've identified {len(recommendations)} excellent investment opportunities.

**Top Recommendation: {top_rec.get('zone_name', 'Unknown Zone')}**
- Investment Score: {top_rec.get('score', 0)*100:.0f}%
- Current Price: ₹{top_rec.get('current_price', 0)/100000:.1f}L
- 3-Year Growth Potential: {top_rec.get('growth_potential', [0,0,0])[-1]:.1f}%
- Rental Yield: {top_rec.get('rental_yield', 0):.1f}%

**AI Analysis:**
{insights}

**Key Highlights:**
"""
        
        for highlight in top_rec.get('highlights', [])[:3]:
            response += f"• {highlight}\n"
        
        response += f"\n**Why this location?**\n"
        for reason in top_rec.get('reasons', [])[:3]:
            response += f"• {reason}\n"
        
        if len(recommendations) > 1:
            response += f"\nI've also found {len(recommendations)-1} other promising options. Would you like to explore them or schedule site visits?"
        
        return response
    
    def _generate_map_command_response(self, map_action: Dict[str, Any]) -> str:
        """Generate chat response specifically for map commands"""
        action_type = map_action.get("action", "")
        location = map_action.get("location", "the location")
        
        if action_type == "center":
            return f"📍 Navigating to {location} on the map. The map will smoothly pan to show you this area."
        
        elif action_type == "drawBuffer":
            radius = map_action.get("radius", 2)
            return f"⭕ Drawing a {radius}km radius around {location} on the map. This will help you visualize the area coverage and nearby zones."
        
        elif action_type == "drawPolygon":
            return f"✏️ Activating polygon drawing mode around {location}. Click on the map to create boundary points."
        
        elif action_type == "addMarker":
            return f"📍 Adding a marker at {location} on the map to highlight this area."
        
        elif action_type == "compareAreas":
            areas = map_action.get("areas", [])
            area_names = ", ".join(areas) if areas else "these areas"
            return f"⚖️ Comparing {area_names} on the map. I'll highlight both zones so you can see the differences."
        
        elif action_type == "showProperties":
            return f"🏠 Showing properties in {location} on the map with detailed markers."
        
        elif action_type == "drawCircle":
            return f"⭕ Activating circle drawing mode. Click on the map to set the center."
        
        elif action_type == "drawRectangle":
            return f"▢ Activating rectangle drawing mode. Click and drag on the map to draw."
        
        elif action_type == "drawPropertyBoundary":
            return f"🏠 Drawing property boundary mode activated. Click on the map to mark plot corners. Double-click to finish."
        
        elif action_type == "drawCatchmentArea":
            amenity = map_action.get("amenityType", "amenity")
            return f"🏢 Drawing catchment area for {amenity}. This shows the accessible coverage zone."
        
        elif action_type == "compareZones":
            zones = map_action.get("zones", [])
            zone_names = ", ".join([z.get("location", "") for z in zones]) if zones else "selected zones"
            return f"⚖️ Comparing {zone_names} with overlay zones. Each area will be highlighted in a different color."
        
        # Default fallback
        return f"🗺️ Executing map action: {action_type} for {location}."
    
    def _generate_chat_response(self, final_result: Dict[str, Any], confidence: float) -> str:
        """Fallback synchronous chat response generation"""
        recommendations = final_result.get("recommendations", [])
        rag_matches = final_result.get("rag_matches", [])
        map_action = final_result.get("map_action")
        
        logger.info(f"Generating chat response: {len(recommendations)} recommendations, {len(rag_matches)} RAG matches, map_action={bool(map_action)}")
        
        # If there's a map action, prioritize describing it
        if map_action:
            action_type = map_action.get("action", "")
            location = map_action.get("location", "the location")
            
            if action_type == "center":
                return f"📍 Navigating to {location} on the map. The map will smoothly pan to show you this area."
            
            elif action_type == "drawBuffer":
                radius = map_action.get("radius", 2)
                return f"⭕ Drawing a {radius}km radius around {location} on the map. This will help you visualize the area coverage and nearby zones."
            
            elif action_type == "drawPolygon":
                return f"✏️ Activating polygon drawing mode around {location}. Click on the map to create boundary points."
            
            elif action_type == "addMarker":
                return f"📍 Adding a marker at {location} on the map to highlight this area."
            
            elif action_type == "compareAreas":
                areas = map_action.get("areas", [])
                area_names = ", ".join(areas) if areas else "these areas"
                return f"⚖️ Comparing {area_names} on the map. I'll highlight both zones so you can see the differences."
            
            elif action_type == "showProperties":
                return f"🏠 Showing properties in {location} on the map with detailed markers."
            
            # If recommendations exist alongside map action, mention both
            if recommendations:
                top_rec = recommendations[0]
                return f"🗺️ I've navigated to {location} and found {len(recommendations)} investment opportunities. Top pick: **{top_rec.get('zone_name', 'Unknown')}** with {top_rec.get('score', 0)*100:.0f}% score."
        
        if not recommendations:
            # If we have RAG matches but no scored recommendations, surface them
            if rag_matches:
                top = rag_matches[:5]
                lines = ["Here are some relevant places I found:"]
                for m in top:
                    name = m.get("metadata", {}).get("name") or m.get("name", "Place")
                    loc = m.get("metadata", {}).get("locality") or m.get("locality", "")
                    city = m.get("metadata", {}).get("city") or m.get("city", "")
                    lines.append(f"• {name}{' - ' + loc if loc else ''}{' (' + city + ')' if city else ''}")
                lines.append("Would you like me to analyze any of these or refine your criteria?")
                return "\n".join(lines)
            return "I couldn't find suitable properties matching your criteria. Would you like to adjust your search parameters?"
        
        top_rec = recommendations[0] if recommendations else {}
        
        response = f"""I'm Valora, your AI real estate advisor. Based on your requirements, I've identified {len(recommendations)} excellent investment opportunities.

**Top Recommendation: {top_rec.get('zone_name', 'Unknown Zone')}**
- Investment Score: {top_rec.get('score', 0)*100:.0f}%
- Current Price: ₹{top_rec.get('current_price', 0)/100000:.1f}L
- 3-Year Growth Potential: {top_rec.get('growth_potential', [0,0,0])[-1]:.1f}%
- Rental Yield: {top_rec.get('rental_yield', 0):.1f}%

**Key Highlights:**
"""
        
        for highlight in top_rec.get('highlights', [])[:3]:
            response += f"• {highlight}\n"
        
        response += f"\n**Why this location?**\n"
        for reason in top_rec.get('reasons', [])[:3]:
            response += f"• {reason}\n"
        
        if len(recommendations) > 1:
            response += f"\nI've also found {len(recommendations)-1} other promising options. Would you like to explore them or schedule site visits?"
        
        # Append RAG matches for additional context
        if rag_matches:
            response += "\n\n**Similar Places Found:**\n"
            for m in rag_matches[:3]:
                name = m.get("metadata", {}).get("name") or m.get("name", "Place")
                loc = m.get("metadata", {}).get("locality") or m.get("locality", "")
                city = m.get("metadata", {}).get("city") or m.get("city", "")
                response += f"• {name}{' - ' + loc if loc else ''}{' (' + city + ')' if city else ''}\n"
        
        return response
    
    def _build_error_response(self, error: str) -> Dict[str, Any]:
        """Build error response"""
        return {
            "plan_id": str(uuid.uuid4()),
            "status": "error",
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "chat_response": f"I'm Valora, and I encountered an issue while processing your request: {error}. Please try again or refine your search criteria."
        }
    
    def _is_greeting(self, text: str) -> bool:
        """Detect if the user input is a simple greeting."""
        if not text:
            return False
        t = text.strip().lower()
        # Normalize common punctuation
        for ch in ["!", ".", ","]:
            t = t.replace(ch, "")
        # Exact greeting phrases
        exact = {
            "hi", "hello", "hey", "yo", "hiya", "howdy",
            "good morning", "good afternoon", "good evening",
            "namaste", "gm", "gn"
        }
        if t in exact:
            return True
        # Short polite variants like "hi there", "hello valora"
        if (t.startswith("hi") or t.startswith("hello") or t.startswith("hey")) and len(t) <= 20:
            return True
        return False

    

    async def _handle_geospatial_command(self, user_id: str, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle geospatial drawing and analysis commands"""
        try:
            # Parse the drawing command
            drawing_info = self.geospatial_agent.interpret_drawing_command(intent)
            
            # Execute based on command type
            result = None
            map_action = None
            
            if drawing_info["type"] == "buffer" and drawing_info.get("locations") and drawing_info.get("radius_meters"):
                # Create buffer around location
                # For now, use a default center - in production, geocode the location
                center = context.get("center", [12.9716, 77.5946])  # Default Bangalore center
                result = self.geospatial_agent.create_buffer(center, drawing_info["radius_meters"])
                
                map_action = {
                    "action": "draw_buffer",
                    "center": center,
                    "radius": drawing_info["radius_meters"],
                    "purpose": drawing_info["purpose"]
                }
            
            elif drawing_info["type"] == "polygon" and context.get("coordinates"):
                # Create polygon from provided coordinates
                result = self.geospatial_agent.create_polygon(context["coordinates"])
                
                map_action = {
                    "action": "draw_polygon",
                    "coordinates": context["coordinates"],
                    "purpose": drawing_info["purpose"]
                }
            
            elif "compare" in intent.lower() and context.get("zones"):
                # Compare multiple zones
                polygons = [Polygon(z["coordinates"]) for z in context["zones"]]
                result = self.geospatial_agent.compare_zones(polygons)
                
                map_action = {
                    "action": "compare_zones",
                    "zones": context["zones"]
                }
            
            elif "optimal" in intent.lower() or "suggest" in intent.lower():
                # Suggest optimal zones
                criteria = {
                    "budget": context.get("budget"),
                    "property_type": context.get("property_type", "residential"),
                    "purpose": drawing_info["purpose"]
                }
                result = self.geospatial_agent.suggest_optimal_zones(criteria)
                
                map_action = {
                    "action": "highlight_zones",
                    "zones": result
                }
            
            # Build response
            response_text = self._format_geospatial_response(drawing_info, result)
            
            return {
                "plan_id": str(uuid.uuid4()),
                "plan": {
                    "user_intent": intent,
                    "tasks": [{"task": "geospatial_analysis", "status": "completed"}]
                },
                "final_result": result or {},
                "map_action": map_action,
                "drawing_info": drawing_info,
                "confidence": 0.95,
                "chat_response": response_text,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Geospatial command error: {e}")
            return {
                "plan_id": str(uuid.uuid4()),
                "error": str(e),
                "chat_response": f"I understood you want to {intent.lower()}, but I need more specific information. Can you provide coordinates or be more specific about the location?",
                "confidence": 0.5,
                "timestamp": datetime.now().isoformat()
            }
    
    def _format_geospatial_response(self, drawing_info: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format geospatial analysis results for chat"""
        if not result:
            return f"I've understood your request to {drawing_info['type']} for {drawing_info['purpose']}, but I need more information to proceed."
        
        response = f"📍 **Spatial Analysis Complete**\n\n"
        
        if result.get("area_sqm"):
            response += f"**Area**: {result['area_sqm']:,.0f} sqm ({result.get('area_acres', 0):,.2f} acres)\n"
        
        if result.get("perimeter_m"):
            response += f"**Perimeter**: {result['perimeter_m']:,.0f} meters\n"
        
        if result.get("properties_analysis"):
            pa = result["properties_analysis"]
            response += f"\n**Property Analysis**:\n"
            response += f"• Total Properties: {pa.get('total_properties', 0)}\n"
            response += f"• Amenities Score: {pa.get('amenities_score', 0):.0f}/100\n"
            response += f"• Infrastructure Score: {pa.get('infrastructure_score', 0):.0f}/100\n"
            response += f"• Investment Potential: {pa.get('investment_potential', 0):.0f}/100\n"
        
        if result.get("zones"):
            response += f"\n**Zone Comparison**:\n"
            for zone in result["zones"]:
                response += f"• Zone {zone['zone_id']}: {zone.get('investment_potential', 0):.0f} potential\n"
            
            if result.get("best_for_investment"):
                response += f"\n✅ **Best for Investment**: Zone {result['best_for_investment']}\n"
        
        if drawing_info.get("suggested_actions"):
            response += f"\n**Suggested Next Steps**:\n"
            for action in drawing_info["suggested_actions"][:3]:
                response += f"• {action.replace('_', ' ').title()}\n"
        
        return response

    def _build_greeting_response(self, intent: str) -> Dict[str, Any]:
        """Return a friendly greeting with quick suggestions and zero confidence to hide banner."""
        greeting = (
            "👋 Hi! I'm Valora, your AI real estate advisor for Bangalore.\n\n"
            "I can help you: \n"
            "• Show areas (e.g., 'Show me Whitefield')\n"
            "• Find properties (e.g., 'Find 3BHK in HSR under 1.5 crore')\n"
            "• Compare zones (e.g., 'Compare Whitefield vs Electronic City')\n"
            "• Draw on the map (e.g., 'Draw 2km radius around Manyata Tech Park')\n\n"
            "Tell me what you'd like to do!"
        )
        return {
            "plan_id": str(uuid.uuid4()),
            "plan": {
                "user_intent": intent,
                "tasks": []
            },
            "final_result": {},
            "map_action": None,
            "provenance": [],
            "confidence": 0.0,  # Hide AI Confidence banner in frontend
            "human_actions": ["try_sample_queries", "ask_for_help"],
            "validation": {"status": "pass", "errors": [], "warnings": [], "confidence": 1.0, "validation_timestamp": datetime.now().isoformat()},
            "timestamp": datetime.now().isoformat(),
            "chat_response": greeting
        }
    
    def _log_execution(self, user_id: str, plan: Plan, response: Dict[str, Any]):
        """Log execution for analysis"""
        execution_log = {
            "user_id": user_id,
            "plan_id": plan.id,
            "intent": plan.user_intent,
            "timestamp": datetime.now().isoformat(),
            "confidence": response.get("confidence", 0),
            "validation_status": response.get("validation", {}).get("status", "unknown")
        }
        self.execution_history.append(execution_log)
        logger.info(f"Executed plan {plan.id} for user {user_id}")
    
    def get_active_plans(self) -> List[Dict[str, Any]]:
        """Get all active plans"""
        return [
            {
                "id": plan.id,
                "intent": plan.user_intent,
                "status": plan.status,
                "created_at": plan.created_at.isoformat()
            }
            for plan in self.active_plans.values()
        ]
    
    def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific plan"""
        if plan_id not in self.active_plans:
            return None
        
        plan = self.active_plans[plan_id]
        return {
            "id": plan.id,
            "status": plan.status,
            "tasks": [
                {
                    "id": t.id,
                    "agent": t.agent.value,
                    "status": t.status.value,
                    "confidence": t.confidence
                }
                for t in plan.tasks
            ],
            "confidence": plan.confidence
        }
