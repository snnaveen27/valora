import { useEffect, useState } from 'react'
import OnlineOSMMap from '../spatial/OnlineOSMMap'
import AnalysisPanel from './AnalysisPanel'
import ChatPanel from './ChatPanel'
import AdminPanel from './AdminPanel'
import ScrapeController from './ScrapeController'
import CinemaOverlay from './CinemaOverlay'
import PaymentCheckout from './PaymentCheckout'
import { useAuth } from '../contexts/AuthContext'
import { Sparkles, Maximize2, Minimize2, X, ChevronRight, ChevronLeft, Wallet, TrendingUp, FileText, StickyNote, Settings, Brain, Expand, Shrink, LogOut, User, Crown, Zap } from 'lucide-react'

import { API_URL } from '../apiConfig'

export default function MainApp() {
  const { user, logout, isAdmin } = useAuth()
  const [agentData, setAgentData] = useState({})
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('insights')
  const [analysisWidth, setAnalysisWidth] = useState('narrow') // narrow, wide, or fullscreen
  const [chatWidth, setChatWidth] = useState('narrow') // narrow or wide
  const [usage, setUsage] = useState(null)
  const [isAdminOpen, setIsAdminOpen] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [showPaymentCheckout, setShowPaymentCheckout] = useState(false)
  const [paymentType, setPaymentType] = useState('subscription') // 'subscription' or 'topup'
  const [liveAnalysis, setLiveAnalysis] = useState(null) // Real-time analysis from AI
  const [isAnalysisFullscreen, setIsAnalysisFullscreen] = useState(false) // Fullscreen mode for deep analysis
  const [isChatFullscreen, setIsChatFullscreen] = useState(false) // Fullscreen mode for chat
  const [isMapFullscreen, setIsMapFullscreen] = useState(false) // Fullscreen mode for map
  
  // Cinema mode for simulations and storytelling
  const [isCinemaMode, setIsCinemaMode] = useState(false)
  const [cinemaNarration, setCinemaNarration] = useState('')
  const [isCinemaPaused, setIsCinemaPaused] = useState(false)

  // Font size persistence
  const [analysisFontSize, setAnalysisFontSize] = useState(() => {
    return parseInt(localStorage.getItem('valora_analysis_font_size')) || 100
  })
  const [chatFontSize, setChatFontSize] = useState(() => {
    return parseInt(localStorage.getItem('valora_chat_font_size')) || 100
  })

  useEffect(() => {
    localStorage.setItem('valora_analysis_font_size', analysisFontSize)
  }, [analysisFontSize])

  useEffect(() => {
    localStorage.setItem('valora_chat_font_size', chatFontSize)
  }, [chatFontSize])

  const adjustAnalysisFontSize = (delta) => {
    setAnalysisFontSize(prev => Math.min(150, Math.max(75, prev + delta)))
  }

  const adjustChatFontSize = (delta) => {
    setChatFontSize(prev => Math.min(150, Math.max(75, prev + delta)))
  }

  useEffect(() => {
    const fetchUsage = async () => {
      if (!user?.id) return
      try {
        const resp = await fetch(`${API_URL}/api/usage/${user.id}`)
        if (resp.ok) {
          const data = await resp.json()
          setUsage(data)
        }
      } catch (err) {
        console.warn('Failed to fetch usage:', err)
      }
    }
    
    if (user?.id) {
      fetchUsage()
      // Refresh usage every 2 minutes
      const interval = setInterval(fetchUsage, 120000)
      return () => clearInterval(interval)
    }
  }, [user?.id])
    
  useEffect(() => {
    const handleUICommand = (e) => {
      const { action, value, panel, tab } = e.detail || {}

      const targetTab = value || tab

      if (action === 'switchTab' && targetTab) {
        // Map old tab names to new 'insights' tab
        if (targetTab === 'analysis' || targetTab === 'market' || targetTab === 'city') {
          setActiveTab('insights')
        } else {
          setActiveTab(targetTab)
        }
      }

      // Handle live analysis updates from AI
      if (action === 'updateAnalysis') {
        setLiveAnalysis(e.detail.analysis)
        setActiveTab('insights') // Auto-switch to insights
        setIsAnalysisOpen(true) // Ensure panel is open
      }

      if (action === 'openPanel') {
        if ((value || panel) === 'analysis' || (value || panel) === 'insights') setIsAnalysisOpen(true)
        if ((value || panel) === 'chat') setIsChatOpen(true)
      }

      if (action === 'closePanel') {
        if ((value || panel) === 'analysis' || (value || panel) === 'insights') setIsAnalysisOpen(false)
        if ((value || panel) === 'chat') setIsChatOpen(false)
      }

      // Agent-controlled fullscreen expansion for deep analysis
      if (action === 'expandAnalysis' || action === 'fullscreenAnalysis') {
        setIsAnalysisFullscreen(true)
        setIsAnalysisOpen(true)
        setActiveTab(targetTab || 'insights')
      }

      if (action === 'collapseAnalysis' || action === 'exitFullscreen') {
        setIsAnalysisFullscreen(false)
      }

      // Toggle comparison mode
      if (action === 'showComparison') {
        setActiveTab('insights')
        setIsAnalysisOpen(true)
        setIsAnalysisFullscreen(true) // Expand for better comparison view
      }

      // Cinema mode controls
      if (action === 'setCinemaMode') {
        setIsCinemaMode(value === true)
        if (value === true) {
          setIsCinemaPaused(false)
        }
      }
      
      if (action === 'updateNarration') {
        setCinemaNarration(value || '')
      }
      
      if (action === 'stopCinema') {
        setIsCinemaMode(false)
        setCinemaNarration('')
        setIsCinemaPaused(false)
      }
      
      // Handle simulation option from insight cards
      if (action === 'showSimulationOption') {
        const { cardType, simulationTypes, lat, lng, preview } = detail
        // Store simulation context in agentData for map to pick up
        setAgentData(prev => ({
          ...prev,
          pendingSimulation: {
            cardType,
            simulationTypes,
            lat,
            lng,
            preview,
            timestamp: Date.now()
          }
        }))
        // Switch to map view to show simulation controls
        setIsMapFullscreen(false)
        // Dispatch event to map to show simulation UI
        window.dispatchEvent(new CustomEvent('valora-map-command', {
          detail: {
            action: 'showSimulationControls',
            cardType,
            simulationTypes,
            lat,
            lng
          }
        }))
      }
    }

    window.addEventListener('valora-ui-command', handleUICommand)
    return () => window.removeEventListener('valora-ui-command', handleUICommand)
  }, [])

  const handleAnalysisUpdate = (analysis) => {
    if (analysis?.coordinates) {
      setAgentData(prev => ({ ...prev, clickedLocation: analysis.coordinates }))
    }
  }

  const toggleAnalysisWidth = () => {
    setAnalysisWidth(prev => prev === 'narrow' ? 'wide' : 'narrow')
  }

  const toggleChatWidth = () => {
    setChatWidth(prev => prev === 'narrow' ? 'wide' : 'narrow')
  }

  const toggleAnalysisFullscreen = () => {
    setIsAnalysisFullscreen(prev => {
      const newState = !prev
      // When enabling analysis fullscreen, disable others
      if (newState) {
        setIsChatFullscreen(false)
        setIsMapFullscreen(false)
      }
      return newState
    })
  }

  const toggleChatFullscreen = () => {
    setIsChatFullscreen(prev => {
      const newState = !prev
      // When enabling chat fullscreen, disable others
      if (newState) {
        setIsAnalysisFullscreen(false)
        setIsMapFullscreen(false)
      }
      return newState
    })
  }

  const toggleMapFullscreen = () => {
    setIsMapFullscreen(prev => {
      const newState = !prev
      // When enabling map fullscreen, disable others
      if (newState) {
        setIsAnalysisFullscreen(false)
        setIsChatFullscreen(false)
      }
      return newState
    })
  }

  // Calculate panel widths based on fullscreen state - smart shrinking
  const getAnalysisWidth = () => {
    if (isAnalysisFullscreen) return 'calc(100% - 64px)' // Nearly full width, leave room for collapse button
    if (isChatFullscreen || isMapFullscreen) return '32px' // Minimize when others are fullscreen
    if (!isAnalysisOpen) return '32px'
    return analysisWidth === 'wide' ? 'calc(50% - 160px)' : 'calc(35% - 112px)'
  }

  const getChatWidth = () => {
    if (isChatFullscreen) return 'calc(100% - 64px)' // Chat fullscreen
    if (isAnalysisFullscreen || isMapFullscreen) return '32px' // Minimize when others are fullscreen
    if (!isChatOpen) return '32px'
    return chatWidth === 'wide' ? 'calc(50% - 160px)' : 'calc(35% - 112px)'
  }

  const getMapWidth = () => {
    if (isMapFullscreen) return 'calc(100% - 64px)' // Map fullscreen
    if (isAnalysisFullscreen || isChatFullscreen) return '32px' // Minimize when others are fullscreen
    return 'flex-1'
  }

  return (
    <div className="h-screen w-screen bg-slate-900 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="h-12 bg-slate-800 border-b border-slate-700 px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-bold text-lg">Valora AI</span>
          <span className="text-slate-400 text-xs ml-2">City Intelligence</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Tier Badge */}
          {user && (
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
              user.tier === 'admin' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' :
              user.tier === 'enterprise' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
              user.tier === 'team' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' :
              user.tier === 'pro' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
              'bg-slate-600/50 text-slate-300 border border-slate-500/30'
            }`}>
              {user.tier === 'admin' && <Crown className="w-3 h-3" />}
              {user.tier === 'enterprise' && <Crown className="w-3 h-3" />}
              {user.tier === 'pro' && <Zap className="w-3 h-3" />}
              {user.tier === 'team' && <Zap className="w-3 h-3" />}
              {user.tier?.toUpperCase() || 'FREE'}
            </div>
          )}

          {/* Usage Display - Monthly Units */}
          {usage && !usage.is_unlimited && (
            <button
              onClick={() => setShowUpgradeModal(true)}
              className={`flex items-center gap-2 px-3 py-1 rounded-full border transition ${
                usage.units_remaining < 20 
                  ? 'bg-red-500/20 border-red-500/50 hover:bg-red-500/30' 
                  : usage.units_remaining < 100 
                    ? 'bg-amber-500/20 border-amber-500/50 hover:bg-amber-500/30'
                    : 'bg-slate-700/50 border-slate-600 hover:bg-slate-600/50'
              }`}
            >
              <Wallet className={`w-3.5 h-3.5 ${
                usage.units_remaining < 20 ? 'text-red-400' : 
                usage.units_remaining < 100 ? 'text-amber-400' : 'text-blue-400'
              }`} />
              <span className="text-white text-xs font-bold">
                {usage.units_remaining}
              </span>
              <span className="text-slate-400 text-[10px]">units left</span>
            </button>
          )}
          
          {/* Unlimited badge for enterprise/admin */}
          {usage?.is_unlimited && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/20 text-emerald-300 rounded-full border border-emerald-500/30 text-xs font-medium">
              <Zap className="w-3 h-3" />
              Unlimited
            </div>
          )}

          {/* Admin Button - Only for admins */}
          {isAdmin && (
            <button
              onClick={() => setIsAdminOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 hover:text-white rounded-lg border border-purple-500/30 transition text-xs font-medium"
            >
              <Settings className="w-3.5 h-3.5" />
              Admin
            </button>
          )}

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white rounded-lg border border-slate-600 transition text-xs"
            >
              <User className="w-3.5 h-3.5" />
              <span className="max-w-[100px] truncate">{user?.name || user?.email}</span>
            </button>
            
            {showUserMenu && (
              <div className="absolute right-0 top-full mt-1 w-56 bg-slate-800 border border-slate-700 rounded-xl shadow-xl z-50 overflow-hidden">
                <div className="p-3 border-b border-slate-700">
                  <p className="text-white font-medium text-sm truncate">{user?.name}</p>
                  <p className="text-slate-400 text-xs truncate">{user?.email}</p>
                  {user?.company && (
                    <p className="text-slate-500 text-xs truncate mt-1">{user.company}</p>
                  )}
                </div>
                <div className="p-2">
                  <button
                    onClick={() => {
                      setShowUserMenu(false)
                      logout()
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 rounded-lg transition text-sm"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content - 3 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Analysis Panel */}
        <div 
          className={`h-full bg-slate-800 border-r border-slate-700 flex flex-col transition-all duration-300 ${isAnalysisFullscreen ? 'z-10' : ''}`}
          style={{
            width: getAnalysisWidth(),
            minWidth: isAnalysisOpen && !isChatFullscreen && !isMapFullscreen ? (isAnalysisFullscreen ? '600px' : '280px') : '0px',
            flexShrink: 0
          }}
        >
          {isAnalysisOpen ? (
            <>
              <div className="p-2 border-b border-slate-700 flex items-center justify-between shrink-0">
                <div className="flex gap-1">
                  {['insights', 'docs', 'notes'].map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-2 py-1 rounded text-xs font-bold transition whitespace-nowrap flex items-center gap-1.5 ${
                        activeTab === tab ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {tab === 'insights' && <TrendingUp className="w-3 h-3" />}
                      {tab === 'docs' && <FileText className="w-3 h-3" />}
                      {tab === 'notes' && <StickyNote className="w-3 h-3" />}
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>
                <div className="flex gap-1 ml-2">
                  <div className="flex items-center gap-0.5 bg-slate-700/50 rounded px-1 mr-1">
                    <button 
                      onClick={() => adjustAnalysisFontSize(-5)}
                      className="p-1 text-slate-400 hover:text-white transition rounded"
                      title="Decrease font size"
                    >
                      <span className="text-xs font-bold">-</span>
                    </button>
                    <span className="text-[10px] text-slate-500 font-bold min-w-[24px] text-center">{analysisFontSize}%</span>
                    <button 
                      onClick={() => adjustAnalysisFontSize(5)}
                      className="p-1 text-slate-400 hover:text-white transition rounded"
                      title="Increase font size"
                    >
                      <span className="text-xs font-bold">+</span>
                    </button>
                  </div>
                  {!isAnalysisFullscreen && (
                    <button 
                      onClick={toggleAnalysisWidth} 
                      className="p-1 text-slate-500 hover:text-white transition rounded hover:bg-slate-700"
                      title={analysisWidth === 'narrow' ? 'Expand' : 'Shrink'}
                    >
                      {analysisWidth === 'narrow' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                    </button>
                  )}
                  <button 
                    onClick={toggleAnalysisFullscreen} 
                    className={`p-1 transition rounded hover:bg-slate-700 ${isAnalysisFullscreen ? 'text-purple-400 hover:text-purple-300' : 'text-slate-500 hover:text-white'}`}
                    title={isAnalysisFullscreen ? 'Exit Fullscreen' : 'Deep Analysis Mode'}
                  >
                    {isAnalysisFullscreen ? <Shrink className="w-3.5 h-3.5" /> : <Expand className="w-3.5 h-3.5" />}
                  </button>
                  <button 
                    onClick={() => { setIsAnalysisOpen(false); setIsAnalysisFullscreen(false); }} 
                    className="p-1 text-slate-500 hover:text-white transition rounded hover:bg-slate-700"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                <AnalysisPanel 
                  agentData={agentData} 
                  setAgentData={setAgentData}
                  activeTab={activeTab}
                  setActiveTab={setActiveTab}
                  fontSize={analysisFontSize}
                  liveAnalysis={liveAnalysis}
                  isFullscreen={isAnalysisFullscreen}
                />
              </div>
            </>
          ) : (
            <button
              onClick={() => setIsAnalysisOpen(true)}
              className="h-full w-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Center Map */}
        <div 
          className="h-full min-w-0 transition-all duration-300 relative"
          style={{ 
            width: isMapFullscreen ? 'calc(100% - 64px)' : (isAnalysisFullscreen || isChatFullscreen ? '32px' : undefined),
            flexGrow: (isMapFullscreen || (!isAnalysisFullscreen && !isChatFullscreen)) ? 1 : 0,
            flexShrink: 1
          }}
        >
          <OnlineOSMMap
            onAnalysisUpdate={handleAnalysisUpdate}
            agentData={agentData}
            setAgentData={setAgentData}
            toggleMapFullscreen={toggleMapFullscreen}
            isMapFullscreen={isMapFullscreen}
          />
        </div>

        {/* Right Chat Panel */}
        <div 
          className="h-full bg-slate-800 border-l border-slate-700 flex flex-col transition-all duration-300"
          style={{
            width: getChatWidth(),
            minWidth: isChatOpen && !isAnalysisFullscreen && !isMapFullscreen ? (isChatFullscreen ? '600px' : '280px') : '0px',
            flexShrink: 0
          }}
        >
          {isChatOpen ? (
            <>
              <div className="p-2 border-b border-slate-700 flex items-center justify-between shrink-0">
                <span className="text-white font-medium text-sm flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  AI Assistant
                </span>
                <div className="flex gap-1">
                  <div className="flex items-center gap-0.5 bg-slate-700/50 rounded px-1 mr-1">
                    <button 
                      onClick={() => adjustChatFontSize(-5)}
                      className="p-1 text-slate-400 hover:text-white transition rounded"
                      title="Decrease font size"
                    >
                      <span className="text-xs font-bold">-</span>
                    </button>
                    <span className="text-[10px] text-slate-500 font-bold min-w-[24px] text-center">{chatFontSize}%</span>
                    <button 
                      onClick={() => adjustChatFontSize(5)}
                      className="p-1 text-slate-400 hover:text-white transition rounded"
                      title="Increase font size"
                    >
                      <span className="text-xs font-bold">+</span>
                    </button>
                  </div>
                  {!isChatFullscreen && (
                    <button 
                      onClick={toggleChatWidth} 
                      className="p-1 text-slate-400 hover:text-white transition rounded hover:bg-slate-700"
                      title={chatWidth === 'narrow' ? 'Expand' : 'Shrink'}
                    >
                      {chatWidth === 'narrow' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                    </button>
                  )}
                  <button 
                    onClick={toggleChatFullscreen} 
                    className={`p-1 transition rounded hover:bg-slate-700 ${isChatFullscreen ? 'text-purple-400 hover:text-purple-300' : 'text-slate-500 hover:text-white'}`}
                    title={isChatFullscreen ? 'Exit Fullscreen' : 'Fullscreen Chat'}
                  >
                    {isChatFullscreen ? <Shrink className="w-3.5 h-3.5" /> : <Expand className="w-3.5 h-3.5" />}
                  </button>
                  <button 
                    onClick={() => { setIsChatOpen(false); setIsChatFullscreen(false); }} 
                    className="p-1 text-slate-400 hover:text-white transition rounded hover:bg-slate-700"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                <ChatPanel 
                  agentData={agentData} 
                  setAgentData={setAgentData} 
                  fontSize={chatFontSize}
                />
              </div>
            </>
          ) : (
            <button
              onClick={() => setIsChatOpen(true)}
              className="h-full w-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Admin Panel Modal */}
      <AdminPanel isOpen={isAdminOpen} onClose={() => setIsAdminOpen(false)} />

      {/* Upgrade/Top-up Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Upgrade Your Plan</h2>
              <button onClick={() => setShowUpgradeModal(false)} className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Current Usage */}
            {usage && (
              <div className="bg-slate-700/50 rounded-xl p-4 mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-slate-400 text-sm">Monthly Usage</span>
                  <span className="text-white font-bold">{usage.units_used} / {usage.monthly_limit} units</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      usage.units_remaining < 20 ? 'bg-red-500' : 
                      usage.units_remaining < 100 ? 'bg-amber-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${Math.min(100, (usage.units_used / usage.monthly_limit) * 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* 80% Launch Promo Banner */}
            <div className="mb-6 p-4 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/50 rounded-xl">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-amber-400 font-bold text-lg">🎉 Launch Special: 80% OFF!</p>
                  <p className="text-amber-200/80 text-xs">Limited time offer for early adopters</p>
                </div>
                <div className="bg-amber-500 text-black px-3 py-1 rounded-full font-bold text-sm">
                  LAUNCH80
                </div>
              </div>
            </div>

            {/* Top-up Packs with Promo */}
            <div className="mb-6">
              <h3 className="text-white font-semibold mb-3">Top-up Packs</h3>
              <div className="grid grid-cols-3 gap-3">
                <button className="p-4 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-blue-500/50 rounded-xl transition text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-bl">80% OFF</div>
                  <p className="text-2xl font-bold text-white">100</p>
                  <p className="text-slate-400 text-xs">units</p>
                  <p className="text-slate-500 line-through text-xs mt-1">₹299</p>
                  <p className="text-amber-400 font-semibold">₹59</p>
                </button>
                <button className="p-4 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-blue-500/50 rounded-xl transition text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-bl">80% OFF</div>
                  <p className="text-2xl font-bold text-white">300</p>
                  <p className="text-slate-400 text-xs">units</p>
                  <p className="text-slate-500 line-through text-xs mt-1">₹699</p>
                  <p className="text-amber-400 font-semibold">₹139</p>
                </button>
                <button className="p-4 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-blue-500/50 rounded-xl transition text-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-bl">80% OFF</div>
                  <p className="text-2xl font-bold text-white">1,000</p>
                  <p className="text-slate-400 text-xs">units</p>
                  <p className="text-slate-500 line-through text-xs mt-1">₹1,999</p>
                  <p className="text-amber-400 font-semibold">₹399</p>
                </button>
              </div>
              <p className="text-slate-500 text-xs mt-2 text-center">Pay via Razorpay or Cashfree</p>
            </div>

            {/* Upgrade Plan with Promo */}
            <div className="border-t border-slate-700 pt-6">
              <h3 className="text-white font-semibold mb-3">Upgrade Your Plan</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 bg-gradient-to-br from-green-500/20 to-emerald-500/10 border border-green-500/30 rounded-xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-bl">80% OFF</div>
                  <p className="text-green-400 font-bold">Pro</p>
                  <p className="text-2xl font-bold text-white">1,000</p>
                  <p className="text-slate-400 text-xs">units/month</p>
                  <p className="text-slate-500 line-through text-xs mt-2">₹2,999/mo</p>
                  <p className="text-amber-400 font-bold text-lg">₹599/mo</p>
                </div>
                <div className="p-4 bg-gradient-to-br from-blue-500/20 to-purple-500/10 border border-blue-500/30 rounded-xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-bl">80% OFF</div>
                  <p className="text-blue-400 font-bold">Team</p>
                  <p className="text-2xl font-bold text-white">3,000</p>
                  <p className="text-slate-400 text-xs">units/month</p>
                  <p className="text-slate-500 line-through text-xs mt-2">₹4,999/seat</p>
                  <p className="text-amber-400 font-bold text-lg">₹999/seat</p>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => {
                    setShowUpgradeModal(false)
                    setPaymentType('subscription')
                    setShowPaymentCheckout(true)
                  }}
                  className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  Subscribe Now
                </button>
                <button
                  onClick={() => {
                    setShowUpgradeModal(false)
                    setPaymentType('topup')
                    setShowPaymentCheckout(true)
                  }}
                  className="flex-1 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                >
                  <Wallet className="w-4 h-4" />
                  Buy Top-up
                </button>
              </div>
              <p className="text-emerald-400 text-xs mt-3 text-center font-medium">✓ Promo applied automatically at checkout</p>
            </div>
          </div>
        </div>
      )}

      {/* Payment Checkout Modal */}
      <PaymentCheckout
        isOpen={showPaymentCheckout}
        onClose={() => setShowPaymentCheckout(false)}
        type={paymentType}
      />

      {/* Cinema Mode Overlay */}
      <CinemaOverlay 
        isActive={isCinemaMode}
        narration={cinemaNarration}
        isPaused={isCinemaPaused}
        onStop={() => {
          setIsCinemaMode(false)
          setCinemaNarration('')
          setIsCinemaPaused(false)
          window.dispatchEvent(new CustomEvent('valora-cinema-stop'))
        }}
        onPause={() => {
          setIsCinemaPaused(!isCinemaPaused)
          window.dispatchEvent(new CustomEvent('valora-cinema-pause', { detail: { paused: !isCinemaPaused } }))
        }}
      />
    </div>
  )
}
