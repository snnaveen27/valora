import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Brain, TrendingUp, Map, Target, AlertCircle, Check, Sparkles, Plus, Minus, MapPin, RefreshCw } from 'lucide-react'
import axios from 'axios'
import VoiceInput from './VoiceInput'

const ChatPanelMultiAgent = ({ isMaximized, onAgentResponse }) => {
  // Resolve backend URL from Vite env (preferred), optional global, or default
  const resolved = (import.meta?.env?.VITE_BACKEND_URL || (typeof window !== 'undefined' ? window.__BACKEND_URL__ : '') || 'http://localhost:8000')
  const backendURL = String(resolved).replace(/\/$/, '')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Welcome to Valora AI for Bangalore Real Estate!\n\nI can help you navigate, analyze, and invest in properties. Ask me anything or try a quick action.",
      type: 'greeting'
    }
  ])
  const [showQuickActions, setShowQuickActions] = useState(false)
  const [messageFontPx, setMessageFontPx] = useState(14)
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activePlan, setActivePlan] = useState(null)
  const [planStatus, setPlanStatus] = useState([])
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const handleFileAnalysis = async (event) => {
      const { fileName, fileType, fileSize, isBinary, fileContent, fullPrompt } = event.detail
      
      setMessages(prev => [...prev, { 
        role: 'user', 
        content: `📄 Analyzing file: ${fileName} (${fileType || 'document'}, ${(fileSize / 1024).toFixed(1)} KB)` 
      }])
      
      setIsLoading(true)
      
      try {
        const response = await axios.post(`/api/agent/plan`, {
          user_id: 'user_' + Date.now(),
          intent: fullPrompt || `Analyze this real estate file: ${fileName}`,
          context: { 
            file_name: fileName,
            file_type: fileType,
            file_size: fileSize,
            is_binary: isBinary,
            file_content_preview: fileContent?.substring(0, 1000)
          }
        })
        
        const data = response.data
        
        let responseContent = data.chat_response
        if (!responseContent || responseContent.length < 50) {
          if (isBinary) {
            responseContent = `📄 **File Uploaded:** ${fileName}\n\n⚠️ **Binary File Limitation**\n\nI received a ${fileType?.includes('word') ? 'Word Document' : fileType?.includes('pdf') ? 'PDF' : 'binary'} file. Unfortunately, I cannot directly read binary file formats (DOCX, PDF, XLS).\n\n**Here's how to analyze your file:**\n\n1️⃣ **Convert to Text:**\n   - Open the file in Word/Excel/PDF reader\n   - Copy the content (Ctrl+A, Ctrl+C)\n   - Paste into chat and ask me to analyze\n\n2️⃣ **Save as TXT/CSV:**\n   - File → Save As → Plain Text (.txt)\n   - Then re-upload the TXT file\n\n3️⃣ **Share Key Details:**\n   - Tell me what's in the file\n   - Share property details, prices, locations\n   - I'll provide analysis based on your input\n\n**What I can help with:**\n✅ Property valuation analysis\n✅ Investment recommendations\n✅ Market trend insights\n✅ Location comparison\n✅ ROI calculations\n\nWhat specific information from "${fileName}" would you like to discuss?`
          } else {
            const contentPreview = fileContent?.substring(0, 500) || ''
            responseContent = `📄 **Analyzing:** ${fileName}\n\n📊 **File Details:**\n- Format: ${fileType || 'Text Document'}\n- Size: ${(fileSize / 1024).toFixed(1)} KB\n\n${contentPreview ? `📝 **Content Found:**\n\`\`\`\n${contentPreview}...\n\`\`\`\n\n` : ''}💡 **Real Estate Analysis:**\n\nI can help you analyze:\n\n1. **Property Details** - Price, size, location, amenities\n2. **Market Trends** - Current pricing, demand patterns\n3. **Investment Potential** - ROI, appreciation forecast\n4. **Location Analysis** - Neighborhood advantages\n5. **Comparative Data** - Similar properties comparison\n\n**What would you like to know about the data in this file?**`
          }
        }
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: responseContent,
          type: 'file_analysis',
          data: data
        }])
        
        if (onAgentResponse) {
          onAgentResponse(data)
        }
      } catch (error) {
        console.error('File analysis error:', error)
        
        let fallbackContent
        if (isBinary) {
          fallbackContent = `📄 **File:** ${fileName}\n\n⚠️ **Cannot Read Binary Files**\n\nI cannot directly analyze ${fileType?.includes('word') ? 'Word documents' : fileType?.includes('pdf') ? 'PDFs' : 'binary files'} (DOCX, PDF, XLS).\n\n**Solution Options:**\n\n**Option 1: Copy & Paste** 📋\nOpen your file → Select all text → Paste here\n\n**Option 2: Convert Format** 🔄\nSave as Plain Text (.txt) → Re-upload\n\n**Option 3: Share Details** 💬\nTell me about:\n• Property locations and prices\n• Investment goals\n• Specific questions\n\n**I'm Ready to Help With:**\n✅ Property valuation & pricing\n✅ Investment analysis & ROI\n✅ Market trends & forecasts\n✅ Location comparisons\n✅ Risk assessment\n\nWhat information from "${fileName}" can I help you analyze?`
        } else {
          const hasContent = fileContent && fileContent.trim().length > 10
          fallbackContent = `📄 **File:** ${fileName} (${(fileSize / 1024).toFixed(1)} KB)\n\n${hasContent ? `✅ **Content Detected**\n\nI can see text content in your file. ` : `⚠️ **No Content Found**\n\nThe file appears empty or unreadable. `}\n\n**Real Estate Analysis Available:**\n\n📊 **Property Analysis**\n• Price evaluation\n• Location assessment\n• Investment potential\n\n📈 **Market Insights**\n• Current trends\n• Demand patterns\n• Growth forecasts\n\n💰 **Investment Guidance**\n• ROI calculations\n• Risk assessment\n• Portfolio recommendations\n\n${hasContent ? 'What specific aspect would you like me to analyze?' : 'Please share the key details you need help with.'}`
        }
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: fallbackContent,
          type: 'file_analysis'
        }])
      } finally {
        setIsLoading(false)
      }
    }
    
    window.addEventListener('analyze-file', handleFileAnalysis)
    return () => window.removeEventListener('analyze-file', handleFileAnalysis)
  }, [backendURL, onAgentResponse])

  const advancedActions = [
    { text: "3BHK in HSR <1.5Cr", full: "Find 3BHK apartments in HSR Layout under 1.5 crore", category: "search", icon: "🏠" },
    { text: "Investment hotspots", full: "Show investment hotspots in Bangalore", category: "analysis", icon: "💰" },
    { text: "Compare areas", full: "Compare Whitefield vs Electronic City", category: "analysis", icon: "📊" },
    { text: "2km radius zone", full: "Draw 2km radius around Manyata Tech Park", category: "map", icon: "⭕" },
    { text: "Near metro", full: "Properties near metro stations", category: "search", icon: "🚇" },
    { text: "Rental yield", full: "Best areas for rental yield", category: "analysis", icon: "🎯" }
  ]

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!inputMessage.trim() || isLoading) return

    const userMessage = inputMessage.trim()
    setInputMessage('')
    
    // Add user message to chat
    setMessages(prev => [...prev, { 
      role: 'user', 
      content: userMessage 
    }])
    
    setIsLoading(true)
    setPlanStatus([])

    try {
      // Call multi-agent system
      const response = await axios.post(`/api/agent/plan`, {
        user_id: 'user_' + Date.now(),
        intent: userMessage,
        context: {
          preferences: {
            investment_horizon: "3-5 years",
            risk_tolerance: "medium"
          }
        }
      })

      const data = response.data
      setActivePlan(data.plan_id)

      // Show agent execution status
      if (data.plan?.tasks) {
        const statuses = data.plan.tasks.map(task => ({
          agent: getAgentName(task.agent),
          action: task.action,
          status: task.status,
          icon: getAgentIcon(task.agent)
        }))
        setPlanStatus(statuses)
      }

      // Add AI response to chat with structured content
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.chat_response || "I've completed the analysis. Please check the panels for detailed results.",
        type: 'agent_response',
        data: data,
        confidence: data.confidence,
        recommendations: data.final_result?.recommendations
      }])

      // Notify parent component to update panels
      if (onAgentResponse) {
        onAgentResponse(data)
      }

      // Handle map action if present
      if (data.map_action) {
        console.log('🗺️ Dispatching map action from multi-agent:', data.map_action)
        window.dispatchEvent(new CustomEvent('valora-map-command', {
          detail: data.map_action
        }))
      }

    } catch (error) {
      console.error('Multi-agent error:', error)

      const status = error.response?.status
      const detail = error.response?.data?.detail || error.message

      const errorMessage = status
        ? `Sorry, I encountered an error (HTTP ${status}). ${detail || ''}`
        : `Sorry, I encountered a network error. Please check that the backend is reachable.`

      setMessages(prev => {
        // Avoid duplicating the exact same last error message
        const last = prev[prev.length - 1]
        if (last && last.type === 'error' && last.content === errorMessage) return prev
        return [...prev, { 
          role: 'assistant', 
          content: errorMessage, 
          type: 'error',
          retryMessage: userMessage
        }]
      })
    } finally {
      setIsLoading(false)
    }
  }

  const getAgentName = (agent) => {
    const names = {
      'planner': 'Planner',
      'map_agent': 'Map Analyst',
      'forecaster': 'Forecaster',
      'recommender': 'Recommender',
      'critic': 'Validator'
    }
    return names[agent] || agent
  }

  const getAgentIcon = (agent) => {
    const icons = {
      'planner': Brain,
      'map_agent': Map,
      'forecaster': TrendingUp,
      'recommender': Target,
      'critic': Check
    }
    return icons[agent] || Brain
  }

  const handleQuickQuery = (query) => {
    setInputMessage(query)
    setShowQuickActions(false)
  }

  const renderMessage = (message, index) => {
    if (message.role === 'user') {
      return (
        <div key={index} className="flex gap-3 justify-end">
          <div className="max-w-[75%] rounded-2xl px-4 py-2 bg-purple-600 text-white rounded-br-none">
            <p className="whitespace-pre-wrap" style={{fontSize: messageFontPx}}>{message.content}</p>
          </div>
          <div className="flex-shrink-0 w-8 h-8 bg-purple-600/20 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-purple-600" />
          </div>
        </div>
      )
    }

    // Assistant messages with different types
    return (
      <div key={index} className="flex gap-3 justify-start">
        <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
        
        <div className="max-w-[85%] space-y-2">
          {/* Main message content */}
          <div className="rounded-2xl rounded-bl-none px-4 py-3 bg-gradient-to-br from-purple-950/60 to-purple-900/40 text-neutral-100 border border-purple-700/30">
            {message.type === 'agent_response' && typeof message.confidence === 'number' && message.confidence > 0 && (
              <div className="flex items-center gap-2 mb-2 pb-2 border-b border-purple-800/20">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                <span className="text-xs text-neutral-400">
                  AI Confidence: <span className="text-blue-400 font-semibold">{(message.confidence * 100).toFixed(0)}%</span>
                </span>
              </div>
            )}
            
            <div className="prose prose-invert max-w-none" style={{fontSize: messageFontPx}}>
              {message.content.split('\n').map((line, i) => {
                if (line.startsWith('**') && line.endsWith('**')) {
                  return <h4 key={i} className="font-semibold text-white mt-2 mb-1">{line.replace(/\*\*/g, '')}</h4>
                }
                if (line.startsWith('•') || line.startsWith('-')) {
                  return <li key={i} className="ml-4 text-neutral-300">{line.substring(1).trim()}</li>
                }
                return <p key={i} className="text-neutral-300">{line}</p>
              })}
            </div>
          </div>

          {/* Show recommendations if available */}
          {message.recommendations && message.recommendations.length > 0 && (
            <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 rounded-lg p-3 border border-indigo-700/30">
              <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-1">
                <Target className="w-3 h-3" />
                Quick Actions - View on Map
              </h4>
              <div className="space-y-1">
                {message.recommendations.slice(0, 3).map((rec, i) => (
                  <button
                    key={i}
                    className="w-full text-left p-2 bg-purple-950/50 hover:bg-purple-700/60 hover:border-purple-500 border border-purple-800/50 rounded-lg transition-all text-xs group"
                    onClick={() => {
                      // Show properties for this zone on the map
                      window.dispatchEvent(new CustomEvent('valora-map-command', {
                        detail: {
                          action: 'showProperties',
                          location: rec.zone_name,
                          coordinates: rec.coordinates || null,
                          zoom: 14
                        }
                      }));
                    }}
                    title={`View ${rec.zone_name} on map`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-white font-medium group-hover:text-purple-300 transition-colors flex items-center gap-1">
                        <span className="text-purple-400">📍</span> {rec.zone_name}
                      </span>
                      <span className="text-green-400">₹{(rec.current_price/100000).toFixed(1)}L</span>
                    </div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">Growth: {rec.growth_potential?.[2]?.toFixed(1)}% • Grade: {rec.investment_grade}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Error messages with retry */}
          {message.type === 'error' && (
            <div className="bg-red-900/20 border border-red-700/30 rounded-lg p-3">
              <div className="flex items-start gap-2 mb-2">
                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <span className="text-xs text-red-300">{message.content}</span>
              </div>
              {message.retryMessage && (
                <button
                  onClick={() => {
                    setInputMessage(message.retryMessage)
                    // Remove this error message
                    setMessages(prev => prev.filter((_, i) => i !== index))
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-800/30 hover:bg-red-700/40 text-red-200 rounded-md transition-colors border border-red-700/50"
                >
                  <RefreshCw className="w-3 h-3" />
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0612]">
      {/* Compact Header */}
      <div className="px-3 py-2 border-b border-purple-700/30 bg-[#100820]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-semibold text-white">Valora</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('valora-map-command', { detail: { action: 'startMarker' } }))}
              className="px-2 py-1 text-xs rounded-md bg-purple-700/40 hover:bg-purple-600/50 text-purple-200 border border-purple-600/50 flex items-center gap-1"
              title="Analyze Pin"
            >
              <MapPin className="w-3 h-3" />
              Analyze Pin
            </button>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setMessageFontPx(v => Math.max(12, v - 1))}
                className="p-1 rounded-md border border-purple-700/50 text-purple-200 hover:bg-purple-900/50"
                title="Decrease font size"
              >
                <Minus className="w-3 h-3" />
              </button>
              <button
                onClick={() => setMessageFontPx(v => Math.min(18, v + 1))}
                className="p-1 rounded-md border border-purple-700/50 text-purple-200 hover:bg-purple-900/50"
                title="Increase font size"
              >
                <Plus className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
        {planStatus.length > 0 && (
          <div className="mt-2">
            <div className="flex flex-wrap gap-1.5">
              {planStatus.map((status, i) => {
                const Icon = status.icon
                const isCompleted = status.status === 'completed'
                const isFailed = status.status === 'failed'
                return (
                  <div
                    key={i}
                    className={`px-2 py-0.5 rounded-full text-[10px] flex items-center gap-1 transition-all
                      ${isCompleted ? 'bg-green-600/30 text-green-300 border border-green-500/50' :
                        isFailed ? 'bg-red-600/30 text-red-300 border border-red-500/50' :
                        'bg-purple-900/50 text-purple-200 border border-purple-600/50 animate-pulse'}`}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{status.agent}</span>
                    {isCompleted && <Check className="w-3 h-3" />}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3 chat-scroll">
        {messages.map((message, index) => renderMessage(message, index))}
        
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center">
              <Bot className="w-5 h-5 text-white animate-pulse" />
            </div>
            <div className="bg-gradient-to-r from-purple-900/50 via-purple-800/50 to-purple-900/50 rounded-2xl rounded-bl-none px-4 py-3 border border-purple-600/50 animate-pulse">
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
                  <div className="absolute inset-0 w-5 h-5 animate-ping opacity-20">
                    <Loader2 className="w-5 h-5 text-purple-400" />
                  </div>
                </div>
                <span className="text-sm text-purple-200 font-medium">Coordinating 5 AI agents...</span>
              </div>
              <div className="mt-2 flex items-center gap-1">
                <div className="h-1 w-12 bg-purple-600 rounded-full animate-pulse"></div>
                <div className="h-1 w-8 bg-purple-500 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                <div className="h-1 w-16 bg-purple-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                <div className="h-1 w-10 bg-purple-500 rounded-full animate-pulse" style={{animationDelay: '0.6s'}}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-3 py-2 border-t border-purple-700/30 bg-[#0d0718]">
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={() => window.dispatchEvent(new CustomEvent('valora-map-command', { detail: { action: 'center', coordinates: [12.9716, 77.5946], zoom: 12 } }))}
            className="px-2 py-1 rounded-md bg-purple-700/30 hover:bg-purple-700/50 text-purple-200 border border-purple-600/40"
          >Center BLR</button>
          <button
            onClick={() => window.dispatchEvent(new CustomEvent('valora-map-command', { detail: { action: 'startMarker' } }))}
            className="px-2 py-1 rounded-md bg-purple-700/30 hover:bg-purple-700/50 text-purple-200 border border-purple-600/40"
          >Analyze Pin</button>
        </div>
      </div>

      {!inputMessage && messages.length <= 1 && (
        <div className="px-3 pb-2">
          <button
            onClick={() => setShowQuickActions(!showQuickActions)}
            className="w-full text-xs text-purple-400 hover:text-purple-300 py-1.5 flex items-center justify-center gap-1 transition-colors"
          >
            <Sparkles className="w-3 h-3" />
            {showQuickActions ? 'Hide' : 'Show'} Quick Actions
          </button>
          
          {showQuickActions && (
            <div className="flex gap-2 overflow-x-auto pb-2 mt-2 quick-scroll">
              {advancedActions.map((action, i) => (
                <button
                  key={i}
                  onClick={() => handleQuickQuery(action.full)}
                  className="flex-shrink-0 px-3 py-1.5 text-xs rounded-full transition-all border bg-[#120a23]/70 hover:bg-[#1b0f32] border-purple-700/50 hover:border-purple-400 text-purple-200 hover:text-white shadow-sm"
                  title={action.full}
                >
                  <span>{action.icon} {action.text}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSendMessage} className="px-3 py-3 border-t border-purple-700/30 bg-[#100820]">
        <div className="flex gap-2 items-center">
          {/* Voice Input */}
          <VoiceInput
            onTranscript={(text) => {
              setInputMessage(text);
              // Auto-submit after voice input
              setTimeout(() => {
                const form = document.querySelector('form');
                if (form && text.trim()) {
                  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                }
              }, 100);
            }}
            onError={(err) => console.error('Voice error:', err)}
            disabled={isLoading}
          />
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask about properties, or use voice 🎤"
            disabled={isLoading}
            className="flex-1 bg-purple-950/50 text-white text-sm placeholder-purple-300/50 rounded-lg px-3 py-2 
                     border border-purple-700/50 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500/30
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 
                     text-white rounded-lg px-3 py-2 flex items-center justify-center
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        {isLoading && (
          <div className="mt-2 flex items-center gap-2 text-[10px] text-purple-400 justify-center">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>AI agents working...</span>
          </div>
        )}
      </form>
    </div>
  )
}

export default ChatPanelMultiAgent
