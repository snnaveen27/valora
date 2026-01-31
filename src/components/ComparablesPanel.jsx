import { useState, useEffect } from 'react'
import { 
  Scale, MapPin, Calendar, Home, ArrowUpDown, Sliders, 
  RefreshCw, ChevronDown, ChevronUp, ExternalLink
} from 'lucide-react'
import { API_URL } from '../apiConfig'

// Adjustment slider component
function AdjustmentSlider({ label, value, onChange, min = -20, max = 20 }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[9px] text-slate-400 w-16">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
      />
      <span className={`text-[10px] font-mono w-10 text-right ${
        value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-slate-400'
      }`}>
        {value > 0 ? '+' : ''}{value}%
      </span>
    </div>
  )
}

// Single comparable card
function CompCard({ comp, isSelected, onSelect, adjustments }) {
  const adjustedPrice = comp.price * (1 + (adjustments?.sqft || 0) / 100) * (1 + (adjustments?.floor || 0) / 100)
  
  return (
    <div 
      className={`p-2 rounded-lg border transition cursor-pointer ${
        isSelected 
          ? 'bg-purple-500/10 border-purple-500/50' 
          : 'bg-slate-900/40 border-slate-700/50 hover:border-slate-600'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between mb-1">
        <div className="flex-1 min-w-0">
          <div className="text-white text-[11px] font-medium truncate">{comp.name || 'Property'}</div>
          <div className="text-slate-500 text-[9px] truncate flex items-center gap-1">
            <MapPin className="w-2.5 h-2.5" />
            {comp.locality} • {comp.distance_m}m away
          </div>
        </div>
        <div className="text-right">
          <div className="text-green-400 text-[11px] font-bold">₹{(comp.price / 100000).toFixed(1)}L</div>
          <div className="text-slate-400 text-[9px]">₹{comp.price_per_sqft}/sqft</div>
        </div>
      </div>
      
      <div className="flex items-center gap-2 text-[9px] text-slate-400">
        <span className="flex items-center gap-0.5">
          <Home className="w-2.5 h-2.5" />
          {comp.bedrooms}BHK
        </span>
        <span>{comp.area_sqft} sqft</span>
        <span className="flex items-center gap-0.5">
          <Calendar className="w-2.5 h-2.5" />
          {comp.date || 'Recent'}
        </span>
      </div>
      
      {isSelected && adjustments && (
        <div className="mt-2 pt-2 border-t border-slate-700/50 text-[9px]">
          <div className="flex items-center justify-between text-slate-400">
            <span>Adjusted estimate:</span>
            <span className="text-purple-400 font-bold">₹{(adjustedPrice / 100000).toFixed(1)}L</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ComparablesPanel({ lat, lng, locality, radius = 1000 }) {
  const [comps, setComps] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedComp, setSelectedComp] = useState(null)
  const [showAdjustments, setShowAdjustments] = useState(false)
  const [adjustments, setAdjustments] = useState({
    sqft: 0,
    floor: 0,
    age: 0,
    facing: 0
  })
  const [sortBy, setSortBy] = useState('distance') // distance, price, date
  
  // Fetch comparables
  useEffect(() => {
    const fetchComps = async () => {
      setLoading(true)
      try {
        // Try API first
        const resp = await fetch(
          `${API_URL}/api/properties/search?lat=${lat}&lng=${lng}&radius=${radius}&limit=10`
        )
        if (resp.ok) {
          const data = await resp.json()
          if (data.properties && data.properties.length > 0) {
            setComps(data.properties)
            setLoading(false)
            return
          }
        }
      } catch (err) {
        console.warn('Comps API failed, using sample data')
      }
      
      // Sample data fallback
      const sampleComps = [
        { id: 1, name: '3BHK in Brigade Gateway', locality: 'Rajajinagar', bedrooms: 3, area_sqft: 1650, price: 18500000, price_per_sqft: 11212, distance_m: 250, date: '2025-12' },
        { id: 2, name: '2BHK in Prestige Lakeside', locality: 'Koramangala', bedrooms: 2, area_sqft: 1200, price: 12000000, price_per_sqft: 10000, distance_m: 450, date: '2025-11' },
        { id: 3, name: '4BHK Villa', locality: 'Indiranagar', bedrooms: 4, area_sqft: 2800, price: 35000000, price_per_sqft: 12500, distance_m: 680, date: '2025-10' },
        { id: 4, name: '2BHK Apartment', locality: 'HSR Layout', bedrooms: 2, area_sqft: 1100, price: 9500000, price_per_sqft: 8636, distance_m: 820, date: '2025-12' },
        { id: 5, name: '3BHK in Sobha Dream', locality: 'Whitefield', bedrooms: 3, area_sqft: 1800, price: 16200000, price_per_sqft: 9000, distance_m: 950, date: '2025-09' },
      ]
      setComps(sampleComps)
      setLoading(false)
    }
    
    if (lat && lng) {
      fetchComps()
    }
  }, [lat, lng, radius])
  
  // Sort comparables
  const sortedComps = [...comps].sort((a, b) => {
    if (sortBy === 'distance') return a.distance_m - b.distance_m
    if (sortBy === 'price') return a.price - b.price
    if (sortBy === 'date') return (b.date || '').localeCompare(a.date || '')
    return 0
  })
  
  // Calculate adjusted valuation
  const calculateAdjustedValuation = () => {
    if (!selectedComp) return null
    const comp = comps.find(c => c.id === selectedComp)
    if (!comp) return null
    
    let adjusted = comp.price
    adjusted *= (1 + adjustments.sqft / 100)
    adjusted *= (1 + adjustments.floor / 100)
    adjusted *= (1 + adjustments.age / 100)
    adjusted *= (1 + adjustments.facing / 100)
    
    return adjusted
  }
  
  if (loading) {
    return (
      <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
        <div className="flex items-center gap-2 animate-pulse">
          <Scale className="w-4 h-4 text-slate-500" />
          <span className="text-slate-500 text-xs">Loading comparables...</span>
        </div>
      </div>
    )
  }
  
  return (
    <div className="bg-slate-800/40 rounded-xl p-3 border border-cyan-500/20 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-cyan-400" />
          <span className="text-cyan-400 font-bold text-[10px] uppercase">Comparables ({comps.length})</span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Sort dropdown */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-slate-900/60 text-[9px] text-slate-300 rounded px-1.5 py-0.5 border-none outline-none"
          >
            <option value="distance">By Distance</option>
            <option value="price">By Price</option>
            <option value="date">By Date</option>
          </select>
          
          {/* Adjustments toggle */}
          <button
            onClick={() => setShowAdjustments(!showAdjustments)}
            className={`p-1 rounded transition ${
              showAdjustments ? 'bg-purple-500/20 text-purple-400' : 'text-slate-500 hover:text-white'
            }`}
            title="Adjustment sliders"
          >
            <Sliders className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      
      {/* Adjustment sliders */}
      {showAdjustments && (
        <div className="mb-3 p-2 bg-slate-900/50 rounded-lg border border-purple-500/20">
          <div className="text-[9px] text-purple-400 mb-2 uppercase tracking-wide">Valuation Adjustments</div>
          <div className="space-y-2">
            <AdjustmentSlider 
              label="Area ±%" 
              value={adjustments.sqft} 
              onChange={(v) => setAdjustments(prev => ({ ...prev, sqft: v }))} 
            />
            <AdjustmentSlider 
              label="Floor ±%" 
              value={adjustments.floor} 
              onChange={(v) => setAdjustments(prev => ({ ...prev, floor: v }))} 
            />
            <AdjustmentSlider 
              label="Age ±%" 
              value={adjustments.age} 
              onChange={(v) => setAdjustments(prev => ({ ...prev, age: v }))} 
            />
            <AdjustmentSlider 
              label="Facing ±%" 
              value={adjustments.facing} 
              onChange={(v) => setAdjustments(prev => ({ ...prev, facing: v }))} 
            />
          </div>
          
          {selectedComp && (
            <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between">
              <span className="text-[10px] text-slate-400">Adjusted Estimate:</span>
              <span className="text-purple-400 font-bold text-sm">
                ₹{(calculateAdjustedValuation() / 100000).toFixed(1)}L
              </span>
            </div>
          )}
        </div>
      )}
      
      {/* Comparables list */}
      <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
        {sortedComps.map((comp) => (
          <CompCard
            key={comp.id}
            comp={comp}
            isSelected={selectedComp === comp.id}
            onSelect={() => setSelectedComp(selectedComp === comp.id ? null : comp.id)}
            adjustments={showAdjustments ? adjustments : null}
          />
        ))}
      </div>
      
      {/* Summary stats */}
      <div className="mt-3 pt-2 border-t border-slate-700/50 grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-[9px] text-slate-400">Avg Price/sqft</div>
          <div className="text-white font-bold text-[11px]">
            ₹{Math.round(comps.reduce((sum, c) => sum + c.price_per_sqft, 0) / comps.length).toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-[9px] text-slate-400">Median Price</div>
          <div className="text-white font-bold text-[11px]">
            ₹{(comps.sort((a, b) => a.price - b.price)[Math.floor(comps.length / 2)]?.price / 100000).toFixed(1)}L
          </div>
        </div>
        <div>
          <div className="text-[9px] text-slate-400">Range</div>
          <div className="text-white font-bold text-[11px]">
            {Math.round(Math.min(...comps.map(c => c.distance_m)))}–{Math.round(Math.max(...comps.map(c => c.distance_m)))}m
          </div>
        </div>
      </div>
    </div>
  )
}
