/**
 * EnhancedChatPanel - Production-grade chat UX for Valora inference
 * 
 * Features:
 * - Multi-tab sessions (up to 3 tabs like Windsurf)
 * - Session persistence across panel close/open
 * - Real-time streaming (no throttling)
 * - Clear chat per session
 * - Local Ollama default
 * - Model selection (local/cloud)
 * - Message copy, edit, regenerate
 * - Code syntax highlighting
 * - Conversation export
 * - Glow effect for new responses
 * - Conversation context integration
 * - Language selector for multilingual support
 */

import { useState, useRef, useEffect, useCallback, memo, useMemo } from 'react'
import { PanelLeftClose, PanelLeft, Download, Trash2, Plus, X, MessageSquare, RefreshCw, ArrowDown, Languages } from 'lucide-react'
import '../../styles/chat-glow.css'

import ChatSidebar from './ChatSidebar'
import ChatMessage from './ChatMessage'
import ChatInputBar from './ChatInputBar'
import MessageFeedback from './MessageFeedback'
import TieredOptionsDisplay from './TieredOptionsDisplay'
import {
  loadSessions,
  saveSession,
  deleteSession,
  createNewSession,
  getCurrentSessionId,
  setCurrentSessionId,
  generateSessionTitle,
  exportSession
} from './ChatSessionManager'
import { getDefaultWelcomeMessage, getDynamicWelcomeTitle, getDynamicWelcomeSubtitle, getClosingMessage } from './ChatConfig'
import { useLanguage } from '../../contexts/LanguageContext'

import { API_URL } from '../../apiConfig'

// Welcome message - dynamically generated with translations
function WelcomeMessage({ onExampleClick }) {
  const { t } = useLanguage()
  const title = t('welcomeTitle')
  const subtitle = t('welcomeSubtitle')
  const closing = getClosingMessage()
  
  return (
    <div className="flex flex-col items-center justify-center h-full py-8 px-4">
      <div className="max-w-md mx-auto space-y-4 text-center">
        <h2 className="text-lg font-medium text-white">
          {title}
        </h2>
        <p className="text-sm text-primary-300/80">
          {subtitle}
        </p>
        <div className="text-xs text-primary-400/50 mt-6">
          {closing}
        </div>
      </div>
    </div>
  )
}

// Virtualized message list for performance with long conversations
const MessageList = memo(function MessageList({ messages, sessionId, onCopy, onRegenerate, onEdit, activeFeedbackId, onToggleFeedback, onDisambiguationSelect }) {
  // Only render last 50 messages for performance (virtualization)
  const VISIBLE_MESSAGE_COUNT = 50
  const totalMessages = messages.length
  const shouldVirtualize = totalMessages > VISIBLE_MESSAGE_COUNT
  
  // Get visible messages (last 50 for long conversations)
  const visibleMessages = shouldVirtualize 
    ? messages.slice(totalMessages - VISIBLE_MESSAGE_COUNT)
    : messages
  
  // Calculate offset for indexing
  const indexOffset = shouldVirtualize ? totalMessages - VISIBLE_MESSAGE_COUNT : 0
  
  return (
    <>
      {shouldVirtualize && (
        <div className="text-center py-2 text-[10px] text-primary-400/50">
          Showing last {VISIBLE_MESSAGE_COUNT} of {totalMessages} messages
        </div>
      )}
      {visibleMessages.map((msg, i) => {
        const actualIndex = indexOffset + i
        const messageId = msg.id || `${sessionId}-${actualIndex}`
        const isLast = actualIndex === totalMessages - 1
        
        return (
          <div key={messageId} className="relative">
            <ChatMessage
              message={msg}
              index={actualIndex}
              onCopy={onCopy}
              onRegenerate={onRegenerate}
              onEdit={onEdit}
              isLast={isLast}
              isLoading={msg.isLoading}
              showFeedback={activeFeedbackId === messageId}
              onToggleFeedback={onToggleFeedback}
              messageId={messageId}
              onDisambiguationSelect={onDisambiguationSelect}
            />
            <MessageFeedback
              isOpen={activeFeedbackId === messageId}
              onClose={() => onToggleFeedback(null)}
              messageId={messageId}
              messageContent={msg.content}
              position={msg.role === 'user' ? 'left' : 'right'}
            />
          </div>
        )
      })}
    </>
  )
}, (prevProps, nextProps) => {
  // Custom comparison for performance
  if (prevProps.sessionId !== nextProps.sessionId) return false
  if (prevProps.messages.length !== nextProps.messages.length) return false
  if (prevProps.activeFeedbackId !== nextProps.activeFeedbackId) return false
  
  // Only check the last few messages for changes during streaming
  const len = prevProps.messages.length
  const checkCount = Math.min(5, len)
  for (let i = 0; i < checkCount; i++) {
    const prev = prevProps.messages[len - 1 - i]
    const next = nextProps.messages[len - 1 - i]
    if (prev?.content !== next?.content || 
        prev?.isStreaming !== next?.isStreaming || 
        prev?.id !== next?.id ||
        prev?.streamingThought !== next?.streamingThought ||
        prev?.isThinking !== next?.isThinking) {
      return false
    }
  }
  return true
})

// Extract key drivers from facts for explainability
function extractKeyDrivers(facts) {
  if (!facts) return []
  const drivers = []
  
  if (facts.accessibility_score !== undefined) {
    drivers.push({ name: 'Accessibility', value: facts.accessibility_score, impact: (facts.accessibility_score - 50) / 100 })
  }
  if (facts.walkability_score !== undefined) {
    drivers.push({ name: 'Walkability', value: facts.walkability_score, impact: (facts.walkability_score - 50) / 100 })
  }
  if (facts.poi_count !== undefined) {
    drivers.push({ name: 'Amenity Density', value: facts.poi_count, impact: Math.min(facts.poi_count / 50, 1) - 0.3 })
  }
  if (facts.price_trend_pct !== undefined) {
    drivers.push({ name: 'Price Trend', value: `${facts.price_trend_pct > 0 ? '+' : ''}${facts.price_trend_pct?.toFixed(1)}%`, impact: facts.price_trend_pct / 20 })
  }
  
  return drivers.sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact)).slice(0, 8)
}

