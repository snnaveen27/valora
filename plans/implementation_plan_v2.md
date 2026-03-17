# Valora AI - Detailed Implementation Plan (Simplified)

**Version:** 2.0  
**Date:** February 16, 2026  
**Status:** Ready for Implementation

---

## Overview

This document provides detailed implementation specifications for **3 HIGH priority enhancements**:

1. **Sequential Model Management** - 6GB VRAM optimization
2. **UI Tab System** - Free vs Pro tier rendering
3. **Payment Integration** - Stripe subscriptions

### Architecture Clarification

**Planning System:** Use existing [`task_orchestrator.py`](backend/ai/task_orchestrator.py) - NO tiered planning needed.

**User Tiers (Free vs Pro):** Only affects:
- Query limits (credits: 50 vs 500/month)
- UI tabs shown (limited vs full content)

---

## Enhancement 1: Sequential Model Management

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│ Task Batcher                                        │
│ • Groups tasks by required model                    │
│ • Minimizes model switches                          │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Sequential Model Manager                            │
│ • Tracks current loaded model                       │
│ • Unloads/loads models as needed                    │
│ • Emits SSE events during switches                  │
│ • VRAM-aware (6GB limit)                            │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Model Execution                                     │
│ • Execute batch with current model                  │
│ • Switch to next model if needed                    │
└─────────────────────────────────────────────────────┘
```

### 1.2 File Structure

```
backend/ai/
├── sequential_model_manager.py  # NEW: Model lifecycle
└── task_batcher.py              # NEW: Group tasks by model
```

### 1.3 Implementation Details

#### 1.3.1 File: `backend/ai/sequential_model_manager.py`

```python
"""
Sequential Model Manager - Manages model loading for 6GB VRAM.
Only one model loaded at a time, with smart switching.
"""

import subprocess
import time
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("valora.model_manager")


class ModelStatus(Enum):
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    name: str
    vram_required_gb: float
    purpose: str
    status: ModelStatus = ModelStatus.NOT_LOADED


