import { useState } from 'react'
import { 
  Brain, ChevronDown, ChevronUp, Info, Zap, ArrowRight,
  Train, School, Droplets, Building2, TrendingUp, MapPin, Trees, ShieldCheck
} from 'lucide-react'

// Feature impact bar component
function FeatureBar({ feature, impact, maxImpact, icon: Icon, expanded, onToggle }) {
  const isPositive = impact > 0
  const width = Math.abs(impact / maxImpact) * 100
  
  return (
    <div className="mb-1.5">
      <div 
        className="flex items-center gap-2 cursor-pointer hover:bg-slate-700/30 rounded p-1 -mx-1 transition"
        onClick={onToggle}
      >
        <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${isPositive ? 'text-green-400' : 'text-red-400'}`} />
        <span className="text-slate-300 text-[10px] flex-1 truncate">{feature}</span>
        <div className="flex items-center gap-1 w-32">
          {/* Negative bar */}
          <div className="w-14 h-2 bg-slate-700/50 rounded-full overflow-hidden flex justify-end">
            {!isPositive && (
              <div 
                className="h-full bg-red-500 rounded-full transition-all duration-500"
                style={{ width: `${width}%` }}
              />
            )}
          </div>
          {/* Center line */}
          <div className="w-0.5 h-3 bg-slate-600" />
          {/* Positive bar */}
          <div className="w-14 h-2 bg-slate-700/50 rounded-full overflow-hidden">
            {isPositive && (
              <div 
                className="h-full bg-green-500 rounded-full transition-all duration-500"
                style={{ width: `${width}%` }}
              />
            )}
          </div>
        </div>
        <span className={`text-[10px] font-bold w-10 text-right ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{impact.toFixed(1)}%
        </span>
        {expanded ? <ChevronUp className="w-3 h-3 text-slate-500" /> : <ChevronDown className="w-3 h-3 text-slate-500" />}
      </div>
      
      {expanded && (
        <div className="ml-6 mt-1 p-2 bg-slate-900/50 rounded text-[9px] text-slate-400 border-l-2 border-slate-700">
          <div className="flex items-center justify-between mb-1">
            <span>Raw value:</span>
            <span className="text-white font-medium">{feature.includes('distance') ? '450m' : feature.includes('score') ? '85/100' : 'High'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>City benchmark:</span>
            <span className="text-slate-300">{feature.includes('distance') ? '1.2km avg' : '72/100 avg'}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// Causal chain component
function CausalChain({ chain }) {
  if (!chain) return null
  
  return (
    <div className="bg-gradient-to-r from-purple-500/10 to-indigo-500/10 rounded-lg p-2.5 border border-purple-500/20 mt-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Zap className="w-3.5 h-3.5 text-purple-400" />
        <span className="text-purple-400 font-bold text-[10px] uppercase">Causal Insight</span>
      </div>
      <div className="flex items-center gap-2 text-[10px]">
        <span className="text-white font-medium">{chain.trigger}</span>
        <ArrowRight className="w-3 h-3 text-purple-400" />
        <span className="text-green-400 font-bold">{chain.effect}</span>
        <span className="text-slate-400">({chain.timeframe})</span>
      </div>
      <div className="mt-1.5 flex items-center gap-1">
        <div className="h-1 flex-1 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
            style={{ width: `${chain.confidence}%` }}
          />
        </div>
        <span className="text-[9px] text-purple-300">{chain.confidence}% confidence</span>
      </div>
    </div>
  )
}

// Raw features table
function RawFeaturesTable({ features, expanded }) {
  if (!expanded || !features) return null
  
  return (
    <div className="mt-3 bg-slate-900/50 rounded-lg p-2 border border-slate-700/50">
      <div className="text-[9px] text-slate-400 mb-2 uppercase tracking-wide">Raw Model Inputs</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {Object.entries(features).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between text-[9px]">
            <span className="text-slate-500 truncate">{key.replace(/_/g, ' ')}</span>
            <span className="text-slate-300 font-mono">{typeof value === 'number' ? value.toFixed(2) : String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ExplainabilityShap({ 
  features = [], 
  causalChain = null,
  rawFeatures = null,
  valuationModel = 'Gradient Boost + Spatial'
}) {
  const [expandedFeature, setExpandedFeature] = useState(null)
  const [showRaw, setShowRaw] = useState(false)
  
  // Default features if none provided
  const defaultFeatures = [
    { name: 'Distance to Metro', impact: 12.5, icon: Train },
    { name: 'School Quality Score', impact: 8.2, icon: School },
    { name: 'Walkability Index', impact: 6.8, icon: MapPin },
    { name: 'Green Cover Ratio', impact: 4.1, icon: Trees },
    { name: 'Flood Risk Zone', impact: -7.3, icon: Droplets },
    { name: 'Supply Growth Rate', impact: -5.2, icon: Building2 },
    { name: 'Infrastructure Age', impact: -3.8, icon: ShieldCheck },
    { name: 'Price Momentum', impact: 5.5, icon: TrendingUp }
  ]
  
  const featureList = features.length > 0 ? features : defaultFeatures
  const sortedFeatures = [...featureList].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
  const maxImpact = Math.max(...sortedFeatures.map(f => Math.abs(f.impact)))
  
  const defaultCausal = {
    trigger: 'Metro Purple Line opens nearby',
    effect: '+12-18% price uplift',
    timeframe: '1-3 years',
    confidence: 85
  }
  
  const defaultRaw = {
    distance_metro_m: 450,
    school_count_1km: 8,
    hospital_count_2km: 3,
    walkability_score: 78,
    green_cover_pct: 12.5,
    flood_risk_score: 0.15,
    avg_building_age: 8.2,
    supply_growth_pct: 4.5,
    demand_index: 72,
    price_momentum_3m: 2.1
  }
  
  return (
    <div className="bg-slate-800/40 rounded-xl p-3 border border-amber-500/20 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-amber-400" />
          <span className="text-amber-400 font-bold text-[10px] uppercase">Why This Valuation?</span>
        </div>
        <div className="flex items-center gap-1">
          <Info className="w-3 h-3 text-slate-500" />
          <span className="text-[8px] text-slate-500">{valuationModel}</span>
        </div>
      </div>
      
      {/* Feature importance bars */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-[9px] text-slate-500 mb-2 px-1">
          <span>Top 8 Value Drivers</span>
          <div className="flex items-center gap-3">
            <span className="text-red-400">← Negative</span>
            <span className="text-green-400">Positive →</span>
          </div>
        </div>
        
        {sortedFeatures.slice(0, 8).map((f, i) => (
          <FeatureBar
            key={i}
            feature={f.name}
            impact={f.impact}
            maxImpact={maxImpact}
            icon={f.icon || MapPin}
            expanded={expandedFeature === i}
            onToggle={() => setExpandedFeature(expandedFeature === i ? null : i)}
          />
        ))}
      </div>
      
      {/* Summary */}
      <div className="flex items-center justify-between text-[10px] py-2 border-t border-slate-700/50">
        <div>
          <span className="text-slate-400">Net Impact: </span>
          <span className="text-green-400 font-bold">
            +{sortedFeatures.reduce((sum, f) => sum + f.impact, 0).toFixed(1)}%
          </span>
          <span className="text-slate-500"> vs baseline</span>
        </div>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="flex items-center gap-1 text-slate-400 hover:text-white transition"
        >
          <span>Raw inputs</span>
          {showRaw ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>
      
      {/* Causal Chain */}
      <CausalChain chain={causalChain || defaultCausal} />
      
      {/* Raw Features */}
      <RawFeaturesTable features={rawFeatures || defaultRaw} expanded={showRaw} />
      
      {/* Method note */}
      <div className="mt-2 text-[9px] text-slate-500 italic">
        <Info className="w-2.5 h-2.5 inline mr-1" />
        SHAP values computed from ensemble model trained on 50k+ Bangalore transactions.
      </div>
    </div>
  )
}
