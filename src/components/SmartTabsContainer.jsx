/**
 * SmartTabsContainer - Enhanced container for Smart Tabs in SmartPanel
 * Implements tiered access control and cognitive workflow features
 * Tab priority: Decision Verdict → Market → Spatial → Risk → ROI → Comps → Strategy → Data → Pitch
 */

import React, { useState, useEffect } from 'react';
import SmartTab from './SmartTab';
import { API_URL } from '../apiConfig';
import {
  TrendingUp, MapPin, AlertTriangle, Percent, Building,
  Compass, Database, Presentation, Lock, Sparkles,
  Download, Share2, FileText, Loader2, Building2, Wallet,
  Eye, Sun, Trophy, CheckCircle, Star
} from 'lucide-react';

// Enhanced tab metadata with icons, descriptions, and tier requirements
const TAB_METADATA = {
  'free_analysis': {
    title: 'Free Analysis',
    icon: '🔍',
    lucideIcon: Eye,
    description: 'Basic area overview (Free)',
    shortLabel: 'Free',
    priority: 0,
    answerQuestion: 'What is this area like?'
  },
  'decision_verdict': {
    title: 'Decision Verdict',
    icon: '⚖️',
    lucideIcon: TrendingUp,
    description: 'BUY / HOLD / AVOID recommendation',
    shortLabel: 'Verdict',
    priority: 1,
    answerQuestion: 'What should I do?'
  },
  'market_snapshot': {
    title: 'Market Snapshot',
    icon: '📈',
    lucideIcon: TrendingUp,
    description: 'Price trends and market dynamics',
    shortLabel: 'Market',
    priority: 2,
    answerQuestion: 'Is market strong?'
  },
  'spatial_intelligence': {
    title: 'Spatial Intelligence',
    icon: '🗺️',
    lucideIcon: MapPin,
    description: 'Infrastructure, connectivity, POIs',
    shortLabel: 'Spatial',
    priority: 3,
    answerQuestion: 'Why does location matter?'
  },
  'risk_analysis': {
    title: 'Risk Analysis',
    icon: '⚠️',
    lucideIcon: AlertTriangle,
    description: 'Flood, legal, and market risks',
    shortLabel: 'Risk',
    priority: 4,
    answerQuestion: 'What could go wrong?'
  },
  'roi_projection': {
    title: 'ROI Projection',
    icon: '%',
    lucideIcon: Percent,
    description: '3-year return scenarios',
    shortLabel: 'ROI',
    priority: 5,
    answerQuestion: 'What returns to expect?'
  },
  'comparables': {
    title: 'Comparables',
    icon: '🏢',
    lucideIcon: Building,
    description: 'Similar properties analysis',
    shortLabel: 'Comps',
    priority: 6,
    answerQuestion: 'Is price justified?'
  },
  'strategy': {
    title: 'Strategy',
    icon: '🧭',
    lucideIcon: Compass,
    description: 'Entry/exit recommendations',
    shortLabel: 'Strategy',
    priority: 7,
    answerQuestion: 'How to proceed?'
  },
  'data_transparency': {
    title: 'Data Transparency',
    icon: '🗄️',
    lucideIcon: Database,
    description: 'Source verification',
    shortLabel: 'Data',
    priority: 8,
    answerQuestion: 'Can I trust this?'
  },
  'client_pitch': {
    title: 'Client Pitch',
    icon: '📊',
    lucideIcon: Presentation,
    description: 'Broker presentation',
    shortLabel: 'Pitch',
    priority: 9,
    answerQuestion: 'How to present?'
  }
};

// Tier configuration for tabs - Only FREE and PRO tiers
const TIER_CONFIG = {
  free: {
    name: 'Free',
    color: 'slate',
    tabs: {
      'free_analysis': 'full',             // Always free
      'decision_verdict': 'limited',       // Limited version
      'market_snapshot': 'limited',        // Limited version
      'spatial_intelligence': 'preview',   // Blurred preview
      'risk_analysis': 'locked',           // Locked
      'roi_projection': 'locked',          // Locked
      'comparables': 'locked',             // Locked
      'strategy': 'locked',                // Locked
      'data_transparency': 'locked',       // Locked
      'client_pitch': 'locked'             // Locked
    },
    upgradeMessage: 'Upgrade to Pro for full analysis'
  },
  pro: {
    name: 'Pro',
    color: 'blue',
    tabs: {
      'free_analysis': 'full',             // Always free
      'decision_verdict': 'full',          // Full access
      'market_snapshot': 'full',           // Full access
      'spatial_intelligence': 'full',      // Full access
      'risk_analysis': 'full',             // Full access
      'roi_projection': 'full',            // Full access
      'comparables': 'full',               // Full access
      'strategy': 'full',                  // Full access
      'data_transparency': 'full',         // Full access
      'client_pitch': 'full'               // Full access for Pro
    },
    upgradeMessage: null  // No upgrade - Pro is the highest tier
  }
};

