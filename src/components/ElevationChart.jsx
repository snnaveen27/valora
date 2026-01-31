import { useState, useEffect } from 'react'
import { Mountain, TrendingUp, TrendingDown } from 'lucide-react'

import { API_URL } from '../apiConfig'

export default function ElevationChart({ lat, lng, radius = 2.0, data }) {
  const [profileData, setProfileData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!lat || !lng) {
      setLoading(false)
      return
    }

    const fetchProfile = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const response = await fetch(
          `${API_URL}/api/terrain/profile?lat=${lat}&lng=${lng}&radius_km=${radius}`
        )
        
        if (!response.ok) {
          throw new Error('Failed to fetch elevation data')
        }
        
        const result = await response.json()
        
        if (result.success && result.data) {
          setProfileData(result.data)
        } else {
          setError(result.error || 'No elevation data available')
        }
      } catch (err) {
        console.warn('Elevation profile fetch failed:', err)
        setError('Unable to load elevation data')
      } finally {
        setLoading(false)
      }
    }

    fetchProfile()
  }, [lat, lng, radius])

  if (loading) {
    return (
      <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
        <div className="flex items-center gap-2 mb-2">
          <Mountain className="w-3.5 h-3.5 text-slate-400 animate-pulse" />
          <span className="text-slate-400 text-xs">Loading elevation profile...</span>
        </div>
      </div>
    )
  }

  if (error || !profileData) {
    return null // Silently hide if no data available
  }

  const { profile, statistics } = profileData
  
  if (!profile || profile.length === 0) {
    return null
  }

  // Calculate chart dimensions
  const chartWidth = 280
  const chartHeight = 80
  const padding = { top: 10, right: 10, bottom: 20, left: 35 }
  const plotWidth = chartWidth - padding.left - padding.right
  const plotHeight = chartHeight - padding.top - padding.bottom

  // Scale data to chart dimensions
  const minElev = statistics.min_elevation
  const maxElev = statistics.max_elevation
  const elevRange = maxElev - minElev || 10 // Avoid division by zero
  
  const minDist = Math.min(...profile.map(p => p.distance_km))
  const maxDist = Math.max(...profile.map(p => p.distance_km))
  const distRange = maxDist - minDist || 1

  // Generate SVG path
  const points = profile.map(p => {
    const x = padding.left + ((p.distance_km - minDist) / distRange) * plotWidth
    const y = padding.top + plotHeight - ((p.elevation_m - minElev) / elevRange) * plotHeight
    return { x, y, ...p }
  })

  const pathData = points.map((p, i) => 
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ')

  // Create filled area path
  const areaPath = `${pathData} L ${points[points.length - 1].x} ${chartHeight - padding.bottom} L ${points[0].x} ${chartHeight - padding.bottom} Z`

  // Y-axis ticks
  const yTicks = [minElev, (minElev + maxElev) / 2, maxElev]

  return (
    <div className="bg-slate-800/40 rounded-xl p-3 border border-emerald-500/20 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-1.5">
          <Mountain className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-emerald-400 font-bold text-[10px] uppercase tracking-tight">Elevation Profile</span>
        </div>
        <span className="text-[8px] text-slate-500">±{radius}km</span>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-3 gap-2 mb-2 text-[10px]">
        <div className="bg-slate-900/40 rounded px-2 py-1">
          <div className="text-slate-400">Min</div>
          <div className="text-white font-bold">{Math.round(minElev)}m</div>
        </div>
        <div className="bg-slate-900/40 rounded px-2 py-1">
          <div className="text-slate-400">Avg</div>
          <div className="text-emerald-400 font-bold">{Math.round(statistics.avg_elevation)}m</div>
        </div>
        <div className="bg-slate-900/40 rounded px-2 py-1">
          <div className="text-slate-400">Max</div>
          <div className="text-white font-bold">{Math.round(maxElev)}m</div>
        </div>
      </div>

      {/* Elevation Chart */}
      <div className="bg-slate-900/60 rounded-lg p-2">
        <svg width={chartWidth} height={chartHeight} className="overflow-visible">
          {/* Grid lines */}
          {yTicks.map((tick, i) => {
            const y = padding.top + plotHeight - ((tick - minElev) / elevRange) * plotHeight
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={chartWidth - padding.right}
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
                  {Math.round(tick)}
                </text>
              </g>
            )
          })}

          {/* Filled area */}
          <path
            d={areaPath}
            fill="url(#elevGradient)"
            opacity="0.3"
          />

          {/* Elevation line */}
          <path
            d={pathData}
            fill="none"
            stroke="#10b981"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Center point marker */}
          {points.map((p, i) => {
            if (p.direction === 'Center') {
              return (
                <g key={i}>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="3"
                    fill="#10b981"
                    stroke="#0f172a"
                    strokeWidth="1.5"
                  />
                </g>
              )
            }
            return null
          })}

          {/* X-axis labels */}
          <text
            x={padding.left}
            y={chartHeight - 5}
            textAnchor="start"
            fill="#64748b"
            fontSize="9"
          >
            W
          </text>
          <text
            x={padding.left + plotWidth / 2}
            y={chartHeight - 5}
            textAnchor="middle"
            fill="#10b981"
            fontSize="9"
            fontWeight="600"
          >
            Center
          </text>
          <text
            x={chartWidth - padding.right}
            y={chartHeight - 5}
            textAnchor="end"
            fill="#64748b"
            fontSize="9"
          >
            E
          </text>

          {/* Gradient definition */}
          <defs>
            <linearGradient id="elevGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.1" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Terrain info */}
      <div className="mt-2 flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-1 text-slate-400">
          {statistics.elevation_range > 50 ? (
            <>
              <TrendingUp className="w-3 h-3 text-orange-400" />
              <span>Hilly terrain ({Math.round(statistics.elevation_range)}m range)</span>
            </>
          ) : statistics.elevation_range > 20 ? (
            <>
              <TrendingUp className="w-3 h-3 text-yellow-400" />
              <span>Moderate slope ({Math.round(statistics.elevation_range)}m range)</span>
            </>
          ) : (
            <>
              <TrendingDown className="w-3 h-3 text-green-400" />
              <span>Flat terrain ({Math.round(statistics.elevation_range)}m range)</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
