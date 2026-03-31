import { useEffect, useRef, useState, lazy, Suspense } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useLocation } from '../contexts/LocationContext'
import { Sparkles, Maximize2, Minimize2, X, ChevronRight, ChevronLeft, ChevronDown, TrendingUp, FileText, StickyNote, Settings, Brain, Expand, Shrink, LogOut, User, Crown, Zap, MapPin, LocateFixed, Cloud, Loader2, Activity, CheckCircle2, Circle, AlertTriangle, Percent, Building, Compass, Database, Presentation, Eye, Download, Users } from 'lucide-react'

import { API_URL } from '../apiConfig'
import CreditBalance from './CreditBalance'
import TaskProgressBar from './TaskProgressBar'
import OnboardingModal from './OnboardingModal'

// Lazy load heavy components
const OnlineOSMMap = lazy(() => import('../spatial/OnlineOSMMap'))
const SmartPanel = lazy(() => import('./SmartPanel'))
const EnhancedChatPanel = lazy(() => import('./chat/EnhancedChatPanel'))

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
  const { user, token, logout, isAdmin, loading: authLoading } = useAuth()
  const { t } = useLanguage()
  const { location, coordinates, locality, place, updateLocationFromCoordinates, setExplicitLocation } = useLocation()
  const [agentData, setAgentData] = useState({})
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('smart')
  const [smartPanelActiveTab, setSmartPanelActiveTab] = useState('free_analysis')
  const [analysisWidth, setAnalysisWidth] = useState('narrow') // narrow, wide, or fullscreen
  const [chatWidth, setChatWidth] = useState('narrow') // narrow or wide
  const [userTier, setUserTier] = useState('free') // User's credit tier
  const [tierLoaded, setTierLoaded] = useState(false) // Track if tier has been fetched
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [showPaymentCheckout, setShowPaymentCheckout] = useState(false)
  const [paymentType, setPaymentType] = useState('subscription') // 'subscription' or 'topup'
  const [liveAnalysis, setLiveAnalysis] = useState(null) // Real-time analysis from AI
  const [isAnalysisFullscreen, setIsAnalysisFullscreen] = useState(false) // Fullscreen mode for deep analysis
  const [isChatFullscreen, setIsChatFullscreen] = useState(false) // Fullscreen mode for chat
  const [isMapFullscreen, setIsMapFullscreen] = useState(false) // Fullscreen mode for map
  
  // Onboarding modal state - show for new users
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [userPreferences, setUserPreferences] = useState(null)
  
  // Report generation task state
  const [reportTask, setReportTask] = useState(null) // { taskId, locality, creditsCharged }
  
  // Check if user is new (no previous sessions) on mount
  useEffect(() => {
    const onboardingComplete = localStorage.getItem('valora_onboarding_complete')
    const savedPreferences = localStorage.getItem('valora_preferences')
    
    if (!onboardingComplete && !savedPreferences) {
      // New user - show onboarding
      setShowOnboarding(true)
    } else if (savedPreferences) {
      // Existing user - load preferences
      try {
        setUserPreferences(JSON.parse(savedPreferences))
      } catch (e) {
        console.warn('[MainApp] Failed to parse saved preferences:', e)
      }
    }
  }, [])
  
  // Handle onboarding completion
  const handleOnboardingComplete = (preferences) => {
    setUserPreferences(preferences)
    setShowOnboarding(false)
  }
  
  // Handle top-up purchase
  const handleTopUp = async (packageId) => {
    try {
      const userId = user?.email || user?.id || 'anonymous'
      const response = await fetch(`${API_URL}/api/credits/top-up`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, package: packageId })
      })
      
      if (response.ok) {
        const data = await response.json()
        setShowUpgradeModal(false)
        // Refresh credit balance by triggering a re-render
        window.dispatchEvent(new CustomEvent('valora-credits-deducted', { 
          detail: { remaining_credits: data.new_balance } 
        }))
      }
    } catch (error) {
      console.error('Top-up failed:', error)
    }
  }
  
  // Handle subscription
  const handleSubscribe = async () => {
    try {
      const userId = user?.email || user?.id || 'anonymous'
      const response = await fetch(`${API_URL}/api/payments/create-checkout-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, tier: 'pro' })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.url) {
          // Redirect to Stripe checkout or show demo success
          if (data.demo_mode) {
            setShowUpgradeModal(false)
            window.dispatchEvent(new CustomEvent('valora-credits-deducted', { 
              detail: { remaining_credits: 500 } 
            }))
          } else {
            window.open(data.url, '_blank')
          }
        }
      }
    } catch (error) {
      console.error('Subscription failed:', error)
    }
  }
  
  // Cinema mode for simulations and storytelling
  const [isCinemaMode, setIsCinemaMode] = useState(false)
  const [cinemaNarration, setCinemaNarration] = useState('')
  const [isCinemaPaused, setIsCinemaPaused] = useState(false)
  
  // Top task banner state
  const [taskBannerData, setTaskBannerData] = useState(null)
  const [showTaskBanner, setShowTaskBanner] = useState(false)
  // Load user preference from localStorage or default to hidden
  const [showFloatingBanner, setShowFloatingBanner] = useState(() => {
    const saved = localStorage.getItem('valora_showFloatingBanner')
    return saved !== null ? saved === 'true' : false
  })
  
  // Persist showFloatingBanner preference to localStorage
  useEffect(() => {
    localStorage.setItem('valora_showFloatingBanner', String(showFloatingBanner))
  }, [showFloatingBanner])
  const [currentQuery, setCurrentQuery] = useState('')
  const [lastTaskProgress, setLastTaskProgress] = useState(null)
  const [isTaskCancelled, setIsTaskCancelled] = useState(false)
  const [taskHistory, setTaskHistory] = useState([]) // Track task history

  // Update last task progress when taskBannerData changes
  useEffect(() => {
    if (taskBannerData) {
      const type = taskBannerData.type
      
      // Multi-Stage LLM Execution Events
      if (type === 'orchestration_start') {
        setIsTaskCancelled(false)
        setTaskHistory([]) // Clear history for new query
        setShowTaskBanner(true)
        setShowFloatingBanner(true) // Auto-show floating banner
        setLastTaskProgress({ 
          step: 'Starting', 
          detail: 'Initializing analysis...', 
          percent: 0, 
          timestamp: Date.now() 
        })
        return
      }
      
      if (type === 'stage_start') {
        const stageDetails = {
          'understand': { step: 'Understanding', detail: 'Analyzing your request...', percent: 5 },
          'plan': { step: 'Planning', detail: 'Creating execution plan...', percent: 20 },
          'execute': { step: 'Executing', detail: 'Running tasks...', percent: 40 },
          'validate': { step: 'Validating', detail: 'Verifying results...', percent: 75 },
          'synthesize': { step: 'Synthesizing', detail: 'Generating response...', percent: 90 }
        }
        const stageInfo = stageDetails[taskBannerData.stage] || { step: 'Processing', detail: taskBannerData.message || 'Working...', percent: 50 }
        const progress = { ...stageInfo, timestamp: Date.now() }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'stage_complete') {
        const stageProgress = {
          'understand': 20,
          'plan': 40,
          'execute': 70,
          'validate': 85,
          'synthesize': 95
        }
        const percent = stageProgress[taskBannerData.stage] || 50
        const progress = { 
          step: taskBannerData.stage?.charAt(0).toUpperCase() + taskBannerData.stage?.slice(1), 
          detail: taskBannerData.reasoning || 'Stage complete', 
          percent, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'query_understood') {
        const intent = taskBannerData.intent?.primary || taskBannerData.intent || 'query'
        const progress = { 
          step: 'Understood', 
          detail: `Intent: ${intent.toString().replace(/_/g, ' ')}`, 
          percent: 20, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'task_graph') {
        const taskCount = taskBannerData.tasks?.length || 0
        const progress = { 
          step: 'Planned', 
          detail: `${taskCount} tasks planned`, 
          percent: 35, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'tasks_executed') {
        const executed = taskBannerData.tasks_executed || 0
        const progress = { 
          step: 'Executed', 
          detail: `${executed} tasks completed`, 
          percent: 70, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'validation_result') {
        const isComplete = taskBannerData.is_complete
        const coverage = Math.round((taskBannerData.coverage_score || 1) * 100)
        const progress = { 
          step: 'Validated', 
          detail: isComplete ? 'Results verified' : 'Filling gaps...', 
          percent: 85, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'response_synthesized') {
        const insights = taskBannerData.key_insights?.length || 0
        const progress = { 
          step: 'Complete', 
          detail: `Generated response with ${insights} insights`, 
          percent: 95, 
          timestamp: Date.now() 
        }
        setLastTaskProgress(progress)
        setTaskHistory(prev => [...prev.slice(-4), progress])
        return
      }
      
      if (type === 'orchestration_complete') {
        setLastTaskProgress({ step: 'Done', detail: 'Complete!', percent: 100, timestamp: Date.now() })
        setIsTaskCancelled(false)
        setTaskHistory(prev => [...prev.slice(-4), { step: 'Done', detail: 'Complete!', percent: 100, timestamp: Date.now() }])
        // Auto-clear after 3 seconds
        setTimeout(() => setLastTaskProgress(null), 3000)
        return
      }
      
      // Legacy Events (kept for backward compatibility)
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
        // Auto-switch to Smart tab when query completes
        setActiveTab('smart')
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

  // Fetch user tier from credits API
  useEffect(() => {
    const fetchUserTier = async () => {
      const userId = user?.email || user?.id
      if (!userId) {
        // If no user, mark tier as loaded (will use default 'free')
        setTierLoaded(true)
        return
      }
      
      try {
        const resp = await fetch(`${API_URL}/api/credits/balance?user_id=${userId}`)
        if (resp.ok) {
          const data = await resp.json()
          console.log('[MainApp] Fetched user tier:', data.tier, 'for user:', userId)
          setUserTier(data.tier || 'free')
        }
      } catch (err) {
        console.warn('Failed to fetch user tier:', err)
      } finally {
        setTierLoaded(true)
      }
    }
    
    fetchUserTier()
    // Refresh tier every minute
    const interval = setInterval(fetchUserTier, 60000)
    return () => clearInterval(interval)
  }, [user?.email, user?.id])
  
  // App is ready when auth is loaded and tier is fetched
  const appReady = !authLoading && tierLoaded
  
  // Sync location from agentData (viewportAnalysis) to LocationContext
  useEffect(() => {
    const viewportAnalysis = agentData?.viewportAnalysis
    const mapCenter = agentData?.mapCenter
    
    // If we have viewportAnalysis with coordinates, update the location context
    if (viewportAnalysis?.coordinates?.lat && viewportAnalysis?.coordinates?.lng) {
      setExplicitLocation({
        coordinates: viewportAnalysis.coordinates,
        locality: viewportAnalysis.area_name,
        place: viewportAnalysis.area_name
      })
    } else if (mapCenter?.lat && mapCenter?.lng) {
      // Fallback to mapCenter coordinates
      setExplicitLocation({
        coordinates: mapCenter,
        locality: viewportAnalysis?.area_name || locality,
        place: viewportAnalysis?.area_name || place
      })
    }
  }, [agentData?.viewportAnalysis, agentData?.mapCenter, setExplicitLocation, locality, place])
  
  // Update agentData.mapCenter when location changes
  useEffect(() => {
    if (coordinates?.lat && coordinates?.lng) {
      setAgentData(prev => ({
        ...prev,
        mapCenter: coordinates
      }))
    }
  }, [coordinates])
  
  // Switch to verdict tab when analysis is performed
  useEffect(() => {
    if (agentData?.buildingAnalysis || agentData?.viewportAnalysis || agentData?.explainability) {
      setSmartPanelActiveTab('decision_verdict')
    }
  }, [agentData?.buildingAnalysis, agentData?.viewportAnalysis, agentData?.explainability])
  
  // Listen for free analysis completion to switch to verdict tab
  useEffect(() => {
    const handleFreeAnalysisComplete = (e) => {
      setSmartPanelActiveTab('decision_verdict')
    }
    window.addEventListener('valora-free-analysis-complete', handleFreeAnalysisComplete)
    return () => window.removeEventListener('valora-free-analysis-complete', handleFreeAnalysisComplete)
  }, [])
    
  useEffect(() => {
    const handleUICommand = (e) => {
      const { action, value, panel, tab } = e.detail || {}

      const targetTab = value || tab

      if (action === 'switchTab' && targetTab) {
        // Map old tab names to new smart panel tabs
        if (targetTab === 'analysis' || targetTab === 'market' || targetTab === 'city' || targetTab === 'insights') {
          setActiveTab('smart')
          setSmartPanelActiveTab('decision_verdict')
        } else if (targetTab === 'agent' || targetTab === 'agent_control') {
          setActiveTab('smart')
          setSmartPanelActiveTab('agent_control')
        } else if (targetTab === 'verdict' || targetTab === 'decision_verdict') {
          setActiveTab('smart')
          setSmartPanelActiveTab('decision_verdict')
        } else {
          setActiveTab(targetTab)
        }
      }

      // Handle live analysis updates from AI
      if (action === 'updateAnalysis') {
        setLiveAnalysis(e.detail.analysis)
        setActiveTab('smart') // Auto-switch to smart panel
        setSmartPanelActiveTab('decision_verdict')
        setIsAnalysisOpen(true) // Ensure panel is open
      }

      if (action === 'openPanel') {
        if ((value || panel) === 'analysis' || (value || panel) === 'insights' || (value || panel) === 'smart') setIsAnalysisOpen(true)
        if ((value || panel) === 'agent' || (value || panel) === 'agent_control') {
          setIsAnalysisOpen(true)
          setSmartPanelActiveTab('agent_control')
        }
        if ((value || panel) === 'chat') setIsChatOpen(true)
      }

      if (action === 'closePanel') {
        if ((value || panel) === 'analysis' || (value || panel) === 'insights' || (value || panel) === 'smart') setIsAnalysisOpen(false)
        if ((value || panel) === 'chat') setIsChatOpen(false)
      }

      // Agent-controlled fullscreen expansion for deep analysis
      if (action === 'expandAnalysis' || action === 'fullscreenAnalysis') {
        setIsAnalysisFullscreen(true)
        setIsAnalysisOpen(true)
        setActiveTab('smart')
        setSmartPanelActiveTab(targetTab || 'decision_verdict')
      }

      if (action === 'collapseAnalysis' || action === 'exitFullscreen') {
        setIsAnalysisFullscreen(false)
      }

      // Toggle comparison mode
      if (action === 'showComparison') {
        setActiveTab('smart')
        setSmartPanelActiveTab('decision_verdict')
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
  
  // Handle upgrade request from SmartTabs
  useEffect(() => {
    const handleUpgradeRequest = () => {
      setShowUpgradeModal(true)
    }
    
    window.addEventListener('valora-upgrade-request', handleUpgradeRequest)
    return () => window.removeEventListener('valora-upgrade-request', handleUpgradeRequest)
  }, [])
  
  // Listen for report task started
  useEffect(() => {
    const handleReportTaskStarted = (e) => {
      const { taskId, locality, creditsCharged } = e.detail || {}
      if (taskId) {
        setReportTask({ taskId, locality, creditsCharged })
      }
    }
    
    window.addEventListener('valora-report-task-started', handleReportTaskStarted)
    return () => window.removeEventListener('valora-report-task-started', handleReportTaskStarted)
  }, [])

  const handleAnalysisUpdate = (analysis) => {
    if (analysis?.coordinates) {
      setAgentData(prev => ({ ...prev, clickedLocation: analysis.coordinates }))
    }
    // Switch to verdict tab when analysis is performed
    if (analysis?.viewportAnalysis || analysis?.buildingAnalysis) {
      setSmartPanelActiveTab('decision_verdict')
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
    if (!isAnalysisOpen) return '48px' // Collapsed tab sidebar width
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
      {/* Loading Overlay - Show while app is initializing */}
      {!appReady && (
        <div className="absolute inset-0 z-[100] bg-slate-900/95 backdrop-blur-md flex flex-col items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center animate-pulse">
              <Sparkles className="w-10 h-10 text-white" />
            </div>
            <div className="text-white font-bold text-xl">Valora AI</div>
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Initializing...</span>
            </div>
          </div>
        </div>
      )}
      
      {/* Onboarding Modal for new users */}
      <OnboardingModal 
        isOpen={showOnboarding} 
        onComplete={handleOnboardingComplete} 
      />
      
      {/* Header - High z-index for dropdowns (above map's z-50) */}
      <div className="h-12 bg-slate-800/95 border-b border-slate-700 px-4 flex items-center shrink-0 backdrop-blur-sm relative z-[60]">
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

        {/* Center Section - Dynamic Task Progress */}
        <div className="flex-1 flex justify-center px-4 min-w-0">
          {lastTaskProgress && (
            <button
              onClick={() => setShowFloatingBanner(!showFloatingBanner)}
              className={`flex items-center gap-2 px-3 py-1 rounded-full transition-all duration-200 w-full max-w-lg ${
                lastTaskProgress.percent > 0 && lastTaskProgress.percent < 100 && !isTaskCancelled
                  ? 'bg-violet-500/15 border border-violet-500/30'
                  : lastTaskProgress.percent === 100 
                    ? 'bg-emerald-500/15 border border-emerald-500/30'
                    : 'bg-slate-800/50 border border-slate-700/50 hover:border-slate-600'
              }`}
              title={showFloatingBanner ? "Hide details" : "Show details"}
            >
              {/* Animated Status Dot */}
              <div className="relative flex-shrink-0">
                {isTaskCancelled ? (
                  <Circle className="w-3 h-3 text-red-400" />
                ) : lastTaskProgress.percent === 100 ? (
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                ) : (
                  <>
                    <Loader2 className="w-3 h-3 text-violet-400 animate-spin" />
                    <span className="absolute inset-0 rounded-full bg-violet-400/30 animate-ping" />
                  </>
                )}
              </div>

              {/* Dynamic Status Text */}
              <div className="flex-1 min-w-0 overflow-hidden">
                <div className={`text-xs font-medium text-left whitespace-nowrap ${
                  String(lastTaskProgress.detail || lastTaskProgress.step || '').length > 40 
                    ? 'animate-marquee' 
                    : ''
                }`}>
                  <span className={`${
                    isTaskCancelled ? 'text-red-400' :
                    lastTaskProgress.percent === 100 ? 'text-emerald-400' : 'text-slate-200'
                  }`}>
                    {typeof lastTaskProgress.detail === 'string' 
                      ? lastTaskProgress.detail 
                      : typeof lastTaskProgress.step === 'string'
                        ? lastTaskProgress.step
                        : 'Processing...'}
                  </span>
                </div>
              </div>

              {/* Compact Progress Indicator */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div className="w-12 h-0.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      isTaskCancelled ? 'bg-red-400' :
                      lastTaskProgress.percent === 100 ? 'bg-emerald-400' : 'bg-violet-400'
                    }`}
                    style={{ width: `${lastTaskProgress.percent}%` }}
                  />
                </div>
                <span className={`text-[9px] font-mono ${
                  isTaskCancelled ? 'text-red-400' :
                  lastTaskProgress.percent === 100 ? 'text-emerald-400' : 'text-slate-500'
                }`}>
                  {lastTaskProgress.percent}%
                </span>
              </div>

              {/* Expand Arrow */}
              <ChevronRight
                className={`w-3 h-3 text-slate-500 transition-transform duration-200 flex-shrink-0 ${showFloatingBanner ? 'rotate-90' : ''}`}
              />
            </button>
          )}
        </div>

        {/* Right Section - User Menu */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Credit Balance Widget */}
          <CreditBalance 
            userId={user?.email || user?.id || 'anonymous'}
            onUpgrade={() => setShowUpgradeModal(true)}
          />

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 hover:text-white rounded-lg border border-slate-600 transition text-xs"
            >
              <User className="w-3.5 h-3.5" />
              <span className="max-w-[100px] truncate">{user?.name || user?.email}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>
            
            {showUserMenu && (
              <>
                {/* Backdrop to close menu */}
                <div className="fixed inset-0 z-[90]" onClick={() => setShowUserMenu(false)} />
                
                {/* Dropdown Menu */}
                <div className="absolute right-0 top-full mt-1 w-60 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-[100] overflow-hidden">
                  {/* User Info Header */}
                  <div className="p-3 border-b border-slate-700 bg-slate-800/80">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
                        {(user?.name || user?.email || 'U')[0].toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-medium text-sm truncate">{user?.name || 'User'}</p>
                        <p className="text-slate-400 text-xs truncate">{user?.email}</p>
                      </div>
                    </div>
                    {user?.company && (
                      <p className="text-slate-500 text-xs truncate mt-2">{user.company}</p>
                    )}
                  </div>
                  
                  {/* Menu Items */}
                  <div className="p-2">
                    {/* Documents */}
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        setIsAnalysisOpen(true);
                        setActiveTab('docs');
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-slate-300 hover:bg-slate-700/50 rounded-lg transition text-sm"
                    >
                      <FileText className="w-4 h-4" />
                      {t('documents') || 'Documents'}
                    </button>
                    
                    {/* Notes */}
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        setIsAnalysisOpen(true);
                        setActiveTab('notes');
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-slate-300 hover:bg-slate-700/50 rounded-lg transition text-sm"
                    >
                      <StickyNote className="w-4 h-4" />
                      {t('notes') || 'Notes'}
                    </button>
                    
                    {/* Divider */}
                    <div className="my-1 border-t border-slate-700/50" />
                    
                    {/* Admin Panel */}
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        window.open('#/admin', '_blank');
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-slate-300 hover:bg-slate-700/50 rounded-lg transition text-sm"
                    >
                      <Settings className="w-4 h-4" />
                      {t('adminPanel') || 'Admin Panel'}
                    </button>
                    
                    {/* Divider */}
                    <div className="my-1 border-t border-slate-700/50" />
                    
                    {/* Sign Out */}
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        logout();
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 rounded-lg transition text-sm"
                    >
                      <LogOut className="w-4 h-4" />
                      {t('signOut') || 'Sign Out'}
                    </button>
                  </div>
                </div>
              </>
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
          taskHistory={taskHistory}
        />
      </Suspense>

      {/* Main Content - 3 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Analysis Panel */}
        <div 
          className="h-full bg-slate-800 border-r border-slate-700 flex flex-col transition-all duration-300 z-50"
          style={{
            width: getAnalysisWidth(),
            minWidth: isAnalysisOpen ? (isAnalysisFullscreen ? '600px' : '280px') : '48px',
            flexShrink: 0
          }}
        >
          {isAnalysisOpen ? (
            <>
              {/* Panel Header with controls */}
              <div className="p-2 border-b border-slate-700 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-bold text-white">Smart Report</span>
                </div>
                <div className="flex gap-1 ml-2">
                  {/* Report Task Progress Bar - Show when task is active */}
                  {reportTask?.taskId && (
                    <div className="mr-2 min-w-[200px]">
                      <TaskProgressBar
                        taskId={reportTask.taskId}
                        onComplete={(taskResult) => {
                          // Task completed - could show notification
                          console.log('Report generation completed:', taskResult)
                        }}
                        onCancel={() => {
                          setReportTask(null)
                        }}
                        showDetails={false}
                      />
                    </div>
                  )}
                  {/* Gold Download Button - Only show when entity analysis exists */}
                  {(agentData?.buildingAnalysis || agentData?.viewportAnalysis || agentData?.explainability) && (
                    <button 
                      onClick={() => {
                        // Trigger download event
                        console.log('[MainApp] Download button clicked, dispatching valora-download-report event')
                        window.dispatchEvent(new CustomEvent('valora-download-report'));
                      }}
                      className="flex items-center gap-1 px-2 py-1 bg-gradient-to-r from-amber-500 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-900 text-xs font-bold rounded transition shadow-lg shadow-amber-500/20"
                      title="Download Report"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">
                        {(() => {
                          // Check building name
                          if (agentData?.buildingAnalysis?.building?.name) {
                            return `Download ${agentData.buildingAnalysis.building.name} Report`
                          }
                          // Check viewport area name
                          if (agentData?.viewportAnalysis?.area_name) {
                            return `Download ${agentData.viewportAnalysis.area_name} Report`
                          }
                          // Check explainability locality name
                          if (agentData?.explainability?.locality?.name) {
                            return `Download ${agentData.explainability.locality.name} Report`
                          }
                          // Check if explainability has area directly
                          if (agentData?.explainability?.area) {
                            return `Download ${agentData.explainability.area} Report`
                          }
                          // Check dashboard location
                          if (agentData?.dashboard?.location) {
                            return `Download ${agentData.dashboard.location} Report`
                          }
                          // Fallback: Extract location from AI response content
                          const aiContent = agentData?.lastAIResponse || window.__lastAIContent || '';
                          // Try to extract location from common patterns like "in Hebbal", "Hebbal area", "Hebbal, Bangalore"
                          const locationPatterns = [
                            /in\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)/,
                            /([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+area/i,
                            /([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?),\s*Bangalore/i,
                            /about\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)/i,
                            /analyzing\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)/i,
                          ];
                          for (const pattern of locationPatterns) {
                            const match = aiContent.match(pattern);
                            if (match && match[1]) {
                              return `Download ${match[1]} Report`
                            }
                          }
                          return 'Download Report'
                        })()}
                      </span>
                    </button>
                  )}
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
                  <SmartPanel
                    agentData={agentData}
                    setAgentData={setAgentData}
                    viewportAnalysis={agentData?.viewportAnalysis}
                    userTier={userTier}
                    authToken={token}
                    authUser={user}
                    fontSize={analysisFontSize}
                    activeTab={smartPanelActiveTab}
                    onTabChange={setSmartPanelActiveTab}
                  />
                </Suspense>
              </div>
            </>
          ) : (
            /* Collapsed Tab Sidebar */
            <div className="h-full w-12 bg-slate-800/30 border-r border-slate-700 flex flex-col py-1 overflow-hidden">
              {[
                { id: 'free_analysis', icon: Eye, label: 'Free' },
                { id: 'decision_verdict', icon: TrendingUp, label: 'Verdict' },
                { id: 'market_snapshot', icon: TrendingUp, label: 'Market' },
                { id: 'spatial_intelligence', icon: MapPin, label: 'Spatial' },
                { id: 'risk_analysis', icon: AlertTriangle, label: 'Risk' },
                { id: 'roi_projection', icon: Percent, label: 'ROI' },
                { id: 'comparables', icon: Building, label: 'Comps' },
                { id: 'strategy', icon: Compass, label: 'Strategy' },
                { id: 'data_transparency', icon: Database, label: 'Data' },
                { id: 'client_pitch', icon: Presentation, label: 'Pitch' },
                { id: 'agent_control', icon: Brain, label: 'Agent', shine: true },
                { id: 'community_pulse', icon: Users, label: 'Comm', shine: true }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => { setSmartPanelActiveTab(tab.id); setIsAnalysisOpen(true); }}
                  className="relative flex flex-col items-center justify-center py-2 px-1 text-slate-500 hover:text-slate-300 hover:bg-slate-700/30 transition-all duration-200 group overflow-hidden"
                  title={tab.label}
                  style={tab.shine ? {
                     boxShadow: '0 0 8px 2px rgba(34, 211, 238, 0.5)'
                   } : undefined}
                >
                  <tab.icon className={`w-4 h-4 z-10 ${tab.shine ? 'text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.9)]' : ''}`} />
                  <span className={`text-[8px] mt-0.5 font-medium z-10 ${tab.shine ? 'text-cyan-300' : ''}`}>{tab.label}</span>
                  
                  {/* Tooltip */}
                  <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 border border-slate-600 rounded text-[10px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                    {tab.label}
                  </div>
                </button>
              ))}
            </div>
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
          className="h-full bg-slate-800 border-l border-slate-700 flex flex-col transition-all duration-300 relative z-50"
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
                    authUser={user}
                    authToken={token}
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



      {/* Upgrade/Top-up Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Get More Credits</h2>
              <button onClick={() => setShowUpgradeModal(false)} className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Pricing Info */}
            <div className="bg-slate-700/50 rounded-xl p-4 mb-6">
              <p className="text-slate-300 text-sm mb-2">
                <span className="text-amber-400 font-medium">Simple Pricing:</span> 2 credits per local query (Qwen/Phi), 5 credits per cloud query (DeepSeek)
              </p>
            </div>

            {/* Top-up Packs */}
            <div className="mb-6">
              <h3 className="text-white font-semibold mb-3">Top-up Packs</h3>
              <div className="grid grid-cols-3 gap-3">
                <button 
                  onClick={() => handleTopUp('starter')}
                  className="p-4 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-blue-500/50 rounded-xl transition text-center"
                >
                  <p className="text-lg font-bold text-blue-400">Starter</p>
                  <p className="text-2xl font-bold text-white">100</p>
                  <p className="text-slate-400 text-xs">credits</p>
                  <p className="text-green-400 font-semibold mt-2">$5</p>
                </button>
                <button 
                  onClick={() => handleTopUp('standard')}
                  className="p-4 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/50 rounded-xl transition text-center relative"
                >
                  <div className="absolute -top-2 right-2 bg-blue-500 text-white text-[9px] font-bold px-2 py-0.5 rounded-full">POPULAR</div>
                  <p className="text-lg font-bold text-blue-400">Standard</p>
                  <p className="text-2xl font-bold text-white">275</p>
                  <p className="text-slate-400 text-xs">credits (250 + 25 bonus)</p>
                  <p className="text-green-400 font-semibold mt-2">$10</p>
                </button>
                <button 
                  onClick={() => handleTopUp('power')}
                  className="p-4 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-blue-500/50 rounded-xl transition text-center"
                >
                  <p className="text-lg font-bold text-blue-400">Power</p>
                  <p className="text-2xl font-bold text-white">800</p>
                  <p className="text-slate-400 text-xs">credits (700 + 100 bonus)</p>
                  <p className="text-green-400 font-semibold mt-2">$25</p>
                </button>
              </div>
            </div>

            {/* Pro Subscription */}
            <div className="border-t border-slate-700 pt-6">
              <h3 className="text-white font-semibold mb-3">Monthly Subscription</h3>
              <div className="p-4 bg-gradient-to-br from-purple-500/20 to-blue-500/10 border border-purple-500/30 rounded-xl">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-purple-400 font-bold flex items-center gap-2">
                      <Crown className="w-4 h-4" />
                      Pro Plan
                    </p>
                    <p className="text-2xl font-bold text-white">500</p>
                    <p className="text-slate-400 text-xs">credits/month + rollover</p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 font-bold text-2xl">$19</p>
                    <p className="text-slate-400 text-xs">/month</p>
                  </div>
                </div>
                <button
                  onClick={() => handleSubscribe()}
                  className="w-full mt-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  Subscribe Now
                </button>
              </div>
              <p className="text-slate-400 text-xs mt-3 text-center">
                All users get 50 free credits monthly • Admin users get premium status
              </p>
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
