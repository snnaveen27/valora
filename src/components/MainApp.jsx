import { useEffect, useState } from 'react'
import OnlineOSMMap from '../spatial/OnlineOSMMap'
import AnalysisPanel from './AnalysisPanel'
import ChatPanel from './ChatPanel'
import { Sparkles, Maximize2, Minimize2, X, ChevronRight, ChevronLeft } from 'lucide-react'

export default function MainApp() {
  const [agentData, setAgentData] = useState({})
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('insights')
  const [analysisWidth, setAnalysisWidth] = useState('narrow') // narrow or wide
  const [chatWidth, setChatWidth] = useState('narrow') // narrow or wide

  useEffect(() => {
    const handleUICommand = (e) => {
      const { action, value, panel, tab } = e.detail || {}
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
                <span className="text-white font-medium text-sm">Insights & Analysis</span>
                <div className="flex gap-1">
                  <button 
                    onClick={toggleAnalysisWidth} 
                    className="p-1 text-slate-400 hover:text-white transition"
                    title={analysisWidth === 'narrow' ? 'Expand' : 'Shrink'}
                  >
                    {analysisWidth === 'narrow' ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={() => setIsAnalysisOpen(false)} className="p-1 text-slate-400 hover:text-white transition">
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
              ? (chatWidth === 'wide' ? 'calc(50% - 160px)' : 'calc(33% - 107px)')
              : '32px',
            minWidth: isChatOpen ? '300px' : '0px'
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
                <ChatPanel agentData={agentData} setAgentData={setAgentData} />
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
