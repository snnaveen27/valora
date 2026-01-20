import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, MapPin, Navigation } from 'lucide-react'
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

export default function ChatPanel({ agentData, setAgentData, fontSize = 100 }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '# Welcome to Valora AI\n\nI\'m your GIS assistant for Bangalore.\n\n## What you can do\n- **Navigate** to any location (neighborhoods, landmarks, metro/bus stops)\n- **Analyze** buildings (click on the map)\n- **Explore** POIs, transport, and amenities\n- **Get** area insights from real OSM + terrain data\n\n## Try\n- "Show me Tin Factory"\n- "Show me Airport"\n- "Show me Hebbal"\n- Click any building, then ask: "Tell me about this area"\n\nTip: If a search has multiple matches, I\'ll show you options to choose from.' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [disambiguationCandidates, setDisambiguationCandidates] = useState(null) // For showing multiple location options
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Check backend health on mount
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
    checkBackend()
  }, [])

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
          credits: data.user_credits?.balance ?? prev.credits
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
    setMessages(prev => [...prev, { role: 'assistant', content: aiResponse }])
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
                <div className="prose prose-invert prose-sm max-w-none prose-headings:mt-2 prose-headings:mb-2 prose-p:my-2 prose-ul:my-2 prose-li:my-1 prose-hr:my-3 prose-strong:text-slate-50">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
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
