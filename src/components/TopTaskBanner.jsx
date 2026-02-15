/**
 * TopTaskBanner - Simple Task Progress Banner
 * Shows query progress without animations
 */

import { useState, useEffect } from 'react'
import { Loader2, CheckCircle2, ChevronRight } from 'lucide-react'

export default function TopTaskBanner({
  query,
  streamingData,
  isVisible,
  onClose,
  tasks: externalTasks,
  progress: externalProgress,
  taskProgress // New prop for synchronized progress from MainApp
}) {
  const [tasks, setTasks] = useState([])
  const [detectedIntent, setDetectedIntent] = useState(null)
  const [progress, setProgress] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [currentStep, setCurrentStep] = useState('')
  const [isThinking, setIsThinking] = useState(false)

  // Use synchronized progress from MainApp if available
  const displayProgress = taskProgress || { step: currentStep, detail: '', percent: progress }

  useEffect(() => {
    if (!streamingData) return
    
    switch (streamingData.type) {
      case 'intent_classification_start':
        setIsThinking(true)
        setDetectedIntent(null)
        setCurrentStep('Understanding your query...')
        setProgress(5)
        setIsComplete(false)
        setTasks([])
        break
        
      case 'intent_detected':
        setIsThinking(false)
        setDetectedIntent(streamingData.intent)
        setCurrentStep(`Preparing ${streamingData.intent?.replace(/_/g, ' ')}...`)
        
        if (streamingData.task_graph?.tasks) {
          setTasks(streamingData.task_graph.tasks.map((t, i) => ({
            id: t.id || `task_${i}`,
            label: t.label || t,
            status: t.status || 'pending',
            progress_percent: t.progress_percent || 0
          })))
        }
        break
        
      case 'task_started':
        setTasks(prev => {
          const idx = prev.findIndex(t => t.id === streamingData.task_id)
          if (idx >= 0) {
            const updated = [...prev]
            updated[idx] = { 
              ...updated[idx], 
              label: streamingData.task_name, 
              status: 'running',
              progress_percent: 10
            }
            return updated
          }
          return [...prev, { 
            id: streamingData.task_id, 
            label: streamingData.task_name, 
            status: 'running',
            progress_percent: 10
          }]
        })
        setCurrentStep(streamingData.task_name)
        break

      case 'task_completed':
        setTasks(prev => prev.map(t => 
          t.id === streamingData.task_id 
            ? { ...t, label: streamingData.task_name || t.label, status: 'complete', progress_percent: 100 }
            : t
        ))
        break

      case 'agentic_start':
        setTasks(prev => [...prev, { 
          id: 'agentic', 
          label: streamingData.message || 'Deep analysis started...', 
          status: 'running',
          progress_percent: 30 
        }])
        break

      case 'agentic_action':
        const toolLabel = streamingData.tool ? streamingData.tool.replace(/_/g, ' ') : 'reasoning'
        const thought = streamingData.thought ? streamingData.thought.slice(0, 80) : ''
        setTasks(prev => prev.map(t =>
          t.id === 'agentic' ? { ...t, label: `${toolLabel}${thought ? ': ' + thought : ''}`, progress_percent: 50 } : t
        ))
        break

      case 'done':
        setTasks(prev => prev.map(t => ({ ...t, status: 'complete', progress_percent: 100 })))
        setProgress(100)
        setIsComplete(true)
        setCurrentStep('All tasks completed!')
        setTimeout(() => {
          if (onClose) onClose()
        }, 2000)
        break
    }
  }, [streamingData, onClose])

  // Sync with external tasks if provided
  useEffect(() => {
    if (externalTasks && externalTasks.length > 0) {
      setTasks(externalTasks)
    }
  }, [externalTasks])

  // Sync with external progress if provided
  useEffect(() => {
    if (externalProgress !== undefined) {
      setProgress(externalProgress)
    }
  }, [externalProgress])

  useEffect(() => {
    if (tasks.length === 0) return
    const completed = tasks.filter(t => t.status === 'complete').length
    const running = tasks.filter(t => t.status === 'running').length
    setProgress(Math.round(((completed + (running * 0.5)) / tasks.length) * 100))
  }, [tasks])

  if (!isVisible) return null

  const hasActivity = isThinking || detectedIntent || tasks.length > 0
  if (!hasActivity) return null

  const completedCount = tasks.filter(t => t.status === 'complete').length
  const runningTask = tasks.find(t => t.status === 'running')
  const pendingTasks = tasks.filter(t => t.status === 'pending')

  // Use synchronized progress from MainApp
  const displayStep = taskProgress?.step || currentStep
  const displayDetail = taskProgress?.detail || ''
  const displayPercent = taskProgress?.percent ?? progress

  return (
    <div className="fixed top-24 left-1/2 -translate-x-1/2 z-[9999]">
      <div
        className="bg-slate-900 border border-slate-700 shadow-xl overflow-hidden rounded-xl w-[560px]"
      >
        {/* Simple top border */}
        <div
          className="h-1 w-full bg-gradient-to-r from-violet-600 via-purple-500 to-violet-600"
        />

        {/* Query Display */}
        {query && (
          <div className="px-4 py-2 bg-slate-800/50 border-b border-slate-800">
            <p className="text-xs text-slate-500">Query:</p>
            <p className="text-sm text-slate-300 truncate">"{query}"</p>
          </div>
        )}

        {/* Main Banner Row - Always Expanded */}
        <div className="flex items-center gap-4 px-4 py-3">
          {/* Progress Ring */}
          <div className="relative w-10 h-10 flex-shrink-0">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
              <circle cx="20" cy="20" r="16" className="stroke-slate-700 fill-none" strokeWidth="3" />
              <circle
                cx="20" cy="20" r="16"
                fill="none"
                stroke={isComplete ? '#10b981' : '#8b5cf6'}
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 16}
                strokeDashoffset={2 * Math.PI * 16 * (1 - displayPercent / 100)}
                className="transition-all duration-500"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white">
              {Math.round(displayPercent)}%
            </span>
          </div>

          {/* Content - Synchronized with Header */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium ${isComplete ? 'text-emerald-400' : 'text-violet-200'}`}>
                {displayStep}
              </span>
              {displayDetail && (
                <>
                  <span className="text-slate-600">|</span>
                  <span className="text-sm text-slate-300 truncate">{displayDetail}</span>
                </>
              )}
              {!isComplete && displayPercent > 0 && displayPercent < 100 && (
                <span className="flex gap-0.5 ml-1">
                  <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
              )}
            </div>
          </div>
           
          {/* Stats */}
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {!isThinking && tasks.length > 0 && (
              <span className="font-mono bg-slate-800 px-2 py-0.5 rounded">
                {completedCount}/{tasks.length}
              </span>
            )}
            {/* Close button instead of chevron */}
            <button 
              onClick={(e) => {
                e.stopPropagation()
                if (onClose) onClose()
              }}
              className="text-slate-500 hover:text-slate-300 transition-colors"
              title="Close"
            >
              <span className="text-lg">&times;</span>
            </button>
          </div>
        </div>
         
        {/* Detailed Task List - Always Visible */}
        <div className="overflow-hidden max-h-[400px]">
          <div className="px-4 pb-3 border-t border-slate-800">
            {/* Currently Running Task - Highlighted */}
            {runningTask && (
              <div className="py-2 border-b border-slate-800/50">
                <div className="text-xs text-violet-400 mb-1 font-medium">Currently Processing</div>
                <div className="flex items-center gap-3 px-3 py-2 rounded bg-violet-500/10 border border-violet-500/20">
                  <Loader2 className="w-4 h-4 text-violet-400" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-slate-200 block">{runningTask.label}</span>
                    <div className="w-full h-1.5 bg-slate-700 rounded-full mt-2 overflow-hidden">
                      <div 
                        className="h-full bg-violet-500 rounded-full transition-all duration-300"
                        style={{ width: `${runningTask.progress_percent || 50}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-violet-400 font-mono">{runningTask.progress_percent || 50}%</span>
                </div>
              </div>
            )}
             
            {/* Completed Tasks */}
            {completedCount > 0 && (
              <div className="py-2 border-b border-slate-800/50">
                <div className="text-xs text-emerald-500/70 mb-1 font-medium">Completed ({completedCount})</div>
                <div className="space-y-1">
                  {tasks.filter(t => t.status === 'complete').slice(-3).map((task) => (
                    <div key={task.id} className="flex items-center gap-2 text-sm py-1 px-2 rounded bg-slate-800/30">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      <span className="text-slate-400 truncate flex-1">{task.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Pending Tasks */}
            {pendingTasks.length > 0 && (
              <div className="py-2">
                <div className="text-xs text-slate-600 mb-1 font-medium">Pending ({pendingTasks.length})</div>
                <div className="space-y-1">
                  {pendingTasks.slice(0, 3).map((task) => (
                    <div key={task.id} className="flex items-center gap-2 text-sm py-1 px-2">
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-600 flex-shrink-0" />
                      <span className="text-slate-600 truncate">{task.label}</span>
                    </div>
                  ))}
                  {pendingTasks.length > 3 && (
                    <p className="text-xs text-slate-700 pl-5">+{pendingTasks.length - 3} more...</p>
                  )}
                </div>
              </div>
            )}
             
            {/* Completion message */}
            {isComplete && (
              <div className="flex items-center gap-2 py-2 px-3 rounded bg-emerald-500/10 border border-emerald-500/20 mt-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-medium text-emerald-400">All tasks completed successfully!</span>
              </div>
            )}
          </div>
        </div>
         
        {/* Simple bottom progress bar */}
        <div className="h-1 bg-slate-800 w-full">
          <div
            className="h-full transition-all duration-500 bg-violet-500"
            style={{ width: `${displayPercent}%` }}
          />
        </div>
      </div>
    </div>
  )
}
