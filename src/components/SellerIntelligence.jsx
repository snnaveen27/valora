/**
 * SellerIntelligence - AI-powered seller insights
 * 
 * Shows for listings:
 * - Suggested price range
 * - Demand score
 * - Comparable properties
 * - Market trend insights
 * - Best time to sell
 */

import { useState } from 'react'
import { TrendingUp, TrendingDown, Minus, Star, Calendar, Target, BarChart3, Info } from 'lucide-react'
import { API_URL } from '../apiConfig'

export default function SellerIntelligence({ listing, locality }) {
  const [intelligence, setIntelligence] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchIntelligence = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/seller/intelligence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_type: listing.property_type,
          bedrooms: listing.bedrooms,
          area_sqft: listing.area_sqft,
          locality: listing.locality || locality,
          price: listing.price,
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setIntelligence(data)
      } else {
        setError('Failed to fetch insights')
      }
    } catch (err) {
      setError('Error loading insights')
      console.error('[SellerIntelligence] Error:', err)
    } finally {
      setLoading(false)
    }
  }

  // Trend icon
  const TrendIcon = ({ trend }) => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4 text-green-400" />
    if (trend === 'down') return <TrendingDown className="w-4 h-4 text-red-400" />
    return <Minus className="w-4 h-4 text-yellow-400" />
  }

  // Score bar
  const ScoreBar = ({ score, max = 100, color = 'primary' }) => (
    <div className="w-full bg-dark-600 rounded-full h-2">
      <div 
        className={`h-2 rounded-full transition-all ${
          color === 'green' ? 'bg-green-500' : color === 'yellow' ? 'bg-yellow-500' : 'bg-primary-500'
        }`}
        style={{ width: `${Math.min(100, score)}%` }}
      />
    </div>
  )

  return (
    <div className="bg-dark-800/50 rounded-xl p-4 border border-primary-700/30">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-white flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary-400" />
          Seller Intelligence
        </h4>
        <button
          onClick={fetchIntelligence}
          disabled={loading}
          className="text-xs text-primary-400 hover:text-white"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-400 mb-3">{error}</p>
      )}

      {intelligence ? (
        <div className="space-y-4">
          {/* Suggested Price Range */}
          <div className="bg-dark-700/50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-4 h-4 text-primary-400" />
              <span className="text-sm font-medium text-white">Suggested Price</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-green-400">
                ₹{intelligence.suggested_price_min?.toLocaleString()}
              </span>
              <span className="text-primary-400">-</span>
              <span className="text-xl font-bold text-green-400">
                ₹{intelligence.suggested_price_max?.toLocaleString()}
              </span>
            </div>
            {intelligence.listing_price && intelligence.suggested_price_max && (
              <p className={`text-xs mt-1 ${
                intelligence.listing_price > intelligence.suggested_price_max 
                  ? 'text-yellow-400' 
                  : 'text-green-400'
              }`}>
                {intelligence.listing_price > intelligence.suggested_price_max 
                  ? '⚠️ Above market - may take longer to sell'
                  : '✓ Within market range'}
              </p>
            )}
          </div>

          {/* Demand Score */}
          <div className="bg-dark-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4 text-yellow-400" />
                <span className="text-sm font-medium text-white">Demand Score</span>
              </div>
              <span className="text-lg font-bold text-white">{intelligence.demand_score}/100</span>
            </div>
            <ScoreBar score={intelligence.demand_score} color={intelligence.demand_score > 70 ? 'green' : intelligence.demand_score > 40 ? 'yellow' : 'primary'} />
            <p className="text-xs text-primary-400 mt-1">
              {intelligence.demand_score > 70 ? 'High demand area' : intelligence.demand_score > 40 ? 'Moderate demand' : 'Lower demand'}
            </p>
          </div>

          {/* Best Time to Sell */}
          <div className="bg-dark-700/50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-primary-400" />
              <span className="text-sm font-medium text-white">Best Time to Sell</span>
            </div>
            <p className="text-primary-200">{intelligence.best_time || 'Now is a good time'}</p>
          </div>

          {/* Market Trend */}
          <div className="bg-dark-700/50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <TrendIcon trend={intelligence.market_trend} />
              <span className="text-sm font-medium text-white">Market Trend</span>
            </div>
            <p className="text-primary-200">
              {intelligence.trend_description || 'Stable market'}
            </p>
          </div>

          {/* Comparables */}
          {intelligence.comparable_properties?.length > 0 && (
            <div className="bg-dark-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <Info className="w-4 h-4 text-primary-400" />
                <span className="text-sm font-medium text-white">Comparable Properties</span>
              </div>
              <div className="space-y-2">
                {intelligence.comparable_properties.slice(0, 3).map((comp, i) => (
                  <div key={i} className="flex justify-between items-center text-sm">
                    <span className="text-primary-300">{comp.property}</span>
                    <span className="text-primary-200">₹{comp.price?.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-primary-400 text-center py-4">
          Click "Analyze" to get AI-powered insights
        </p>
      )}
    </div>
  )
}