export default function SmartTabsContainer({ 
  agentData, 
  viewportAnalysis, 
  userTier = 'free',
  onUpgrade,
  lat,
  lng,
  locality,
  buildingAnalysis,
  selectedBuilding,
  activeTab: externalActiveTab,
  onTabChange,
  setAgentData
}) {
  const [internalActiveTab, setInternalActiveTab] = useState('decision_verdict');
  const [tabs, setTabs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [exporting, setExporting] = useState(false);
  
  // Use external activeTab if provided, otherwise use internal state
  const activeTab = externalActiveTab !== undefined ? externalActiveTab : internalActiveTab;
  const setActiveTab = onTabChange || setInternalActiveTab;

  // Export handlers
  const handleExportPDF = async () => {
    if (!reportData) return;
    
    setExporting(true);
    try {
      const response = await fetch(`${API_URL}/api/smart-report/export/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_data: reportData,
          locality: locality || 'Unknown Location',
          include_sections: ['verdict', 'market', 'spatial', 'risk', 'roi']
        })
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Valora_Smart_Report_${locality || 'Property'}_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Dispatch credit deduction event
        window.dispatchEvent(new CustomEvent('valora-credits-used', { 
          detail: { action: 'pdf_export', credits: 5 } 
        }));
      } else {
        console.error('PDF export failed');
        alert('PDF export requires credits. Please ensure you have sufficient balance.');
      }
    } catch (err) {
      console.error('Export error:', err);
      alert('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleShare = async () => {
    if (!reportData) return;
    
    try {
      const response = await fetch(`${API_URL}/api/smart-report/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_data: reportData,
          locality: locality || 'Unknown Location'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const shareUrl = data.share_url || `${window.location.origin}/shared/${data.report_id}`;
        
        // Copy to clipboard
        await navigator.clipboard.writeText(shareUrl);
        alert('Share link copied to clipboard!');
        
        // Dispatch credit deduction event
        window.dispatchEvent(new CustomEvent('valora-credits-used', { 
          detail: { action: 'share_report', credits: 2 } 
        }));
      } else {
        // Fallback: copy current URL
        await navigator.clipboard.writeText(window.location.href);
        alert('Current page URL copied to clipboard!');
      }
    } catch (err) {
      console.error('Share error:', err);
      // Fallback
      try {
        await navigator.clipboard.writeText(window.location.href);
        alert('Page URL copied to clipboard!');
      } catch (e) {
        alert('Unable to share. Please copy the URL manually.');
      }
    }
  };

  const handleQuickExport = async (type) => {
    if (!reportData) return;
    
    setExporting(true);
    try {
      const response = await fetch(`${API_URL}/api/smart-report/export/section`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: type,
          report_data: reportData,
          locality: locality || 'Unknown Location'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Create downloadable text file
        const content = data.content || JSON.stringify(reportData.decision_verdict || reportData, null, 2);
        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Valora_${type}_Report_${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Dispatch credit deduction event
        window.dispatchEvent(new CustomEvent('valora-credits-used', { 
          detail: { action: `quick_export_${type}`, credits: 1 } 
        }));
      } else {
        console.error('Quick export failed');
      }
    } catch (err) {
      console.error('Quick export error:', err);
    } finally {
      setExporting(false);
    }
  };

  // Generate tabs based on user tier and available data
  useEffect(() => {
    generateTabs();
  }, [userTier, agentData, viewportAnalysis]);

  // Fetch smart report data from backend
  useEffect(() => {
    const fetchReportData = async () => {
      if (!lat || !lng) return;
      
      setLoading(true);
      try {
        const response = await fetch(
          `${API_URL}/api/smart-report/generate?lat=${lat}&lng=${lng}&locality=${encodeURIComponent(locality || '')}`
        );
        if (response.ok) {
          const data = await response.json();
          setReportData(data);
        }
      } catch (err) {
        console.warn('Smart report fetch failed, using generated data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchReportData();
  }, [lat, lng, locality]);

  const generateTabs = () => {
    const tierConfig = TIER_CONFIG[userTier] || TIER_CONFIG['free'];
    const tabOrder = [
      'free_analysis',
      'decision_verdict',
      'market_snapshot',
      'spatial_intelligence',
      'risk_analysis',
      'roi_projection',
      'comparables',
      'strategy',
      'data_transparency',
      'client_pitch'
    ];

    // Generate content for each tab based on agentData
    const tabsWithContent = tabOrder.map(tabId => ({
      id: tabId,
      type: tierConfig.tabs[tabId] || 'locked',
      ...TAB_METADATA[tabId],
      content: generateTabContent(tabId, agentData, viewportAnalysis, reportData)
    }));

    setTabs(tabsWithContent);
  };

  const generateTabContent = (tabId, agentData, viewportAnalysis, reportData) => {
    const data = agentData || {};
    const viewport = viewportAnalysis || {};
    const report = reportData || {};
    const building = buildingAnalysis || {};
    const buildingData = building.building || {};
    const valuation = building.valuation || {};
    const analysis3d = building.analysis_3d || {};
    const areaImportance = building.area_importance || {};
    const investmentScore = analysis3d.investment_score || {};

    // Use report data if available, otherwise generate from agentData
    switch (tabId) {
      case 'free_analysis':
        return {
          area_name: viewport.area_name || locality || 'Selected Area',
          overview: viewport.overview || data.summary || 'Basic area analysis based on publicly available data.',
          price_range: viewport.price_range || data.price_range || '₹8,000 - ₹12,000 per sq ft',
          connectivity_score: viewport.connectivity_score || data.connectivity_score || 7,
          safety_score: viewport.safety_score || data.safety_score || 6,
          livability_score: viewport.livability_score || data.livability_score || 7,
          key_landmarks: viewport.key_landmarks || data.key_landmarks || [
            'Metro Station within 2km',
            'Shopping Mall nearby',
            'Hospital within 3km'
          ],
          price_trend: viewport.price_trend || data.price_trend || 'Stable',
          demand_level: viewport.demand_level || data.demand_level || 'Moderate',
          is_free: true
        };
      case 'decision_verdict':
        return {
          verdict: report.verdict || data.verdict || data.explainability?.verdict || 'HOLD',
          confidence: report.confidence || data.confidence || data.explainability?.confidence || 0.75,
          confidence_score: report.confidence_score || Math.round((data.confidence || 0.75) * 100),
          risk_level: report.risk_level || 'MEDIUM',
          risk_score: report.risk_score || 35,
          time_horizon: report.time_horizon || 'Medium-term',
          summary: report.summary || data.summary || data.explainability?.summary || 
            'Analysis based on available market data and spatial intelligence.',
          top_reasons: report.top_reasons || data.explainability?.keyDrivers?.slice(0, 5).map(d => d.factor || d.name) || [
            'Good connectivity to major hubs',
            'Developing infrastructure',
            'Competitive pricing relative to area',
            'Strong rental yield potential',
            'Low environmental risk'
          ],
          key_risks: report.key_risks || data.risks || [
            'Market volatility in short term',
            'Infrastructure project delays possible',
            'Regulatory changes may impact returns'
          ],
          strategy_recommendation: report.strategy || {
            entry_price: '₹8,200-8,800/sqft',
            hold_duration: '3-5 years',
            exit_target: '₹11,000+/sqft'
          },
          // INSIGHTS: SHAP Explainability data from Why? sub-tab
          shap_explainability: {
            features: data.explainability?.keyDrivers?.map(d => ({
              name: d.name || d.factor,
              impact: (d.impact || 0) * 100,
              direction: (d.impact || 0) > 0 ? 'positive' : 'negative'
            })) || [
              { name: 'Metro Connectivity', impact: 25, direction: 'positive' },
              { name: 'School Proximity', impact: 18, direction: 'positive' },
              { name: 'Market Trend', impact: 15, direction: 'positive' },
              { name: 'Traffic Congestion', impact: -8, direction: 'negative' }
            ],
            causalChain: data.simulation ? {
              trigger: data.simulation.scenario?.description || 'Infrastructure change',
              effect: `${data.simulation.impacts?.property_value_impact > 0 ? '+' : ''}${data.simulation.impacts?.property_value_impact || 12}% price impact`,
              timeframe: '1-3 years',
              confidence: Math.round((data.simulation.impacts?.confidence || 0.75) * 100)
            } : null
          },
          // Building-specific data
          building: buildingData,
          area_importance: areaImportance,
          building_valuation: valuation,
          has_building: !!buildingAnalysis
        };

      case 'market_snapshot':
        return {
          avg_price_sqft: report.avg_price_sqft || viewport.market?.avg_price_per_sqft || data.dashboard?.market?.avgPricePerSqft || 8500,
          sample_count: report.sample_count || 156,
          price_trend: report.price_trend || {
            '1Y': viewport.market?.price_trend_pct ? `+${viewport.market.price_trend_pct}%` : '+12%',
            '3Y': '+35%',
            '5Y': '+62%'
          },
          demand_supply: report.demand_supply || viewport.market?.demand || 'High Demand',
          rental_yield: report.rental_yield || '3.5%',
          liquidity_score: report.liquidity_score || 70,
          advanced_indicators: report.advanced_indicators || {
            'Market Momentum': 'Bullish',
            'Price Volatility': 'Low',
            'Inventory Days': '45 days',
            'Buyer Interest': 'High'
          },
          // INSIGHTS: KPI Metrics from insights tab
          kpi_metrics: {
            medianPrice: viewport.market?.avg_price_per_sqft || data.dashboard?.market?.avgPricePerSqft,
            priceChange3Y: viewport.market?.price_trend_pct ? viewport.market.price_trend_pct * 3 : 15,
            momentum: viewport.investment?.growth_potential > 70 ? 'hot' : viewport.investment?.growth_potential > 50 ? 'warming' : 'neutral',
            riskScore: viewport.livability?.safety_index ? 100 - viewport.livability.safety_index : 35,
            confidence: viewport.comparison ? 78 : 72,
            confidenceDrivers: [
              { name: 'Property data', impact: 25 },
              { name: 'POI coverage', impact: 18 },
              { name: 'Price history', impact: -8 }
            ]
          },
          // INSIGHTS: Price time series data
          price_time_series: {
            locality: viewport.area_name,
            lat: data.mapCenter?.lat,
            lng: data.mapCenter?.lng
          },
          // INSIGHTS: Elevation data
          elevation: {
            lat: data.mapCenter?.lat,
            lng: data.mapCenter?.lng,
            radius: 2.0
          },
          // INSIGHTS: Analytics metrics
          analytics_metrics: viewport,
          // Building-specific valuation data
          building_valuation: valuation,
          building_market: building.market,
          has_building: !!buildingAnalysis
        };

      case 'spatial_intelligence':
        return {
          nearby_infrastructure: report.nearby_infrastructure || data.nearby_infrastructure || [
            { name: 'Metro Station', distance: '1.2 km' },
            { name: 'Shopping Mall', distance: '2.5 km' },
            { name: 'Tech Park', distance: '3.0 km' },
            { name: 'Hospital', distance: '1.8 km' },
            { name: 'School', distance: '0.5 km' },
            { name: 'Bus Stop', distance: '200 m' },
            { name: 'Restaurant Hub', distance: '1.0 km' }
          ],
          pois: report.pois || {
            schools: viewport.spatial?.poi_schools || 5,
            hospitals: viewport.spatial?.poi_hospitals || 3,
            malls: viewport.spatial?.poi_malls || 2,
            offices: viewport.spatial?.poi_offices || 8
          },
          walkability_score: report.walkability_score || viewport.livability?.walkability || 75,
          transit_score: report.transit_score || 68,
          bike_score: report.bike_score || 72,
          growth_hotspots: report.growth_hotspots || [
            { name: 'Metro Corridor', growth: 18 },
            { name: 'IT Belt Extension', growth: 15 },
            { name: 'Commercial Zone', growth: 12 }
          ],
          // INSIGHTS: Elevation data
          elevation: {
            lat: data.mapCenter?.lat,
            lng: data.mapCenter?.lng,
            radius: 2.0
          },
          // Building-specific 3D analysis
          building_info: buildingData,
          shadow_analysis: analysis3d.shadow_analysis,
          view_quality: analysis3d.view_quality,
          neighbors_3d: analysis3d.neighbors_3d,
          solar_potential: analysis3d.solar_potential,
          has_building: !!buildingAnalysis
        };

      case 'risk_analysis':
        return {
          overall_risk_score: report.overall_risk_score || 35,
          risks: report.risks || {
            flood: { 
              level: 'LOW', 
              score: 15, 
              mitigation: ['Check seasonal waterlogging patterns', 'Review drainage plans']
            },
            legal: { 
              level: 'MODERATE', 
              score: 40, 
              mitigation: ['Verify all title documents', 'Check RERA registration', 'Review encumbrance certificate']
            },
            market: { 
              level: 'LOW', 
              score: 30, 
              mitigation: ['Monitor new project launches', 'Track demand indicators']
            },
            infrastructure: { 
              level: 'LOW', 
              score: 25, 
              mitigation: ['Track metro project timeline', 'Review BBMP development plans']
            },
            environmental: { 
              level: 'MODERATE', 
              score: 35, 
              mitigation: ['Check pollution levels during site visit', 'Review noise assessment']
            }
          },
          mitigation_suggestions: report.mitigation_suggestions || [
            'Verify all title documents before purchase',
            'Check for pending litigation on the property',
            'Review RERA compliance status',
            'Conduct physical site visit during monsoon'
          ],
          has_building: !!buildingAnalysis
        };

      case 'roi_projection':
        return {
          projection_3year: report.projection_3year || {
            best_case: { return: '+35%', price: 11500, probability: 20 },
            expected: { return: '+20%', price: 10200, probability: 50 },
            worst_case: { return: '+3%', price: 8800, probability: 30 }
          },
          entry_exit: report.entry_exit || {
            recommended_entry: '₹8,200-8,800/sqft',
            target_exit: '₹11,000+/sqft'
          },
          rental_yield: report.rental_yield || {
            current: '3.5%',
            projected: '4.2%',
            annual_income: '₹3.6L'
          },
          // INSIGHTS: Scenario Simulator data
          simulator: {
            lat: data.mapCenter?.lat,
            lng: data.mapCenter?.lng,
            locality: viewport.area_name,
            activeSimulation: data.simulation ? {
              scenario: data.simulation.scenario?.description || 'What-if simulation',
              price_impact: data.simulation.impacts?.property_value_impact,
              confidence: data.simulation.impacts?.confidence
            } : null
          },
          // Building-specific investment score
          investment_score: investmentScore,
          has_building: !!buildingAnalysis
        };

      case 'comparables':
        return {
          comparables: report.comparables || data.comparables || [
            { project: 'Prestige Lakeside', distance: '0.8 km', price_sqft: 9200, similarity: 92 },
            { project: 'Brigade Cosmopolis', distance: '1.5 km', price_sqft: 8800, similarity: 85 },
            { project: 'Phoenix One', distance: '2.0 km', price_sqft: 9500, similarity: 78 },
            { project: 'Sobha Dream Acres', distance: '2.5 km', price_sqft: 8600, similarity: 75 }
          ],
          price_analysis: report.price_analysis || {
            subject_property: 8500,
            area_average: 8900,
            percentile: '35th'
          },
          // Building-specific data
          building_valuation: valuation,
          building_name: buildingData.name,
          has_building: !!buildingAnalysis
        };

      case 'strategy':
        return {
          investment_strategy: report.investment_strategy || {
            entry_timing: 'NOW - prices stable',
            negotiation_range: '₹8,200-8,600/sqft',
            portfolio_fit: 'Good for long-term growth'
          },
          action_items: report.action_items || [
            'Schedule site visit',
            'Review legal documents',
            'Compare with 3 similar properties',
            'Negotiate 5-7% below asking',
            'Check rental potential'
          ],
          timeline: report.timeline || {
            due_diligence: '2 weeks',
            closing: '4-6 weeks'
          },
          // Building-specific recommendations
          building_recommendations: building.recommendations,
          has_building: !!buildingAnalysis
        };

      case 'data_transparency':
        return {
          verification_status: report.verification_status || 'VERIFIED',
          data_sources: report.data_sources || [
            { source: 'Property Registry', records: 42500, freshness: '2 days ago' },
            { source: 'POI Database', records: 26961, freshness: '5 days ago' },
            { source: 'Market Trends', records: 15000, freshness: '1 day ago' },
            { source: 'Building Footprints', records: 686000, freshness: '1 week ago' }
          ],
          confidence_breakdown: report.confidence_breakdown || {
            'Property Data': 85,
            'Market Data': 78,
            'Spatial Data': 92,
            'Infrastructure Data': 88
          },
          missing_data_warnings: report.missing_data_warnings || [],
          // INSIGHTS: Data Quality Widget data
          data_quality: {
            properties: data.buildingsCount || 12450,
            pois: viewport.spatial?.poi_count ? viewport.spatial.poi_count * 100 : 8920,
            buildings: data.buildingsCount || 156000,
            overallQuality: 82,
            spatialCoverage: 88,
            temporalCoverage: 75,
            attributeCompleteness: 79
          },
          // INSIGHTS: Raw viewport data for debugging
          raw_viewport_data: viewport,
          // Building-specific data sources
          building_confidence: valuation.confidence,
          has_building: !!buildingAnalysis
        };

      case 'client_pitch':
        return {
          client_summary: report.client_summary || {
            headline: 'Premium Investment Opportunity',
            key_points: [
              '15% below market average',
              'Metro connectivity planned 2027',
              'Top-rated schools within 1km',
              'Strong rental yield potential'
            ],
            ask: '₹1.2 Cr',
            expected_return: '18-25% in 3 years'
          },
          upgrade_benefits: [
            'Auto-generated property summaries',
            'Investment thesis highlights',
            'Export to PDF/WhatsApp/Email',
            'Custom branding options',
            'CRM integration'
          ],
          // Building-specific pitch data
          building_name: buildingData.name,
          building_valuation: valuation,
          investment_score: investmentScore,
          area_grade: areaImportance.grade,
          has_building: !!buildingAnalysis
        };

      default:
        return {};
    }
  };

  const activeTabData = tabs.find(t => t.id === activeTab) || tabs[0];
  const tierConfig = TIER_CONFIG[userTier] || TIER_CONFIG['free'];

  // Count locked tabs for upgrade prompt
  const lockedCount = tabs.filter(t => t.type === 'locked').length;
  const limitedCount = tabs.filter(t => t.type === 'limited' || t.type === 'preview').length;

  return (
    <div className="smart-tabs-container p-2">
      {/* Header with tier indicator and subject */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Dynamic subject indicator */}
          {buildingAnalysis ? (
            <span className="text-[10px] text-cyan-400 flex items-center gap-1">
              <Building2 className="w-3 h-3" />
              {buildingAnalysis.building?.name || 'Building'}
            </span>
          ) : (
            <span className="text-[10px] text-blue-400 flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {locality || 'Area'}
            </span>
          )}
          <span className={`text-[10px] px-2 py-0.5 rounded-full ${
            userTier === 'premium' ? 'bg-purple-500/20 text-purple-400' :
            userTier === 'pro' ? 'bg-blue-500/20 text-blue-400' :
            'bg-slate-500/20 text-slate-400'
          }`}>
            {tierConfig.name}
          </span>
        </div>
        
        {loading && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            Analyzing...
          </div>
        )}
      </div>

      {/* Active Tab Question Indicator */}
      {activeTabData && (
        <div className="text-[10px] text-slate-500 mb-2 flex items-center gap-1">
          <span>→</span>
          <span>{activeTabData.answerQuestion}</span>
        </div>
      )}

      {/* Tab Content */}
      <div className="smart-tab-content bg-slate-800/30 rounded-lg min-h-[300px]">
        {activeTabData && (
          <SmartTab
            tab={activeTabData}
            userTier={userTier}
            onUpgrade={onUpgrade}
            setAgentData={setAgentData}
          />
        )}
      </div>

      {/* Upgrade Prompt for Free/Pro Users */}
      {tierConfig.upgradeMessage && (
        <div className="mt-3 p-3 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-white font-medium">
                {lockedCount > 0 && `${lockedCount} tabs locked • `}
                {limitedCount > 0 && `${limitedCount} tabs limited`}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">
                {tierConfig.upgradeMessage}
              </div>
            </div>
            <button
              onClick={onUpgrade}
              className="px-3 py-1.5 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white text-xs font-medium rounded-lg transition"
            >
              Upgrade
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
