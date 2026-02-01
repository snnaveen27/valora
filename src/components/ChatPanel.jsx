import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, MapPin, Navigation, Settings, Cloud, HardDrive, ChevronDown, ChevronRight, Brain, Loader2, Sparkles, Search, Building2, TrendingUp, Compass, Zap, MessageCircle, Target, BarChart3 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Backend API URL
import { API_URL } from '../apiConfig'

// Confidence threshold for auto-navigation (0-100)
const AUTO_NAV_CONFIDENCE = 70

// Extract key drivers from facts for SHAP-style explainability
function extractKeyDrivers(facts) {
  if (!facts) return []
  
  const drivers = []
  
  // Location quality factors
  if (facts.accessibility_score !== undefined) {
    drivers.push({ 
      name: 'Accessibility', 
      value: facts.accessibility_score, 
      impact: (facts.accessibility_score - 50) / 100 
    })
  }
  if (facts.walkability_score !== undefined) {
    drivers.push({ 
      name: 'Walkability', 
      value: facts.walkability_score, 
      impact: (facts.walkability_score - 50) / 100 
    })
  }
  if (facts.poi_count !== undefined) {
    drivers.push({ 
      name: 'Amenity Density', 
      value: facts.poi_count, 
      impact: Math.min(facts.poi_count / 50, 1) - 0.3 
    })
  }
  if (facts.transport_count !== undefined) {
    drivers.push({ 
      name: 'Transit Access', 
      value: facts.transport_count, 
      impact: Math.min(facts.transport_count / 10, 1) - 0.2 
    })
  }
  
  // Market factors
  if (facts.price_trend_pct !== undefined) {
    drivers.push({ 
      name: 'Price Trend', 
      value: `${facts.price_trend_pct > 0 ? '+' : ''}${facts.price_trend_pct?.toFixed(1)}%`, 
      impact: facts.price_trend_pct / 20 
    })
  }
  if (facts.demand_level) {
    const demandImpact = facts.demand_level === 'High' ? 0.3 : facts.demand_level === 'Medium' ? 0 : -0.3
    drivers.push({ 
      name: 'Market Demand', 
      value: facts.demand_level, 
      impact: demandImpact 
    })
  }
  
  // Risk factors (negative impact)
  if (facts.overall_risk_score !== undefined) {
    drivers.push({ 
      name: 'Risk Score', 
      value: facts.overall_risk_score, 
      impact: -(facts.overall_risk_score - 30) / 100 
    })
  }
  if (facts.flood_risk && facts.flood_risk !== 'low') {
    drivers.push({ 
      name: 'Flood Risk', 
      value: facts.flood_risk, 
      impact: facts.flood_risk === 'high' ? -0.4 : -0.2 
    })
  }
  
  // Locality factors
  if (facts.locality_growth_stage) {
    const stageImpact = {
      'mature': 0.2,
      'maturing': 0.3,
      'growing': 0.4,
      'emerging': 0.2,
      'nascent': 0.1,
      'declining': -0.3,
    }
    drivers.push({ 
      name: 'Growth Stage', 
      value: facts.locality_growth_stage, 
      impact: stageImpact[facts.locality_growth_stage] || 0 
    })
  }
  
  // 3D factors
  if (facts.sky_view_factor !== undefined) {
    drivers.push({ 
      name: 'Sky View', 
      value: `${(facts.sky_view_factor * 100).toFixed(0)}%`, 
      impact: facts.sky_view_factor - 0.5 
    })
  }
  if (facts.view_quality) {
    const viewImpact = {
      'excellent': 0.4,
      'good': 0.2,
      'moderate': 0,
      'poor': -0.3,
    }
    drivers.push({ 
      name: 'View Quality', 
      value: facts.view_quality, 
      impact: viewImpact[facts.view_quality] || 0 
    })
  }
  
  // Sort by absolute impact
  return drivers.sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact)).slice(0, 8)
}

// Check if message is a navigation request and extract place
function detectNavigationIntent(message) {
  const msg = message.toLowerCase()
  
  // Exclude property/analysis/search queries - these should go to AI
  const excludePatterns = [
    /propert(y|ies)/i,
    /listing/i,
    /top\s+\d+/i,
    /best/i,
    /recommend/i,
    /analysis|analyze/i,
    /compare/i,
    /price|valuation/i,
    /investment/i
  ]
  
  for (const pattern of excludePatterns) {
    if (pattern.test(msg)) {
      return { isNavigation: false, placeName: null }
    }
  }
  
  // Navigation patterns - simple place navigation only
  const navPatterns = [
    /^(?:go\s+to|take\s+me\s+to|navigate\s+to|fly\s+to|zoom\s+to)\s+([a-z\s]+)$/i,
    /^(?:where\s+is|locate)\s+([a-z\s]+)$/i,
  ]
  
  for (const pattern of navPatterns) {
    const match = message.match(pattern)
    if (match && match[1]) {
      let place = match[1].trim().replace(/[?.!,]+$/, '').replace(/\s+(please|now)$/i, '')
      return { isNavigation: true, placeName: place }
    }
  }
  
  return { isNavigation: false, placeName: null }
}

// Intent Configuration with icons and colors
const INTENT_CONFIG = {
  greeting: { icon: MessageCircle, label: 'Chat', color: 'emerald', bg: 'from-emerald-500/20 to-emerald-600/10' },
  help: { icon: Sparkles, label: 'Help', color: 'blue', bg: 'from-blue-500/20 to-blue-600/10' },
  thanks: { icon: MessageCircle, label: 'Chat', color: 'emerald', bg: 'from-emerald-500/20 to-emerald-600/10' },
  farewell: { icon: MessageCircle, label: 'Chat', color: 'emerald', bg: 'from-emerald-500/20 to-emerald-600/10' },
  smalltalk: { icon: MessageCircle, label: 'Chat', color: 'emerald', bg: 'from-emerald-500/20 to-emerald-600/10' },
  navigate: { icon: Compass, label: 'Exploring', color: 'cyan', bg: 'from-cyan-500/20 to-cyan-600/10' },
  property_search: { icon: Search, label: 'Finding Properties', color: 'blue', bg: 'from-blue-500/20 to-blue-600/10' },
  analyze_area: { icon: Target, label: 'Analyzing', color: 'purple', bg: 'from-purple-500/20 to-purple-600/10' },
  analyze_building: { icon: Building2, label: 'Building Analysis', color: 'indigo', bg: 'from-indigo-500/20 to-indigo-600/10' },
  investment: { icon: TrendingUp, label: 'Investment Analysis', color: 'green', bg: 'from-green-500/20 to-green-600/10' },
  recommendation: { icon: Sparkles, label: 'Recommending', color: 'amber', bg: 'from-amber-500/20 to-amber-600/10' },
  market_trend: { icon: BarChart3, label: 'Market Analysis', color: 'rose', bg: 'from-rose-500/20 to-rose-600/10' },
  valuation: { icon: TrendingUp, label: 'Valuation', color: 'green', bg: 'from-green-500/20 to-green-600/10' },
  comparison: { icon: BarChart3, label: 'Comparing', color: 'orange', bg: 'from-orange-500/20 to-orange-600/10' },
  simulate: { icon: Zap, label: 'Simulating', color: 'yellow', bg: 'from-yellow-500/20 to-yellow-600/10' },
  terrain: { icon: Compass, label: 'Terrain Analysis', color: 'teal', bg: 'from-teal-500/20 to-teal-600/10' },
  general: { icon: Brain, label: 'Thinking', color: 'slate', bg: 'from-slate-500/20 to-slate-600/10' },
}

