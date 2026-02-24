/**
 * SentimentDashboard - Main dashboard for market sentiment analysis
 * 
 * Features:
 * - Overview of sentiment for selected locality
 * - Key metrics summary (sentiment score, investment score, demand score, supply score)
 * - Price momentum indicator
 * - Quick links to detailed views
 * - Credit system integration
 * - Multiple view modes (locality, city, trending)
 * 
 * Props:
 * @param {string} [localityId] - Selected locality ID
 * @param {string} [localityName] - Selected locality name
 * @param {string} [city] - City name
 * @param {string} [viewMode] - Initial view mode (locality, city, trending)
 * @param {function} [onNavigate] - Navigation callback
 * @param {boolean} [autoLoad] - Auto-load data on mount
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  MapPin, 
  Building, 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  Loader2,
  AlertCircle,
  Lock,
  Star,
  ChevronRight,
  Home,
  BarChart3,
  Activity,
  Wallet,
  Clock,
  ArrowLeft,
  CreditCard,
} from 'lucide-react';

import SentimentGauge from './SentimentGauge';
import InvestmentScore from './InvestmentScore';
import ActivityFeed from './ActivityFeed';
import PriceTrendChart from './PriceTrendChart';

import * as sentimentApi from '../../services/sentimentApi';

// Credit costs
const CREDIT_COSTS = {
  locality_sentiment: 5,
  city_sentiment: 5,
  investment_score: 5,
  price_history: 5,
  trends: 10,
  rental_yield: 3,
  days_on_market: 3,
};

// View Mode configurations
const VIEW_MODES = [
  { key: 'locality', label: 'Locality', icon: MapPin },
  { key: 'city', label: 'City', icon: Building },
  { key: 'trending', label: 'Trending', icon: TrendingUp },
];

// Key Metrics Card
function MetricCard({ title, value, subtitle, icon: Icon, color, trend, onClick, loading }) {
  return (
    <div 
      onClick={onClick}
      className={`
        p-4 rounded-xl border transition-all cursor-pointer
        ${onClick ? 'hover:scale-[1.02] hover:shadow-lg' : ''}
        bg-gray-800/50 border-gray-700 hover:border-gray-600
      `}
    >
      <div className="flex items-start justify-between mb-2">
        <div className={`p-2 rounded-lg ${color.bg}`}>
          <Icon size={18} className={color.text} />
        </div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      
      <div className="space-y-1">
        <div className="text-sm text-gray-400">{title}</div>
        {loading ? (
          <div className="h-8 w-16 bg-gray-700 animate-pulse rounded" />
        ) : (
          <div className="text-2xl font-bold text-white">{value}</div>
        )}
        {subtitle && <div className="text-xs text-gray-500">{subtitle}</div>}
      </div>
    </div>
  );
}

// Quick Actions Panel
function QuickActions({ onAction }) {
  const actions = [
    { key: 'full_analysis', label: 'Full Analysis', icon: BarChart3, credits: 15 },
    { key: 'price_alerts', label: 'Set Price Alert', icon: Clock, credits: 2 },
    { key: 'compare', label: 'Compare Area', icon: Activity, credits: 5 },
    { key: 'report', label: 'Download Report', icon: Wallet, credits: 10 },
  ];
  
  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-2">
        {actions.map(({ key, label, icon: Icon, credits }) => (
          <button
            key={key}
            onClick={() => onAction(key)}
            className="flex items-center gap-2 p-3 bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-colors text-left"
          >
            <Icon size={16} className="text-blue-400" />
            <div className="flex-1 min-w-0">
              <div className="text-sm text-white truncate">{label}</div>
              <div className="text-xs text-gray-500">{credits} credits</div>
            </div>
            <ChevronRight size={14} className="text-gray-500" />
          </button>
        ))}
      </div>
    </div>
  );
}

// Credits Banner
function CreditsBanner({ credits, onUpgrade }) {
  // Handle both number and object formats for credits
  const creditsDisplay = typeof credits === 'object' 
    ? (credits?.remaining ?? credits?.total ?? 0)
    : (credits || 0);
    
  return (
    <div className="flex items-center justify-between p-3 bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-lg border border-amber-500/30">
      <div className="flex items-center gap-2">
        <Star className="text-amber-400" size={18} />
        <span className="text-sm text-amber-200">
          <span className="font-semibold">{creditsDisplay}</span> credits remaining
        </span>
      </div>
      <button
        onClick={onUpgrade}
        className="flex items-center gap-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-sm rounded-lg transition-colors"
      >
        <CreditCard size={14} />
        Get More
      </button>
    </div>
  );
}

// Loading Overlay
function LoadingOverlay({ message }) {
  return (
    <div className="absolute inset-0 bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-10">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="animate-spin text-blue-500" size={32} />
        <span className="text-sm text-gray-300">{message || 'Loading...'}</span>
      </div>
    </div>
  );
}

// Error Banner
function ErrorBanner({ message, onRetry, onDismiss }) {
  return (
    <div className="flex items-center justify-between p-3 bg-red-500/10 rounded-lg border border-red-500/30 mb-4">
      <div className="flex items-center gap-2">
        <AlertCircle className="text-red-400" size={18} />
        <span className="text-sm text-red-200">{message}</span>
      </div>
      <div className="flex items-center gap-2">
        {onRetry && (
          <button
            onClick={onRetry}
            className="p-1.5 hover:bg-red-500/20 rounded transition-colors"
          >
            <RefreshCw size={14} className="text-red-400" />
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1.5 hover:bg-red-500/20 rounded transition-colors"
          >
            <span className="text-red-400 text-lg">&times;</span>
          </button>
        )}
      </div>
    </div>
  );
}

// Trending Localities Card
function TrendingCard({ localities, onSelect, loading }) {
  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-300">Trending Localities</h3>
        <TrendingUp size={16} className="text-emerald-400" />
      </div>
      
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-12 bg-gray-700/30 animate-pulse rounded-lg" />
          ))}
        </div>
      ) : localities?.length > 0 ? (
        <div className="space-y-2">
          {localities.slice(0, 5).map((item, index) => (
            <button
              key={item.locality_id || index}
              onClick={() => onSelect(item.locality_id, item.locality_name)}
              className="w-full flex items-center gap-3 p-2 hover:bg-gray-700/50 rounded-lg transition-colors text-left"
            >
              <div className={`
                w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                ${index < 3 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-700 text-gray-400'}
              `}>
                {index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white truncate">{item.locality_name}</div>
                <div className="text-xs text-gray-500">{item.city}</div>
              </div>
              {item.sentiment_score && (
                <div className={`text-sm font-medium ${
                  item.sentiment_score >= 60 ? 'text-emerald-400' :
                  item.sentiment_score >= 40 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {item.sentiment_score}
                </div>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-6 text-gray-500 text-sm">
          No trending data available
        </div>
      )}
    </div>
  );
}

// Main Component
export default function SentimentDashboard({
  localityId: initialLocalityId,
  localityName: initialLocalityName,
  city: initialCity,
  viewMode: initialViewMode = 'locality',
  onNavigate,
  autoLoad = true,
}) {
  // State
  const [viewMode, setViewMode] = useState(initialViewMode);
  const [localityId, setLocalityId] = useState(initialLocalityId);
  const [localityName, setLocalityName] = useState(initialLocalityName);
  const [city, setCity] = useState(initialCity || 'Bangalore');
  const [period, setPeriod] = useState('1yr');
  
  // Data state
  const [sentimentData, setSentimentData] = useState(null);
  const [investmentData, setInvestmentData] = useState(null);
  const [priceData, setPriceData] = useState(null);
  const [rentalYield, setRentalYield] = useState(null);
  const [daysOnMarket, setDaysOnMarket] = useState(null);
  const [trending, setTrending] = useState([]);
  const [activities, setActivities] = useState([]);
  const [credits, setCredits] = useState(50); // Default credits
  
  // Loading/Error states
  const [loading, setLoading] = useState(false);
  const [loadingSentiment, setLoadingSentiment] = useState(false);
  const [loadingInvestment, setLoadingInvestment] = useState(false);
  const [loadingPrice, setLoadingPrice] = useState(false);
  const [error, setError] = useState(null);
  
  // Check credits on mount
  useEffect(() => {
    const checkCredits = async () => {
      try {
        const data = await sentimentApi.checkCredits();
        // Handle both object and number formats
        const creditValue = typeof data === 'object' 
          ? (data?.credits || data?.available_credits || data?.remaining || 50)
          : (data || 50);
        setCredits(creditValue);
      } catch (err) {
        console.error('Error checking credits:', err);
      }
    };
    checkCredits();
  }, []);
  
  // Load data based on view mode
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (viewMode === 'trending') {
        // Load trending localities
        const trendingData = await sentimentApi.getTrending(city, 10);
        setTrending(trendingData.localities || trendingData.results || []);
      } else if (viewMode === 'city') {
        // Load city sentiment
        const data = await sentimentApi.getCitySentiment(city);
        setSentimentData(data);
      } else if (localityId) {
        // Load locality data
        const [sentiment, investment, price, rental, days] = await Promise.all([
          sentimentApi.getSentiment(localityId).catch(err => ({ error: err.message })),
          sentimentApi.getInvestmentScore(localityId).catch(err => ({ error: err.message })),
          sentimentApi.getPriceData(localityId, period).catch(err => ({ error: err.message })),
          sentimentApi.getRentalYield(localityId).catch(err => ({ error: err.message })),
          sentimentApi.getDaysOnMarket(localityId).catch(err => ({ error: err.message })),
        ]);
        
        setSentimentData(sentiment);
        setInvestmentData(investment);
        setPriceData(price);
        setRentalYield(rental);
        setDaysOnMarket(days);
      }
    } catch (err) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [viewMode, localityId, city, period]);
  
  // Auto-load on mount and when dependencies change
  useEffect(() => {
    if (autoLoad) {
      loadData();
    }
  }, [loadData, autoLoad]);
  
  // Handle view mode change
  const handleViewModeChange = (mode) => {
    setViewMode(mode);
    setError(null);
  };
  
  // Handle locality selection
  const handleLocalitySelect = (id, name) => {
    setLocalityId(id);
    setLocalityName(name);
    setViewMode('locality');
  };
  
  // Handle refresh
  const handleRefresh = () => {
    loadData();
  };
  
  // Handle quick action
  const handleQuickAction = (action) => {
    console.log('Quick action:', action);
    onNavigate?.(action);
  };
  
  // Get sentiment score
  const sentimentScore = sentimentData?.sentiment_score 
    || sentimentData?.overall_score 
    || sentimentData?.score 
    || 0;
  
  // Get demand score
  const demandScore = sentimentData?.components?.demand_score || 0;
  
  // Get supply score
  const supplyScore = sentimentData?.components?.supply_score || 0;
  
  // Colors for metrics
  const colors = {
    sentiment: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    demand: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
    supply: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
    investment: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
  };
  
  return (
    <div className="min-h-screen bg-gray-900 p-4 md:p-6">
      {/* Credits Banner */}
      <div className="mb-4">
        <CreditsBanner credits={credits} onUpgrade={() => onNavigate?.('upgrade')} />
      </div>
      
      {/* Error Banner */}
      {error && (
        <ErrorBanner 
          message={error} 
          onRetry={handleRefresh} 
          onDismiss={() => setError(null)} 
        />
      )}
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Market Sentiment Dashboard</h1>
          <p className="text-gray-400">Real-time insights for {localityName || city || 'Indian Real Estate'}</p>
        </div>
        
        {/* View Mode Selector */}
        <div className="flex items-center gap-2 p-1 bg-gray-800 rounded-lg">
          {VIEW_MODES.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => handleViewModeChange(key)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${viewMode === key
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }
              `}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Locality Selector (for city/trending views) */}
      {viewMode !== 'locality' && (
        <div className="mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {viewMode === 'city' && (
              <div className="flex-1">
                <label className="text-sm text-gray-400 mb-1 block">City</label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder="Enter city name"
                />
              </div>
            )}
            {viewMode === 'locality' && (
              <div className="flex-1">
                <label className="text-sm text-gray-400 mb-1 block">Locality</label>
                <input
                  type="text"
                  value={localityName || ''}
                  onChange={(e) => setLocalityName(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder="Enter locality name"
                />
                <input
                  type="hidden"
                  value={localityId || ''}
                  onChange={(e) => setLocalityId(e.target.value)}
                />
              </div>
            )}
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              Analyze
            </button>
          </div>
        </div>
      )}
      
      {/* Main Content */}
      {loading && !localityId && viewMode === 'locality' ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="animate-spin text-blue-500" size={40} />
        </div>
      ) : viewMode === 'trending' ? (
        // Trending View
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <TrendingCard 
            localities={trending} 
            onSelect={handleLocalitySelect}
            loading={loading}
          />
        </div>
      ) : (
        <>
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Sentiment Score"
              value={sentimentScore}
              subtitle="Market mood"
              icon={Activity}
              color={colors.sentiment}
              loading={loadingSentiment}
            />
            <MetricCard
              title="Demand Score"
              value={demandScore}
              subtitle="Buyer interest"
              icon={TrendingUp}
              color={colors.demand}
              trend={5}
            />
            <MetricCard
              title="Supply Score"
              value={supplyScore}
              subtitle="Listings available"
              icon={Building}
              color={colors.supply}
              trend={-2}
            />
            <MetricCard
              title="Investment Score"
              value={investmentData?.overall_score || '—'}
              subtitle="Overall rating"
              icon={Wallet}
              color={colors.investment}
              onClick={() => onNavigate?.('investment_details')}
              loading={loadingInvestment}
            />
          </div>
          
          {/* Main Dashboard Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Sentiment & Investment */}
            <div className="lg:col-span-1 space-y-6">
              <SentimentGauge
                score={sentimentScore}
                components={sentimentData?.components}
                size="lg"
                showBreakdown={true}
                change={sentimentData?.change_percent}
                label={localityName || 'Market Sentiment'}
              />
              
              <InvestmentScore
                data={investmentData}
                loading={loadingInvestment}
                error={investmentData?.error}
                onRefresh={() => sentimentApi.getInvestmentScore(localityId).then(setInvestmentData)}
                showDetails={true}
                compareToMarket={true}
                localityId={localityId}
              />
            </div>
            
            {/* Middle Column - Price Trends */}
            <div className="lg:col-span-2 space-y-6">
              <PriceTrendChart
                data={priceData}
                momentum={priceData?.momentum}
                loading={loadingPrice}
                period={period}
                onPeriodChange={setPeriod}
                onRefresh={() => sentimentApi.getPriceData(localityId, period).then(setPriceData)}
                localityName={localityName}
                height={250}
              />
              
              {/* Activity Feed */}
              <ActivityFeed
                activities={activities}
                loading={loading}
                showStats={true}
                localityId={localityId}
              />
            </div>
          </div>
          
          {/* Quick Actions */}
          <div className="mt-6">
            <QuickActions onAction={handleQuickAction} />
          </div>
        </>
      )}
    </div>
  );
}

// Export sub-components for granular usage
export { SentimentDashboard };
