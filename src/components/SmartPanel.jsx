/**
 * SmartPanel - Refactored analysis panel with vertical smart tabs
 * Consolidated from AnalysisPanel - shows only Smart Report tabs
 */

import { useState, useEffect } from 'react';
import SmartTabsContainer from './SmartTabsContainer';
import ComponentErrorBoundary from './ComponentErrorBoundary';
import { useLanguage } from '../contexts/LanguageContext';
import { useLocation } from '../contexts/LocationContext';
import { useAuth } from '../contexts/AuthContext';
import {
  TrendingUp, MapPin, AlertTriangle, Percent, Building,
  Compass, Database, Presentation, Eye, Bot, Users, Target
} from 'lucide-react';
import { IDENTITY_ROLES } from '../config/roles';

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
  },
  'agent_control': {
    title: 'Agent',
    icon: '🤖',
    lucideIcon: Bot,
    description: 'Manage alerts, tasks, and leads',
    shortLabel: 'agent',
    color: 'from-cyan-500 to-blue-500'
  },
  'community_pulse': {
    title: safeT('communityPulse'),
    icon: '👥',
    lucideIcon: Users,
    description: 'Decision-Room, Locality Reviews & Market Sentiment',
    shortLabel: 'community',
    color: 'from-indigo-500 to-purple-500'
  },
  'broker_dashboard': {
    title: safeT('dashboard') || 'Dashboard',
    icon: '📊',
    lucideIcon: Target,
    description: 'Your personalized dashboard',
    shortLabel: 'dashboard',
    color: 'from-blue-500 to-indigo-500'
  }
  };
};

// Tab visibility by identity role
// Each role sees only tabs relevant to their workflow
const TAB_VISIBILITY = {
  [IDENTITY_ROLES.BROKER]: [
    'free_analysis',
    'decision_verdict',
    'market_snapshot',
    'spatial_intelligence',
    'risk_analysis',
    'roi_projection',
    'comparables',
    'strategy',
    'data_transparency',
    'client_pitch',
    'broker_dashboard',
    'agent_control',
    'community_pulse',
  ],
  [IDENTITY_ROLES.DEVELOPER]: [
    'free_analysis',
    'decision_verdict',
    'market_snapshot',
    'spatial_intelligence',
    'risk_analysis',
    'roi_projection',
    'comparables',
    'strategy',
    'data_transparency',
    'broker_dashboard',
    'agent_control',
    'community_pulse',
  ],
  [IDENTITY_ROLES.BUYER]: [
    'free_analysis',
    'decision_verdict',
    'market_snapshot',
    'spatial_intelligence',
    'risk_analysis',
    'roi_projection',
    'comparables',
    'strategy',
    'data_transparency',
    'broker_dashboard',
    'agent_control',
    'community_pulse',
  ],
  [IDENTITY_ROLES.ADMIN]: [
    'free_analysis',
    'decision_verdict',
    'market_snapshot',
    'spatial_intelligence',
    'risk_analysis',
    'roi_projection',
    'comparables',
    'strategy',
    'data_transparency',
    'client_pitch',
    'broker_dashboard',
    'agent_control',
    'community_pulse',
  ],
  [IDENTITY_ROLES.VALORA_TEAM]: [
    'free_analysis',
    'decision_verdict',
    'market_snapshot',
    'spatial_intelligence',
    'risk_analysis',
    'roi_projection',
    'comparables',
    'strategy',
    'data_transparency',
    'client_pitch',
    'broker_dashboard',
    'agent_control',
    'community_pulse',
  ],
};

// Default tabs for unknown roles
const DEFAULT_TABS = TAB_VISIBILITY[IDENTITY_ROLES.BUYER];

function getTabsForRole(role) {
  return TAB_VISIBILITY[role] || DEFAULT_TABS;
}

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
  'client_pitch',
  'broker_dashboard',
  'agent_control',
  'community_pulse'
];