// Modern Intent Bubble Component
function IntentBubble({ intent, isLoading }) {
  const config = INTENT_CONFIG[intent] || INTENT_CONFIG.general
  const Icon = config.icon
  
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${config.bg} border border-${config.color}-500/30`}>
      {isLoading ? (
        <Loader2 className={`w-3 h-3 text-${config.color}-400 animate-spin`} />
      ) : (
        <Icon className={`w-3 h-3 text-${config.color}-400`} />
      )}
      <span className={`text-${config.color}-300`}>{config.label}</span>
    </div>
  )
}

// AI Reasoning Display - Ollama-style with real-time streaming support
function ThinkingDisplay({ thought, thinkingTime, isStreaming, streamingThought }) {
  const [expanded, setExpanded] = useState(true) // Default expanded during streaming
  
  // Auto-collapse when streaming finishes for better UX
  useEffect(() => {
    if (isStreaming) {
      setExpanded(true) // Expand while streaming
    } else if (thought || streamingThought) {
      setExpanded(false) // Collapse when finished
    }
  }, [isStreaming, thought, streamingThought])
  
  const displayThought = streamingThought || thought
  const displayTime = thinkingTime || 0
  
  if (!displayThought && !isStreaming) return null
  
  return (
    <div className="mb-3">
      {/* Prominent "Thought for X seconds" header - Ollama style */}
      <div className="mb-2 pb-2 border-b border-slate-700/50">
        <div className="text-sm text-slate-400 font-normal flex items-center gap-2">
          {isStreaming ? (
            <>
              <div className="w-2 h-2 bg-violet-400 rounded-full animate-pulse" />
              <span>Thinking... <span className="font-semibold text-slate-300">{displayTime.toFixed(1)}</span>s</span>
            </>
          ) : (
            <span>Thought for <span className="font-semibold text-slate-300">{displayTime.toFixed(1)}</span> seconds</span>
          )}
        </div>
      </div>
      
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-2 py-1.5 text-xs text-violet-400 hover:text-violet-300 hover:bg-violet-500/5 rounded transition-colors"
      >
        <Brain className={`w-3.5 h-3.5 ${isStreaming ? 'animate-pulse' : ''}`} />
        <span className="font-medium">{expanded ? 'Hide reasoning' : 'Show reasoning'}</span>
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>
      
      {expanded && displayThought && (
        <div className="mt-2 p-4 bg-slate-900/60 rounded-lg border border-slate-700/50">
          <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
            {displayThought}
            {isStreaming && <span className="animate-pulse">▌</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// Typing Indicator - Human-like dots
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="w-2 h-2 bg-blue-400/60 rounded-full animate-bounce" style={{ animationDelay: '0ms', animationDuration: '1s' }} />
      <span className="w-2 h-2 bg-blue-400/60 rounded-full animate-bounce" style={{ animationDelay: '150ms', animationDuration: '1s' }} />
      <span className="w-2 h-2 bg-blue-400/60 rounded-full animate-bounce" style={{ animationDelay: '300ms', animationDuration: '1s' }} />
    </div>
  )
}

// Simplified Status Display (no task list)
function StatusDisplay({ intent, isLoading }) {
  if (!isLoading && !intent) return null
  
  return (
    <div className="mb-2">
      <IntentBubble intent={intent} isLoading={isLoading} />
    </div>
  )
}

// REMOVED: ThinkingTasksPanel - replaced with cleaner StatusDisplay

// Collapsible Thinking/Reasoning Panel Component
function ThinkingPanel({ trace, intent, factsSummary }) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const stepTypeIcons = {
    'decompose': '🔍',
    'verify': '✓',
    'infer': '💡',
    'synthesize': '🔗',
    'validate': '✅',
    'gather': '📊',
    'geocode': '📍',
    'search': '🔎'
  }
  
  const confidenceColor = trace.confidence >= 80 ? 'text-green-400' : 
                          trace.confidence >= 50 ? 'text-yellow-400' : 'text-red-400'
  
  return (
    <div className="mb-3 -mt-1">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-300 transition-colors py-1 group"
      >
        {isExpanded ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        <Brain className="w-3 h-3 text-purple-400" />
        <span>Thinking</span>
        {intent && (
          <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded text-[10px] uppercase">
            {intent}
          </span>
        )}
        {trace.confidence > 0 && (
          <span className={`text-[10px] ${confidenceColor}`}>
            {trace.confidence}% confident
          </span>
        )}
        <span className="text-[10px] text-slate-500">
          ({trace.steps?.length || 0} steps)
        </span>
      </button>
      
      {isExpanded && (
        <div className="mt-2 bg-slate-900/50 rounded-lg p-3 border border-slate-700/50 text-xs space-y-2">
          {/* Reasoning Steps */}
          {trace.steps && trace.steps.map((step, idx) => (
            <div key={idx} className="flex gap-2 items-start">
              <span className="text-base leading-none mt-0.5">
                {stepTypeIcons[step.type] || '→'}
              </span>
              <div className="flex-1">
                <span className="text-slate-300">
                  {typeof step.description === 'string' 
                    ? step.description 
                    : typeof step.description === 'object'
                      ? JSON.stringify(step.description, null, 0).slice(0, 100)
                      : String(step.description)}
                </span>
                {step.data && typeof step.data === 'object' && (
                  <div className="mt-1 text-slate-500 bg-slate-800/50 rounded px-2 py-1">
                    {Object.entries(step.data).slice(0, 3).map(([k, v]) => (
                      <span key={k} className="mr-2">
                        <span className="text-slate-400">{k}:</span>{' '}
                        {typeof v === 'object' ? JSON.stringify(v).slice(0, 30) : String(v).slice(0, 30)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {/* Facts Summary */}
          {factsSummary && (
            <div className="mt-2 pt-2 border-t border-slate-700/50">
              <div className="text-slate-400 mb-1 flex items-center gap-1">
                <span>📊</span> Facts Used:
              </div>
              <div className="flex flex-wrap gap-2">
                {factsSummary.location && (
                  <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                    📍 {factsSummary.location}
                  </span>
                )}
                {factsSummary.poi_count > 0 && (
                  <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                    🏪 {factsSummary.poi_count} POIs
                  </span>
                )}
                {factsSummary.active_listings > 0 && (
                  <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                    🏠 {factsSummary.active_listings} listings
                  </span>
                )}
                {factsSummary.walkability > 0 && (
                  <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                    🚶 Walk: {factsSummary.walkability}/100
                  </span>
                )}
              </div>
            </div>
          )}
          
          {/* Sources */}
          {trace.sources && trace.sources.length > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-700/50 text-slate-500">
              Sources: {trace.sources.join(', ')}
            </div>
          )}
          
          {/* Warnings */}
          {trace.warnings && trace.warnings.length > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-700/50">
              {trace.warnings.map((w, i) => (
                <div key={i} className="text-yellow-400 flex items-center gap-1">
                  <span>⚠️</span> {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ChatPanel({ agentData, setAgentData, fontSize = 100, userLocation = null, locationLabel = null, locationSource = 'ip' }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `Hey there! 👋 I'm **Valora**, your AI assistant for Bangalore real estate.

I can help you with:

🏠 **Finding properties** — "3BHK in Whitefield under 1.5Cr"
📍 **Exploring areas** — "Tell me about Koramangala"
💰 **Investment advice** — "Is Hebbal a good investment?"
📊 **Market trends** — "Price trends in HSR Layout"
🔮 **What-if scenarios** — "What if metro comes to Sarjapur?"

Just ask naturally — I understand casual conversation too!

*Try: "Hi" or "What can you do?"*`, isFastResponse: true }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [disambiguationCandidates, setDisambiguationCandidates] = useState(null) // For showing multiple location options
  const [showModelSelector, setShowModelSelector] = useState(false)
  const [llmConfig, setLlmConfig] = useState({
    provider: 'local', // 'local' or 'openrouter'
    local_model: 'qwen3-vl:8b',  // Primary chat
    local_model_fast: 'llama3.2',  // Quick responses
    local_model_reasoning: 'deepseek-r1:8b',  // Simulation/reasoning
    active_model_type: 'primary',  // 'primary', 'fast', 'reasoning'
    openrouter_model: 'meta-llama/llama-3.3-70b-instruct:free'
  })
  const [availableModels, setAvailableModels] = useState({ openrouter: [], local: [], loading: false })
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Listen for "Ask about this" events from AnalysisPanel
  useEffect(() => {
    const handleAskQuestion = async (e) => {
      const query = e.detail?.query
      if (!query || isLoading) return
      
      setInput('')
      setMessages(prev => [...prev, { role: 'user', content: query }])
      setIsLoading(true)
      
      const aiResponse = await callAI(query)
      const reasoningTrace = window.__lastReasoningTrace
      const intent = window.__lastIntent
      const factsSummary = window.__lastFactsSummary
      const localityData = window.__lastLocalityData || null
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: aiResponse,
        reasoningTrace,
        intent,
        factsSummary,
        locality: localityData
      }])
      setIsLoading(false)
    }
    
    window.addEventListener('valora-ask-question', handleAskQuestion)
    return () => window.removeEventListener('valora-ask-question', handleAskQuestion)
  }, [isLoading])

  // Listen for building clicks from map to auto-analyze
  useEffect(() => {
    const handleBuildingClick = async (e) => {
      if (isLoading) return
      
      const { building, query } = e.detail || {}
      if (!building || !query) return
      
      // Add user-style message showing what was clicked
      const clickMessage = `🏢 Clicked: ${building.type || 'Building'} (${building.height || '?'}m, ${building.levels || '?'} floors)`
      setMessages(prev => [...prev, { role: 'user', content: clickMessage }])
      setIsLoading(true)
      
      // Add AI thinking placeholder
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '',
        isLoading: true,
        isStreaming: true,
        isThinking: true,
        streamingThought: '',
        streamingContent: '',
        thinkingTime: 0
      }])
      
      const messageIndex = messages.length + 1 // After user message
      
      // Use streaming for the building analysis
      await callAIStreaming(
        query,
        (thinking, time, isThinking) => {
          setMessages(prev => {
            const newMessages = [...prev]
            if (newMessages[messageIndex]) {
              newMessages[messageIndex] = {
                ...newMessages[messageIndex],
                streamingThought: thinking,
                thinkingTime: time,
                isThinking: isThinking,
                isLoading: isThinking,
                isStreaming: true
              }
            }
            return newMessages
          })
        },
        (content, time) => {
          setMessages(prev => {
            const newMessages = [...prev]
            if (newMessages[messageIndex]) {
              newMessages[messageIndex] = {
                ...newMessages[messageIndex],
                streamingContent: content,
                content: content,
                thinkingTime: time,
                isThinking: false,
                isLoading: false,
                isStreaming: true
              }
            }
            return newMessages
          })
        },
        (result) => {
          setMessages(prev => {
            const newMessages = [...prev]
            if (newMessages[messageIndex]) {
              newMessages[messageIndex] = {
                role: 'assistant',
                content: result.content,
                chainOfThought: result.thinking,
                thinkingTime: result.thinkingTime,
                intent: 'analyze_building',
                isLoading: false,
                isStreaming: false,
                isThinking: false,
                isFastResponse: false,
                streamingThought: null,
                streamingContent: null
              }
            }
            return newMessages
          })
          setIsLoading(false)
        }
      )
    }
    
    window.addEventListener('valora-building-clicked', handleBuildingClick)
    return () => window.removeEventListener('valora-building-clicked', handleBuildingClick)
  }, [isLoading, messages.length])

  // Listen for insight card explanations from AnalyticsMetrics
  useEffect(() => {
    const handleInsightExplanation = (e) => {
      const { cardType, cardName, explanation, cacheHit, charged, unitsCharged, hasSimulation, simulationData, areaName } = e.detail || {}
      
      if (!explanation) return
      
      // Build a message showing the insight
      const cacheInfo = cacheHit ? '📦 (cached - free)' : charged ? `💰 ${unitsCharged} units` : '✓ free'
      const userMsg = `📊 **${cardName || cardType}** insight for ${areaName || 'this area'} ${cacheInfo}`
      
      setMessages(prev => [...prev, { role: 'user', content: userMsg }])
      
      // Add the AI explanation
      const aiContent = explanation + (hasSimulation && simulationData?.available 
        ? `\n\n---\n🎬 **Simulation Available:** ${simulationData.preview}\n_Click to run a what-if scenario._` 
        : '')
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: aiContent,
        intent: 'insight_explanation',
        isInsight: true,
        insightType: cardType,
        hasSimulation,
        simulationData
      }])
    }
    
    const handleTopupNeeded = (e) => {
      const { message, cost, remaining } = e.detail || {}
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `⚠️ **Insufficient Units**\n\n${message}\n\n💳 [Top up now](/topup) to continue using AI insights.`,
        intent: 'topup_needed',
        isError: true
      }])
    }
    
    const handleSimulationAvailable = (e) => {
      const { cardType, simulationTypes, lat, lng, preview } = e.detail || {}
      
      // Dispatch to map panel to show simulation option
      window.dispatchEvent(new CustomEvent('valora-ui-command', {
        detail: { 
          action: 'showSimulationOption', 
          cardType, 
          simulationTypes, 
          lat, 
          lng,
          preview 
        }
      }))
    }
    
    window.addEventListener('valora-insight-explanation', handleInsightExplanation)
    window.addEventListener('valora-topup-needed', handleTopupNeeded)
    window.addEventListener('valora-simulation-available', handleSimulationAvailable)
    
    return () => {
      window.removeEventListener('valora-insight-explanation', handleInsightExplanation)
      window.removeEventListener('valora-topup-needed', handleTopupNeeded)
      window.removeEventListener('valora-simulation-available', handleSimulationAvailable)
    }
  }, [])

  // Check backend health on mount and load LLM config
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const resp = await fetch(`${API_URL}/health`, { method: 'GET' })
        if (resp.ok) {
          const data = await resp.json()
          setBackendStatus(data.nominatim === 'ok' ? 'ready' : 'no-nominatim')
        } else {
          setBackendStatus('offline')
        }
      } catch {
        setBackendStatus('offline')
      }
    }
    const loadLlmConfig = async () => {
      try {
        const resp = await fetch(`${API_URL}/api/admin/llm-config`)
        if (resp.ok) {
          const data = await resp.json()
          setLlmConfig({
            provider: data.provider || 'local',
            local_model: data.local_model || 'llama3.2',
            openrouter_model: data.openrouter_model || 'meta-llama/llama-3.2-3b-instruct:free'
          })
        }
      } catch {}
    }
    checkBackend()
    loadLlmConfig()
  }, [])

  // Save LLM config when changed + unload previous model to free RAM
  const saveLlmConfig = async (newConfig) => {
    const oldModel = llmConfig.local_model
    const newModel = newConfig.active_model_type === 'fast' ? newConfig.local_model_fast :
                     newConfig.active_model_type === 'reasoning' ? newConfig.local_model_reasoning :
                     newConfig.local_model
    
    setLlmConfig(newConfig)
    
    try {
      // Unload old model if switching to free up RAM
      if (newConfig.provider === 'local' && oldModel && oldModel !== newModel) {
        await fetch(`${API_URL}/api/admin/unload-model`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: oldModel })
        })
      }
      
      await fetch(`${API_URL}/api/admin/llm-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      })
    } catch {}
  }

  // Fetch available models from backend (real-time check)
  const fetchAvailableModels = async () => {
    setAvailableModels(prev => ({ ...prev, loading: true }))
    try {
      const resp = await fetch(`${API_URL}/api/admin/llm-models`)
      if (resp.ok) {
        const data = await resp.json()
        setAvailableModels({
          openrouter: data.openrouter || [],
          local: data.local || [],
          openrouter_error: data.openrouter_error,
          local_error: data.local_error,
          loading: false
        })
      }
    } catch {
      setAvailableModels(prev => ({ ...prev, loading: false }))
    }
  }

  // Fetch models when selector opens
  useEffect(() => {
    if (showModelSelector) {
      fetchAvailableModels()
    }
  }, [showModelSelector])

  // Geocode using backend API
  const geocodePlace = async (query) => {
    try {
      const resp = await fetch(`${API_URL}/api/geocode?q=${encodeURIComponent(query)}&limit=3`)
      if (!resp.ok) throw new Error('Geocode failed')
      const data = await resp.json()
      return data
    } catch (err) {
      console.error('Geocode error:', err)
      return null
    }
  }

  // Streaming chat with SSE - real-time thinking display
  const callAIStreaming = async (userMessage, onThinkingUpdate, onContentUpdate, onComplete) => {
    // Build comprehensive context for AI agent with all analysis data
    const context = {
      selectedBuilding: agentData?.selectedBuilding || null,
      selectedLocation: agentData?.selectedLocation || null,
      selectedPlace: agentData?.selectedPlace || null,
      mapCenter: agentData?.mapCenter || null,
      drawnPolygon: agentData?.drawnPolygon || null,
      drawnBuffer: agentData?.drawnBuffer || null,
      polygonAnalysis: agentData?.polygonAnalysis || null,
      bufferAnalysis: agentData?.bufferAnalysis || null,
      // Include viewport analysis for accurate responses
      viewportAnalysis: agentData?.viewportAnalysis || null,
      // Include current analysis metrics
      currentAnalysis: {
        areaName: agentData?.viewportAnalysis?.area_name || agentData?.explainability?.locality?.name,
        market: agentData?.viewportAnalysis?.market || null,
        spatial: agentData?.viewportAnalysis?.spatial || null,
        infrastructure: agentData?.viewportAnalysis?.infrastructure || null,
        livability: agentData?.viewportAnalysis?.livability || null,
        investment: agentData?.viewportAnalysis?.investment || null,
        terrain: agentData?.viewportAnalysis?.terrain || null,
        comparison: agentData?.viewportAnalysis?.comparison || null,
      },
      // Include explainability data
      explainability: agentData?.explainability || null,
      // Include simulation results if any
      simulation: agentData?.simulation || null,
      // Buildings count in viewport
      buildingsCount: agentData?.buildingsCount || 0,
    }

    try {
      console.log('[STREAM] Starting streaming request...')
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            ...messages.filter(m => m.role !== 'system').map(m => ({
              role: m.role,
              content: m.content
            })),
            { role: 'user', content: userMessage }
          ],
          context
        })
      })

      if (!response.ok) {
        console.error('[STREAM] HTTP error:', response.status)
        throw new Error(`HTTP ${response.status}`)
      }

      if (!response.body) {
        console.error('[STREAM] No response body')
        throw new Error('Streaming not supported')
      }

      const reader = response.body.getReader()
      console.log('[STREAM] Got reader, starting to read...')
      const decoder = new TextDecoder()
      let thinkingBuffer = ''
      let contentBuffer = ''
      let thinkingTime = 0

      // SSE events are separated by a blank line (\n\n). We must buffer across chunks.
      let sseBuffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        sseBuffer += text

        // Process complete SSE events (handle \n\n and \r\n\r\n)
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

          const normalizedEvent = rawEvent.replace(/\r\n/g, '\n')

          // Ignore comments/empty
          if (!normalizedEvent.trim()) continue

          // Collect all data: lines (SSE spec)
          const dataLines = normalizedEvent
            .split('\n')
            .filter(l => l.startsWith('data:'))
            .map(l => l.slice(5).trimStart())

          if (dataLines.length === 0) continue

          const dataStr = dataLines.join('\n')
          if (dataStr === '[DONE]') {
            onComplete({ content: contentBuffer, thinking: thinkingBuffer, thinkingTime })
            return
          }

          let data
          try {
            data = JSON.parse(dataStr)
          } catch (e) {
            // If backend ever sends non-JSON events, skip
            continue
          }

          thinkingTime = data.thinking_time ?? thinkingTime

          switch (data.type) {
            case 'status':
              // Keep UI in "thinking" state until we see actual content tokens.
              // This makes the experience feel like real LLM inference.
              onThinkingUpdate(thinkingBuffer, thinkingTime, true)
              break
            case 'thinking_start':
              onThinkingUpdate(thinkingBuffer, thinkingTime, true)
              break
            case 'thinking':
              if (data.content) thinkingBuffer += data.content
              onThinkingUpdate(thinkingBuffer, thinkingTime, true)
              break
            case 'thinking_end':
              onThinkingUpdate(thinkingBuffer, thinkingTime, false)
              break
            case 'content':
              if (data.content) contentBuffer += data.content
              onContentUpdate(contentBuffer, thinkingTime)
              break
            case 'done':
              onComplete({
                content: contentBuffer || data.full_response || '',
                thinking: thinkingBuffer || data.full_thinking || '',
                thinkingTime: data.thinking_time ?? thinkingTime
              })
              return
            case 'error':
              onComplete({ content: `Error: ${data.content}`, thinking: '', thinkingTime: 0 })
              return
          }
        }
      }
      // If stream ended without done, finalize whatever we have
      onComplete({ content: contentBuffer, thinking: thinkingBuffer, thinkingTime })
      return
    } catch (err) {
      console.error('[STREAM] Streaming error:', err)
      onComplete({ content: `Streaming error: ${err?.message || String(err)}`, thinking: '', thinkingTime: 0 })
    }
  }

  // Call backend AI chat endpoint with full context (non-streaming fallback)
  const callAI = async (userMessage) => {
    try {
      // Build comprehensive context for AI agent with all analysis data
      const context = {
        selectedBuilding: agentData?.selectedBuilding || null,
        selectedLocation: agentData?.selectedLocation || null,
        selectedPlace: agentData?.selectedPlace || null,
        mapCenter: agentData?.mapCenter || null,
        drawnPolygon: agentData?.drawnPolygon || null,
        drawnBuffer: agentData?.drawnBuffer || null,
        polygonAnalysis: agentData?.polygonAnalysis || null,
        bufferAnalysis: agentData?.bufferAnalysis || null,
        viewport: {
          buildingsCount: agentData?.buildingsCount || 0,
          zoom: agentData?.zoom || 'medium'
        },
        // Include user's precise location for better context
        userLocation: userLocation ? {
          lat: userLocation.lat,
          lng: userLocation.lng,
          accuracy: userLocation.accuracy,
          label: locationLabel,
          source: locationSource
        } : null,
        // Include viewport analysis for accurate responses
        viewportAnalysis: agentData?.viewportAnalysis || null,
        // Include current analysis metrics
        currentAnalysis: {
          areaName: agentData?.viewportAnalysis?.area_name || agentData?.explainability?.locality?.name,
          market: agentData?.viewportAnalysis?.market || null,
          spatial: agentData?.viewportAnalysis?.spatial || null,
          infrastructure: agentData?.viewportAnalysis?.infrastructure || null,
          livability: agentData?.viewportAnalysis?.livability || null,
          investment: agentData?.viewportAnalysis?.investment || null,
          terrain: agentData?.viewportAnalysis?.terrain || null,
          comparison: agentData?.viewportAnalysis?.comparison || null,
        },
        // Include explainability data
        explainability: agentData?.explainability || null,
        // Include simulation results if any
        simulation: agentData?.simulation || null,
      }

      // Add 120 second timeout for complex queries
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 120000)
      
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [
            ...messages.filter(m => m.role !== 'system').map(m => ({
              role: m.role,
              content: m.content
            })),
            { role: 'user', content: userMessage }
          ],
          context: context
        }),
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`AI API error: ${response.status}`)
      }

      const data = await response.json()
      
      // Update global agent data with simulation and digital twin state
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          dashboard: data.dashboard || prev.dashboard,
          simulation: data.simulation || null,
          digitalTwinState: data.digital_twin_state || null,
          lastReasoningTrace: data.reasoning_trace || null,
          // City Intelligence data for explainability
          explainability: {
            confidence: data.reasoning_trace?.confidence || data.facts?.confidence_score || 75,
            keyDrivers: data.facts?.key_drivers || extractKeyDrivers(data.facts),
            reasoning_chain: data.reasoning_trace?.steps || [],
            causal_analysis: data.facts?.causal_analysis,
            risk_profile: data.facts?.risk_profile,
            risk_warnings: data.facts?.risk_warnings || [],
            prediction: data.facts?.prediction,
            locality: {
              archetype: data.facts?.locality_archetype,
              growth_stage: data.facts?.locality_growth_stage,
              tagline: data.facts?.locality_tagline,
              personality: data.facts?.locality_personality,
            }
          },
          // For real-time panel updates
          causalAnalysis: data.facts?.causal_analysis,
          riskProfile: data.facts?.risk_profile,
          riskWarnings: data.facts?.risk_warnings,
          reasoningTrace: data.reasoning_trace,
        }))
        
        // Dispatch live analysis update event for real-time panel sync
        window.dispatchEvent(new CustomEvent('valora-ui-command', { 
          detail: { 
            action: 'updateAnalysis', 
            analysis: {
              confidence: data.reasoning_trace?.confidence || 75,
              keyDrivers: extractKeyDrivers(data.facts),
              reasoning_chain: data.reasoning_trace?.steps || [],
              causal_analysis: data.facts?.causal_analysis,
              risk_profile: data.facts?.risk_profile,
              risk_warnings: data.facts?.risk_warnings || [],
              dataPoints: data.facts?.poi_count || 0,
            }
          } 
        }))
      }
      
      // Store reasoning trace, chain-of-thought for UI display
      window.__lastReasoningTrace = data.reasoning_trace || null
      window.__lastIntent = data.intent || null
      window.__lastFactsSummary = data.facts_summary || null
      window.__lastChainOfThought = data.chain_of_thought || null
      window.__lastThinkingTime = data.thinking_time || 0
      window.__lastFastResponse = data.fast_response || false  // Conversational responses (no LLM)
      
      // Store locality data for inline card display
      if (data.facts?.locality_archetype) {
        window.__lastLocalityData = {
          name: data.facts.location_name,
          archetype: data.facts.locality_archetype,
          growth_stage: data.facts.locality_growth_stage,
          tagline: data.facts.locality_tagline,
          personality: data.facts.locality_personality,
        }
      } else {
        window.__lastLocalityData = null
      }
      
      // Dispatch storytelling event if we have location + narrative data
      if (data.facts?.lat && data.facts?.lng && data.storyboard) {
        window.dispatchEvent(new CustomEvent('valora-storyboard', { 
          detail: data.storyboard 
        }))
      }

      if (Array.isArray(data?.ui_actions)) {
        for (const a of data.ui_actions) {
          if (!a || !a.action) continue

          if (a.action === 'flyTo' && a.lat != null && a.lng != null && setAgentData) {
            setAgentData(prev => ({
              ...prev,
              flyTo: { lat: a.lat, lng: a.lng, zoom: a.zoom || 18 }
            }))
          }

          if (a.action === 'switchTab' || a.action === 'openPanel' || a.action === 'closePanel') {
            window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: a }))
          }
          
          // Map Sync: Dispatch highlightProperties to map
          if (a.action === 'highlightProperties' && a.properties) {
            window.dispatchEvent(new CustomEvent('valora-ui-command', { detail: a }))
          }
          
          // Analysis Panel commands: Switch analysis sub-tabs, show specific views
          if (a.action === 'showAnalysis' || a.action === 'switchAnalysisTab') {
            window.dispatchEvent(new CustomEvent('valora-analysis-command', { 
              detail: { action: 'switchTab', tab: a.tab || 'overview' }
            }))
          }
          if (a.action === 'showSimulation') {
            window.dispatchEvent(new CustomEvent('valora-analysis-command', { 
              detail: { action: 'showSimulation', data: a.data }
            }))
          }
          if (a.action === 'showComparables' || a.action === 'showComps') {
            window.dispatchEvent(new CustomEvent('valora-analysis-command', { 
              detail: { action: 'showComps' }
            }))
          }
          if (a.action === 'showExplainability' || a.action === 'explainValuation') {
            window.dispatchEvent(new CustomEvent('valora-analysis-command', { 
              detail: { action: 'showExplainability' }
            }))
          }
          if (a.action === 'analyzeLocation' && a.lat && a.lng) {
            window.dispatchEvent(new CustomEvent('valora-analyze-location', { 
              detail: { lat: a.lat, lng: a.lng, locality: a.locality }
            }))
          }
        }
      }

      return data.message || data.assistant_message || ''
    } catch (err) {
      console.error('AI call failed:', err)
      console.error('Error details:', {
        name: err.name,
        message: err.message,
        stack: err.stack
      })
      
      // Check if it's a timeout
      if (err.name === 'AbortError') {
        return `⚠️ Request took too long (>120s). The analysis is complex and timed out.\n\nPlease try a simpler query or check if the backend is processing.`
      }
      
      return `⚠️ Connection error: ${err.message}\n\nBackend may be slow or unavailable. Please wait and try again.`
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    if (disambiguationCandidates) setDisambiguationCandidates(null)
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    // Step 1: Detect navigation intent
    const navIntent = detectNavigationIntent(userMessage)
    
    if (navIntent.isNavigation && navIntent.placeName) {
      // Step 2: Geocode using backend API (has local OSM fallback)
      const geocodeResult = await geocodePlace(navIntent.placeName)
      
      if (geocodeResult?.success && geocodeResult.top_result) {
        const place = geocodeResult.top_result
        const allResults = geocodeResult.results || [place]
        const confidence = (place?.score != null)
          ? Number(place.score)
          : (place?.importance != null)
            ? Math.round(Number(place.importance) * 100)
            : 50
        
        // Check if we have multiple results and low confidence - show disambiguation
        if (allResults.length > 1 && confidence < AUTO_NAV_CONFIDENCE) {
          setDisambiguationCandidates({
            query: navIntent.placeName,
            results: allResults.slice(0, 3) // Show top 3 options
          })
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: `📍 I found multiple locations matching "${navIntent.placeName}". Please select one:`
          }])
          setIsLoading(false)
          return
        }
        
        // High confidence or single result - navigate directly
        setAgentData(prev => ({
          ...prev,
          flyTo: {
            lat: place.lat,
            lng: place.lng,
            zoom: 18
          },
          selectedPlace: place
        }))
        
        // Step 4: Call AI with navigation context for insights
        const aiResponse = await callAI(`The user navigated to ${place.name} (${place.display_name}). Provide brief insights about this area based on the OSM context data.`)
        setMessages(prev => [...prev, { role: 'assistant', content: aiResponse }])
        setIsLoading(false)
        return
      } else {
        // Place not found
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `📍 I couldn't find "${navIntent.placeName}" in our Bangalore database. Try searching for neighborhoods (Hebbal, Koramangala), landmarks, bus stops, or metro stations. You can also click directly on the map.`
        }])
        setIsLoading(false)
        return
      }
    }
    
    // For all other queries (analysis, questions, building info, etc.), use AI
    // Generate smart loading tasks based on query content
    const generateSmartLoadingTasks = (query) => {
      const q = query.toLowerCase()
      const tasks = []
      
      // Always start with understanding
      tasks.push({ id: 'task_0', step: `Understanding: "${query.slice(0, 40)}${query.length > 40 ? '...' : ''}"`, status: 'in_progress' })
      
      // Property search queries
      if (q.includes('property') || q.includes('apartment') || q.includes('flat') || q.includes('bhk') || q.includes('house') || q.includes('villa')) {
        const location = query.match(/in\s+([A-Za-z\s]+)/i)?.[1] || 'area'
        tasks.push({ id: 'task_1', step: `Geocoding location: ${location.trim()}`, status: 'pending' })
        tasks.push({ id: 'task_2', step: 'Searching property database', status: 'pending' })
        if (q.includes('under') || q.includes('below') || q.includes('budget')) {
          tasks.push({ id: 'task_3', step: 'Applying budget filters', status: 'pending' })
        }
        tasks.push({ id: 'task_4', step: 'Calculating distances & amenities', status: 'pending' })
        tasks.push({ id: 'task_5', step: 'Ranking by relevance', status: 'pending' })
      }
      // Analysis queries
      else if (q.includes('analyze') || q.includes('analysis') || q.includes('tell me about') || q.includes('how is')) {
        tasks.push({ id: 'task_1', step: 'Gathering spatial data (POIs, transport)', status: 'pending' })
        tasks.push({ id: 'task_2', step: 'Calculating accessibility scores', status: 'pending' })
        tasks.push({ id: 'task_3', step: 'Fetching market data & trends', status: 'pending' })
        tasks.push({ id: 'task_4', step: 'Analyzing risk factors', status: 'pending' })
        tasks.push({ id: 'task_5', step: 'Generating locality profile', status: 'pending' })
      }
      // Simulation queries
      else if (q.includes('what if') || q.includes('simulate') || q.includes('impact')) {
        tasks.push({ id: 'task_1', step: 'Gathering baseline data', status: 'pending' })
        tasks.push({ id: 'task_2', step: 'Running causal reasoning engine', status: 'pending' })
        tasks.push({ id: 'task_3', step: 'Simulating infrastructure impact', status: 'pending' })
        tasks.push({ id: 'task_4', step: 'Calculating price changes', status: 'pending' })
        tasks.push({ id: 'task_5', step: 'Generating visualization', status: 'pending' })
      }
      // Comparison queries
      else if (q.includes('compare') || q.includes('vs') || q.includes('versus') || q.includes('better')) {
        const locations = query.match(/([A-Z][a-z]+)/g) || ['Location 1', 'Location 2']
        tasks.push({ id: 'task_1', step: `Analyzing ${locations[0] || 'first area'}`, status: 'pending' })
        tasks.push({ id: 'task_2', step: `Analyzing ${locations[1] || 'second area'}`, status: 'pending' })
        tasks.push({ id: 'task_3', step: 'Computing comparative metrics', status: 'pending' })
      }
      // Default for other queries
      else {
        tasks.push({ id: 'task_1', step: 'Gathering relevant context', status: 'pending' })
        tasks.push({ id: 'task_2', step: 'Processing spatial data', status: 'pending' })
        tasks.push({ id: 'task_3', step: 'Analyzing information', status: 'pending' })
      }
      
      // Always end with synthesis
      tasks.push({ id: `task_${tasks.length}`, step: 'Synthesizing AI response', status: 'pending' })
      
      return tasks
    }
    
    // Detect intent for loading UI
    const detectLoadingIntent = (query) => {
      const q = query.toLowerCase()
      if (q.includes('property') || q.includes('apartment') || q.includes('flat') || q.includes('bhk')) return 'property_search'
      if (q.includes('analyze') || q.includes('tell me about')) return 'analyze_area'
      if (q.includes('what if') || q.includes('simulate')) return 'simulate'
      if (q.includes('compare') || q.includes('vs')) return 'comparison'
      if (q.includes('go to') || q.includes('show me') || q.includes('navigate')) return 'navigate'
      return 'general'
    }
    
    const loadingIntent = detectLoadingIntent(userMessage)
    
    // Add streaming message placeholder and capture its index
    // Note: messages.length here is AFTER user message was added (line 892)
    // So the assistant will be at index = current messages.length + 1 (user msg) = messages.length + 1
    // But since we use prev in setMessages, we need to add 1 for the user message
    const placeholderMessageIndex = messages.length + 1
    
    // Add streaming message placeholder
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: '',
      intent: loadingIntent,
      isLoading: true,
      isStreaming: true,
      isThinking: true,
      streamingThought: '',
      streamingContent: '',
      thinkingTime: 0
    }])
    
    // Use streaming API for real-time thinking display
    await callAIStreaming(
      userMessage,
      // onThinkingUpdate - called as thinking tokens arrive
      (thinking, time, isThinking) => {
        setMessages(prev => {
          const newMessages = [...prev]
          if (newMessages[placeholderMessageIndex]) {
            newMessages[placeholderMessageIndex] = {
              ...newMessages[placeholderMessageIndex],
              streamingThought: thinking,
              thinkingTime: time,
              isThinking: isThinking,
              isLoading: isThinking,
              isStreaming: true
            }
          }
          return newMessages
        })
      },
      // onContentUpdate - called as response tokens arrive
      (content, time) => {
        setMessages(prev => {
          const newMessages = [...prev]
          if (newMessages[placeholderMessageIndex]) {
            newMessages[placeholderMessageIndex] = {
              ...newMessages[placeholderMessageIndex],
              streamingContent: content,
              content: content,
              thinkingTime: time,
              isThinking: false,
              isLoading: false,
              isStreaming: true
            }
          }
          return newMessages
        })
      },
      // onComplete - called when streaming is done
      (result) => {
        setMessages(prev => {
          const newMessages = [...prev]
          if (newMessages[placeholderMessageIndex]) {
            newMessages[placeholderMessageIndex] = {
              role: 'assistant',
              content: result.content,
              chainOfThought: result.thinking,
              thinkingTime: result.thinkingTime,
              intent: loadingIntent,
              isLoading: false,
              isStreaming: false,
              isThinking: false,
              isFastResponse: false,
              // Clear streaming fields to prevent duplicate ThinkingDisplay
              streamingThought: null,
              streamingContent: null
            }
          }
          return newMessages
        })
        setIsLoading(false)
      }
    )
    return
    
    // Fallback (old non-streaming code kept for reference)
    const aiResponse = await callAI(userMessage)
    
    // Include reasoning trace, chain-of-thought from the last response
    const reasoningTrace = window.__lastReasoningTrace
    const intent = window.__lastIntent
    const factsSummary = window.__lastFactsSummary
    const chainOfThought = window.__lastChainOfThought || null
    const thinkingTime = window.__lastThinkingTime || 0
    const localityData = window.__lastLocalityData || null
    const isFastResponse = window.__lastFastResponse || false
    
    // Update the placeholder message with actual response
    setMessages(prev => {
      const newMessages = [...prev]
      newMessages[placeholderMessageIndex] = {
        role: 'assistant', 
        content: aiResponse,
        reasoningTrace,
        chainOfThought,
        thinkingTime,
        intent: intent || loadingIntent,
        factsSummary,
        locality: localityData,
        isFastResponse,
        isLoading: false
      }
      return newMessages
    })
    setIsLoading(false)
  }

  // Handle selecting a place from disambiguation list
  const handleSelectPlace = async (place) => {
    setDisambiguationCandidates(null) // Clear disambiguation UI
    setIsLoading(true)
    
    // Navigate to selected place
    setAgentData(prev => ({
      ...prev,
      flyTo: {
        lat: place.lat,
        lng: place.lng,
        zoom: 18
      },
      selectedPlace: place
    }))
    
    // Add user selection as a message
    setMessages(prev => [...prev, { 
      role: 'user', 
      content: `→ ${place.name || place.display_name}` 
    }])
    
    // Get AI insights for selected place
    const aiResponse = await callAI(`The user selected and navigated to ${place.name} (${place.display_name}). Provide brief insights about this area based on the OSM context data.`)
    setMessages(prev => [...prev, { role: 'assistant', content: aiResponse }])
    setIsLoading(false)
  }

  return (
    <div className="flex flex-col h-full" style={{ zoom: `${fontSize}%` }}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-blue-400" />
              </div>
            )}
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === 'user' 
                ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/20' 
                : 'bg-slate-800/80 text-slate-100 border border-slate-700/50 shadow-lg'
            }`}>
              {msg.role === 'assistant' ? (
                <div className="space-y-2">
                  {/* Modern Intent Bubble - Shows what AI is doing */}
                  {msg.intent && !msg.isFastResponse && !msg.isStreaming && (
                    <StatusDisplay intent={msg.intent} isLoading={msg.isLoading && !msg.streamingThought} />
                  )}
                  
                  {/* Unified Thinking Display - handles both streaming and completed states */}
                  {(msg.streamingThought || msg.chainOfThought || msg.isThinking) && (
                    <ThinkingDisplay 
                      thought={msg.chainOfThought}
                      thinkingTime={msg.thinkingTime}
                      isStreaming={msg.isThinking}
                      streamingThought={msg.streamingThought}
                    />
                  )}
                  
                  {/* Loading state - only show if not streaming and no thinking */}
                  {msg.isLoading && !msg.isStreaming && !msg.streamingThought && !msg.isThinking ? (
                    <div className="py-2">
                      <TypingIndicator />
                    </div>
                  ) : (
                    <>
                      
                      {/* Main content - show streaming or final */}
                      {(msg.content || msg.streamingContent) && (
                        <div className="prose prose-invert prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-headings:font-semibold prose-p:my-2 prose-ul:my-2 prose-li:my-0.5 prose-hr:my-3 prose-strong:text-white prose-a:text-blue-400">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content || msg.streamingContent}
                          </ReactMarkdown>
                          {msg.isStreaming && !msg.isThinking && <span className="animate-pulse">▌</span>}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-slate-600 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-slate-200" />
              </div>
            )}
          </div>
        ))}
        {/* Disambiguation UI - Show location options */}
        {disambiguationCandidates && (
          <div className="flex gap-2">
            <div className="w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0">
              <MapPin className="w-4 h-4 text-blue-400" />
            </div>
            <div className="flex-1 space-y-2">
              {disambiguationCandidates.results.map((place, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectPlace(place)}
                  className="w-full text-left bg-slate-800/80 hover:bg-slate-700/80 border border-slate-600/50 hover:border-blue-500/50 rounded-xl px-4 py-3 transition-all group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-white text-sm truncate">
                        {place.name || place.display_name?.split(',')[0]}
                      </div>
                      <div className="text-xs text-slate-400 truncate mt-0.5">
                        {place.display_name || `${place.lat?.toFixed(4)}, ${place.lng?.toFixed(4)}`}
                      </div>
                      {place.type && (
                        <div className="text-xs text-blue-400 mt-1">
                          {place.type}
                        </div>
                      )}
                    </div>
                    <Navigation className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors shrink-0 ml-2" />
                  </div>
                </button>
              ))}
              <button
                onClick={() => setDisambiguationCandidates(null)}
                className="text-xs text-slate-500 hover:text-slate-400 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
        {isLoading && (
          <div className="flex gap-2">
            <div className="w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-blue-400" />
            </div>
            <div className="bg-slate-700/50 rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-700">
        {/* Model Selector - Single Model */}
        <div className="relative mb-2">
          <div className="flex items-center gap-2">
            {/* Active Model Display */}
            <button
              onClick={() => setShowModelSelector(!showModelSelector)}
              className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-300 transition-colors px-2 py-1 rounded hover:bg-slate-700/50"
            >
              <Settings className="w-3 h-3" />
              <span className="text-[10px]">
                {llmConfig.provider === 'local' ? (
                  llmConfig.local_model || 'llama3.2'
                ) : (
                  llmConfig.openrouter_model?.split('/').pop().split(':')[0] || 'llama-3.3-70b'
                )}
              </span>
              <ChevronDown className={`w-3 h-3 transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
            </button>
          </div>
          
          {showModelSelector && (
            <div className="absolute bottom-full left-0 mb-2 bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl z-50 min-w-[320px]">
              <div className="text-xs text-slate-400 mb-2 font-medium">Model Configuration</div>
              
              {/* Provider Toggle */}
              <div className="flex gap-2 mb-3">
                <button
                  onClick={() => saveLlmConfig({ ...llmConfig, provider: 'local' })}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    llmConfig.provider === 'local'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                      : 'bg-slate-700 text-slate-400 border border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <HardDrive className="w-3.5 h-3.5" /> Local (Ollama)
                </button>
                <button
                  onClick={() => saveLlmConfig({ ...llmConfig, provider: 'openrouter' })}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    llmConfig.provider === 'openrouter'
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                      : 'bg-slate-700 text-slate-400 border border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <Cloud className="w-3.5 h-3.5" /> Cloud
                </button>
              </div>
              
              {llmConfig.provider === 'local' && (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Local Model</label>
                  <select
                    value={llmConfig.local_model}
                    onChange={(e) => saveLlmConfig({ ...llmConfig, local_model: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white"
                  >
                    {availableModels.local.length > 0 ? (
                      availableModels.local.map(m => (
                        <option key={m.id} value={m.id}>{m.id}</option>
                      ))
                    ) : (
                      <>
                        <option value="llama3.2">llama3.2</option>
                        <option value="qwen3-vl:4b">qwen3-vl:4b</option>
                        <option value="deepseek-r1:8b">deepseek-r1:8b</option>
                      </>
                    )}
                  </select>
                  <p className="text-[10px] text-slate-500 mt-2">
                    {availableModels.local.length > 0 ? '✓ Ollama connected' : 'Run: ollama serve'}
                  </p>
                </div>
              )}
              
              {llmConfig.provider === 'openrouter' && (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Cloud Model</label>
                  <select
                    value={llmConfig.openrouter_model}
                    onChange={(e) => saveLlmConfig({ ...llmConfig, openrouter_model: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white"
                  >
                    <option value="meta-llama/llama-3.3-70b-instruct:free">Llama 3.3 70B (Free)</option>
                    <option value="google/gemini-2.0-flash-exp:free">Gemini 2.0 Flash (Free)</option>
                    <option value="deepseek/deepseek-r1-0528:free">DeepSeek R1 (Free)</option>
                  </select>
                </div>
              )}
              
              <button
                onClick={() => setShowModelSelector(false)}
                className="w-full mt-3 text-xs text-slate-500 hover:text-slate-400"
              >
                Close
              </button>
            </div>
          )}
        </div>
        
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask me anything about Bangalore real estate..."
            className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-3 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg transition"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  )
}