class SequentialModelManager:
    """
    Manages model loading/unloading for limited VRAM environments.
    
    Features:
    - Only one model loaded at a time
    - Automatic switching with SSE notifications
    - VRAM tracking
    - Keepalive management
    """
    
    MODELS = {
        'qwen3:4b-instruct': ModelInfo(
            name='qwen3:4b-instruct',
            vram_required_gb=3.5,
            purpose='general_execution'
        ),
        'qwen3:8b': ModelInfo(
            name='qwen3:8b',
            vram_required_gb=5.5,
            purpose='general_execution'
        ),
        'phi-4': ModelInfo(
            name='phi-4',
            vram_required_gb=4.8,
            purpose='specialist_planner'
        )
    }
    
    def __init__(
        self, 
        vram_gb: float = 6.0,
        sse_callback: Optional[Callable] = None
    ):
        self.vram_gb = vram_gb
        self.sse_callback = sse_callback
        self.current_model: Optional[str] = None
        self.switch_overhead_s = 4.0
        self._model_status: Dict[str, ModelStatus] = {
            name: ModelStatus.NOT_LOADED 
            for name in self.MODELS
        }
    
    def ensure_model(self, model_name: str) -> bool:
        """
        Ensure the specified model is loaded.
        Switches models if necessary.
        
        Args:
            model_name: Name of the model to load
        
        Returns:
            True if model is ready, False on error
        """
        # Normalize model name
        model_name = self._normalize_model_name(model_name)
        
        # Check if already loaded
        if self.current_model == model_name:
            logger.debug(f"Model {model_name} already loaded")
            return True
        
        # Check if model exists
        if model_name not in self.MODELS:
            logger.warning(f"Unknown model: {model_name}")
            return False
        
        # Emit switching event
        self._emit_sse('model_switching', {
            'from': self.current_model,
            'to': model_name,
            'estimated_delay_s': self.switch_overhead_s
        })
        
        # Unload current model
        if self.current_model:
            self._unload_model(self.current_model)
        
        # Load new model
        success = self._load_model(model_name)
        
        if success:
            self.current_model = model_name
            self._emit_sse('model_loaded', {'model': model_name})
        else:
            self._emit_sse('model_error', {'model': model_name})
        
        return success
    
    def _normalize_model_name(self, name: str) -> str:
        """Normalize model name to canonical form."""
        aliases = {
            'qwen3': 'qwen3:4b-instruct',
            'qwen': 'qwen3:4b-instruct',
            'phi4': 'phi-4',
        }
        return aliases.get(name.lower(), name)
    
    def _unload_model(self, model_name: str):
        """Unload a model from VRAM."""
        logger.info(f"Unloading model: {model_name}")
        self._model_status[model_name] = ModelStatus.NOT_LOADED
        
        try:
            result = subprocess.run(
                ['ollama', 'stop', model_name],
                capture_output=True,
                timeout=30
            )
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
    
    def _load_model(self, model_name: str) -> bool:
        """Load a model into VRAM."""
        logger.info(f"Loading model: {model_name}")
        self._model_status[model_name] = ModelStatus.LOADING
        
        try:
            result = subprocess.run(
                ['ollama', 'run', model_name, '--keepalive', '10m'],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self._model_status[model_name] = ModelStatus.LOADED
                return True
            else:
                self._model_status[model_name] = ModelStatus.ERROR
                logger.error(f"Model load failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._model_status[model_name] = ModelStatus.ERROR
            logger.error(f"Model load timeout: {model_name}")
            return False
        except Exception as e:
            self._model_status[model_name] = ModelStatus.ERROR
            logger.error(f"Error loading model: {e}")
            return False
    
    def _emit_sse(self, event_type: str, data: Dict[str, Any]):
        """Emit an SSE event."""
        if self.sse_callback:
            self.sse_callback(event_type, data)
        logger.info(f"SSE: {event_type} - {data}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current model status."""
        return {
            'current_model': self.current_model,
            'vram_gb': self.vram_gb,
            'models': {
                name: {
                    'status': status.value,
                    'vram_required': self.MODELS[name].vram_required_gb,
                    'purpose': self.MODELS[name].purpose
                }
                for name, status in self._model_status.items()
            }
        }


# Singleton
_manager_instance = None

def get_model_manager(sse_callback: Callable = None) -> SequentialModelManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SequentialModelManager(sse_callback=sse_callback)
    return _manager_instance
```

#### 1.3.2 File: `backend/ai/task_batcher.py`

```python
"""
Task Batcher - Groups tasks by model to minimize switches.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("valora.task_batcher")


@dataclass
class TaskBatch:
    """A batch of tasks for a single model."""
    model: str
    tasks: List[Any] = field(default_factory=list)


class TaskBatcher:
    """
    Groups tasks by their required model.
    Minimizes model switches during execution.
    """
    
    def __init__(self, default_model: str = 'qwen3:4b-instruct'):
        self.default_model = default_model
    
    def batch_by_model(self, task_graph) -> List[TaskBatch]:
        """
        Group tasks by model, respecting dependencies.
        """
        batches: List[TaskBatch] = []
        current_batch: Optional[TaskBatch] = None
        
        sorted_tasks = task_graph.sorted_by_priority()
        
        for task in sorted_tasks:
            required_model = getattr(task, 'model_hint', None) or self.default_model
            
            if current_batch and current_batch.model == required_model:
                current_batch.tasks.append(task)
            else:
                if current_batch:
                    batches.append(current_batch)
                current_batch = TaskBatch(model=required_model, tasks=[task])
        
        if current_batch and current_batch.tasks:
            batches.append(current_batch)
        
        logger.info(f"Created {len(batches)} batches from {len(sorted_tasks)} tasks")
        return batches
    
    def estimate_switches(self, batches: List[TaskBatch]) -> int:
        """Estimate number of model switches needed."""
        if not batches:
            return 0
        
        switches = 0
        prev_model = None
        
        for batch in batches:
            if prev_model and batch.model != prev_model:
                switches += 1
            prev_model = batch.model
        
        return switches


# Singleton
_batcher_instance = None

def get_task_batcher() -> TaskBatcher:
    global _batcher_instance
    if _batcher_instance is None:
        _batcher_instance = TaskBatcher()
    return _batcher_instance
```

---

## Enhancement 2: Smart Tab System

### 2.1 Architecture Overview

**Integration Point:** Smart Tabs will be displayed inside the existing [`AnalysisPanel.jsx`](src/components/AnalysisPanel.jsx) component.

```
Query Response
    ↓
┌─────────────────────────────────────────────────────┐
│ Smart Tab Renderer (Backend)                        │
│ • Determines tabs based on user tier                │
│ • Filters content (limited/full)                    │
│ • Adds locked tab placeholders                      │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ AnalysisPanel.jsx (Existing Component)              │
│ • Smart Tab section integrated                      │
│                                                     │
│ FREE:                                               │
│ ├── Decision Verdict (limited)                      │
│ ├── Market Snapshot (limited)                       │
│ ├── Risk Analysis 🔒                                │
│ ├── ROI Projection 🔒                               │
│ └── Comparables 🔒                                  │
│                                                     │
│ PRO:                                                │
│ ├── Decision Verdict (full)                         │
│ ├── Market Snapshot (full)                          │
│ ├── Risk Analysis (full)                            │
│ ├── ROI Projection (full)                           │
│ └── Comparables (full)                              │
└─────────────────────────────────────────────────────┘
```

### 2.2 File Structure

```
backend/ai/
└── smart_tab_renderer.py       # NEW: Tab generation

src/components/
├── AnalysisPanel.jsx           # MODIFY: Add Smart Tab section
└── SmartTab.jsx                # NEW: Individual tab component
```

### 2.3 Implementation Details

#### 2.3.1 File: `backend/ai/smart_tab_renderer.py`

```python
"""
Smart Tab Renderer - Generates tiered tab structure for AnalysisPanel.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("valora.ui_tabs")


class TabType(Enum):
    LIMITED = "limited"
    FULL = "full"
    LOCKED = "locked"


@dataclass
class Tab:
    id: str
    title: str
    type: TabType
    content: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""
    order: int = 0


TABS_BY_TIER = {
    'free': [
        {'id': 'decision_verdict', 'type': 'limited', 'order': 1},
        {'id': 'market_snapshot', 'type': 'limited', 'order': 2},
        {'id': 'risk_analysis', 'type': 'locked', 'order': 3},
        {'id': 'roi_projection', 'type': 'locked', 'order': 4},
        {'id': 'comparables', 'type': 'locked', 'order': 5},
    ],
    'pro': [
        {'id': 'decision_verdict', 'type': 'full', 'order': 1},
        {'id': 'market_snapshot', 'type': 'full', 'order': 2},
        {'id': 'risk_analysis', 'type': 'full', 'order': 3},
        {'id': 'roi_projection', 'type': 'full', 'order': 4},
        {'id': 'comparables', 'type': 'full', 'order': 5},
    ]
}

TAB_METADATA = {
    'decision_verdict': {
        'title': 'Decision Verdict',
        'icon': 'gavel',
        'description': 'BUY / HOLD / AVOID recommendation'
    },
    'market_snapshot': {
        'title': 'Market Snapshot',
        'icon': 'chart-line',
        'description': 'Price trends and market dynamics'
    },
    'risk_analysis': {
        'title': 'Risk Analysis',
        'icon': 'exclamation-triangle',
        'description': 'Flood, legal, and market risks'
    },
    'roi_projection': {
        'title': 'ROI Projection',
        'icon': 'percentage',
        'description': '3-year return scenarios'
    },
    'comparables': {
        'title': 'Comparable Properties',
        'icon': 'building',
        'description': 'Similar listings in the area'
    }
}


class UITabRenderer:
    def __init__(self):
        self.tabs_by_tier = TABS_BY_TIER
        self.tab_metadata = TAB_METADATA
    
    def render(
        self, 
        results: Dict[str, Any], 
        user_tier: str,
        verification: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        tab_configs = self.tabs_by_tier.get(user_tier, self.tabs_by_tier['free'])
        rendered_tabs = []
        
        for config in tab_configs:
            tab_id = config['id']
            tab_type = TabType(config['type'])
            metadata = self.tab_metadata.get(tab_id, {})
            
            tab = Tab(
                id=tab_id,
                title=metadata.get('title', tab_id.replace('_', ' ').title()),
                type=tab_type,
                icon=metadata.get('icon', ''),
                order=config['order']
            )
            
            if tab_type == TabType.LOCKED:
                tab.content = self._generate_locked_content(tab_id)
            elif tab_type == TabType.LIMITED:
                tab.content = self._generate_limited_content(tab_id, results)
            else:
                tab.content = self._generate_full_content(tab_id, results, verification)
            
            rendered_tabs.append({
                'id': tab.id,
                'title': tab.title,
                'type': tab.type.value,
                'icon': tab.icon,
                'order': tab.order,
                'content': tab.content
            })
        
        rendered_tabs.sort(key=lambda t: t['order'])
        return rendered_tabs
    
    def _generate_locked_content(self, tab_id: str) -> Dict[str, Any]:
        metadata = self.tab_metadata.get(tab_id, {})
        return {
            'locked': True,
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'upgrade_message': 'Upgrade to Pro to unlock this feature',
            'upgrade_cta': 'Upgrade Now'
        }
    
    def _generate_limited_content(self, tab_id: str, results: Dict) -> Dict[str, Any]:
        if tab_id == 'decision_verdict':
            return {
                'verdict': results.get('verdict', 'HOLD'),
                'confidence': results.get('confidence', 0.7),
                'summary': results.get('summary', '')[:200],
                'limited': True
            }
        elif tab_id == 'market_snapshot':
            return {
                'avg_price': results.get('avg_price'),
                'price_trend': results.get('price_trend'),
                'limited': True
            }
        return {'limited': True}
    
    def _generate_full_content(
        self, 
        tab_id: str, 
        results: Dict, 
        verification: Optional[Dict]
    ) -> Dict[str, Any]:
        content = results.get(tab_id, results)
        if verification:
            content['verification'] = {
                'verified_ratio': verification.get('verified_ratio', 0),
                'status': verification.get('status', 'UNKNOWN')
            }
        return content


_renderer_instance = None

def get_ui_tab_renderer() -> UITabRenderer:
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = UITabRenderer()
    return _renderer_instance
```

#### 2.3.2 File: `src/components/SmartTab.jsx`

```jsx
/**
 * SmartTab - Individual tab component for AnalysisPanel
 * Supports limited, full, and locked states
 */

import React from 'react';

const TAB_ICONS = {
  'gavel': '⚖️',
  'chart-line': '📈',
  'exclamation-triangle': '⚠️',
  'percentage': '%',
  'building': '🏢'
};

export default function SmartTab({ tab, onUpgrade }) {
  const { type, content } = tab;
  
  // Locked tab - show upgrade prompt
  if (type === 'locked') {
    return (
      <div className="smart-tab locked">
        <div className="locked-icon">🔒</div>
        <h3>{content.title}</h3>
        <p className="locked-description">{content.description}</p>
        
        <div className="locked-benefits">
          <h4>Unlock with Pro:</h4>
          <ul>
            <li>✓ Full {content.title.toLowerCase()}</li>
            <li>✓ Detailed analysis & insights</li>
            <li>✓ 500 queries per month</li>
          </ul>
        </div>

        <button className="upgrade-button" onClick={onUpgrade}>
          Upgrade to Pro — $19/month
        </button>
      </div>
    );
  }
  
  // Decision Verdict Tab
  if (tab.id === 'decision_verdict') {
    return (
      <div className="smart-tab verdict">
        <div className={`verdict-badge ${content.verdict?.toLowerCase()}`}>
          {content.verdict}
        </div>
        <p className="verdict-summary">{content.summary}</p>
        {content.limited && (
          <p className="limited-notice">📊 Full analysis available with Pro</p>
        )}
      </div>
    );
  }
  
  // Market Snapshot Tab
  if (tab.id === 'market_snapshot') {
    return (
      <div className="smart-tab market">
        <div className="market-stat">
          <label>Avg Price</label>
          <span>₹{content.avg_price?.toLocaleString()}/sqft</span>
        </div>
        <div className="market-stat">
          <label>Trend</label>
          <span className={content.price_trend > 0 ? 'up' : 'down'}>
            {content.price_trend > 0 ? '↑' : '↓'} {Math.abs(content.price_trend)}%
          </span>
        </div>
      </div>
    );
  }
  
  // Generic content
  return (
    <div className="smart-tab generic">
      <pre>{JSON.stringify(content, null, 2)}</pre>
    </div>
  );
}
```

#### 2.3.3 Integration in `src/components/AnalysisPanel.jsx`

Add Smart Tab section to the existing AnalysisPanel:

```jsx
// Add import at top
import SmartTab from './SmartTab';

// Add inside AnalysisPanel component, after existing content:
{/* Smart Tabs Section */}
{smartTabs && smartTabs.length > 0 && (
  <div className="smart-tabs-section mt-4">
    <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
      <Sparkles className="w-4 h-4 text-yellow-400" />
      Smart Analysis
    </h3>
    
    {/* Tab Headers */}
    <div className="flex gap-1 mb-2 border-b border-slate-700">
      {smartTabs.map((tab, index) => (
        <button
          key={tab.id}
          onClick={() => setActiveSmartTab(index)}
          className={`px-3 py-1.5 text-xs font-medium transition ${
            activeSmartTab === index 
              ? 'text-blue-400 border-b-2 border-blue-400' 
              : 'text-slate-400 hover:text-slate-300'
          } ${tab.type === 'locked' ? 'opacity-75' : ''}`}
        >
          {TAB_ICONS[tab.icon]} {tab.title}
          {tab.type === 'locked' && ' 🔒'}
        </button>
      ))}
    </div>
    
    {/* Tab Content */}
    <div className="bg-slate-800/50 rounded-lg p-3">
      <SmartTab 
        tab={smartTabs[activeSmartTab]} 
        onUpgrade={handleUpgrade}
      />
    </div>
  </div>
)}
```

---

## Enhancement 3: Payment Integration

### 3.1 Architecture Overview

```
User clicks "Upgrade"
    ↓
┌─────────────────────────────────────────────────────┐
│ Frontend: PaymentCheckout.jsx                       │
│ • Calls /api/payments/create-checkout-session       │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: payment_routes.py                          │
│ • Creates Stripe Checkout Session                   │
│ • Returns checkout URL                              │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Stripe Checkout                                     │
│ • User enters payment details                       │
│ • Processes payment                                 │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Webhook: /api/payments/webhook                      │
│ • Receives checkout.session.completed               │
│ • Upgrades user tier in database                    │
└─────────────────────────────────────────────────────┘
```

### 3.2 File Structure

```
backend/
├── routes/
│   └── payment_routes.py        # NEW: Stripe endpoints
└── services/
    └── stripe_service.py        # NEW: Stripe integration
```

### 3.3 Implementation Details

#### 3.3.1 File: `backend/routes/payment_routes.py`

```python
"""
Payment Routes - Stripe integration endpoints.
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("valora.payments")

router = APIRouter(prefix="/api/payments", tags=["payments"])

STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
PRO_MONTHLY_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "price_pro_monthly")


class CreateCheckoutRequest(BaseModel):
    user_id: str
    tier: str = "pro"


@router.post("/create-checkout-session")
async def create_checkout_session(request: CreateCheckoutRequest):
    """Create a Stripe Checkout session for Pro subscription."""
    import stripe
    stripe.api_key = STRIPE_API_KEY
    
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": PRO_MONTHLY_PRICE_ID,
                "quantity": 1
            }],
            metadata={
                "user_id": request.user_id,
                "tier": request.tier
            },
            success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/payment/cancel"
        )
        
        logger.info(f"Created checkout session for user {request.user_id}")
        return {"url": session.url, "session_id": session.id}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    import stripe
    stripe.api_key = STRIPE_API_KEY
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_complete(session)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_cancelled(subscription)
    
    return {"status": "success"}


async def handle_checkout_complete(session: dict):
    """Handle successful checkout."""
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier", "pro")
    
    logger.info(f"Checkout complete for user {user_id}, tier {tier}")
    
    from ai.credits_rate_limiter import CreditsRateLimiter
    limiter = CreditsRateLimiter()
    limiter.update_tier(user_id, tier)


async def handle_subscription_cancelled(subscription: dict):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    logger.info(f"Subscription cancelled for customer {customer_id}")


@router.get("/subscription/{user_id}")
async def get_subscription(user_id: str):
    """Get subscription status for a user."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    status = limiter.get_user_status(user_id)
    
    return {
        "user_id": user_id,
        "tier": status.get("tier", "free"),
        "credits": status.get("remaining_credits", 0)
    }
```

#### 3.3.2 File: `backend/services/stripe_service.py`

```python
"""
Stripe Service - Helper functions for Stripe operations.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("valora.stripe")

import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


class StripeService:
    def __init__(self):
        self.is_configured = bool(stripe.api_key)
    
    def create_customer(self, email: str, user_id: str) -> Optional[str]:
        if not self.is_configured:
            return None
        
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id}
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            return None
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        if not self.is_configured:
            return False
        
        try:
            stripe.Subscription.delete(subscription_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False


_service_instance = None

def get_stripe_service() -> StripeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = StripeService()
    return _service_instance
```

### 3.4 Environment Variables

Add to `.env`:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
FRONTEND_URL=http://localhost:5173
```

---

## Enhancement 4: Credit System (Cursor/KiloCode Style)

### 4.1 Credit Plans

| Plan | Monthly Price | Credits/Month | Features |
|------|---------------|---------------|----------|
| **Free** | $0 | 50 credits | Basic queries, limited tabs |
| **Pro** | $19/month | 500 credits + rollover | Full tabs, priority support |
| **Credit Top-ups** | Pay-as-you-go | Buy credits anytime | Never expire |

### 4.2 Credit Top-up Packages

| Package | Price | Credits | Bonus |
|---------|-------|---------|-------|
| **Starter** | $5 | 100 credits | — |
| **Standard** | $10 | 250 credits | +25 bonus |
| **Power** | $25 | 700 credits | +100 bonus |

### 4.3 Credit Costs - Simple LLM-Based Pricing

```python
# Only 2 pricing tiers based on LLM type
LLM_CREDIT_COSTS = {
    'local': 2,    # Local Ollama (qwen, phi) - 2 credits per LLM call
    'cloud': 5,    # Cloud (deepseek, openrouter) - 5 credits per LLM call
}

# Local models (all cost same - 2 credits)
LOCAL_MODELS = ['qwen3:4b-instruct', 'qwen3:8b', 'phi-4', 'valora-ai-mini']

# Cloud models (all cost same - 5 credits)
CLOUD_MODELS = ['deepseek-chat', 'deepseek-reasoner', 'openrouter/*']

def get_llm_type(model: str) -> str:
    """Determine if model is local or cloud."""
    if any(local in model.lower() for local in ['qwen', 'phi', 'valora']):
        return 'local'
    return 'cloud'

def calculate_credit_cost(model: str) -> int:
    """Calculate credits based on LLM type only."""
    llm_type = get_llm_type(model)
    return LLM_CREDIT_COSTS[llm_type]
```

### 4.4 Model Usage Flow

```
User Query
    ↓
┌─────────────────────────────────────────────────────┐
│ Task Orchestrator                                   │
│ • Decomposes query into tasks                       │
│ • Each task may need LLM call                       │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ For Each LLM Call:                                  │
│                                                     │
│ LOCAL (qwen/phi) → 2 credits                        │
│ • Default for most queries                          │
│ • Runs on local Ollama                              │
│                                                     │
│ CLOUD (deepseek) → 5 credits                        │
│ • Only when local insufficient                      │
│ • User must opt-in                                  │
└─────────────────────────────────────────────────────┘
```

### 4.5 Example Credit Usage

| Query | LLM Calls | Type | Total Credits |
|-------|-----------|------|---------------|
| "Find 2BHK in Whitefield" | 1 | local | 2 |
| "Compare Whitefield vs Koramangala" | 2 | local | 4 |
| "ROI for investment in HSR" | 3 | local | 6 |
| "Legal issues with this property" | 2 | cloud | 10 |
| "Complex valuation" | 2 local + 1 cloud | mixed | 9 |

### 4.6 Implementation in Task Orchestrator

```python
# In task_orchestrator.py or multi_stage_executor.py

class CreditTrackingExecutor:
    """Tracks LLM usage and deducts credits."""
    
    def __init__(self, user_id: str, credits_limiter):
        self.user_id = user_id
        self.credits_limiter = credits_limiter
        self.total_credits_used = 0
        self.llm_calls = []
    
    async def execute_with_llm(self, task, model: str) -> dict:
        """Execute task with LLM, tracking credit usage."""
        # Calculate credits
        llm_type = 'local' if any(m in model for m in ['qwen', 'phi']) else 'cloud'
        credits = LLM_CREDIT_COSTS[llm_type]
        
        # Check if user has enough credits
        balance = self.credits_limiter.get_balance(self.user_id)
        if balance['total_available'] < credits:
            raise InsufficientCreditsError(f"Need {credits} credits, have {balance['total_available']}")
        
        # Execute LLM call
        result = await self._call_llm(task, model)
        
        # Deduct credits
        self.credits_limiter.use_credits(
            user_id=self.user_id,
            amount=credits,
            action=f'llm_{llm_type}',
            metadata={'model': model, 'task': task.type}
        )
        
        self.total_credits_used += credits
        self.llm_calls.append({
            'model': model,
            'type': llm_type,
            'credits': credits,
            'task': task.type
        })
        
        return result
    
    def get_usage_summary(self) -> dict:
        """Get summary of LLM usage for this query."""
        return {
            'total_credits': self.total_credits_used,
            'llm_calls': len(self.llm_calls),
            'breakdown': self.llm_calls
        }
```

### 4.4 Implementation Details

#### 4.4.1 Update `backend/ai/credits_rate_limiter.py`

```python
class CreditsRateLimiter:
    """
    Credit system with monthly allowances + top-ups.
    Similar to Cursor/Windsurf/KiloCode model.
    """
    
    # Monthly credit allowances
    MONTHLY_CREDITS = {
        'free': 50,
        'pro': 500,
    }
    
    # Credit top-up packages
    TOP_UP_PACKAGES = {
        'starter': {'price': 5, 'credits': 100, 'bonus': 0},
        'standard': {'price': 10, 'credits': 250, 'bonus': 25},
        'power': {'price': 25, 'credits': 700, 'bonus': 100},
        'unlimited': {'price': 50, 'credits': 2000, 'bonus': 500},
    }
    
    # Credit costs per action
    ACTION_COSTS = {
        'basic_query': 1,
        'analysis_query': 2,
        'deep_analysis': 5,
        'specialist_query': 10,
        'map_action': 1,
    }
    
    def get_balance(self, user_id: str) -> dict:
        """Get user's credit balance."""
        return {
            'monthly_credits': self._get_monthly_credits(user_id),
            'top_up_credits': self._get_top_up_credits(user_id),
            'total_available': self._get_total_credits(user_id),
            'next_reset': self._get_next_reset_date(user_id)
        }
    
    def use_credits(self, user_id: str, action: str, amount: int = 1) -> bool:
        """
        Use credits for an action.
        Priority: Top-up credits first, then monthly credits.
        """
        cost = self.ACTION_COSTS.get(action, 1) * amount
        balance = self.get_balance(user_id)
        
        if balance['total_available'] < cost:
            return False  # Insufficient credits
        
        # Deduct from top-up first (they never expire)
        if balance['top_up_credits'] >= cost:
            self._deduct_top_up(user_id, cost)
        else:
            # Deduct remaining from monthly
            remaining = cost - balance['top_up_credits']
            self._deduct_top_up(user_id, balance['top_up_credits'])
            self._deduct_monthly(user_id, remaining)
        
        return True
    
    def add_top_up(self, user_id: str, package: str) -> dict:
        """Add credits from a top-up purchase."""
        pkg = self.TOP_UP_PACKAGES.get(package)
        if not pkg:
            return {'success': False, 'error': 'Invalid package'}
        
        total_credits = pkg['credits'] + pkg['bonus']
        self._add_top_up_credits(user_id, total_credits)
        
        return {
            'success': True,
            'credits_added': total_credits,
            'new_balance': self.get_balance(user_id)
        }
    
    def reset_monthly_credits(self, user_id: str):
        """Reset monthly credits (called on billing date)."""
        tier = self._get_user_tier(user_id)
        monthly = self.MONTHLY_CREDITS.get(tier, 50)
        
        # Pro users: rollover up to 2 months worth
        if tier == 'pro':
            current = self._get_monthly_credits(user_id)
            rollover = min(current, monthly * 2)  # Max 2 months
            self._set_monthly_credits(user_id, monthly + rollover)
        else:
            self._set_monthly_credits(user_id, monthly)
```

#### 4.4.2 Add Top-up Routes to `backend/routes/payment_routes.py`

```python
@router.post("/top-up")
async def purchase_top_up(request: TopUpRequest):
    """Purchase credit top-up package."""
    import stripe
    stripe.api_key = STRIPE_API_KEY
    
    package = TOP_UP_PACKAGES.get(request.package)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    try:
        # Create one-time payment
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Valora Credits - {request.package.title()}",
                        "description": f"{package['credits'] + package['bonus']} credits"
                    },
                    "unit_amount": package['price'] * 100
                },
                "quantity": 1
            }],
            metadata={
                "user_id": request.user_id,
                "type": "top_up",
                "package": request.package
            },
            success_url=f"{FRONTEND_URL}/payment/success",
            cancel_url=f"{FRONTEND_URL}/payment/cancel"
        )
        
        return {"url": session.url}
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/balance/{user_id}")
async def get_credit_balance(user_id: str):
    """Get user's credit balance."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    balance = limiter.get_balance(user_id)
    
    return balance
```

#### 4.4.3 Frontend Credit Display Component

```jsx
// src/components/CreditBalance.jsx
export default function CreditBalance({ balance, onTopUp }) {
  return (
    <div className="credit-balance">
      <div className="balance-display">
        <span className="total">{balance.total_available}</span>
        <span className="label">credits</span>
      </div>
      
      <div className="balance-breakdown text-xs text-slate-400">
        <div>Monthly: {balance.monthly_credits}</div>
        <div>Top-up: {balance.top_up_credits}</div>
        <div>Resets: {balance.next_reset}</div>
      </div>
      
      <button onClick={onTopUp} className="top-up-btn">
        Buy Credits
      </button>
    </div>
  );
}
```

---

## Summary

### Credit System (Simple LLM-Based Pricing)

| Plan | Price | Credits | Features |
|------|-------|---------|----------|
| **Free** | $0 | 50/month | Local LLM only, limited tabs |
| **Pro** | $19/month | 500/month + rollover | All LLMs, cloud opt-in |
| **Top-ups** | $5-$25 | 100-800 credits | Never expire |

### LLM Credit Costs

| LLM Type | Credits | Models |
|----------|---------|--------|
| **Local** | 2 | qwen, phi (Ollama) |
| **Cloud** | 5 | deepseek, openrouter |

### Example Usage

| Query | LLM Calls | Credits |
|-------|-----------|---------|
| "Find 2BHK" | 1 local | 2 |
| "Compare areas" | 2 local | 4 |
| "ROI analysis" | 3 local | 6 |
| "Legal issues" | 2 cloud | 10 |

### New Files (7)

| File | Purpose |
|------|---------|
| `backend/ai/sequential_model_manager.py` | Model lifecycle |
| `backend/ai/task_batcher.py` | Task batching |
| `backend/ai/smart_tab_renderer.py` | Smart Tab generation |
| `backend/routes/payment_routes.py` | Stripe endpoints + top-ups |
| `backend/services/stripe_service.py` | Stripe helper |
| `src/components/SmartTab.jsx` | Individual tab component |
| `src/components/CreditBalance.jsx` | Credit display + top-up |

### Modified Files (3)

| File | Changes |
|------|---------|
| `backend/routes/chat_routes.py` | Add SSE events, smart tab rendering |
| `backend/ai/credits_rate_limiter.py` | Add top-ups, rollover, balance tracking |
| `src/components/AnalysisPanel.jsx` | Add Smart Tab section |

---

*Implementation Plan v2.0 - February 16, 2026*