function SmartPanelInner({
  agentData,
  viewportAnalysis,
  userTier = 'free',
  fontSize = 100,
  activeTab: externalActiveTab,
  onTabChange,
  setAgentData,
  authToken = null,
  authUser = null
}) {
  const { t } = useLanguage();
  const { location, coordinates, locality, place } = useLocation();
  const { user } = useAuth();
  const [internalActiveTab, setInternalActiveTab] = useState('free_analysis');
  
  // Get translated tab metadata
  const TAB_METADATA = getTabMetadata(t);
  
  // Filter tabs based on user role
  const userRole = user?.job_role || IDENTITY_ROLES.BUYER;
  const visibleTabs = getTabsForRole(userRole);
  const filteredTabOrder = TAB_ORDER.filter(tab => visibleTabs.includes(tab));
  
  // Ensure activeTab is in filtered list, otherwise default to first visible tab
  const effectiveTabOrder = filteredTabOrder.length > 0 ? filteredTabOrder : DEFAULT_TABS;
  
  // Use external activeTab if provided, otherwise use internal state
  const activeTab = externalActiveTab !== undefined ? externalActiveTab : internalActiveTab;
  const setActiveTab = onTabChange || setInternalActiveTab;

  // If current activeTab is not visible for this role, switch to first visible tab
  useEffect(() => {
    if (!effectiveTabOrder.includes(activeTab)) {
      setActiveTab(effectiveTabOrder[0]);
    }
  }, [activeTab, effectiveTabOrder, setActiveTab]);

  // Listen for tab changes from SmartTabsContainer
  useEffect(() => {
    const handleTabChange = (e) => {
      if (e.detail?.tab && effectiveTabOrder.includes(e.detail.tab)) {
        setActiveTab(e.detail.tab);
      }
    };
    window.addEventListener('valora-smart-tab-change', handleTabChange);
    return () => window.removeEventListener('valora-smart-tab-change', handleTabChange);
  }, [effectiveTabOrder, setActiveTab]);

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-900" style={{ zoom: `${fontSize}%` }}>
      {/* Main content with vertical tabs */}
      <div className="flex flex-1 overflow-hidden">
        {/* Vertical Tab Bar */}
        <div className="w-12 bg-slate-800/30 border-r border-slate-700 flex flex-col py-1 shrink-0 overflow-y-auto">
          {effectiveTabOrder.map(tabId => {
            const tab = TAB_METADATA[tabId];
            if (!tab) return null;
            const Icon = tab.lucideIcon;
            const isActive = activeTab === tabId;
            const isShineTab = tabId === 'agent_control' || tabId === 'community_pulse';
            
            return (
              <button
                key={tabId}
                onClick={() => setActiveTab(tabId)}
                className={`
                  relative flex flex-col items-center justify-center py-2 px-1
                  transition-all duration-200 group overflow-hidden
                  ${isActive 
                    ? 'bg-blue-500/20 text-blue-400 border-r-2 border-blue-400' 
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-700/30'
                  }
                `}
                title={tab.title}
                style={isShineTab && !isActive ? {
                   boxShadow: '0 0 8px 2px rgba(34, 211, 238, 0.5)'
                 } : undefined}
              >
                <Icon className={`w-4 h-4 z-10 ${isShineTab && !isActive ? 'text-cyan-400 drop-shadow-[0_0_6px_rgba(34,211,238,0.8)]' : ''}`} />
                <span className={`text-[8px] mt-0.5 font-medium z-10 ${isShineTab && !isActive ? 'text-cyan-300' : ''}`}>{tab.shortLabel}</span>
                
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
            lat={coordinates?.lat || agentData?.mapCenter?.lat}
            lng={coordinates?.lng || agentData?.mapCenter?.lng}
            locality={locality || viewportAnalysis?.area_name}
            place={place}
            location={location}
            buildingAnalysis={agentData?.buildingAnalysis}
            selectedBuilding={agentData?.selectedBuilding}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            setAgentData={setAgentData}
            authToken={authToken}
            authUser={authUser}
            userRole={userRole}
            onUpgrade={() => {
              window.dispatchEvent(new CustomEvent('valora-upgrade-request'));
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default function SmartPanel(props) {
  return (
    <ComponentErrorBoundary name="Smart Report Panel">
      <SmartPanelInner {...props} />
    </ComponentErrorBoundary>
  );
}
