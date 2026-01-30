import { useState, useRef, useEffect } from 'react'
import { TrendingUp, MapPin, BarChart2, FileText, StickyNote, Zap, Building2, Layers, Ruler, MapPinned, Sparkles, Download, Star, Navigation, Wallet, AlertTriangle, CheckCircle, Eye, Compass, Brain, MessageCircle, Trophy, ArrowUpRight, ArrowDownRight, Scale, Database, Play, Bookmark, GitCompare } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import PropertyTypeScraper from './PropertyTypeScraper'
import ExplainabilityPanel from './ExplainabilityPanel'
import ElevationChart from './ElevationChart'
import AnalyticsMetrics from './AnalyticsMetrics'
import KPISummaryRow from './KPISummaryRow'
import PriceTimeSeriesChart from './PriceTimeSeriesChart'
import ExplainabilityShap from './ExplainabilityShap'
import ComparablesPanel from './ComparablesPanel'
import ScenarioSimulator from './ScenarioSimulator'
import DataQualityWidget from './DataQualityWidget'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// "Ask about this" button component
function AskAboutButton({ query, label }) {
  const handleClick = () => {
    window.dispatchEvent(new CustomEvent('valora-ask-question', { 
      detail: { query } 
    }))
  }
  
  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-2 py-1 rounded transition"
      title={`Ask: ${query}`}
    >
      <MessageCircle className="w-3 h-3" />
      {label || 'Ask about this'}
    </button>
  )
}

// Locality Card Component (moved from ChatPanel)
function LocalityCard({ locality, onExplore, onAskAbout }) {
  if (!locality || !locality.archetype) return null
  
  const archetypeColors = {
    'tech_hub': 'from-blue-500 to-cyan-500',
    'premium_residential': 'from-purple-500 to-pink-500',
    'family_residential': 'from-green-500 to-emerald-500',
    'commercial_district': 'from-orange-500 to-amber-500',
    'emerging': 'from-yellow-500 to-lime-500',
    'transit_oriented': 'from-indigo-500 to-blue-500',
  }
  
  const archetypeIcons = {
    'tech_hub': '💻',
    'premium_residential': '🏠',
    'family_residential': '👨‍👩‍👧',
    'commercial_district': '🏪',
    'emerging': '🚀',
    'transit_oriented': '🚇',
  }
  
  const bgColor = archetypeColors[locality.archetype] || 'from-slate-500 to-slate-600'
  const icon = archetypeIcons[locality.archetype] || '📍'
  
  const handleExplore = () => {
    window.dispatchEvent(new CustomEvent('valora-fly-to-locality', { 
      detail: { locality: locality.name } 
    }))
  }
  
  const handleAskAbout = () => {
    window.dispatchEvent(new CustomEvent('valora-ask-question', { 
      detail: { query: `Tell me more about ${locality.name} - investment potential, risk factors, and who should consider buying here.` } 
    }))
  }
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 overflow-hidden">
      <div className={`bg-gradient-to-r ${bgColor} px-3 py-2 flex items-center gap-2`}>
        <span className="text-lg">{icon}</span>
        <span className="text-white font-medium text-xs">{locality.name}</span>
        {locality.growth_stage && (
          <span className="ml-auto text-[10px] bg-white/20 px-2 py-0.5 rounded-full text-white">
            {locality.growth_stage.replace('_', ' ')}
          </span>
        )}
      </div>
      <div className="p-2">
        {locality.tagline && (
          <p className="text-[10px] text-slate-300 mb-1.5 italic">"{locality.tagline}"</p>
        )}
        <div className="grid grid-cols-2 gap-1.5 text-[10px] mb-2">
          {locality.personality?.tech_orientation !== undefined && (
            <div className="flex items-center gap-1">
              <span className="text-slate-400">Tech:</span>
              <span className="text-blue-400 font-medium">{locality.personality.tech_orientation}/100</span>
            </div>
          )}
          {locality.personality?.family_friendliness !== undefined && (
            <div className="flex items-center gap-1">
              <span className="text-slate-400">Family:</span>
              <span className="text-green-400 font-medium">{locality.personality.family_friendliness}/100</span>
            </div>
          )}
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={handleExplore}
            className="flex-1 text-[10px] bg-blue-600 hover:bg-blue-500 text-white px-2 py-1 rounded transition flex items-center justify-center gap-1"
          >
            <MapPin className="w-2.5 h-2.5" /> Explore
          </button>
          <button
            onClick={handleAskAbout}
            className="flex-1 text-[10px] bg-slate-700 hover:bg-slate-600 text-white px-2 py-1 rounded transition flex items-center justify-center gap-1"
          >
            <MessageCircle className="w-2.5 h-2.5" /> Ask
          </button>
        </div>
      </div>
    </div>
  )
}

// Property Comparison Card Component
function PropertyComparisonCard({ properties, onCompare }) {
  if (!properties || properties.length < 2) return null
  
  const [prop1, prop2] = properties.slice(0, 2)
  
  const compareValue = (v1, v2, higherIsBetter = true) => {
    if (v1 === v2) return 'tie'
    if (higherIsBetter) return v1 > v2 ? 'win' : 'lose'
    return v1 < v2 ? 'win' : 'lose'
  }
  
  const getColor = (result) => {
    if (result === 'win') return 'text-green-400'
    if (result === 'lose') return 'text-red-400'
    return 'text-slate-400'
  }
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-purple-500/30 overflow-hidden">
      <div className="bg-purple-600/20 px-3 py-2 flex items-center gap-2">
        <Scale className="w-3.5 h-3.5 text-purple-400" />
        <span className="text-purple-400 font-bold text-xs uppercase">Property Comparison</span>
      </div>
      <div className="p-2">
        <div className="grid grid-cols-3 gap-1 text-[10px] mb-2">
          <div className="font-medium text-slate-400">Metric</div>
          <div className="font-medium text-center truncate">{prop1.locality || 'Property 1'}</div>
          <div className="font-medium text-center truncate">{prop2.locality || 'Property 2'}</div>
        </div>
        
        {/* Price comparison */}
        <div className="grid grid-cols-3 gap-1 text-[10px] border-t border-slate-700/50 py-1">
          <div className="text-slate-400">Price</div>
          <div className={`text-center ${getColor(compareValue(prop2.price, prop1.price, false))}`}>
            ₹{(prop1.price / 100000).toFixed(1)}L
          </div>
          <div className={`text-center ${getColor(compareValue(prop1.price, prop2.price, false))}`}>
            ₹{(prop2.price / 100000).toFixed(1)}L
          </div>
        </div>
        
        {/* Area comparison */}
        <div className="grid grid-cols-3 gap-1 text-[10px] border-t border-slate-700/50 py-1">
          <div className="text-slate-400">Area</div>
          <div className={`text-center ${getColor(compareValue(prop1.area_sqft, prop2.area_sqft))}`}>
            {prop1.area_sqft} sqft
          </div>
          <div className={`text-center ${getColor(compareValue(prop2.area_sqft, prop1.area_sqft))}`}>
            {prop2.area_sqft} sqft
          </div>
        </div>
        
        {/* Price/sqft comparison */}
        <div className="grid grid-cols-3 gap-1 text-[10px] border-t border-slate-700/50 py-1">
          <div className="text-slate-400">₹/sqft</div>
          <div className={`text-center ${getColor(compareValue(prop2.price_per_sqft || 0, prop1.price_per_sqft || 0, false))}`}>
            ₹{Math.round(prop1.price_per_sqft || prop1.price / prop1.area_sqft)}
          </div>
          <div className={`text-center ${getColor(compareValue(prop1.price_per_sqft || 0, prop2.price_per_sqft || 0, false))}`}>
            ₹{Math.round(prop2.price_per_sqft || prop2.price / prop2.area_sqft)}
          </div>
        </div>
        
        <button
          onClick={() => onCompare?.(prop1, prop2)}
          className="w-full mt-2 text-[10px] bg-purple-600 hover:bg-purple-500 text-white px-2 py-1.5 rounded transition"
        >
          Detailed Comparison
        </button>
      </div>
    </div>
  )
}

