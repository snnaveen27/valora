/**
 * TopTaskBanner - User-Friendly Task Progress Banner
 * Shows clear, understandable task progress with real-time updates
 */

import { useState, useEffect } from 'react'
import { Loader2, CheckCircle2, Circle, X, Zap, Brain, MapPin, Search, BarChart3, Route, Building, Globe, TrendingUp, Shield, Home } from 'lucide-react'

// User-friendly task icons
const TaskIcon = ({ taskType, status }) => {
  const iconClass = `w-3.5 h-3.5 ${
    status === 'complete' ? 'text-emerald-400' : 
    status === 'running' ? 'text-violet-400' : 'text-slate-500'
  }`
  
  const iconMap = {
    'geocode': <MapPin className={iconClass} />,
    'flyto': <Globe className={iconClass} />,
    'search': <Search className={iconClass} />,
    'analyze': <BarChart3 className={iconClass} />,
    'route': <Route className={iconClass} />,
    'property': <Home className={iconClass} />,
    'building': <Building className={iconClass} />,
    'ai': <Brain className={iconClass} />,
    'agentic': <Zap className={iconClass} />,
    'investment': <TrendingUp className={iconClass} />,
    'risk': <Shield className={iconClass} />,
    'default': status === 'complete' ? <CheckCircle2 className={iconClass} /> : 
               status === 'running' ? <Loader2 className={`${iconClass} animate-spin`} /> : 
               <Circle className={iconClass} />
  }
  
  return iconMap[taskType?.toLowerCase()] || iconMap.default
}

// Convert technical task to user-friendly description
const getUserFriendlyLabel = (task) => {
  const label = task.label || task.description || ''
  const action = task.action?.toLowerCase() || ''
  const entity = task.entity?.toLowerCase() || ''
  
  // User-friendly action mappings
  const actionLabels = {
    'geocode': 'Locating',
    'flyto': 'Navigating to',
    'orbit': 'Exploring',
    'spatialquery': 'Searching',
    'areametrics': 'Analyzing',
    'routeanalysis': 'Calculating route',
    'terrainanalysis': 'Analyzing terrain',
    'skyviewanalysis': 'Analyzing views',
    'parse': 'Understanding',
    'compare': 'Comparing',
    'analyze': 'Analyzing',
    'summarize': 'Summarizing',
    'explain': 'Explaining',
    'simulate': 'Simulating',
    'getpropertydetails': 'Fetching property',
    'getmarketdata': 'Getting market data',
    'gethistoricaldata': 'Fetching history',
    'getpoidata': 'Finding amenities',
    'markproperties': 'Displaying results',
    'drawroute': 'Drawing route',
    'drawcircle': 'Drawing area'
  }
  
  // If we have a good label, use it
  if (label && !label.includes('_') && label.length > 3) {
    return label
  }
  
  // Generate from action
  const friendlyAction = actionLabels[action] || action
  const friendlyEntity = entity.replace(/_/g, ' ')
  
  return `${friendlyAction} ${friendlyEntity}`.trim()
}

// Get phase description for user
const getPhaseDescription = (phase, task) => {
  const phases = {
    'understanding': 'Understanding your request...',
    'planning': 'Planning the analysis...',
    'executing': task ? `Working: ${task}` : 'Processing...',
    'finalizing': 'Finalizing results...',
    'complete': 'Done!'
  }
  return phases[phase] || 'Processing...'
}

