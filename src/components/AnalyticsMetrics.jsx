import { useState, useEffect } from 'react'
import { 
  Building2, School, Heart, Trees, UtensilsCrossed, ShoppingBag, 
  Landmark, Train, Bus, TrendingUp, TrendingDown, Shield, Clock,
  Users, Leaf, Car, Home, ArrowUpRight, ArrowDownRight, Minus,
  Target, Wallet, BarChart3, Activity, Gauge, Sparkles, Play, Loader2, Coins
} from 'lucide-react'

import { API_URL } from '../apiConfig'

const CARD_COSTS = {
  infrastructure: 5,
  livability: 5,
  investment: 8,
  comparison: 5
}

// Clickable card wrapper with AI explanation
function ClickableInsightCard({ cardType, cardData, lat, lng, areaName, userId = 1, children }) {
  const [isLoading, setIsLoading] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const cost = CARD_COSTS[cardType] || 5
  
  const handleClick = async () => {
    if (isLoading) return
    
    setIsLoading(true)
    
    try {
      const response = await fetch(`${API_URL}/api/insight/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          card_type: cardType,
          lat: lat || 12.9716,
          lng: lng || 77.5946,
          user_id: userId,
          area_name: areaName || 'Current Area',
          card_data: cardData
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        // Send explanation to chat panel
        window.dispatchEvent(new CustomEvent('valora-insight-explanation', {
          detail: {
            cardType,
            cardName: result.card_name || cardType,
            explanation: result.explanation,
            cacheHit: result.cache_hit,
            charged: result.charged,
            unitsCharged: result.units_charged,
            hasSimulation: result.has_simulation,
            simulationData: result.simulation_data,
            lat,
            lng,
            areaName
          }
        }))
        
        // If simulation is available, also trigger cinema mode
        if (result.has_simulation && result.simulation_data?.available) {
          window.dispatchEvent(new CustomEvent('valora-simulation-available', {
            detail: {
              cardType,
              simulationTypes: result.simulation_data.simulation_types,
              lat,
              lng,
              preview: result.simulation_data.preview
            }
          }))
        }
      } else if (result.error === 'insufficient_units') {
        // Show top-up prompt
        window.dispatchEvent(new CustomEvent('valora-topup-needed', {
          detail: {
            message: result.message,
            cost: result.cost,
            remaining: result.remaining
          }
        }))
      }
    } catch (error) {
      console.error('Failed to get insight explanation:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  return (
    <div 
      className="relative cursor-pointer transition-all duration-200 hover:scale-[1.02] hover:shadow-lg hover:shadow-blue-500/10"
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-slate-900/80 rounded-xl flex items-center justify-center z-10">
          <div className="flex items-center gap-2 text-blue-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-xs">Analyzing...</span>
          </div>
        </div>
      )}
      
      {/* Hover indicator */}
      {isHovered && !isLoading && (
        <div className="absolute top-1 right-1 z-10 flex items-center gap-1 bg-blue-500/90 text-white text-[8px] px-1.5 py-0.5 rounded-full">
          <Sparkles className="w-2.5 h-2.5" />
          <span>Click for AI insight</span>
          <Coins className="w-2.5 h-2.5 ml-0.5" />
          <span>{cost}</span>
        </div>
      )}
      
      {children}
    </div>
  )
}

// Score bar component for visual representation
function ScoreBar({ score, max = 100, color = 'blue', size = 'sm' }) {
  const percentage = Math.min(100, (score / max) * 100)
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    purple: 'bg-purple-500',
    cyan: 'bg-cyan-500',
    orange: 'bg-orange-500'
  }
  
  return (
    <div className={`w-full bg-slate-700/50 rounded-full overflow-hidden ${size === 'sm' ? 'h-1.5' : 'h-2'}`}>
      <div 
        className={`h-full ${colorClasses[color] || colorClasses.blue} transition-all duration-500`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

// Comparison indicator
function ComparisonBadge({ value, suffix = '%' }) {
  if (!value && value !== 0) return null
  
  const isPositive = value > 0
  const isNeutral = value === 0
  
  return (
    <span className={`flex items-center gap-0.5 text-[9px] font-medium ${
      isPositive ? 'text-green-400' : isNeutral ? 'text-slate-400' : 'text-red-400'
    }`}>
      {isPositive ? <ArrowUpRight className="w-2.5 h-2.5" /> : 
       isNeutral ? <Minus className="w-2.5 h-2.5" /> : 
       <ArrowDownRight className="w-2.5 h-2.5" />}
      {isPositive ? '+' : ''}{value}{suffix}
    </span>
  )
}

// Infrastructure breakdown component
export function InfrastructureBreakdown({ infrastructure, lat, lng, areaName, userId }) {
  if (!infrastructure) return null
  
  const items = [
    { key: 'schools', icon: School, label: 'Schools', color: 'text-blue-400' },
    { key: 'hospitals', icon: Heart, label: 'Hospitals', color: 'text-red-400' },
    { key: 'parks', icon: Trees, label: 'Parks', color: 'text-green-400' },
    { key: 'restaurants', icon: UtensilsCrossed, label: 'Restaurants', color: 'text-orange-400' },
    { key: 'shopping', icon: ShoppingBag, label: 'Shopping', color: 'text-purple-400' },
    { key: 'banks_atms', icon: Landmark, label: 'Banks/ATMs', color: 'text-yellow-400' },
    { key: 'metro_stations', icon: Train, label: 'Metro', color: 'text-cyan-400' },
    { key: 'bus_stops', icon: Bus, label: 'Bus Stops', color: 'text-slate-300' }
  ]
  
  return (
    <ClickableInsightCard 
      cardType="infrastructure" 
      cardData={infrastructure} 
      lat={lat} 
      lng={lng} 
      areaName={areaName}
      userId={userId}
    >
      <div className="bg-slate-800/40 rounded-xl p-3 border border-slate-700/50 h-fit hover:border-blue-500/50 transition-colors">
        <div className="flex items-center gap-1.5 mb-2">
          <Building2 className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-blue-400 font-bold text-[10px] uppercase tracking-tight">Infrastructure (1km)</span>
        </div>
        <div className="grid grid-cols-4 gap-1.5">
          {items.map(({ key, icon: Icon, label, color }) => (
            <div key={key} className="bg-slate-900/50 rounded-lg p-1.5 text-center">
              <Icon className={`w-3 h-3 mx-auto ${color}`} />
              <div className="text-white font-bold text-xs mt-0.5">{infrastructure[key] || 0}</div>
              <div className="text-slate-500 text-[7px] truncate">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </ClickableInsightCard>
  )
}

// Livability scores component
export function LivabilityScores({ livability, lat, lng, areaName, userId }) {
  if (!livability) return null
  
  const scores = [
    { key: 'overall_score', label: 'Overall', icon: Gauge, color: 'purple' },
    { key: 'commute_score', label: 'Commute', icon: Car, color: 'blue' },
    { key: 'lifestyle_score', label: 'Lifestyle', icon: Activity, color: 'orange' },
    { key: 'safety_index', label: 'Safety', icon: Shield, color: 'green' },
    { key: 'green_score', label: 'Green', icon: Leaf, color: 'cyan' }
  ]
  
  return (
    <ClickableInsightCard 
      cardType="livability" 
      cardData={livability} 
      lat={lat} 
      lng={lng} 
      areaName={areaName}
      userId={userId}
    >
      <div className="bg-slate-800/40 rounded-xl p-3 border border-green-500/20 h-fit hover:border-green-500/50 transition-colors">
        <div className="flex items-center gap-1.5 mb-2">
          <Activity className="w-3.5 h-3.5 text-green-400" />
          <span className="text-green-400 font-bold text-[10px] uppercase tracking-tight">Livability Index</span>
        </div>
        <div className="space-y-1.5">
          {scores.map(({ key, label, icon: Icon, color }) => (
            <div key={key} className="flex items-center gap-2">
              <Icon className={`w-3 h-3 text-${color}-400 flex-shrink-0`} />
              <span className="text-slate-400 text-[9px] w-12">{label}</span>
              <div className="flex-1 min-w-0">
                <ScoreBar score={livability[key] || 0} color={color} />
              </div>
              <span className="text-white font-bold text-[9px] w-6 text-right">{livability[key] || 0}</span>
            </div>
          ))}
        </div>
      </div>
    </ClickableInsightCard>
  )
}

// Investment metrics component
export function InvestmentMetrics({ investment, market, lat, lng, areaName, userId }) {
  if (!investment) return null
  
  const riskColors = {
    'Low': 'text-green-400 bg-green-500/10',
    'Medium': 'text-yellow-400 bg-yellow-500/10',
    'High': 'text-red-400 bg-red-500/10'
  }
  
  const liquidityColors = {
    'High': 'text-green-400',
    'Medium': 'text-yellow-400',
    'Low': 'text-red-400'
  }
  
  return (
    <ClickableInsightCard 
      cardType="investment" 
      cardData={investment} 
      lat={lat} 
      lng={lng} 
      areaName={areaName}
      userId={userId}
    >
    <div className="bg-slate-800/40 rounded-xl p-3 border border-purple-500/20 h-fit hover:border-purple-500/50 transition-colors">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-1">
        <div className="flex items-center gap-1.5">
          <Target className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-purple-400 font-bold text-[10px] uppercase tracking-tight">Investment</span>
        </div>
        <span className={`text-[8px] px-1.5 py-0.5 rounded ${riskColors[investment.risk_level] || riskColors['Medium']}`}>
          {investment.risk_level} Risk
        </span>
      </div>
      
      {/* Growth Potential */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-[9px] mb-1">
          <span className="text-slate-400">Growth Potential</span>
          <span className="text-purple-400 font-bold">{investment.growth_potential}/100</span>
        </div>
        <ScoreBar score={investment.growth_potential} color="purple" size="md" />
      </div>
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-1.5 text-[9px]">
        <div className="bg-slate-900/50 rounded-lg p-1.5">
          <div className="text-slate-400 text-[8px]">Rental Yield</div>
          <div className="text-green-400 font-bold text-xs">{investment.rental_yield_pct}%</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-1.5">
          <div className="text-slate-400 text-[8px]">Liquidity</div>
          <div className={`font-bold text-xs ${liquidityColors[investment.liquidity] || 'text-slate-300'}`}>
            {investment.liquidity}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-1.5">
          <div className="text-slate-400 text-[8px]">1Y Growth</div>
          <div className="flex items-center gap-0.5">
            <TrendingUp className="w-2.5 h-2.5 text-green-400" />
            <span className="text-green-400 font-bold text-xs">+{investment.appreciation_1y}%</span>
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-1.5">
          <div className="text-slate-400 text-[8px]">5Y Forecast</div>
          <div className="flex items-center gap-0.5">
            <TrendingUp className="w-2.5 h-2.5 text-cyan-400" />
            <span className="text-cyan-400 font-bold text-xs">+{investment.appreciation_5y}%</span>
          </div>
        </div>
      </div>
      
      {/* Buyer recommendation */}
      <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between text-[9px] flex-wrap gap-1">
        <div className="flex items-center gap-1">
          <Users className="w-2.5 h-2.5 text-slate-400" />
          <span className="text-white font-medium">{investment.buyer_type}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-2.5 h-2.5 text-slate-400" />
          <span className="text-slate-300">{investment.holding_period}</span>
        </div>
      </div>
    </div>
    </ClickableInsightCard>
  )
}

// Area comparison component
export function AreaComparison({ comparison, lat, lng, areaName, userId }) {
  if (!comparison) return null
  
  const vsAvg = comparison.vs_city_avg || {}
  
  const metrics = [
    { key: 'price', label: 'Price', suffix: '%' },
    { key: 'accessibility', label: 'Accessibility', suffix: '' },
    { key: 'walkability', label: 'Walkability', suffix: '' },
    { key: 'amenities', label: 'Amenities', suffix: '%' }
  ]
  
  const stageColors = {
    'Mature': 'text-green-400 bg-green-500/10',
    'Growing': 'text-yellow-400 bg-yellow-500/10',
    'Emerging': 'text-cyan-400 bg-cyan-500/10'
  }
  
  const bracketColors = {
    'Premium': 'text-purple-400 bg-purple-500/10',
    'Mid-range': 'text-blue-400 bg-blue-500/10',
    'Affordable': 'text-green-400 bg-green-500/10'
  }
  
  return (
    <ClickableInsightCard 
      cardType="comparison" 
      cardData={comparison} 
      lat={lat} 
      lng={lng} 
      areaName={areaName}
      userId={userId}
    >
    <div className="bg-slate-800/40 rounded-xl p-3 border border-cyan-500/20 h-fit hover:border-cyan-500/50 transition-colors">
      <div className="flex items-center gap-1.5 mb-2">
        <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
        <span className="text-cyan-400 font-bold text-[10px] uppercase tracking-tight">vs City Average</span>
      </div>
      
      {/* Comparison bars */}
      <div className="space-y-1 mb-2">
        {metrics.map(({ key, label, suffix }) => (
          <div key={key} className="flex items-center gap-2 text-[9px]">
            <span className="text-slate-400 w-16">{label}</span>
            <div className="flex-1 flex items-center gap-1">
              <ComparisonBadge value={vsAvg[key]} suffix={suffix} />
            </div>
          </div>
        ))}
      </div>
      
      {/* Tags */}
      <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-slate-700/50 flex-wrap">
        <span className={`text-[8px] px-1.5 py-0.5 rounded ${bracketColors[comparison.price_bracket] || bracketColors['Mid-range']}`}>
          {comparison.price_bracket}
        </span>
        <span className={`text-[8px] px-1.5 py-0.5 rounded ${stageColors[comparison.development_stage] || stageColors['Growing']}`}>
          {comparison.development_stage}
        </span>
      </div>
    </div>
    </ClickableInsightCard>
  )
}

// Main combined metrics component
export default function AnalyticsMetrics({ viewportAnalysis, lat, lng, areaName, userId = 1 }) {
  if (!viewportAnalysis) return null
  
  const { infrastructure, livability, investment, comparison } = viewportAnalysis
  
  // Extract coordinates from viewportAnalysis if not provided
  const coordLat = lat || viewportAnalysis?.coordinates?.lat || 12.9716
  const coordLng = lng || viewportAnalysis?.coordinates?.lng || 77.5946
  const name = areaName || viewportAnalysis?.area_name || 'Current Area'
  
  // Don't render if no enhanced metrics available
  if (!infrastructure && !livability && !investment && !comparison) {
    return null
  }
  
  return (
    <div className="max-w-4xl mx-auto">
      {/* Info banner */}
      <div className="mb-2 flex items-center gap-2 text-[9px] text-slate-400 bg-slate-800/30 rounded-lg px-2 py-1">
        <Sparkles className="w-3 h-3 text-blue-400" />
        <span>Click any card for AI-powered insights • Cached within 2km</span>
      </div>
      
      {/* Responsive 2-column grid for larger screens */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {infrastructure && (
          <InfrastructureBreakdown 
            infrastructure={infrastructure} 
            lat={coordLat} 
            lng={coordLng} 
            areaName={name}
            userId={userId}
          />
        )}
        {livability && (
          <LivabilityScores 
            livability={livability} 
            lat={coordLat} 
            lng={coordLng} 
            areaName={name}
            userId={userId}
          />
        )}
        {investment && (
          <InvestmentMetrics 
            investment={investment} 
            market={viewportAnalysis.market} 
            lat={coordLat} 
            lng={coordLng} 
            areaName={name}
            userId={userId}
          />
        )}
        {comparison && (
          <AreaComparison 
            comparison={comparison} 
            lat={coordLat} 
            lng={coordLng} 
            areaName={name}
            userId={userId}
          />
        )}
      </div>
    </div>
  )
}
