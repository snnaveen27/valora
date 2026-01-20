import { useState, useRef } from 'react'
import { TrendingUp, MapPin, BarChart2, FileText, StickyNote, Zap, Building2, Layers, Ruler, MapPinned, Sparkles, Download, Star, Navigation, Wallet, AlertTriangle, CheckCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function AnalysisPanel({ agentData, setAgentData, activeTab, setActiveTab }) {
  const [notes, setNotes] = useState([])
  const [currentNote, setCurrentNote] = useState({ title: '', content: '' })

  const saveNote = () => {
    if (currentNote.title && currentNote.content) {
      setNotes(prev => [...prev, { ...currentNote, id: Date.now() }])
      setCurrentNote({ title: '', content: '' })
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="p-2 border-b border-slate-700 flex gap-1 overflow-x-auto shrink-0">
        {['insights', 'docs', 'notes'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-2 py-1 rounded text-xs font-medium transition whitespace-nowrap flex items-center gap-1 ${
              activeTab === tab ? 'bg-blue-500 text-white' : 'text-slate-400 hover:bg-slate-700'
            }`}
          >
            {tab === 'insights' && <TrendingUp className="w-3 h-3" />}
            {tab === 'docs' && <FileText className="w-3 h-3" />}
            {tab === 'notes' && <StickyNote className="w-3 h-3" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'insights' && (
          <div className="space-y-3">
            <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-3">
              <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                City Insights
              </h3>
              <p className="text-slate-400 text-xs mt-1">Combined analysis and market intelligence</p>
            </div>

            {/* AI Agent Reasoning Section */}
            {agentData?.dashboard?.ai_analysis && (
              <div className="bg-blue-600/10 border border-blue-500/30 rounded-lg p-3">
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

            {/* Market Overview Section (Formerly Market Tab) */}
            {agentData?.dashboard?.market && (
              <div className="bg-slate-800/60 rounded-lg p-3 border border-blue-500/20">
                <h4 className="text-blue-400 font-semibold text-xs mb-2 flex items-center gap-2">
                  <BarChart2 className="w-3 h-3" /> Market Overview
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-700/50 rounded p-2">
                    <p className="text-slate-400 text-[10px]">Avg Price/sqft</p>
                    <p className="text-white font-semibold text-sm">{agentData.dashboard.market.avgPricePerSqft || '—'}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2">
                    <p className="text-slate-400 text-[10px]">1Y Growth</p>
                    <p className="text-green-400 font-semibold text-sm">{agentData.dashboard.market.growth1y || '—'}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2">
                    <p className="text-slate-400 text-[10px]">Active Listings</p>
                    <p className="text-white font-semibold text-sm">{agentData.dashboard.market.activeListings || '—'}</p>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2">
                    <p className="text-slate-400 text-[10px]">Demand Index</p>
                    <p className="text-blue-400 font-semibold text-sm">{agentData.dashboard.market.demandIndex || '—'}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Map Stats */}
            <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/50">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-xs">Loaded Buildings</span>
                {agentData?.loadingBuildings && (
                  <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                )}
              </div>
              <p className="text-white font-bold text-lg mt-1">
                {agentData?.buildingsCount ? agentData.buildingsCount.toLocaleString() : '0'}
              </p>
              {agentData?.loadingBuildings && (
                <p className="text-blue-400 text-xs mt-1">🔍 Analysing area...</p>
              )}
            </div>

            {agentData?.dashboard?.title && (
              <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
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

            {/* Building Analysis Loading State */}
            {agentData?.buildingAnalysisLoading && (
              <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/40 rounded-lg p-4">
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
            {agentData?.buildingAnalysis && !agentData?.buildingAnalysisLoading && (
              <div className="space-y-3">
                {/* Header with PDF Download */}
                <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/40 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-white font-semibold text-sm flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-blue-400" />
                      Building Analysis
                    </h4>
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
                      className="px-2 py-1 bg-blue-500/20 hover:bg-blue-500/40 border border-blue-500/50 rounded text-blue-400 text-[10px] font-medium flex items-center gap-1 transition"
                    >
                      <Download className="w-3 h-3" /> Export
                    </button>
                  </div>
                  
                  {/* Building Basic Info */}
                  <div className="grid grid-cols-4 gap-1.5 text-center">
                    <div className="bg-slate-800/60 rounded p-1.5">
                      <p className="text-slate-400 text-[9px]">Height</p>
                      <p className="text-white font-semibold text-xs">{agentData.buildingAnalysis.building?.height || '?'}m</p>
                    </div>
                    <div className="bg-slate-800/60 rounded p-1.5">
                      <p className="text-slate-400 text-[9px]">Floors</p>
                      <p className="text-white font-semibold text-xs">{agentData.buildingAnalysis.building?.levels || '?'}</p>
                    </div>
                    <div className="bg-slate-800/60 rounded p-1.5">
                      <p className="text-slate-400 text-[9px]">Type</p>
                      <p className="text-cyan-400 font-medium text-[10px] capitalize truncate">{agentData.buildingAnalysis.building?.type || '?'}</p>
                    </div>
                    <div className="bg-slate-800/60 rounded p-1.5">
                      <p className="text-slate-400 text-[9px]">Area</p>
                      <p className="text-white font-medium text-[10px]">{agentData.buildingAnalysis.building?.area ? `${agentData.buildingAnalysis.building.area}m²` : '?'}</p>
                    </div>
                  </div>
                </div>

                {/* Area Importance Score */}
                {agentData.buildingAnalysis.area_importance && (
                  <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="text-white font-medium text-xs flex items-center gap-1.5">
                        <Star className="w-3 h-3 text-yellow-400" /> Area Importance
                      </h5>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        agentData.buildingAnalysis.area_importance.grade === 'A+' ? 'bg-green-500/30 text-green-400' :
                        agentData.buildingAnalysis.area_importance.grade === 'A' ? 'bg-blue-500/30 text-blue-400' :
                        agentData.buildingAnalysis.area_importance.grade === 'B+' ? 'bg-cyan-500/30 text-cyan-400' :
                        'bg-yellow-500/30 text-yellow-400'
                      }`}>
                        {agentData.buildingAnalysis.area_importance.grade}
                      </span>
                    </div>
                    <div className="mb-2">
                      <div className="flex justify-between text-[10px] mb-1">
                        <span className="text-slate-400">Overall Score</span>
                        <span className="text-white font-medium">{agentData.buildingAnalysis.area_importance.score}/100</span>
                      </div>
                      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-blue-500 to-green-400 rounded-full transition-all"
                          style={{ width: `${agentData.buildingAnalysis.area_importance.score}%` }}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <p className="text-slate-400 text-[9px]">Accessibility</p>
                        <p className="text-white font-semibold text-xs">{agentData.buildingAnalysis.area_importance.factors?.accessibility || 0}/100</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-[9px]">Walkability</p>
                        <p className="text-white font-semibold text-xs">{agentData.buildingAnalysis.area_importance.factors?.walkability || 0}/100</p>
                      </div>
                      <div>
                        <p className="text-slate-400 text-[9px]">Amenity Density</p>
                        <p className="text-white font-semibold text-xs">{agentData.buildingAnalysis.area_importance.factors?.amenity_density || 0}/km²</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Valuation */}
                {agentData.buildingAnalysis.valuation && (
                  <div className="bg-slate-800/40 rounded-lg p-3 border border-green-500/30">
                    <h5 className="text-green-400 font-medium text-xs flex items-center gap-1.5 mb-2">
                      <Wallet className="w-3 h-3" /> Valuation Estimate
                    </h5>
                    <div className="text-center mb-2">
                      <p className="text-green-400 font-bold text-xl">
                        ₹{(agentData.buildingAnalysis.valuation.estimated_price / 100000).toFixed(1)}L
                      </p>
                      <p className="text-slate-400 text-[10px]">
                        ₹{agentData.buildingAnalysis.valuation.price_per_sqft?.toLocaleString()}/sqft • {(agentData.buildingAnalysis.valuation.confidence * 100).toFixed(0)}% confidence
                      </p>
                    </div>
                    <div className="bg-slate-700/40 rounded p-2">
                      <p className="text-slate-400 text-[9px] mb-1">Price Range</p>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-300">₹{(agentData.buildingAnalysis.valuation.price_range?.low / 100000).toFixed(1)}L</span>
                        <span className="text-slate-500">—</span>
                        <span className="text-slate-300">₹{(agentData.buildingAnalysis.valuation.price_range?.high / 100000).toFixed(1)}L</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Market Stats */}
                {agentData.buildingAnalysis.market && (
                  <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
                    <h5 className="text-blue-400 font-medium text-xs flex items-center gap-1.5 mb-2">
                      <TrendingUp className="w-3 h-3" /> Market Trends (1.5km)
                    </h5>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-slate-700/40 rounded p-2">
                        <p className="text-slate-400 text-[9px]">Avg Price/sqft</p>
                        <p className="text-white font-semibold text-sm">₹{agentData.buildingAnalysis.market.avg_price_per_sqft?.toLocaleString()}</p>
                      </div>
                      <div className="bg-slate-700/40 rounded p-2">
                        <p className="text-slate-400 text-[9px]">1Y Growth</p>
                        <p className="text-green-400 font-semibold text-sm">+{agentData.buildingAnalysis.market.growth_1y}%</p>
                      </div>
                      <div className="bg-slate-700/40 rounded p-2">
                        <p className="text-slate-400 text-[9px]">Properties</p>
                        <p className="text-white font-semibold text-sm">{agentData.buildingAnalysis.market.total_properties}</p>
                      </div>
                      <div className="bg-slate-700/40 rounded p-2">
                        <p className="text-slate-400 text-[9px]">Demand</p>
                        <p className={`font-semibold text-sm ${
                          agentData.buildingAnalysis.market.demand_index === 'High' ? 'text-green-400' :
                          agentData.buildingAnalysis.market.demand_index === 'Medium' ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>{agentData.buildingAnalysis.market.demand_index}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* AI Analysis */}
                {agentData.buildingAnalysis.ai_analysis && (
                  <div className="bg-purple-600/10 border border-purple-500/30 rounded-lg p-3">
                    <h5 className="text-purple-400 font-semibold text-xs mb-2 flex items-center gap-1.5">
                      <Sparkles className="w-3 h-3" /> AI Investment Analysis
                    </h5>
                    <div className="text-slate-200 text-xs leading-relaxed prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {agentData.buildingAnalysis.ai_analysis}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Recommendations */}
                {agentData.buildingAnalysis.recommendations?.length > 0 && (
                  <div className="bg-slate-800/40 rounded-lg p-2 border border-slate-700/50">
                    <h5 className="text-white font-medium text-xs flex items-center gap-1.5 mb-1.5">
                      <CheckCircle className="w-3 h-3 text-green-400" /> Key Highlights
                    </h5>
                    <div className="space-y-1">
                      {agentData.buildingAnalysis.recommendations.map((rec, idx) => (
                        <div key={idx} className="flex items-center gap-1.5 text-[10px] text-slate-300">
                          <span className="w-1 h-1 bg-green-400 rounded-full"></span>
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
              <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/40 rounded-lg p-3">
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

        {activeTab === 'docs' && (
          <div className="space-y-3">
            <h3 className="text-white font-semibold text-sm">Documents</h3>
            <p className="text-slate-400 text-xs">Upload documents for analysis</p>
            <label className="cursor-pointer px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-xs flex items-center gap-1 w-fit">
              <FileText className="w-3 h-3" /> Upload
              <input type="file" className="hidden" multiple accept=".pdf,.doc,.docx,.jpg,.png" />
            </label>
          </div>
        )}

        {activeTab === 'notes' && (
          <div className="space-y-3">
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
