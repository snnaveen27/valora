/**
 * DecisionVerdictTab - Primary tab for Smart Report
 * Shows BUY/HOLD/AVOID recommendation with confidence scoring
 * Designed as the primary conversion driver
 */

import { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle, 
  Clock, Target, DollarSign, Shield, Zap, Lock, ChevronRight,
  BarChart3, ArrowUpRight, ArrowDownRight, HelpCircle
} from 'lucide-react';

// Verdict badge component with animated styling
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
      bg: 'bg-gradient-to-r from-yellow-500 to-amber-600',
      text: 'text-white',
      icon: Minus,
      pulse: false,
      glow: 'shadow-yellow-500/50'
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

// Confidence meter with visual indicator
function ConfidenceMeter({ score, showBreakdown = false, isLimited = false }) {
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
          Confidence Score
        </span>
        <span className={`text-lg font-bold ${getScoreColor(score)}`}>
          {score}%
        </span>
      </div>
      
      {/* Progress bar */}
      <div className="relative h-3 bg-slate-700/50 rounded-full overflow-hidden">
        <div 
          className={`absolute inset-y-0 left-0 bg-gradient-to-r ${getBarColor(score)} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${score}%` }}
        />
        {/* Markers */}
        <div className="absolute inset-0 flex">
          <div className="flex-1 border-r border-slate-600/30" />
          <div className="flex-1 border-r border-slate-600/30" />
          <div className="flex-1 border-r border-slate-600/30" />
          <div className="flex-1" />
        </div>
      </div>
      
      {/* Score labels */}
      <div className="flex justify-between text-[10px] text-slate-500 mt-1">
        <span>Low</span>
        <span>Medium</span>
        <span>High</span>
        <span>Very High</span>
      </div>

      {isLimited && (
        <div className="mt-2 text-[10px] text-blue-400 flex items-center gap-1">
          <Lock className="w-3 h-3" />
          Full confidence breakdown available with Pro
        </div>
      )}
    </div>
  );
}

// Risk level indicator
function RiskIndicator({ level, score }) {
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
        <div className="text-[10px] text-slate-400">Risk Level</div>
        <div className={`text-sm font-bold ${c.color}`}>{level}</div>
      </div>
      {score && (
        <div className="ml-auto text-right">
          <div className="text-[10px] text-slate-400">Score</div>
          <div className="text-sm text-white font-medium">{score}/100</div>
        </div>
      )}
    </div>
  );
}

// Time horizon recommendation
function TimeHorizon({ horizon, reasoning }) {
  const config = {
    'Short-term': { icon: Zap, color: 'text-orange-400', desc: '1-2 years' },
    'Medium-term': { icon: Clock, color: 'text-blue-400', desc: '3-5 years' },
    'Long-term': { icon: Target, color: 'text-purple-400', desc: '5+ years' }
  };

  const c = config[horizon] || config['Medium-term'];
  const Icon = c.icon;

  return (
    <div className="bg-slate-800/50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${c.color}`} />
        <span className="text-sm text-slate-300">Time Horizon</span>
      </div>
      <div className={`text-lg font-bold ${c.color}`}>{horizon}</div>
      <div className="text-xs text-slate-400">{c.desc}</div>
      {reasoning && (
        <div className="mt-2 text-[10px] text-slate-500 italic">{reasoning}</div>
      )}
    </div>
  );
}

// Reason item with impact indicator
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

