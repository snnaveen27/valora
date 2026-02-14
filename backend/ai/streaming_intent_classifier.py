"""
DEPRECATED: Streaming Intent Classifier - No longer used.
Intent classification is handled by IntentRouter in gis_agents.py with LLM fallback.
This file is kept for backward compatibility but is not imported anywhere.
"""
from typing import AsyncGenerator, Dict, Any

class StreamingIntentClassifier:
    """Minimal stub for streaming intent classification."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def classify_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream classification events."""
        # Emit start event first to trigger TopTaskBanner
        yield {
            "type": "intent_classification_start",
            "query": query,
            "stage": "intent"
        }
        
        # Simple fallback classification
        intent = "general"
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ['find', 'search', 'looking', '2bhk', '3bhk', 'apartment']):
            intent = "property_search"
        elif any(kw in query_lower for kw in ['navigate', 'go to', 'fly to', 'show me']):
            intent = "navigate"
        elif any(kw in query_lower for kw in ['analyze', 'analysis', 'tell me about']):
            intent = "analyze_area"
        elif any(kw in query_lower for kw in ['hi', 'hello', 'hey']):
            intent = "greeting"
        
        yield {
            "type": "intent_detected",
            "intent": intent,
            "confidence": 0.7,
            "task_graph": {
                "query": query,
                "intent": intent,
                "tasks": [
                    {"id": "t1", "label": "Processing query", "status": "running", "type": "action"}
                ]
            }
        }

# Convenience function
def get_streaming_intent_classifier(llm_client=None):
    return StreamingIntentClassifier(llm_client)
