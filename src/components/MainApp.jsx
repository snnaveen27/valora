import { useState, useEffect, useRef, useMemo, lazy, Suspense } from 'react'
import axios from 'axios'
import InteractiveMapView from './InteractiveMapView'
import TimeSlider from './TimeSlider'
import ChatPanelMultiAgent from './ChatPanelMultiAgent'
import { Maximize2, Minimize2, BarChart2, X, ChevronLeft, ChevronRight, FileText, StickyNote, Upload, Trash2, Sparkles, RefreshCw, User, LogOut, Settings, ChevronDown, TrendingUp, AlertTriangle, Target, Zap, Building2, Box } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts'

// Lazy load Digital Twin viewer for performance
const DigitalTwinViewer = lazy(() => import('./DigitalTwinViewer'))

export default function MainApp({ user, onLogout }) {
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(true)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [analysisWidth, setAnalysisWidth] = useState('1/3')
  const [chatWidth, setChatWidth] = useState('1/3')
  const [summary, setSummary] = useState(null)
  const [latestAnalysis, setLatestAnalysis] = useState(null)
  const [mapNotification, setMapNotification] = useState(null)
  const mapRegionRef = useRef(null)
  const [activeTab, setActiveTab] = useState('stats')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [notes, setNotes] = useState([])
  const [currentNote, setCurrentNote] = useState({ title: '', content: '' })
  const [analyzingFile, setAnalyzingFile] = useState(null)
  const [editingNote, setEditingNote] = useState(null)
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [timeData, setTimeData] = useState({ monthsFromNow: 0, mode: 'current', label: 'Present' })
  const [dmpeData, setDmpeData] = useState(null)
  const [loadingDmpe, setLoadingDmpe] = useState(false)
  const [showDigitalTwin, setShowDigitalTwin] = useState(false)
  
  const [agentData, setAgentData] = useState({
    forecasts: null,
    recommendations: null,
    spatialData: null,
    chatResponse: null,
    confidence: 0,
    planId: null
  })

  useEffect(() => {
    let mounted = true
    axios.get('/api/market/summary')
      .then(res => { if (mounted) setSummary(res.data) })
      .catch(() => {})
    return () => { mounted = false }
  }, [])

  // Fetch DMPE forecast data
  useEffect(() => {
    if (activeTab === 'forecast' && !dmpeData) {
      setLoadingDmpe(true)
      // Fetch DMPE data from backend
      axios.get('/api/dmpe/market-analysis')
        .then(res => setDmpeData(res.data))
        .catch(() => {
          // Use mock data if API not available
          setDmpeData({
            priceTrends: [
              { month: 'Jul', price: 8500 }, { month: 'Aug', price: 8650 },
              { month: 'Sep', price: 8800 }, { month: 'Oct', price: 8950 },
              { month: 'Nov', price: 9100 }, { month: 'Dec', price: 9250 }
            ],
            forecast: { current: 9250, predicted_1y: 10175, growth: 10.0, confidence: 0.87 },
            hotLocalities: [
              { name: 'Whitefield', growth: 12.5, grade: 'A+' },
              { name: 'Sarjapur', growth: 11.2, grade: 'A' },
              { name: 'Electronic City', growth: 9.8, grade: 'A' },
              { name: 'HSR Layout', growth: 8.5, grade: 'B+' }
            ],
            riskMetrics: { market: 0.25, liquidity: 0.35, regulatory: 0.15 },
            demandSupply: [
              { name: 'Supply', value: 35 },
              { name: 'Demand', value: 65 }
            ]
          })
        })
        .finally(() => setLoadingDmpe(false))
    }
  }, [activeTab, dmpeData])

  const handleAnalysisUpdate = (analysis) => {
    setLatestAnalysis(analysis)
    if (analysis?.spatialData) {
      setAgentData(prev => ({ ...prev, spatialData: analysis.spatialData }))
    }
  }

  const handlePropertySelect = (property) => {
    setSelectedProperty(property)
    setActiveTab('property')
    if (!isAnalysisOpen) setIsAnalysisOpen(true)
  }

  const handleTimeChange = (data) => {
    setTimeData(data)
  }

  const formatPrice = (price) => {
    if (!price) return 'N/A'
    if (price >= 10000000) return `₹${(price/10000000).toFixed(2)} Cr`
    if (price >= 100000) return `₹${(price/100000).toFixed(2)} L`
    return `₹${price.toLocaleString()}`
  }

  // Use percentage values for responsive layout
  const getWidthPercent = (w) => {
    return w === '1/2' ? '35%' : '25%'
  }

  const cycleWidth = (current) => {
    // Toggle between 25% and 35%
    return current === '1/3' ? '1/2' : '1/3'
  }

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 overflow-hidden flex flex-col">
      {/* Notification */}
      {mapNotification && (
        <div className={`fixed top-20 left-1/2 transform -translate-x-1/2 z-[100] px-4 py-2 rounded-lg shadow-lg ${
          mapNotification.type === 'error' ? 'bg-red-500/90' : 'bg-green-500/90'
        } text-white font-medium`}>
          {mapNotification.message}
        </div>
      )}

      {/* Top Header Bar with Logo and User Profile */}
      <div className="h-14 bg-slate-800/90 backdrop-blur-sm border-b border-slate-700 px-4 flex items-center justify-between z-40">
        {/* Left: Logo */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-white font-bold text-lg">Valora AI</span>
          </div>
        </div>

        {/* Right: User Profile & Logout */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-700/50 transition"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-white text-sm font-medium truncate max-w-[120px]">{user?.name || user?.email?.split('@')[0] || 'User'}</p>
              <p className="text-slate-400 text-xs capitalize">{user?.role || 'Member'}</p>
            </div>
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
          </button>

          {/* User Dropdown Menu */}
          {showUserMenu && (
            <>
              {/* Backdrop to close menu */}
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setShowUserMenu(false)}
              />
              <div className="absolute right-0 top-full mt-2 w-64 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                {/* User Info Header */}
                <div className="p-4 bg-gradient-to-br from-blue-500/20 to-purple-500/20 border-b border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                      <User className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="text-white font-semibold">{user?.name || 'User'}</p>
                      <p className="text-slate-400 text-sm truncate">{user?.email || 'No email'}</p>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="p-2">
                  <button
                    onClick={() => {
                      setActiveTab('stats')
                      setIsAnalysisOpen(true)
                      setShowUserMenu(false)
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-300 hover:bg-slate-700/50 rounded-lg transition text-left"
                  >
                    <User className="w-4 h-4" />
                    <span>My Profile</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('notes')
                      setIsAnalysisOpen(true)
                      setShowUserMenu(false)
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-300 hover:bg-slate-700/50 rounded-lg transition text-left"
                  >
                    <StickyNote className="w-4 h-4" />
                    <span>My Notes</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('docs')
                      setIsAnalysisOpen(true)
                      setShowUserMenu(false)
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-300 hover:bg-slate-700/50 rounded-lg transition text-left"
                  >
                    <FileText className="w-4 h-4" />
                    <span>My Documents</span>
                  </button>
                </div>

                {/* Logout */}
                <div className="p-2 border-t border-slate-700">
                  <button
                    onClick={() => {
                      setShowUserMenu(false)
                      onLogout()
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 text-red-400 hover:bg-red-500/10 rounded-lg transition text-left"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Main Content Area - Flex layout for side-by-side panels */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Analysis Panel */}
        <div 
          className={`h-full bg-slate-800 border-r border-slate-700 flex flex-col transition-all duration-300 overflow-hidden shrink-0 ${!isAnalysisOpen ? 'w-8' : ''}`}
          style={isAnalysisOpen ? { 
            width: analysisWidth === '1/2' ? 'calc(50% - 160px)' : 'calc(33% - 107px)',
            minWidth: '280px'
          } : { width: '32px' }}
        >
          {isAnalysisOpen ? (
            <>
              {/* Panel Header */}
              <div className="p-2 border-b border-slate-700 flex items-center justify-between shrink-0">
                <div className="flex gap-1 overflow-x-auto">
                  {['stats', 'forecast', 'property', 'docs', 'notes'].map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-2 py-1 rounded text-xs font-medium transition whitespace-nowrap ${
                        activeTab === tab ? 'bg-blue-500 text-white' : 'text-slate-400 hover:bg-slate-700'
                      }`}
                    >
                      {tab === 'stats' && <BarChart2 className="w-3 h-3 inline mr-1" />}
                      {tab === 'forecast' && <TrendingUp className="w-3 h-3 inline mr-1" />}
                      {tab === 'property' && '🏠 '}
                      {tab === 'docs' && <FileText className="w-3 h-3 inline mr-1" />}
                      {tab === 'notes' && <StickyNote className="w-3 h-3 inline mr-1" />}
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>
                <div className="flex gap-1 shrink-0">
                  <button 
                    onClick={() => setAnalysisWidth(cycleWidth(analysisWidth))} 
                    className="p-1 text-slate-400 hover:text-white transition"
                    title={analysisWidth === '1/3' ? 'Expand' : 'Shrink'}
                  >
                    {analysisWidth === '1/3' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={() => setIsAnalysisOpen(false)} className="p-1 text-slate-400 hover:text-white transition" title="Close">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Panel Content */}
              <div className="flex-1 overflow-y-auto p-3">
                {activeTab === 'stats' && (
                  <div className="space-y-3">
                    <h3 className="text-white font-semibold text-sm">Market Overview</h3>
                    {summary ? (
                      <div className="grid grid-cols-2 gap-2">
                        <div className="bg-slate-700/50 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px]">Avg Price</p>
                          <p className="text-white font-semibold text-sm">{formatPrice(summary.avg_price)}</p>
                        </div>
                        <div className="bg-slate-700/50 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px]">Listings</p>
                          <p className="text-white font-semibold text-sm">{summary.total_listings?.toLocaleString() || 'N/A'}</p>
                        </div>
                        <div className="bg-slate-700/50 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px]">Price/sqft</p>
                          <p className="text-white font-semibold text-sm">₹{summary.price_per_sqft?.toLocaleString() || 'N/A'}</p>
                        </div>
                        <div className="bg-slate-700/50 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px]">Hot Areas</p>
                          <p className="text-white font-semibold text-xs truncate">{summary.hot_areas || 'Loading...'}</p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-slate-400 text-sm">Loading...</div>
                    )}
                    
                    <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                      <p className="text-blue-400 text-xs font-medium">View: {timeData.label}</p>
                      <p className="text-slate-400 text-[10px]">Mode: {timeData.mode}</p>
                    </div>
                  </div>
                )}

                {activeTab === 'forecast' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-green-400" />
                        DMPE Forecast
                      </h3>
                      <button 
                        onClick={() => setDmpeData(null)} 
                        className="p-1 text-slate-400 hover:text-white"
                        title="Refresh"
                      >
                        <RefreshCw className={`w-3 h-3 ${loadingDmpe ? 'animate-spin' : ''}`} />
                      </button>
                    </div>
                    
                    {loadingDmpe ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                      </div>
                    ) : dmpeData ? (
                      <>
                        {/* Price Forecast Card */}
                        <div className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-lg p-3">
                          <p className="text-slate-400 text-[10px]">1-Year Price Forecast</p>
                          <div className="flex items-end gap-2">
                            <p className="text-white font-bold text-lg">₹{dmpeData.forecast?.predicted_1y?.toLocaleString()}/sqft</p>
                            <span className="text-green-400 text-xs font-medium flex items-center">
                              <TrendingUp className="w-3 h-3 mr-0.5" />
                              +{dmpeData.forecast?.growth}%
                            </span>
                          </div>
                          <p className="text-slate-500 text-[10px] mt-1">Confidence: {Math.round((dmpeData.forecast?.confidence || 0) * 100)}%</p>
                        </div>

                        {/* Price Trend Chart */}
                        <div className="bg-slate-700/30 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px] mb-2">Price Trend (₹/sqft)</p>
                          <div className="h-24">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart data={dmpeData.priceTrends}>
                                <defs>
                                  <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                  </linearGradient>
                                </defs>
                                <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                                <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={35} />
                                <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px', fontSize: '10px' }} />
                                <Area type="monotone" dataKey="price" stroke="#3b82f6" fill="url(#priceGradient)" strokeWidth={2} />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                        {/* Hot Localities */}
                        <div className="bg-slate-700/30 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px] mb-2 flex items-center gap-1">
                            <Zap className="w-3 h-3 text-yellow-400" /> Hot Localities
                          </p>
                          <div className="space-y-1">
                            {dmpeData.hotLocalities?.slice(0, 4).map((loc, i) => (
                              <div key={i} className="flex items-center justify-between py-1 border-b border-slate-600/50 last:border-0">
                                <span className="text-white text-xs">{loc.name}</span>
                                <div className="flex items-center gap-2">
                                  <span className="text-green-400 text-[10px]">+{loc.growth}%</span>
                                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                                    loc.grade === 'A+' ? 'bg-green-500/20 text-green-400' :
                                    loc.grade === 'A' ? 'bg-blue-500/20 text-blue-400' :
                                    'bg-yellow-500/20 text-yellow-400'
                                  }`}>{loc.grade}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Risk Metrics */}
                        <div className="bg-slate-700/30 rounded-lg p-2">
                          <p className="text-slate-400 text-[10px] mb-2 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-orange-400" /> Risk Assessment
                          </p>
                          <div className="space-y-2">
                            {[
                              { label: 'Market Risk', value: dmpeData.riskMetrics?.market, color: 'bg-blue-500' },
                              { label: 'Liquidity Risk', value: dmpeData.riskMetrics?.liquidity, color: 'bg-orange-500' },
                              { label: 'Regulatory Risk', value: dmpeData.riskMetrics?.regulatory, color: 'bg-green-500' }
                            ].map((risk, i) => (
                              <div key={i}>
                                <div className="flex justify-between text-[10px] mb-0.5">
                                  <span className="text-slate-400">{risk.label}</span>
                                  <span className="text-white">{Math.round((risk.value || 0) * 100)}%</span>
                                </div>
                                <div className="h-1.5 bg-slate-600 rounded-full overflow-hidden">
                                  <div className={`h-full ${risk.color} rounded-full`} style={{ width: `${(risk.value || 0) * 100}%` }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    ) : (
                      <p className="text-slate-400 text-xs">No forecast data available</p>
                    )}
                  </div>
                )}

                {activeTab === 'property' && (
                  <div className="space-y-3">
                    <h3 className="text-white font-semibold text-sm">Property Details</h3>
                    {selectedProperty ? (
                      <div className="bg-slate-700/50 rounded-lg p-3 space-y-2">
                        <div>
                          <p className="text-slate-400 text-[10px]">Price</p>
                          <p className="text-white font-bold text-lg">{formatPrice(selectedProperty.price)}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <p className="text-slate-400 text-[10px]">Type</p>
                            <p className="text-white text-sm">{selectedProperty.property_type || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-slate-400 text-[10px]">Area</p>
                            <p className="text-white text-sm">{selectedProperty.area_sqft || selectedProperty.size} sqft</p>
                          </div>
                        </div>
                        
                        {/* 3D Digital Twin Button */}
                        <button
                          onClick={() => setShowDigitalTwin(true)}
                          className="w-full mt-3 py-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
                        >
                          <Box className="w-4 h-4" />
                          View 3D Digital Twin
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <p className="text-slate-400 text-xs">Click a property marker to view details</p>
                        
                        {/* Demo 3D button */}
                        <button
                          onClick={() => setShowDigitalTwin(true)}
                          className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-xs transition flex items-center justify-center gap-2"
                        >
                          <Box className="w-3 h-3" />
                          Demo: View 3D Building
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'docs' && (
                  <div className="space-y-3">
                    <h3 className="text-white font-semibold text-sm">Documents</h3>
                    <label className="cursor-pointer px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-xs flex items-center gap-1 w-fit">
                      <Upload className="w-3 h-3" /> Upload
                      <input type="file" className="hidden" multiple accept=".pdf,.doc,.docx,.jpg,.png" />
                    </label>
                    <p className="text-slate-400 text-xs">No documents yet</p>
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
                    <button className="w-full py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition text-xs">
                      Save Note
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <button
              onClick={() => setIsAnalysisOpen(true)}
              className="h-full w-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition"
              title="Open Analysis Panel"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Center Map Area - Takes remaining space */}
        <div className="flex-1 h-full flex flex-col min-w-0" ref={mapRegionRef}>
          {/* Time Slider - Attached to top */}
          <TimeSlider onTimeChange={handleTimeChange} onAnalyze={() => {}} />
          
          {/* Map */}
          <div className="flex-1 relative">
            <InteractiveMapView
              onAnalysisUpdate={handleAnalysisUpdate}
              agentData={agentData}
              setAgentData={setAgentData}
              onPropertySelect={handlePropertySelect}
            />
          </div>
        </div>

        {/* Right Chat Panel */}
        <div
          className="h-full bg-slate-800 border-l border-slate-700 flex flex-col transition-all duration-300 overflow-hidden shrink-0"
          style={{ 
            width: chatWidth === '1/2' ? 'calc(50% - 160px)' : 'calc(33% - 107px)',
            minWidth: '300px'
          }}
        >
          {/* Chat Header */}
          <div className="p-2 border-b border-slate-700 flex items-center justify-between shrink-0">
            <h3 className="text-white font-semibold text-sm flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              AI Assistant
            </h3>
            <button 
              onClick={() => setChatWidth(cycleWidth(chatWidth))} 
              className="p-1 text-slate-400 hover:text-white transition"
              title={chatWidth === '1/3' ? 'Expand' : 'Shrink'}
            >
              {chatWidth === '1/3' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
          
          {/* Chat Content */}
          <div className="flex-1 overflow-hidden">
            <ChatPanelMultiAgent
              onAnalysisUpdate={handleAnalysisUpdate}
              agentData={agentData}
              setAgentData={setAgentData}
            />
          </div>
        </div>
      </div>

      {/* Digital Twin 3D Viewer Modal */}
      {showDigitalTwin && (
        <Suspense fallback={
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-white">Loading 3D Viewer...</p>
            </div>
          </div>
        }>
          <DigitalTwinViewer
            property={selectedProperty}
            isOpen={showDigitalTwin}
            onClose={() => setShowDigitalTwin(false)}
          />
        </Suspense>
      )}
    </div>
  )
}