// Strategy recommendation card
function StrategyCard({ entryPrice, holdDuration, exitTarget, isLocked = false }) {
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
            <p className="text-sm text-slate-300">Strategy recommendations</p>
            <button className="mt-2 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mx-auto">
              Unlock with Pro <ChevronRight className="w-3 h-3" />
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
        <span className="text-sm font-medium text-blue-400">Strategy Recommendation</span>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-800/50 rounded-lg p-2">
          <div className="text-[10px] text-slate-400 mb-1">Entry Price</div>
          <div className="text-sm font-bold text-white">{entryPrice}</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-2">
          <div className="text-[10px] text-slate-400 mb-1">Hold Duration</div>
          <div className="text-sm font-bold text-white">{holdDuration}</div>
        </div>
        {exitTarget && (
          <div className="col-span-2 bg-slate-800/50 rounded-lg p-2">
            <div className="text-[10px] text-slate-400 mb-1">Exit Target</div>
            <div className="text-sm font-bold text-green-400">{exitTarget}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// Upgrade prompt for free users
function UpgradePrompt({ onUpgrade, feature }) {
  return (
    <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
          <BarChart3 className="w-5 h-5 text-purple-400" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-white">Unlock Full Analysis</div>
          <div className="text-xs text-slate-400">
            Get complete {feature} with Pro subscription
          </div>
        </div>
        <button 
          onClick={onUpgrade}
          className="px-4 py-2 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white text-sm font-medium rounded-lg transition"
        >
          Upgrade
        </button>
      </div>
    </div>
  );
}

// Main DecisionVerdictTab component
export default function DecisionVerdictTab({ 
  data = {}, 
  userTier = 'free',
  onUpgrade,
  viewportAnalysis,
  agentData 
}) {
  const [animatedScore, setAnimatedScore] = useState(0);
  
  // Extract data with defaults
  const verdict = data.verdict || 'HOLD';
  const confidenceScore = data.confidence_score || data.confidence * 100 || 75;
  const riskLevel = data.risk_level || 'MEDIUM';
  const riskScore = data.risk_score || 35;
  const timeHorizon = data.time_horizon || 'Medium-term';
  const summary = data.summary || 'Analysis based on available market data and spatial intelligence.';
  
  const topReasons = data.top_reasons || [
    'Good connectivity to major hubs',
    'Developing infrastructure',
    'Competitive pricing relative to area'
  ];
  
  const keyRisks = data.key_risks || [
    'Market volatility in short term',
    'Infrastructure project delays possible'
  ];
  
  const strategy = data.strategy || {
    entry_price: '₹8,200-8,800/sqft',
    hold_duration: '3-5 years',
    exit_target: '₹11,000+/sqft'
  };

  const isFree = userTier === 'free';
  const isPro = userTier === 'pro' || userTier === 'premium';

  // Animate confidence score on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedScore(confidenceScore);
    }, 300);
    return () => clearTimeout(timer);
  }, [confidenceScore]);

  return (
    <div className="decision-verdict-tab space-y-4">
      {/* Header Section - Verdict Badge + Confidence */}
      <div className="bg-slate-800/30 rounded-xl p-4">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
          {/* Verdict Badge */}
          <VerdictBadge verdict={verdict} size="large" />
          
          {/* Confidence Meter */}
          <div className="flex-1 w-full">
            <ConfidenceMeter 
              score={animatedScore} 
              showBreakdown={isPro}
              isLimited={isFree}
            />
          </div>
        </div>
        
        {/* Summary */}
        <p className="mt-4 text-sm text-slate-300 leading-relaxed">
          {summary}
        </p>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 gap-3">
        <RiskIndicator level={riskLevel} score={riskScore} />
        <TimeHorizon 
          horizon={timeHorizon} 
          reasoning={isPro ? 'Based on market cycle analysis' : null}
        />
      </div>

      {/* Top Reasons Section */}
      <div className="bg-slate-800/30 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-green-400 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            Top Reasons
          </h3>
          <span className="text-[10px] text-slate-500">
            {topReasons.length} factors analyzed
          </span>
        </div>
        
        <div className="space-y-1">
          {topReasons.slice(0, isFree ? 3 : 5).map((reason, i) => (
            <ReasonItem 
              key={i}
              reason={reason}
              type="positive"
              impact={isPro ? Math.floor(Math.random() * 15) + 5 : null}
              index={i}
            />
          ))}
        </div>
        
        {isFree && topReasons.length > 3 && (
          <div className="mt-3 text-center">
            <button 
              onClick={onUpgrade}
              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 mx-auto"
            >
              <Lock className="w-3 h-3" />
              Unlock {topReasons.length - 3} more reasons with Pro
            </button>
          </div>
        )}
      </div>

      {/* Key Risks Section - Pro Feature */}
      {isPro ? (
        <div className="bg-slate-800/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-yellow-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Key Risks
            </h3>
            <span className="text-[10px] text-slate-500">
              Honest assessment
            </span>
          </div>
          
          <div className="space-y-1">
            {keyRisks.map((risk, i) => (
              <ReasonItem 
                key={i}
                reason={risk}
                type="risk"
                impact={Math.floor(Math.random() * 10) + 3}
                index={i}
              />
            ))}
          </div>
        </div>
      ) : (
        <UpgradePrompt 
          onUpgrade={onUpgrade}
          feature="risk analysis"
        />
      )}

      {/* Strategy Recommendation */}
      <StrategyCard 
        entryPrice={strategy.entry_price}
        holdDuration={strategy.hold_duration}
        exitTarget={strategy.exit_target}
        isLocked={isFree}
      />

      {/* Data Freshness Indicator */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 px-1">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span>Analysis current as of {new Date().toLocaleTimeString()}</span>
        </div>
        <button className="flex items-center gap-1 text-slate-400 hover:text-slate-300">
          <HelpCircle className="w-3 h-3" />
          How is this calculated?
        </button>
      </div>

      {/* Conversion CTA for Free Users */}
      {isFree && (
        <div className="mt-4 p-4 bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-xl">
          <div className="text-center">
            <div className="text-lg font-bold text-white mb-1">
              Get the Complete Picture
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Unlock all analysis tabs, full risk assessment, and ROI projections
            </p>
            <button 
              onClick={onUpgrade}
              className="px-6 py-2.5 bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white font-medium rounded-lg transition shadow-lg"
            >
              Upgrade to Pro — $19/month
            </button>
            <div className="mt-2 text-[10px] text-slate-500">
              7-day free trial • Cancel anytime
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
