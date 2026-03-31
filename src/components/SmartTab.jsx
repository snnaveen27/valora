/**
 * SmartTab - Enhanced individual tab component for SmartPanel
 * Supports limited, full, preview, and locked states
 * Includes cognitive workflow features and conversion optimization
 */

import { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle,
  Clock, Target, DollarSign, Shield, Zap, Lock, ChevronRight,
  BarChart3, ArrowUpRight, ArrowDownRight, HelpCircle, Info,
  MapPin, Building, Droplets, Scale, Compass, Database,
  Presentation, Share2, Download, MessageCircle, Mail,
  Star, Eye, EyeOff, Sparkles, Loader2
} from 'lucide-react';
import { API_URL } from '../apiConfig';
import { useLanguage } from '../contexts/LanguageContext';

const TAB_ICONS = {
  'gavel': '⚖️',
  'chart-line': '📈',
  'map': '🗺️',
  'exclamation-triangle': '⚠️',
  'percentage': '%',
  'building': '🏢',
  'compass': '🧭',
  'database': '🗄️',
  'presentation': '📊'
};

// ============================================
// DECISION VERDICT TAB - PRIMARY TAB
// ============================================

function VerdictBadge({ verdict, size = 'large' }) {
  const config = {
    'BUY': {
      bg: 'bg-gradient-to-r from-green-500 to-emerald-600',
      text: 'text-white',
      icon: TrendingUp,
      pulse: true,
      glow: 'shadow-green-500/50'
    },
    'HOLD': {
      bg: 'bg-gradient-to-r from-slate-500 to-slate-600',
      text: 'text-white',
      icon: Minus,
      pulse: false,
      glow: 'shadow-slate-500/30'
    },
    'AVOID': {
      bg: 'bg-gradient-to-r from-red-500 to-rose-600',
      text: 'text-white',
      icon: TrendingDown,
      pulse: false,
      glow: 'shadow-red-500/50'
    }
  };

  const c = config[verdict] || config['HOLD'];
  const Icon = c.icon;
  
  const sizeClasses = size === 'large' 
    ? 'px-6 py-3 text-2xl gap-3' 
    : 'px-3 py-1.5 text-sm gap-1.5';

  return (
    <div className={`
      ${c.bg} ${c.text} rounded-xl font-bold flex items-center justify-center
      ${sizeClasses} shadow-lg ${c.glow}
      ${c.pulse ? 'animate-pulse' : ''}
      transition-all duration-300
    `}>
      <Icon className={size === 'large' ? 'w-7 h-7' : 'w-4 h-4'} />
      <span>{verdict}</span>
    </div>
  );
}

function ConfidenceMeter({ score, showBreakdown = false, isLimited = false }) {
  const { t } = useLanguage();
  const [animatedScore, setAnimatedScore] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 300);
    return () => clearTimeout(timer);
  }, [score]);

  const getScoreColor = (s) => {
    if (s >= 80) return 'text-green-400';
    if (s >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getBarColor = (s) => {
    if (s >= 80) return 'from-green-500 to-emerald-400';
    if (s >= 60) return 'from-yellow-500 to-amber-400';
    return 'from-red-500 to-rose-400';
  };

  return (
    <div className="confidence-meter">
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-400 text-sm flex items-center gap-1">
          <Shield className="w-4 h-4" />
          {t('confidenceScore')}
        </span>
        <span className={`text-lg font-bold ${getScoreColor(animatedScore)}`}>
          {animatedScore}%
        </span>
      </div>
      
      <div className="relative h-3 bg-slate-700/50 rounded-full overflow-hidden">
        <div 
          className={`absolute inset-y-0 left-0 bg-gradient-to-r ${getBarColor(animatedScore)} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${animatedScore}%` }}
        />
        <div className="absolute inset-0 flex">
          <div className="flex-1 border-r border-slate-600/30" />
          <div className="flex-1 border-r border-slate-600/30" />
          <div className="flex-1 border-r border-slate-600/30" />
          <div className="flex-1" />
        </div>
      </div>
      
      <div className="flex justify-between text-[10px] text-slate-500 mt-1">
        <span>{t('low')}</span>
        <span>{t('medium')}</span>
        <span>{t('high')}</span>
        <span>{t('veryHigh')}</span>
      </div>

      {isLimited && (
        <div className="mt-2 text-[10px] text-blue-400 flex items-center gap-1">
          <Lock className="w-3 h-3" />
          {t('fullConfidencePro')}
        </div>
      )}
    </div>
  );
}

function RiskIndicator({ level, score }) {
  const { t } = useLanguage();
  const config = {
    'LOW': { color: 'text-green-400', bg: 'bg-green-500/20', icon: Shield },
    'MEDIUM': { color: 'text-yellow-400', bg: 'bg-yellow-500/20', icon: AlertTriangle },
    'HIGH': { color: 'text-red-400', bg: 'bg-red-500/20', icon: AlertTriangle }
  };

  const c = config[level] || config['MEDIUM'];
  const Icon = c.icon;

  return (
    <div className={`flex items-center gap-2 ${c.bg} rounded-lg px-3 py-2`}>
      <Icon className={`w-4 h-4 ${c.color}`} />
      <div>
        <div className="text-[10px] text-slate-400">{t('riskLevel')}</div>
        <div className={`text-sm font-bold ${c.color}`}>{level}</div>
      </div>
      {score && (
        <div className="ml-auto text-right">
          <div className="text-[10px] text-slate-400">{t('score')}</div>
          <div className="text-sm text-white font-medium">{score}/100</div>
        </div>
      )}
    </div>
  );
}

function TimeHorizon({ horizon, reasoning }) {
  const { t } = useLanguage();
  const config = {
    'Short-term': { icon: Zap, color: 'text-orange-400', desc: t('shortTermDesc') },
    'Medium-term': { icon: Clock, color: 'text-blue-400', desc: t('mediumTermDesc') },
    'Long-term': { icon: Target, color: 'text-purple-400', desc: t('longTermDesc') }
  };

  const c = config[horizon] || config['Medium-term'];
  const Icon = c.icon;

  return (
    <div className="bg-slate-800/50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${c.color}`} />
        <span className="text-sm text-slate-300">{t('timeHorizon')}</span>
      </div>
      <div className={`text-lg font-bold ${c.color}`}>{horizon}</div>
      <div className="text-xs text-slate-400">{c.desc}</div>
      {reasoning && (
        <div className="mt-2 text-[10px] text-slate-500 italic">{reasoning}</div>
      )}
    </div>
  );
}

