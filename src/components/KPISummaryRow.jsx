import { useState, useEffect } from 'react'
import { 
  MapPin, TrendingUp, TrendingDown, Minus, AlertTriangle, Shield, 
  Gauge, Info, Flame, Snowflake, ThermometerSun, Navigation
} from 'lucide-react'

// Momentum indicator component
function MomentumBadge({ momentum }) {
  const config = {
    hot: { icon: Flame, color: 'text-orange-400 bg-orange-500/20', label: 'Hot' },
    warming: { icon: TrendingUp, color: 'text-yellow-400 bg-yellow-500/20', label: 'Warming' },
    neutral: { icon: ThermometerSun, color: 'text-slate-400 bg-slate-500/20', label: 'Neutral' },
    cooling: { icon: Snowflake, color: 'text-blue-400 bg-blue-500/20', label: 'Cooling' }
  }
  
  const { icon: Icon, color, label } = config[momentum] || config.neutral
  
  return (
    <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${color}`}>
      <Icon className="w-3 h-3" />
      {label}
    </div>
  )
}

// Risk gauge component
function RiskGauge({ riskScore, label = 'Risk' }) {
  const getColor = (score) => {
    if (score <= 30) return { color: 'text-green-400', bg: 'bg-green-500', label: 'Low' }
    if (score <= 60) return { color: 'text-yellow-400', bg: 'bg-yellow-500', label: 'Medium' }
    return { color: 'text-red-400', bg: 'bg-red-500', label: 'High' }
  }
  
  const { color, bg, label: riskLabel } = getColor(riskScore)
  const rotation = (riskScore / 100) * 180 - 90 // -90 to 90 degrees
  
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-12 h-6 overflow-hidden">
        {/* Gauge background */}
        <div className="absolute bottom-0 left-0 right-0 h-6 rounded-t-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 opacity-30" />
        {/* Needle */}
        <div 
          className="absolute bottom-0 left-1/2 w-0.5 h-5 bg-white origin-bottom transition-transform duration-500"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        />
        {/* Center dot */}
        <div className="absolute bottom-0 left-1/2 w-2 h-2 -translate-x-1/2 translate-y-1/2 bg-white rounded-full" />
      </div>
      <div className={`text-[9px] font-medium ${color} mt-0.5`}>{riskLabel}</div>
    </div>
  )
}

// Confidence indicator
function ConfidenceIndicator({ confidence, drivers = [] }) {
  const [showTooltip, setShowTooltip] = useState(false)
  
  const getColor = (conf) => {
    if (conf >= 80) return 'text-green-400'
    if (conf >= 60) return 'text-yellow-400'
    return 'text-red-400'
  }
  
  return (
    <div className="relative">
      <div 
        className="flex items-center gap-1 cursor-help"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <div className={`text-lg font-bold ${getColor(confidence)}`}>{confidence}%</div>
        <Info className="w-3 h-3 text-slate-500" />
      </div>
      
      {showTooltip && drivers.length > 0 && (
        <div className="absolute top-full left-0 mt-1 p-2 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 min-w-[180px]">
          <div className="text-[9px] text-slate-400 mb-1">Confidence Drivers:</div>
          {drivers.map((d, i) => (
            <div key={i} className="text-[10px] text-slate-300 flex justify-between">
              <span>{d.name}</span>
              <span className={d.impact > 0 ? 'text-green-400' : 'text-red-400'}>
                {d.impact > 0 ? '+' : ''}{d.impact}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function KPISummaryRow({ 
  locality, 
  medianPrice, 
  priceChange3Y, 
  momentum, 
  riskScore, 
  confidence,
  confidenceDrivers = [],
  onFlyTo,
  isFullscreen = false
}) {
  return (
    <div className="bg-gradient-to-r from-slate-800/80 to-slate-900/80 rounded-xl p-3 border border-slate-700/50 backdrop-blur-sm max-w-4xl mx-auto">
      {/* Responsive grid - adapts from row to 2-row layout */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        
        {/* Locality Name + Fly-to - spans 2 cols on mobile */}
        <div className="col-span-2 sm:col-span-1 lg:col-span-1 flex items-center gap-2 min-w-0">
          <button 
            onClick={onFlyTo}
            className="p-2 bg-blue-500/20 hover:bg-blue-500/30 rounded-xl transition group flex-shrink-0"
            title="Fly to location"
          >
            <Navigation className="w-4 h-4 text-blue-400 group-hover:text-blue-300" />
          </button>
          <div className="min-w-0">
            <div className="text-white font-semibold text-sm truncate max-w-[140px]">{locality || 'Current Location'}</div>
            <div className="text-slate-500 text-[9px]">Analysis Zone</div>
          </div>
        </div>
        
        {/* Median Price - compact card style */}
        <div className="bg-slate-900/50 rounded-lg p-2 text-center">
          <div className="text-slate-400 text-[9px] uppercase tracking-wide">₹/sqft</div>
          <div className="text-white font-bold text-base">
            {medianPrice ? `₹${medianPrice.toLocaleString()}` : '—'}
          </div>
          {priceChange3Y !== undefined && (
            <div className={`flex items-center justify-center gap-0.5 text-[9px] ${
              priceChange3Y > 0 ? 'text-green-400' : priceChange3Y < 0 ? 'text-red-400' : 'text-slate-400'
            }`}>
              {priceChange3Y > 0 ? <TrendingUp className="w-2.5 h-2.5" /> : 
               priceChange3Y < 0 ? <TrendingDown className="w-2.5 h-2.5" /> : 
               <Minus className="w-2.5 h-2.5" />}
              {priceChange3Y > 0 ? '+' : ''}{priceChange3Y}%
            </div>
          )}
        </div>
        
        {/* Momentum - compact card */}
        <div className="bg-slate-900/50 rounded-lg p-2 flex flex-col items-center justify-center">
          <div className="text-slate-400 text-[9px] uppercase tracking-wide mb-1">Momentum</div>
          <MomentumBadge momentum={momentum || 'neutral'} />
        </div>
        
        {/* Risk Index - compact card */}
        <div className="bg-slate-900/50 rounded-lg p-2 flex flex-col items-center justify-center">
          <div className="text-slate-400 text-[9px] uppercase tracking-wide mb-1">Risk</div>
          <RiskGauge riskScore={riskScore || 50} />
        </div>
        
        {/* Confidence - compact card */}
        <div className="bg-slate-900/50 rounded-lg p-2 flex flex-col items-center justify-center">
          <div className="text-slate-400 text-[9px] uppercase tracking-wide mb-1">Confidence</div>
          <ConfidenceIndicator 
            confidence={confidence || 75} 
            drivers={confidenceDrivers}
          />
        </div>
        
      </div>
    </div>
  )
}
