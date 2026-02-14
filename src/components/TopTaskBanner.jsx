/**
 * TopTaskBanner - Animated task planner banner at top center
 * Shows query progress with "talking to app" feel
 */

import { useState, useEffect, useRef } from 'react'
import { 
  Sparkles, Loader2, CheckCircle2, Circle, Brain,
  MessageSquare, ChevronRight, Zap, Activity
} from 'lucide-react'

// Morphing Blob Loading Animation
const MorphingBlob = ({ isActive }) => {
  if (!isActive) return null
  
  return (
    <div className="relative w-16 h-16 flex items-center justify-center">
      {/* Outer glow */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-cyan-500/20 blur-xl animate-pulse" />
      
      {/* Morphing blob */}
      <div className="relative w-12 h-12">
        <div 
          className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500 via-purple-500 to-cyan-400 opacity-80"
          style={{
            animation: 'morph 3s ease-in-out infinite',
            filter: 'blur(0.5px) drop-shadow(0 0 8px rgba(59, 130, 246, 0.5))'
          }}
        />
        <div 
          className="absolute inset-1 rounded-full bg-gradient-to-tr from-cyan-400 via-blue-400 to-purple-500 opacity-60"
          style={{
            animation: 'morph 3s ease-in-out infinite reverse',
            animationDelay: '0.5s'
          }}
        />
        <div 
          className="absolute inset-2 rounded-full bg-gradient-to-bl from-purple-400 via-cyan-500 to-blue-500 opacity-40"
          style={{
            animation: 'morph 2.5s ease-in-out infinite',
            animationDelay: '1s'
          }}
        />
      </div>
      
      {/* Inner core */}
      <div className="absolute w-4 h-4 rounded-full bg-gradient-to-br from-white/80 to-blue-200/50 animate-pulse" />
      
      <style>{`
        @keyframes morph {
          0%, 100% {
            border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
            transform: rotate(0deg) scale(1);
          }
          25% {
            border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%;
            transform: rotate(90deg) scale(1.05);
          }
          50% {
            border-radius: 50% 60% 30% 60% / 30% 40% 70% 50%;
            transform: rotate(180deg) scale(0.95);
          }
          75% {
            border-radius: 60% 40% 60% 30% / 70% 30% 50% 60%;
            transform: rotate(270deg) scale(1.02);
          }
        }
      `}</style>
    </div>
  )
}

// Animated typing dots
const TalkingDots = ({ isActive }) => {
  if (!isActive) return null
  
  return (
    <div className="flex items-center gap-1">
      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  )
}

// Task progress ring
const ProgressRing = ({ progress, isComplete }) => {
  const circumference = 2 * Math.PI * 12
  const strokeDashoffset = circumference - (progress / 100) * circumference
  
  return (
    <div className="relative w-7 h-7">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 28 28">
        <circle
          cx="14" cy="14" r="12"
          className="stroke-slate-700 fill-none"
          strokeWidth="3"
        />
        <circle
          cx="14" cy="14" r="12"
          className={`${isComplete ? 'stroke-emerald-400' : 'stroke-blue-400'} fill-none transition-all duration-500`}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
        />
      </svg>
      {isComplete && (
        <CheckCircle2 className="absolute inset-0 w-4 h-4 m-auto text-emerald-400" />
      )}
    </div>
  )
}

// Individual task item with animation
const AnimatedTaskItem = ({ task, index, isActive }) => {
  const isComplete = task.status === 'complete'
  const isRunning = task.status === 'running'
  const isPending = task.status === 'pending'
  
  return (
    <div 
      className={`flex items-center gap-2 transition-all duration-300 ${
        isRunning ? 'opacity-100' : isComplete ? 'opacity-80' : 'opacity-70'
      }`}
      style={{ 
        animationDelay: `${index * 100}ms`,
        transform: isRunning ? 'translateX(4px)' : 'translateX(0)'
      }}
    >
      <div className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${
        isComplete ? 'bg-emerald-400' : 
        isRunning ? 'bg-blue-400 animate-pulse' : 
        'bg-slate-400'
      }`} />
      <span className={`text-xs transition-all duration-300 ${
        isComplete ? 'text-slate-300 line-through' : 
        isRunning ? 'text-blue-200 font-medium' : 
        'text-slate-300'
      }`}>
        {task.label}
      </span>
      {isRunning && (
        <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
      )}
    </div>
  )
}

// Main banner component
const TopTaskBanner = ({ 
  query,
  streamingData,
  isVisible,
  onClose
}) => {
  const [tasks, setTasks] = useState([])
  const [detectedIntent, setDetectedIntent] = useState(null)
  const [confidence, setConfidence] = useState(0)
  const [isThinking, setIsThinking] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [progress, setProgress] = useState(0)
  const [showExpanded, setShowExpanded] = useState(true)
  const timerRef = useRef(null)

  // Reset state when query changes
  useEffect(() => {
    if (!query) return
    
    setTasks([])
    setDetectedIntent(null)
    setConfidence(0)
    setIsThinking(false)
    setElapsed(0)
    setProgress(0)
    setShowExpanded(true)
    
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [query])

  // Handle streaming data
  useEffect(() => {
    if (!streamingData) return
    
    switch (streamingData.type) {
      case 'intent_classification_start':
        setIsThinking(true)  // Show "Processing..." during classification
        setTasks([])
        setDetectedIntent(null)
        setConfidence(0)
        // Only reset elapsed if we're starting fresh (not if already running)
        setElapsed(prev => prev === 0 ? 0 : prev)
        setProgress(0)
        break
        
      case 'intent_detected':
        setIsThinking(false)  // Stop showing "Processing..." once intent detected
        setDetectedIntent(streamingData.intent)
        setConfidence(streamingData.confidence || 0)
        
        if (streamingData.task_graph?.tasks) {
          const graphTasks = streamingData.task_graph.tasks
          setTasks(graphTasks.map((task, i) => ({
            id: task.id || `task_${i}`,
            label: task.label || task,
            status: task.status || 'pending',
            progress_percent: task.progress_percent || 0
          })))
          setProgress(0)
        } else if (streamingData.tasks) {
          setTasks(streamingData.tasks.map((task, i) => ({
            id: `task_${i}`,
            label: typeof task === 'string' ? task : task.label,
            status: 'pending',
            progress_percent: 0
          })))
        }
        break
        
      case 'task_plan_created':
        // Initialize task slots based on total_tasks count
        if (streamingData.total_tasks) {
          const placeholders = Array.from({ length: streamingData.total_tasks }, (_, i) => ({
            id: `task_${i}`,
            label: `Step ${i + 1}`,
            status: 'pending',
            progress_percent: 0
          }))
          setTasks(placeholders)
        }
        break

      case 'task_started':
        setTasks(prev => {
          const updated = [...prev]
          const idx = updated.findIndex(t => t.id === streamingData.task_id)
          if (idx >= 0) {
            updated[idx] = { ...updated[idx], label: streamingData.task_name, status: 'running', progress_percent: 50 }
          } else {
            updated.push({ id: streamingData.task_id, label: streamingData.task_name, status: 'running', progress_percent: 50 })
          }
          return updated
        })
        // Update overall progress
        setProgress(prev => {
          const parts = (streamingData.progress || '0/1').split('/')
          const current = parseInt(parts[0]) || 0
          const total = parseInt(parts[1]) || 1
          return Math.round(((current - 0.5) / total) * 100)
        })
        break

      case 'task_completed':
        setTasks(prev => prev.map(t => 
          t.id === streamingData.task_id 
            ? { ...t, label: streamingData.task_name || t.label, status: 'complete', progress_percent: 100 }
            : t
        ))
        setProgress(prev => {
          const parts = (streamingData.progress || '0/1').split('/')
          const current = parseInt(parts[0]) || 0
          const total = parseInt(parts[1]) || 1
          return Math.round((current / total) * 100)
        })
        break

      case 'task_failed':
        setTasks(prev => prev.map(t => 
          t.id === streamingData.task_id 
            ? { ...t, label: `${streamingData.task_name || t.label} (failed)`, status: 'complete', progress_percent: 100 }
            : t
        ))
        break

      case 'task_progress':
        if (streamingData.task_graph?.tasks) {
          const updatedTasks = streamingData.task_graph.tasks
          setTasks(prev => prev.map(task => {
            const updated = updatedTasks.find(t => t.id === task.id)
            return updated ? { ...task, ...updated } : task
          }))
        }
        break

      case 'agentic_start':
        // Autonomous reasoning loop activated — show the actual message
        setTasks(prev => [...prev, { id: 'agentic', label: streamingData.message || 'Deep analysis started...', status: 'running', progress_percent: 30 }])
        break

      case 'agentic_action': {
        // Show each agentic step as a real task with the tool and thought
        const toolLabel = streamingData.tool ? streamingData.tool.replace(/_/g, ' ') : 'reasoning'
        const thought = streamingData.thought ? ` — ${streamingData.thought.slice(0, 60)}` : ''
        const stepLabel = `${toolLabel}${thought}`
        // Add each step as its own visible task
        setTasks(prev => {
          const updated = prev.map(t =>
            t.id === 'agentic' ? { ...t, label: stepLabel, progress_percent: 50 } : t
          )
          // Also add completed previous steps
          if (streamingData.step > 1) {
            const prevStepId = `agentic_step_${streamingData.step - 1}`
            if (!updated.find(t => t.id === prevStepId)) {
              // Mark the agentic placeholder as the previous step completed
              const agenticIdx = updated.findIndex(t => t.id === 'agentic')
              if (agenticIdx >= 0) {
                const prevLabel = updated[agenticIdx].label
                updated.splice(agenticIdx, 0, { id: prevStepId, label: prevLabel, status: 'complete', progress_percent: 100 })
                // Reset current agentic task
                const newIdx = updated.findIndex(t => t.id === 'agentic')
                if (newIdx >= 0) updated[newIdx] = { ...updated[newIdx], label: stepLabel, progress_percent: 50 }
              }
            }
          }
          return updated
        })
        break
      }

      case 'agentic_complete':
        // Mark agentic reasoning as complete with actual result
        setTasks(prev => prev.map(t =>
          t.id === 'agentic'
            ? { ...t, label: `Analysis complete (${streamingData.steps_taken} steps, ${Math.round((streamingData.confidence || 0) * 100)}% confidence)`, status: 'complete', progress_percent: 100 }
            : t
        ))
        break
        
      case 'done':
        setTasks(prev => prev.map(t => ({ ...t, status: 'complete', progress_percent: 100 })))
        setProgress(100)
        setTimeout(() => {
          if (onClose) onClose()
        }, 2000)
        break
    }
  }, [streamingData, onClose])

  // Timer
  useEffect(() => {
    if (!isVisible || (!isThinking && tasks.length === 0)) {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }
    
    timerRef.current = setInterval(() => {
      setElapsed(e => e + 1)
    }, 1000)
    
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isVisible, isThinking, tasks.length])

  // Calculate progress
  useEffect(() => {
    if (tasks.length === 0) {
      setProgress(isThinking ? 5 : 0)
      return
    }
    const completed = tasks.filter(t => t.status === 'complete').length
    const running = tasks.filter(t => t.status === 'running').length
    const newProgress = ((completed + (running * 0.5)) / tasks.length) * 100
    setProgress(Math.round(newProgress))
  }, [tasks, isThinking])

  // Format elapsed time
  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  // Get intent display name
  const getIntentDisplay = (intent) => {
    const displays = {
      'navigate': 'Navigating',
      'analyze_area': 'Analyzing Area',
      'analyze_building': 'Analyzing Building',
      'property_search': 'Searching Properties',
      'valuation': 'Valuation',
      'terrain': 'Terrain Analysis',
      'comparison': 'Comparing',
      'simulate': 'Simulation',
      'general': 'Processing'
    }
    return displays[intent] || intent?.replace(/_/g, ' ') || 'Processing'
  }

  // Show banner if we have any activity - either thinking, detected intent, or tasks
  const hasActivity = isThinking || detectedIntent || tasks.length > 0
  if (!isVisible || !hasActivity) return null

  const completedCount = tasks.filter(t => t.status === 'complete').length
  const runningTask = tasks.find(t => t.status === 'running')
  const isComplete = progress >= 100

  return (
    <div className="fixed top-28 left-1/2 -translate-x-1/2 z-[9999]">
      <div 
        className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 shadow-2xl overflow-hidden transition-all duration-500 w-[520px]"
      >
        {/* Main Banner Row */}
        <div 
          className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-800/50 transition-colors"
          onClick={() => setShowExpanded(!showExpanded)}
        >
          {/* Progress Ring - hide when thinking, show blob instead */}
          <div className="relative">
            {isThinking ? (
              <MorphingBlob isActive={true} />
            ) : (
              <ProgressRing progress={progress} isComplete={isComplete} />
            )}
          </div>
          
          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Status Line */}
            <div className="flex items-center gap-2">
              {isThinking ? (
                <>
                  <span className="text-sm font-medium text-blue-300">
                    Analysing...
                  </span>
                </>
              ) : (
                <>
                  <Sparkles className={`w-3.5 h-3.5 ${isComplete ? 'text-emerald-400' : 'text-blue-400'}`} />
                  <span className={`text-sm font-medium ${
                    isComplete ? 'text-emerald-300' : 'text-slate-200'
                  }`}>
                    {getIntentDisplay(detectedIntent)}
                  </span>
                </>
              )}
            </div>
            
            {/* Query preview */}
            {query && (
              <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                {query}
              </p>
            )}
          </div>
          
          {/* Right side stats */}
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {!isThinking && tasks.length > 0 && (
              <span className="text-slate-400">
                {completedCount}/{tasks.length}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3" />
              {formatTime(elapsed)}
            </span>
            <ChevronRight className={`w-4 h-4 text-slate-600 transition-transform ${showExpanded ? 'rotate-90' : ''}`} />
          </div>
        </div>
        
        {/* Expanded Task List */}
        <div className={`overflow-hidden transition-all duration-500 ${showExpanded ? 'max-h-[300px]' : 'max-h-0'}`}>
          <div className="px-4 pb-3 border-t border-slate-800/50">
            {/* Running task highlight */}
            {runningTask && (
              <div className="py-3 border-b border-slate-800/50">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                  <span className="text-xs font-medium text-amber-300">Currently Processing</span>
                </div>
                <div className="flex items-center gap-3 bg-slate-800/50 px-3 py-2">
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
                  <span className="text-sm text-slate-200">{runningTask.label}</span>
                </div>
              </div>
            )}
            
            {/* Task list */}
            <div className="py-2 space-y-1.5">
              {tasks.map((task, index) => (
                <AnimatedTaskItem 
                  key={task.id || index}
                  task={task}
                  index={index}
                  isActive={task.status === 'running'}
                />
              ))}
            </div>
            
            {/* Completion message */}
            {isComplete && (
              <div className="flex items-center gap-2 py-2 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-sm font-medium">All tasks completed!</span>
              </div>
            )}
          </div>
        </div>
        
        {/* Bottom progress bar */}
        <div className="h-0.5 bg-slate-800/50 w-full">
          <div 
            className={`h-full transition-all duration-500 ${
              isComplete ? 'bg-emerald-400' : 'bg-gradient-to-r from-blue-500 via-purple-500 to-blue-400'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  )
}

export default TopTaskBanner
