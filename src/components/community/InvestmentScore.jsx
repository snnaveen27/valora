/**
 * InvestmentScore - Investment score card component
 * 
 * Features:
 * - Detailed investment score breakdown
 * - Component scores display
 * - Score explanation/tooltips
 * - Comparison with market average
 * - Rating badges and indicators
 * 
 * Props:
 * @param {Object} data - Investment score data from API
 * @param {boolean} loading - Loading state
 * @param {string} [error] - Error message
 * @param {boolean} [showDetails] - Whether to show detailed breakdown
 * @param {boolean} [compareToMarket] - Whether to show market comparison
 * @param {function} [onRefresh] - Refresh handler
 * @param {function} [onUpgrade] - Upgrade handler for premium features
 */

import { useState, useMemo } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  RefreshCw, 
  Lock, 
  Info, 
  Star,
  Target,
  BarChart3,
  Home,
  Building,
  Users,
  Clock,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';

// Score thresholds
const SCORE_RATINGS = [
  { min: 80, label: 'Excellent', color: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30' },
  { min: 60, label: 'Good', color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30' },
  { min: 40, label: 'Average', color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
  { min: 20, label: 'Below Average', color: 'text-orange-400', bg: 'bg-orange-500/20', border: 'border-orange-500/30' },
  { min: 0, label: 'Poor', color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
];

/**
 * Get rating based on score
 * @param {number} score - Score value
 * @returns {Object} Rating object
 */
const getRating = (score) => {
  return SCORE_RATINGS.find(r => score >= r.min) || SCORE_RATINGS[SCORE_RATINGS.length - 1];
};

// Component score icon mapping
const COMPONENT_ICONS = {
  price_growth: BarChart3,
  rental_yield: Home,
  demand_supply: Users,
  infrastructure: Building,
  appreciation_potential: TrendingUp,
  risk_factor: AlertTriangle,
};

// Score Bar Component
function ScoreBar({ label, score, maxScore = 100, icon: Icon, showComparison = false, marketAvg }) {
  const percentage = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const comparison = showComparison && marketAvg !== undefined ? score - marketAvg : null;
  
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={14} className="text-gray-400" />}
          <span className="text-gray-300">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{score}</span>
          {comparison !== null && (
            <span className={`text-xs flex items-center gap-0.5 ${comparison >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {comparison > 0 ? <TrendingUp size={10} /> : comparison < 0 ? <TrendingDown size={10} /> : <Minus size={10} />}
              {Math.abs(comparison)}
            </span>
          )}
        </div>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            percentage >= 70 ? 'bg-emerald-500' : percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// Market Comparison Component
function MarketComparison({ score, marketAvg, city }) {
  const diff = score - marketAvg;
  const percentDiff = ((diff / marketAvg) * 100).toFixed(1);
  
  return (
    <div className="mt-4 p-3 bg-gray-700/50 rounded-lg border border-gray-600">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-gray-400" />
          <span className="text-sm text-gray-300">vs {city || 'City'} Average</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">{marketAvg}</span>
          <span className={`text-sm font-medium ${diff >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {diff > 0 ? '+' : ''}{percentDiff}%
          </span>
        </div>
      </div>
      <div className="mt-2 relative h-3 bg-gray-600 rounded-full overflow-hidden">
        {/* Market average marker */}
        <div 
          className="absolute top-0 h-full w-1 bg-white/50"
          style={{ left: `${Math.min(100, Math.max(0, (marketAvg / 100) * 100))}%` }}
        />
        {/* Score marker */}
        <div
          className={`absolute top-0 h-full w-2 rounded-full ${diff >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
          style={{ left: `${Math.min(98, Math.max(0, percentage))}%`, transition: 'left 0.5s ease-out' }}
        />
      </div>
      <div className="flex justify-between mt-1 text-xs text-gray-500">
        <span>0</span>
        <span>100</span>
      </div>
    </div>
  );
}

// Explanation Tooltip Component
function ExplanationTooltip({ type }) {
  const explanations = {
    price_growth: 'Historical price appreciation rate over the past 1-3 years',
    rental_yield: 'Annual rental income as percentage of property value',
    demand_supply: 'Ratio of buyer interest to available properties',
    infrastructure: 'Quality of roads, metro, schools, hospitals nearby',
    appreciation_potential: 'Projected future value growth based on trends',
    risk_factor: 'Market stability and potential downside risks',
  };
  
  return (
    <div className="group relative inline-flex">
      <Info size={14} className="text-gray-500 hover:text-gray-300 cursor-help" />
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-gray-300 text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 border border-gray-700">
        {explanations[type] || 'No explanation available'}
        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900" />
      </div>
    </div>
  );
}

// Skeleton Loader
function SkeletonLoader() {
  return (
    <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700 animate-pulse">
      <div className="flex items-center gap-4 mb-4">
        <div className="w-16 h-16 bg-gray-700 rounded-full" />
        <div className="space-y-2">
          <div className="h-4 w-24 bg-gray-700 rounded" />
          <div className="h-6 w-16 bg-gray-700 rounded" />
        </div>
      </div>
      <div className="space-y-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-8 bg-gray-700 rounded" />
        ))}
      </div>
    </div>
  );
}

// Error State
function ErrorState({ message, onRetry }) {
  return (
    <div className="p-4 bg-red-500/10 rounded-xl border border-red-500/30">
      <div className="flex items-center gap-3">
        <AlertTriangle className="text-red-400" size={20} />
        <div className="flex-1">
          <p className="text-red-400 text-sm">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
          >
            <RefreshCw size={16} className="text-red-400" />
          </button>
        )}
      </div>
    </div>
  );
}

// Locked State (Premium Feature)
function LockedState({ credits, cost, onUpgrade }) {
  return (
    <div className="p-6 bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-xl border border-gray-700">
      <div className="flex flex-col items-center text-center">
        <div className="w-16 h-16 mb-4 rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
          <Lock className="text-amber-400" size={24} />
        </div>
        <h3 className="text-lg font-semibold text-white mb-2">Premium Feature</h3>
        <p className="text-gray-400 text-sm mb-4">
          Unlock detailed investment analysis for {cost} credits
        </p>
        <div className="flex items-center gap-2 mb-4">
          <Star className="text-amber-400" size={16} />
          <span className="text-amber-400 font-medium">{credits} credits available</span>
        </div>
        <button
          onClick={onUpgrade}
          className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg font-medium hover:from-amber-600 hover:to-orange-600 transition-all"
        >
          Unlock for {cost} Credits
        </button>
      </div>
    </div>
  );
}

// Main Component
export default function InvestmentScore({
  data,
  loading = false,
  error,
  showDetails = true,
  compareToMarket = false,
  onRefresh,
  onUpgrade,
  localityId,
}) {
  const [showAllComponents, setShowAllComponents] = useState(false);
  
  const scoreData = useMemo(() => {
    if (!data) return null;
    
    return {
      overallScore: data.overall_score || data.score || 0,
      rating: getRating(data.overall_score || data.score || 0),
      components: data.components || {},
      marketAvg: data.market_average || data.city_average,
      city: data.city,
      localityName: data.locality_name || data.localityId,
      lastUpdated: data.calculated_at || data.last_updated,
      recommendation: data.recommendation,
      riskLevel: data.risk_level,
    };
  }, [data]);
  
  if (loading) {
    return <SkeletonLoader />;
  }
  
  if (error) {
    return <ErrorState message={error} onRetry={onRefresh} />;
  }
  
  if (!scoreData) {
    return (
      <ErrorState 
        message="No investment data available" 
        onRetry={onRefresh} 
      />
    );
  }
  
  const mainComponents = [
    { key: 'price_growth', label: 'Price Growth', icon: 'BarChart3' },
    { key: 'rental_yield', label: 'Rental Yield', icon: 'Home' },
    { key: 'demand_supply', label: 'Demand vs Supply', icon: 'Users' },
  ];
  
  const additionalComponents = [
    { key: 'infrastructure', label: 'Infrastructure', icon: 'Building' },
    { key: 'appreciation_potential', label: 'Appreciation Potential', icon: 'TrendingUp' },
    { key: 'risk_factor', label: 'Risk Factor', icon: 'AlertTriangle' },
  ];
  
  const displayComponents = showAllComponents 
    ? [...mainComponents, ...additionalComponents]
    : mainComponents;
  
  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`
              w-12 h-12 rounded-full flex items-center justify-center
              ${scoreData.rating.bg}
            `}>
              <Target className={scoreData.rating.color} size={24} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Investment Score</h3>
              <p className="text-sm text-gray-400">{scoreData.localityName}</p>
            </div>
          </div>
          
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <RefreshCw size={16} className="text-gray-400" />
            </button>
          )}
        </div>
        
        {/* Overall Score */}
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-white">
            {scoreData.overallScore}
            <span className="text-lg text-gray-500">/100</span>
          </div>
          <div className={`
            px-3 py-1 rounded-full text-sm font-medium
            ${scoreData.rating.bg} ${scoreData.rating.color} ${scoreData.rating.border}
          `}>
            {scoreData.rating.label}
          </div>
        </div>
        
        {/* Recommendation Badge */}
        {scoreData.recommendation && (
          <div className={`mt-3 flex items-center gap-2 text-sm ${
            scoreData.recommendation === 'buy' ? 'text-emerald-400' :
            scoreData.recommendation === 'hold' ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {scoreData.recommendation === 'buy' ? (
              <CheckCircle size={16} />
            ) : scoreData.recommendation === 'hold' ? (
              <Minus size={16} />
            ) : (
              <AlertTriangle size={16} />
            )}
            <span className="capitalize">Recommendation: {scoreData.recommendation}</span>
          </div>
        )}
      </div>
      
      {/* Components Breakdown */}
      {showDetails && (
        <div className="p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-300">Score Breakdown</h4>
            <button
              onClick={() => setShowAllComponents(!showAllComponents)}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              {showAllComponents ? 'Show Less' : 'Show All'}
            </button>
          </div>
          
          <div className="space-y-3">
            {displayComponents.map(({ key, label, icon }) => {
              const IconComponent = COMPONENT_ICONS[key];
              return (
                <ScoreBar
                  key={key}
                  label={label}
                  score={scoreData.components[key] || 0}
                  icon={IconComponent}
                  showComparison={compareToMarket}
                  marketAvg={compareToMarket ? scoreData.marketAvg?.[key] : undefined}
                />
              );
            })}
          </div>
          
          {/* Market Comparison */}
          {compareToMarket && scoreData.marketAvg && (
            <MarketComparison
              score={scoreData.overallScore}
              marketAvg={scoreData.marketAvg.overall || 50}
              city={scoreData.city}
            />
          )}
          
          {/* Last Updated */}
          {scoreData.lastUpdated && (
            <div className="flex items-center gap-2 text-xs text-gray-500 pt-2">
              <Clock size={12} />
              <span>Last updated: {new Date(scoreData.lastUpdated).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
