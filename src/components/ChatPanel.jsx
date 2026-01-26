import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, MapPin, Navigation, Settings, Cloud, HardDrive, ChevronDown, ChevronRight, Brain, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Backend API URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Confidence threshold for auto-navigation (0-100)
const AUTO_NAV_CONFIDENCE = 70

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
                <span className="text-slate-300">{step.description}</span>
                {step.data && typeof step.data === 'object' && (
                  <div className="mt-1 text-slate-500 bg-slate-800/50 rounded px-2 py-1">
                    {Object.entries(step.data).slice(0, 3).map(([k, v]) => (
                      <span key={k} className="mr-2">
                        <span className="text-slate-400">{k}:</span> {String(v).slice(0, 30)}
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

export default function ChatPanel({ agentData, setAgentData, fontSize = 100 }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `# 🏙️ Welcome to Valora AI

Your intelligent city assistant for **Bangalore real estate & urban intelligence**.

---

## 🎯 What I Can Do

### 🗺️ Navigation & Exploration
- **"Go to Koramangala"** — Fly to any neighborhood
- **"Show me Hebbal Lake"** — Navigate to landmarks
- **"Where is Indiranagar Metro?"** — Find transport stops

### 🏢 Property Intelligence
- **"Find 3BHK apartments in Whitefield under 1.5Cr"**
- **"Compare properties in HSR Layout vs BTM"**
- **"What's the price trend in Electronic City?"**

### 📊 Area Analysis
- **Click any building** on the map for instant analysis
- **"Analyze this area"** — Get walkability, POIs, transport scores
- **"What's nearby?"** — Discover amenities around you

### 🔮 Simulations
- **"What if a metro station opens near Sarjapur?"**
- **"Simulate infrastructure impact on property values"**

---

## 🚀 Quick Start
Try: **"Show me the best areas for investment"** or click anywhere on the map!

*Powered by local data — works completely offline* ✨` }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [disambiguationCandidates, setDisambiguationCandidates] = useState(null) // For showing multiple location options
  const [showModelSelector, setShowModelSelector] = useState(false)
  const [llmConfig, setLlmConfig] = useState({
    provider: 'local', // 'local' or 'openrouter'
    local_model: 'llama3.2',
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

  // Save LLM config when changed
  const saveLlmConfig = async (newConfig) => {
    setLlmConfig(newConfig)
    try {
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

  // Call backend AI chat endpoint with full context
  const callAI = async (userMessage) => {
    try {
      // Build context payload with all available map/building data
      const context = {
        selectedBuilding: agentData?.selectedBuilding || null,
        selectedLocation: agentData?.selectedLocation || null,
        selectedPlace: agentData?.selectedPlace || null,
        mapCenter: agentData?.mapCenter || null,
        viewport: {
          buildingsCount: agentData?.buildingsCount || 0,
          zoom: agentData?.zoom || 'medium'
        }
      }

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
        })
      })

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
          credits: data.user_credits?.balance ?? prev.credits,
          lastReasoningTrace: data.reasoning_trace || null
        }))
      }
      
      // Store reasoning trace for UI display
      window.__lastReasoningTrace = data.reasoning_trace || null
      window.__lastIntent = data.intent || null
      window.__lastFactsSummary = data.facts_summary || null

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
        }
      }

      return data.message || data.assistant_message || ''
    } catch (err) {
      console.error('AI call failed:', err)
      return `⚠️ AI service temporarily unavailable. ${err.message}\n\nPlease try again in a moment.`
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
    const aiResponse = await callAI(userMessage)
    // Include reasoning trace from the last response
    const reasoningTrace = window.__lastReasoningTrace
    const intent = window.__lastIntent
    const factsSummary = window.__lastFactsSummary
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: aiResponse,
      reasoningTrace,
      intent,
      factsSummary
    }])
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
            <div className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
              msg.role === 'user' 
                ? 'bg-blue-500 text-white' 
                : 'bg-slate-800/70 text-slate-100 border border-slate-700/60'
            }`}>
              {msg.role === 'assistant' ? (
                <>
                  {/* Collapsible Thinking/Reasoning UI */}
                  {msg.reasoningTrace && msg.reasoningTrace.steps && msg.reasoningTrace.steps.length > 0 && (
                    <ThinkingPanel 
                      trace={msg.reasoningTrace} 
                      intent={msg.intent}
                      factsSummary={msg.factsSummary}
                    />
                  )}
                  <div className="prose prose-invert prose-sm max-w-none prose-headings:mt-2 prose-headings:mb-2 prose-p:my-2 prose-ul:my-2 prose-li:my-1 prose-hr:my-3 prose-strong:text-slate-50">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </>
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
        {/* Model Selector */}
        <div className="relative mb-2">
          <button
            onClick={() => setShowModelSelector(!showModelSelector)}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-300 transition-colors"
          >
            {llmConfig.provider === 'local' ? (
              <><HardDrive className="w-3 h-3" /> Local: {llmConfig.local_model}</>
            ) : (
              <><Cloud className="w-3 h-3" /> Cloud: {llmConfig.openrouter_model.split('/').pop()}</>
            )}
            <ChevronDown className={`w-3 h-3 transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
          </button>
          
          {showModelSelector && (
            <div className="absolute bottom-full left-0 mb-2 bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl z-50 min-w-[280px]">
              <div className="text-xs text-slate-400 mb-2 font-medium">LLM Provider</div>
              <div className="flex gap-2 mb-3">
                <button
                  onClick={() => saveLlmConfig({ ...llmConfig, provider: 'local' })}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    llmConfig.provider === 'local'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                      : 'bg-slate-700 text-slate-400 border border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <HardDrive className="w-3.5 h-3.5" /> Local (Offline)
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
              
              {availableModels.loading ? (
                <div className="text-center py-3">
                  <div className="text-xs text-slate-400">Loading available models...</div>
                </div>
              ) : llmConfig.provider === 'local' ? (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
                    Local Model {availableModels.local.length > 0 && <span className="text-green-400">({availableModels.local.length} available)</span>}
                  </label>
                  {availableModels.local_error ? (
                    <div className="text-xs text-red-400 bg-red-500/10 rounded p-2 mb-2">{availableModels.local_error}</div>
                  ) : null}
                  <select
                    value={llmConfig.local_model}
                    onChange={(e) => saveLlmConfig({ ...llmConfig, local_model: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white"
                  >
                    {availableModels.local.length > 0 ? (
                      availableModels.local.map(m => (
                        <option key={m.id} value={m.id}>{m.id} {m.size ? `(${(m.size / 1e9).toFixed(1)}GB)` : ''}</option>
                      ))
                    ) : (
                      <>
                        <option value="llama3.2">llama3.2 (pull with: ollama pull llama3.2)</option>
                        <option value="llama3.1">llama3.1</option>
                        <option value="mistral">mistral</option>
                      </>
                    )}
                  </select>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {availableModels.local.length > 0 ? '✓ Ollama connected' : 'Start Ollama to see available models'}
                  </p>
                </div>
              ) : (
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
                    Cloud Model {availableModels.openrouter.length > 0 && <span className="text-blue-400">({availableModels.openrouter.length} free)</span>}
                  </label>
                  {availableModels.openrouter_error ? (
                    <div className="text-xs text-red-400 bg-red-500/10 rounded p-2 mb-2">{availableModels.openrouter_error}</div>
                  ) : null}
                  <select
                    value={llmConfig.openrouter_model}
                    onChange={(e) => saveLlmConfig({ ...llmConfig, openrouter_model: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm text-white max-h-48 overflow-y-auto"
                  >
                    {availableModels.openrouter.length > 0 ? (
                      availableModels.openrouter.slice(0, 20).map(m => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))
                    ) : (
                      <>
                        <option value="meta-llama/llama-3.3-70b-instruct:free">Llama 3.3 70B (Free)</option>
                        <option value="google/gemini-2.0-flash-exp:free">Gemini 2.0 Flash (Free)</option>
                        <option value="deepseek/deepseek-r1-0528:free">DeepSeek R1 (Free)</option>
                      </>
                    )}
                  </select>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {availableModels.openrouter.length > 0 ? '✓ OpenRouter connected' : 'Add API key in Admin Panel'}
                  </p>
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
            placeholder="Ask about locations..."
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
