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
 */

import { useState, useRef, useEffect, useCallback, memo, useMemo } from 'react'
import { PanelLeftClose, PanelLeft, Download, Trash2, Plus, X, MessageSquare, RefreshCw, ArrowDown } from 'lucide-react'

import ChatSidebar from './ChatSidebar'
import ChatMessage from './ChatMessage'
import ChatInputBar from './ChatInputBar'
import MessageFeedback from './MessageFeedback'
import CreditsWidget from './CreditsWidget'
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

import { API_URL } from '../../apiConfig'

// Welcome message - dynamically generated
function WelcomeMessage({ onExampleClick }) {
  const title = getDynamicWelcomeTitle()
  const subtitle = getDynamicWelcomeSubtitle()
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
const MessageList = memo(function MessageList({ messages, sessionId, onCopy, onRegenerate, onEdit, activeFeedbackId, onToggleFeedback }) {
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
  onSidebarClose = null
}) {
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
  
  // LLM config — cloud toggle controls whether model router can escalate
  const [llmConfig, setLlmConfig] = useState({
    provider: 'ollama',
    local_model: 'valora-2025v1', // Use available model
    cloud_enabled: false,
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
      const { building, query } = e.detail || {}
      if (!building || !query) return
      
      addMessage({ role: 'user', content: `🏢 Clicked: ${building.type || 'Building'} (${building.height || '?'}m)` })
      await handleSendMessage(query, true)
    }
    
    const handleAreaClick = async (e) => {
      if (isLoading) return
      const { coordinates, query } = e.detail || {}
      if (!coordinates || !query) return
      
      addMessage({ role: 'user', content: `📍 Analyzing area at ${coordinates.lat.toFixed(4)}, ${coordinates.lng.toFixed(4)}` })
      await handleSendMessage(query, true)
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
    
    window.addEventListener('valora-ask-question', handleAskQuestion)
    window.addEventListener('valora-building-clicked', handleBuildingClick)
    window.addEventListener('valora-area-clicked', handleAreaClick)
    window.addEventListener('valora-property-clicked', handlePropertyClick)
    window.addEventListener('valora-insight-explanation', handleInsightExplanation)
    
    return () => {
      window.removeEventListener('valora-ask-question', handleAskQuestion)
      window.removeEventListener('valora-building-clicked', handleBuildingClick)
      window.removeEventListener('valora-area-clicked', handleAreaClick)
      window.removeEventListener('valora-property-clicked', handlePropertyClick)
      window.removeEventListener('valora-insight-explanation', handleInsightExplanation)
    }
  }, [isLoading])
  
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

  // Stable user_id — persist across sessions
  const [userId] = useState(() => {
    const stored = localStorage.getItem('valora_user_id')
    if (stored) return stored
    const id = `user_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`
    localStorage.setItem('valora_user_id', id)
    return id
  })

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
  const buildContext = useCallback(() => ({
    user_id: userId,
    thread_id: currentSession?.id || null,
    selectedBuilding: agentData?.selectedBuilding || null,
    selectedLocation: agentData?.selectedLocation || null,
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
    agentic_mode: llmConfig.agentic_mode ?? null,  // null=auto, true=always, false=never
    llm_config: {
      provider: llmConfig.provider || 'ollama',
      local_model: llmConfig.local_model || 'qwen3:4b-instruct',
      cloud_enabled: llmConfig.cloud_enabled ?? false,
    }
  }), [userId, currentSession?.id, agentData, userLocation, locationLabel, attachedImages, llmConfig])
  
  // Streaming chat with abort support
  const callAIStreaming = useCallback(async (userMessage, onThinking, onContent, onComplete, signal) => {
    let capturedUIActions = []
    let capturedIntent = null
    
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
            case 'metadata':
              // Capture ui_actions, intent, dashboard, and facts for map/panel integration
              if (data.ui_actions) capturedUIActions = data.ui_actions
              if (data.intent) capturedIntent = data.intent
              
              // Update agentData with dashboard and facts for analysis panel
              if (setAgentData) {
                const updates = {}
                if (data.dashboard) updates.dashboard = data.dashboard
                if (data.facts) {
                  updates.explainability = {
                    confidence: 75,
                    keyDrivers: extractKeyDrivers(data.facts)
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
              
              // Dispatch UI actions for map integration
              if (setAgentData && capturedUIActions.length > 0) {
                for (const action of capturedUIActions) {
                  if (action.action === 'flyTo' && action.lat != null && action.lng != null) {
                    setAgentData(prev => ({ ...prev, flyTo: { lat: action.lat, lng: action.lng, zoom: action.zoom || 18 } }))
                  }
                  if (['switchTab', 'openPanel', 'closePanel', 'highlightProperties'].includes(action.action)) {
                    window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: action }))
                  }
                }
              }
              
              onComplete({ 
                content: finalContent, 
                thinking: finalThinking, 
                thinkingTime: data.thinking_time ?? thinkingTime,
                intent: capturedIntent,
                ui_actions: capturedUIActions
              })
              return
            case 'error':
              // Rate limit error — show upgrade prompt
              if (data.credits) {
                const upgradeMsg = `⚠️ **Credit limit reached** (${data.credits.remaining}/${data.credits.total} remaining, ${data.credits.tier} tier).\n\nUpgrade your plan or purchase more credits to continue using Valora AI.`
                onComplete({ content: upgradeMsg, thinking: '', thinkingTime: 0, rateLimited: true })
              } else {
                onComplete({ content: `Error: ${data.content}`, thinking: '', thinkingTime: 0 })
              }
              fetchCredits()
              return
          }
        }
      }
      
      onComplete({ content: contentBuffer || thinkingBuffer, thinking: thinkingBuffer, thinkingTime })
    } catch (err) {
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
          }
        }))
        
        // Dispatch UI commands
        if (Array.isArray(data?.ui_actions)) {
          for (const a of data.ui_actions) {
            if (a.action === 'flyTo' && a.lat != null && a.lng != null) {
              setAgentData(prev => ({ ...prev, flyTo: { lat: a.lat, lng: a.lng, zoom: a.zoom || 18 } }))
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
      
      return {
        content: data.message || data.assistant_message || '',
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
  const handleSendMessage = useCallback(async (messageOverride = null, skipUserMessage = false) => {
    const userMessage = messageOverride || input.trim()
    if (!userMessage || isLoading) return
    
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
  }, [input, isLoading, addMessage, updateLastMessage, callAIStreaming])
  
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
      title: 'New Chat'
    }
    setCurrentSession(clearedSession)
    saveSession(clearedSession)
    setSessions(prev => prev.map(s => s.id === clearedSession.id ? clearedSession : s))
  }, [currentSession])
  
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
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
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
            title={sidebarOpen ? 'Hide history' : 'Show history'}
          >
            {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            <span className="text-xs font-medium hidden sm:block">
              {sidebarOpen ? 'Hide' : 'History'}
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
                    {session?.title || 'New Chat'}
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
              title="New chat tab"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
          
          {/* Actions - compact */}
          <div className="flex items-center gap-0.5 shrink-0 ml-1 border-l border-primary-700/30 pl-1.5">
            <button
              onClick={handleClearChat}
              className="p-1.5 text-primary-400/70 hover:text-accent-fuchsia hover:bg-accent-fuchsia/10 rounded-lg transition-colors"
              title="Clear chat"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => currentSession && handleExportSession(currentSession)}
              className="p-1.5 text-primary-400/70 hover:text-white hover:bg-primary-700/30 rounded-lg transition-colors"
              title="Export chat"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => currentSession && handleDeleteSession(currentSession.id)}
              className="p-1.5 text-primary-400/70 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Delete chat"
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
          
          <div ref={messagesEndRef} className="h-1" />
        </div>
        
        {/* Scroll to bottom button - fixed position */}
        {showScrollButton && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-20 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-primary-600/90 hover:bg-primary-500 text-white text-xs rounded-full shadow-lg shadow-primary-900/30 transition-all flex items-center gap-1.5 animate-bounce-subtle z-50 pointer-events-auto"
            title="Scroll to bottom"
          >
            <ArrowDown className="w-3.5 h-3.5" />
            <span>Latest</span>
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
        />
      </div>
    </div>
  )
}
