import { useState, useEffect, useMemo, useRef } from 'react'
import { 
  TrendingUp, Calendar, BarChart3, Activity, ChevronDown, 
  Minus, ArrowUpRight, ArrowDownRight 
} from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Generate sample time series data (will be replaced by API)
function generateSampleData(months = 36, basePrice = 6500) {
  const data = []
  let price = basePrice
  const now = new Date()
  
  for (let i = months - 1; i >= 0; i--) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
    // Add some realistic volatility
    const trend = 0.003 // ~3.6% annual growth
    const volatility = (Math.random() - 0.5) * 0.02
    price = price * (1 + trend + volatility)
    
    data.push({
      date: date.toISOString().slice(0, 7),
      price: Math.round(price),
      volume: Math.floor(Math.random() * 50 + 20),
      rentalYield: 4 + Math.random() * 1.5
    })
  }
  return data
}

// Mini bar chart for volume
function VolumeChart({ data, height = 30 }) {
  if (!data || data.length === 0) return null
  
  const maxVolume = Math.max(...data.map(d => d.volume))
  
  return (
    <div className="flex items-end gap-0.5" style={{ height }}>
      {data.slice(-24).map((d, i) => (
        <div
          key={i}
          className="flex-1 bg-blue-500/40 hover:bg-blue-500/60 transition rounded-t-sm min-w-[3px]"
          style={{ height: `${(d.volume / maxVolume) * 100}%` }}
          title={`${d.date}: ${d.volume} transactions`}
        />
      ))}
    </div>
  )
}

