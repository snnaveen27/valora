import { useEffect, useState } from 'react'
import OnlineOSMMap from '../spatial/OnlineOSMMap'
import AnalysisPanel from './AnalysisPanel'
import ChatPanel from './ChatPanel'
import { Sparkles, Maximize2, Minimize2, X, ChevronRight, ChevronLeft, Wallet, TrendingUp, FileText, StickyNote } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function MainApp() {
  const [agentData, setAgentData] = useState({})
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('insights')
  const [analysisWidth, setAnalysisWidth] = useState('narrow') // narrow or wide
  const [chatWidth, setChatWidth] = useState('narrow') // narrow or wide
  const [credits, setCredits] = useState(null)

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
    const fetchCredits = async () => {
      try {
        const resp = await fetch(`${API_URL}/api/credits/user_demo`)
        if (resp.ok) {
          const data = await resp.json()
          setCredits(data.balance)
        }
      } catch (err) {
        console.warn('Failed to fetch credits:', err)
      }
    }
    
    fetchCredits()
    // Refresh credits every minute
    const interval = setInterval(fetchCredits, 60000)
    
    const handleUICommand = (e) => {
      const { action, value, panel, tab } = e.detail || {}
      
      // Update credits if a deduction happened
      if (action === 'creditUpdate') {
        fetchCredits()
      }

      const targetTab = value || tab

      if (action === 'switchTab' && targetTab) {
        // Map old tab names to new 'insights' tab
        if (targetTab === 'analysis' || targetTab === 'market') {
          setActiveTab('insights')
        } else {
          setActiveTab(targetTab)
        }
      }

      if (action === 'openPanel') {
        if ((value || panel) === 'analysis' || (value || panel) === 'insights') setIsAnalysisOpen(true)
        if ((value || panel) === 'chat') setIsChatOpen(true)
      }

      if (action === 'closePanel') {
        if ((value || panel) === 'analysis' || (value || panel) === 'insights') setIsAnalysisOpen(false)
        if ((value || panel) === 'chat') setIsChatOpen(false)
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

        {/* Credits Display */}
        {credits !== null && (
          <div className="flex items-center gap-2 px-3 py-1 bg-slate-700/50 rounded-full border border-slate-600">
            <Wallet className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-white text-xs font-bold">{credits}</span>
            <span className="text-slate-400 text-[10px]">credits</span>
          </div>
        )}
      </div>

      {/* Main Content - 3 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Analysis Panel */}
        <div 
          className="h-full bg-slate-800 border-r border-slate-700 flex flex-col transition-all duration-300 shrink-0"
          style={{
            width: isAnalysisOpen 
              ? (analysisWidth === 'wide' ? 'calc(50% - 160px)' : 'calc(33% - 107px)')
              : '32px',
            minWidth: isAnalysisOpen ? '280px' : '0px'
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
                  <button 
                    onClick={toggleAnalysisWidth} 
                    className="p-1 text-slate-500 hover:text-white transition rounded hover:bg-slate-700"
                    title={analysisWidth === 'narrow' ? 'Expand' : 'Shrink'}
                  >
                    {analysisWidth === 'narrow' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                  </button>
                  <button 
                    onClick={() => setIsAnalysisOpen(false)} 
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
        <div className="flex-1 h-full min-w-0">
          <OnlineOSMMap
            onAnalysisUpdate={handleAnalysisUpdate}
            agentData={agentData}
            setAgentData={setAgentData}
          />
        </div>

        {/* Right Chat Panel */}
        <div 
          className="h-full bg-slate-800 border-l border-slate-700 flex flex-col transition-all duration-300 shrink-0"
          style={{
            width: isChatOpen 
              ? (chatWidth === 'wide' ? 'calc(40% - 128px)' : 'calc(25% - 80px)')
              : '32px',
            minWidth: isChatOpen ? '280px' : '0px'
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
                  <button 
                    onClick={toggleChatWidth} 
                    className="p-1 text-slate-400 hover:text-white transition"
                    title={chatWidth === 'narrow' ? 'Expand' : 'Shrink'}
                  >
                    {chatWidth === 'narrow' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={() => setIsChatOpen(false)} className="p-1 text-slate-400 hover:text-white transition">
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
    </div>
  )
}
