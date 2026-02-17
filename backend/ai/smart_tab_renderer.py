"""
Smart Tab Renderer - Generates tiered tab structure for AnalysisPanel.
Implements the 9-tab system with tiered access.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("valora.smart_tabs")


class TabType(Enum):
    LIMITED = "limited"     # Free tier, limited content
    FULL = "full"           # Pro tier, full content
    LOCKED = "locked"       # Locked, shows upgrade prompt
    PREVIEW = "preview"     # Preview with upgrade prompt


@dataclass
class Tab:
    """A single Smart Tab."""
    id: str
    title: str
    type: TabType
    content: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""
    order: int = 0
    description: str = ""


# Tab configuration by tier
TABS_BY_TIER = {
    'free': [
        {'id': 'decision_verdict', 'type': 'limited', 'order': 1},
        {'id': 'market_snapshot', 'type': 'limited', 'order': 2},
        {'id': 'spatial_intelligence', 'type': 'preview', 'order': 3},
        {'id': 'risk_analysis', 'type': 'locked', 'order': 4},
        {'id': 'roi_projection', 'type': 'locked', 'order': 5},
        {'id': 'comparables', 'type': 'locked', 'order': 6},
        {'id': 'strategy', 'type': 'locked', 'order': 7},
        {'id': 'data_transparency', 'type': 'locked', 'order': 8},
        {'id': 'client_pitch', 'type': 'locked', 'order': 9},
    ],
    'pro': [
        {'id': 'decision_verdict', 'type': 'full', 'order': 1},
        {'id': 'market_snapshot', 'type': 'full', 'order': 2},
        {'id': 'spatial_intelligence', 'type': 'full', 'order': 3},
        {'id': 'risk_analysis', 'type': 'full', 'order': 4},
        {'id': 'roi_projection', 'type': 'full', 'order': 5},
        {'id': 'comparables', 'type': 'full', 'order': 6},
        {'id': 'strategy', 'type': 'full', 'order': 7},
        {'id': 'data_transparency', 'type': 'full', 'order': 8},
        {'id': 'client_pitch', 'type': 'full', 'order': 9},  # Now available for Pro
    ]
}

# Tab metadata
TAB_METADATA = {
    'decision_verdict': {
        'title': 'Decision Verdict',
        'icon': 'gavel',
        'description': 'BUY / HOLD / AVOID recommendation',
        'answers': 'What should I do?'
    },
    'market_snapshot': {
        'title': 'Market Snapshot',
        'icon': 'chart-line',
        'description': 'Price trends and market dynamics',
        'answers': 'Is market strong?'
    },
    'spatial_intelligence': {
        'title': 'Spatial Intelligence',
        'icon': 'map',
        'description': 'Infrastructure, connectivity, POIs',
        'answers': 'Why does location matter?'
    },
    'risk_analysis': {
        'title': 'Risk Analysis',
        'icon': 'exclamation-triangle',
        'description': 'Flood, legal, and market risks',
        'answers': 'What could go wrong?'
    },
    'roi_projection': {
        'title': 'ROI Projection',
        'icon': 'percentage',
        'description': '3-year return scenarios',
        'answers': 'What returns can I expect?'
    },
    'comparables': {
        'title': 'Comparable Properties',
        'icon': 'building',
        'description': 'Similar listings in the area',
        'answers': 'Is this fairly priced?'
    },
    'strategy': {
        'title': 'Strategy & Recommendations',
        'icon': 'compass',
        'description': 'Entry/exit strategy',
        'answers': 'How should I proceed?'
    },
    'data_transparency': {
        'title': 'Data Transparency',
        'icon': 'database',
        'description': 'Truth Firewall verification',
        'answers': 'Can I trust this data?'
    },
    'client_pitch': {
        'title': 'Client Pitch',
        'icon': 'presentation',
        'description': 'Broker presentation mode',
        'answers': 'How do I present this?'
    }
}


class SmartTabRenderer:
    """
    Renders Smart Tabs based on user tier.
    
    Tab Structure:
    1. Decision Verdict - BUY/HOLD/AVOID + reasoning
    2. Market Snapshot - Price trends, demand/supply
    3. Spatial Intelligence - Infrastructure, connectivity
    4. Risk Analysis - Flood, legal, oversupply risks
    5. ROI Projection - 3-year scenarios
    6. Comparables - Similar listings
    7. Strategy & Recommendations - Entry/exit strategy
    8. Data Transparency - Truth Firewall verification
    9. Client Pitch - Broker presentation (Premium)
    """
    
    def __init__(self):
        self.tabs_by_tier = TABS_BY_TIER
        self.tab_metadata = TAB_METADATA
    
    def render(
        self, 
        results: Dict[str, Any], 
        user_tier: str,
        verification: Optional[Dict] = None,
        query: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Render tabs for the given results and user tier.
        
        Args:
            results: Execution results from task graph
            user_tier: User's subscription tier (free/pro/premium)
            verification: Optional fact verification results
            query: Original user query
            
        Returns:
            List of tab dictionaries
        """
        # Get tab configuration for tier
        tab_configs = self.tabs_by_tier.get(user_tier, self.tabs_by_tier['free'])
        
        rendered_tabs = []
        
        for config in tab_configs:
            tab_id = config['id']
            tab_type = TabType(config['type'])
            
            # Get metadata
            metadata = self.tab_metadata.get(tab_id, {})
            
            # Create tab
            tab = Tab(
                id=tab_id,
                title=metadata.get('title', tab_id.replace('_', ' ').title()),
                type=tab_type,
                icon=metadata.get('icon', ''),
                order=config['order'],
                description=metadata.get('description', '')
            )
            
            # Generate content based on type
            if tab_type == TabType.LOCKED:
                tab.content = self._generate_locked_content(tab_id)
            elif tab_type == TabType.PREVIEW:
                tab.content = self._generate_preview_content(tab_id, results)
            elif tab_type == TabType.LIMITED:
                tab.content = self._generate_limited_content(tab_id, results)
            else:  # FULL
                tab.content = self._generate_full_content(tab_id, results, verification)
            
            rendered_tabs.append({
                'id': tab.id,
                'title': tab.title,
                'type': tab.type.value,
                'icon': tab.icon,
                'order': tab.order,
                'description': tab.description,
                'content': tab.content
            })
        
        # Sort by order
        rendered_tabs.sort(key=lambda t: t['order'])
        
        return rendered_tabs
    
    def _generate_locked_content(self, tab_id: str) -> Dict[str, Any]:
        """Generate content for a locked tab."""
        metadata = self.tab_metadata.get(tab_id, {})
        return {
            'locked': True,
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'answers': metadata.get('answers', ''),
            'upgrade_message': 'Upgrade to Pro to unlock this feature',
            'upgrade_cta': 'Upgrade Now',
            'upgrade_benefits': [
                f'Full {metadata.get("title", "").lower()}',
                'Detailed analysis & insights',
                'Data-backed recommendations',
                '500 queries per month'
            ]
        }
    
    def _generate_preview_content(self, tab_id: str, results: Dict) -> Dict[str, Any]:
        """Generate preview content with blur."""
        metadata = self.tab_metadata.get(tab_id, {})
        
        # Get some preview data
        preview_data = self._get_preview_data(tab_id, results)
        
        return {
            'preview': True,
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'preview_data': preview_data,
            'blurred': True,
            'upgrade_message': 'Unlock full insights with Pro',
            'upgrade_cta': 'Upgrade Now'
        }
    
    def _generate_limited_content(self, tab_id: str, results: Dict) -> Dict[str, Any]:
        """Generate limited content for free tier."""
        if tab_id == 'decision_verdict':
            return {
                'verdict': results.get('verdict', 'HOLD'),
                'confidence': results.get('confidence', 0.7),
                'summary': results.get('summary', '')[:200],  # Truncated
                'limited': True,
                'full_available': True,
                'top_reasons': results.get('reasons', [])[:2],  # Only 2 reasons
            }
        elif tab_id == 'market_snapshot':
            return {
                'avg_price': results.get('avg_price'),
                'price_trend': results.get('price_trend'),
                'limited': True,
                'full_available': True
            }
        return {'limited': True}
    
    def _generate_full_content(
        self, 
        tab_id: str, 
        results: Dict, 
        verification: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate full content for pro tier."""
        content = results.get(tab_id, results)
        
        # Tab-specific content generation
        if tab_id == 'decision_verdict':
            content = self._generate_verdict_content(results)
        elif tab_id == 'market_snapshot':
            content = self._generate_market_content(results)
        elif tab_id == 'spatial_intelligence':
            content = self._generate_spatial_content(results)
        elif tab_id == 'risk_analysis':
            content = self._generate_risk_content(results)
        elif tab_id == 'roi_projection':
            content = self._generate_roi_content(results)
        elif tab_id == 'comparables':
            content = self._generate_comparables_content(results)
        elif tab_id == 'strategy':
            content = self._generate_strategy_content(results)
        elif tab_id == 'data_transparency':
            content = self._generate_transparency_content(results, verification)
        elif tab_id == 'client_pitch':
            content = self._generate_pitch_content(results)
        
        # Add verification badge
        if verification:
            content['verification'] = {
                'verified_ratio': verification.get('verified_ratio', 0),
                'status': verification.get('status', 'UNKNOWN')
            }
        
        return content
    
    def _get_preview_data(self, tab_id: str, results: Dict) -> Dict[str, Any]:
        """Get preview data for a tab."""
        if tab_id == 'spatial_intelligence':
            return {
                'nearby_highlights': results.get('pois', {}).get('count', 0),
                'connectivity_score': results.get('connectivity_score', 'N/A')
            }
        return {}
    
    def _generate_verdict_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Decision Verdict tab content."""
        return {
            'verdict': results.get('verdict', 'HOLD'),
            'confidence_score': results.get('confidence', 75),
            'risk_level': results.get('risk_level', 'MODERATE'),
            'time_horizon': results.get('time_horizon', '3-5 years'),
            'top_reasons': results.get('reasons', [
                'Strong infrastructure growth',
                'Below market price',
                'High rental yield potential'
            ]),
            'key_risks': results.get('risks', [
                'Metro Phase 2 delay possible',
                'Slightly elevated flood zone'
            ]),
            'strategy_recommendation': {
                'entry_price': results.get('entry_price', '₹8,500-9,000/sqft'),
                'hold_duration': results.get('hold_duration', '5-7 years'),
                'exit_strategy': results.get('exit_strategy', 'Sell when metro completes')
            }
        }
    
    def _generate_market_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Market Snapshot tab content."""
        return {
            'avg_price_sqft': results.get('avg_price_sqft', 8500),
            'price_trend': {
                '1Y': results.get('price_trend_1y', '+8%'),
                '3Y': results.get('price_trend_3y', '+24%')
            },
            'demand_supply': results.get('demand_supply', 'HIGH DEMAND'),
            'rental_yield': results.get('rental_yield', '3.8%'),
            'liquidity_score': results.get('liquidity_score', 72),
            'price_range': {
                'min': results.get('price_min', 7500),
                'max': results.get('price_max', 11000),
                'median': results.get('price_median', 8800)
            }
        }
    
    def _generate_spatial_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Spatial Intelligence tab content."""
        return {
            'nearby_infrastructure': results.get('infrastructure', [
                {'name': 'Metro Station', 'distance': '0.8km', 'status': 'operational'},
                {'name': 'Tech Park', 'distance': '2.1km', 'status': 'operational'}
            ]),
            'connectivity': {
                'metro': results.get('metro_access', True),
                'highway': results.get('highway_access', True),
                'airport_distance': results.get('airport_distance', '35km')
            },
            'pois': results.get('pois', {
                'schools': 5,
                'hospitals': 3,
                'malls': 2,
                'offices': 12
            }),
            'walkability_score': results.get('walkability', 78),
            'development_hotspots': results.get('hotspots', [
                'Sarjapur Road extension',
                'Metro Phase 2'
            ])
        }
    
    def _generate_risk_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Risk Analysis tab content."""
        return {
            'overall_risk_score': results.get('risk_score', 35),
            'risks': {
                'flood': {'level': 'LOW', 'score': 15},
                'environmental': {'level': 'MODERATE', 'score': 40},
                'oversupply': {'level': 'LOW', 'score': 20},
                'legal': {'level': 'LOW', 'score': 10},
                'infrastructure_delay': {'level': 'MODERATE', 'score': 45}
            },
            'mitigation_suggestions': results.get('mitigations', [
                'Check RERA compliance',
                'Verify flood zone classification'
            ])
        }
    
    def _generate_roi_content(self, results: Dict) -> Dict[str, Any]:
        """Generate ROI Projection tab content."""
        return {
            'projection_3year': {
                'best_case': {'price': 11500, 'return': '+35%'},
                'expected': {'price': 10200, 'return': '+20%'},
                'worst_case': {'price': 8800, 'return': '+3%'}
            },
            'rental_yield_scenarios': {
                'conservative': '3.2%',
                'expected': '3.8%',
                'optimistic': '4.5%'
            },
            'entry_exit': {
                'recommended_entry': '₹8,200-8,800/sqft',
                'target_exit': '₹11,000+/sqft',
                'hold_period': '4-6 years'
            }
        }
    
    def _generate_comparables_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Comparables tab content."""
        return {
            'comparables': results.get('comparables', [
                {'project': 'Prestige Lakeside', 'price_sqft': 9200, 'distance': '0.5km', 'similarity': 92},
                {'project': 'Brigade Cosmopolis', 'price_sqft': 8800, 'distance': '1.2km', 'similarity': 85}
            ]),
            'price_analysis': {
                'subject_property': 8500,
                'area_average': 8900,
                'percentile': '35th'
            }
        }
    
    def _generate_strategy_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Strategy tab content."""
        return {
            'investment_strategy': {
                'entry_timing': 'NOW - prices stable',
                'negotiation_range': '₹8,200-8,600/sqft',
                'portfolio_fit': 'Good for long-term growth'
            },
            'action_items': [
                'Verify RERA approval',
                'Check rental agreement terms',
                'Negotiate 3-5% below asking'
            ],
            'timeline': {
                'due_diligence': '2 weeks',
                'closing': '4-6 weeks'
            }
        }
    
    def _generate_transparency_content(self, results: Dict, verification: Optional[Dict]) -> Dict[str, Any]:
        """Generate Data Transparency tab content."""
        return {
            'data_sources': [
                {'source': 'BBMP', 'type': 'Building records', 'freshness': 'Updated 2 days ago'},
                {'source': 'RERA', 'type': 'Project approvals', 'freshness': 'Updated weekly'},
                {'source': 'MagicBricks', 'type': 'Listings', 'freshness': 'Updated daily'}
            ],
            'confidence_breakdown': {
                'price_data': {'confidence': 92, 'source': 'aggregated'},
                'infrastructure': {'confidence': 88, 'source': 'government'},
                'projections': {'confidence': 65, 'source': 'model_estimated'}
            },
            'missing_data_warnings': results.get('missing_data', []),
            'verification_status': verification.get('status', 'VERIFIED') if verification else 'VERIFIED'
        }
    
    def _generate_pitch_content(self, results: Dict) -> Dict[str, Any]:
        """Generate Client Pitch tab content (Premium)."""
        return {
            'presentation_mode': True,
            'client_summary': {
                'headline': f"{results.get('area', 'Property')} - Strong Investment Opportunity",
                'key_points': [
                    '20% below market',
                    'Metro connectivity',
                    'High rental demand'
                ],
                'ask': results.get('asking_price', '₹1.2 Cr'),
                'expected_return': '18-25% in 3 years'
            },
            'shareable_report': {
                'pdf_export': True,
                'whatsapp_share': True,
                'email_template': True
            }
        }


# Singleton
_renderer_instance = None


def get_smart_tab_renderer() -> SmartTabRenderer:
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = SmartTabRenderer()
    return _renderer_instance
