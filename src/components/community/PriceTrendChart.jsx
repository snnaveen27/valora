/**
 * PriceTrendChart - Price visualization component
 * 
 * Features:
 * - Line chart showing price trends
 * - Multiple time periods (1mo, 3mo, 6mo, 1yr)
 * - Momentum indicator
 * - Price change percentages
 * - Interactive tooltip
 * - Responsive design
 * 
 * Props:
 * @param {Object} data - Price history data from API
 * @param {Object} momentum - Price momentum data
 * @param {boolean} loading - Loading state
 * @param {string} [error] - Error message
 * @param {string} [period] - Selected time period
 * @param {function} [onPeriodChange] - Period change handler
 * @param {function} [onRefresh] - Refresh handler
 * @param {string} [localityName] - Locality name to display
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  RefreshCw, 
  Loader2,
  AlertTriangle,
  Info,
  IndianRupee,
  Calendar,
} from 'lucide-react';

// Format price in Indian Rupees
const formatPrice = (price) => {
  if (price >= 10000000) {
    return `₹${(price / 10000000).toFixed(2)} Cr`;
  } else if (price >= 100000) {
    return `₹${(price / 100000).toFixed(2)} L`;
  }
  return `₹${price.toLocaleString()}`;
};

// Format date based on period
const formatDate = (dateStr, period) => {
  const date = new Date(dateStr);
  if (period === '1mo' || period === '3mo') {
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  }
  return date.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
};

// Period configurations
const PERIODS = [
  { key: '1mo', label: '1M', days: 30 },
  { key: '3mo', label: '3M', days: 90 },
  { key: '6mo', label: '6M', days: 180 },
  { key: '1yr', label: '1Y', days: 365 },
];

// Simple SVG Line Chart Component
function PriceLineChart({ data, width = 400, height = 200, showArea = true }) {
  const svgRef = useRef(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        No data available
      </div>
    );
  }
  
  const prices = data.map(d => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;
  
  // Padding
  const padding = { top: 20, right: 20, bottom: 30, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  // Calculate points
  const points = data.map((d, i) => ({
    x: padding.left + (i / (data.length - 1)) * chartWidth,
    y: padding.top + chartHeight - ((d.price - minPrice) / priceRange) * chartHeight,
    data: d,
  }));
  
  // Create path
  const linePath = points.length > 0 
    ? `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}`
    : '';
  
  // Area path
  const areaPath = points.length > 0
    ? `${linePath} L ${points[points.length - 1].x},${padding.top + chartHeight} L ${points[0].x},${padding.top + chartHeight} Z`
    : '';
  
  // Y-axis ticks
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks }, (_, i) => 
    minPrice + (priceRange / (yTicks - 1)) * i
  );
  
  // Handle mouse events
  const handleMouseMove = (e) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    
    // Find closest point
    let closest = null;
    let minDist = Infinity;
    points.forEach(p => {
      const dist = Math.abs(p.x - x);
      if (dist < minDist) {
        minDist = dist;
        closest = p;
      }
    });
    
    if (closest && minDist < 30) {
      setHoveredPoint(closest);
    } else {
      setHoveredPoint(null);
    }
  };
  
  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="overflow-visible"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoveredPoint(null)}
    >
      {/* Grid lines */}
      {yTickValues.map((tick, i) => (
        <line
          key={i}
          x1={padding.left}
          y1={padding.top + chartHeight - (i / (yTicks - 1)) * chartHeight}
          x2={width - padding.right}
          y2={padding.top + chartHeight - (i / (yTicks - 1)) * chartHeight}
          stroke="currentColor"
          strokeOpacity={0.1}
          strokeDasharray="4 4"
        />
      ))}
      
      {/* Y-axis labels */}
      {yTickValues.map((tick, i) => (
        <text
          key={i}
          x={padding.left - 8}
          y={padding.top + chartHeight - (i / (yTicks - 1)) * chartHeight}
          textAnchor="end"
          alignmentBaseline="middle"
          className="fill-gray-500 text-xs"
        >
          {formatPrice(tick)}
        </text>
      ))}
      
      {/* Area fill */}
      {showArea && (
        <path
          d={areaPath}
          className="fill-blue-500/10"
        />
      )}
      
      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-blue-500"
      />
      
      {/* Data points */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={hoveredPoint === p ? 6 : 3}
          fill={hoveredPoint === p ? '#3b82f6' : 'currentColor'}
          className={hoveredPoint === p ? 'text-blue-500' : 'text-blue-500/50'}
        />
      ))}
      
      {/* Tooltip */}
      {hoveredPoint && (
        <g>
          <rect
            x={hoveredPoint.x - 60}
            y={hoveredPoint.y - 50}
            width={120}
            height={40}
            rx={4}
            fill="#1f2937"
            stroke="#374151"
          />
          <text
            x={hoveredPoint.x}
            y={hoveredPoint.y - 30}
            textAnchor="middle"
            className="fill-gray-400 text-xs"
          >
            {formatDate(hoveredPoint.data.date, '1yr')}
          </text>
          <text
            x={hoveredPoint.x}
            y={hoveredPoint.y - 12}
            textAnchor="middle"
            className="fill-white text-sm font-medium"
          >
            {formatPrice(hoveredPoint.data.price)}
          </text>
        </g>
      )}
    </svg>
  );
}

