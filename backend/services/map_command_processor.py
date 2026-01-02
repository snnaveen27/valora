"""
Map Command Processor - Handles natural language to map commands conversion
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

logger = logging.getLogger(__name__)

class MapCommandProcessor:
    """Processes natural language queries into map commands"""
    
    def __init__(self):
        # Bangalore locations database with coordinates
        self.bangalore_locations = {
            # Major areas
            "whitefield": {"lat": 12.9698, "lng": 77.7500, "aliases": ["whitfield", "white field"]},
            "koramangala": {"lat": 12.9352, "lng": 77.6245, "aliases": ["koramangla", "kormangala"]},
            "hsr layout": {"lat": 12.9081, "lng": 77.6476, "aliases": ["hsr", "hsr sector"]},
            "marathahalli": {"lat": 12.9591, "lng": 77.6974, "aliases": ["marathalli", "marthahalli"]},
            "electronic city": {"lat": 12.8456, "lng": 77.6600, "aliases": ["e-city", "ecity", "electronic city phase 1", "electronic city phase 2"]},
            "indiranagar": {"lat": 12.9784, "lng": 77.6408, "aliases": ["indira nagar"]},
            "hebbal": {"lat": 13.0358, "lng": 77.5970, "aliases": ["hebbel"]},
            "btm layout": {"lat": 12.9165, "lng": 77.6101, "aliases": ["btm", "btm stage"]},
            "jp nagar": {"lat": 12.9100, "lng": 77.5850, "aliases": ["jayanagar", "jp nagar phase"]},
            "sarjapur": {"lat": 12.8599, "lng": 77.7906, "aliases": ["sarjapur road", "sarjapura"]},
            "yeshwanthpur": {"lat": 13.0280, "lng": 77.5340, "aliases": ["yeshwantpur", "yeswanthpur"]},
            "yelahanka": {"lat": 13.1007, "lng": 77.5963, "aliases": ["yellahanka", "yelahanka new town"]},
            "bannerghatta": {"lat": 12.8009, "lng": 77.5755, "aliases": ["bannerghatta road", "bannergatta"]},
            "jayanagar": {"lat": 12.9308, "lng": 77.5838, "aliases": ["jaya nagar"]},
            "malleshwaram": {"lat": 13.0030, "lng": 77.5640, "aliases": ["malleswaram", "malleshwara"]},
            "mg road": {"lat": 12.9762, "lng": 77.6033, "aliases": ["mahatma gandhi road", "m g road"]},
            "brigade road": {"lat": 12.9716, "lng": 77.6077, "aliases": ["brigade rd"]},
            "commercial street": {"lat": 12.9822, "lng": 77.6085, "aliases": ["commercial st"]},
            "vijayanagar": {"lat": 12.9698, "lng": 77.5350, "aliases": ["vijaya nagar"]},
            "rajajinagar": {"lat": 12.9925, "lng": 77.5633, "aliases": ["rajaji nagar"]},
            "basavanagudi": {"lat": 12.9420, "lng": 77.5680, "aliases": ["basavana gudi"]},
            "richmond town": {"lat": 12.9650, "lng": 77.6120, "aliases": ["richmond"]},
            "cunningham road": {"lat": 12.9850, "lng": 77.5950, "aliases": ["cunningham rd"]},
            
            # Tech parks
            "manyata tech park": {"lat": 13.0480, "lng": 77.6210, "aliases": ["manyata", "manyata embassy"]},
            "bagmane tech park": {"lat": 12.9360, "lng": 77.6950, "aliases": ["bagmane"]},
            "ecospace": {"lat": 12.9180, "lng": 77.6780, "aliases": ["eco space"]},
            "prestige tech park": {"lat": 12.9610, "lng": 77.7470, "aliases": ["prestige"]},
            
            # Railway stations
            "whitefield railway station": {"lat": 12.9784, "lng": 77.7370, "aliases": ["whitefield station"]},
            "bangalore city railway station": {"lat": 12.9791, "lng": 77.5713, "aliases": ["majestic", "ksr bengaluru"]},
            "yeshwanthpur railway station": {"lat": 13.0219, "lng": 77.5430, "aliases": ["ypr", "yeshwanthpur station"]},
            
            # Metro stations
            "koramangala metro": {"lat": 12.9352, "lng": 77.6245, "aliases": ["koramangala metro station"]},
            "indiranagar metro": {"lat": 12.9784, "lng": 77.6408, "aliases": ["indiranagar metro station"]},
            
            # Landmarks
            "cubbon park": {"lat": 12.9763, "lng": 77.5929, "aliases": ["cubbon"]},
            "lalbagh": {"lat": 12.9507, "lng": 77.5848, "aliases": ["lal bagh", "lalbagh botanical garden"]},
            "ulsoor lake": {"lat": 12.9817, "lng": 77.6201, "aliases": ["ulsoor", "halasuru lake"]},
            "bangalore palace": {"lat": 12.9986, "lng": 77.5921, "aliases": ["palace"]},
            
            # General
            "bangalore": {"lat": 12.9716, "lng": 77.5946, "aliases": ["bengaluru", "blr", "bangalor"]},
            "outer ring road": {"lat": 12.9591, "lng": 77.6974, "aliases": ["orr", "outer ring rd"]},
        }
        
        # Enhanced command patterns with more variations
        self.command_patterns = [
            # Property visibility commands should be checked before generic navigation patterns
            ("show_properties", [
                r"(?:show|find|search|display)\s+(?:me\s+)?(?:properties|apartments|houses|flats|villas)\s+(?:in|near|around)\s+(.+)",
                r"properties\s+(?:in|near)\s+(.+)",
                r"(?:show|find|search|display)\s+(?:me\s+)?(?:properties|apartments|houses|flats|villas)(?:\s+(?:now|please|all))?$"
            ]),

            # Navigation/centering commands
            ("navigate", [
                r"(?:go to|navigate to|show|center on|focus on|zoom to|take me to|show me)\s+(.+)",
                r"(.+?)(?:\s+on map|\s+area|\s+location)?$"
            ]),
            
            # Buffer/radius drawing commands - Enhanced for real estate
            ("draw_buffer", [
                r"draw\s+(?:a\s+)?(\d+)\s*(?:km|kilometer|kilometres?)?\s+(?:radius|buffer|circle|zone)\s+(?:around|near|at)\s+(.+)",
                r"(?:show|create|add|make)\s+(?:a\s+)?(\d+)\s*(?:km)?\s+(?:catchment|coverage|service area|zone)\s+(?:around|for|at)\s+(.+)",
                r"(\d+)\s*(?:km)?\s+radius\s+(?:around|at|near)\s+(.+)",
                r"buffer\s+(?:of\s+)?(\d+)\s*(?:km)?\s+(?:around|at)\s+(.+)",
                r"mark\s+(\d+)\s*(?:km)?\s+(?:area|zone|circle)\s+(?:around|near)\s+(.+)"
            ]),
            
            # Property boundary drawing
            ("draw_property", [
                r"(?:draw|mark|outline|trace)\s+property\s+(?:boundary|boundaries|outline)",
                r"(?:show|create)\s+property\s+(?:limits|boundary|area)",
                r"(?:mark|draw)\s+plot\s+(?:boundary|area|outline)"
            ]),
            
            # Catchment area for amenities
            ("draw_catchment", [
                r"(?:show|draw|mark)\s+catchment\s+(?:area|zone)\s+(?:for|around)\s+(.+)",
                r"(?:walkable|walking|transit)\s+(?:area|zone|distance)\s+(?:from|around)\s+(.+)",
                r"(?:amenity|facility)\s+(?:coverage|reach|access)\s+(?:for|around)\s+(.+)"
            ]),
            
            # Investment zone analysis
            ("draw_investment", [
                r"(?:mark|show|highlight)\s+investment\s+(?:zones?|hotspots?|areas?)",
                r"(?:identify|find|show)\s+(?:high|best)\s+(?:growth|appreciation)\s+(?:zones?|areas?)",
                r"(?:investment|growth)\s+(?:potential|opportunity)\s+(?:zones?|areas?)"
            ]),
            
            # Compare locations
            ("compare", [
                r"compare\s+(.+?)\s+(?:with|vs|versus|and|to)\s+(.+?)(?:\s+for investment)?",
                r"(.+?)\s+vs\s+(.+)",
                r"which is better\s*[:,-]?\s*(.+?)\s+or\s+(.+)"
            ]),
            
            # Draw polygon
            ("draw_polygon", [
                r"(?:draw|create|mark)\s+(?:a\s+)?(?:polygon|boundary|area|zone)\s+(?:around|for|in)\s+(.+)",
                r"outline\s+(.+)"
            ]),
            
            ("investment_hotspots", [
                r"(?:show|display|find)\s+(?:investment\s+)?hotspots\s+(?:in|around|near)?\s*(.+)?",
                r"best\s+(?:investment\s+)?areas\s+(?:in|around)?\s*(.+)?"
            ])
        ]
    
    def fuzzy_match_location(self, query: str) -> Optional[Dict[str, Any]]:
        """Fuzzy match a location query to known Bangalore locations"""
        query_lower = query.lower().strip()
        
        # Direct match
        if query_lower in self.bangalore_locations:
            return {
                "name": query_lower,
                "coordinates": [
                    self.bangalore_locations[query_lower]["lat"],
                    self.bangalore_locations[query_lower]["lng"]
                ],
                "confidence": 1.0
            }
        
        # Check aliases
        for location, data in self.bangalore_locations.items():
            if query_lower in data.get("aliases", []):
                return {
                    "name": location,
                    "coordinates": [data["lat"], data["lng"]],
                    "confidence": 0.95
                }
        
        # Fuzzy matching
        all_locations = list(self.bangalore_locations.keys())
        for loc_data in self.bangalore_locations.values():
            all_locations.extend(loc_data.get("aliases", []))
        
        best_match = process.extractOne(query_lower, all_locations, scorer=fuzz.ratio)
        
        if best_match and best_match[1] > 70:  # 70% similarity threshold
            matched_name = best_match[0]
            
            # Find the actual location
            for location, data in self.bangalore_locations.items():
                if location == matched_name or matched_name in data.get("aliases", []):
                    return {
                        "name": location,
                        "coordinates": [data["lat"], data["lng"]],
                        "confidence": best_match[1] / 100.0
                    }
        
        return None
    
    def parse_intent(self, query: str) -> Dict[str, Any]:
        """Parse user query into map command and parameters"""
        query = query.strip()
        logger.info(f"🔎 Parsing map intent from query: '{query}'")
        
        # Check each command pattern
        for command_type, patterns in self.command_patterns:
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    logger.info(f"✅ Pattern matched! Type: {command_type}, Pattern: {pattern}, Groups: {match.groups()}")
                    return self._process_command(command_type, match.groups(), query)
        
        # Default: try to interpret as navigation command
        location = self.fuzzy_match_location(query)
        if location:
            return {
                "command": "navigate",
                "parameters": {
                    "location": location["name"],
                    "coordinates": location["coordinates"]
                },
                "confidence": location["confidence"],
                "original_query": query
            }
        
        return {
            "command": None,
            "parameters": {},
            "confidence": 0,
            "original_query": query,
            "error": "Could not understand the map command"
        }
    
    def _process_command(self, command_type: str, groups: Tuple, query: str) -> Dict[str, Any]:
        """Process specific command types"""
        
        if command_type == "navigate":
            location_query = groups[0] if groups else query
            location = self.fuzzy_match_location(location_query)
            
            if location:
                return {
                    "command": "navigate",
                    "parameters": {
                        "location": location["name"],
                        "coordinates": location["coordinates"]
                    },
                    "confidence": location["confidence"],
                    "original_query": query
                }
        
        elif command_type == "draw_buffer":
            radius = int(groups[0]) if groups[0] else 2
            location_query = groups[1] if len(groups) > 1 else "bangalore"
            location = self.fuzzy_match_location(location_query)
            
            # If location is recognized, use it
            if location:
                return {
                    "command": "draw_buffer",
                    "parameters": {
                        "radius_km": radius,
                        "location": location["name"],
                        "coordinates": location["coordinates"]
                    },
                    "confidence": location["confidence"],
                    "original_query": query
                }
            # If location not recognized but pattern matched, still return with high confidence
            # The frontend will geocode it
            else:
                return {
                    "command": "draw_buffer",
                    "parameters": {
                        "radius_km": radius,
                        "location": location_query.strip(),
                        "coordinates": None  # Will be geocoded on frontend
                    },
                    "confidence": 0.85,  # High confidence because pattern matched
                    "original_query": query
                }
        
        elif command_type == "draw_property":
            return {
                "command": "draw_property",
                "parameters": {},
                "confidence": 0.9,
                "original_query": query
            }
        
        elif command_type == "draw_catchment":
            amenity = groups[0] if groups else "general"
            return {
                "command": "draw_catchment",
                "parameters": {
                    "amenity_type": amenity.strip()
                },
                "confidence": 0.85,
                "original_query": query
            }
        
        elif command_type == "draw_investment":
            return {
                "command": "draw_investment",
                "parameters": {},
                "confidence": 0.85,
                "original_query": query
            }
        
        elif command_type == "compare":
            location1 = self.fuzzy_match_location(groups[0]) if groups else None
            location2 = self.fuzzy_match_location(groups[1]) if len(groups) > 1 else None
            
            if location1 and location2:
                return {
                    "command": "compare",
                    "parameters": {
                        "locations": [
                            {"name": location1["name"], "coordinates": location1["coordinates"]},
                            {"name": location2["name"], "coordinates": location2["coordinates"]}
                        ]
                    },
                    "confidence": min(location1["confidence"], location2["confidence"]),
                    "original_query": query
                }
        
        elif command_type == "draw_polygon":
            location_query = groups[0] if groups else query
            location = self.fuzzy_match_location(location_query)
            
            if location:
                return {
                    "command": "draw_polygon",
                    "parameters": {
                        "location": location["name"],
                        "coordinates": location["coordinates"]
                    },
                    "confidence": location["confidence"],
                    "original_query": query
                }
        
        elif command_type == "show_properties":
            location_query = groups[0] if groups else "bangalore"
            location = self.fuzzy_match_location(location_query)
            
            if location:
                return {
                    "command": "show_properties",
                    "parameters": {
                        "location": location["name"],
                        "coordinates": location["coordinates"]
                    },
                    "confidence": location["confidence"],
                    "original_query": query
                }
        
        elif command_type == "investment_hotspots":
            location_query = groups[0] if groups and groups[0] else "bangalore"
            location = self.fuzzy_match_location(location_query)
            
            if location:
                return {
                    "command": "investment_hotspots",
                    "parameters": {
                        "location": location["name"],
                        "coordinates": location["coordinates"]
                    },
                    "confidence": location["confidence"] if location else 0.5,
                    "original_query": query
                }
        
        return {
            "command": None,
            "parameters": {},
            "confidence": 0,
            "original_query": query
        }
    
    def generate_map_action(self, parsed_intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate map action from parsed intent"""
        
        if not parsed_intent.get("command"):
            return None
        
        command = parsed_intent["command"]
        params = parsed_intent["parameters"]
        
        if command == "navigate":
            return {
                "action": "center",
                "location": params["location"],
                "coordinates": params["coordinates"],
                "zoom": 15
            }
        
        elif command == "draw_buffer":
            return {
                "action": "drawBuffer",
                "location": params["location"],
                "coordinates": params["coordinates"],
                "radius": params["radius_km"]
            }
        
        elif command == "compare":
            return {
                "action": "compareAreas",
                "areas": params["locations"]
            }
        
        elif command == "draw_polygon":
            return {
                "action": "startPolygon",
                "center": params["coordinates"],
                "location": params["location"]
            }
        
        elif command == "show_properties":
            return {
                "action": "showProperties",
                "location": params["location"],
                "coordinates": params["coordinates"]
            }
        
        elif command == "investment_hotspots":
            return {
                "action": "showHotspots",
                "location": params.get("location", "bangalore"),
                "coordinates": params.get("coordinates", [12.9716, 77.5946])
            }
        
        elif command == "draw_property":
            return {
                "action": "drawPropertyBoundary",
                "parameters": params
            }
        
        elif command == "draw_catchment":
            return {
                "action": "drawCatchmentArea",
                "amenityType": params.get("amenity_type", "general")
            }
        
        elif command == "draw_investment":
            return {
                "action": "drawInvestmentZone",
                "parameters": params
            }
        
        return None
