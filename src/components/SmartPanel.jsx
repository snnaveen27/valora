/**
 * SmartPanel - Refactored analysis panel with vertical smart tabs
 * Consolidated from AnalysisPanel - shows only Smart Report tabs
 */

import React, { useState, useEffect } from 'react';
import SmartTabsContainer from './SmartTabsContainer';
import { useLanguage } from '../contexts/LanguageContext';
import {
  TrendingUp, MapPin, AlertTriangle, Percent, Building,
  Compass, Database, Presentation, Eye
} from 'lucide-react';

// Tab metadata with icons - will be populated with translations
// Added safeT fallback to handle missing translations gracefully
const getTabMetadata = (t) => {
  // Safe translation function with fallback
  const safeT = (key) => {
    try {
      const result = t(key);
      return typeof result === 'string' ? result : key;
    } catch {
      return key;
    }
  };

  return {
  'free_analysis': {
    title: safeT('freeAnalysisTab'),
    icon: '🔍',
    lucideIcon: Eye,
    description: safeT('basicAreaOverview'),
    shortLabel: safeT('free'),
    color: 'from-emerald-500 to-green-600'
  },
  'decision_verdict': {
    title: safeT('decisionVerdict'),
    icon: '⚖️',
    lucideIcon: TrendingUp,
    description: safeT('buyHoldAvoid'),
    shortLabel: safeT('verdict'),
    color: 'from-green-500 to-emerald-600'
  },
  'market_snapshot': {
    title: safeT('marketSnapshot'),
    icon: '📈',
    lucideIcon: TrendingUp,
    description: safeT('priceTrendsMarket'),
    shortLabel: safeT('market'),
    color: 'from-blue-500 to-cyan-500'
  },
  'spatial_intelligence': {
    title: safeT('spatialIntelligence'),
    icon: '🗺️',
    lucideIcon: MapPin,
    description: safeT('infrastructureConnectivity'),
    shortLabel: safeT('spatial'),
    color: 'from-purple-500 to-pink-500'
  },
  'risk_analysis': {
    title: safeT('riskAnalysisTab'),
    icon: '⚠️',
    lucideIcon: AlertTriangle,
    description: safeT('floodLegalMarketRisks'),
    shortLabel: safeT('risk'),
    color: 'from-orange-500 to-red-500'
  },
  'roi_projection': {
    title: safeT('roiProjection'),
    icon: '%',
    lucideIcon: Percent,
    description: safeT('threeYearReturn'),
    shortLabel: safeT('roi'),
    color: 'from-green-500 to-teal-500'
  },
  'comparables': {
    title: safeT('comparablesTab'),
    icon: '🏢',
    lucideIcon: Building,
    description: safeT('similarProperties'),
    shortLabel: safeT('comps'),
    color: 'from-indigo-500 to-purple-500'
  },
  'strategy': {
    title: safeT('strategyTab'),
    icon: '🧭',
    lucideIcon: Compass,
    description: safeT('entryExitRecommendations'),
    shortLabel: safeT('strategy'),
    color: 'from-cyan-500 to-blue-500'
  },
  'data_transparency': {
    title: safeT('dataTransparency'),
    icon: '🗄️',
    lucideIcon: Database,
    description: safeT('sourceVerification'),
    shortLabel: safeT('data'),
    color: 'from-slate-500 to-slate-600'
  },
  'client_pitch': {
    title: safeT('clientPitch'),
    icon: '📊',
    lucideIcon: Presentation,
    description: safeT('brokerPresentation'),
    shortLabel: safeT('pitch'),
    color: 'from-amber-500 to-orange-500'
  }
  };
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
  const { t } = useLanguage();
  const [internalActiveTab, setInternalActiveTab] = useState('free_analysis');
  
  // Get translated tab metadata
  const TAB_METADATA = getTabMetadata(t);
  
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
                    <p className="text-white font-medium text-sm">{t('analyzingBuilding')}</p>
                    <p className="text-slate-400 text-xs">{t('runningSpatialValuation')}</p>
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