// Rental yield mini chart
function YieldChart({ data, height = 30 }) {
  if (!data || data.length === 0) return null
  
  const yields = data.slice(-24).map(d => d.rentalYield)
  const minY = Math.min(...yields) - 0.5
  const maxY = Math.max(...yields) + 0.5
  const range = maxY - minY
  
  const points = yields.map((y, i) => {
    const x = (i / (yields.length - 1)) * 100
    const yPos = ((y - minY) / range) * height
    return `${x},${height - yPos}`
  }).join(' ')
  
  return (
    <svg width="100%" height={height} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke="#22c55e"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function PriceTimeSeriesChart({ 
  locality, 
  lat, 
  lng, 
  showComparison = true 
}) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [range, setRange] = useState('3y') // 1y, 2y, 3y
  const [smoothing, setSmoothing] = useState(true)
  const [compareCity, setCompareCity] = useState(false)
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const [containerWidth, setContainerWidth] = useState(320)
  const containerRef = useRef(null)
  
  // Track container width for responsive chart
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.offsetWidth - 24 // Account for padding
        setContainerWidth(Math.min(Math.max(width, 200), 600)) // Clamp between 200-600
      }
    }
    updateWidth()
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])
  
  // Fetch or generate data
  useEffect(() => {
    setLoading(true)
    // TODO: Replace with actual API call
    // fetch(`${API_URL}/api/valuation/market-stats?locality=${locality}&range=${range}`)
    const months = range === '1y' ? 12 : range === '2y' ? 24 : 36
    const sampleData = generateSampleData(months)
    setData(sampleData)
    setLoading(false)
  }, [locality, lat, lng, range])
  
  // Calculate chart dimensions and paths
  const chartConfig = useMemo(() => {
    if (!data || data.length === 0) return null
    
    const width = containerWidth
    const height = 100
    const padding = { top: 10, right: 10, bottom: 20, left: 45 }
    const plotWidth = width - padding.left - padding.right
    const plotHeight = height - padding.top - padding.bottom
    
    const prices = data.map(d => d.price)
    const minPrice = Math.min(...prices) * 0.95
    const maxPrice = Math.max(...prices) * 1.05
    const priceRange = maxPrice - minPrice
    
    // Generate path
    const points = data.map((d, i) => {
      const x = padding.left + (i / (data.length - 1)) * plotWidth
      const y = padding.top + plotHeight - ((d.price - minPrice) / priceRange) * plotHeight
      return { x, y, ...d }
    })
    
    // Smooth path using bezier curves if enabled
    let pathD = ''
    if (smoothing && points.length > 2) {
      pathD = `M ${points[0].x} ${points[0].y}`
      for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1]
        const curr = points[i]
        const cpx = (prev.x + curr.x) / 2
        pathD += ` Q ${prev.x + (curr.x - prev.x) * 0.5} ${prev.y}, ${cpx} ${(prev.y + curr.y) / 2}`
      }
      pathD += ` L ${points[points.length - 1].x} ${points[points.length - 1].y}`
    } else {
      pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
    }
    
    // Area path
    const areaD = `${pathD} L ${points[points.length - 1].x} ${height - padding.bottom} L ${points[0].x} ${height - padding.bottom} Z`
    
    // City average line (sample)
    const cityAvgPrice = prices.reduce((a, b) => a + b, 0) / prices.length * 0.9
    const cityY = padding.top + plotHeight - ((cityAvgPrice - minPrice) / priceRange) * plotHeight
    
    return {
      width, height, padding, plotWidth, plotHeight,
      minPrice, maxPrice, priceRange,
      points, pathD, areaD, cityY, cityAvgPrice
    }
  }, [data, smoothing])
  
  // Calculate stats
  const stats = useMemo(() => {
    if (!data || data.length < 2) return null
    
    const first = data[0].price
    const last = data[data.length - 1].price
    const change = ((last - first) / first) * 100
    const avgVolume = Math.round(data.reduce((a, d) => a + d.volume, 0) / data.length)
    const avgYield = data.reduce((a, d) => a + d.rentalYield, 0) / data.length
    
    return {
      currentPrice: last,
      priceChange: change,
      avgVolume,
      avgYield: avgYield.toFixed(1)
    }
  }, [data])
  
  if (loading) {
    return (
      <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
        <div className="flex items-center gap-2 animate-pulse">
          <BarChart3 className="w-4 h-4 text-slate-500" />
          <span className="text-slate-500 text-xs">Loading price history...</span>
        </div>
      </div>
    )
  }
  
  if (!chartConfig) return null
  
  const { width, height, padding, points, pathD, areaD, cityY, minPrice, maxPrice } = chartConfig
  
  return (
    <div ref={containerRef} className="bg-slate-800/40 rounded-xl p-3 border border-indigo-500/20 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-indigo-400" />
          <span className="text-indigo-400 font-bold text-xs uppercase">Price Trends</span>
        </div>
        
        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Range selector */}
          <div className="flex bg-slate-900/60 rounded-lg p-0.5">
            {['1y', '2y', '3y'].map(r => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-2 py-0.5 text-[9px] rounded transition ${
                  range === r 
                    ? 'bg-indigo-500 text-white' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>
          
          {/* Smoothing toggle */}
          <button
            onClick={() => setSmoothing(!smoothing)}
            className={`p-1 rounded text-[9px] transition ${
              smoothing ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500'
            }`}
            title="Toggle smoothing"
          >
            <Activity className="w-3 h-3" />
          </button>
          
          {/* Compare toggle */}
          {showComparison && (
            <button
              onClick={() => setCompareCity(!compareCity)}
              className={`px-1.5 py-0.5 rounded text-[9px] transition ${
                compareCity ? 'bg-yellow-500/20 text-yellow-400' : 'text-slate-500'
              }`}
            >
              vs City
            </button>
          )}
        </div>
      </div>
      
      {/* Main Chart */}
      <div className="relative">
        <svg width={width} height={height} className="overflow-visible">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = padding.top + (1 - pct) * (height - padding.top - padding.bottom)
            const price = minPrice + pct * (maxPrice - minPrice)
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#334155"
                  strokeWidth="0.5"
                  strokeDasharray="2,2"
                />
                <text
                  x={padding.left - 5}
                  y={y + 3}
                  textAnchor="end"
                  fill="#64748b"
                  fontSize="9"
                >
                  {Math.round(price / 1000)}k
                </text>
              </g>
            )
          })}
          
          {/* City average line */}
          {compareCity && (
            <line
              x1={padding.left}
              y1={cityY}
              x2={width - padding.right}
              y2={cityY}
              stroke="#eab308"
              strokeWidth="1"
              strokeDasharray="4,2"
            />
          )}
          
          {/* Gradient definition */}
          <defs>
            <linearGradient id="priceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.05" />
            </linearGradient>
          </defs>
          
          {/* Area fill */}
          <path d={areaD} fill="url(#priceGradient)" />
          
          {/* Line */}
          <path
            d={pathD}
            fill="none"
            stroke="#6366f1"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          
          {/* Hover points */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={hoveredPoint === i ? 5 : 3}
              fill={hoveredPoint === i ? '#6366f1' : 'transparent'}
              stroke={hoveredPoint === i ? '#fff' : 'transparent'}
              strokeWidth="2"
              className="cursor-pointer"
              onMouseEnter={() => setHoveredPoint(i)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
          
          {/* X-axis labels */}
          {[0, Math.floor(data.length / 2), data.length - 1].map(i => (
            <text
              key={i}
              x={points[i]?.x}
              y={height - 5}
              textAnchor="middle"
              fill="#64748b"
              fontSize="9"
            >
              {data[i]?.date}
            </text>
          ))}
        </svg>
        
        {/* Tooltip */}
        {hoveredPoint !== null && points[hoveredPoint] && (
          <div 
            className="absolute bg-slate-900 border border-slate-700 rounded-lg p-2 shadow-xl z-10 pointer-events-none"
            style={{
              left: Math.min(points[hoveredPoint].x, width - 100),
              top: points[hoveredPoint].y - 60
            }}
          >
            <div className="text-[10px] text-slate-400">{points[hoveredPoint].date}</div>
            <div className="text-sm font-bold text-white">₹{points[hoveredPoint].price.toLocaleString()}/sqft</div>
            <div className="text-[9px] text-slate-500">{points[hoveredPoint].volume} transactions</div>
          </div>
        )}
      </div>
      
      {/* Sub-charts */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        {/* Volume */}
        <div className="bg-slate-900/40 rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] text-slate-400">Transaction Volume</span>
            <span className="text-[10px] text-blue-400 font-medium">{stats?.avgVolume}/mo avg</span>
          </div>
          <VolumeChart data={data} height={25} />
        </div>
        
        {/* Rental Yield */}
        <div className="bg-slate-900/40 rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] text-slate-400">Rental Yield</span>
            <span className="text-[10px] text-green-400 font-medium">{stats?.avgYield}% avg</span>
          </div>
          <YieldChart data={data} height={25} />
        </div>
      </div>
      
      {/* Stats row */}
      {stats && (
        <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between text-[10px]">
          <div className="flex items-center gap-1">
            <span className="text-slate-400">Current:</span>
            <span className="text-white font-bold">₹{stats.currentPrice.toLocaleString()}</span>
          </div>
          <div className={`flex items-center gap-0.5 ${
            stats.priceChange > 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {stats.priceChange > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {stats.priceChange > 0 ? '+' : ''}{stats.priceChange.toFixed(1)}% ({range})
          </div>
        </div>
      )}
    </div>
  )
}
