import { useEffect, useRef, useState, lazy, Suspense } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Sparkles, Maximize2, Minimize2, X, ChevronRight, ChevronLeft, Wallet, TrendingUp, FileText, StickyNote, Settings, Brain, Expand, Shrink, LogOut, User, Crown, Zap, MapPin, LocateFixed, Cloud, Loader2, Activity, CheckCircle2 } from 'lucide-react'

import { API_URL } from '../apiConfig'

// Lazy load heavy components
const OnlineOSMMap = lazy(() => import('../spatial/OnlineOSMMap'))
const AnalysisPanel = lazy(() => import('./AnalysisPanel'))
const EnhancedChatPanel = lazy(() => import('./chat/EnhancedChatPanel'))
const AdminPanel = lazy(() => import('./AdminPanel'))
const ScrapeController = lazy(() => import('./ScrapeController'))
const CinemaOverlay = lazy(() => import('./CinemaOverlay'))
const PaymentCheckout = lazy(() => import('./PaymentCheckout'))
const TopTaskBanner = lazy(() => import('./TopTaskBanner'))

// Loading spinner component
const ComponentLoader = () => (
  <div className="flex items-center justify-center h-full">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
  </div>
)

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
  
  // Top task banner state
  const [taskBannerData, setTaskBannerData] = useState(null)
  const [showTaskBanner, setShowTaskBanner] = useState(false)
  const [showFloatingBanner, setShowFloatingBanner] = useState(false) // Hidden by default
  const [currentQuery, setCurrentQuery] = useState('')
  const [lastTaskProgress, setLastTaskProgress] = useState(null)
  const [isTaskCancelled, setIsTaskCancelled] = useState(false)
  const [taskHistory, setTaskHistory] = useState([]) // Track task history

  // Update last task progress when taskBannerData changes
  useEffect(() => {
    if (taskBannerData) {
      const type = taskBannerData.type
      
      if (type === 'task_cancelled') {
        setLastTaskProgress({ step: 'Stopped', detail: 'Query cancelled by user', percent: 0, timestamp: Date.now() })
        setIsTaskCancelled(true)
        setShowTaskBanner(false) // Hide floating banner
        setShowFloatingBanner(false)
        // Add to history
        setTaskHistory(prev => [...prev.slice(-4), { step: 'Stopped', detail: 'Query cancelled', percent: 0, timestamp: Date.now() }])
        // Auto-clear after 2 seconds
        setTimeout(() => {
          setLastTaskProgress(null)
          setIsTaskCancelled(false)
        }, 2000)
        return
      }
      
      // Reset cancelled state on new tasks and show floating banner
      if (type === 'intent_classification_start') {
        setIsTaskCancelled(false)
        setTaskHistory([]) // Clear history for new query
        setShowTaskBanner(true)
        setShowFloatingBanner(true) // Auto-show floating banner
      }
      
      if (type === 'done') {
        setLastTaskProgress({ step: 'Done', detail: 'Complete!', percent: 100, timestamp: Date.now() })
        setIsTaskCancelled(false)
        setTaskHistory(prev => [...prev.slice(-4), { step: 'Done', detail: 'Complete!', percent: 100, timestamp: Date.now() }])
        // Auto-clear after 3 seconds
        setTimeout(() => setLastTaskProgress(null), 3000)
        return
      }
      if (type === 'intent_classification_start') {
        setLastTaskProgress({ step: 'Step 1/1', detail: 'Analyzing...', percent: 5, timestamp: Date.now() })
        return
      }
      if (type === 'intent_detected') {
        const total = taskBannerData.task_graph?.tasks?.length || 1
        const progress = { step: `Step 1/${total}`, detail: `Intent: ${taskBannerData.intent?.replace(/_/g, ' ') || 'Processing'}`, percent: 15, timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      if (type === 'task_started') {
        const progressStr = taskBannerData.progress || '1/1'
        const [current, total] = progressStr.split('/').map(Number)
        const progress = { step: `Step ${current}/${total}`, detail: taskBannerData.task_name || 'Processing', percent: Math.round(((current - 0.5) / total) * 100), timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      if (type === 'task_completed') {
        const progressStr = taskBannerData.progress || '1/1'
        const [current, total] = progressStr.split('/').map(Number)
        const progress = { step: `Step ${current}/${total}`, detail: `Completed: ${taskBannerData.task_name || 'Task'}`, percent: Math.round((current / total) * 100), timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      if (type === 'agentic_start') {
        const progress = { step: 'AI', detail: 'Deep analysis...', percent: 30, timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      if (type === 'agentic_action') {
        const toolName = taskBannerData.tool?.replace(/_/g, ' ') || 'Analysis'
        const thought = taskBannerData.thought?.substring(0, 60) || ''
        const detail = thought ? `${toolName}: ${thought}...` : toolName
        const progress = { step: 'AI Analysis', detail, percent: 50, timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      // Handle model selection
      if (type === 'model_selection') {
        const modelName = taskBannerData.model || 'AI Model'
        const progress = { 
          step: 'Selecting Model', 
          detail: `Using ${modelName}${taskBannerData.reasoning ? ': ' + taskBannerData.reasoning.substring(0, 50) + '...' : ''}`, 
          percent: 20, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      // Handle agentic observation
      if (type === 'agentic_observation') {
        const observation = taskBannerData.observation?.substring(0, 70) || 'Processing data...'
        const progress = { step: 'Processing', detail: observation, percent: 60, timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      // Handle any other task types dynamically
      if (taskBannerData.task_name || taskBannerData.message || taskBannerData.content) {
        const detail = taskBannerData.task_name || taskBannerData.message || taskBannerData.content
        const progressStr = taskBannerData.progress || ''
        const percent = taskBannerData.percent || taskBannerData.progress_percent || 0
        const step = progressStr || 'Processing'
        const progress = { step, detail: detail.substring(0, 80), percent, timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
      }
    }
  }, [taskBannerData])

  const [userLocation, setUserLocation] = useState(null)
  const [locationLabel, setLocationLabel] = useState('Detecting…')
  const [locationSource, setLocationSource] = useState('ip')
  const [gpsEnabled, setGpsEnabled] = useState(false)
  const [locationError, setLocationError] = useState(null)
  const geolocationWatchIdRef = useRef(null)
  const lastReverseGeocodeRef = useRef({ t: 0, lat: null, lng: null })

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

  useEffect(() => {
    let cancelled = false

    const fetchIpLocation = async () => {
      try {
        const resp = await fetch('https://ipapi.co/json/')
        if (!resp.ok) return
        const data = await resp.json()
        if (cancelled) return

        const lat = Number(data.latitude)
        const lng = Number(data.longitude)
        const city = data.city
        const region = data.region

        if (Number.isFinite(lat) && Number.isFinite(lng)) {
          setUserLocation({ lat, lng, accuracy: null })
          setLocationSource('ip')
          setLocationError(null)
          if (city && region) setLocationLabel(`${city}, ${region}`)
          else if (city) setLocationLabel(city)
          else setLocationLabel(`${lat.toFixed(3)}, ${lng.toFixed(3)}`)
        }
      } catch (err) {
        if (!cancelled) setLocationError('ip_location_failed')
      }
    }

    const promptForGeolocation = () => {
      if (!navigator.geolocation) {
        fetchIpLocation()
        return
      }

      setLocationLabel('Requesting permission…')
      
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          if (cancelled) return
          const lat = Number(pos.coords.latitude)
          const lng = Number(pos.coords.longitude)
          const accuracy = Number(pos.coords.accuracy)
          
          if (Number.isFinite(lat) && Number.isFinite(lng)) {
            setUserLocation({ lat, lng, accuracy: Number.isFinite(accuracy) ? accuracy : null })
            setLocationSource('gps')
            setLocationError(null)
            setGpsEnabled(true)
            reverseGeocode(lat, lng)
            console.log('📍 Browser geolocation granted:', { lat, lng, accuracy })
          }
        },
        (err) => {
          if (cancelled) return
          console.log('📍 Browser geolocation denied or failed, falling back to IP')
          setLocationError(err?.code === 1 ? 'permission_denied' : 'gps_failed')
          fetchIpLocation()
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      )
    }

    promptForGeolocation()

    return () => {
      cancelled = true
    }
  }, [])

  const reverseGeocode = async (lat, lng) => {
    const now = Date.now()
    const prev = lastReverseGeocodeRef.current

    const shouldThrottle = prev.t && now - prev.t < 30000
    const movedEnough =
      prev.lat == null ||
      prev.lng == null ||
      Math.abs(prev.lat - lat) > 0.001 ||
      Math.abs(prev.lng - lng) > 0.001

    if (shouldThrottle && !movedEnough) return

    lastReverseGeocodeRef.current = { t: now, lat, lng }

    try {
      const resp = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}`
      )
      if (!resp.ok) return
      const data = await resp.json()
      const a = data.address || {}
      const label =
        a.suburb ||
        a.neighbourhood ||
        a.village ||
        a.town ||
        a.city ||
        a.county ||
        a.state
      if (label) setLocationLabel(label)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    if (!gpsEnabled) {
      if (geolocationWatchIdRef.current != null && navigator.geolocation) {
        try {
          navigator.geolocation.clearWatch(geolocationWatchIdRef.current)
        } catch {}
        geolocationWatchIdRef.current = null
      }
      return
    }

    if (!navigator.geolocation) {
      setLocationError('geolocation_unavailable')
      setGpsEnabled(false)
      return
    }

    setLocationError(null)
    setLocationSource('gps')

    geolocationWatchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude)
        const lng = Number(pos.coords.longitude)
        const accuracy = Number(pos.coords.accuracy)
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return

        setUserLocation({ lat, lng, accuracy: Number.isFinite(accuracy) ? accuracy : null })
        reverseGeocode(lat, lng)
      },
      (err) => {
        setLocationError(err?.code === 1 ? 'permission_denied' : 'gps_failed')
        setGpsEnabled(false)
        setLocationSource('ip')
      },
      {
        enableHighAccuracy: true,
        maximumAge: 15000,
        timeout: 10000
      }
    )

    return () => {
      if (geolocationWatchIdRef.current != null) {
        try {
          navigator.geolocation.clearWatch(geolocationWatchIdRef.current)
        } catch {}
        geolocationWatchIdRef.current = null
      }
    }
  }, [gpsEnabled])

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

  // Handle streaming task data from chat
  const handleTaskStreaming = (data) => {
    setTaskBannerData(data)
    setShowTaskBanner(true)
    if (data?.query) {
      setCurrentQuery(data.query)
    }
    // Hide banner when done (after a delay)
    if (data?.type === 'done') {
      setTimeout(() => setShowTaskBanner(false), 3000)
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
      <div className="h-12 bg-slate-800/95 border-b border-slate-700 px-4 flex items-center shrink-0 backdrop-blur-sm">
        {/* Left Section - Logo & Location */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-bold text-lg hidden sm:block">Valora AI</span>
          <span className="text-slate-400 text-xs ml-2 hidden lg:block">City Intelligence</span>

          <button
            onClick={() => setGpsEnabled(v => !v)}
            className={`ml-2 flex items-center gap-2 px-2 py-1 rounded-full border transition text-xs ${
              gpsEnabled
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200 hover:bg-emerald-500/20'
                : 'bg-slate-700/40 border-slate-600 text-slate-200 hover:bg-slate-700/60'
            }`}
            title={
              userLocation?.lat && userLocation?.lng
                ? `${locationSource.toUpperCase()} · ${userLocation.lat.toFixed(5)}, ${userLocation.lng.toFixed(5)}${userLocation.accuracy ? ` · ±${Math.round(userLocation.accuracy)}m` : ''}`
                : 'Detect your location'
            }
          >
            {gpsEnabled ? <LocateFixed className="w-3.5 h-3.5" /> : <MapPin className="w-3.5 h-3.5" />}
            <span className="max-w-[120px] xl:max-w-[180px] truncate hidden sm:block">{locationLabel}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${gpsEnabled ? 'bg-emerald-500/20 text-emerald-200' : 'bg-slate-600/40 text-slate-300'}`}>
              {gpsEnabled ? 'GPS' : 'IP'}
            </span>
          </button>

          {gpsEnabled && agentData?.weather?.metrics && !agentData?.weather?.error && (
            <div className="hidden md:flex ml-2 items-center gap-2 px-2 py-1 rounded-full border border-slate-600 bg-slate-700/40 text-xs text-slate-200">
              <Cloud className="w-3.5 h-3.5 text-blue-300" />
              <span className="capitalize text-slate-200 hidden lg:block">{agentData.weather.metrics.conditionDesc || '—'}</span>
              <span className="text-slate-400 hidden lg:block">·</span>
              <span className="font-mono text-slate-200">
                {Number.isFinite(agentData.weather.metrics.tempC) ? `${agentData.weather.metrics.tempC.toFixed(0)}°C` : '—'}
              </span>
            </div>
          )}
        </div>

        {/* Center Section - Task Progress (Adaptive & Centered) */}
        <div className="flex-1 flex justify-center px-4 min-w-0">
          {lastTaskProgress && (
            <button
              onClick={() => setShowFloatingBanner(!showFloatingBanner)}
              className={`flex items-center gap-3 px-4 py-1.5 rounded-lg transition-all duration-300 group w-full max-w-2xl relative overflow-hidden ${
                lastTaskProgress.percent > 0 && lastTaskProgress.percent < 100 && !isTaskCancelled
                  ? 'bg-slate-900 border border-violet-500/60'
                  : 'bg-slate-800 border border-slate-700 hover:border-violet-500/40'
              }`}
              title={showFloatingBanner ? "Hide detailed view" : "Click for detailed view"}
            >
              {/* Animated Inner Glow - Processing Effect */}
              {lastTaskProgress.percent > 0 && lastTaskProgress.percent < 100 && !isTaskCancelled && (
                <>
                  {/* Rolling gradient background */}
                  <div 
                    className="absolute inset-0 rounded-lg opacity-30"
                    style={{
                      background: 'linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.4), rgba(168, 85, 247, 0.4), rgba(139, 92, 246, 0.4), transparent)',
                      backgroundSize: '200% 100%',
                      animation: 'gradient-roll 2s linear infinite'
                    }}
                  />
                  {/* Pulsing background glow */}
                  <div 
                    className="absolute inset-0 rounded-lg"
                    style={{
                      background: 'radial-gradient(ellipse at center, rgba(139, 92, 246, 0.15) 0%, transparent 70%)',
                      animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                    }}
                  />
                  {/* Animated border glow */}
                  <div 
                    className="absolute inset-0 rounded-lg"
                    style={{
                      boxShadow: 'inset 0 0 20px rgba(139, 92, 246, 0.2), inset 0 0 40px rgba(139, 92, 246, 0.1)',
                      animation: 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                    }}
                  />
                  {/* Corner accents */}
                  <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-violet-500/60 rounded-tl-lg" 
                       style={{ animation: 'pulse 2s infinite' }} />
                  <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-violet-500/60 rounded-tr-lg"
                       style={{ animation: 'pulse 2s infinite 0.5s' }} />
                  <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-violet-500/60 rounded-bl-lg"
                       style={{ animation: 'pulse 2s infinite 1s' }} />
                  <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-violet-500/60 rounded-br-lg"
                       style={{ animation: 'pulse 2s infinite 1.5s' }} />
                </>
              )}

              {/* Progress Ring with Glow */}
              <div className="relative w-7 h-7 flex-shrink-0 z-10">
                {/* Glow Effect */}
                {lastTaskProgress.percent > 0 && lastTaskProgress.percent < 100 && !isTaskCancelled && (
                  <div className="absolute inset-0 rounded-full bg-violet-500/40 animate-pulse" />
                )}
                <svg className="w-full h-full -rotate-90 relative z-10" viewBox="0 0 28 28">
                  <circle cx="14" cy="14" r="11" className="stroke-slate-700 fill-none" strokeWidth="2.5" />
                  <circle
                    cx="14" cy="14" r="11"
                    fill="none"
                    stroke={isTaskCancelled ? '#ef4444' : lastTaskProgress.percent === 100 ? '#10b981' : '#8b5cf6'}
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeDasharray={2 * Math.PI * 11}
                    strokeDashoffset={2 * Math.PI * 11 * (1 - lastTaskProgress.percent / 100)}
                    className="transition-all duration-500"
                    style={{
                      filter: lastTaskProgress.percent > 0 && lastTaskProgress.percent < 100 && !isTaskCancelled
                        ? 'drop-shadow(0 0 4px rgba(139, 92, 246, 0.6))'
                        : 'none'
                    }}
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-white z-20">
                  {lastTaskProgress.percent}%
                </span>
              </div>

              {/* Task Info - Single Line */}
              <div className="flex-1 min-w-0 flex flex-col justify-center z-10">
                <div className="flex items-center gap-2">
                  {/* Step counter */}
                  <span className={`text-sm font-semibold whitespace-nowrap ${
                    isTaskCancelled ? 'text-red-400' :
                    lastTaskProgress.percent === 100 ? 'text-emerald-400' : 'text-violet-200'
                  }`}>
                    {lastTaskProgress.step}
                  </span>

                  {/* Separator */}
                  <span className="text-slate-600">|</span>

                  {/* Task detail */}
                  <span className="text-sm text-slate-300 truncate flex-1">
                    {lastTaskProgress.detail}
                  </span>

                  {/* Running indicator */}
                  {lastTaskProgress.percent > 0 && lastTaskProgress.percent < 100 && !isTaskCancelled && (
                    <span className="flex gap-0.5 flex-shrink-0">
                      <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 bg-slate-700/50 rounded-full mt-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isTaskCancelled ? 'bg-red-500' :
                      lastTaskProgress.percent === 100 ? 'bg-emerald-500' : 'bg-violet-500'
                    }`}
                    style={{ width: `${lastTaskProgress.percent}%` }}
                  />
                </div>
              </div>

              {/* Right side - step count and toggle */}
              <div className="flex items-center gap-2 flex-shrink-0 z-10">
                {taskHistory.length > 0 && (
                  <span className="text-[10px] text-slate-500 font-mono bg-slate-900/50 px-1.5 py-0.5 rounded whitespace-nowrap">
                    {taskHistory.filter(t => t.percent === 100).length}/{taskHistory.length}
                  </span>
                )}
                <ChevronRight
                  className={`w-4 h-4 text-violet-400 transition-transform duration-200 ${showFloatingBanner ? 'rotate-90' : ''}`}
                />
              </div>
            </button>
          )}
        </div>

        {/* Right Section - User Menu */}
        <div className="flex items-center gap-2 shrink-0">
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

      {/* Top Task Banner - Floating on map (always expanded) */}
      <Suspense fallback={null}>
        <TopTaskBanner
          query={currentQuery}
          streamingData={taskBannerData}
          isVisible={showTaskBanner && showFloatingBanner}
          onClose={() => setShowFloatingBanner(false)}
          taskProgress={lastTaskProgress}
        />
      </Suspense>

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
                <Suspense fallback={<ComponentLoader />}>
                  <AnalysisPanel 
                    agentData={agentData} 
                    setAgentData={setAgentData}
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    fontSize={analysisFontSize}
                    liveAnalysis={liveAnalysis}
                    isFullscreen={isAnalysisFullscreen}
                  />
                </Suspense>
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
          <Suspense fallback={<ComponentLoader />}>
            <OnlineOSMMap
              onAnalysisUpdate={handleAnalysisUpdate}
              agentData={agentData}
              setAgentData={setAgentData}
              toggleMapFullscreen={toggleMapFullscreen}
              isMapFullscreen={isMapFullscreen}
              userLocation={userLocation}
              gpsEnabled={gpsEnabled}
            />
          </Suspense>
        </div>

        {/* Right Chat Panel */}
        <div 
          className="h-full bg-slate-800 border-l border-slate-700 flex flex-col transition-all duration-300 relative"
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
                <Suspense fallback={<ComponentLoader />}>
                  <EnhancedChatPanel 
                    agentData={agentData} 
                    setAgentData={setAgentData} 
                    fontSize={chatFontSize}
                    userLocation={userLocation}
                    locationLabel={locationLabel}
                    locationSource={locationSource}
                    onTaskStreaming={handleTaskStreaming}
                    onSidebarOpen={() => setChatWidth('wide')}
                    onSidebarClose={() => setChatWidth('narrow')}
                  />
                </Suspense>
              </div>
            </>
          ) : (
            <button
              onClick={() => setIsChatOpen(true)}
              className="h-full w-full flex items-center justify-end pr-2 text-slate-400 hover:text-white hover:bg-slate-700 transition"
              title="Open Chat"
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
      <Suspense fallback={null}>
        <PaymentCheckout
          isOpen={showPaymentCheckout}
          onClose={() => setShowPaymentCheckout(false)}
          type={paymentType}
        />
      </Suspense>

      {/* Cinema Mode Overlay */}
      <Suspense fallback={null}>
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
      </Suspense>
    </div>
  )
}