export default function TopTaskBanner({
  query,
  streamingData,
  isVisible,
  onClose,
  tasks: externalTasks,
  progress: externalProgress,
  taskProgress,
  taskHistory
}) {
  const [tasks, setTasks] = useState([])
  const [progress, setProgress] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [currentStep, setCurrentStep] = useState('')
  const [processingPhase, setProcessingPhase] = useState('')

  const displayProgress = taskProgress || { step: currentStep, detail: '', percent: progress }

  useEffect(() => {
    if (!streamingData) return
    
    const type = streamingData.type
    
    switch (type) {
      // Multi-Stage LLM Execution Events
      case 'orchestration_start':
        setCurrentStep('Starting analysis...')
        setProcessingPhase('understanding')
        setProgress(0)
        setIsComplete(false)
        setTasks([])
        break
        
      case 'stage_start':
        const stageMessages = {
          'understand': 'Understanding your request...',
          'plan': 'Planning the analysis...',
          'execute': 'Executing tasks...',
          'validate': 'Validating results...',
          'synthesize': 'Generating response...'
        }
        const stagePhases = {
          'understand': 'understanding',
          'plan': 'planning',
          'execute': 'executing',
          'validate': 'validating',
          'synthesize': 'finalizing'
        }
        setCurrentStep(stageMessages[streamingData.stage] || 'Processing...')
        setProcessingPhase(stagePhases[streamingData.stage] || 'executing')
        break
        
      case 'stage_complete':
        // Update progress based on stage completion
        const stageProgress = {
          'understand': 20,
          'plan': 40,
          'execute': 70,
          'validate': 85,
          'synthesize': 95
        }
        setProgress(stageProgress[streamingData.stage] || progress)
        break
        
      case 'query_understood':
        setTasks([{
          id: 'understand',
          label: 'Query analyzed',
          type: 'ai',
          status: 'complete',
          progress_percent: 100
        }])
        break
        
      case 'task_graph':
        setProcessingPhase('executing')
        if (streamingData.tasks && streamingData.tasks.length > 0) {
          setTasks(streamingData.tasks.map((t, i) => ({
            id: t.id || `task_${i}`,
            label: t.label || t.description || t.action,
            description: t.label || t.description,
            type: t.type || t.action || 'default',
            action: t.action,
            entity: t.entity,
            status: 'pending',
            progress_percent: 0
          })))
        }
        break
        
      case 'tasks_executed':
        setTasks(prev => prev.map(t => {
          const result = streamingData.task_results?.[t.id]
          if (result) {
            return { ...t, status: 'complete', progress_percent: 100 }
          }
          return t
        }))
        break
        
      case 'validation_result':
        setProcessingPhase('finalizing')
        if (!streamingData.is_complete && streamingData.missing_information?.length > 0) {
          setTasks(prev => [...prev, {
            id: 'validation',
            label: 'Filling gaps...',
            type: 'ai',
            status: 'running',
            progress_percent: 50
          }])
        }
        break
        
      case 'response_synthesized':
        setTasks(prev => prev.map(t => ({ ...t, status: 'complete', progress_percent: 100 })))
        setProgress(95)
        break
        
      case 'orchestration_complete':
        setTasks(prev => prev.map(t => ({ ...t, status: 'complete', progress_percent: 100 })))
        setProgress(100)
        setIsComplete(true)
        setCurrentStep('Complete')
        setProcessingPhase('complete')
        setTimeout(() => {
          if (onClose) onClose()
        }, 2000)
        break
      
      // Legacy Events (kept for backward compatibility)
      case 'recovering':
        setCurrentStep('Reconnecting...')
        setProgress(50)
        setIsComplete(false)
        setTasks([{
          id: 'recovering',
          label: 'Restoring your session',
          type: 'system',
          status: 'running',
          progress_percent: 50
        }])
        break
        
      case 'intent_classification_start':
        setCurrentStep('Understanding your request...')
        setProcessingPhase('understanding')
        setProgress(5)
        setIsComplete(false)
        setTasks([])
        break
        
      case 'intent_detected':
        setProcessingPhase('planning')
        setCurrentStep(`Planning: ${streamingData.intent?.replace(/_/g, ' ')}`)
        
        if (streamingData.task_graph?.tasks) {
          setTasks(streamingData.task_graph.tasks.map((t, i) => ({
            id: t.id || `task_${i}`,
            label: t.label || t.description || t,
            description: t.description || t.label,
            type: t.type || t.action || 'default',
            action: t.action,
            entity: t.entity,
            status: t.status || 'pending',
            progress_percent: t.progress_percent || 0
          })))
        }
        break
        
      case 'task_started':
        setProcessingPhase('executing')
        setTasks(prev => {
          const idx = prev.findIndex(t => t.id === streamingData.task_id)
          const taskType = streamingData.task_type || streamingData.task_name?.toLowerCase().split(' ')[0] || 'default'
          
          if (idx >= 0) {
            const updated = [...prev]
            updated[idx] = { 
              ...updated[idx], 
              label: streamingData.task_name || updated[idx].label,
              type: taskType,
              status: 'running',
              progress_percent: 10
            }
            return updated
          }
          return [...prev, { 
            id: streamingData.task_id, 
            label: streamingData.task_name || 'Processing',
            type: taskType,
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
        setProcessingPhase('executing')
        setTasks(prev => {
          if (prev.some(t => t.id === 'agentic')) {
            return prev.map(t => t.id === 'agentic' 
              ? { ...t, label: 'AI Analysis', status: 'running', progress_percent: 30 }
              : t
            )
          }
          return [...prev, { 
            id: 'agentic', 
            label: 'AI Analysis',
            type: 'agentic',
            status: 'running',
            progress_percent: 30 
          }]
        })
        break

      case 'agentic_action':
        const toolLabel = streamingData.tool ? streamingData.tool.replace(/_/g, ' ') : 'reasoning'
        setTasks(prev => prev.map(t =>
          t.id === 'agentic' ? { ...t, label: `AI: ${toolLabel}`, progress_percent: 50 } : t
        ))
        break

      case 'done':
        setTasks(prev => prev.map(t => ({ ...t, status: 'complete', progress_percent: 100 })))
        setProgress(100)
        setIsComplete(true)
        setCurrentStep('Complete')
        setProcessingPhase('complete')
        setTimeout(() => {
          if (onClose) onClose()
        }, 2000)
        break
        
      case 'task_recovered_done':
        setTimeout(() => {
          if (onClose) onClose()
        }, 1000)
        break
    }
  }, [streamingData, onClose])

  useEffect(() => {
    if (externalTasks && externalTasks.length > 0) {
      setTasks(externalTasks)
    }
  }, [externalTasks])

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

  const hasActivity = tasks.length > 0 || currentStep
  if (!hasActivity) return null

  const completedCount = tasks.filter(t => t.status === 'complete').length
  const runningTask = tasks.find(t => t.status === 'running')
  const totalTasks = tasks.length

  return (
    <div className="fixed top-24 left-1/2 -translate-x-1/2 z-[9999]">
      <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/50 rounded-lg shadow-2xl w-[420px] overflow-hidden">
        {/* Header with Phase */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700/50">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            {/* Progress Ring */}
            <div className="relative w-7 h-7 flex-shrink-0">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 28 28">
                <circle cx="14" cy="14" r="10" className="stroke-slate-700 fill-none" strokeWidth="2" />
                <circle
                  cx="14" cy="14" r="10"
                  fill="none"
                  stroke={isComplete ? '#34d399' : '#a78bfa'}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 10}
                  strokeDashoffset={2 * Math.PI * 10 * (1 - progress / 100)}
                  className="transition-all duration-300"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-[8px] font-semibold text-white">
                {Math.round(progress)}%
              </span>
            </div>
            
            {/* Phase & Current Action */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                {processingPhase && !isComplete && (
                  <span className="text-[9px] font-medium text-violet-400 uppercase tracking-wider">
                    {processingPhase === 'executing' ? 'Processing' : processingPhase}
                  </span>
                )}
                {isComplete && (
                  <span className="text-[9px] font-medium text-emerald-400 uppercase tracking-wider">
                    Complete
                  </span>
                )}
              </div>
              <p className={`text-xs font-medium truncate ${isComplete ? 'text-emerald-400' : 'text-white'}`}>
                {runningTask ? getUserFriendlyLabel(runningTask) : getPhaseDescription(processingPhase)}
              </p>
            </div>
          </div>
          
          {/* Task Counter */}
          {totalTasks > 0 && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-slate-800 rounded text-[10px] text-slate-400">
              <span className="font-medium text-white">{completedCount}</span>
              <span>/</span>
              <span>{totalTasks}</span>
              <span className="text-slate-500 ml-1">tasks</span>
            </div>
          )}
          
          {/* Close */}
          <button 
            onClick={onClose}
            className="p-1 text-slate-500 hover:text-white transition-colors rounded hover:bg-slate-700/50 ml-1"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Task List - User Friendly */}
        {tasks.length > 0 && (
          <div className="max-h-[180px] overflow-y-auto">
            <div className="px-3 py-2">
              <div className="space-y-1">
                {tasks.map((task, index) => (
                  <div 
                    key={task.id || index}
                    className={`flex items-center gap-2 py-1.5 px-2 rounded-md transition-all duration-200 ${
                      task.status === 'running' 
                        ? 'bg-violet-500/10 border border-violet-500/20' 
                        : task.status === 'complete'
                          ? 'bg-slate-800/30'
                          : 'bg-slate-800/20'
                    }`}
                  >
                    <TaskIcon taskType={task.type || task.action} status={task.status} />
                    <span className={`text-xs truncate flex-1 ${
                      task.status === 'complete' 
                        ? 'text-slate-400' 
                        : task.status === 'running'
                          ? 'text-white font-medium'
                          : 'text-slate-500'
                    }`}>
                      {getUserFriendlyLabel(task)}
                    </span>
                    {task.status === 'running' && (
                      <div className="flex items-center gap-1">
                        <div className="w-8 h-0.5 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-violet-400 rounded-full transition-all duration-300"
                            style={{ width: `${task.progress_percent || 0}%` }}
                          />
                        </div>
                      </div>
                    )}
                    {task.status === 'complete' && (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Progress Bar */}
        <div className="h-0.5 bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${isComplete ? 'bg-emerald-500' : 'bg-violet-500'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  )
}