// Investment Score Leaderboard Component
function InvestmentLeaderboard({ localities }) {
  if (!localities || localities.length === 0) return null
  
  // Sort by investment score
  const sorted = [...localities].sort((a, b) => (b.investment_score || 0) - (a.investment_score || 0)).slice(0, 5)
  
  const getMedalColor = (idx) => {
    if (idx === 0) return 'text-yellow-400'
    if (idx === 1) return 'text-slate-300'
    if (idx === 2) return 'text-amber-600'
    return 'text-slate-500'
  }
  
  const getTrendIcon = (trend) => {
    if (trend > 0) return <ArrowUpRight className="w-3 h-3 text-green-400" />
    if (trend < 0) return <ArrowDownRight className="w-3 h-3 text-red-400" />
    return null
  }
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-yellow-500/30 overflow-hidden">
      <div className="bg-yellow-600/20 px-3 py-2 flex items-center gap-2">
        <Trophy className="w-3.5 h-3.5 text-yellow-400" />
        <span className="text-yellow-400 font-bold text-xs uppercase">Investment Leaders</span>
      </div>
      <div className="p-2 space-y-1">
        {sorted.map((loc, idx) => (
          <button
            key={loc.name}
            onClick={() => {
              window.dispatchEvent(new CustomEvent('valora-fly-to-locality', { 
                detail: { locality: loc.name } 
              }))
            }}
            className="w-full flex items-center gap-2 p-1.5 rounded hover:bg-slate-700/50 transition text-left"
          >
            <span className={`font-bold text-sm ${getMedalColor(idx)}`}>#{idx + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="text-white text-[11px] font-medium truncate">{loc.name}</div>
              <div className="text-[9px] text-slate-400">{loc.archetype?.replace('_', ' ') || 'Area'}</div>
            </div>
            <div className="flex items-center gap-1">
              {getTrendIcon(loc.price_trend)}
              <span className="text-xs font-bold text-blue-400">{loc.investment_score || 75}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function AnalysisPanel({ agentData, setAgentData, activeTab, setActiveTab, fontSize = 100, liveAnalysis = null, isFullscreen = false }) {
  const [notes, setNotes] = useState([])
  const [currentNote, setCurrentNote] = useState({ title: '', content: '' })
  const [viewportAnalysis, setViewportAnalysis] = useState(null)
  const [viewportLoading, setViewportLoading] = useState(false)
  const [exportingPDF, setExportingPDF] = useState(false)
  const [exportingCSV, setExportingCSV] = useState(false)
  const [analysisSubTab, setAnalysisSubTab] = useState('overview') // overview, why, simulator, comps, data
  const [watchlist, setWatchlist] = useState([])
  const lastFetchedCenter = useRef(null)
  const analysisPanelRef = useRef(null)

  // Export analysis to CSV
  const exportToCSV = () => {
    setExportingCSV(true)
    try {
      const areaName = viewportAnalysis?.area_name || agentData?.explainability?.locality?.name || 'Analysis'
      const timestamp = new Date().toISOString().split('T')[0]
      
      // Build CSV data
      const rows = [
        ['Valora AI Analysis Report'],
        ['Area', areaName],
        ['Generated', new Date().toLocaleString()],
        [''],
        ['=== Market Overview ==='],
        ['Metric', 'Value'],
        ['Avg Price/sqft', `₹${viewportAnalysis?.market?.avg_price_per_sqft || agentData?.dashboard?.market?.avgPricePerSqft || 'N/A'}`],
        ['Price Trend', `${viewportAnalysis?.market?.price_trend_pct || agentData?.dashboard?.market?.growth1y || 'N/A'}%`],
        ['Demand Level', viewportAnalysis?.market?.demand_level || 'N/A'],
        ['Active Listings', viewportAnalysis?.market?.active_listings || viewportAnalysis?.properties?.count || 'N/A'],
        [''],
        ['=== Spatial Analysis ==='],
        ['POIs Nearby', viewportAnalysis?.spatial?.poi_count || 'N/A'],
        ['Transport Hubs', viewportAnalysis?.spatial?.transport_count || 'N/A'],
        ['Accessibility Score', `${viewportAnalysis?.spatial?.accessibility_score || 'N/A'}/100`],
        ['Walkability Score', `${viewportAnalysis?.spatial?.walkability_score || 'N/A'}/100`],
        [''],
        ['=== Terrain & Risk ==='],
        ['Elevation', `${viewportAnalysis?.terrain?.elevation_m || 'N/A'}m`],
        ['Flood Risk', viewportAnalysis?.terrain?.flood_risk || 'N/A'],
      ]
      
      // Add properties if available
      if (agentData?.properties?.length > 0) {
        rows.push([''], ['=== Properties ==='])
        rows.push(['Name', 'Price', 'Area', 'Type', 'Locality'])
        agentData.properties.slice(0, 20).forEach(p => {
          rows.push([
            p.title || p.name || 'Property',
            `₹${(p.price / 100000).toFixed(1)}L`,
            `${p.area_sqft || p.area} sqft`,
            p.property_type || p.type || 'N/A',
            p.locality || 'N/A'
          ])
        })
      }
      
      const csvContent = rows.map(row => row.join(',')).join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `valora-analysis-${areaName.replace(/\s+/g, '-').toLowerCase()}-${timestamp}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      console.log('📊 CSV exported successfully')
    } catch (err) {
      console.error('CSV export failed:', err)
    } finally {
      setExportingCSV(false)
    }
  }

  // Export analysis to PDF (HTML-based for proper formatting)
  const exportToPDF = async () => {
    setExportingPDF(true)
    try {
      const areaName = viewportAnalysis?.area_name || agentData?.explainability?.locality?.name || 'Valora Analysis'
      const timestamp = new Date().toLocaleString()
      
      // Build HTML report for better PDF quality
      const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valora AI Analysis - ${areaName}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #1e293b; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; }
    .header { text-align: center; border-bottom: 3px solid #7c3aed; padding-bottom: 20px; margin-bottom: 30px; }
    .header h1 { color: #7c3aed; font-size: 28px; margin-bottom: 5px; }
    .header .tagline { color: #64748b; font-style: italic; font-size: 14px; }
    .header .timestamp { color: #94a3b8; font-size: 12px; margin-top: 10px; }
    .section { margin-bottom: 25px; }
    .section-title { color: #7c3aed; font-size: 16px; font-weight: 600; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 15px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    .metric { background: #f8fafc; border-radius: 8px; padding: 15px; }
    .metric-label { color: #64748b; font-size: 12px; text-transform: uppercase; }
    .metric-value { color: #1e293b; font-size: 20px; font-weight: 600; margin-top: 5px; }
    .metric-unit { color: #94a3b8; font-size: 12px; }
    .driver { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
    .driver-name { color: #334155; }
    .driver-impact { color: #7c3aed; font-weight: 600; }
    .score-bar { height: 8px; background: #e2e8f0; border-radius: 4px; margin-top: 5px; overflow: hidden; }
    .score-fill { height: 100%; background: linear-gradient(90deg, #7c3aed, #a855f7); border-radius: 4px; }
    .footer { text-align: center; color: #94a3b8; font-size: 11px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; }
    @media print { body { padding: 20px; } .section { page-break-inside: avoid; } }
  </style>
</head>
<body>
  <div class="header">
    <h1>📊 VALORA AI ANALYSIS</h1>
    <div style="font-size: 22px; font-weight: 600; color: #1e293b; margin-top: 10px;">${areaName}</div>
    ${agentData?.explainability?.locality?.tagline ? `<div class="tagline">"${agentData.explainability.locality.tagline}"</div>` : ''}
    <div class="timestamp">Generated: ${timestamp}</div>
  </div>

  <div class="section">
    <div class="section-title">📈 Market Overview</div>
    <div class="grid">
      <div class="metric">
        <div class="metric-label">Avg Price/sqft</div>
        <div class="metric-value">₹${(viewportAnalysis?.market?.avg_price_per_sqft || agentData?.dashboard?.market?.avgPricePerSqft || 0).toLocaleString()}</div>
      </div>
      <div class="metric">
        <div class="metric-label">1Y Price Growth</div>
        <div class="metric-value">${viewportAnalysis?.market?.price_trend_pct || agentData?.dashboard?.market?.growth1y || '+5.2'}%</div>
      </div>
      <div class="metric">
        <div class="metric-label">Demand Level</div>
        <div class="metric-value">${viewportAnalysis?.market?.demand_level || agentData?.dashboard?.market?.demandIndex || 'High'}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Active Listings</div>
        <div class="metric-value">${viewportAnalysis?.market?.active_listings || viewportAnalysis?.properties?.count || 'N/A'}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🗺️ Spatial Analysis</div>
    <div class="grid">
      <div class="metric">
        <div class="metric-label">POIs Nearby (2km)</div>
        <div class="metric-value">${viewportAnalysis?.spatial?.poi_count || 'N/A'}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Transport Hubs</div>
        <div class="metric-value">${viewportAnalysis?.spatial?.transport_count || 'N/A'}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Accessibility Score</div>
        <div class="metric-value">${viewportAnalysis?.spatial?.accessibility_score || 75}/100</div>
        <div class="score-bar"><div class="score-fill" style="width: ${viewportAnalysis?.spatial?.accessibility_score || 75}%"></div></div>
      </div>
      <div class="metric">
        <div class="metric-label">Walkability Score</div>
        <div class="metric-value">${viewportAnalysis?.spatial?.walkability_score || 70}/100</div>
        <div class="score-bar"><div class="score-fill" style="width: ${viewportAnalysis?.spatial?.walkability_score || 70}%"></div></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🏔️ Terrain & Risk</div>
    <div class="grid">
      <div class="metric">
        <div class="metric-label">Elevation</div>
        <div class="metric-value">${typeof viewportAnalysis?.terrain?.elevation_m === 'number' ? viewportAnalysis.terrain.elevation_m.toFixed(0) : 'N/A'}<span class="metric-unit">m</span></div>
      </div>
      <div class="metric">
        <div class="metric-label">Flood Risk</div>
        <div class="metric-value">${viewportAnalysis?.terrain?.flood_risk || 'Low'}</div>
      </div>
    </div>
  </div>

  ${agentData?.explainability?.keyDrivers?.length > 0 ? `
  <div class="section">
    <div class="section-title">🔍 Key Value Drivers</div>
    ${agentData.explainability.keyDrivers.map(d => `
      <div class="driver">
        <span class="driver-name">${d.name}: ${d.value}</span>
        <span class="driver-impact">${d.impact > 0 ? '+' : ''}${(d.impact * 100).toFixed(0)}% impact</span>
      </div>
    `).join('')}
  </div>
  ` : ''}

  ${agentData?.simulation ? `
  <div class="section">
    <div class="section-title">🔮 Simulation Results</div>
    <p style="color: #64748b; margin-bottom: 15px;">${agentData.simulation.scenario?.description || 'What-if scenario analysis'}</p>
    <div class="grid">
      <div class="metric">
        <div class="metric-label">Accessibility Change</div>
        <div class="metric-value">${agentData.simulation.impacts?.accessibility_change || '+15'}%</div>
      </div>
      <div class="metric">
        <div class="metric-label">Property Value Impact</div>
        <div class="metric-value">${agentData.simulation.impacts?.property_value_impact || '+8'}%</div>
      </div>
    </div>
  </div>
  ` : ''}

  <div class="footer">
    <p>📍 Report generated by <strong>Valora AI</strong> - City Intelligence Platform for Bangalore</p>
    <p>This report is for informational purposes only. Investment decisions should be made with professional advice.</p>
  </div>
</body>
</html>`.trim()
      
      // Open HTML in new window for print/save as PDF
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(htmlContent)
        printWindow.document.close()
        printWindow.focus()
        setTimeout(() => printWindow.print(), 500)
      } else {
        // Fallback: download as HTML
        const blob = new Blob([htmlContent], { type: 'text/html' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `valora-analysis-${areaName.replace(/\s+/g, '-').toLowerCase()}.html`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
      
      console.log('📄 Analysis exported successfully')
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExportingPDF(false)
    }
  }

  // Cross-panel communication: Listen for events from Chat and Map panels
  useEffect(() => {
    // Handle AI agent commands to switch analysis tabs or trigger updates
    const handleAnalysisCommand = (event) => {
      const { action, tab, data } = event.detail || {}
      
      if (action === 'switchTab' && tab) {
        setAnalysisSubTab(tab)
      }
      if (action === 'refreshAnalysis') {
        lastFetchedCenter.current = null // Force refresh
      }
      if (action === 'showSimulation' && data) {
        setAnalysisSubTab('simulator')
      }
      if (action === 'showComps') {
        setAnalysisSubTab('comps')
      }
      if (action === 'showExplainability') {
        setAnalysisSubTab('why')
      }
    }
    
    // Handle requests to analyze a specific location
    const handleAnalyzeLocation = async (event) => {
      const { lat, lng, locality } = event.detail || {}
      if (lat && lng) {
        try {
          const resp = await fetch(`${API_URL}/api/viewport/analyze?lat=${lat}&lng=${lng}`)
          if (resp.ok) {
            const data = await resp.json()
            setViewportAnalysis(data)
            if (setAgentData) {
              setAgentData(prev => ({
                ...prev,
                viewportAnalysis: data,
                lastAnalysisUpdate: Date.now()
              }))
            }
          }
        } catch (err) {
          console.warn('Location analysis failed:', err)
        }
      }
    }
    
    window.addEventListener('valora-analysis-command', handleAnalysisCommand)
    window.addEventListener('valora-analyze-location', handleAnalyzeLocation)
    
    return () => {
      window.removeEventListener('valora-analysis-command', handleAnalysisCommand)
      window.removeEventListener('valora-analyze-location', handleAnalyzeLocation)
    }
  }, [setAgentData])

  // Auto-fetch viewport analysis when mapCenter changes
  useEffect(() => {
    const fetchViewportAnalysis = async () => {
      const center = agentData?.mapCenter
      if (!center?.lat || !center?.lng) return
      
      // Debounce: don't refetch if center hasn't moved significantly
      const lastCenter = lastFetchedCenter.current
      if (lastCenter) {
        const latDiff = Math.abs(center.lat - lastCenter.lat)
        const lngDiff = Math.abs(center.lng - lastCenter.lng)
        if (latDiff < 0.001 && lngDiff < 0.001) return // Less than ~100m movement
      }
      
      lastFetchedCenter.current = { lat: center.lat, lng: center.lng }
      setViewportLoading(true)
      
      try {
        const resp = await fetch(`${API_URL}/api/viewport/analyze?lat=${center.lat}&lng=${center.lng}`)
        if (resp.ok) {
          const data = await resp.json()
          setViewportAnalysis(data)
          
          // Store in agentData for cross-panel communication with ChatPanel
          if (setAgentData) {
            setAgentData(prev => ({
              ...prev,
              viewportAnalysis: data,
              lastAnalysisUpdate: Date.now()
            }))
          }
        }
      } catch (err) {
        console.warn('Viewport analysis fetch failed:', err)
      } finally {
        setViewportLoading(false)
      }
    }
    
    fetchViewportAnalysis()
    
    // Auto-refresh analysis every 30 seconds when map is active
    const refreshInterval = setInterval(() => {
      if (agentData?.mapCenter?.lat && agentData?.mapCenter?.lng) {
        fetchViewportAnalysis()
      }
    }, 30000)
    
    return () => clearInterval(refreshInterval)
  }, [agentData?.mapCenter?.lat, agentData?.mapCenter?.lng, setAgentData])

  const saveNote = () => {
    if (currentNote.title && currentNote.content) {
      setNotes(prev => [...prev, { ...currentNote, id: Date.now() }])
      setCurrentNote({ title: '', content: '' })
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ zoom: `${fontSize}%` }}>
      {/* Content */}
      <div className="flex-1 overflow-y-auto analysis-panel-scroll p-2">
        {activeTab === 'insights' && (
          <div className="space-y-2">

            {/* KPI Summary Row - Always visible at top */}
            <KPISummaryRow
              locality={viewportAnalysis?.area_name || agentData?.explainability?.locality?.name || 'Current Location'}
              medianPrice={viewportAnalysis?.market?.avg_price_per_sqft || agentData?.dashboard?.market?.avgPricePerSqft}
              priceChange3Y={viewportAnalysis?.market?.price_trend_pct ? viewportAnalysis.market.price_trend_pct * 3 : 15}
              momentum={viewportAnalysis?.investment?.growth_potential > 70 ? 'hot' : viewportAnalysis?.investment?.growth_potential > 50 ? 'warming' : 'neutral'}
              riskScore={viewportAnalysis?.livability?.safety_index ? 100 - viewportAnalysis.livability.safety_index : 35}
              confidence={viewportAnalysis?.comparison ? 78 : 72}
              confidenceDrivers={[
                { name: 'Property data', impact: 25 },
                { name: 'POI coverage', impact: 18 },
                { name: 'Price history', impact: -8 }
              ]}
              onFlyTo={() => {
                if (agentData?.mapCenter) {
                  window.dispatchEvent(new CustomEvent('valora-map-command', {
                    detail: { action: 'center', coordinates: [agentData.mapCenter.lat, agentData.mapCenter.lng], zoom: 15 }
                  }))
                }
              }}
            />

            {/* Sub-tab Navigation */}
            <div className="flex items-center gap-1 bg-slate-900/50 rounded-lg p-1">
              {[
                { id: 'overview', label: 'Overview', icon: Eye },
                { id: 'why', label: 'Why?', icon: Brain },
                { id: 'simulator', label: 'Simulator', icon: Zap },
                { id: 'comps', label: 'Comps', icon: Scale },
                { id: 'data', label: 'Data', icon: Database }
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setAnalysisSubTab(id)}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[10px] font-medium transition ${
                    analysisSubTab === id 
                      ? 'bg-blue-500 text-white' 
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  }`}
                >
                  <Icon className="w-3 h-3" />
                  {label}
                </button>
              ))}
            </div>

            {/* Overview Sub-tab */}
            {analysisSubTab === 'overview' && (
              <>
                {/* Price Time Series Chart */}
                <PriceTimeSeriesChart
                  locality={viewportAnalysis?.area_name}
                  lat={agentData?.mapCenter?.lat}
                  lng={agentData?.mapCenter?.lng}
                />

                {/* Elevation Chart */}
                {agentData?.mapCenter?.lat && agentData?.mapCenter?.lng && (
                  <ElevationChart 
                    lat={agentData.mapCenter.lat} 
                    lng={agentData.mapCenter.lng} 
                    radius={2.0}
                  />
                )}

                {/* Enhanced Analytics Metrics */}
                {viewportAnalysis && (
                  <AnalyticsMetrics 
                    viewportAnalysis={viewportAnalysis}
                    lat={agentData?.mapCenter?.lat}
                    lng={agentData?.mapCenter?.lng}
                    areaName={viewportAnalysis?.area_name}
                  />
                )}
              </>
            )}

            {/* Why? Sub-tab - SHAP Explainability */}
            {analysisSubTab === 'why' && (
              <ExplainabilityShap
                features={agentData?.explainability?.keyDrivers?.map(d => ({
                  name: d.name || d.factor,
                  impact: (d.impact || 0) * 100,
                  icon: MapPin
                }))}
                causalChain={agentData?.simulation ? {
                  trigger: agentData.simulation.scenario?.description || 'Infrastructure change',
                  effect: `${agentData.simulation.impacts?.property_value_impact > 0 ? '+' : ''}${agentData.simulation.impacts?.property_value_impact || 12}% price impact`,
                  timeframe: '1-3 years',
                  confidence: Math.round((agentData.simulation.impacts?.confidence || 0.75) * 100)
                } : null}
              />
            )}

            {/* Simulator Sub-tab */}
            {analysisSubTab === 'simulator' && (
              <ScenarioSimulator
                lat={agentData?.mapCenter?.lat}
                lng={agentData?.mapCenter?.lng}
                locality={viewportAnalysis?.area_name}
                onSimulationComplete={(result) => {
                  if (setAgentData) {
                    setAgentData(prev => ({
                      ...prev,
                      simulation: {
                        scenario: { description: 'What-if simulation' },
                        impacts: {
                          property_value_impact: result.price_impact,
                          confidence: result.confidence / 100
                        }
                      }
                    }))
                  }
                }}
              />
            )}

            {/* Comps Sub-tab */}
            {analysisSubTab === 'comps' && (
              <ComparablesPanel
                lat={agentData?.mapCenter?.lat}
                lng={agentData?.mapCenter?.lng}
                locality={viewportAnalysis?.area_name}
                radius={1500}
              />
            )}

            {/* Data Sub-tab */}
            {analysisSubTab === 'data' && (
              <>
                <DataQualityWidget
                  dataStats={{
                    properties: agentData?.buildingsCount || 12450,
                    pois: viewportAnalysis?.spatial?.poi_count ? viewportAnalysis.spatial.poi_count * 100 : 8920,
                    buildings: agentData?.buildingsCount || 156000,
                    overallQuality: 82,
                    spatialCoverage: 88,
                    temporalCoverage: 75,
                    attributeCompleteness: 79
                  }}
                  lastUpdated={new Date().toISOString()}
                />

                {/* Current View Analysis */}
                {(viewportAnalysis || viewportLoading) && (
                  <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-lg p-2">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-cyan-400 font-semibold text-xs flex items-center gap-2">
                        <Eye className="w-3 h-3" /> Raw Viewport Data
                      </h4>
                      {viewportLoading && (
                        <div className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
                      )}
                    </div>
                    <pre className="text-[9px] text-slate-400 bg-slate-900/50 rounded p-2 overflow-x-auto max-h-[200px]">
                      {JSON.stringify(viewportAnalysis, null, 2)}
                    </pre>
                  </div>
                )}
              </>
            )}

            {/* Legacy content for overview tab - Simulation Results */}
            {analysisSubTab === 'overview' && agentData?.simulation && (
              <div className="bg-orange-600/5 border border-orange-500/20 rounded-lg p-2.5 animate-in fade-in slide-in-from-bottom-2">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-orange-400" />
                    <span className="text-orange-400 font-bold text-xs uppercase tracking-tight">Active Simulation</span>
                  </div>
                  <span className="text-[9px] text-orange-500 font-black px-1.5 py-0.5 bg-orange-500/10 rounded uppercase tracking-widest">Live</span>
                </div>
                
                <p className="text-white text-[11px] font-bold leading-tight mb-2.5">{agentData.simulation.scenario?.description}</p>
                
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
                  <div className="flex items-center justify-between border-b border-orange-500/10 pb-1">
                    <span className="text-slate-400">Value Impact</span>
                    <span className={`font-black ${agentData.simulation.impacts?.property_value_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {agentData.simulation.impacts?.property_value_impact > 0 ? '+' : ''}{agentData.simulation.impacts?.property_value_impact}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-orange-500/10 pb-1">
                    <span className="text-slate-400">Confidence</span>
                    <span className="text-blue-400 font-black">{Math.round((agentData.simulation.impacts?.confidence || 0) * 100)}%</span>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={exportToPDF}
                disabled={exportingPDF}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-green-600 hover:bg-green-500 disabled:bg-slate-600 text-white text-[10px] font-medium rounded-lg transition"
              >
                {exportingPDF ? <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Download className="w-3 h-3" />}
                Report
              </button>
              <button
                onClick={exportToCSV}
                disabled={exportingCSV}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white text-[10px] font-medium rounded-lg transition"
              >
                {exportingCSV ? <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <FileText className="w-3 h-3" />}
                CSV
              </button>
              <button
                onClick={() => {
                  const item = {
                    id: Date.now(),
                    locality: viewportAnalysis?.area_name || 'Location',
                    lat: agentData?.mapCenter?.lat,
                    lng: agentData?.mapCenter?.lng,
                    price: viewportAnalysis?.market?.avg_price_per_sqft,
                    added: new Date().toISOString()
                  }
                  setWatchlist(prev => [...prev, item])
                }}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-[10px] font-medium rounded-lg transition"
              >
                <Bookmark className="w-3 h-3" />
                Watchlist
              </button>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('valora-ask-question', {
                    detail: { query: `Compare ${viewportAnalysis?.area_name || 'this area'} with a similar neighborhood` }
                  }))
                }}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-600 hover:bg-slate-500 text-white text-[10px] font-medium rounded-lg transition"
              >
                <GitCompare className="w-3 h-3" />
                Compare
              </button>
            </div>

            {/* Simulation Results Section - Professional & Dense */}
            {agentData?.simulation && (
              <div className="bg-orange-600/5 border border-orange-500/20 rounded-lg p-2.5 animate-in fade-in slide-in-from-bottom-2">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-orange-400" />
                    <span className="text-orange-400 font-bold text-xs uppercase tracking-tight">Urban Simulation</span>
                  </div>
                  <span className="text-[9px] text-orange-500 font-black px-1.5 py-0.5 bg-orange-500/10 rounded uppercase tracking-widest">Live</span>
                </div>
                
                <p className="text-white text-[11px] font-bold leading-tight mb-2.5">{agentData.simulation.scenario?.description}</p>
                
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
                  <div className="flex items-center justify-between border-b border-orange-500/10 pb-1">
                    <span className="text-slate-400">Accessibility</span>
                    <span className={`font-black ${agentData.simulation.impacts?.accessibility_change > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {agentData.simulation.impacts?.accessibility_change > 0 ? '+' : ''}{agentData.simulation.impacts?.accessibility_change}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-orange-500/10 pb-1">
                    <span className="text-slate-400">Value Impact</span>
                    <span className={`font-black ${agentData.simulation.impacts?.property_value_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {agentData.simulation.impacts?.property_value_impact > 0 ? '+' : ''}{agentData.simulation.impacts?.property_value_impact}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Dev Pressure</span>
                    <span className="text-orange-400 font-black">{agentData.simulation.impacts?.development_pressure}<span className="text-slate-600 font-normal text-[9px]">/100</span></span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Confidence</span>
                    <span className="text-blue-400 font-black">{Math.round(agentData.simulation.impacts?.confidence * 100)}%</span>
                  </div>
                </div>

                {agentData.simulation.impacts?.reasoning && (
                  <div className="mt-2.5 text-[10px] text-slate-400 leading-relaxed italic border-l-2 border-orange-500/20 pl-2">
                    {agentData.simulation.impacts.reasoning}
                  </div>
                )}
              </div>
            )}

            {/* Digital Twin State Section */}
            {agentData?.digitalTwinState && (
              <div className="bg-indigo-600/10 border border-indigo-500/30 rounded-lg p-2 space-y-1.5">
                <h4 className="text-indigo-400 font-semibold text-xs flex items-center gap-2">
                  <Layers className="w-3 h-3" /> Digital Twin State
                </h4>
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-400">Infrastructure (POIs)</span>
                    <span className="text-white font-medium">{agentData.digitalTwinState.infrastructure?.pois || 0}</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-400">Transport Hubs</span>
                    <span className="text-white font-medium">
                      {(agentData.digitalTwinState.transport?.metro_count || 0) + (agentData.digitalTwinState.transport?.bus_count || 0)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-400">Market Avg</span>
                    <span className="text-green-400 font-medium">₹{Math.round(agentData.digitalTwinState.economy?.avg_price_per_sqft || 0).toLocaleString()}/sqft</span>
                  </div>
                  <div className="mt-2 pt-2 border-t border-indigo-500/20">
                    <p className="text-[9px] text-slate-500 flex items-center gap-1">
                      <Zap className="w-2.5 h-2.5" /> Last sync: {new Date(agentData.digitalTwinState.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* AI Agent Reasoning Section */}
            {agentData?.dashboard?.ai_analysis && (
              <div className="bg-blue-600/10 border border-blue-500/30 rounded-lg p-2">
                <h4 className="text-blue-400 font-semibold text-xs mb-2 flex items-center gap-2">
                  <Sparkles className="w-3 h-3" /> Valora AI Analysis
                </h4>
                <div className="text-slate-200 text-xs leading-relaxed prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {agentData.dashboard.ai_analysis}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {/* Market Overview with Explainability - Dense & Professional */}
            {agentData?.dashboard?.market && (
              <div className="bg-slate-800/40 rounded-lg p-2.5 border border-blue-500/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <BarChart2 className="w-3.5 h-3.5 text-blue-400" />
                    <span className="text-blue-400 font-bold text-xs uppercase tracking-tight">Market Overview</span>
                  </div>
                  <AskAboutButton 
                    query="What's driving the market trends in this area? Is it a good time to invest?"
                    label="Why?"
                  />
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
                  <div className="flex items-center justify-between border-b border-slate-700/30 pb-1">
                    <span className="text-slate-400">Avg Price/sqft</span>
                    <span className="text-white font-bold">{agentData.dashboard.market.avgPricePerSqft || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-slate-700/30 pb-1">
                    <span className="text-slate-400">1Y Growth</span>
                    <span className="text-green-400 font-bold">{agentData.dashboard.market.growth1y || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Active Listings</span>
                    <span className="text-white font-bold">{agentData.dashboard.market.activeListings || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Demand Index</span>
                    <span className="text-blue-400 font-bold">{agentData.dashboard.market.demandIndex || '—'}</span>
                  </div>
                </div>

                {/* Integrated Explainability - Key Drivers */}
                {(liveAnalysis?.keyDrivers || agentData?.dashboard?.keyDrivers) && (
                  <div className="mt-2.5 pt-2.5 border-t border-slate-700/30">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Brain className="w-3 h-3 text-purple-400" />
                      <span className="text-purple-400 font-bold text-[10px] uppercase">Why These Numbers?</span>
                    </div>
                    <div className="space-y-1">
                      {(liveAnalysis?.keyDrivers || agentData?.dashboard?.keyDrivers || []).slice(0, 3).map((driver, idx) => (
                        <div key={idx} className="flex items-start gap-1.5 text-[10px]">
                          <span className="text-blue-400 font-bold mt-0.5">•</span>
                          <div className="flex-1">
                            <span className="text-slate-300 font-medium">{driver.factor || driver.name}</span>
                            {driver.impact && (
                              <span className="text-slate-500 ml-1">({driver.impact > 0 ? '+' : ''}{driver.impact}%)</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Current View Analysis - Shows info about where user is looking */}
            {(viewportAnalysis || viewportLoading) && !agentData?.selectedBuilding && (
              <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-lg p-2">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-cyan-400 font-semibold text-xs flex items-center gap-2">
                    <Eye className="w-3 h-3" /> Current View
                  </h4>
                  <div className="flex items-center gap-2">
                    {viewportAnalysis?.area_name && (
                      <AskAboutButton 
                        query={`Tell me about ${viewportAnalysis.area_name} - what's special about this area?`}
                        label="Explore"
                      />
                    )}
                    {viewportLoading && (
                      <div className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
                    )}
                  </div>
                </div>
                
                {viewportAnalysis?.area_name && (
                  <p className="text-white text-sm font-medium mb-2">{viewportAnalysis.area_name}</p>
                )}
                
                {viewportAnalysis?.spatial && (
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <div className="bg-slate-800/60 rounded p-2">
                      <p className="text-slate-400 text-[10px]">POIs (2km)</p>
                      <p className="text-white font-semibold text-sm">{viewportAnalysis.spatial.poi_count}</p>
                    </div>
                    <div className="bg-slate-800/60 rounded p-2">
                      <p className="text-slate-400 text-[10px]">Transport</p>
                      <p className="text-white font-semibold text-sm">{viewportAnalysis.spatial.transport_count}</p>
                    </div>
                    <div className="bg-slate-800/60 rounded p-2">
                      <p className="text-slate-400 text-[10px]">Accessibility</p>
                      <p className="text-white font-semibold text-sm">{viewportAnalysis.spatial.accessibility_score}/100</p>
                    </div>
                    <div className="bg-slate-800/60 rounded p-2">
                      <p className="text-slate-400 text-[10px]">Walkability</p>
                      <p className="text-white font-semibold text-sm">{viewportAnalysis.spatial.walkability_score}/100</p>
                    </div>
                  </div>
                )}
                
                {viewportAnalysis?.market && (
                  <div className="bg-slate-800/40 rounded p-2 mb-2">
                    <p className="text-slate-400 text-[10px] mb-1">Market Data</p>
                    <div className="flex items-center justify-between">
                      <span className="text-white text-xs">₹{viewportAnalysis.market.avg_price_per_sqft?.toLocaleString()}/sqft</span>
                      <span className={`text-xs font-medium ${
                        viewportAnalysis.market.demand_level === 'High' ? 'text-green-400' :
                        viewportAnalysis.market.demand_level === 'Medium' ? 'text-yellow-400' : 'text-slate-400'
                      }`}>{viewportAnalysis.market.demand_level} Demand</span>
                    </div>
                    {viewportAnalysis.market.price_trend_pct && (
                      <p className="text-green-400 text-[10px] mt-1">
                        {viewportAnalysis.market.price_trend_pct > 0 ? '+' : ''}{viewportAnalysis.market.price_trend_pct}% annual growth
                      </p>
                    )}
                  </div>
                )}
                
                {viewportAnalysis?.terrain && (
                  <div className="flex items-center gap-2 text-[10px]">
                    <Compass className="w-3 h-3 text-slate-400" />
                    <span className="text-slate-300">
                      Elevation: {
                        typeof viewportAnalysis.terrain.elevation_m === 'number' 
                          ? viewportAnalysis.terrain.elevation_m.toFixed(0)
                          : typeof viewportAnalysis.terrain.elevation_m === 'object' && viewportAnalysis.terrain.elevation_m?.mean
                            ? viewportAnalysis.terrain.elevation_m.mean.toFixed(0)
                            : 'N/A'
                      }m
                      {viewportAnalysis.terrain.flood_risk && viewportAnalysis.terrain.flood_risk !== 'unknown' && (
                        <span className={viewportAnalysis.terrain.flood_risk === 'low' ? 'text-green-400' : 'text-yellow-400'}>
                          {' '}• Flood risk: {viewportAnalysis.terrain.flood_risk}
                        </span>
                      )}
                    </span>
                  </div>
                )}
                
                <p className="text-slate-500 text-[10px] mt-2 italic">
                  Click a building for detailed analysis
                </p>
              </div>
            )}

            {/* Elevation Chart - Shows when analyzing any coordinate */}
            {agentData?.mapCenter?.lat && agentData?.mapCenter?.lng && (
              <ElevationChart 
                lat={agentData.mapCenter.lat} 
                lng={agentData.mapCenter.lng} 
                radius={2.0}
              />
            )}

            {/* Enhanced Analytics Metrics - Infrastructure, Livability, Investment, Comparison */}
            {viewportAnalysis && (
              <AnalyticsMetrics 
                viewportAnalysis={viewportAnalysis}
                lat={agentData?.mapCenter?.lat}
                lng={agentData?.mapCenter?.lng}
                areaName={viewportAnalysis?.area_name}
              />
            )}

            {/* Locality Card - Shows current area profile */}
            {agentData?.explainability?.locality?.archetype && (
              <LocalityCard locality={{
                name: agentData.explainability.locality.name || viewportAnalysis?.area_name || 'Current Area',
                archetype: agentData.explainability.locality.archetype,
                growth_stage: agentData.explainability.locality.growth_stage,
                tagline: agentData.explainability.locality.tagline,
                personality: agentData.explainability.locality.personality,
              }} />
            )}

            {/* Investment Score Leaderboard */}
            {agentData?.dashboard?.hotLocalities && agentData.dashboard.hotLocalities.length > 0 && (
              <InvestmentLeaderboard localities={agentData.dashboard.hotLocalities} />
            )}

            {/* Property Comparison Card */}
            {agentData?.comparisonProperties && agentData.comparisonProperties.length >= 2 && (
              <PropertyComparisonCard 
                properties={agentData.comparisonProperties}
                onCompare={(p1, p2) => {
                  window.dispatchEvent(new CustomEvent('valora-ask-question', { 
                    detail: { query: `Compare ${p1.locality || 'first property'} vs ${p2.locality || 'second property'} in detail - which is the better investment?` } 
                  }))
                }}
              />
            )}

            {/* Export & Map Stats Row */}
            <div className="flex items-center gap-2">
              {/* Export Buttons */}
              <div className="flex gap-1">
                <button
                  onClick={exportToPDF}
                  disabled={exportingPDF}
                  className="flex items-center gap-1 px-2 py-1.5 bg-green-600 hover:bg-green-500 disabled:bg-slate-600 text-white text-[10px] rounded transition"
                  title="Export as PDF"
                >
                  {exportingPDF ? (
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <Download className="w-3 h-3" />
                  )}
                  PDF
                </button>
                <button
                  onClick={exportToCSV}
                  disabled={exportingCSV}
                  className="flex items-center gap-1 px-2 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white text-[10px] rounded transition"
                  title="Export as CSV"
                >
                  {exportingCSV ? (
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <FileText className="w-3 h-3" />
                  )}
                  CSV
                </button>
              </div>
              
            </div>

            {agentData?.dashboard?.title && (
              <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/50">
                <h4 className="text-white font-semibold text-sm mb-2">{agentData.dashboard.title}</h4>
                {Array.isArray(agentData.dashboard.cards) && agentData.dashboard.cards.length > 0 && (
                  <div className="grid grid-cols-2 gap-2">
                    {agentData.dashboard.cards.map((c, idx) => (
                      <div key={idx} className="bg-slate-700/40 rounded p-2">
                        <p className="text-slate-400 text-[10px]">{c.label}</p>
                        <p className="text-white font-semibold text-sm">{c.value?.toLocaleString?.() ?? c.value}</p>
                      </div>
                    ))}
                  </div>
                )}

                {agentData.dashboard.area?.nearest_transit?.name && (
                  <div className="mt-2 bg-slate-700/30 rounded p-2">
                    <p className="text-slate-400 text-[10px]">Nearest Transit</p>
                    <p className="text-white text-xs font-medium">
                      {agentData.dashboard.area.nearest_transit.name}
                      {typeof agentData.dashboard.area.nearest_transit.distance_m === 'number' ? ` • ${agentData.dashboard.area.nearest_transit.distance_m}m` : ''}
                    </p>
                  </div>
                )}

                {Array.isArray(agentData.dashboard.area?.top_pois) && agentData.dashboard.area.top_pois.length > 0 && (
                  <div className="mt-2">
                    <p className="text-slate-400 text-[10px] mb-1">Top Nearby POIs</p>
                    <div className="space-y-1">
                      {agentData.dashboard.area.top_pois.slice(0, 5).map((p, idx) => (
                        <div key={idx} className="bg-slate-700/30 rounded px-2 py-1 flex items-center justify-between">
                          <span className="text-slate-200 text-xs truncate pr-2">{p.name || `${p.type || 'poi'} ${p.subtype || ''}`}</span>
                          {typeof p.distance_m === 'number' && (
                            <span className="text-slate-400 text-[10px]">{p.distance_m}m</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Location Analysis Loading State */}
            {agentData?.locationAnalysisLoading && (
              <div className="bg-gradient-to-r from-green-500/20 to-cyan-500/20 border border-green-500/40 rounded-lg p-2">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 border-2 border-green-400 border-t-transparent rounded-full animate-spin"></div>
                  <div>
                    <p className="text-white font-medium text-sm">Analyzing Location...</p>
                    <p className="text-slate-400 text-xs">Running micro-economics + valuation + property analysis</p>
                  </div>
                </div>
              </div>
            )}

            {/* Location Analysis Results (for any clicked coordinate) */}
            {agentData?.locationAnalysis && !agentData?.selectedBuilding && (
              <div className="bg-gradient-to-r from-green-500/10 to-cyan-500/10 border border-green-500/30 rounded-lg p-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <h4 className="text-green-400 font-semibold text-xs flex items-center gap-2">
                    <MapPin className="w-3 h-3" /> Location Analysis
                  </h4>
                  {agentData.locationAnalysis.investment_score && (
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      agentData.locationAnalysis.investment_score >= 70 ? 'bg-green-500/20 text-green-400' :
                      agentData.locationAnalysis.investment_score >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      Score: {agentData.locationAnalysis.investment_score}/100
                    </span>
                  )}
                </div>
                
                {agentData.locationAnalysis.area_name && (
                  <p className="text-white text-sm font-medium">{agentData.locationAnalysis.area_name}</p>
                )}

                {/* Micro-Economics Section */}
                {agentData.locationAnalysis.micro_economics && (
                  <div className="bg-slate-800/60 rounded p-2">
                    <p className="text-cyan-400 text-[10px] font-semibold mb-2 flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" /> Micro-Economics
                    </p>
                    <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                      <div className="bg-slate-700/50 rounded p-1.5">
                        <span className="text-slate-400">Rental Yield</span>
                        <p className="text-white font-semibold">{agentData.locationAnalysis.micro_economics.rental_yield_estimate}%</p>
                      </div>
                      <div className="bg-slate-700/50 rounded p-1.5">
                        <span className="text-slate-400">1Y Appreciation</span>
                        <p className={`font-semibold ${agentData.locationAnalysis.micro_economics.appreciation_forecast_1y > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {agentData.locationAnalysis.micro_economics.appreciation_forecast_1y > 0 ? '+' : ''}{agentData.locationAnalysis.micro_economics.appreciation_forecast_1y}%
                        </p>
                      </div>
                      <div className="bg-slate-700/50 rounded p-1.5">
                        <span className="text-slate-400">Liquidity</span>
                        <p className="text-white font-semibold">{agentData.locationAnalysis.micro_economics.liquidity_score}/100</p>
                      </div>
                      <div className="bg-slate-700/50 rounded p-1.5">
                        <span className="text-slate-400">Dev Potential</span>
                        <p className={`font-semibold ${
                          agentData.locationAnalysis.micro_economics.development_potential === 'High' ? 'text-green-400' :
                          agentData.locationAnalysis.micro_economics.development_potential === 'Medium' ? 'text-yellow-400' : 'text-slate-400'
                        }`}>{agentData.locationAnalysis.micro_economics.development_potential}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Market & Valuation */}
                {(agentData.locationAnalysis.market || agentData.locationAnalysis.valuation) && (
                  <div className="bg-slate-800/60 rounded p-2">
                    <p className="text-blue-400 text-[10px] font-semibold mb-2 flex items-center gap-1">
                      <Wallet className="w-3 h-3" /> Market & Valuation
                    </p>
                    <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                      {agentData.locationAnalysis.market?.avg_price_per_sqft && (
                        <div className="bg-slate-700/50 rounded p-1.5">
                          <span className="text-slate-400">Avg Price/sqft</span>
                          <p className="text-white font-semibold">₹{agentData.locationAnalysis.market.avg_price_per_sqft.toLocaleString()}</p>
                        </div>
                      )}
                      {agentData.locationAnalysis.market?.demand_level && (
                        <div className="bg-slate-700/50 rounded p-1.5">
                          <span className="text-slate-400">Demand</span>
                          <p className={`font-semibold ${
                            agentData.locationAnalysis.market.demand_level === 'High' ? 'text-green-400' :
                            agentData.locationAnalysis.market.demand_level === 'Medium' ? 'text-yellow-400' : 'text-slate-400'
                          }`}>{agentData.locationAnalysis.market.demand_level}</p>
                        </div>
                      )}
                      {agentData.locationAnalysis.valuation?.estimated_price_2bhk_1200sqft && (
                        <div className="bg-slate-700/50 rounded p-1.5 col-span-2">
                          <span className="text-slate-400">Est. 2BHK 1200sqft</span>
                          <p className="text-white font-semibold">₹{(agentData.locationAnalysis.valuation.estimated_price_2bhk_1200sqft / 100000).toFixed(1)}L</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Nearby Properties */}
                {agentData.locationAnalysis.nearby_properties?.length > 0 && (
                  <div className="bg-slate-800/60 rounded p-2">
                    <p className="text-purple-400 text-[10px] font-semibold mb-2 flex items-center gap-1">
                      <Building2 className="w-3 h-3" /> Nearby Properties ({agentData.locationAnalysis.nearby_properties.length})
                    </p>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {agentData.locationAnalysis.nearby_properties.slice(0, 5).map((prop, idx) => (
                        <div key={idx} className="bg-slate-700/40 rounded p-1.5 text-[10px]">
                          <div className="flex justify-between items-start">
                            <span className="text-white truncate flex-1">{prop.name}</span>
                            {prop.price && (
                              <span className="text-green-400 font-semibold ml-2">
                                ₹{prop.price < 10000000 ? `${(prop.price/100000).toFixed(0)}L` : `${(prop.price/10000000).toFixed(1)}Cr`}
                              </span>
                            )}
                          </div>
                          <div className="flex gap-2 text-slate-400 mt-0.5">
                            {prop.bedrooms && <span>{prop.bedrooms}BHK</span>}
                            {prop.area_sqft && <span>{prop.area_sqft}sqft</span>}
                            {prop.distance_m && <span>{prop.distance_m}m away</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendations */}
                {agentData.locationAnalysis.recommendations?.length > 0 && (
                  <div className="bg-slate-800/40 rounded p-2">
                    <p className="text-yellow-400 text-[10px] font-semibold mb-1">Recommendations</p>
                    <ul className="space-y-0.5">
                      {agentData.locationAnalysis.recommendations.map((rec, idx) => (
                        <li key={idx} className="text-slate-300 text-[10px] flex items-start gap-1">
                          <CheckCircle className="w-3 h-3 text-green-400 shrink-0 mt-0.5" />
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Building Analysis Loading State */}
            {agentData?.buildingAnalysisLoading && (
              <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/40 rounded-lg p-2">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                  <div>
                    <p className="text-white font-medium text-sm">Analyzing Building...</p>
                    <p className="text-slate-400 text-xs">Running AI + Spatial + Valuation analysis</p>
                  </div>
                </div>
              </div>
            )}

            {/* Rich Building Analysis */}
            {agentData?.buildingAnalysis && (
              <div className="space-y-1.5">
                <div className="bg-slate-800/40 rounded-lg p-2 border border-cyan-500/30">
                <div className="flex items-center justify-between mb-1.5">
                  <h4 className="text-cyan-400 font-bold text-[11px] flex items-center gap-1.5 uppercase tracking-tight">
                    <Building2 className="w-3.5 h-3.5" /> Rich Building Analysis
                  </h4>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => {
                        const building = agentData.buildingAnalysis?.building
                        if (building?.lat && building?.lng) {
                          window.dispatchEvent(new CustomEvent('valora-map-command', {
                            detail: {
                              action: 'center',
                              coordinates: [building.lat, building.lng],
                              zoom: 19
                            }
                          }))
                        }
                      }}
                      className="px-1.5 py-0.5 bg-cyan-500/20 hover:bg-cyan-500/40 border border-cyan-500/50 rounded text-cyan-400 text-[9px] font-medium flex items-center gap-1 transition"
                      title="Center map on this building"
                    >
                      <Navigation className="w-2.5 h-2.5" />
                    </button>
                    <button
                      onClick={() => {
                        const analysis = agentData.buildingAnalysis
                        const content = `
VALORA AI - BUILDING ANALYSIS REPORT
=====================================
Generated: ${new Date().toLocaleString()}

BUILDING DETAILS
----------------
Location: ${analysis.building?.lat?.toFixed(5)}, ${analysis.building?.lng?.toFixed(5)}
Height: ${analysis.building?.height || 'N/A'}m
Floors: ${analysis.building?.levels || 'N/A'}
Type: ${analysis.building?.type || 'N/A'}
Area: ${analysis.building?.area || 'N/A'}m²

AREA IMPORTANCE
---------------
Score: ${analysis.area_importance?.score || 'N/A'}/100 (Grade: ${analysis.area_importance?.grade || 'N/A'})
Accessibility: ${analysis.area_importance?.factors?.accessibility || 'N/A'}/100
Walkability: ${analysis.area_importance?.factors?.walkability || 'N/A'}/100

VALUATION
---------
Estimated Price: ₹${analysis.valuation?.estimated_price?.toLocaleString() || 'N/A'}
Price/sqft: ₹${analysis.valuation?.price_per_sqft?.toLocaleString() || 'N/A'}
Confidence: ${((analysis.valuation?.confidence || 0) * 100).toFixed(0)}%
Range: ₹${analysis.valuation?.price_range?.low?.toLocaleString() || 'N/A'} - ₹${analysis.valuation?.price_range?.high?.toLocaleString() || 'N/A'}

MARKET STATS
------------
Avg Price: ₹${analysis.market?.avg_price?.toLocaleString() || 'N/A'}
1Y Growth: ${analysis.market?.growth_1y || 'N/A'}%
Demand: ${analysis.market?.demand_index || 'N/A'}

AI ANALYSIS
-----------
${analysis.ai_analysis || 'No AI analysis available'}

---
Report generated by Valora AI - City Intelligence Platform
                        `.trim()
                        
                        const blob = new Blob([content], { type: 'text/plain' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `valora-building-analysis-${Date.now()}.txt`
                        a.click()
                        URL.revokeObjectURL(url)
                      }}
                      className="px-1.5 py-0.5 bg-blue-500/20 hover:bg-blue-500/40 border border-blue-500/50 rounded text-blue-400 text-[9px] font-medium flex items-center gap-1 transition"
                      title="Export analysis report"
                    >
                      <Download className="w-2.5 h-2.5" /> Export
                    </button>
                  </div>
                </div>
                  
                  {/* Building Name */}
                  {agentData.buildingAnalysis.building?.name && (
                    <div className="text-white font-semibold text-sm mb-1">
                      {agentData.buildingAnalysis.building.name}
                    </div>
                  )}
                  
                  {/* Building Address/Location */}
                  {(agentData.buildingAnalysis.building?.address || agentData.buildingAnalysis.building?.locality) && (
                    <div className="text-slate-400 text-[10px] mb-1.5 flex items-center gap-1">
                      <span>📍</span>
                      <span>{agentData.buildingAnalysis.building?.address || agentData.buildingAnalysis.building?.locality}</span>
                    </div>
                  )}
                  
                  {/* Building Info - Single Dense Row */}
                  <div className="flex items-center gap-2 text-[10px] flex-wrap">
                    <div className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-700/30 rounded">
                      <span className="text-slate-500">H:</span>
                      <span className="text-white font-bold">{agentData.buildingAnalysis.building?.height || '?'}m</span>
                    </div>
                    <div className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-700/30 rounded">
                      <span className="text-slate-500">F:</span>
                      <span className="text-white font-bold">{agentData.buildingAnalysis.building?.levels || '?'}</span>
                    </div>
                    <div className="flex items-center gap-1 px-1.5 py-0.5 bg-cyan-500/10 rounded">
                      <span className="text-cyan-400 font-bold capitalize">{agentData.buildingAnalysis.building?.type || '?'}</span>
                    </div>
                    <div className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-700/30 rounded">
                      <span className="text-slate-500">A:</span>
                      <span className="text-white font-bold">{agentData.buildingAnalysis.building?.area || '?'}m²</span>
                    </div>
                  </div>
                </div>

                {/* Area Importance - Ultra Compact with Mini Charts */}
                {agentData.buildingAnalysis.area_importance && (
                  <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <Star className="w-3 h-3 text-yellow-400" />
                        <span className="text-white font-bold text-[10px]">Area Importance</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-black ${
                          agentData.buildingAnalysis.area_importance.grade === 'A+' ? 'bg-green-500/20 text-green-400' :
                          agentData.buildingAnalysis.area_importance.grade === 'A' ? 'bg-blue-500/20 text-blue-400' :
                          agentData.buildingAnalysis.area_importance.grade === 'B+' ? 'bg-cyan-500/20 text-cyan-400' :
                          'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {agentData.buildingAnalysis.area_importance.grade}
                        </span>
                      </div>
                      <span className="text-white font-black text-sm">{agentData.buildingAnalysis.area_importance.score}<span className="text-slate-500 text-[9px] font-normal">/100</span></span>
                    </div>
                    {/* Score Bar with Gradient */}
                    <div className="h-1 bg-slate-700/50 rounded-full overflow-hidden mb-2">
                      <div className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-green-400 rounded-full" style={{ width: `${agentData.buildingAnalysis.area_importance.score}%` }} />
                    </div>
                    {/* Factors as Mini Bar Charts - Single Row */}
                    <div className="flex items-center gap-3 text-[9px]">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-slate-500">Access</span>
                          <span className="text-white font-bold">{agentData.buildingAnalysis.area_importance.factors?.accessibility || 0}</span>
                        </div>
                        <div className="h-1 bg-slate-700/50 rounded-full overflow-hidden">
                          <div className="h-full bg-green-500 rounded-full" style={{ width: `${agentData.buildingAnalysis.area_importance.factors?.accessibility || 0}%` }} />
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-slate-500">Walk</span>
                          <span className="text-white font-bold">{agentData.buildingAnalysis.area_importance.factors?.walkability || 0}</span>
                        </div>
                        <div className="h-1 bg-slate-700/50 rounded-full overflow-hidden">
                          <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${agentData.buildingAnalysis.area_importance.factors?.walkability || 0}%` }} />
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-slate-500">Amenity</span>
                          <span className="text-white font-bold">{Math.min(100, Math.round((agentData.buildingAnalysis.area_importance.factors?.amenity_density || 0) / 2))}</span>
                        </div>
                        <div className="h-1 bg-slate-700/50 rounded-full overflow-hidden">
                          <div className="h-full bg-purple-500 rounded-full" style={{ width: `${Math.min(100, (agentData.buildingAnalysis.area_importance.factors?.amenity_density || 0) / 2)}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Valuation - Compact with Range Visualization */}
                {agentData.buildingAnalysis.valuation && (
                  <div className="bg-slate-800/40 rounded-lg p-2 border border-green-500/30">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <Wallet className="w-3 h-3 text-green-400" />
                        <span className="text-green-400 font-bold text-[10px] uppercase">Valuation</span>
                        <span className="text-slate-500 text-[8px] flex items-center gap-0.5">
                          <CheckCircle className="w-2 h-2" />{(agentData.buildingAnalysis.valuation.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <span className="text-green-400 font-black text-xl">₹{(agentData.buildingAnalysis.valuation.estimated_price / 100000).toFixed(1)}L</span>
                    </div>
                    {/* Price Range Visual Bar */}
                    <div className="relative h-4 bg-slate-700/30 rounded-full overflow-hidden mb-1">
                      <div className="absolute inset-y-0 bg-gradient-to-r from-slate-600 via-green-500/50 to-slate-600 rounded-full" 
                        style={{ 
                          left: '10%', 
                          right: '10%'
                        }} 
                      />
                      <div className="absolute inset-y-0 w-0.5 bg-green-400" style={{ left: '50%' }} />
                      <div className="absolute inset-0 flex items-center justify-between px-2 text-[8px]">
                        <span className="text-slate-400 font-medium">₹{(agentData.buildingAnalysis.valuation.price_range?.low / 100000).toFixed(0)}L</span>
                        <span className="text-slate-400 font-medium">₹{(agentData.buildingAnalysis.valuation.price_range?.high / 100000).toFixed(0)}L</span>
                      </div>
                    </div>
                    <div className="text-center text-slate-500 text-[9px]">
                      ₹{agentData.buildingAnalysis.valuation.price_per_sqft?.toLocaleString()}/sqft
                    </div>
                  </div>
                )}

                {/* Market Stats - Single Row with Spark Chart */}
                {agentData.buildingAnalysis.market && (
                  <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <TrendingUp className="w-3 h-3 text-blue-400" />
                        <span className="text-blue-400 font-bold text-[10px] uppercase">Market (2km)</span>
                      </div>
                      {/* Mini Spark Line Chart */}
                      <svg width="50" height="16" className="text-green-400">
                        <polyline
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          points="0,14 8,12 16,10 24,8 32,6 40,4 50,2"
                        />
                      </svg>
                    </div>
                    <div className="flex items-center gap-2 text-[9px]">
                      <div className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-700/30 rounded">
                        <span className="text-slate-500">₹</span>
                        <span className="text-white font-bold">{agentData.buildingAnalysis.market.avg_price_per_sqft?.toLocaleString()}</span>
                        <span className="text-slate-500">/sqft</span>
                      </div>
                      <div className="flex items-center gap-1 px-1.5 py-0.5 bg-green-500/10 rounded">
                        <span className="text-green-400 font-black">+{agentData.buildingAnalysis.market.growth_1y}%</span>
                      </div>
                      <div className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-700/30 rounded">
                        <span className="text-white font-bold">{agentData.buildingAnalysis.market.total_properties}</span>
                        <span className="text-slate-500">props</span>
                      </div>
                      <div className={`px-1.5 py-0.5 rounded font-black text-[8px] uppercase ${
                        agentData.buildingAnalysis.market.demand_index === 'High' ? 'bg-green-500/20 text-green-400' :
                        agentData.buildingAnalysis.market.demand_index === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {agentData.buildingAnalysis.market.demand_index}
                      </div>
                    </div>
                  </div>
                )}

                {/* AI Analysis - Professional Section */}
                {agentData.buildingAnalysis.ai_analysis && (
                  <div className="bg-purple-600/5 border border-purple-500/20 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                      <span className="text-purple-400 font-bold text-xs uppercase tracking-tight">AI Investment Analysis</span>
                    </div>
                    <div className="text-slate-300 text-[11px] leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:text-xs prose-headings:my-1">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {agentData.buildingAnalysis.ai_analysis}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Highlights - Tighter list */}
                {agentData.buildingAnalysis.recommendations?.length > 0 && (
                  <div className="bg-slate-800/40 rounded-lg p-2.5 border border-slate-700/50">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-white font-bold text-xs uppercase tracking-tight">Key Highlights</span>
                    </div>
                    <div className="space-y-1.5">
                      {agentData.buildingAnalysis.recommendations.map((rec, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-[11px] text-slate-300 leading-tight">
                          <div className="w-1 h-1 bg-green-500 rounded-full mt-1.5 shrink-0"></div>
                          {rec}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Fallback: Selected Building (no analysis yet) */}
            {agentData?.selectedBuilding && !agentData?.buildingAnalysis && !agentData?.buildingAnalysisLoading && (
              <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/40 rounded-lg p-2">
                <h4 className="text-white font-semibold text-sm mb-3 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-blue-400" />
                  🏢 Building Selected
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-[10px] flex items-center gap-1">
                      <Ruler className="w-3 h-3" /> Height
                    </p>
                    <p className="text-white font-semibold text-sm">{agentData.selectedBuilding.height}m</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-[10px] flex items-center gap-1">
                      <Layers className="w-3 h-3" /> Floors
                    </p>
                    <p className="text-white font-semibold text-sm">{agentData.selectedBuilding.levels}</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-[10px]">Type</p>
                    <p className="text-cyan-400 font-medium text-xs capitalize">{agentData.selectedBuilding.buildingType}</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-[10px]">Area</p>
                    <p className="text-white font-medium text-xs">{agentData.selectedBuilding.area > 0 ? `~${agentData.selectedBuilding.area}m²` : 'N/A'}</p>
                  </div>
                </div>
                {agentData.selectedBuilding.coordinates?.lat && (
                  <div className="mt-2 bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-[10px] flex items-center gap-1">
                      <MapPinned className="w-3 h-3" /> Location
                    </p>
                    <p className="text-slate-300 text-[10px]">
                      {agentData.selectedBuilding.coordinates.lat?.toFixed(5)}, {agentData.selectedBuilding.coordinates.lng?.toFixed(5)}
                    </p>
                  </div>
                )}
                <p className="text-slate-400 text-[10px] mt-2 italic">
                  💡 Ask AI: "Tell me about this building" or "What's the investment potential?"
                </p>
              </div>
            )}

            {/* Selected Location (when no building) */}
            {agentData?.selectedLocation && !agentData?.selectedBuilding && (
              <div className="bg-slate-700/30 rounded-lg p-2">
                <h4 className="text-white font-medium text-xs mb-2 flex items-center gap-2">
                  <MapPin className="w-3 h-3 text-blue-400" />
                  Selected Location
                </h4>
                <div className="text-xs text-slate-300">
                  <p>Lat: {agentData.selectedLocation.lat?.toFixed(5)}</p>
                  <p>Lng: {agentData.selectedLocation.lng?.toFixed(5)}</p>
                </div>
              </div>
            )}

            {/* Hot Localities */}
            <div className="bg-slate-700/30 rounded-lg p-2">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-white font-medium text-xs flex items-center gap-2">
                  <Zap className="w-3 h-3 text-yellow-400" />
                  Hot Localities
                </h4>
              </div>
              <div className="space-y-1">
                {(agentData?.dashboard?.hotLocalities || []).map((loc, i) => (
                  <button
                    key={i}
                    onClick={() => setAgentData(prev => ({ ...prev, flyTo: { lat: loc.lat, lng: loc.lng, zoom: 15 } }))}
                    className="w-full flex items-center justify-between py-1.5 px-2 hover:bg-slate-600/30 transition rounded"
                  >
                    <span className="text-white text-xs flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-blue-400" />
                      {loc.name}
                    </span>
                    <div className="flex items-center gap-2">
                      {typeof loc.growth === 'number' && (
                        <span className="text-green-400 text-[10px]">+{loc.growth}%</span>
                      )}
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                        loc.grade === 'A+' ? 'bg-green-500/20 text-green-400' :
                        loc.grade === 'A' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>{loc.grade}</span>
                    </div>
                  </button>
                ))}

                {(!agentData?.dashboard?.hotLocalities || agentData.dashboard.hotLocalities.length === 0) && (
                  <p className="text-slate-400 text-xs">Ask Valora AI for a locality comparison to populate this.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'data' && (
          <div className="space-y-2">
            <PropertyTypeScraper />
          </div>
        )}

        {activeTab === 'docs' && (
          <div className="space-y-2">
            <h3 className="text-white font-semibold text-sm">Documents</h3>
            <p className="text-slate-400 text-xs">Upload documents for analysis</p>
            <label className="cursor-pointer px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-xs flex items-center gap-1 w-fit">
              <FileText className="w-3 h-3" /> Upload
              <input type="file" className="hidden" multiple accept=".pdf,.doc,.docx,.jpg,.png" />
            </label>
          </div>
        )}


        {activeTab === 'notes' && (
          <div className="space-y-2">
            <h3 className="text-white font-semibold text-sm">Notes</h3>
            <input
              type="text"
              placeholder="Title..."
              value={currentNote.title}
              onChange={(e) => setCurrentNote(prev => ({ ...prev, title: e.target.value }))}
              className="w-full px-2 py-1.5 bg-slate-700/50 border border-slate-600 rounded text-white placeholder-slate-400 text-xs"
            />
            <textarea
              placeholder="Write note..."
              value={currentNote.content}
              onChange={(e) => setCurrentNote(prev => ({ ...prev, content: e.target.value }))}
              rows={3}
              className="w-full px-2 py-1.5 bg-slate-700/50 border border-slate-600 rounded text-white placeholder-slate-400 text-xs resize-none"
            />
            <button 
              onClick={saveNote}
              className="w-full py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition text-xs"
            >
              Save Note
            </button>
            {notes.length > 0 && (
              <div className="space-y-2 mt-4">
                <p className="text-slate-400 text-xs">Saved Notes</p>
                {notes.map(note => (
                  <div key={note.id} className="bg-slate-700/50 rounded p-2">
                    <p className="text-white text-xs font-medium">{note.title}</p>
                    <p className="text-slate-400 text-xs mt-1">{note.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