// Momentum Badge Component
function MomentumBadge({ momentum }) {
  if (!momentum) return null;
  
  const { change_percent: change, direction } = momentum;
  const isPositive = change > 0;
  const isNeutral = change === 0;
  
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
      isPositive ? 'bg-emerald-500/20' : isNeutral ? 'bg-gray-500/20' : 'bg-red-500/20'
    }`}>
      {isPositive ? (
        <TrendingUp size={16} className="text-emerald-400" />
      ) : isNeutral ? (
        <Minus size={16} className="text-gray-400" />
      ) : (
        <TrendingDown size={16} className="text-red-400" />
      )}
      <span className={`font-medium ${
        isPositive ? 'text-emerald-400' : isNeutral ? 'text-gray-400' : 'text-red-400'
      }`}>
        {isPositive ? '+' : ''}{change?.toFixed(1) || 0}%
      </span>
      <span className="text-xs text-gray-500">vs last period</span>
    </div>
  );
}

// Price Stats Component
function PriceStats({ data, currentPrice }) {
  const stats = useMemo(() => {
    if (!data || data.length < 2) return null;
    
    const firstPrice = data[0].price;
    const lastPrice = data[data.length - 1].price;
    const change = lastPrice - firstPrice;
    const changePercent = ((change / firstPrice) * 100);
    const min = Math.min(...data.map(d => d.price));
    const max = Math.max(...data.map(d => d.price));
    const avg = data.reduce((sum, d) => sum + d.price, 0) / data.length;
    
    return {
      change,
      changePercent,
      min,
      max,
      avg,
      current: currentPrice || lastPrice,
    };
  }, [data, currentPrice]);
  
  if (!stats) return null;
  
  return (
    <div className="grid grid-cols-4 gap-3 mt-4">
      <div className="p-3 bg-gray-700/30 rounded-lg">
        <div className="text-xs text-gray-500 mb-1">Current</div>
        <div className="text-sm font-semibold text-white">{formatPrice(stats.current)}</div>
      </div>
      <div className="p-3 bg-gray-700/30 rounded-lg">
        <div className="text-xs text-gray-500 mb-1">Change</div>
        <div className={`text-sm font-semibold ${
          stats.change >= 0 ? 'text-emerald-400' : 'text-red-400'
        }`}>
          {stats.change >= 0 ? '+' : ''}{stats.changePercent.toFixed(1)}%
        </div>
      </div>
      <div className="p-3 bg-gray-700/30 rounded-lg">
        <div className="text-xs text-gray-500 mb-1">Min</div>
        <div className="text-sm font-semibold text-white">{formatPrice(stats.min)}</div>
      </div>
      <div className="p-3 bg-gray-700/30 rounded-lg">
        <div className="text-xs text-gray-500 mb-1">Max</div>
        <div className="text-sm font-semibold text-white">{formatPrice(stats.max)}</div>
      </div>
    </div>
  );
}

// Period Selector Component
function PeriodSelector({ period, onPeriodChange }) {
  return (
    <div className="flex items-center gap-1 p-1 bg-gray-700/50 rounded-lg">
      {PERIODS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onPeriodChange(key)}
          className={`
            px-3 py-1.5 rounded-md text-sm font-medium transition-all
            ${period === key
              ? 'bg-blue-500 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-600'
            }
          `}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// Skeleton Loader
function ChartSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex justify-between">
        <div className="h-8 w-32 bg-gray-700 rounded" />
        <div className="h-8 w-24 bg-gray-700 rounded" />
      </div>
      <div className="h-48 bg-gray-700/50 rounded-lg" />
      <div className="grid grid-cols-4 gap-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-16 bg-gray-700/30 rounded-lg" />
        ))}
      </div>
    </div>
  );
}

// Error State
function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <AlertTriangle className="text-yellow-400 mb-3" size={32} />
      <h3 className="text-lg font-medium text-gray-300 mb-1">Unable to Load Price Data</h3>
      <p className="text-sm text-gray-500 mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
      >
        <RefreshCw size={16} />
        Try Again
      </button>
    </div>
  );
}

// Main Component
export default function PriceTrendChart({
  data,
  momentum,
  loading = false,
  error,
  period: initialPeriod = '1yr',
  onPeriodChange,
  onRefresh,
  localityName = 'Locality',
  showStats = true,
  height = 200,
}) {
  const [period, setPeriod] = useState(initialPeriod);
  const [containerWidth, setContainerWidth] = useState(400);
  const containerRef = useRef(null);
  
  // Auto-resize
  useEffect(() => {
    if (!containerRef.current) return;
    
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };
    
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);
  
  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);
    onPeriodChange?.(newPeriod);
  };
  
  // Transform data for chart
  const chartData = useMemo(() => {
    if (!data?.price_history && !data?.history) return [];
    
    const history = data.price_history || data.history || [];
    return history.map(item => ({
      date: item.date || item.month || item.timestamp,
      price: item.price || item.average_price || item.value,
    }));
  }, [data]);
  
  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Price Trends</h3>
            <p className="text-sm text-gray-400">{localityName}</p>
          </div>
          
          <div className="flex items-center gap-3">
            <MomentumBadge momentum={momentum} />
            <PeriodSelector period={period} onPeriodChange={handlePeriodChange} />
          </div>
        </div>
        
        {/* Current Price */}
        {data?.current_price && (
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">
              {formatPrice(data.current_price)}
            </span>
            <span className="text-sm text-gray-500">current price</span>
          </div>
        )}
      </div>
      
      {/* Chart */}
      <div ref={containerRef} className="p-4">
        {loading ? (
          <ChartSkeleton />
        ) : error ? (
          <ErrorState message={error} onRetry={onRefresh} />
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-gray-500">
            No price data available
          </div>
        ) : (
          <>
            <PriceLineChart
              data={chartData}
              width={Math.max(300, containerWidth - 32)}
              height={height}
            />
            
            {showStats && (
              <PriceStats data={chartData} currentPrice={data?.current_price} />
            )}
          </>
        )}
      </div>
      
      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <Info size={12} />
          <span>Historical data based on recorded transactions</span>
        </div>
        
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="flex items-center gap-1 hover:text-white transition-colors"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        )}
      </div>
    </div>
  );
}

// Export mock data generator for demo purposes
export const generateMockPriceData = (period = '1yr') => {
  const periods = {
    '1mo': 30,
    '3mo': 90,
    '6mo': 180,
    '1yr': 365,
  };
  
  const days = periods[period] || 365;
  const basePrice = 8500000; // 85 Lakhs
  const data = [];
  
  for (let i = days; i >= 0; i -= Math.max(1, Math.floor(days / 20))) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    
    // Add some randomness but with upward trend
    const randomFactor = 1 + (Math.random() - 0.5) * 0.1;
    const trendFactor = 1 + ((days - i) / days) * 0.15; // 15% growth over period
    const price = basePrice * trendFactor * randomFactor;
    
    data.push({
      date: date.toISOString().split('T')[0],
      price: Math.round(price),
    });
  }
  
  return {
    price_history: data,
    current_price: data[data.length - 1]?.price || basePrice,
    momentum: {
      change_percent: ((data[data.length - 1]?.price - data[0]?.price) / data[0]?.price * 100) || 0,
      direction: 'up',
    },
  };
};
