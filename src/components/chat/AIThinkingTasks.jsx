/**
 * AIThinkingTasks - Professional compact task visualization
 * Shows AI intents as transparent, trackable tasks with progress indicators
 */

import { useEffect, useState, useCallback } from 'react';
import { 
  Brain, 
  Target, 
  MapPin, 
  Building2, 
  TrendingUp, 
  Sun, 
  Eye, 
  Layers,
  Sparkles,
  CheckCircle2,
  Circle,
  Clock,
  Zap,
  ArrowRight,
  X
} from 'lucide-react';

const taskIcons = {
  'intent_classification': Target,
  'analyze_area': MapPin,
  'analyze_building': Building2,
  'property_search': Layers,
  'valuation': TrendingUp,
  'investment': TrendingUp,
  'terrain': Layers,
  'view_analysis': Eye,
  'shadow_analysis': Sun,
  'comparison': ArrowRight,
  'batch_analysis': Layers,
  'narrative_generation': Sparkles,
  'tool_execution': Zap,
  'memory_lookup': Brain,
  'default': Circle
};

const taskLabels = {
  'intent_classification': 'Understanding your query',
  'analyze_area': 'Analyzing location',
  'analyze_building': 'Analyzing building',
  'property_search': 'Searching properties',
  'valuation': 'Calculating value',
  'investment': 'Assessing investment potential',
  'terrain': 'Analyzing terrain',
  'view_analysis': 'Analyzing views',
  'shadow_analysis': 'Calculating sunlight',
  'comparison': 'Comparing options',
  'batch_analysis': 'Processing batch analysis',
  'narrative_generation': 'Generating response',
  'tool_execution': 'Gathering data',
  'memory_lookup': 'Checking memory'
};

const TaskStep = ({ task, isActive, isComplete, index, total }) => {
  const Icon = taskIcons[task.type] || taskIcons.default;
  
  return (
    <div className={`
      flex items-center gap-2 py-1.5 px-2 rounded-md transition-all duration-300
      ${isActive ? 'bg-blue-500/20 border border-blue-500/30' : 
        isComplete ? 'opacity-60' : 'opacity-30'}
    `}>
      <div className="relative">
        {isComplete ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        ) : isActive ? (
          <div className="relative">
            <Icon className="w-4 h-4 text-blue-400" />
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
          </div>
        ) : (
          <Circle className="w-4 h-4 text-slate-500" />
        )}
      </div>
      
      <span className={`
        text-xs font-medium truncate flex-1
        ${isActive ? 'text-blue-200' : 
          isComplete ? 'text-slate-400' : 'text-slate-600'}
      `}>
        {taskLabels[task.type] || task.type}
      </span>
      
      {isActive && (
        <Clock className="w-3 h-3 text-blue-400/70 animate-pulse" />
      )}
    </div>
  );
};