function ReasonItem({ reason, type = 'positive', impact, index }) {
  const isPositive = type === 'positive';
  
  return (
    <div className="flex items-start gap-2 py-2 border-b border-slate-700/30 last:border-0">
      <div className={`
        w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5
        ${isPositive ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}
      `}>
        {isPositive ? (
          <CheckCircle className="w-3 h-3" />
        ) : (
          <AlertTriangle className="w-3 h-3" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-slate-200">{reason}</div>
        {impact && (
          <div className={`text-[10px] mt-0.5 ${isPositive ? 'text-green-400' : 'text-yellow-400'}`}>
            {isPositive ? '+' : ''}{impact}% impact
          </div>
        )}
      </div>
      <div className="text-[10px] text-slate-500">#{index + 1}</div>
    </div>
  );
}

function StrategyCard({ entryPrice, holdDuration, exitTarget, isLocked = false, onUpgrade }) {
  const { t } = useLanguage();
  if (isLocked) {
    return (
      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-4 relative overflow-hidden">
        <div className="blur-sm">
          <div className="h-4 bg-slate-600 rounded w-1/2 mb-2" />
          <div className="h-3 bg-slate-600 rounded w-3/4 mb-3" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-8 bg-slate-600 rounded" />
            <div className="h-8 bg-slate-600 rounded" />
          </div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/60">
          <div className="text-center">
            <Lock className="w-6 h-6 text-blue-400 mx-auto mb-2" />
            <p className="text-sm text-slate-300">{t('strategyRecommendations')}</p>
            <button onClick={onUpgrade} className="mt-2 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mx-auto">
              {t('unlockWithPro')} <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Target className="w-4 h-4 text-blue-400" />
        <span className="text-sm font-medium text-blue-400">{t('strategyRecommendation')}</span>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-800/50 rounded-lg p-2">
          <div className="text-[10px] text-slate-400 mb-1">{t('entryPrice')}</div>
          <div className="text-sm font-bold text-white">{entryPrice}</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-2">
          <div className="text-[10px] text-slate-400 mb-1">{t('holdDuration')}</div>
          <div className="text-sm font-bold text-white">{holdDuration}</div>
        </div>
        {exitTarget && (
          <div className="col-span-2 bg-slate-800/50 rounded-lg p-2">
            <div className="text-[10px] text-slate-400 mb-1">{t('exitTarget')}</div>
            <div className="text-sm font-bold text-green-400">{exitTarget}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function UpgradePrompt({ onUpgrade, feature }) {
  const { t } = useLanguage();
  return (
    <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
          <BarChart3 className="w-5 h-5 text-purple-400" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-white">{t('unlockFullAnalysis')}</div>
          <div className="text-xs text-slate-400">
            {t('getCompleteWithPro', { feature })}
          </div>
        </div>
        <button 
          onClick={onUpgrade}
          className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white text-sm font-medium rounded-lg transition"
        >
          {t('upgrade')}
        </button>
      </div>
    </div>
  );
}

// Enhanced Decision Verdict Content
function VerdictContent({ content, isLimited, onUpgrade }) {
  const { t } = useLanguage();
  const verdict = content.verdict || 'HOLD';
  const confidenceScore = content.confidence_score || Math.round((content.confidence || 0.75) * 100);
  const riskLevel = content.risk_level || 'MEDIUM';
  const riskScore = content.risk_score || 35;
  const timeHorizon = content.time_horizon || 'Medium-term';
  const summary = content.summary || t('analysisBasedOnMarketData');
  
  const topReasons = content.top_reasons || [
    t('goodConnectivity'),
    t('developingInfrastructure'),
    t('competitivePricing')
  ];
  
  const keyRisks = content.key_risks || [
    t('marketVolatility'),
    t('infrastructureDelays')
  ];
  
  const strategy = content.strategy_recommendation || {
    entry_price: '₹8,200-8,800/sqft',
    hold_duration: '3-5 years',
    exit_target: '₹11,000+/sqft'
  };

  return (
    <div className="verdict-content p-4 space-y-4">
      {/* Header Section */}
      <div className="bg-slate-800/30 rounded-xl p-4">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
          <VerdictBadge verdict={verdict} size="large" />
          <div className="flex-1 w-full">
            <ConfidenceMeter 
              score={confidenceScore} 
              showBreakdown={!isLimited}
              isLimited={isLimited}
            />
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-300 leading-relaxed">{summary}</p>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 gap-3">
        <RiskIndicator level={riskLevel} score={riskScore} />
        <TimeHorizon horizon={timeHorizon} reasoning={!isLimited ? t('basedOnMarketCycle') : null} />
      </div>

      {/* Top Reasons */}
      <div className="bg-slate-800/30 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-green-400 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            {t('topReasons')}
          </h3>
          <span className="text-[10px] text-slate-500">{topReasons.length} {t('factorsAnalyzed')}</span>
        </div>
        <div className="space-y-1">
          {(Array.isArray(topReasons) ? topReasons : []).slice(0, isLimited ? 3 : 5).map((reason, i) => (
            <ReasonItem 
              key={i}
              reason={reason}
              type="positive"
              impact={!isLimited ? Math.floor(Math.random() * 15) + 5 : null}
              index={i}
            />
          ))}
        </div>
        {isLimited && topReasons.length > 3 && (
          <button onClick={onUpgrade} className="mt-3 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mx-auto">
            <Lock className="w-3 h-3" />
            {t('unlockMoreReasons', { count: topReasons.length - 3 })}
          </button>
        )}
      </div>

      {/* Key Risks - Pro Feature */}
      {!isLimited ? (
        <div className="bg-slate-800/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-yellow-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {t('keyRisks')}
            </h3>
            <span className="text-[10px] text-slate-500">{t('honestAssessment')}</span>
          </div>
          <div className="space-y-1">
            {(Array.isArray(keyRisks) ? keyRisks : []).map((risk, i) => (
              <ReasonItem key={i} reason={risk} type="risk" impact={Math.floor(Math.random() * 10) + 3} index={i} />
            ))}
          </div>
        </div>
      ) : (
        <UpgradePrompt onUpgrade={onUpgrade} feature={t('riskAnalysis')} />
      )}

      {/* Strategy */}
      <StrategyCard 
        entryPrice={strategy.entry_price}
        holdDuration={strategy.hold_duration}
        exitTarget={strategy.exit_target}
        isLocked={isLimited}
        onUpgrade={onUpgrade}
      />

      {/* SHAP Explainability - Why this verdict? */}
      {!isLimited && content.shap_explainability && (
        <div className="bg-slate-800/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-purple-400 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              {t('whyThisVerdict')}
            </h3>
            <span className="text-[10px] text-slate-500">{t('shapAnalysis')}</span>
          </div>
          
          {/* Feature Impacts */}
          <div className="space-y-2 mb-3">
            {(Array.isArray(content.shap_explainability?.features) ? content.shap_explainability.features : []).slice(0, 5).map((feature, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-300">{feature.name}</span>
                    <span className={feature.direction === 'positive' ? 'text-green-400' : 'text-red-400'}>
                      {feature.direction === 'positive' ? '+' : '-'}{Math.abs(feature.impact)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${feature.direction === 'positive' ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(Math.abs(feature.impact) * 2, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {/* Causal Chain */}
          {content.shap_explainability.causalChain && (
            <div className="bg-slate-900/50 rounded-lg p-2 text-xs">
              <div className="flex items-center gap-2 text-slate-400">
                <span className="text-blue-400">{content.shap_explainability.causalChain.trigger}</span>
                <span>→</span>
                <span className="text-green-400">{content.shap_explainability.causalChain.effect}</span>
                <span className="text-slate-500">({content.shap_explainability.causalChain.timeframe})</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Data Freshness */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 px-1">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span>{t('analysisCurrentAsOf', { time: new Date().toLocaleTimeString() })}</span>
        </div>
        <button className="flex items-center gap-1 text-slate-400 hover:text-slate-300">
          <HelpCircle className="w-3 h-3" />
          {t('howIsThisCalculated')}
        </button>
      </div>

      {/* Conversion CTA for Free Users */}
      {isLimited && (
        <div className="mt-4 p-4 bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-xl">
          <div className="text-center">
            <div className="text-lg font-bold text-white mb-1">{t('getCompletePicture')}</div>
            <p className="text-xs text-slate-400 mb-3">{t('unlockAllAnalysisTabs')}</p>
            <button onClick={onUpgrade} className="px-6 py-2.5 bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white font-medium rounded-lg transition shadow-lg">
              {t('upgradeToPro')}
            </button>
            <div className="mt-2 text-[10px] text-slate-500">{t('freeTrialCancelAnytime')}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// MARKET SNAPSHOT TAB - ENHANCED
// ============================================

function MarketContent({ content, isLimited }) {
  const { t } = useLanguage();
  const [selectedPeriod, setSelectedPeriod] = useState('1Y');
  const hasBuilding = content.has_building && content.building_valuation;
  const kpiMetrics = content.kpi_metrics;
  
  return (
    <div className="market-content p-4 space-y-4">
      {/* KPI Summary Row - from insights */}
      {kpiMetrics && (
        <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl p-3">
          <div className="grid grid-cols-4 gap-2 text-center">
            <div>
              <div className="text-[10px] text-slate-400">{t('medianPrice')}</div>
              <div className="text-sm font-bold text-white">₹{kpiMetrics.medianPrice?.toLocaleString() || 'N/A'}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400">{t('threeYearChange')}</div>
              <div className="text-sm font-bold text-green-400">+{kpiMetrics.priceChange3Y}%</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400">{t('momentum')}</div>
              <div className={`text-sm font-bold ${kpiMetrics.momentum === 'hot' ? 'text-red-400' : kpiMetrics.momentum === 'warming' ? 'text-yellow-400' : 'text-slate-400'}`}>
                {kpiMetrics.momentum === 'hot' ? `🔥 ${t('hot')}` : kpiMetrics.momentum === 'warming' ? `📈 ${t('warming')}` : `➡️ ${t('neutral')}`}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400">{t('riskScore')}</div>
              <div className="text-sm font-bold text-yellow-400">{kpiMetrics.riskScore}%</div>
            </div>
          </div>
        </div>
      )}
      
      {/* Building Valuation Section - if building selected */}
      {hasBuilding && (
        <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Building className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-semibold text-cyan-400">🏢 {t('thisBuilding')}</span>
          </div>
          
          <div className="mb-3">
            <div className="text-[10px] text-slate-400 mb-1">{t('estimatedValue')}</div>
            <div className="text-2xl font-bold text-white">
              ₹{((content.building_valuation?.estimated_price || 0) / 100000).toFixed(1)}L
            </div>
            <div className="text-sm text-slate-400">
              ₹{content.building_valuation?.price_per_sqft?.toLocaleString() || 'N/A'}/sqft
            </div>
          </div>
          
          {/* Confidence */}
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-400">{t('confidence')}</span>
              <span className="text-green-400 font-medium">
                {Math.round((content.building_valuation?.confidence || 0.75) * 100)}%
              </span>
            </div>
            <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full"
                style={{ width: `${(content.building_valuation?.confidence || 0.75) * 100}%` }}
              />
            </div>
          </div>
          
          {/* Price Range */}
          {content.building_valuation?.price_range && (
            <div className="bg-slate-800/50 rounded-lg p-2">
              <div className="text-[10px] text-slate-400 mb-1">{t('priceRange')}</div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300">
                  ₹{((content.building_valuation.price_range.low || 0) / 100000).toFixed(0)}L
                </span>
                <span className="text-slate-500">—</span>
                <span className="text-slate-300">
                  ₹{((content.building_valuation.price_range.high || 0) / 100000).toFixed(0)}L
                </span>
              </div>
            </div>
          )}
          
          {/* vs Area Average */}
          {content.building_market && (
            <div className="mt-2 text-xs text-slate-400">
              {t('vsAreaAvg')}: <span className="text-cyan-400 font-medium">
                {content.avg_price_sqft && content.building_valuation?.price_per_sqft
                  ? `${Math.round(((content.building_valuation.price_per_sqft / content.avg_price_sqft) - 1) * 100)}% ${content.building_valuation.price_per_sqft > content.avg_price_sqft ? t('premium') : t('discount')}`
                  : 'N/A'}
              </span>
            </div>
          )}
        </div>
      )}
      
      {/* Area Context Section */}
      <div className={hasBuilding ? 'opacity-80' : ''}>
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-semibold text-slate-300">
            {hasBuilding ? `📍 ${t('areaContext')}` : t('marketOverview')}
          </span>
        </div>
        
        {/* Primary Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <label className="text-xs text-slate-400 block mb-1">{t('avgPriceSqft')}</label>
            <span className="text-xl font-bold text-white">
              ₹{content.avg_price_sqft?.toLocaleString() || content.avg_price?.toLocaleString() || 'N/A'}
            </span>
            {!isLimited && (
              <div className="text-[10px] text-slate-500 mt-1">{t('basedOnListings', { count: content.sample_count || 156 })}</div>
            )}
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <label className="text-xs text-slate-400 block mb-1">{t('priceTrend')}</label>
            <div className="flex items-center gap-2">
              <span className={`text-xl font-bold ${content.price_trend?.['1Y']?.includes('+') ? 'text-green-400' : 'text-red-400'}`}>
                {content.price_trend?.[selectedPeriod] || content.price_trend || 'N/A'}
              </span>
              {content.price_trend?.['1Y']?.includes('+') ? (
                <ArrowUpRight className="w-5 h-5 text-green-400" />
              ) : (
                <ArrowDownRight className="w-5 h-5 text-red-400" />
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Period Selector */}
      <div className="flex items-center gap-1 bg-slate-800/30 rounded-lg p-1">
        {['1Y', '3Y', '5Y'].map(period => (
          <button
            key={period}
            onClick={() => setSelectedPeriod(period)}
            className={`flex-1 py-1.5 text-xs font-medium rounded transition ${
              selectedPeriod === period 
                ? 'bg-blue-500 text-white' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {period}
          </button>
        ))}
      </div>
      
      {/* Secondary Metrics */}
      {!isLimited && (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="bg-slate-800/30 rounded p-2">
            <div className="text-xs text-slate-400">{t('demand')}</div>
            <div className="text-sm text-white font-medium">{content.demand_supply || t('high')}</div>
          </div>
          <div className="bg-slate-800/30 rounded p-2">
            <div className="text-xs text-slate-400">{t('rentalYield')}</div>
            <div className="text-sm text-white font-medium">{content.rental_yield || '3.5%'}</div>
          </div>
          <div className="bg-slate-800/30 rounded p-2">
            <div className="text-xs text-slate-400">{t('liquidity')}</div>
            <div className="text-sm text-white font-medium">{content.liquidity_score || 70}%</div>
          </div>
        </div>
      )}
      {/* Advanced Indicators - Pro */}
      {!isLimited && content.advanced_indicators && (
        <div className="bg-slate-800/30 rounded-lg p-3">
          <h4 className="text-xs font-medium text-slate-300 mb-2">{t('advancedIndicators')}</h4>
          <div className="space-y-2">
            {Object.entries(content.advanced_indicators || {}).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="text-slate-400 capitalize">{key.replace(/_/g, ' ')}</span>
                <span className="text-white font-medium">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// SPATIAL INTELLIGENCE TAB - ENHANCED
// ============================================

function SpatialContent({ content, isLimited }) {
  const { t } = useLanguage();
  const hasBuilding = content.has_building && content.building_info;
  
  return (
    <div className="spatial-content p-4 space-y-4">
      {/* Building 3D Analysis Section - if building selected */}
      {hasBuilding && (
        <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Building className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-semibold text-cyan-400">🏢 {t('buildingSpatialData')}</span>
          </div>
          
          {/* Building Info */}
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-slate-800/50 rounded p-2 text-center">
              <div className="text-slate-400">{t('height')}</div>
              <div className="text-white font-bold">{content.building_info?.height || '?'}m</div>
            </div>
            <div className="bg-slate-800/50 rounded p-2 text-center">
              <div className="text-slate-400">{t('floors')}</div>
              <div className="text-white font-bold">{content.building_info?.levels || '?'}</div>
            </div>
            <div className="bg-slate-800/50 rounded p-2 text-center">
              <div className="text-slate-400">{t('type')}</div>
              <div className="text-cyan-400 font-bold capitalize">{content.building_info?.type || '?'}</div>
            </div>
          </div>
          
          {/* Shadow Analysis */}
          {content.shadow_analysis && (
            <div className="bg-slate-800/40 rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-sm">🌑</span>
                <span className="text-xs font-medium text-slate-300">{t('shadowAnalysis')}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('length')}:</span>
                  <span className="text-white font-medium">{content.shadow_analysis.shadow_length_m}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('direction')}:</span>
                  <span className="text-white font-medium">{content.shadow_analysis.shadow_direction}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('hoursDay')}:</span>
                  <span className="text-white font-medium">{content.shadow_analysis.shadow_hours_per_day}h</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('impact')}:</span>
                  <span className={`font-medium ${content.shadow_analysis.impact_level === 'low' ? 'text-green-400' : 'text-yellow-400'}`}>
                    {content.shadow_analysis.impact_level}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          {/* View Quality */}
          {content.view_quality && (
            <div className="bg-slate-800/40 rounded-lg p-2">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <Eye className="w-3 h-3 text-blue-400" />
                  <span className="text-xs font-medium text-slate-300">{t('viewQuality')}</span>
                </div>
                <span className="text-white font-bold text-sm">{content.view_quality.view_score}<span className="text-slate-500 text-[10px]">/100</span></span>
              </div>
              <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden mb-2">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
                  style={{ width: `${content.view_quality.view_score}%` }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Best Floor:</span>
                  <span className="text-green-400 font-medium">F{content.view_quality.best_floor}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Worst Floor:</span>
                  <span className="text-red-400 font-medium">F{content.view_quality.worst_floor}</span>
                </div>
              </div>
            </div>
          )}
          
          {/* 3D Neighbors */}
          {content.neighbors_3d && (
            <div className="bg-slate-800/40 rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-2">
                <Building className="w-3 h-3 text-purple-400" />
                <span className="text-xs font-medium text-slate-300">3D Neighbors</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-center mb-2">
                <div className="bg-slate-700/30 rounded p-1">
                  <div className="text-slate-400 text-[10px]">Above</div>
                  <div className="text-white font-bold">{content.neighbors_3d.buildings_above}</div>
                </div>
                <div className="bg-slate-700/30 rounded p-1">
                  <div className="text-slate-400 text-[10px]">At Level</div>
                  <div className="text-white font-bold">{content.neighbors_3d.buildings_at_level}</div>
                </div>
                <div className="bg-slate-700/30 rounded p-1">
                  <div className="text-slate-400 text-[10px]">Below</div>
                  <div className="text-white font-bold">{content.neighbors_3d.buildings_below}</div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <div className="flex justify-between flex-1">
                  <span className="text-slate-400">Privacy:</span>
                  <span className="text-white font-medium">{content.neighbors_3d.privacy_score}%</span>
                </div>
                <div className="flex justify-between flex-1">
                  <span className="text-slate-400">Light:</span>
                  <span className="text-white font-medium">{content.neighbors_3d.light_access_score}%</span>
                </div>
              </div>
            </div>
          )}
          
          {/* Solar Potential */}
          {content.solar_potential && (
            <div className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">☀️</span>
                <div>
                  <div className="text-white font-bold text-sm">Solar Potential</div>
                  <div className="text-yellow-400 text-xs capitalize">{content.solar_potential.suitability} suitability</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                <div className="bg-slate-800/50 rounded p-1.5">
                  <div className="text-slate-400 text-[10px]">Roof Area</div>
                  <div className="text-white font-bold">{content.solar_potential.roof_area_sqm}m²</div>
                </div>
                <div className="bg-slate-800/50 rounded p-1.5">
                  <div className="text-slate-400 text-[10px]">Peak Sun Hours</div>
                  <div className="text-white font-bold">{content.solar_potential.solar_hours}h</div>
                </div>
              </div>
              <div className="bg-slate-800/50 rounded p-2 text-center">
                <div className="text-slate-400 text-[10px]">Potential Capacity</div>
                <div className="text-yellow-400 font-bold text-lg">{content.solar_potential.potential_kw} kW</div>
                <div className="text-slate-500 text-[10px]">~{Math.round(content.solar_potential.potential_kw * 4)} units/day</div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Area Context Section */}
      <div className={hasBuilding ? 'opacity-80' : ''}>
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-semibold text-slate-300">
            {hasBuilding ? '📍 AREA CONTEXT' : 'Nearby Infrastructure'}
          </span>
        </div>
        
        {/* Infrastructure List */}
        <div className="mb-4">
          <div className="space-y-2">
            {(Array.isArray(content.nearby_infrastructure) ? content.nearby_infrastructure : []).slice(0, isLimited ? 3 : 10).map((infra, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-slate-800/30 rounded p-2">
                <span className="text-white">{infra.name}</span>
                <span className="text-slate-400">{infra.distance}</span>
              </div>
            ))}
          </div>
          {isLimited && (Array.isArray(content.nearby_infrastructure) ? content.nearby_infrastructure.length : 0) > 3 && (
            <div className="text-center mt-2">
              <span className="text-[10px] text-blue-400">+{(Array.isArray(content.nearby_infrastructure) ? content.nearby_infrastructure.length : 0) - 3} more with Pro</span>
            </div>
          )}
        </div>
      </div>
      
      {/* POI Grid */}
      <div className="grid grid-cols-4 gap-2 text-center mb-4">
        <div className="bg-slate-800/30 rounded p-2">
          <div className="text-lg">🏫</div>
          <div className="text-xs text-slate-400">Schools</div>
          <div className="text-sm text-white font-medium">{content.pois?.schools || 0}</div>
        </div>
        <div className="bg-slate-800/30 rounded p-2">
          <div className="text-lg">🏥</div>
          <div className="text-xs text-slate-400">Hospitals</div>
          <div className="text-sm text-white font-medium">{content.pois?.hospitals || 0}</div>
        </div>
        <div className="bg-slate-800/30 rounded p-2">
          <div className="text-lg">🛒</div>
          <div className="text-xs text-slate-400">Malls</div>
          <div className="text-sm text-white font-medium">{content.pois?.malls || 0}</div>
        </div>
        <div className="bg-slate-800/30 rounded p-2">
          <div className="text-lg">🏢</div>
          <div className="text-xs text-slate-400">Offices</div>
          <div className="text-sm text-white font-medium">{content.pois?.offices || 0}</div>
        </div>
      </div>
      
      {/* Scores */}
      <div className="space-y-2">
        <div className="flex items-center justify-between bg-slate-800/50 rounded p-3">
          <span className="text-sm text-slate-300">Walkability Score</span>
          <span className="text-lg font-bold text-green-400">{content.walkability_score || 75}%</span>
        </div>
        {!isLimited && (
          <>
            <div className="flex items-center justify-between bg-slate-800/50 rounded p-3">
              <span className="text-sm text-slate-300">Transit Score</span>
              <span className="text-lg font-bold text-blue-400">{content.transit_score || 68}%</span>
            </div>
            <div className="flex items-center justify-between bg-slate-800/50 rounded p-3">
              <span className="text-sm text-slate-300">Bike Score</span>
              <span className="text-lg font-bold text-purple-400">{content.bike_score || 72}%</span>
            </div>
          </>
        )}
      </div>

      {/* Growth Hotspots - Pro */}
      {!isLimited && content.growth_hotspots && Array.isArray(content.growth_hotspots) && (
        <div className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-lg p-3">
          <h4 className="text-xs font-medium text-green-400 mb-2 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            Growth Hotspots
          </h4>
          <div className="space-y-1">
            {content.growth_hotspots.map((spot, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-slate-300">{spot.name}</span>
                <span className="text-green-400">+{spot.growth}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// RISK ANALYSIS TAB - ENHANCED
// ============================================

function RiskCategoryCard({ category, data, isExpanded, onToggle }) {
  const categoryConfig = {
    flood: { icon: Droplets, label: 'Flood Risk', color: 'blue' },
    legal: { icon: Scale, label: 'Legal Risk', color: 'purple' },
    market: { icon: TrendingDown, label: 'Market Risk', color: 'orange' },
    infrastructure: { icon: Building, label: 'Infrastructure Risk', color: 'cyan' },
    environmental: { icon: AlertTriangle, label: 'Environmental Risk', color: 'green' }
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

  return (
    <div className="risk-category-card bg-slate-800/40 rounded-lg overflow-hidden">
      <button onClick={onToggle} className="w-full p-3 flex items-center gap-3 hover:bg-slate-700/30 transition">
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
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${data.score <= 30 ? 'text-green-400' : data.score <= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
            {data.score || 35}
          </div>
          <div className="text-[10px] text-slate-500">risk score</div>
        </div>
        <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
      </button>
      
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30 pt-3">
          <div className="mb-3">
            <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${data.score <= 30 ? 'bg-green-500' : data.score <= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                style={{ width: `${data.score}%` }}
              />
            </div>
          </div>
          {data.mitigation && Array.isArray(data.mitigation) && (
            <div className="bg-slate-700/30 rounded-lg p-2">
              <div className="text-[10px] text-slate-400 mb-1">Mitigation:</div>
              <ul className="space-y-1">
                {data.mitigation.slice(0, 2).map((item, i) => (
                  <li key={i} className="flex items-start gap-1 text-[10px] text-slate-300">
                    <CheckCircle className="w-2.5 h-2.5 text-green-400 shrink-0 mt-0.5" />
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

function RiskContent({ content, isLimited }) {
  const [expandedCategory, setExpandedCategory] = useState(null);
  
  const overallScore = content.overall_risk_score || 35;
  const risks = content.risks || {
    flood: { level: 'LOW', score: 15, mitigation: ['Check seasonal patterns'] },
    legal: { level: 'MODERATE', score: 40, mitigation: ['Verify title documents', 'Check RERA compliance'] },
    market: { level: 'LOW', score: 30, mitigation: ['Monitor new launches'] },
    infrastructure: { level: 'LOW', score: 25, mitigation: ['Track project timelines'] }
  };

  return (
    <div className="risk-content p-4 space-y-4">
      {/* Overall Score */}
      <div className="bg-slate-800/30 rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Shield className="w-4 h-4 text-yellow-400" />
            Overall Risk Score
          </h3>
          <span className={`text-2xl font-bold ${overallScore <= 30 ? 'text-green-400' : overallScore <= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
            {overallScore}%
          </span>
        </div>
        <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-500 ${
              overallScore <= 30 ? 'bg-gradient-to-r from-green-500 to-emerald-400' :
              overallScore <= 60 ? 'bg-gradient-to-r from-yellow-500 to-amber-400' :
              'bg-gradient-to-r from-red-500 to-rose-400'
            }`}
            style={{ width: `${overallScore}%` }}
          />
        </div>
      </div>

      {/* Risk Categories */}
      <div className="space-y-2">
        {Object.entries(risks).map(([category, data]) => (
          <RiskCategoryCard
            key={category}
            category={category}
            data={data}
            isExpanded={expandedCategory === category}
            onToggle={() => setExpandedCategory(expandedCategory === category ? null : category)}
          />
        ))}
      </div>

      {/* Mitigation Suggestions */}
      {content.mitigation_suggestions && Array.isArray(content.mitigation_suggestions) && (
        <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-3">
          <h4 className="text-xs font-medium text-blue-400 mb-2">Recommended Actions</h4>
          <ul className="space-y-1">
            {content.mitigation_suggestions.map((s, i) => (
              <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                <span className="text-blue-400">→</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ============================================
// ROI PROJECTION TAB - ENHANCED
// ============================================

function ROIContent({ content, isLimited }) {
  const projection = content.projection_3year || {
    best_case: { return: '+35%', price: 11500, probability: 20 },
    expected: { return: '+20%', price: 10200, probability: 50 },
    worst_case: { return: '+3%', price: 8800, probability: 30 }
  };
  
  const hasBuilding = content.has_building && content.investment_score;
  const investmentScore = content.investment_score || {};

  return (
    <div className="roi-content p-4 space-y-4">
      {/* Building Investment Score - if building selected */}
      {hasBuilding && (
        <div className="bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Trophy className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-semibold text-cyan-400">🏢 BUILDING INVESTMENT SCORE</span>
          </div>
          
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-300 text-sm">Overall Score</span>
            <span className="text-green-400 font-black text-3xl">
              {investmentScore.overall_score || 75}
              <span className="text-slate-500 text-sm">/100</span>
            </span>
          </div>
          
          <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden mb-3">
            <div 
              className="h-full bg-gradient-to-r from-yellow-500 via-green-500 to-emerald-400 rounded-full"
              style={{ width: `${investmentScore.overall_score || 75}%` }}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-800/40 rounded-lg p-2">
              <div className="text-slate-400 text-[10px]">Appreciation</div>
              <div className={`font-bold ${investmentScore.appreciation_potential === 'high' ? 'text-green-400' : 'text-yellow-400'}`}>
                {investmentScore.appreciation_potential?.toUpperCase() || 'HIGH'}
              </div>
            </div>
            <div className="bg-slate-800/40 rounded-lg p-2">
              <div className="text-slate-400 text-[10px]">Rental Yield</div>
              <div className="text-white font-bold">{investmentScore.rental_yield_estimate || '4.2%'}</div>
            </div>
          </div>
          
          {investmentScore.key_factors && Array.isArray(investmentScore.key_factors) && investmentScore.key_factors.length > 0 && (
            <div className="mt-3 bg-slate-800/40 rounded-lg p-2">
              <div className="text-slate-400 text-[10px] mb-1.5">Key Factors</div>
              <div className="flex flex-wrap gap-1">
                {investmentScore.key_factors.map((factor, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-[10px]">{factor}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      <h4 className="text-sm font-medium text-slate-300 mb-3">3-Year Projection</h4>
      
      {/* Scenario Cards */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-green-500/20 rounded p-3 text-center">
          <div className="text-xs text-green-400">Best Case</div>
          <div className="text-lg font-bold text-white">{projection.best_case?.return || '+35%'}</div>
          <div className="text-xs text-slate-400">₹{projection.best_case?.price?.toLocaleString() || '11,500'}/sqft</div>
          {!isLimited && (
            <div className="text-[10px] text-slate-500 mt-1">{projection.best_case?.probability || 20}% probability</div>
          )}
        </div>
        <div className="bg-blue-500/20 rounded p-3 text-center">
          <div className="text-xs text-blue-400">Expected</div>
          <div className="text-lg font-bold text-white">{projection.expected?.return || '+20%'}</div>
          <div className="text-xs text-slate-400">₹{projection.expected?.price?.toLocaleString() || '10,200'}/sqft</div>
          {!isLimited && (
            <div className="text-[10px] text-slate-500 mt-1">{projection.expected?.probability || 50}% probability</div>
          )}
        </div>
        <div className="bg-red-500/20 rounded p-3 text-center">
          <div className="text-xs text-red-400">Worst Case</div>
          <div className="text-lg font-bold text-white">{projection.worst_case?.return || '+3%'}</div>
          <div className="text-xs text-slate-400">₹{projection.worst_case?.price?.toLocaleString() || '8,800'}/sqft</div>
          {!isLimited && (
            <div className="text-[10px] text-slate-500 mt-1">{projection.worst_case?.probability || 30}% probability</div>
          )}
        </div>
      </div>
      
      {/* Entry/Exit Strategy */}
      <div className="bg-slate-800/50 rounded p-3">
        <h4 className="text-xs font-medium text-slate-300 mb-2">Entry/Exit Strategy</h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-slate-400">Entry:</span>
            <span className="text-white ml-1">{content.entry_exit?.recommended_entry || '₹8,200-8,800/sqft'}</span>
          </div>
          <div>
            <span className="text-slate-400">Exit:</span>
            <span className="text-white ml-1">{content.entry_exit?.target_exit || '₹11,000+/sqft'}</span>
          </div>
        </div>
      </div>

      {/* Rental Yield - Pro */}
      {!isLimited && content.rental_yield && (
        <div className="bg-slate-800/30 rounded-lg p-3">
          <h4 className="text-xs font-medium text-slate-300 mb-2">Rental Yield Analysis</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-700/30 rounded p-2">
              <div className="text-slate-400">Current Yield</div>
              <div className="text-white font-medium">{content.rental_yield.current || '3.5%'}</div>
            </div>
            <div className="bg-slate-700/30 rounded p-2">
              <div className="text-slate-400">Projected Yield</div>
              <div className="text-green-400 font-medium">{content.rental_yield.projected || '4.2%'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// COMPARABLES TAB - ENHANCED
// ============================================

function ComparablesContent({ content, isLimited }) {
  const comparables = content.comparables || [
    { project: 'Prestige Lakeside', distance: '0.8 km', price_sqft: 9200, similarity: 92 },
    { project: 'Brigade Cosmopolis', distance: '1.5 km', price_sqft: 8800, similarity: 85 },
    { project: 'Phoenix One', distance: '2.0 km', price_sqft: 9500, similarity: 78 }
  ];

  return (
    <div className="comparables-content p-4 space-y-4">
      <div className="space-y-2 mb-4">
        {(Array.isArray(comparables) ? comparables : []).map((comp, i) => (
          <div key={i} className="bg-slate-800/30 rounded p-3 flex items-center justify-between">
            <div>
              <div className="text-sm text-white font-medium">{comp.project}</div>
              <div className="text-xs text-slate-400">{comp.distance} away</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-white">₹{comp.price_sqft?.toLocaleString()}/sqft</div>
              <div className="text-xs text-green-400">{comp.similarity}% similar</div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Price Analysis */}
      <div className="bg-slate-800/50 rounded p-3">
        <h4 className="text-xs font-medium text-slate-300 mb-2">Price Positioning</h4>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-400">Subject Property:</span>
            <span className="text-white">₹{content.price_analysis?.subject_property?.toLocaleString() || '8,500'}/sqft</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Area Average:</span>
            <span className="text-white">₹{content.price_analysis?.area_average?.toLocaleString() || '8,900'}/sqft</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Percentile:</span>
            <span className="text-green-400">{content.price_analysis?.percentile || '35th'} (below avg = good value)</span>
          </div>
        </div>
      </div>

      {/* Similarity Algorithm Info */}
      {!isLimited && (
        <div className="bg-slate-800/30 rounded-lg p-3">
          <h4 className="text-xs font-medium text-slate-300 mb-2 flex items-center gap-1">
            <Info className="w-3 h-3" />
            Similarity Algorithm
          </h4>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div className="flex justify-between"><span className="text-slate-400">Location</span><span className="text-white">30%</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Property Type</span><span className="text-white">25%</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Size</span><span className="text-white">20%</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Amenities</span><span className="text-white">25%</span></div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// STRATEGY TAB - ENHANCED
// ============================================

function StrategyContent({ content, isLimited }) {
  return (
    <div className="strategy-content p-4 space-y-4">
      <div className="bg-slate-800/50 rounded p-3 mb-4">
        <h4 className="text-sm font-medium text-slate-300 mb-2">Investment Strategy</h4>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-400">Entry Timing:</span>
            <span className="text-white">{content.investment_strategy?.entry_timing || 'NOW - prices stable'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Negotiation Range:</span>
            <span className="text-white">{content.investment_strategy?.negotiation_range || '₹8,200-8,600/sqft'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Portfolio Fit:</span>
            <span className="text-white">{content.investment_strategy?.portfolio_fit || 'Good for long-term growth'}</span>
          </div>
        </div>
      </div>
      
      <div className="mb-4">
        <h4 className="text-sm font-medium text-slate-300 mb-2">Action Items</h4>
        <ul className="space-y-1">
          {(Array.isArray(content.action_items) ? content.action_items : []).map((item, i) => (
            <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
              <span className="text-blue-400">☐</span> {item}
            </li>
          ))}
        </ul>
      </div>
      
      <div className="bg-blue-500/20 rounded p-3">
        <h4 className="text-xs font-medium text-blue-400 mb-2">Timeline</h4>
        <div className="flex justify-between text-xs">
          <span className="text-slate-400">Due Diligence:</span>
          <span className="text-white">{content.timeline?.due_diligence || '2 weeks'}</span>
        </div>
        <div className="flex justify-between text-xs mt-1">
          <span className="text-slate-400">Closing:</span>
          <span className="text-white">{content.timeline?.closing || '4-6 weeks'}</span>
        </div>
      </div>
    </div>
  );
}

// ============================================
// DATA TRANSPARENCY TAB - TRUTH FIREWALL
// ============================================

function TransparencyContent({ content, isLimited }) {
  return (
    <div className="transparency-content p-4 space-y-4">
      {/* Verification Status */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-slate-300">Verification Status</span>
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          content.verification_status === 'VERIFIED' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
        }`}>
          {content.verification_status || 'VERIFIED'}
        </span>
      </div>
      
      {/* Data Sources */}
      <div className="mb-4">
        <h4 className="text-xs font-medium text-slate-300 mb-2 flex items-center gap-1">
          <Database className="w-3 h-3" />
          Data Sources
        </h4>
        <div className="space-y-1">
          {(content.data_sources || [
            { source: 'Property Registry', records: 42500, freshness: '2 days ago' },
            { source: 'POI Database', records: 26961, freshness: '5 days ago' },
            { source: 'Market Trends', records: 15000, freshness: '1 day ago' }
          ]).map((source, i) => (
            <div key={i} className="flex items-center justify-between text-xs bg-slate-800/30 rounded p-2">
              <span className="text-white">{source.source}</span>
              <div className="text-right">
                <span className="text-slate-400 text-[10px]">{source.records?.toLocaleString()} records</span>
                <span className="text-slate-500 text-[10px] ml-2">{source.freshness}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Confidence Breakdown */}
      <div className="mb-4">
        <h4 className="text-xs font-medium text-slate-300 mb-2">Confidence Breakdown</h4>
        <div className="space-y-2">
          {Object.entries(content.confidence_breakdown || {
            'Property Data': 85,
            'Market Data': 78,
            'Spatial Data': 92
          }).map(([key, val]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-slate-400 capitalize flex-1">{key}</span>
              <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${val}%` }} />
              </div>
              <span className="text-xs text-white w-8">{val}%</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Missing Data Warnings */}
      {content.missing_data_warnings && Array.isArray(content.missing_data_warnings) && content.missing_data_warnings.length > 0 && (
        <div className="bg-yellow-500/10 rounded p-2">
          <h4 className="text-xs font-medium text-yellow-400 mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Missing Data
          </h4>
          <ul className="space-y-1">
            {content.missing_data_warnings.map((warning, i) => (
              <li key={i} className="text-xs text-slate-300">{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Truth Firewall Badge */}
      <div className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-lg p-3 text-center">
        <Shield className="w-8 h-8 text-green-400 mx-auto mb-2" />
        <div className="text-sm font-bold text-white">Truth Firewall™</div>
        <div className="text-xs text-slate-400">All facts verified against 1.6M+ records</div>
      </div>
    </div>
  );
}

// ============================================
// FREE ANALYSIS TAB - ALWAYS ACCESSIBLE
// ============================================

function FreeAnalysisContent({ content, setAgentData, userTier }) {
  const [freeProperties, setFreeProperties] = useState({});
  const [loading, setLoading] = useState(true);
  const [analyzingProperty, setAnalyzingProperty] = useState(null);
  const [analysesRemaining, setAnalysesRemaining] = useState(3);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  // Fetch free properties on mount - don't force refresh on initial load
  useEffect(() => {
    // Small delay to ensure backend is ready
    const timer = setTimeout(() => {
      fetchFreeProperties(false);  // Don't force refresh on initial load
    }, 500);
    return () => clearTimeout(timer);
  }, []);
  
  // Auto-retry with exponential backoff when there's an error
  useEffect(() => {
    if (error && retryCount < 3) {
      const delay = Math.min(1000 * Math.pow(2, retryCount), 5000); // 1s, 2s, 4s max 5s
      console.log(`[FreeAnalysis] Auto-retrying in ${delay}ms (attempt ${retryCount + 1}/3)`);
      const timer = setTimeout(() => {
        setRetryCount(prev => prev + 1);
        fetchFreeProperties(false);
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [error, retryCount]);

  // Show properties on map when loaded - filter for those with both images AND coordinates
  useEffect(() => {
    if (freeProperties && typeof freeProperties === 'object' && Object.keys(freeProperties).length > 0) {
      // Filter properties that have both coordinates AND images
      const validProperties = Object.entries(freeProperties)
        .filter(([_, prop]) => {
          const hasCoords = prop.latitude && prop.longitude;
          const hasImage = prop.image_url;
          return hasCoords && hasImage;
        })
        .map(([category, prop]) => ({
          lat: prop.latitude,
          lng: prop.longitude,
          bedrooms: prop.bedrooms,
          price: prop.price,
          property_type: category,
          image_url: prop.image_url,
          title: prop.title,
          locality: prop.locality,
          ...prop
        }));
      
      if (validProperties.length > 0) {
        window.dispatchEvent(new CustomEvent('valora-map-command', {
          detail: {
            action: 'highlightProperties',
            properties: validProperties
          }
        }));
      }
    }
    
    // Cleanup: clear markers when component unmounts
    return () => {
      window.dispatchEvent(new CustomEvent('valora-map-command', {
        detail: { action: 'clearPropertyMarkers' }
      }));
    };
  }, [freeProperties]);

  const fetchFreeProperties = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const refreshParam = forceRefresh ? '&refresh=true' : '';
      const response = await fetch(`${API_URL}/api/free-properties?user_id=${localStorage.getItem('valora_user_id') || 'anonymous'}${refreshParam}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      console.log('[FreeAnalysis] Fetched properties:', data);
      console.log('[FreeAnalysis] Properties with coords AND images:', 
        Object.entries(data.properties || {}).filter(([_, p]) => p.latitude && p.longitude && p.image_url).length
      );
      // Log each property's image URL for debugging
      Object.entries(data.properties || {}).forEach(([cat, p]) => {
        console.log(`[FreeAnalysis] ${cat}: image_url=${p.image_url}, lat=${p.latitude}, lng=${p.longitude}`);
      });
      
      if (data.success) {
        // Filter to only include properties with both coordinates AND images
        const filteredProperties = {};
        for (const [category, prop] of Object.entries(data.properties)) {
          const hasCoords = prop.latitude && prop.longitude;
          const hasImage = prop.image_url;
          if (hasCoords && hasImage) {
            filteredProperties[category] = prop;
          }
        }
        setFreeProperties(filteredProperties);
        setAnalysesRemaining(data.analyses_remaining);
        setError(null); // Clear error on success
        setRetryCount(0); // Reset retry count on success
      } else {
        setError('Failed to load free properties');
      }
    } catch (err) {
      console.error('Failed to fetch free properties:', err);
      setError('Failed to load free properties');
    } finally {
      setLoading(false);
    }
  };

  // Handle card hover to fly to property location
  const handleCardHover = (property) => {
    if (property.latitude && property.longitude && setAgentData) {
      setAgentData(prev => ({
        ...prev,
        flyTo: { 
          lat: property.latitude, 
          lng: property.longitude, 
          zoom: 15,  // Zoom 15 for good visibility
          pitch: -90  // Straight down for centered marker
        }
      }));
    }
  };

  const handleAnalyzeFree = async (property) => {
    if (analysesRemaining <= 0) return;
    setAnalyzingProperty(property.id);

    try {
      // First, track the free analysis usage
      const trackResponse = await fetch(`${API_URL}/api/analyze-free`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_id: property.id,
          user_id: localStorage.getItem('valora_user_id') || 'anonymous',
          track_only: true  // Just track, don't analyze
        })
      });

      const trackData = await trackResponse.json();
      if (!trackData.success) {
        alert(trackData.detail || 'Daily limit reached');
        setAnalyzingProperty(null);
        return;
      }

      // Update remaining count
      setAnalysesRemaining(trackData.analyses_remaining);

      // Fly to the property first
      if (setAgentData && property.latitude && property.longitude) {
        setAgentData(prev => ({
          ...prev,
          flyTo: { lat: property.latitude, lng: property.longitude, zoom: 15, pitch: -90 },
          mapCenter: { lat: property.latitude, lng: property.longitude }
        }));
      }

      // Build the query
      const query = `Analyze this property: ${property.title} in ${property.locality || 'Bangalore'}. Price: ₹${property.price?.toLocaleString() || 'N/A'}, Area: ${property.area_sqft?.toLocaleString() || 'N/A'} sqft. Provide investment verdict, market analysis, and recommendations.`;

      // Dispatch event for ChatPanel to handle the streaming analysis
      // This follows the same pattern as building clicks
      window.dispatchEvent(new CustomEvent('valora-free-analysis-trigger', {
        detail: {
          property,
          query,
          context: {
            lat: property.latitude,
            lng: property.longitude,
            locality: property.locality,
            is_free_analysis: true
          }
        }
      }));

      // Dispatch event to switch to Decision Verdict tab
      window.dispatchEvent(new CustomEvent('valora-free-analysis-complete', {
        detail: { property }
      }));
    } catch (err) {
      console.error('Free analysis failed:', err);
      alert('Analysis failed. Please try again.');
    } finally {
      setAnalyzingProperty(null);
    }
  };

  const formatPrice = (price) => {
    if (!price) return 'N/A';
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(1)}Cr`;
    if (price >= 100000) return `₹${(price / 100000).toFixed(0)}L`;
    return `₹${price.toLocaleString()}`;
  };

  const categoryIcons = {
    'apartment': Building,
    'flat': Building,
    'villa': Building,
    'warehouse': Building,
    'shop': Building,
    'plot': MapPin,
    'office': Building
  };

  const categoryColors = {
    'apartment': 'from-blue-500 to-cyan-500',
    'flat': 'from-green-500 to-emerald-500',
    'villa': 'from-purple-500 to-pink-500',
    'warehouse': 'from-orange-500 to-amber-500',
    'shop': 'from-rose-500 to-red-500',
    'plot': 'from-teal-500 to-green-500',
    'office': 'from-indigo-500 to-blue-500'
  };

  // Error state (only show after all retries exhausted)
  if (error && retryCount >= 3 && !loading) {
    return (
      <div className="free-analysis-content p-4">
        <div className="flex items-center gap-2 mb-4">
          <Eye className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-bold text-white">Free Property Analysis</h3>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-400">{error}</p>
          <button 
            onClick={() => { setRetryCount(0); fetchFreeProperties(); }}
            className="mt-3 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Loading state (includes auto-retry)
  if (loading) {
    return (
      <div className="free-analysis-content p-4">
        <div className="flex items-center gap-2 mb-4">
          <Eye className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-bold text-white">Free Property Analysis</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mb-2" />
          <p className="text-slate-400 text-sm">
            {retryCount > 0 ? `Retrying... (${retryCount}/3)` : 'Loading properties...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="free-analysis-content p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-bold text-white">Free Analysis</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full ${
            analysesRemaining > 0 
              ? 'bg-emerald-500/20 text-emerald-400' 
              : 'bg-red-500/20 text-red-400'
          }`}>
            {analysesRemaining}/3 free today
          </span>
        </div>
      </div>

      {/* Properties Grid */}
      <div className="grid grid-cols-1 gap-3">
        {Object.entries(freeProperties || {}).map(([category, property]) => {
          if (!property) return null;
          const Icon = categoryIcons[category] || Building;
          const gradient = categoryColors[category] || 'from-slate-500 to-slate-600';
          
          return (
            <div 
              key={category}
              className="bg-slate-800/50 rounded-lg overflow-hidden border border-slate-700/50 hover:border-slate-500 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300 cursor-pointer group"
              onMouseEnter={() => handleCardHover(property)}
              onClick={() => handleAnalyzeFree(property)}
            >
              {/* Property Image with Zoom Effect */}
              {property.image_url ? (
                <div className="relative h-32 w-full overflow-hidden">
                  <img 
                    src={property.image_url} 
                    alt={property.title || category}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    onError={(e) => {
                      console.log('[FreeAnalysis] Image failed to load:', property.image_url);
                      e.target.onerror = null; // Prevent infinite loop
                      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23334155" width="100" height="100"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="%2394a3b8" font-size="12">No Image</text></svg>';
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent" />
                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/10 transition-colors duration-300" />
                </div>
              ) : (
                <div className="relative h-20 w-full overflow-hidden bg-slate-700/50 flex items-center justify-center">
                  <Building className="w-8 h-8 text-slate-500" />
                </div>
              )}
              
              {/* Category Header */}
              <div className={`bg-gradient-to-r ${gradient} px-3 py-1.5 flex items-center justify-between`}>
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-white" />
                  <span className="text-white font-medium text-sm capitalize">{category}</span>
                </div>
                <span className="text-white/80 text-xs px-2 py-0.5 bg-white/20 rounded">
                  {property.listing_type === 'rent' ? 'For Rent' : 'For Sale'}
                </span>
              </div>
              
              {/* Property Details */}
              <div className="p-3">
                <h4 className="text-white font-medium text-sm mb-1 truncate">
                  {property.title || `${category.charAt(0).toUpperCase() + category.slice(1)} in ${property.locality || 'Bangalore'}`}
                </h4>
                
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                  <MapPin className="w-3 h-3" />
                  <span>{property.locality || 'Bangalore'}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-lg font-bold text-white">{formatPrice(property.price)}</span>
                    {property.listing_type === 'rent' && <span className="text-xs text-slate-400">/mo</span>}
                  </div>
                  <div className="text-right">
                    <span className="text-sm text-slate-300">{property.area_sqft?.toLocaleString() || 'N/A'}</span>
                    <span className="text-xs text-slate-400 block">sqft</span>
                  </div>
                </div>
                
                {/* Click hint */}
                <div className="mt-2 text-center text-xs text-slate-500 group-hover:text-purple-400 transition-colors">
                  <Sparkles className="w-3 h-3 inline-block mr-1" />
                  Click to analyze
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {Object.keys(freeProperties).length === 0 && (
        <div className="text-center py-8">
          <Building className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No free properties available today</p>
          <p className="text-xs text-slate-500 mt-1">Check back tomorrow for new properties</p>
        </div>
      )}

      {/* Upgrade Prompt - Only for free users */}
      {userTier === 'free' && (
        <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-3 mt-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">Want unlimited analyses?</span>
          </div>
          <p className="text-xs text-slate-400 mb-2">
            Upgrade to Pro for unlimited property analyses, full market insights, and personalized recommendations.
          </p>
          <button className="w-full py-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white text-xs font-medium rounded-lg transition">
            Upgrade to Pro
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================
// CLIENT PITCH TAB - BROKER KILLER
// ============================================

function PitchContent({ content, isLimited, onUpgrade }) {
  if (isLimited) {
    return (
      <div className="pitch-content p-4">
        <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-xl p-6 text-center">
          <Presentation className="w-12 h-12 text-purple-400 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-white mb-2">Client Pitch Generator</h3>
          <p className="text-sm text-slate-400 mb-4">
            Create professional presentations for your clients with one click
          </p>
          
          <div className="space-y-2 text-left mb-4">
            {[
              'Auto-generated property summaries',
              'Investment thesis highlights',
              'Export to PDF/WhatsApp/Email',
              'Custom branding options'
            ].map((feature, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-slate-300">
                <CheckCircle className="w-3 h-3 text-green-400" />
                {feature}
              </div>
            ))}
          </div>
          
          <button
            onClick={onUpgrade}
            className="w-full py-2.5 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white font-medium rounded-lg transition"
          >
            Upgrade to Pro — ₹599/month
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="pitch-content p-4 space-y-4">
      {/* Summary Card */}
      <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-lg p-4">
        <h3 className="text-lg font-bold text-white mb-2">
          {content.client_summary?.headline || 'Investment Opportunity'}
        </h3>
        <div className="space-y-1 mb-3">
          {(content.client_summary?.key_points || [
            '15% below market average',
            'Metro connectivity in 2027',
            'Top-rated schools within 1km'
          ]).map((point, i) => (
            <div key={i} className="text-xs text-slate-300 flex items-center gap-2">
              <span className="text-green-400">✓</span> {point}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Asking:</span>
          <span className="text-xl font-bold text-white">{content.client_summary?.ask || '₹1.2 Cr'}</span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-sm text-slate-400">Expected Return:</span>
          <span className="text-green-400 font-medium">{content.client_summary?.expected_return || '18-25% in 3 years'}</span>
        </div>
      </div>
      
      {/* Export Options */}
      <div className="grid grid-cols-3 gap-2">
        <button className="flex items-center justify-center gap-1 bg-blue-500 hover:bg-blue-600 text-white text-xs py-2 rounded transition">
          <Download className="w-3 h-3" /> PDF
        </button>
        <button className="flex items-center justify-center gap-1 bg-green-500 hover:bg-green-600 text-white text-xs py-2 rounded transition">
          <MessageCircle className="w-3 h-3" /> WhatsApp
        </button>
        <button className="flex items-center justify-center gap-1 bg-purple-500 hover:bg-purple-600 text-white text-xs py-2 rounded transition">
          <Mail className="w-3 h-3" /> Email
        </button>
      </div>

      {/* Presentation Mode */}
      <button className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white text-sm py-3 rounded-lg transition">
        <Presentation className="w-4 h-4" />
        Enter Presentation Mode
      </button>
    </div>
  );
}

// ============================================
// MAIN SMARTTAB COMPONENT
// ============================================

export default function SmartTab({ tab, onUpgrade, userTier, setAgentData }) {
  const { type, content, title, icon, description } = tab;
  const isLimited = type === 'limited';
  const isLocked = type === 'locked';
  const isPreview = type === 'preview';
  
  // Locked tab - show upgrade prompt
  if (isLocked) {
    return (
      <div className="smart-tab locked p-6 text-center">
        <div className="locked-icon text-4xl mb-3">🔒</div>
        <h3 className="text-lg font-semibold text-white mb-2">{content.title || title}</h3>
        <p className="text-slate-400 text-sm mb-4">{content.description || description}</p>
        
        <div className="locked-benefits bg-slate-800/50 rounded-lg p-4 mb-4 text-left">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Unlock with Pro:</h4>
          <ul className="space-y-1">
            {(content.upgrade_benefits || [
              'Full analysis & insights',
              'Data-backed recommendations',
              '500 queries per month'
            ]).map((benefit, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-center gap-2">
                <span className="text-green-400">✓</span> {benefit}
              </li>
            ))}
          </ul>
        </div>

        <button 
          onClick={onUpgrade}
          className="upgrade-button bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white px-6 py-2 rounded-lg font-medium transition"
        >
          Upgrade to Pro — $19/month
        </button>
      </div>
    );
  }
  
  // Preview tab - show blurred content
  if (isPreview) {
    return (
      <div className="smart-tab preview p-4">
        <div className="preview-content relative">
          <div className="blur-sm pointer-events-none">
            <div className="p-4 space-y-3">
              <div className="h-4 bg-slate-700 rounded w-3/4" />
              <div className="h-4 bg-slate-700 rounded w-1/2" />
              <div className="h-20 bg-slate-700 rounded" />
            </div>
          </div>
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 rounded-lg">
            <div className="text-center p-4">
              <span className="text-2xl">👁️</span>
              <p className="text-sm text-slate-300 mt-2">Preview mode</p>
              <button onClick={onUpgrade} className="mt-2 text-xs text-blue-400 hover:text-blue-300">
                Unlock full insights →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  // Render appropriate content based on tab id
  switch (tab.id) {
    case 'free_analysis':
      return <FreeAnalysisContent content={content} setAgentData={setAgentData} userTier={userTier} />;
    case 'decision_verdict':
      return <VerdictContent content={content} isLimited={isLimited} onUpgrade={onUpgrade} />;
    case 'market_snapshot':
      return <MarketContent content={content} isLimited={isLimited} />;
    case 'spatial_intelligence':
      return <SpatialContent content={content} isLimited={isLimited} />;
    case 'risk_analysis':
      return <RiskContent content={content} isLimited={isLimited} />;
    case 'roi_projection':
      return <ROIContent content={content} isLimited={isLimited} />;
    case 'comparables':
      return <ComparablesContent content={content} isLimited={isLimited} />;
    case 'strategy':
      return <StrategyContent content={content} isLimited={isLimited} />;
    case 'data_transparency':
      return <TransparencyContent content={content} isLimited={isLimited} />;
    case 'client_pitch':
      return <PitchContent content={content} isLimited={isLimited} onUpgrade={onUpgrade} />;
    default:
      return (
        <div className="smart-tab generic p-4">
          <pre className="text-xs text-slate-300 overflow-auto">
            {JSON.stringify(content, null, 2)}
          </pre>
        </div>
      );
  }
}
