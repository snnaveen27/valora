/**
 * Windsurf-style AI Thinking Panel - PRODUCTION VERSION
 * Shows user query, task graph with execution status, and results
 * Matches Windsurf IDE's design language
 */

import React, { useEffect, useState } from 'react';
import { 
  Brain, Target, CheckCircle2, Circle, Clock,
  Loader2, ChevronDown, ChevronRight, Lightbulb,
  XCircle, Play, Cpu, Zap, HardDrive, Eye
} from 'lucide-react';

// Task status badge component
const TaskStatusBadge = ({ status, progress }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'complete':
        return { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Done' };
      case 'running':
        return { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: progress > 0 ? `${progress}%` : 'Running' };
      case 'failed':
        return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Failed' };
      case 'pending':
      default:
        return { icon: Circle, color: 'text-slate-500', bg: 'bg-slate-500/10', label: 'Pending' };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${config.bg} ${config.color}`}>
      <Icon className={`w-3 h-3 ${status === 'running' ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  );
};

// Individual task item - Windsurf style
const TaskItem = ({ task, isLast }) => {
  const isComplete = task.status === 'complete';
  const isRunning = task.status === 'running';
  const isFailed = task.status === 'failed';

  return (
    <div className={`flex items-start gap-3 py-2 ${!isLast ? 'border-b border-slate-700/30' : ''}`}>
      {/* Status indicator line */}
      <div className="flex flex-col items-center mt-0.5">
        <div className={`w-2 h-2 rounded-full ${
          isComplete ? 'bg-emerald-400' : 
          isRunning ? 'bg-blue-400 animate-pulse' : 
          isFailed ? 'bg-red-400' : 
          'bg-slate-600'
        }`} />
        {!isLast && (
          <div className={`w-0.5 flex-1 min-h-[20px] mt-1 ${
            isComplete ? 'bg-emerald-500/30' : 'bg-slate-700/30'
          }`} />
        )}
      </div>

      {/* Task content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-medium truncate ${
              isComplete ? 'text-slate-400 line-through' : 
              isRunning ? 'text-blue-300' : 
              isFailed ? 'text-red-400' : 
              'text-slate-300'
            }`}>
              {task.label}
            </div>
            {task.detail && (
              <div className={`text-xs mt-0.5 ${
                isRunning ? 'text-blue-400/70' : 'text-slate-500'
              }`}>
                {task.detail}
              </div>
            )}
          </div>
          <TaskStatusBadge status={task.status} progress={task.progress_percent} />
        </div>

        {/* Tool indicator */}
        {task.tool && (
          <div className="flex items-center gap-1 mt-1.5">
            <Cpu className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] text-slate-500">{task.tool}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Main panel component
const WindsurfThinkingPanel = ({ 
  query,
  streamingData,
  onClose,
  className = ''
}) => {
  const [tasks, setTasks] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);
  const [detectedIntent, setDetectedIntent] = useState(null);
  const [showDetails, setShowDetails] = useState(true);
  const [confidence, setConfidence] = useState(0);
  const [reasoning, setReasoning] = useState('');
  const [tools, setTools] = useState([]);
  const [taskGraph, setTaskGraph] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingContent, setThinkingContent] = useState('');
  const [selectedModel, setSelectedModel] = useState(null);

  // Initialize
  useEffect(() => {
    if (!query) return;
    
    setIsThinking(true);
    setTasks([]);
    setTaskGraph(null);
    setDetectedIntent(null);
    setConfidence(0);
    setReasoning('');
    setTools([]);
    setElapsed(0);
    setSelectedModel(null);
  }, [query]);

  // Handle streaming data
  useEffect(() => {
    if (!streamingData) return
    
    // Handle thinking content from streaming data
    if (streamingData.thinking) {
      setThinkingContent(streamingData.thinking);
      setIsThinking(true);
    }
    
    switch (streamingData.type) {
      case 'intent_classification_start':
        setIsThinking(true);
        break;
        
      case 'thinking_start':
        setIsThinking(true);
        break;
        
      case 'thinking':
        // Keep thinking state active while streaming thinking content
        setIsThinking(true);
        break;
        
      case 'thinking_end':
        setIsThinking(false);
        break;
        
      case 'intent_detected':
        setDetectedIntent(streamingData.intent);
        setConfidence(streamingData.confidence || 0);
        setReasoning(streamingData.reasoning || '');
        // Don't set isThinking to false here - let thinking content keep streaming
        
        // Handle task graph
        if (streamingData.task_graph) {
          setTaskGraph(streamingData.task_graph);
          const graphTasks = streamingData.task_graph.tasks || [];
          setTasks(graphTasks.map((task, i) => ({
            id: task.id || `task_${i}`,
            label: task.label || task,
            detail: task.description || '',
            type: task.type || 'action',
            status: task.status || 'pending',
            progress_percent: task.progress_percent || 0,
            tool: task.tool
          })));
        } else if (streamingData.tasks) {
          setTasks(streamingData.tasks.map((task, i) => ({
            id: `task_${i}`,
            label: typeof task === 'string' ? task : task.label,
            detail: typeof task === 'object' ? task.detail : '',
            status: 'pending',
            type: 'action',
            progress_percent: 0
          })));
        }
        
        if (streamingData.tools_needed) {
          setTools(streamingData.tools_needed);
        }
        break;
        
      case 'task_progress':
        if (streamingData.task_graph) {
          setTaskGraph(streamingData.task_graph);
          const updatedTasks = streamingData.task_graph.tasks || [];
          setTasks(prev => prev.map(task => {
            const updated = updatedTasks.find(t => t.id === task.id);
            return updated ? { ...task, ...updated } : task;
          }));
        }
        break;
        
      case 'model_selection':
        setSelectedModel({
          model: streamingData.model,
          is_cloud: streamingData.is_cloud,
          is_vision: streamingData.is_vision,
          escalated: streamingData.escalated,
          complexity_score: streamingData.complexity_score,
          reasoning: streamingData.model_reasoning || streamingData.reasoning,
        });
        break;
        
      case 'done':
        setTasks(prev => prev.map(t => ({ ...t, status: 'complete', progress_percent: 100 })));
        setIsThinking(false);
        // Auto-collapse the panel after completion
        setIsMinimized(true);
        break;
    }
  }, [streamingData]);

  // Timer
  useEffect(() => {
    if (!query || streamingData?.type === 'done') return;
    const interval = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(interval);
  }, [query, streamingData]);

  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const completedCount = tasks.filter(t => t.status === 'complete').length;
  const runningCount = tasks.filter(t => t.status === 'running').length;
  const progress = tasks.length > 0 ? (completedCount / tasks.length) * 100 : 0;

  // Minimized view
  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 rounded-lg text-sm transition-all"
      >
        {isThinking ? (
          <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
        ) : (
          <Brain className="w-4 h-4 text-blue-400" />
        )}
        <span className="text-slate-300">
          {isThinking ? 'Thinking...' : `${completedCount}/${tasks.length} tasks`}
        </span>
        <span className="text-slate-500">·</span>
        <Clock className="w-3 h-3 text-slate-500" />
        <span className="text-slate-500 text-xs">{formatTime(elapsed)}</span>
        {detectedIntent && !isThinking && (
          <span className="ml-2 px-2 py-0.5 bg-emerald-500/20 text-emerald-300 rounded text-[10px]">
            {detectedIntent}
          </span>
        )}
      </button>
    );
  }

  // Empty state - show as long as we have query and either intent or we're still processing
  const hasActivity = detectedIntent || isThinking || tasks.length > 0 || thinkingContent;
  if (!query || (!hasActivity && streamingData?.type === 'done')) return null;

  return (
    <div className={`bg-slate-900/95 border border-slate-700 rounded-xl overflow-hidden shadow-2xl w-full max-w-md ${className}`}>
      {/* Header - Query */}
      <div className="px-4 py-3 bg-slate-800/50 border-b border-slate-700/50">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
            <span className="text-xs text-blue-400 font-medium">U</span>
          </div>
          <span className="text-xs text-slate-500 uppercase tracking-wider">Query</span>
        </div>
        <p className="text-sm text-slate-200 leading-relaxed pl-7">{query}</p>
      </div>

      {/* Task Execution Section */}
      <div className="border-b border-slate-700/50">
        {/* Section Header */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            {showDetails ? (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-500" />
            )}
            <Target className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-slate-200">
              {isThinking ? 'Analyzing...' : 'Execution Plan'}
            </span>
            {!isThinking && (
              <span className="text-xs text-slate-500">
                ({completedCount}/{tasks.length})
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!isThinking && (
              <span className="px-2 py-0.5 bg-blue-500/10 text-blue-300 rounded text-[10px]">
                {Math.round(confidence * 100)}%
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsMinimized(true);
              }}
              className="p-1 text-slate-500 hover:text-slate-300"
            >
              <div className="w-3 h-0.5 bg-current rounded" />
            </button>
          </div>
        </button>

        {/* Progress Bar */}
        {tasks.length > 0 && (
          <div className="px-4 pb-2">
            <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Task List */}
        {showDetails && (
          <div className="px-4 pb-3">
            {isThinking ? (
              <div className="flex items-center gap-2 py-3 text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Planning execution...</span>
              </div>
            ) : tasks.length > 0 ? (
              <div className="pt-1">
                {tasks.map((task, index) => (
                  <TaskItem 
                    key={task.id || index} 
                    task={task} 
                    isLast={index === tasks.length - 1}
                  />
                ))}
              </div>
            ) : (
              <div className="py-3 text-xs text-slate-500 italic">
                No tasks generated
              </div>
            )}

            {/* Tools */}
            {tools.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3 pt-2 border-t border-slate-700/30">
                {tools.map((tool, i) => (
                  <span 
                    key={i} 
                    className="flex items-center gap-1 px-2 py-1 bg-slate-800 text-slate-400 text-[10px] rounded border border-slate-700"
                  >
                    <Cpu className="w-3 h-3" />
                    {tool}
                  </span>
                ))}
              </div>
            )}

            {/* Model Selection Info */}
            {selectedModel && (
              <div className="mt-3 pt-2 border-t border-slate-700/30">
                <div className="flex items-center gap-2 flex-wrap">
                  {selectedModel.is_vision ? (
                    <Eye className="w-3.5 h-3.5 text-purple-400" />
                  ) : selectedModel.is_cloud ? (
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                  ) : (
                    <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  <span className={`text-xs font-medium ${
                    selectedModel.is_vision ? 'text-purple-300' :
                    selectedModel.is_cloud ? 'text-amber-300' : 'text-slate-300'
                  }`}>
                    {selectedModel.model}
                  </span>
                  {selectedModel.escalated && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">
                      escalated
                    </span>
                  )}
                  {selectedModel.is_vision && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 font-medium">
                      vision
                    </span>
                  )}
                  {!selectedModel.is_cloud && !selectedModel.escalated && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 font-medium">
                      local
                    </span>
                  )}
                </div>
                {/* Complexity score bar */}
                {selectedModel.complexity_score > 0 && (
                  <div className="flex items-center gap-2 mt-1.5 ml-5">
                    <span className="text-[9px] text-slate-500 w-14">complexity</span>
                    <div className="flex-1 h-1 bg-slate-700/50 rounded-full overflow-hidden max-w-[100px]">
                      <div
                        className={`h-full rounded-full transition-all ${
                          selectedModel.complexity_score > 0.6 ? 'bg-amber-500' :
                          selectedModel.complexity_score > 0.35 ? 'bg-blue-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.round(selectedModel.complexity_score * 100)}%` }}
                      />
                    </div>
                    <span className="text-[9px] text-slate-500">{Math.round(selectedModel.complexity_score * 100)}%</span>
                  </div>
                )}
                {selectedModel.reasoning && (
                  <p className="text-[10px] text-slate-500 mt-1 ml-5 leading-relaxed">
                    {selectedModel.reasoning}
                  </p>
                )}
              </div>
            )}

            {/* Streaming Thinking Content */}
            {thinkingContent && isThinking && (
              <div className="mt-3 pt-2 border-t border-slate-700/30">
                <div className="flex items-start gap-2">
                  <Loader2 className="w-3 h-3 text-blue-400 mt-0.5 animate-spin" />
                  <div className="flex-1">
                    <p className="text-[10px] text-blue-400 uppercase tracking-wide mb-1">Thinking</p>
                    <p className="text-xs text-slate-300 font-mono whitespace-pre-wrap">{thinkingContent}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Reasoning */}
            {reasoning && (
              <div className="mt-3 pt-2 border-t border-slate-700/30">
                <div className="flex items-start gap-2">
                  <Lightbulb className="w-3 h-3 text-slate-500 mt-0.5" />
                  <p className="text-xs text-slate-400 italic">"{reasoning}"</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="px-4 py-2 bg-slate-800/30 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3 text-slate-500">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatTime(elapsed)}
          </span>
          {runningCount > 0 && (
            <span className="flex items-center gap-1 text-blue-400">
              <Play className="w-3 h-3" />
              {runningCount} running
            </span>
          )}
          {selectedModel && (
            <span className={`flex items-center gap-1 ${
              selectedModel.is_cloud ? 'text-amber-400' : 'text-slate-400'
            }`}>
              {selectedModel.is_cloud ? <Zap className="w-3 h-3" /> : <HardDrive className="w-3 h-3" />}
              {selectedModel.model}
            </span>
          )}
        </div>
        
        {progress >= 100 && (
          <span className="flex items-center gap-1 text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            Complete
          </span>
        )}
      </div>
    </div>
  );
};

export default WindsurfThinkingPanel;