const AIThinkingTasks = ({ 
  tasks, 
  currentTaskIndex, 
  query,
  onClose,
  estimatedTime,
  confidence
}) => {
  const [elapsed, setElapsed] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(e => e + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const completedTasks = tasks.filter((_, i) => i < currentTaskIndex).length;
  const progress = tasks.length > 0 ? (completedTasks / tasks.length) * 100 : 0;

  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/20 border border-blue-500/40 rounded-full text-xs hover:bg-blue-500/30 transition"
      >
        <Brain className="w-3.5 h-3.5 text-blue-400" />
        <span className="text-blue-200">{completedTasks}/{tasks.length} tasks</span>
        <span className="text-slate-400">·</span>
        <span className="text-slate-400">{formatTime(elapsed)}</span>
      </button>
    );
  }

  return (
    <div className="bg-slate-800/95 border border-slate-700 rounded-xl overflow-hidden shadow-xl backdrop-blur-sm max-w-sm">
      {/* Header */}
      <div className="px-3 py-2 bg-slate-700/50 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Brain className="w-4 h-4 text-blue-400" />
            <div className="absolute inset-0 bg-blue-400/30 rounded-full animate-ping" />
          </div>
          <span className="text-xs font-semibold text-white">AI Processing</span>
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 text-slate-400 hover:text-white transition"
          >
            <div className="w-3 h-0.5 bg-current rounded" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-red-400 transition"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="px-3 pt-2">
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Query Preview */}
      {query && (
        <div className="px-3 py-2 border-b border-slate-700/50">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Query</p>
          <p className="text-xs text-slate-300 truncate" title={query}>
            "{query.length > 50 ? query.slice(0, 50) + '...' : query}"
          </p>
        </div>
      )}

      {/* Task List */}
      <div className="px-2 py-2 space-y-0.5 max-h-48 overflow-y-auto">
        {tasks.map((task, index) => (
          <TaskStep
            key={`${task.type}-${index}`}
            task={task}
            isActive={index === currentTaskIndex}
            isComplete={index < currentTaskIndex}
            index={index}
            total={tasks.length}
          />
        ))}
      </div>

      {/* Footer Stats */}
      <div className="px-3 py-2 bg-slate-700/30 border-t border-slate-700 flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">
            {formatTime(elapsed)} elapsed
          </span>
          {estimatedTime && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-slate-500">
                ~{estimatedTime}s est.
              </span>
            </>
          )}
        </div>
        
        {confidence !== undefined && (
          <span className={`
            px-1.5 py-0.5 rounded text-[10px] font-medium
            ${confidence > 0.8 ? 'bg-emerald-500/20 text-emerald-300' :
              confidence > 0.6 ? 'bg-amber-500/20 text-amber-300' :
              'bg-red-500/20 text-red-300'}
          `}>
            {(confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </div>

      {/* Current Task Detail */}
      {tasks[currentTaskIndex]?.details && (
        <div className="px-3 py-2 bg-blue-500/10 border-t border-blue-500/20">
          <p className="text-[10px] text-blue-300/80">
            {tasks[currentTaskIndex].details}
          </p>
        </div>
      )}
    </div>
  );
};

// Hook for managing AI task state
export const useAIThinking = () => {
  const [isThinking, setIsThinking] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [query, setQuery] = useState('');
  const [confidence, setConfidence] = useState(null);
  const [estimatedTime, setEstimatedTime] = useState(null);

  const startThinking = useCallback((userQuery, predictedTasks = []) => {
    setQuery(userQuery);
    setTasks(predictedTasks.length > 0 ? predictedTasks : [
      { type: 'intent_classification' },
      { type: 'tool_execution' },
      { type: 'narrative_generation' }
    ]);
    setCurrentTaskIndex(0);
    setIsThinking(true);
    setConfidence(null);
    setEstimatedTime(predictedTasks.length * 2); // Rough estimate
  }, []);

  const updateTask = useCallback((taskIndex, updates) => {
    setTasks(prev => prev.map((task, i) => 
      i === taskIndex ? { ...task, ...updates } : task
    ));
  }, []);

  const advanceTask = useCallback(() => {
    setCurrentTaskIndex(prev => Math.min(prev + 1, tasks.length));
  }, [tasks.length]);

  const setTaskComplete = useCallback((taskIndex) => {
    setCurrentTaskIndex(prev => Math.max(prev, taskIndex + 1));
  }, []);

  const updateConfidence = useCallback((newConfidence) => {
    setConfidence(newConfidence);
  }, []);

  const stopThinking = useCallback(() => {
    setIsThinking(false);
    setCurrentTaskIndex(tasks.length); // Mark all complete
  }, [tasks.length]);

  const resetThinking = useCallback(() => {
    setIsThinking(false);
    setTasks([]);
    setCurrentTaskIndex(0);
    setQuery('');
    setConfidence(null);
    setEstimatedTime(null);
  }, []);

  return {
    isThinking,
    tasks,
    currentTaskIndex,
    query,
    confidence,
    estimatedTime,
    startThinking,
    updateTask,
    advanceTask,
    setTaskComplete,
    updateConfidence,
    stopThinking,
    resetThinking,
    // For passing to component
    componentProps: {
      tasks,
      currentTaskIndex,
      query,
      confidence,
      estimatedTime
    }
  };
};

// Inline thinking indicator for compact display
export const InlineThinking = ({ stage, progress }) => {
  const stages = {
    'thinking': { icon: Brain, text: 'Thinking...' },
    'analyzing': { icon: Target, text: 'Analyzing...' },
    'searching': { icon: Layers, text: 'Searching...' },
    'generating': { icon: Sparkles, text: 'Generating...' }
  };

  const current = stages[stage] || stages.thinking;
  const Icon = current.icon;

  return (
    <div className="flex items-center gap-2 text-slate-400">
      <div className="relative">
        <Icon className="w-4 h-4 animate-pulse" />
        {progress !== undefined && (
          <svg className="absolute -inset-1 w-6 h-6 -rotate-90">
            <circle
              cx="12"
              cy="12"
              r="10"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-slate-700"
            />
            <circle
              cx="12"
              cy="12"
              r="10"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray={`${progress * 63} 63`}
              className="text-blue-400 transition-all duration-500"
            />
          </svg>
        )}
      </div>
      <span className="text-xs">{current.text}</span>
    </div>
  );
};

export default AIThinkingTasks;
