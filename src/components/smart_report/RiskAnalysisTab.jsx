/**
 * RiskAnalysisTab - Comprehensive risk assessment for Smart Report
 * Shows flood, legal, market, and infrastructure risks
 * Pro tier feature - key conversion driver
 */

import { useState } from 'react';
import {
  AlertTriangle, Shield, Droplets, Scale, TrendingDown,
  Building, Clock, Lock, ChevronRight, Info, CheckCircle,
  XCircle, AlertCircle, ArrowUpRight, ArrowDownRight, Minus
} from 'lucide-react';

// Risk category card with detailed breakdown
function RiskCategoryCard({ category, data, isExpanded, onToggle }) {
  const categoryConfig = {
    flood: {
      icon: Droplets,
      label: 'Flood Risk',
      color: 'blue',
      description: 'Waterlogging and flood zone analysis'
    },
    legal: {
      icon: Scale,
      label: 'Legal Risk',
      color: 'purple',
      description: 'Title, zoning, and compliance issues'
    },
    market: {
      icon: TrendingDown,
      label: 'Market Risk',
      color: 'orange',
      description: 'Price volatility and demand fluctuations'
    },
    infrastructure: {
      icon: Building,
      label: 'Infrastructure Risk',
      color: 'cyan',
      description: 'Project delays and connectivity issues'
    },
    environmental: {
      icon: AlertTriangle,
      label: 'Environmental Risk',
      color: 'green',
      description: 'Pollution, noise, and hazard factors'
    }
  };

  const config = categoryConfig[category] || categoryConfig.market;
  const Icon = config.icon;
  
  const getLevelColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'LOW': return 'text-green-400';
      case 'MODERATE': return 'text-yellow-400';
      case 'HIGH': return 'text-red-400';
      default: return 'text-slate-400';
    }
  };

  const getLevelBg = (level) => {
    switch (level?.toUpperCase()) {
      case 'LOW': return 'bg-green-500/20';
      case 'MODERATE': return 'bg-yellow-500/20';
      case 'HIGH': return 'bg-red-500/20';
      default: return 'bg-slate-500/20';
    }
  };

  const getScoreColor = (score) => {
    if (score <= 30) return 'text-green-400';
    if (score <= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="risk-category-card bg-slate-800/40 rounded-lg overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={onToggle}
        className="w-full p-3 flex items-center gap-3 hover:bg-slate-700/30 transition"
      >
        <div className={`w-10 h-10 rounded-lg ${getLevelBg(data.level)} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${getLevelColor(data.level)}`} />
        </div>
        
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white">{config.label}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${getLevelBg(data.level)} ${getLevelColor(data.level)} font-medium`}>
              {data.level || 'MODERATE'}
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-0.5">{config.description}</div>
        </div>
        
        <div className="text-right">
          <div className={`text-lg font-bold ${getScoreColor(data.score)}`}>
            {data.score || 35}
          </div>
          <div className="text-[10px] text-slate-500">risk score</div>
        </div>
        
        <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
      </button>
      
      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 pt-3">
          {/* Score Bar */}
          <div className="mb-3">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Risk Score</span>
              <span className={getScoreColor(data.score)}>{data.score}/100</span>
            </div>
            <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  data.score <= 30 ? 'bg-gradient-to-r from-green-500 to-emerald-400' :
                  data.score <= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-400' :
                  'bg-gradient-to-r from-red-500 to-rose-400'
                }`}
                style={{ width: `${data.score}%` }}
              />
            </div>
          </div>
          
          {/* Risk Factors */}
          {data.factors && data.factors.length > 0 && (
            <div className="space-y-2 mb-3">
              <div className="text-xs text-slate-400">Contributing Factors:</div>
              {data.factors.map((factor, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <AlertCircle className="w-3 h-3 text-yellow-400" />
                  <span className="text-slate-300">{factor}</span>
                </div>
              ))}
            </div>
          )}
          
          {/* Mitigation Suggestions */}
          {data.mitigation && data.mitigation.length > 0 && (
            <div className="bg-slate-700/30 rounded-lg p-2">
              <div className="text-xs text-slate-400 mb-2">Mitigation Suggestions:</div>
              <ul className="space-y-1">
                {data.mitigation.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400 shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Overall risk gauge
function RiskGauge({ score }) {
  const getRiskLevel = (s) => {
    if (s <= 25) return { label: 'LOW', color: 'text-green-400', bg: 'bg-green-500' };
    if (s <= 50) return { label: 'MODERATE', color: 'text-yellow-400', bg: 'bg-yellow-500' };
    if (s <= 75) return { label: 'ELEVATED', color: 'text-orange-400', bg: 'bg-orange-500' };
    return { label: 'HIGH', color: 'text-red-400', bg: 'bg-red-500' };
  };

  const risk = getRiskLevel(score);
  
  // Calculate rotation for gauge needle (-90 to 90 degrees)
  const rotation = -90 + (score / 100) * 180;

  return (
    <div className="risk-gauge flex flex-col items-center">
      {/* Gauge visualization */}
      <div className="relative w-32 h-16 overflow-hidden">
        {/* Background arc */}
        <div className="absolute inset-0">
          <svg viewBox="0 0 100 50" className="w-full h-full">
            {/* Green zone */}
            <path d="M 10 50 A 40 40 0 0 1 30 15" fill="none" stroke="#22c55e" strokeWidth="8" />
            {/* Yellow zone */}
            <path d="M 30 15 A 40 40 0 0 1 70 15" fill="none" stroke="#eab308" strokeWidth="8" />
            {/* Red zone */}
            <path d="M 70 15 A 40 40 0 0 1 90 50" fill="none" stroke="#ef4444" strokeWidth="8" />
          </svg>
        </div>
        
        {/* Needle */}
        <div 
          className="absolute bottom-0 left-1/2 w-1 h-12 bg-white origin-bottom transition-transform duration-1000"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        >
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-3 h-3 bg-white rounded-full" />
        </div>
      </div>
      
      {/* Score display */}
      <div className="mt-2 text-center">
        <div className={`text-2xl font-bold ${risk.color}`}>{score}</div>
        <div className="text-xs text-slate-400">Overall Risk Score</div>
        <div className={`text-sm font-medium ${risk.color} mt-1`}>{risk.label} RISK</div>
      </div>
    </div>
  );
}

// Risk trend indicator
function RiskTrend({ trend, description }) {
  const config = {
    improving: { icon: ArrowDownRight, color: 'text-green-400', label: 'Improving' },
    stable: { icon: Minus, color: 'text-yellow-400', label: 'Stable' },
    worsening: { icon: ArrowUpRight, color: 'text-red-400', label: 'Worsening' }
  };

  const c = config[trend] || config.stable;
  const Icon = c.icon;

  return (
    <div className="flex items-center gap-2 bg-slate-800/30 rounded-lg px-3 py-2">
      <Icon className={`w-4 h-4 ${c.color}`} />
      <div>
        <div className={`text-xs font-medium ${c.color}`}>{c.label}</div>
        {description && (
          <div className="text-[10px] text-slate-400">{description}</div>
        )}
      </div>
    </div>
  );
}

// Locked state for free users
function LockedRiskAnalysis({ onUpgrade }) {
  return (
    <div className="locked-risk-analysis">
      {/* Teaser content */}
      <div className="bg-slate-800/30 rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Shield className="w-4 h-4 text-yellow-400" />
            Risk Analysis
          </h3>
          <span className="text-xs text-yellow-400 bg-yellow-500/20 px-2 py-1 rounded">
            PRO FEATURE
          </span>
        </div>
        
        {/* Blurred preview */}
        <div className="relative">
          <div className="blur-sm opacity-60 space-y-2">
            <div className="h-20 bg-slate-700/50 rounded-lg" />
            <div className="h-20 bg-slate-700/50 rounded-lg" />
            <div className="h-20 bg-slate-700/50 rounded-lg" />
          </div>
          
          {/* Lock overlay */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center bg-slate-900/80 rounded-xl p-6">
              <Lock className="w-10 h-10 text-yellow-400 mx-auto mb-3" />
              <h4 className="text-lg font-bold text-white mb-2">Unlock Risk Analysis</h4>
              <p className="text-sm text-slate-400 mb-4 max-w-xs">
                Get comprehensive risk assessment including flood zones, legal issues, and market volatility
              </p>
              
              {/* Benefits list */}
              <div className="text-left space-y-2 mb-4">
                {[
                  'Flood & environmental risk mapping',
                  'Legal & title risk assessment',
                  'Market volatility analysis',
                  'Infrastructure project tracking',
                  'Mitigation recommendations'
                ].map((benefit, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-slate-300">
                    <CheckCircle className="w-3 h-3 text-green-400" />
                    {benefit}
                  </div>
                ))}
              </div>
              
              <button
                onClick={onUpgrade}
                className="w-full py-2.5 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white font-medium rounded-lg transition"
              >
                Upgrade to Pro — $19/month
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main RiskAnalysisTab component
export default function RiskAnalysisTab({
  data = {},
  userTier = 'free',
  onUpgrade,
  viewportAnalysis,
  agentData
}) {
  const [expandedCategory, setExpandedCategory] = useState(null);

  // Show locked state for free users
  if (userTier === 'free') {
    return <LockedRiskAnalysis onUpgrade={onUpgrade} />;
  }

  // Extract data with defaults
  const overallScore = data.overall_risk_score || 35;
  const trend = data.trend || 'stable';
  const trendDescription = data.trend_description || 'Risk profile stable over past quarter';
  
  const riskCategories = data.risks || {
    flood: {
      level: 'LOW',
      score: 15,
      factors: ['Area has good drainage', 'Not in flood zone'],
      mitigation: ['Check seasonal waterlogging patterns']
    },
    legal: {
      level: 'MODERATE',
      score: 40,
      factors: ['Some properties have title disputes', 'RERA compliance varies'],
      mitigation: ['Verify all title documents', 'Check RERA registration', 'Review encumbrance certificate']
    },
    market: {
      level: 'LOW',
      score: 30,
      factors: ['Stable demand', 'Limited new supply'],
      mitigation: ['Monitor new project launches']
    },
    infrastructure: {
      level: 'LOW',
      score: 25,
      factors: ['Good road connectivity', 'Metro planned'],
      mitigation: ['Track metro project timeline']
    },
    environmental: {
      level: 'MODERATE',
      score: 35,
      factors: ['Moderate air quality', 'Some noise from main road'],
      mitigation: ['Check pollution levels during site visit']
    }
  };

  const mitigationSuggestions = data.mitigation_suggestions || [
    'Verify all title documents before purchase',
    'Check for pending litigation on the property',
    'Review RERA compliance status',
    'Conduct physical site visit during monsoon'
  ];

  return (
    <div className="risk-analysis-tab space-y-4">
      {/* Header with Overall Score */}
      <div className="bg-slate-800/30 rounded-xl p-4">
        <div className="flex flex-col md:flex-row gap-4 items-center">
          {/* Risk Gauge */}
          <RiskGauge score={overallScore} />
          
          {/* Summary */}
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400" />
              Risk Assessment Summary
            </h3>
            <p className="text-sm text-slate-300 mb-3">
              {data.summary || `This property has a ${overallScore <= 30 ? 'low' : overallScore <= 60 ? 'moderate' : 'elevated'} overall risk profile. Key areas to review include legal documentation and environmental factors.`}
            </p>
            
            <div className="flex flex-wrap gap-2">
              <RiskTrend trend={trend} description={trendDescription} />
              <div className="flex items-center gap-2 bg-slate-800/30 rounded-lg px-3 py-2">
                <Clock className="w-4 h-4 text-slate-400" />
                <div>
                  <div className="text-xs text-slate-400">Last Updated</div>
                  <div className="text-xs text-white">{new Date().toLocaleDateString()}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Categories */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-slate-400 uppercase tracking-wide px-1">
          Risk Categories
        </h4>
        
        {Object.entries(riskCategories).map(([category, categoryData]) => (
          <RiskCategoryCard
            key={category}
            category={category}
            data={categoryData}
            isExpanded={expandedCategory === category}
            onToggle={() => setExpandedCategory(
              expandedCategory === category ? null : category
            )}
          />
        ))}
      </div>

      {/* Overall Mitigation Suggestions */}
      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4" />
          Recommended Actions
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {mitigationSuggestions.map((suggestion, i) => (
            <div 
              key={i}
              className="flex items-start gap-2 bg-slate-800/30 rounded-lg p-2"
            >
              <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs text-blue-400 font-medium">{i + 1}</span>
              </div>
              <span className="text-xs text-slate-300">{suggestion}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Disclaimer */}
      <div className="text-[10px] text-slate-500 px-1 flex items-start gap-1">
        <Info className="w-3 h-3 shrink-0 mt-0.5" />
        <span>
          Risk scores are based on available data and AI analysis. They should not be considered as 
          professional legal or financial advice. Always consult qualified professionals before making 
          investment decisions.
        </span>
      </div>
    </div>
  );
}
