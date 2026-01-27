import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, MapPin, Navigation, Settings, Cloud, HardDrive, ChevronDown, ChevronRight, Brain, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Backend API URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

// Task List Component - Windsurf-style task progress display
function TaskListPanel({ tasks, isExpanded = true }) {
  const [expanded, setExpanded] = useState(isExpanded)
  
  if (!tasks || tasks.length === 0) return null
  
  const completedCount = tasks.filter(t => t.status === 'completed').length
  const inProgressTask = tasks.find(t => t.status === 'in_progress')
  
  return (
    <div className="mb-3 bg-slate-800/50 rounded-lg border border-slate-700/50 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-purple-400">📋</span>
          <span className="text-slate-300 font-medium">Tasks</span>
          <span className="text-slate-500">({completedCount}/{tasks.length})</span>
        </div>
        {expanded ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />}
      </button>
      
      {expanded && (
        <div className="px-3 pb-3 space-y-1.5">
          {tasks.map((task, idx) => (
            <div 
              key={idx} 
              className={`flex items-start gap-2 text-xs ${
                task.status === 'in_progress' ? 'bg-blue-500/10 rounded px-2 py-1.5 -mx-2' : ''
              }`}
            >
              {task.status === 'completed' ? (
                <span className="text-green-400 mt-0.5">✓</span>
              ) : task.status === 'in_progress' ? (
                <Loader2 className="w-3 h-3 text-blue-400 animate-spin mt-0.5" />
              ) : (
                <span className="w-3 h-3 rounded border border-slate-600 mt-0.5" />
              )}
              <span className={`flex-1 ${
                task.status === 'completed' ? 'text-slate-500 line-through' :
                task.status === 'in_progress' ? 'text-blue-300' : 'text-slate-400'
              }`}>
                {task.content || task.step}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
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
      
      // Store reasoning trace and tasks for UI display
      window.__lastReasoningTrace = data.reasoning_trace || null
      window.__lastIntent = data.intent || null
      window.__lastFactsSummary = data.facts_summary || null
      window.__lastTasks = data.tasks || null
      
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
    // Include reasoning trace and tasks from the last response
    const reasoningTrace = window.__lastReasoningTrace
    const intent = window.__lastIntent
    const factsSummary = window.__lastFactsSummary
    const tasks = window.__lastTasks || null
    // Get locality data for inline card display
    const localityData = window.__lastLocalityData || null
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: aiResponse,
      reasoningTrace,
      intent,
      factsSummary,
      tasks,
      locality: localityData
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
                  {/* Task List - Windsurf style */}
                  {msg.tasks && msg.tasks.length > 0 && (
                    <TaskListPanel tasks={msg.tasks} isExpanded={true} />
                  )}
                  
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
        {/* Model Selector - 3 Model Types */}
        <div className="relative mb-2">
          <div className="flex items-center gap-2">
            {/* Model Type Quick Selector */}
            <div className="flex bg-slate-700/50 rounded-lg p-0.5">
              <button
                onClick={() => saveLlmConfig({ ...llmConfig, active_model_type: 'primary' })}
                className={`px-2 py-1 text-[10px] rounded transition-all ${
                  llmConfig.active_model_type === 'primary'
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Primary: qwen3-vl:8b - Best quality"
              >
                🎯 Quality
              </button>
              <button
                onClick={() => saveLlmConfig({ ...llmConfig, active_model_type: 'fast' })}
                className={`px-2 py-1 text-[10px] rounded transition-all ${
                  llmConfig.active_model_type === 'fast'
                    ? 'bg-green-500 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Fast: llama3.2 - Quick responses"
              >
                ⚡ Fast
              </button>
              <button
                onClick={() => saveLlmConfig({ ...llmConfig, active_model_type: 'reasoning' })}
                className={`px-2 py-1 text-[10px] rounded transition-all ${
                  llmConfig.active_model_type === 'reasoning'
                    ? 'bg-blue-500 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Reasoning: deepseek-r1:8b - Complex analysis"
              >
                🧠 Deep
              </button>
            </div>
            
            {/* Active Model Display */}
            <button
              onClick={() => setShowModelSelector(!showModelSelector)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <span className="text-[10px]">
                {llmConfig.provider === 'local' ? (
                  llmConfig.active_model_type === 'reasoning' ? llmConfig.local_model_reasoning :
                  llmConfig.active_model_type === 'fast' ? llmConfig.local_model_fast :
                  llmConfig.local_model
                ) : (
                  llmConfig.openrouter_model.split('/').pop().split(':')[0]
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
                <div className="space-y-2">
                  <div className="text-[10px] text-slate-500 mb-1">Configure models for each mode:</div>
                  
                  {/* Primary Model */}
                  <div className="flex items-center gap-2">
                    <span className="text-purple-400 text-[10px] w-16">🎯 Quality</span>
                    <select
                      value={llmConfig.local_model}
                      onChange={(e) => saveLlmConfig({ ...llmConfig, local_model: e.target.value })}
                      className="flex-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-white"
                    >
                      {availableModels.local.length > 0 ? (
                        availableModels.local.map(m => (
                          <option key={m.id} value={m.id}>{m.id}</option>
                        ))
                      ) : (
                        <>
                          <option value="qwen3-vl:8b">qwen3-vl:8b</option>
                          <option value="qwen3-vl:4b">qwen3-vl:4b</option>
                          <option value="llama3.2">llama3.2</option>
                        </>
                      )}
                    </select>
                  </div>
                  
                  {/* Fast Model */}
                  <div className="flex items-center gap-2">
                    <span className="text-green-400 text-[10px] w-16">⚡ Fast</span>
                    <select
                      value={llmConfig.local_model_fast}
                      onChange={(e) => saveLlmConfig({ ...llmConfig, local_model_fast: e.target.value })}
                      className="flex-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-white"
                    >
                      {availableModels.local.length > 0 ? (
                        availableModels.local.map(m => (
                          <option key={m.id} value={m.id}>{m.id}</option>
                        ))
                      ) : (
                        <>
                          <option value="llama3.2">llama3.2</option>
                          <option value="qwen3-vl:4b">qwen3-vl:4b</option>
                        </>
                      )}
                    </select>
                  </div>
                  
                  {/* Reasoning Model */}
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400 text-[10px] w-16">🧠 Deep</span>
                    <select
                      value={llmConfig.local_model_reasoning}
                      onChange={(e) => saveLlmConfig({ ...llmConfig, local_model_reasoning: e.target.value })}
                      className="flex-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-white"
                    >
                      {availableModels.local.length > 0 ? (
                        availableModels.local.map(m => (
                          <option key={m.id} value={m.id}>{m.id}</option>
                        ))
                      ) : (
                        <>
                          <option value="deepseek-r1:8b">deepseek-r1:8b</option>
                          <option value="qwen3-vl:8b">qwen3-vl:8b</option>
                        </>
                      )}
                    </select>
                  </div>
                  
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
