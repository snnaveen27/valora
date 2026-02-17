/**
 * SmartPanel - Refactored analysis panel with vertical smart tabs
 * Consolidated from AnalysisPanel - shows only Smart Report tabs
 */

import React, { useState, useEffect } from 'react';
import SmartTabsContainer from './SmartTabsContainer';
import {
  TrendingUp, MapPin, AlertTriangle, Percent, Building,
  Compass, Database, Presentation, Eye
} from 'lucide-react';

// Tab metadata with icons
const TAB_METADATA = {
  'free_analysis': {
    title: 'Free Analysis',
    icon: '🔍',
    lucideIcon: Eye,
    description: 'Basic area overview (Free)',
    shortLabel: 'Free',
    color: 'from-emerald-500 to-green-600'
  },
  'decision_verdict': {
    title: 'Decision Verdict',
    icon: '⚖️',
    lucideIcon: TrendingUp,
    description: 'BUY / HOLD / AVOID recommendation',
    shortLabel: 'Verdict',
    color: 'from-green-500 to-emerald-600'
  },
  'market_snapshot': {
    title: 'Market Snapshot',
    icon: '📈',
    lucideIcon: TrendingUp,
    description: 'Price trends and market dynamics',
    shortLabel: 'Market',
    color: 'from-blue-500 to-cyan-500'
  },
  'spatial_intelligence': {
    title: 'Spatial Intelligence',
    icon: '🗺️',
    lucideIcon: MapPin,
    description: 'Infrastructure, connectivity, POIs',
    shortLabel: 'Spatial',
    color: 'from-purple-500 to-pink-500'
  },
  'risk_analysis': {
    title: 'Risk Analysis',
    icon: '⚠️',
    lucideIcon: AlertTriangle,
    description: 'Flood, legal, and market risks',
    shortLabel: 'Risk',
    color: 'from-orange-500 to-red-500'
  },
  'roi_projection': {
    title: 'ROI Projection',
    icon: '%',
    lucideIcon: Percent,
    description: '3-year return scenarios',
    shortLabel: 'ROI',
    color: 'from-green-500 to-teal-500'
  },
  'comparables': {
    title: 'Comparables',
    icon: '🏢',
    lucideIcon: Building,
    description: 'Similar properties analysis',
    shortLabel: 'Comps',
    color: 'from-indigo-500 to-purple-500'
  },
  'strategy': {
    title: 'Strategy',
    icon: '🧭',
    lucideIcon: Compass,
    description: 'Entry/exit recommendations',
    shortLabel: 'Strategy',
    color: 'from-cyan-500 to-blue-500'
  },
  'data_transparency': {
    title: 'Data Transparency',
    icon: '🗄️',
    lucideIcon: Database,
    description: 'Source verification',
    shortLabel: 'Data',
    color: 'from-slate-500 to-slate-600'
  },
  'client_pitch': {
    title: 'Client Pitch',
    icon: '📊',
    lucideIcon: Presentation,
    description: 'Broker presentation',
    shortLabel: 'Pitch',
    color: 'from-amber-500 to-orange-500'
  }
};

const TAB_ORDER = [
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

export default function SmartPanel({
  agentData,
  viewportAnalysis,
  userTier = 'free',
  fontSize = 100,
  isFullscreen = false,
  onToggleFullscreen,
  onClose,
  onFontSizeChange,
  activeTab: externalActiveTab,
  onTabChange,
  setAgentData
}) {
  const [internalActiveTab, setInternalActiveTab] = useState('free_analysis');
  
  // Use external activeTab if provided, otherwise use internal state
  const activeTab = externalActiveTab !== undefined ? externalActiveTab : internalActiveTab;
  const setActiveTab = onTabChange || setInternalActiveTab;

  // Listen for tab changes from SmartTabsContainer
  useEffect(() => {
    const handleTabChange = (e) => {
      if (e.detail?.tab) {
        setActiveTab(e.detail.tab);
      }
    };
    window.addEventListener('valora-smart-tab-change', handleTabChange);
    return () => window.removeEventListener('valora-smart-tab-change', handleTabChange);
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-900" style={{ zoom: `${fontSize}%` }}>
      {/* Main content with vertical tabs */}
      <div className="flex flex-1 overflow-hidden">
        {/* Vertical Tab Bar */}
        <div className="w-12 bg-slate-800/30 border-r border-slate-700 flex flex-col py-1 shrink-0 overflow-y-auto">
          {TAB_ORDER.map(tabId => {
            const tab = TAB_METADATA[tabId];
            const Icon = tab.lucideIcon;
            const isActive = activeTab === tabId;
            
            return (
              <button
                key={tabId}
                onClick={() => setActiveTab(tabId)}
                className={`
                  relative flex flex-col items-center justify-center py-2 px-1
                  transition-all duration-200 group
                  ${isActive 
                    ? 'bg-blue-500/20 text-blue-400 border-r-2 border-blue-400' 
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-700/30'
                  }
                `}
                title={tab.title}
              >
                <Icon className="w-4 h-4" />
                <span className="text-[8px] mt-0.5 font-medium">{tab.shortLabel}</span>
                
                {/* Tooltip */}
                <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 border border-slate-600 rounded text-[10px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  {tab.title}
                </div>
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto">
          {/* Building Analysis Loading State */}
          {agentData?.buildingAnalysisLoading && (
            <div className="p-3">
              <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/40 rounded-lg p-3">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                  <div>
                    <p className="text-white font-medium text-sm">Analyzing Building...</p>
                    <p className="text-slate-400 text-xs">Running 3D spatial + valuation analysis</p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Smart Tabs Container */}
          <SmartTabsContainer
            agentData={agentData}
            viewportAnalysis={viewportAnalysis}
            userTier={userTier}
            lat={agentData?.mapCenter?.lat}
            lng={agentData?.mapCenter?.lng}
            locality={viewportAnalysis?.area_name}
            buildingAnalysis={agentData?.buildingAnalysis}
            selectedBuilding={agentData?.selectedBuilding}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            setAgentData={setAgentData}
            onUpgrade={() => {
              window.dispatchEvent(new CustomEvent('valora-upgrade-request'));
            }}
          />
        </div>
      </div>
    </div>
  );
}