export default function EnhancedChatPanel({ 
  agentData, 
  setAgentData, 
  fontSize = 100, 
  userLocation = null, 
  locationLabel = null, 
  locationSource = 'ip',
  onTaskStreaming = null,
  onSidebarOpen = null,
  onSidebarClose = null,
  authUser = null,
  authToken = null
}) {
  // Get translation function and language setter
  const { t, language, setLanguage } = useLanguage()
  
  // AI Thinking state - query-driven intelligent tasks
  const [currentQuery, setCurrentQuery] = useState('')
  const [streamingData, setStreamingData] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  // Session management
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  
  // Chat state
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [attachedImages, setAttachedImages] = useState([])
  const [abortController, setAbortController] = useState(null)
  
  // Multi-tab support (up to 3 tabs like Windsurf)
  const [openTabs, setOpenTabs] = useState([]) // Array of session IDs
  const [activeTabId, setActiveTabId] = useState(null)
  const MAX_TABS = 3
  
  // LLM config — model selection is now automated based on query complexity
  const [llmConfig, setLlmConfig] = useState({
    provider: 'ollama',
    local_model: 'valora-2025v1', // Use available model
    cloud_enabled: true, // Always enabled - router decides based on complexity
  })
  
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const userScrolledRef = useRef(false)
  const inputRef = useRef(null)
  const scrollTimeoutRef = useRef(null)
  const lastScrollTopRef = useRef(0)
  const autoScrollThrottleRef = useRef(0)
  const intersectionObserverRef = useRef(null)
  const [showScrollButton, setShowScrollButton] = useState(false)
  
  // Track if component has initialized to prevent duplicate session creation
  const hasInitializedRef = useRef(false)
  
  // Feedback state management
  const [activeFeedbackId, setActiveFeedbackId] = useState(null)
  
  // Glow effect state - for new message animation
  const [isGlowing, setIsGlowing] = useState(false)
  const glowTimeoutRef = useRef(null)
  
  // Ref for handleSendMessage to avoid circular dependency in callbacks
  const sendMessageRef = useRef(null)
  
  // Language selector state - now uses context
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false)
  
  // User preferences from localStorage
  const [userPreferences, setUserPreferences] = useState(null)
  
  // Initialize intersection observer for scroll button
  useEffect(() => {
    if (!messagesEndRef.current || !messagesContainerRef.current) return
    
    intersectionObserverRef.current = new IntersectionObserver(
      (entries) => {
        const [entry] = entries
        // Show button when end is not visible (user scrolled up)
        setShowScrollButton(!entry.isIntersecting)
      },
      {
        root: messagesContainerRef.current,
        threshold: 0.1,
        rootMargin: '100px'
      }
    )
    
    intersectionObserverRef.current.observe(messagesEndRef.current)
    
    return () => {
      intersectionObserverRef.current?.disconnect()
    }
  }, [currentSession?.id])
  
  // Load user preferences from localStorage
  useEffect(() => {
    const savedPrefs = localStorage.getItem('valora_preferences')
    if (savedPrefs) {
      try {
        const prefs = JSON.parse(savedPrefs)
        setUserPreferences(prefs)
      } catch (e) {
        console.warn('[EnhancedChatPanel] Failed to parse preferences:', e)
      }
    }
  }, [])
  
  // Glow effect trigger - when new assistant message completes
  const triggerGlowEffect = useCallback(() => {
    // Clear any existing timeout
    if (glowTimeoutRef.current) {
      clearTimeout(glowTimeoutRef.current)
    }
    
    // Start glowing
    setIsGlowing(true)
    
    // Stop glowing after 15 seconds
    glowTimeoutRef.current = setTimeout(() => {
      setIsGlowing(false)
    }, 15000)
  }, [])
  
  // Cleanup glow timeout on unmount
  useEffect(() => {
    return () => {
      if (glowTimeoutRef.current) {
        clearTimeout(glowTimeoutRef.current)
      }
    }
  }, [])
  
  // Initialize sessions on mount - PERSIST across panel close/open
  useEffect(() => {
    // Prevent double initialization (React StrictMode or remounts)
    if (hasInitializedRef.current) return
    hasInitializedRef.current = true
    
    const loadedSessions = loadSessions()
    setSessions(loadedSessions)
    
    // Restore open tabs from localStorage
    const savedTabs = JSON.parse(localStorage.getItem('valora_open_tabs') || '[]')
    const savedActiveTab = localStorage.getItem('valora_active_tab')
    
    // Filter to valid sessions only
    const validTabs = savedTabs.filter(id => loadedSessions.find(s => s.id === id))
    
    if (validTabs.length > 0) {
      setOpenTabs(validTabs)
      const activeId = validTabs.includes(savedActiveTab) ? savedActiveTab : validTabs[0]
      setActiveTabId(activeId)
      const session = loadedSessions.find(s => s.id === activeId)
      if (session) setCurrentSession(session)
    } else if (loadedSessions.length > 0) {
      // Open first session as tab - DON'T create new if sessions exist
      setOpenTabs([loadedSessions[0].id])
      setActiveTabId(loadedSessions[0].id)
      setCurrentSession(loadedSessions[0])
    } else {
      // Only create new session if NO sessions exist at all
      const newSession = createNewSession()
      setSessions([newSession])
      setCurrentSession(newSession)
      setOpenTabs([newSession.id])
      setActiveTabId(newSession.id)
      saveSession(newSession)
    }
    
    // Check for active request from previous session (page refresh recovery)
    const activeRequest = JSON.parse(localStorage.getItem('valora_active_request') || 'null')
    if (activeRequest && activeRequest.query) {
      console.log('[EnhancedChatPanel] Recovering active request:', activeRequest)
      // Restore the task banner state
      setCurrentQuery(activeRequest.query)
      setIsProcessing(true)
      setIsLoading(true)
      setStreamingData({
        stage: 'recovering',
        query: activeRequest.query,
        request_id: activeRequest.request_id
      })
      
      // Notify parent about recovery
      if (onTaskStreaming) {
        onTaskStreaming({
          type: 'recovering',
          query: activeRequest.query,
          request_id: activeRequest.request_id,
          stage: 'reconnecting'
        })
      }
      
      // Clear the active request after a delay (assume it completed or failed)
      // In production, you'd poll the backend for actual status
      setTimeout(() => {
        localStorage.removeItem('valora_active_request')
        setIsProcessing(false)
        setIsLoading(false)
        if (onTaskStreaming) {
          onTaskStreaming({ type: 'task_recovered_done' })
        }
      }, 3000)
    }
  }, [])
  
  // Persist open tabs to localStorage
  useEffect(() => {
    localStorage.setItem('valora_open_tabs', JSON.stringify(openTabs))
    if (activeTabId) localStorage.setItem('valora_active_tab', activeTabId)
  }, [openTabs, activeTabId])
  
  
  // Load LLM config - Local only
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const resp = await fetch(`${API_URL}/api/admin/llm-config`)
        if (resp.ok) {
          const data = await resp.json()
          // Load last used model from localStorage
          const savedModel = localStorage.getItem('valora_selected_model')
          setLlmConfig(prev => ({
            ...prev,
            provider: 'ollama',
            local_model: savedModel || data.local_model || 'valora-2025v1',
          }))
        }
      } catch {}
    }
    loadConfig()
  }, [])
  
  // Smart auto-scroll with throttling to prevent flickering
  useEffect(() => {
    if (!messagesContainerRef.current || !messagesEndRef.current) return
    
    const container = messagesContainerRef.current
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150
    
    // Only auto-scroll if user hasn't manually scrolled up
    if (isNearBottom && !userScrolledRef.current) {
      // Throttle auto-scroll to max 10 times per second
      const now = Date.now()
      if (now - autoScrollThrottleRef.current < 100) return
      autoScrollThrottleRef.current = now
      
      // Use RAF for smooth, non-flickering scroll with instant behavior
      requestAnimationFrame(() => {
        if (messagesEndRef.current && !userScrolledRef.current) {
          // Direct scroll manipulation is smoother than scrollIntoView
          if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
          }
        }
      })
    }
  }, [currentSession?.messages])
  
  // Auto-scroll when input height changes (input becomes multi-line)
  useEffect(() => {
    if (!messagesContainerRef.current) return
    
    const container = messagesContainerRef.current
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 200
    
    // Scroll to bottom when input expands, if user was already near bottom
    if (isNearBottom && !userScrolledRef.current) {
      requestAnimationFrame(() => {
        if (messagesContainerRef.current) {
          messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
        }
      })
    }
  }, [input]) // Watch input changes
  
  // Detect manual scrolling - simplified since IntersectionObserver handles button visibility
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return
    
    const handleScroll = () => {
      const currentScrollTop = container.scrollTop
      const scrollHeight = container.scrollHeight
      const clientHeight = container.clientHeight
      const distanceFromBottom = scrollHeight - currentScrollTop - clientHeight
      
      // Detect upward scroll (user intentionally scrolling up)
      const scrollingUp = currentScrollTop < lastScrollTopRef.current - 5
      lastScrollTopRef.current = currentScrollTop
      
      if (scrollingUp || distanceFromBottom > 150) {
        userScrolledRef.current = true
      } else if (distanceFromBottom < 50) {
        // Near bottom, allow auto-scroll again
        userScrolledRef.current = false
      }
    }
    
    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => {
      container.removeEventListener('scroll', handleScroll)
    }
  }, [])
  
  // Scroll to bottom handler with smooth animation
  const scrollToBottom = useCallback(() => {
    if (!messagesContainerRef.current) return
    
    const container = messagesContainerRef.current
    const targetScroll = container.scrollHeight - container.clientHeight
    
    // Smooth scroll animation
    const duration = 300
    const start = container.scrollTop
    const change = targetScroll - start
    const startTime = performance.now()
    
    const animateScroll = (currentTime) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      
      // Ease out cubic for smooth deceleration
      const easeProgress = 1 - Math.pow(1 - progress, 3)
      
      container.scrollTop = start + change * easeProgress
      
      if (progress < 1) {
        requestAnimationFrame(animateScroll)
      } else {
        userScrolledRef.current = false
        setShowScrollButton(false)
      }
    }
    
    requestAnimationFrame(animateScroll)
  }, [])
  
  // Debounced session save ref
  const sessionSaveTimeoutRef = useRef(null)
  
  // Save session when messages change (debounced for performance)
  useEffect(() => {
    if (!currentSession || currentSession.messages?.length <= 1) return
    
    // Clear existing timeout
    if (sessionSaveTimeoutRef.current) {
      clearTimeout(sessionSaveTimeoutRef.current)
    }
    
    // Debounce save to reduce localStorage writes during streaming
    sessionSaveTimeoutRef.current = setTimeout(() => {
      const updatedSession = {
        ...currentSession,
        title: generateSessionTitle(currentSession.messages),
        updatedAt: new Date().toISOString()
      }
      saveSession(updatedSession)
      setSessions(prev => {
        const idx = prev.findIndex(s => s.id === currentSession.id)
        if (idx >= 0) {
          const newSessions = [...prev]
          newSessions[idx] = updatedSession
          return newSessions
        }
        return [updatedSession, ...prev]
      })
    }, 500) // 500ms debounce
    
    return () => {
      if (sessionSaveTimeoutRef.current) {
        clearTimeout(sessionSaveTimeoutRef.current)
      }
    }
  }, [currentSession?.messages])
  
  // Listen for external events (building clicks, insight explanations, etc.)
  useEffect(() => {
    const handleAskQuestion = async (e) => {
      const query = e.detail?.query
      if (!query || isLoading) return
      await handleSendMessage(query)
    }
    
    const handleBuildingClick = async (e) => {
      if (isLoading) return
      const { building, query, coordinates } = e.detail || {}
      if (!building || !query) return
      
      // The right-click handler already sets selectedLocation and starts rotation
      // Skip flyTo to prevent backend from overriding the camera position
      // Also set clickedLocation to prevent flyTo from changing selectedLocation
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          clickedLocation: coordinates,
          flyTo: null // Clear any pending flyTo
        }))
      }
      
      addMessage({ role: 'user', content: `🏢 Analyzing: ${building.type || 'Building'} (${building.height || '?'}m, ${building.levels || '?'} floors)` })
      await handleSendMessage(query, true, { skipFlyTo: true, buildingCoordinates: coordinates })
    }
    
    const handleAreaClick = async (e) => {
      if (isLoading) return
      const { coordinates, query, skipFlyTo } = e.detail || {}
      if (!coordinates || !query) return
      
      // Store the clicked coordinates to prevent backend flyTo from overriding them
      if (skipFlyTo && setAgentData) {
        setAgentData(prev => ({ 
          ...prev, 
          clickedLocation: coordinates,
          flyTo: null // Clear any pending flyTo
        }))
      }
      
      addMessage({ role: 'user', content: `📍 Analyzing area at ${coordinates.lat.toFixed(4)}, ${coordinates.lng.toFixed(4)}` })
      await handleSendMessage(query, true, { skipFlyTo: true, clickedCoordinates: coordinates })
    }
    
    const handlePropertyClick = async (e) => {
      if (isLoading) return
      const { property, query } = e.detail || {}
      if (!property || !query) return
      
      const bhk = property.bedrooms ? `${property.bedrooms}BHK` : ''
      const pType = property.property_type || property.type || 'Property'
      const price = property.price ? `₹${property.price >= 10000000 ? (property.price / 10000000).toFixed(1) + 'Cr' : (property.price / 100000).toFixed(0) + 'L'}` : ''
      addMessage({ role: 'user', content: `🏠 Selected: ${[bhk, pType, price].filter(Boolean).join(' · ')}` })
      await handleSendMessage(query, true)
    }
    
    const handleInsightExplanation = (e) => {
      const { cardName, explanation, areaName, cacheHit, unitsCharged } = e.detail || {}
      if (!explanation) return
      
      const cacheInfo = cacheHit ? '📦 (cached)' : unitsCharged ? `💰 ${unitsCharged} units` : ''
      addMessage({ role: 'user', content: `📊 **${cardName}** insight for ${areaName || 'this area'} ${cacheInfo}` })
      addMessage({ role: 'assistant', content: explanation, intent: 'insight_explanation' })
    }
    
    const handleFreeAnalysisTrigger = async (e) => {
      if (isLoading) return
      const { property, query, context } = e.detail || {}
      if (!property || !query) return
      
      // Store the clicked coordinates
      if (setAgentData && property.latitude && property.longitude) {
        setAgentData(prev => ({
          ...prev,
          clickedLocation: { lat: property.latitude, lng: property.longitude },
          flyTo: null
        }))
      }
      
      const bhk = property.bedrooms ? `${property.bedrooms}BHK` : ''
      const pType = property.property_type || 'Property'
      const price = property.price ? `₹${property.price >= 10000000 ? (property.price / 10000000).toFixed(1) + 'Cr' : (property.price / 100000).toFixed(0) + 'L'}` : ''
      addMessage({ role: 'user', content: `🏠 Analyzing: ${[bhk, pType, price, property.locality].filter(Boolean).join(' · ')}` })
      await handleSendMessage(query, true, { 
        skipFlyTo: true, 
        clickedCoordinates: { lat: property.latitude, lng: property.longitude },
        isFreeAnalysis: true
      })
    }
    
    window.addEventListener('valora-ask-question', handleAskQuestion)
    window.addEventListener('valora-building-clicked', handleBuildingClick)
    window.addEventListener('valora-area-clicked', handleAreaClick)
    window.addEventListener('valora-property-clicked', handlePropertyClick)
    window.addEventListener('valora-insight-explanation', handleInsightExplanation)
    window.addEventListener('valora-free-analysis-trigger', handleFreeAnalysisTrigger)
    
    return () => {
      window.removeEventListener('valora-ask-question', handleAskQuestion)
      window.removeEventListener('valora-building-clicked', handleBuildingClick)
      window.removeEventListener('valora-area-clicked', handleAreaClick)
      window.removeEventListener('valora-property-clicked', handlePropertyClick)
      window.removeEventListener('valora-insight-explanation', handleInsightExplanation)
      window.removeEventListener('valora-free-analysis-trigger', handleFreeAnalysisTrigger)
    }
  }, [isLoading])
  
  // Use authenticated user's email if available, otherwise fall back to stored/generated ID
  // This is computed reactively so it updates when authUser changes
  const userId = useMemo(() => {
    // If authUser is provided, use their email as user_id
    if (authUser?.email) {
      return authUser.email
    }
    // Fall back to stored or generated ID
    const stored = localStorage.getItem('valora_user_id')
    if (stored) return stored
    const id = `user_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`
    localStorage.setItem('valora_user_id', id)
    return id
  }, [authUser?.email])
  
  const addMessage = useCallback((message) => {
    const newMessage = {
      ...message,
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString()
    }
    setCurrentSession(prev => ({
      ...prev,
      messages: [...(prev?.messages || []), newMessage]
    }))
  }, [])
  
  const updateLastMessage = useCallback((updates) => {
    setCurrentSession(prev => {
      if (!prev?.messages?.length) return prev
      const messages = [...prev.messages]
      messages[messages.length - 1] = { ...messages[messages.length - 1], ...updates }
      return { ...prev, messages }
    })
  }, [])
  
  // Toggle feedback popup for a message
  const handleToggleFeedback = useCallback((messageId) => {
    setActiveFeedbackId(prev => prev === messageId ? null : messageId)
  }, [])
  
  // Handle disambiguation option selection - defined early but will be updated after handleSendMessage
  const handleDisambiguationSelect = useCallback(async (option) => {
    console.log('[ChatPanel] Disambiguation option selected:', option)
    
    // Add user's selection as a message
    addMessage({ 
      role: 'user', 
      content: `I meant ${option.name}${option.area ? `, ${option.area}` : ''}` 
    })
    
    // Send the selected location back to backend for processing
    const query = `Analyze ${option.name} at coordinates ${option.lat}, ${option.lng}`
    // Use sendMessageRef.current instead of handleSendMessage to avoid circular dependency
    if (sendMessageRef.current) {
      await sendMessageRef.current(query, true, { 
        skipFlyTo: false,
        clickedCoordinates: { lat: option.lat, lng: option.lng }
      })
    }
  }, [addMessage])
  
  // Handle tiered option selection - defined early but will be updated after handleSendMessage
  const handleTieredOptionSelect = useCallback(async (selectedOption) => {
    const { id, action, locality, lat, lng, credits } = selectedOption
    
    console.log('[ChatPanel] Tiered option selected:', selectedOption)
    
    // Add user's selection as a message
    addMessage({ 
      role: 'user', 
      content: `I'd like the ${selectedOption.label}` 
    })
    
    // Clear the tiered options display
    setStreamingData(prev => {
      const { tieredOptions, ...rest } = prev
      return { ...rest }
    })
    
    // Handle each option type
    switch (id) {
      case 'quick_overview':
        // Free - trigger area overview immediately
        addMessage({ 
          role: 'assistant', 
          content: `🔍 Getting a quick overview of **${locality}**...`,
          isLoading: true
        })
        // Trigger the analysis via chat
        if (sendMessageRef.current) {
          await sendMessageRef.current(`Give me a quick overview of ${locality}`, true)
        }
        break
        
      case 'area_analysis':
        // 3 credits - trigger area analysis
        addMessage({ 
          role: 'assistant', 
          content: `📊 Running detailed area analysis for **${locality}**... (3 credits)`,
          isLoading: true
        })
        if (sendMessageRef.current) {
          await sendMessageRef.current(`Run a detailed area analysis for ${locality} at coordinates ${lat}, ${lng}`, true)
        }
        break
        
      case 'investment_report':
        // 200 credits - trigger report generation flow
        // Check credits first
        try {
          const creditResp = await fetch(`${API_URL}/api/smart-report/check-credits?user_id=${userId}`)
          if (!creditResp.ok) {
            throw new Error(`Credit check failed: ${creditResp.status}`)
          }
          const creditData = await creditResp.json()
          
          if (!creditData.has_credits) {
            addMessage({ 
              role: 'assistant', 
              content: `⚠️ **Insufficient Credits**\n\nYou need 200 credits to generate a detailed report. You currently have ${creditData.current_credits} credits.\n\nPlease top up your credits to continue.`,
              intent: 'report_error'
            })
            return
          }
          
          // Show confirmation message
          addMessage({ 
            role: 'assistant', 
            content: `📊 **Generate Detailed Report?**\n\nThis will create a comprehensive investment report for **${locality}** covering:\n\n• Decision Verdict\n• Market Analysis\n• Spatial Intelligence\n• Risk Assessment\n• ROI Projections\n• Comparables\n• Investment Strategy\n• Data Transparency\n• Client Pitch\n\n**Cost: 200 credits** (You have ${creditData.current_credits})\n\nReply **YES** or **PROCEED** to continue, or **CANCEL** to abort.`,
            intent: 'report_confirmation',
            metadata: {
              type: 'report_confirmation',
              locality,
              lat,
              lng,
              credits_required: 200
            }
          })
        } catch (err) {
          console.error('[ChatPanel] Failed to check credits:', err)
          addMessage({ 
            role: 'assistant', 
            content: `❌ Failed to check credit balance: ${err.message}\n\nPlease ensure the backend is running and try again.`,
            intent: 'report_error'
          })
        }
        break
        
      default:
        // Generic action - send as chat message
        if (sendMessageRef.current) {
          await sendMessageRef.current(`${action} for ${locality}`, true)
        }
    }
  }, [addMessage, userId])
  
  // Separate effect for download report - MUST be after userId and addMessage definitions
  useEffect(() => {
    const handleDownloadReport = async (e) => {
      console.log('[ChatPanel] Download report event received', { isLoading, agentData, userId })
      
      if (isLoading) {
        console.log('[ChatPanel] Ignoring download - loading in progress')
        return
      }
      
      // Get location info
      const locality = agentData?.buildingAnalysis?.building?.name ||
                       agentData?.viewportAnalysis?.area_name ||
                       agentData?.explainability?.locality?.name ||
                       agentData?.explainability?.area ||
                       agentData?.dashboard?.location ||
                       'this location'
      
      const lat = agentData?.mapCenter?.lat
      const lng = agentData?.mapCenter?.lng
      
      console.log('[ChatPanel] Download report for:', { locality, lat, lng, userId })
      
      // Check credits first
      try {
        const creditResp = await fetch(`${API_URL}/api/smart-report/check-credits?user_id=${userId}`)
        console.log('[ChatPanel] Credit check response:', creditResp.status)
        
        if (!creditResp.ok) {
          throw new Error(`Credit check failed: ${creditResp.status}`)
        }
        
        const creditData = await creditResp.json()
        console.log('[ChatPanel] Credit data:', creditData)
        
        if (!creditData.has_credits) {
          addMessage({ 
            role: 'assistant', 
            content: `⚠️ **Insufficient Credits**\n\nYou need 200 credits to generate a detailed report. You currently have ${creditData.current_credits} credits.\n\nPlease top up your credits to continue.`,
            intent: 'report_error'
          })
          return
        }
        
        // Show confirmation message
        addMessage({ 
          role: 'assistant', 
          content: `📊 **Generate Detailed Report?**\n\nThis will create a comprehensive investment report for **${locality}** covering:\n\n• Decision Verdict\n• Market Analysis\n• Spatial Intelligence\n• Risk Assessment\n• ROI Projections\n• Comparables\n• Investment Strategy\n• Data Transparency\n• Client Pitch\n\n**Cost: 200 credits** (You have ${creditData.current_credits})\n\nReply **YES** or **PROCEED** to continue, or **CANCEL** to abort.`,
          intent: 'report_confirmation',
          metadata: {
            type: 'report_confirmation',
            locality,
            lat,
            lng,
            building_name: agentData?.buildingAnalysis?.building?.name,
            credits_required: 200
          }
        })
        
      } catch (err) {
        console.error('[ChatPanel] Failed to check credits:', err)
        addMessage({ 
          role: 'assistant', 
          content: `❌ Failed to check credit balance: ${err.message}\n\nPlease ensure the backend is running and try again.`,
          intent: 'report_error'
        })
      }
    }
    
    console.log('[ChatPanel] Registering valora-download-report listener')
    window.addEventListener('valora-download-report', handleDownloadReport)
    
    return () => {
      console.log('[ChatPanel] Removing valora-download-report listener')
      window.removeEventListener('valora-download-report', handleDownloadReport)
    }
  }, [isLoading, agentData, userId, addMessage])

  // Credits state
  const [credits, setCredits] = useState(null)

  // Fetch credits on mount and after each message
  const fetchCredits = useCallback(async () => {
    try {
      const resp = await fetch(`${API_URL}/api/credits/${userId}`)
      if (resp.ok) {
        const data = await resp.json()
        setCredits(data)
      }
    } catch (err) {
      console.warn('[Credits] Fetch failed:', err.message)
    }
  }, [userId])

  useEffect(() => { fetchCredits() }, [fetchCredits])

  // Build context for AI
  const buildContext = useCallback(() => {
    // Get clicked coordinates if available (from map click)
    const skipInfo = window._valoraSkipFlyTo
    const clickedCoordinates = (skipInfo?.skip && (Date.now() - skipInfo.timestamp) < 30000) 
      ? skipInfo.coordinates 
      : null
    const skipFlyTo = clickedCoordinates ? true : false
    
    return {
      user_id: userId,
      thread_id: currentSession?.id || null,
      selectedBuilding: agentData?.selectedBuilding || null,
      selectedLocation: clickedCoordinates || agentData?.selectedLocation || null,
      selectedPlace: agentData?.selectedPlace || null,
      mapCenter: agentData?.mapCenter || null,
      viewportBounds: agentData?.viewportBounds || null,
      viewportAnalysis: agentData?.viewportAnalysis || null,
      currentAnalysis: {
        areaName: agentData?.viewportAnalysis?.area_name,
        market: agentData?.viewportAnalysis?.market,
        spatial: agentData?.viewportAnalysis?.spatial,
      },
      explainability: agentData?.explainability || null,
      simulation: agentData?.simulation || null,
      userLocation: userLocation ? { lat: userLocation.lat, lng: userLocation.lng, label: locationLabel } : null,
      image: attachedImages?.length > 0 ? attachedImages : null,
      llm_config: {
        provider: llmConfig.provider || 'ollama',
        local_model: llmConfig.local_model || 'qwen3:4b-instruct',
        cloud_enabled: llmConfig.cloud_enabled ?? false,
      },
      // Pass skipFlyTo and clickedCoordinates for backend to use exact clicked location
      skipFlyTo: skipFlyTo,
      clickedCoordinates: clickedCoordinates,
      // Add language preference for multilingual support
      language: language,
      // Add user preferences for personalized responses
      user_preferences: userPreferences
    }
  }, [userId, currentSession?.id, agentData, userLocation, locationLabel, attachedImages, llmConfig, language, userPreferences])
  
  // Streaming chat with abort support
  const callAIStreaming = useCallback(async (userMessage, onThinking, onContent, onComplete, signal) => {
    let capturedUIActions = []
    let capturedIntent = null
    let uiActionsProcessed = false // Track if UI actions have been processed to avoid duplicates
    let capturedRequestId = null
    
    try {
      const messages = currentSession?.messages?.filter(m => m.role !== 'system').map(m => ({
        role: m.role,
        content: m.content
      })) || []
      
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: userMessage }],
          context: buildContext()
        }),
        signal // AbortSignal for cancellation
      })
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      if (!response.body) throw new Error('Streaming not supported')
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let thinkingBuffer = ''
      let contentBuffer = ''
      let thinkingTime = 0
      let sseBuffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        sseBuffer += decoder.decode(value, { stream: true })
        
        let sepIndex
        while (true) {
          const lfIndex = sseBuffer.indexOf('\n\n')
          const crlfIndex = sseBuffer.indexOf('\r\n\r\n')
          let sepLen = 0
          
          if (lfIndex !== -1 && (crlfIndex === -1 || lfIndex < crlfIndex)) {
            sepIndex = lfIndex
            sepLen = 2
          } else if (crlfIndex !== -1) {
            sepIndex = crlfIndex
            sepLen = 4
          } else {
            break
          }
          
          const rawEvent = sseBuffer.slice(0, sepIndex)
          sseBuffer = sseBuffer.slice(sepIndex + sepLen)
          
          const dataLines = rawEvent.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trimStart())
          if (dataLines.length === 0) continue
          
          const dataStr = dataLines.join('\n')
          if (dataStr === '[DONE]') {
            localStorage.removeItem('valora_active_request') // Clear active request on completion
            onComplete({ content: contentBuffer, thinking: thinkingBuffer, thinkingTime })
            return
          }
          
          let data
          try { 
            data = JSON.parse(dataStr)
            console.log('[SSE] Event type:', data.type, data)
          } catch { 
            continue 
          }
          
          thinkingTime = data.thinking_time ?? thinkingTime
          
          // Store request_id when we first get it for recovery on refresh
          if (data.request_id && !capturedRequestId) {
            capturedRequestId = data.request_id
            localStorage.setItem('valora_active_request', JSON.stringify({
              request_id: data.request_id,
              query: userMessage,
              timestamp: Date.now()
            }))
          }
          
          switch (data.type) {
            case 'intent_classification_start':
              console.log('[INTENT] Classification started')
              // Pass to streaming data for WindsurfThinkingPanel
              const startData = { 
                type: 'intent_classification_start',
                stage: 'intent',
                query: userMessage
              }
              setStreamingData(prev => ({ ...prev, ...startData }))
              // Emit to parent for top banner
              if (onTaskStreaming) onTaskStreaming(startData)
              break
            case 'intent_detected':
              // Forward task graph to banner
              const intentData = {
                type: 'intent_detected',
                intent: data.intent,
                confidence: data.confidence,
                task_graph: data.task_graph,
                query: userMessage
              }
              setStreamingData(prev => ({ ...prev, ...intentData }))
              if (onTaskStreaming) onTaskStreaming(intentData)
              onThinking(thinkingBuffer, thinkingTime, true)
              break
            case 'task_progress':
              // Forward task progress to banner
              const progressData = {
                type: 'task_progress',
                task_graph: data.task_graph,
                current_task: data.current_task,
                phase: data.phase,
                query: userMessage
              }
              setStreamingData(prev => ({ ...prev, ...progressData }))
              if (onTaskStreaming) onTaskStreaming(progressData)
              break
            case 'task_plan_created':
              if (onTaskStreaming) onTaskStreaming({ type: 'task_plan_created', total_tasks: data.total_tasks, query: userMessage })
              break
            case 'task_started':
              if (onTaskStreaming) onTaskStreaming({
                type: 'task_started',
                task_id: data.task_id,
                task_name: data.task_name,
                task_type: data.task_type,
                task_description: data.task_description,
                progress: data.progress,
                query: userMessage
              })
              break
            case 'task_completed':
              if (onTaskStreaming) onTaskStreaming({
                type: 'task_completed',
                task_id: data.task_id,
                task_name: data.task_name,
                summary: data.summary,
                duration_ms: data.duration_ms,
                progress: data.progress,
                query: userMessage
              })
              break
            case 'task_failed':
              if (onTaskStreaming) onTaskStreaming({
                type: 'task_failed',
                task_id: data.task_id,
                task_name: data.task_name,
                error: data.error,
                progress: data.progress,
                query: userMessage
              })
              break
            case 'model_selection':
              // Model router decided which model to use
              setStreamingData(prev => ({ ...prev, 
                model: data.model, 
                is_cloud: data.is_cloud,
                escalated: data.escalated,
                complexity_score: data.complexity_score,
                model_reasoning: data.reasoning,
              }))
              if (onTaskStreaming) onTaskStreaming({
                type: 'model_selection',
                model: data.model,
                is_cloud: data.is_cloud,
                is_vision: data.is_vision,
                escalated: data.escalated,
                complexity_score: data.complexity_score,
                reasoning: data.reasoning,
                query: userMessage
              })
              break
            case 'agentic_start':
              // Autonomous reasoning loop activated for complex queries
              setStreamingData(prev => ({ ...prev, agentic: true, agenticMessage: data.message }))
              if (onTaskStreaming) onTaskStreaming({ type: 'agentic_start', message: data.message, query: userMessage })
              break
            case 'agentic_action':
              // Agentic loop is calling a tool autonomously
              setStreamingData(prev => ({ ...prev, 
                agenticStep: data.step, 
                agenticTool: data.tool,
                agenticThought: data.thought,
              }))
              // Dispatch map visual feedback event for 3D pulse effect
              window.dispatchEvent(new CustomEvent('valora-agentic-step', {
                detail: { step: data.step, tool: data.tool, thought: data.thought, params: data.params }
              }))
              if (onTaskStreaming) onTaskStreaming({
                type: 'agentic_action',
                step: data.step,
                tool: data.tool,
                params: data.params,
                thought: data.thought,
                query: userMessage
              })
              break
            case 'agentic_observation':
              // Tool returned data
              if (onTaskStreaming) onTaskStreaming({
                type: 'agentic_observation',
                step: data.step,
                observation: data.observation,
                query: userMessage
              })
              break
            case 'agentic_complete':
              // Autonomous reasoning finished
              setStreamingData(prev => ({ ...prev, 
                agenticComplete: true,
                agenticConfidence: data.confidence,
                agenticSteps: data.steps_taken,
              }))
              if (onTaskStreaming) onTaskStreaming({
                type: 'agentic_complete',
                confidence: data.confidence,
                steps_taken: data.steps_taken,
                query: userMessage
              })
              break
            case 'suggestions':
              // Proactive follow-up suggestions from the AI
              setStreamingData(prev => ({ ...prev, suggestions: data.suggestions }))
              break
            case 'disambiguation':
              // Location disambiguation required - multiple locations match
              console.log('[ChatPanel] Disambiguation required:', data.options)
              updateLastMessage({
                intent: 'disambiguation',
                disambiguationOptions: data.options,
                content: data.message || `I found multiple locations matching "${data.query}". Which one did you mean?`,
                isLoading: false,
                isStreaming: false
              })
              setIsProcessing(false)
              setIsLoading(false)
              if (onTaskStreaming) onTaskStreaming({ type: 'disambiguation', query: userMessage })
              return
            case 'thinking':
              if (data.content) thinkingBuffer += data.content
              onThinking(thinkingBuffer, thinkingTime, true)
              break
            case 'thinking_end':
              onThinking(thinkingBuffer, thinkingTime, false)
              break
            case 'content':
              if (data.content) contentBuffer += data.content
              onContent(contentBuffer, thinkingTime)
              break
            case 'ui_actions_early':
              // EARLY UI actions - dispatch immediately so map moves BEFORE LLM response
              // This is the ONLY place UI actions are processed during streaming
              console.log('[ChatPanel] 🚀 Received EARLY UI actions:', data.ui_actions)
              if (data.ui_actions && setAgentData) {
                capturedUIActions = data.ui_actions
                uiActionsProcessed = true // Mark as processed to avoid duplicate handling
                for (const action of data.ui_actions) {
                  if (action.action === 'flyTo' && action.lat != null && action.lng != null) {
                    // Check if we should skip flyTo (user clicked on map, camera already there)
                    const skipInfo = window._valoraSkipFlyTo
                    if (skipInfo?.skip && (Date.now() - skipInfo.timestamp) < 30000) {
                      console.log('[ChatPanel] 🚫 Skipping flyTo entirely - user clicked on map, camera already at location')
                      // Don't set flyTo at all - the map click handler already moved the camera
                    } else {
                      console.log('[ChatPanel]  EARLY flyTo:', { lat: action.lat, lng: action.lng, zoom: action.zoom })
                      setAgentData(prev => ({ ...prev, flyTo: { lat: action.lat, lng: action.lng, zoom: action.zoom || 18 } }))
                    }
                  }
                  if (action.action === 'load_buildings' && action.lat != null && action.lng != null) {
                    // Only load buildings for query-based flow (not when user clicked on map)
                    // Map click handler already loads buildings at clicked coordinates
                    const skipInfo = window._valoraSkipFlyTo
                    if (skipInfo?.skip && (Date.now() - skipInfo.timestamp) < 30000) {
                      console.log('[ChatPanel] 🚫 Skipping load_buildings - user clicked on map, buildings already loaded by click handler')
                    } else {
                      console.log('[ChatPanel] 📤 EARLY load_buildings (query-based):', { lat: action.lat, lng: action.lng, radius_km: action.radius_km || 2 })
                      window.dispatchEvent(new CustomEvent('valora-load-buildings', { 
                        detail: { lat: action.lat, lng: action.lng, radius_km: action.radius_km || 2 }
                      }))
                    }
                  }
                  if (['switchTab', 'openPanel', 'closePanel', 'highlightProperties'].includes(action.action)) {
                    window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: action }))
                  }
                  // Handle tiered_options UI action - display analysis options
                  if (action.type === 'tiered_options') {
                    console.log('[ChatPanel] 📊 Received tiered_options:', action)
                    // Store tiered options data for display
                    setStreamingData(prev => ({ 
                      ...prev, 
                      tieredOptions: action,
                      stage: 'tiered_options'
                    }))
                  }
                }
              }
              if (data.intent) capturedIntent = data.intent
              break
            case 'metadata':
              // Capture ui_actions, intent, dashboard, and facts for map/panel integration
              console.log('[ChatPanel] 📨 Received metadata:', { ui_actions_count: data.ui_actions?.length, intent: data.intent })
              // Only capture ui_actions if not already processed (fallback for non-early flow)
              if (data.ui_actions && !uiActionsProcessed) {
                capturedUIActions = data.ui_actions
                console.log('[ChatPanel] 📋 capturedUIActions (fallback):', capturedUIActions)
              }
              if (data.intent) capturedIntent = data.intent
              
              // Update agentData with dashboard and facts for analysis panel
              if (setAgentData) {
                const updates = {}
                if (data.dashboard) updates.dashboard = data.dashboard
                if (data.facts) {
                  updates.explainability = {
                    confidence: 75,
                    keyDrivers: extractKeyDrivers(data.facts),
                    locality: {
                      name: data.facts.location_name,
                      archetype: data.facts.locality_archetype,
                      growth_stage: data.facts.locality_growth_stage,
                      tagline: data.facts.locality_tagline,
                      personality: data.facts.locality_personality,
                    }
                  }
                }
                if (Object.keys(updates).length > 0) {
                  setAgentData(prev => ({ ...prev, ...updates }))
                }
              }
              break
            case 'done':
            case 'processing_complete':
              let finalContent = contentBuffer || data.response?.narrative || data.result?.narrative || ''
              let finalThinking = thinkingBuffer || ''
              if (!finalContent?.trim() && finalThinking?.trim()) {
                finalContent = finalThinking
                finalThinking = ''
              }
              
              // Emit completion with task_graph to parent
              const doneData = { 
                type: 'done', 
                query: userMessage,
                task_graph: data.task_graph 
              }
              if (onTaskStreaming) onTaskStreaming(doneData)
              
              // Process UI actions ONLY if not already processed in ui_actions_early
              // Note: load_buildings is only handled in early handler for query-based loading
              // Map click handler handles click-based building loading
              if (!uiActionsProcessed && setAgentData && capturedUIActions.length > 0) {
                console.log('[ChatPanel] 📋 Processing UI actions (fallback in done handler):', capturedUIActions)
                for (const action of capturedUIActions) {
                  if (action.action === 'flyTo' && action.lat != null && action.lng != null) {
                    console.log('[ChatPanel] 📤 Dispatching flyTo:', { lat: action.lat, lng: action.lng, zoom: action.zoom })
                    setAgentData(prev => ({ ...prev, flyTo: { lat: action.lat, lng: action.lng, zoom: action.zoom || 18 } }))
                  }
                  // load_buildings removed from fallback - only early handler processes it for query-based loading
                  if (['switchTab', 'openPanel', 'closePanel', 'highlightProperties'].includes(action.action)) {
                    window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: action }))
                  }
                }
              }
              
              localStorage.removeItem('valora_active_request') // Clear on completion
              // Store AI content for location extraction
              window.__lastAIContent = finalContent
              onComplete({ 
                content: finalContent, 
                thinking: finalThinking, 
                thinkingTime: data.thinking_time ?? thinkingTime,
                intent: capturedIntent,
                ui_actions: capturedUIActions
              })
              return
            case 'error':
              localStorage.removeItem('valora_active_request') // Clear on error
              // Rate limit error — show the actual reason from backend
              if (data.credits) {
                // Use the actual error content which has the real reason (e.g., daily limit)
                const errorMsg = data.content || `Credit limit reached (${data.credits.remaining}/${data.credits.total} remaining, ${data.credits.tier} tier).`
                const upgradeMsg = `⚠️ **${errorMsg}**\n\nYou have ${data.credits.remaining}/${data.credits.total} monthly credits remaining (${data.credits.tier} tier). Check if you've hit a daily limit. Upgrade your plan or wait for reset.`
                onComplete({ content: upgradeMsg, thinking: '', thinkingTime: 0, rateLimited: true })
              } else {
                onComplete({ content: `Error: ${data.content}`, thinking: '', thinkingTime: 0 })
              }
              fetchCredits()
              return
          }
        }
      }
      
      localStorage.removeItem('valora_active_request') // Clear active request
      onComplete({ content: contentBuffer || thinkingBuffer, thinking: thinkingBuffer, thinkingTime })
    } catch (err) {
      localStorage.removeItem('valora_active_request') // Clear active request on error
      if (err.name === 'AbortError') {
        console.log('[Stream] Aborted by user')
        onComplete({ content: '🛑 Stopped by user', thinking: '', thinkingTime: 0 })
      } else {
        console.error('[Stream] Error:', err)
        onComplete({ content: `Error: ${err.message}`, thinking: '', thinkingTime: 0 })
      }
    }
  }, [currentSession, buildContext, onTaskStreaming])
  
  // Non-streaming fallback
  const callAI = useCallback(async (userMessage) => {
    try {
      const messages = currentSession?.messages?.filter(m => m.role !== 'system').map(m => ({
        role: m.role,
        content: m.content
      })) || []
      
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 120000)
      
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: userMessage }],
          context: buildContext()
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const data = await response.json()
      
      // Update agent data with response
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          dashboard: data.dashboard || prev.dashboard,
          simulation: data.simulation || null,
          explainability: {
            confidence: data.reasoning_trace?.confidence || 75,
            keyDrivers: extractKeyDrivers(data.facts),
            locality: {
              name: data.facts?.location_name,
              archetype: data.facts?.locality_archetype,
              growth_stage: data.facts?.locality_growth_stage,
              tagline: data.facts?.locality_tagline,
              personality: data.facts?.locality_personality,
            }
          }
        }))
        
        // Dispatch UI commands
        if (Array.isArray(data?.ui_actions)) {
          console.log('[ChatPanel] 📋 Processing UI actions (non-streaming):', data.ui_actions)
          for (const a of data.ui_actions) {
            if (a.action === 'flyTo' && a.lat != null && a.lng != null) {
              console.log('[ChatPanel] 📤 Dispatching flyTo (non-streaming):', { lat: a.lat, lng: a.lng, zoom: a.zoom })
              setAgentData(prev => ({ ...prev, flyTo: { lat: a.lat, lng: a.lng, zoom: a.zoom || 18 } }))
            }
            if (a.action === 'load_buildings' && a.lat != null && a.lng != null) {
              // Only load buildings for query-based flow (not when user clicked on map)
              // Map click handler already loads buildings at clicked coordinates
              const skipInfo = window._valoraSkipFlyTo
              if (skipInfo?.skip && (Date.now() - skipInfo.timestamp) < 30000) {
                console.log('[ChatPanel] 🚫 Skipping load_buildings (non-streaming) - user clicked on map, buildings already loaded by click handler')
              } else {
                console.log('[ChatPanel] 📤 NON-STREAMING load_buildings (query-based):', { lat: a.lat, lng: a.lng, radius_km: a.radius_km || 2 })
                window.dispatchEvent(new CustomEvent('valora-load-buildings', { 
                  detail: { lat: a.lat, lng: a.lng, radius_km: a.radius_km || 2 }
                }))
              }
            }
            if (['switchTab', 'openPanel', 'closePanel', 'highlightProperties'].includes(a.action)) {
              window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: a }))
            }
          }
        }
        
        // Dispatch storyboard
        if (data.facts?.lat && data.facts?.lng && data.storyboard) {
          window.dispatchEvent(new CustomEvent('valora-storyboard', { detail: data.storyboard }))
        }
      }
      
      // Store AI content for location extraction
      const aiContent = data.message || data.assistant_message || ''
      window.__lastAIContent = aiContent
      
      return {
        content: aiContent,
        chainOfThought: data.chain_of_thought,
        thinkingTime: data.thinking_time || 0,
        intent: data.intent,
        agents: data.agents_used,
        tools: data.tools_used
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        return { content: '⚠️ Request timed out. Please try a simpler query.' }
      }
      return { content: `⚠️ Error: ${err.message}` }
    }
  }, [currentSession, buildContext, setAgentData])
  
  // Stop streaming handler
  const handleStopStreaming = useCallback(() => {
    if (abortController) {
      abortController.abort()
      setAbortController(null)
      setIsLoading(false)
      
      // Clear active request from localStorage
      localStorage.removeItem('valora_active_request')
      
      // Emit task cancelled event for task panel
      if (onTaskStreaming) {
        onTaskStreaming({
          type: 'task_cancelled',
          query: input || currentQuery
        })
      }
    }
  }, [abortController, onTaskStreaming, input, currentQuery])
  
  // Send message handler
  const handleSendMessage = useCallback(async (messageOverride = null, skipUserMessage = false, options = {}) => {
    const { skipFlyTo, clickedCoordinates } = options
    const userMessage = messageOverride || input.trim()
    if (!userMessage || isLoading) return

    // Fast-path for explicit automation commands routed to Digital Employee APIs.
    const isAutomationCommand = /^(alert|alert me|schedule|weekly report|add lead|new lead|add a lead)/i.test(userMessage.trim())
    if (isAutomationCommand) {
      try {
        if (!authToken) {
          if (!skipUserMessage) addMessage({ role: 'user', content: userMessage })
          addMessage({
            role: 'assistant',
            content: 'Digital employee commands require login. Please sign in and try again.',
            intent: 'digital_employee_auth_required'
          })
          setInput('')
          return
        }

        const cmdResp = await fetch(`${API_URL}/api/digital-employee/commands/parse-and-execute`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({ command: userMessage })
        })

        const cmdData = await cmdResp.json().catch(() => ({}))
        if (cmdResp.ok && cmdData?.handled) {
          if (!skipUserMessage) addMessage({ role: 'user', content: userMessage })
          addMessage({
            role: 'assistant',
            content: cmdData.executed
              ? `✅ ${cmdData.summary || 'Automation command executed.'}`
              : `⚠️ ${cmdData.reason || 'Command recognized but could not be executed.'}`,
            intent: 'digital_employee_command'
          })
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'switchTab', value: 'agent_control' }
          }))
          setInput('')
          fetchCredits()
          return
        }
      } catch (cmdErr) {
        console.warn('[DigitalEmployee] Command fast-path failed, falling back to AI stream:', cmdErr)
      }
    }
    
    // Check if this is a confirmation response for report generation
    const lastMessage = currentSession?.messages?.slice(-1)[0]
    if (lastMessage?.intent === 'report_confirmation' && lastMessage?.metadata?.type === 'report_confirmation') {
      const lowerMessage = userMessage.toLowerCase().trim()
      
      if (lowerMessage === 'yes' || lowerMessage === 'proceed' || lowerMessage === 'y' || lowerMessage === 'confirm') {
        // User confirmed - start report generation
        const { locality, lat, lng, building_name, credits_required } = lastMessage.metadata
        
        addMessage({ role: 'user', content: userMessage })
        addMessage({ 
          role: 'assistant', 
          content: `⏳ Starting report generation for **${locality}**...\n\nI'll process each analysis tab and create a detailed report. This may take a few minutes.`,
          intent: 'report_started'
        })
        
        // Start the report generation task
        try {
          // Get tab data from agentData - properly formatted for backend
          const viewport = agentData?.viewportAnalysis || {};
          const building = agentData?.buildingAnalysis || {};
          const buildingData = building.building || {};
          const valuation = building.valuation || {};
          const explainability = agentData?.explainability || {};
          
          // Format tab data to match what backend report_generator expects
          const tabData = {
            decision_verdict: {
              verdict: explainability?.verdict || 'HOLD',
              confidence: explainability?.confidence || 0.75,
              confidence_score: Math.round((explainability?.confidence || 0.75) * 100),
              risk_level: explainability?.risk_level || 'MEDIUM',
              risk_score: explainability?.risk_score || 35,
              time_horizon: 'Medium-term',
              summary: explainability?.summary || 'Analysis based on available market data.',
              top_reasons: explainability?.keyDrivers?.slice(0, 5).map(d => d.factor || d.name) || [
                'Good connectivity to major hubs',
                'Developing infrastructure',
                'Competitive pricing relative to area'
              ],
              key_risks: explainability?.risks || [
                'Market volatility in short term',
                'Infrastructure project delays possible'
              ],
              strategy_recommendation: {
                entry_price: '₹8,200-8,800/sqft',
                hold_duration: '3-5 years',
                exit_target: '₹11,000+/sqft'
              },
              // New fields for enhanced prompts
              negotiation_leverage_points: [
                'Comparable properties selling at 5-8% lower',
                'Market cooling in last 3 months',
                'Seller motivation: property listed 60+ days'
              ],
              deal_breaker_flags: [
                'Unapproved deviations from building plan',
                'Pending litigation on land title',
                'Encroachment on government land'
              ],
              optimal_holding_period: '5-7 years for maximum appreciation',
              exit_timing: 'Sell when metro phase X completes (2028)'
            },
            market_snapshot: {
              avg_price_sqft: viewport?.market?.avg_price_per_sqft || agentData?.dashboard?.market?.avgPricePerSqft || 8500,
              sample_count: viewport?.market?.property_count || 156,
              price_trend: {
                '1Y': viewport?.market?.price_trend_pct ? `+${viewport.market.price_trend_pct}%` : '+12%',
                '3Y': '+35%',
                '5Y': '+62%'
              },
              demand_supply: viewport?.market?.demand || 'High Demand',
              rental_yield: viewport?.market?.rental_yield || '3.5%',
              liquidity_score: viewport?.market?.liquidity_score || 70,
              advanced_indicators: {
                'Market Momentum': 'Bullish',
                'Price Volatility': 'Low',
                'Inventory Days': '45 days',
                'Buyer Interest': 'High'
              },
              // New fields for enhanced prompts
              micro_market_comparison: {
                vs_adjacent_areas: [
                  { area: 'Koramangala', price_diff: '+15%', reason: 'More developed infrastructure' },
                  { area: 'HSR Layout', price_diff: '+8%', reason: 'Better connectivity' },
                  { area: 'BTM Layout', price_diff: '-5%', reason: 'Less premium segment' }
                ]
              },
              new_launch_pipeline: [
                { project: 'Prestige Lakeside', units: 450, launch: 'Q2 2026', expected_impact: 'May soften prices 3-5%' }
              ],
              rental_demand_employers: [
                { company: 'Infosys', distance: '3 km', employees: 5000 },
                { company: 'Wipro', distance: '4 km', employees: 3500 }
              ],
              price_segmentation: {
                budget: '₹6,000-7,500/sqft',
                mid_segment: '₹7,500-9,000/sqft',
                premium: '₹9,000-12,000/sqft'
              }
            },
            spatial_intelligence: {
              nearby_infrastructure: viewport?.spatial?.nearby_infrastructure || [
                { name: 'Metro Station', distance: '1.2 km' },
                { name: 'Shopping Mall', distance: '2.5 km' },
                { name: 'Tech Park', distance: '3.0 km' },
                { name: 'Hospital', distance: '1.8 km' }
              ],
              pois: viewport?.spatial?.pois || { schools: 5, hospitals: 3, malls: 2, offices: 8 },
              walkability_score: viewport?.spatial?.walkability_score || 75,
              transit_score: viewport?.spatial?.transit_score || 68,
              bike_score: viewport?.spatial?.bike_score || 72,
              growth_hotspots: viewport?.spatial?.growth_hotspots || [],
              // New fields for enhanced prompts
              commute_times: {
                electronic_city: '25 min',
                whitefield: '35 min',
                itpl: '30 min',
                airport: '45 min',
                mg_road: '20 min'
              },
              metro_expansion: {
                upcoming_line: 'Silk Board to KR Puram',
                expected_completion: 'December 2026',
                nearest_station: '1.2 km',
                expected_price_impact: '+8-12% over 2 years'
              },
              school_details: [
                { name: 'Delhi Public School', distance: '1.2 km', rating: 4.5, board: 'CBSE' },
                { name: 'National Public School', distance: '1.8 km', rating: 4.3, board: 'CBSE' }
              ],
              hospital_details: [
                { name: 'Apollo Hospital', distance: '2.5 km', emergency: '24/7' },
                { name: 'Fortis Hospital', distance: '3.0 km', emergency: '24/7' }
              ],
              school_admission_season: 'February-March for most Bangalore schools',
              last_mile_connectivity: 'Autos available 24/7, BMTC bus every 10 min'
            },
            risk_analysis: {
              overall_risk_score: viewport?.risks?.overall_risk_score || 35,
              risks: viewport?.risks || {
                flood: { level: 'LOW', score: 15 },
                legal: { level: 'MODERATE', score: 40 },
                market: { level: 'LOW', score: 30 },
                infrastructure: { level: 'LOW', score: 25 },
                environmental: { level: 'MODERATE', score: 35 }
              },
              mitigation_suggestions: [
                'Verify all title documents before purchase',
                'Check for pending litigation on the property',
                'Review RERA compliance status'
              ],
              // New fields for enhanced prompts
              legal_checklist: {
                bbmp_khata: 'Verify Khata certificate and extract',
                bda_approval: 'Check BDA/BMRDA approval letter',
                encumbrance: 'Get EC for last 30 years',
                rera_check: 'Verify at rera.karnataka.gov.in',
                documents_to_request: [
                  'Sale deed chain (all previous deeds)',
                  'Building approval plan',
                  'Occupancy certificate',
                  'Tax paid receipts (last 5 years)',
                  'Khata certificate',
                  'Encumbrance certificate'
                ]
              },
              flood_history: 'No major flooding recorded in last 10 years',
              warning_signs: [
                'Property price significantly below market rate',
                'Seller rushing to close without proper documentation',
                'Disputes with neighbors over boundaries'
              ]
            },
            roi_projection: {
              projection_3year: viewport?.roi?.projection_3year || {
                best_case: { return: '+35%', price: 11500 },
                expected: { return: '+20%', price: 10200 },
                worst_case: { return: '+3%', price: 8800 }
              },
              entry_exit: {
                recommended_entry: '₹8,200-8,800/sqft',
                target_exit: '₹11,000+/sqft'
              },
              rental_yield: viewport?.market?.rental_yield || '3.5%',
              investment_score: viewport?.investment?.score || 75,
              // New fields for enhanced prompts
              tax_implications: {
                capital_gains: {
                  short_term: 'Taxed at slab rate (held < 2 years)',
                  long_term: '20% with indexation benefit (held > 2 years)'
                },
                home_loan_benefits: {
                  section_80c: '₹1.5 lakh deduction on principal',
                  section_24b: '₹2 lakh deduction on interest'
                },
                stamp_duty: '5-6% of property value',
                registration: '1% of property value',
                rental_income_tax: 'Taxed at slab rate after 30% standard deduction'
              },
              comparison_with_alternatives: {
                fixed_deposit: '6-7% returns, low risk',
                mutual_funds: '10-12% returns, moderate risk',
                gold: '8-10% returns, low risk',
                real_estate: '12-15% returns, moderate risk'
              },
              break_even_analysis: 'Rental income covers 60% of EMI'
            },
            comparables: {
              comparables: viewport?.comparables || [
                { project: 'Similar Property 1', distance: '1.0 km', price_sqft: 8800, similarity: 90 },
                { project: 'Similar Property 2', distance: '1.5 km', price_sqft: 8500, similarity: 85 }
              ],
              price_analysis: {
                subject_property: valuation?.price_per_sqft || 8500,
                area_average: viewport?.market?.avg_price_per_sqft || 8900
              },
              building_valuation: valuation,
              // New fields for enhanced prompts
              transaction_evidence: [
                { project: 'Prestige Sunnyside', sold_price: 8650, sold_date: 'Jan 2026', size: '3BHK' },
                { project: 'Sobha Dream Acres', sold_price: 8400, sold_date: 'Dec 2025', size: '2BHK' }
              ],
              time_on_market: {
                average_days: 45,
                fast_selling: '30 days for well-priced properties',
                slow_selling: '90+ days for overpriced properties'
              },
              negotiation_patterns: {
                average_discount_from_asking: '5-8%',
                buyer_market: 'Buyers have upper hand',
                seller_market: 'Sellers have upper hand'
              },
              builder_reputation: {
                rating: 4.2,
                past_projects: 15,
                on_time_delivery: '85%',
                quality_score: 'Good'
              }
            },
            strategy: {
              investment_strategy: viewport?.strategy || {
                entry_timing: 'NOW - prices stable',
                negotiation_range: '₹8,200-8,600/sqft'
              },
              action_items: [
                'Schedule site visit',
                'Review all legal documents',
                'Check RERA registration',
                'Verify encumbrance certificate'
              ],
              timeline: {
                due_diligence: '2 weeks',
                closing: '4-6 weeks'
              },
              // New fields for enhanced prompts
              week_by_week_timeline: {
                week_1: ['Collect all documents from seller', 'Apply for encumbrance certificate', 'Schedule site visit'],
                week_2: ['Legal review of documents', 'Get property valued', 'Check loan eligibility'],
                week_3: ['Negotiate final price', 'Get loan sanction letter', 'Draft sale agreement'],
                week_4: ['Final negotiation', 'Sign sale agreement', 'Pay token amount']
              },
              document_checklist: [
                { document: 'Sale deed', status: 'Required', source: 'Seller' },
                { document: 'Building approval', status: 'Required', source: 'BBMP/BDA' },
                { document: 'Occupancy certificate', status: 'Required', source: 'Builder' },
                { document: 'Khata certificate', status: 'Required', source: 'BBMP' },
                { document: 'Tax receipts', status: 'Required', source: 'Seller' }
              ],
              home_loan_timeline: {
                pre_approval: '2-3 days',
                full_sanction: '7-10 days',
                disbursement: '2-3 days after registration'
              },
              registration_steps: [
                'Book slot at sub-registrar office',
                'Bring all original documents',
                'Both buyer and seller present with witnesses',
                'Pay stamp duty and registration fees',
                'Collect registered sale deed'
              ]
            },
            data_transparency: {
              verification_status: 'VERIFIED',
              data_sources: [
                { source: 'Property Registry', records: 42500, freshness: '2 days ago' },
                { source: 'POI Database', records: 26961, freshness: '5 days ago' }
              ],
              confidence_breakdown: {
                'Property Data': 85,
                'Market Data': 78,
                'Spatial Data': 92
              },
              // New fields for enhanced prompts
              per_metric_confidence: {
                price_data: 85,
                rental_data: 70,
                spatial_data: 92,
                market_trends: 78,
                risk_scores: 65
              },
              data_freshness: {
                property_listings: 'Updated daily',
                price_trends: 'Updated weekly',
                poi_data: 'Updated monthly',
                infrastructure: 'Updated quarterly'
              },
              verification_sources: [
                'BBMP Property Tax Portal',
                'RERA Karnataka',
                'Sub-Registrar Office',
                'Google Maps API'
              ],
              limitations: [
                'Transaction prices are estimates based on asking prices',
                'Rental data may not reflect negotiated amounts',
                'Infrastructure timelines subject to government delays'
              ]
            },
            client_pitch: {
              client_summary: building?.pitch?.summary || explainability?.summary || `Investment opportunity in ${locality}`,
              building_name: building_name || buildingData?.name || locality,
              building_valuation: valuation,
              investment_score: viewport?.investment?.score || 75,
              // New fields for enhanced prompts
              lifestyle_narrative: `Imagine starting your day with a peaceful walk in the nearby park, dropping your kids at a top-rated school just 1.2 km away, and reaching your office in Electronic City in just 25 minutes. Evenings can be spent at the mall 2.5 km away or enjoying the vibrant cafe culture of the neighborhood.`,
              social_proof: {
                notable_residents: 'IT professionals, doctors, and business owners',
                companies_nearby: ['Infosys', 'Wipro', 'TCS', 'Accenture'],
                similar_buyers: 'Young families and working professionals'
              },
              future_vision: `By 2028, the upcoming metro line will connect you to the entire city. Property prices are expected to appreciate 15-20% as infrastructure develops. The area is transforming from a quiet suburb to a thriving urban center.`,
              fomo_element: `Only 3 units available at this price point. Similar properties sold in the last month have seen 5% price increases. The window to enter at current prices is closing.`
            }
          }
          
          const response = await fetch(`${API_URL}/api/smart-report/generate-detailed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              locality,
              lat,
              lng,
              building_name,
              user_id: userId,
              tab_data: tabData
            })
          })
          
          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || 'Failed to start report generation')
          }
          
          const data = await response.json()
          
          // Dispatch event to show task progress
          window.dispatchEvent(new CustomEvent('valora-report-task-started', {
            detail: {
              taskId: data.task_id,
              locality,
              creditsCharged: data.credits_charged
            }
          }))
          
          // Update credits
          fetchCredits()
          
        } catch (err) {
          console.error('Failed to start report generation:', err)
          addMessage({ 
            role: 'assistant', 
            content: `❌ Failed to start report generation: ${err.message}\n\nPlease try again or contact support if the issue persists.`,
            intent: 'report_error'
          })
        }
        
        setInput('')
        return
      }
      
      if (lowerMessage === 'no' || lowerMessage === 'cancel' || lowerMessage === 'n' || lowerMessage === 'abort') {
        // User cancelled
        addMessage({ role: 'user', content: userMessage })
        addMessage({ 
          role: 'assistant', 
          content: `✅ Report generation cancelled. No credits have been charged.`,
          intent: 'report_cancelled'
        })
        setInput('')
        return
      }
    }
    
    // Store skipFlyTo flag for use in streaming response handler
    if (skipFlyTo && clickedCoordinates) {
      window._valoraSkipFlyTo = { 
        skip: true, 
        coordinates: clickedCoordinates,
        timestamp: Date.now()
      }
    }
    
    // FIX Issue 2 & 3: Dispatch new query event to clear old markers and reset panels
    // Include source info if this was triggered by a map click
    window.dispatchEvent(new CustomEvent('valora-new-query', {
      detail: { 
        query: userMessage,
        source: clickedCoordinates ? 'map-click' : 'chat',
        coordinates: clickedCoordinates,
        skipFlyTo: skipFlyTo
      }
    }))
    
    setInput('')
    setIsLoading(true)
    
    // Create new abort controller
    const controller = new AbortController()
    setAbortController(controller)
    
    if (!skipUserMessage) {
      addMessage({ role: 'user', content: userMessage })
    }
    
    // Add placeholder for assistant response
    addMessage({
      role: 'assistant',
      content: '',
      isLoading: true,
      isStreaming: true,
      isThinking: true,
      streamingThought: '',
      thinkingTime: 0
    })
    
    // Start AI thinking visualization with actual query
    setCurrentQuery(userMessage)
    setIsProcessing(true)
    setStreamingData({ stage: 'intent', confidence: 0 })
    
    // Use streaming with abort signal
    await callAIStreaming(
      userMessage,
      (thinking, time, isThinking) => {
        const thinkingData = { 
          type: 'thinking',
          stage: 'thinking', 
          thinkingTime: time,
          thinking: thinking,
          query: userMessage
        }
        setStreamingData(prev => ({ 
          ...prev, 
          stage: 'thinking', 
          thinkingTime: time,
          thinking: thinking
        }))
        // Emit to top banner in real-time
        if (onTaskStreaming) onTaskStreaming(thinkingData)
        updateLastMessage({
          streamingThought: thinking,
          thinkingTime: time,
          isThinking,
          isLoading: isThinking,
          isStreaming: true
        })
      },
      (content, time) => {
        setStreamingData(prev => ({ ...prev, stage: 'narrative' }))
        updateLastMessage({
          content,
          streamingContent: content,
          thinkingTime: time,
          isThinking: false,
          isLoading: false,
          isStreaming: true
        })
      },
      (result) => {
        setStreamingData(prev => ({ 
          ...prev, 
          stage: 'done', 
          done: true, 
          intent: result.intent,
          confidence: result.confidence || 0.85 
        }))
        updateLastMessage({
          content: result.content,
          intent: result.intent,
          confidence: result.confidence,
          reasoning: result.reasoning,
          tools_used: result.tools_used,
          ui_actions: result.ui_actions,
          streamingContent: null,
          thought: result.thinking, // Preserve the final thinking content
          streamingThought: null,
          isThinking: false,
          isLoading: false,
          isStreaming: false,
          thinkingTime: result.thinkingTime,
          isComplete: true
        }, true)
        
        // Trigger glow effect for new response
        triggerGlowEffect()
        
        // Keep panel visible but mark processing as done
        setIsProcessing(false)
        setIsLoading(false)  // ADD: Hide stop button
        
        // Refresh credits after each query
        fetchCredits()
      },
      controller.signal
    )
    setAbortController(null)
    setAttachedImages([])
  }, [input, isLoading, addMessage, updateLastMessage, callAIStreaming, authToken, fetchCredits, currentSession?.messages])
  
  // Effect to update sendMessageRef after handleSendMessage is defined
  useEffect(() => {
    sendMessageRef.current = handleSendMessage
  }, [handleSendMessage])
  
  // Session handlers - with multi-tab support
  const handleNewChat = useCallback(() => {
    const newSession = createNewSession()
    setSessions(prev => [newSession, ...prev])
    saveSession(newSession)
    
    // Add to tabs (max 3)
    setOpenTabs(prev => {
      if (prev.length >= MAX_TABS) {
        // Replace oldest tab
        return [newSession.id, ...prev.slice(0, MAX_TABS - 1)]
      }
      return [newSession.id, ...prev]
    })
    setActiveTabId(newSession.id)
    setCurrentSession(newSession)
  }, [])
  
  // Open session in tab
  const handleOpenInTab = useCallback((sessionId) => {
    if (openTabs.includes(sessionId)) {
      // Already open, just switch to it
      setActiveTabId(sessionId)
      const session = sessions.find(s => s.id === sessionId)
      if (session) setCurrentSession(session)
      return
    }
    
    setOpenTabs(prev => {
      if (prev.length >= MAX_TABS) {
        return [sessionId, ...prev.slice(0, MAX_TABS - 1)]
      }
      return [sessionId, ...prev]
    })
    setActiveTabId(sessionId)
    const session = sessions.find(s => s.id === sessionId)
    if (session) setCurrentSession(session)
  }, [openTabs, sessions])
  
  // Close tab
  const handleCloseTab = useCallback((tabId, e) => {
    e?.stopPropagation()
    setOpenTabs(prev => {
      const remaining = prev.filter(id => id !== tabId)
      if (remaining.length === 0) {
        // Create new session if closing last tab
        const newSession = createNewSession()
        setSessions(s => [newSession, ...s])
        saveSession(newSession)
        setActiveTabId(newSession.id)
        setCurrentSession(newSession)
        return [newSession.id]
      }
      // Switch to first remaining tab if closing active
      if (activeTabId === tabId) {
        setActiveTabId(remaining[0])
        const session = sessions.find(s => s.id === remaining[0])
        if (session) setCurrentSession(session)
      }
      return remaining
    })
  }, [activeTabId, sessions])
  
  // Switch tab
  const handleSwitchTab = useCallback((tabId) => {
    setActiveTabId(tabId)
    const session = sessions.find(s => s.id === tabId)
    if (session) setCurrentSession(session)
  }, [sessions])
  
  // Clear chat for current session
  const handleClearChat = useCallback(() => {
    if (!currentSession) return
    const clearedSession = {
      ...currentSession,
      messages: [getDefaultWelcomeMessage()],
      title: t('newChat')
    }
    setCurrentSession(clearedSession)
    saveSession(clearedSession)
    setSessions(prev => prev.map(s => s.id === clearedSession.id ? clearedSession : s))
  }, [currentSession, t])
  
  const handleSelectSession = useCallback((sessionId) => {
    // Open in tab instead of just selecting
    handleOpenInTab(sessionId)
  }, [handleOpenInTab])
  
  const handleDeleteSession = useCallback((sessionId) => {
    const remaining = deleteSession(sessionId)
    setSessions(remaining)
    
    if (currentSession?.id === sessionId) {
      if (remaining.length > 0) {
        setCurrentSession(remaining[0])
        setCurrentSessionId(remaining[0].id)
      } else {
        handleNewChat()
      }
    }
  }, [currentSession, handleNewChat])
  
  const handleDeleteAllSessions = useCallback(() => {
    // Clear all sessions from localStorage
    localStorage.removeItem('valora_sessions')
    localStorage.removeItem('valora_open_tabs')
    localStorage.removeItem('valora_current_session')
    
    // Reset state
    setSessions([])
    setOpenTabs([])
    
    // Create a fresh session
    const newSession = createNewSession()
    setSessions([newSession])
    setCurrentSession(newSession)
    setOpenTabs([newSession.id])
    setActiveTabId(newSession.id)
    saveSession(newSession)
  }, [])
  
  const handleRenameSession = useCallback((sessionId, newTitle) => {
    setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title: newTitle } : s))
    if (currentSession?.id === sessionId) {
      const updated = { ...currentSession, title: newTitle }
      setCurrentSession(updated)
      saveSession(updated)
    }
  }, [currentSession])
  
  const handleExportSession = useCallback((session) => {
    const content = exportSession(session, 'markdown')
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${session.title || 'chat'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [])
  
  // Message action handlers
  const handleCopyMessage = useCallback((text) => {
    // Already handled in ChatMessage
  }, [])
  
  const handleRegenerateMessage = useCallback(async (index) => {
    if (!currentSession?.messages || isLoading) return
    
    // Find the last user message before this assistant message
    let userMessageIndex = index - 1
    while (userMessageIndex >= 0 && currentSession.messages[userMessageIndex].role !== 'user') {
      userMessageIndex--
    }
    
    if (userMessageIndex < 0) return
    
    const userMessage = currentSession.messages[userMessageIndex].content
    
    // Remove messages from index onwards
    setCurrentSession(prev => ({
      ...prev,
      messages: prev.messages.slice(0, index)
    }))
    
    // Regenerate
    await handleSendMessage(userMessage, true)
  }, [currentSession, isLoading, handleSendMessage])
  
  const handleEditMessage = useCallback((index, content) => {
    // Remove messages from index onwards and set input
    setCurrentSession(prev => ({
      ...prev,
      messages: prev.messages.slice(0, index)
    }))
    setInput(content)
  }, [])
  
  const handleConfigChange = useCallback(async (newConfig) => {
    setLlmConfig(newConfig)
    try {
      await fetch(`${API_URL}/api/admin/llm-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      })
    } catch {}
  }, [])
  
  const messages = currentSession?.messages || []
  
  return (
    <div className="flex h-full bg-dark-950" style={{ zoom: `${fontSize}%` }}>
      {/* Sidebar */}
      <ChatSidebar
        sessions={sessions}
        currentSessionId={currentSession?.id}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onDeleteAllSessions={handleDeleteAllSessions}
        onRenameSession={handleRenameSession}
        onExportSession={handleExportSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      
      {/* Main chat area */}
      <div className={`flex-1 flex flex-col min-w-0 overflow-hidden relative ${isGlowing ? 'chat-panel-glowing' : ''}`}>
        {/* Tab bar - Professional compact design */}
        <div className="flex items-center gap-1 px-2 py-1.5 border-b border-primary-700/30 bg-surface-primary/80 backdrop-blur-sm shrink-0">
          {/* History toggle button - enhanced with visual feedback */}
          <button
            onClick={() => {
              const newState = !sidebarOpen
              setSidebarOpen(newState)
              // When opening sidebar, also open chat panel and expand width
              if (newState) {
                window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: { action: 'openPanel', value: 'chat' } }))
                if (onSidebarOpen) onSidebarOpen()
              } else {
                // When hiding sidebar, shrink chat panel width
                if (onSidebarClose) onSidebarClose()
              }
            }}
            className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg transition-all shrink-0 ${
              sidebarOpen 
                ? 'bg-primary-600 text-white shadow-md' 
                : 'text-primary-400/70 hover:text-white hover:bg-primary-700/30'
            }`}
            title={sidebarOpen ? t('hideHistory') : t('showHistory')}
          >
            {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            <span className="text-xs font-medium hidden sm:block">
              {sidebarOpen ? t('hide') : t('history')}
            </span>
          </button>
          
          {/* Session tabs - scrollable but no visible scrollbar */}
          <div className="flex items-center gap-1 flex-1 min-w-0 overflow-x-auto scrollbar-hide">
            {openTabs.map(tabId => {
              const session = sessions.find(s => s.id === tabId)
              const isActive = tabId === activeTabId
              return (
                <div
                  key={tabId}
                  onClick={() => handleSwitchTab(tabId)}
                  className={`group flex items-center gap-1.5 px-2.5 py-1 rounded-lg cursor-pointer transition-all shrink-0 max-w-[160px] ${
                    isActive 
                      ? 'bg-primary-700/60 text-white shadow-lg shadow-primary-900/20' 
                      : 'text-primary-400/70 hover:text-white hover:bg-primary-700/30'
                  }`}
                >
                  <MessageSquare className="w-3 h-3 shrink-0" />
                  <span className="text-xs font-medium truncate">
                    {session?.title || t('newChat')}
                  </span>
                  <button
                    onClick={(e) => handleCloseTab(tabId, e)}
                    className="p-0.5 text-primary-400/50 hover:text-white rounded opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )
            })}
          </div>
          
          {/* New tab button */}
          {openTabs.length < MAX_TABS && (
            <button
              onClick={handleNewChat}
              className="p-1.5 text-primary-400/70 hover:text-white hover:bg-primary-700/30 rounded-lg transition-colors shrink-0"
              title={t('newChatTab')}
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
          
          {/* Actions - compact */}
          <div className="flex items-center gap-0.5 shrink-0 ml-1 border-l border-primary-700/30 pl-1.5">
            <button
              onClick={handleClearChat}
              className="p-1.5 text-primary-400/70 hover:text-accent-fuchsia hover:bg-accent-fuchsia/10 rounded-lg transition-colors"
              title={t('clearChat')}
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => currentSession && handleExportSession(currentSession)}
              className="p-1.5 text-primary-400/70 hover:text-white hover:bg-primary-700/30 rounded-lg transition-colors"
              title={t('exportChat')}
            >
              <Download className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => currentSession && handleDeleteSession(currentSession.id)}
              className="p-1.5 text-primary-400/70 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title={t('deleteChat')}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        
        {/* Messages - optimized for performance */}
        <div 
          ref={messagesContainerRef} 
          className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin relative" 
          style={{ scrollBehavior: 'auto' }}
        >
          {messages.length === 0 ? (
            <WelcomeMessage onExampleClick={(text) => { setInput(text); inputRef.current?.focus(); }} />
          ) : (
            <MessageList 
              messages={messages}
              sessionId={currentSession?.id}
              onCopy={handleCopyMessage}
              onRegenerate={handleRegenerateMessage}
              onEdit={handleEditMessage}
              activeFeedbackId={activeFeedbackId}
              onToggleFeedback={handleToggleFeedback}
              onDisambiguationSelect={handleDisambiguationSelect}
            />
          )}
          
          {/* Proactive Suggestions Chips */}
          {streamingData?.suggestions && streamingData.suggestions.length > 0 && !isLoading && (
            <div className="flex flex-wrap gap-2 px-1 py-2 animate-fade-in">
              <span className="text-[10px] text-primary-400/60 uppercase tracking-wider w-full mb-0.5">Suggested follow-ups</span>
              {streamingData.suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setStreamingData(prev => ({ ...prev, suggestions: null })); handleSendMessage(s.query); }}
                  className="text-xs px-3 py-1.5 rounded-full bg-primary-700/40 hover:bg-primary-600/60 text-primary-200 hover:text-white border border-primary-600/30 hover:border-primary-500/50 transition-all cursor-pointer"
                  title={s.reason}
                >
                  {s.query}
                </button>
              ))}
            </div>
          )}
          
          {/* Tiered Options Display - Analysis options for locality */}
          {streamingData?.tieredOptions && !isLoading && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-[85%] rounded-xl px-3 py-2 bg-surface-secondary text-primary-100 border border-primary-700/30">
                <TieredOptionsDisplay
                  options={streamingData.tieredOptions.options}
                  locality={streamingData.tieredOptions.locality}
                  lat={streamingData.tieredOptions.lat}
                  lng={streamingData.tieredOptions.lng}
                  userCredits={streamingData.tieredOptions.user_credits || credits?.credits || 0}
                  onSelectOption={handleTieredOptionSelect}
                  isProcessing={isLoading}
                />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} className="h-1" />
        </div>
        
        {/* Scroll to bottom button - fixed position */}
        {showScrollButton && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-20 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-primary-600/90 hover:bg-primary-500 text-white text-xs rounded-full shadow-lg shadow-primary-900/30 transition-all flex items-center gap-1.5 animate-bounce-subtle z-50 pointer-events-auto"
            title={t('scrollToBottom')}
          >
            <ArrowDown className="w-3.5 h-3.5" />
            <span>{t('latest')}</span>
          </button>
        )}
        
        {/* Input (credits merged inline) */}
        <ChatInputBar
          value={input}
          onChange={setInput}
          onSend={() => handleSendMessage()}
          onStop={handleStopStreaming}
          onImageAttach={(img) => setAttachedImages(prev => [...prev, img])}
          attachedImages={attachedImages}
          onRemoveImage={(idx) => setAttachedImages(prev => prev.filter((_, i) => i !== idx))}
          isLoading={isLoading}
          llmConfig={llmConfig}
          onConfigChange={handleConfigChange}
          credits={credits}
          selectedLanguage={language}
          onLanguageChange={setLanguage}
        />
      </div>
    </div>
  )
}
