/**
 * Intelligent AI Thinking Tasks - Windsurf-style with real intent detection
 * Shows actual tasks based on query analysis, not hardcoded
 */

import React, { useEffect, useState, useCallback } from 'react';
import { 
  Brain, Target, MapPin, Building2, TrendingUp, Sun, 
  Eye, Layers, Sparkles, CheckCircle2, Circle, Clock,
  Zap, ArrowRight, X, Loader2, Search, BarChart3,
  MessageSquare, Navigation, Shield, AlertCircle
} from 'lucide-react';

// Task definitions with icons and descriptions
const TASK_DEFINITIONS = {
  'intent_classification': {
    icon: Target,
    label: 'Understanding your query',
    getDetail: (intent) => `Detected: ${intent?.replace(/_/g, ' ') || 'analyzing...'}`,
    color: 'blue'
  },
  'geocoding': {
    icon: MapPin,
    label: 'Finding location',
    getDetail: (location) => location ? `Found: ${location}` : 'Resolving address...',
    color: 'emerald'
  },
  'spatial_analysis': {
    icon: Layers,
    label: 'Analyzing surroundings',
    getDetail: (data) => data?.poi_count ? `${data.poi_count} POIs found` : 'Scanning area...',
    color: 'purple'
  },
  'property_search': {
    icon: Search,
    label: 'Searching properties',
    getDetail: (data) => data?.count ? `${data.count} properties found` : 'Querying database...',
    color: 'amber'
  },
  'market_analysis': {
    icon: BarChart3,
    label: 'Analyzing market data',
    getDetail: (data) => data?.trend ? `Trend: ${data.trend}` : 'Computing metrics...',
    color: 'cyan'
  },
  'view_analysis': {
    icon: Eye,
    label: 'Analyzing views & sunlight',
    getDetail: (data) => data?.sky_view ? `Sky view: ${(data.sky_view * 100).toFixed(0)}%` : '3D spatial analysis...',
    color: 'orange'
  },
  'shadow_calculation': {
    icon: Sun,
    label: 'Calculating shadows',
    getDetail: (data) => data?.sunlight_hours ? `${data.sunlight_hours}h sunlight` : 'Computing angles...',
    color: 'yellow'
  },
  'risk_assessment': {
    icon: Shield,
    label: 'Assessing risks',
    getDetail: (data) => data?.risk_level ? `Risk: ${data.risk_level}` : 'Evaluating hazards...',
    color: 'red'
  },
  'investment_analysis': {
    icon: TrendingUp,
    label: 'Investment analysis',
    getDetail: (data) => data?.roi ? `ROI: ${data.roi}%` : 'Computing returns...',
    color: 'green'
  },
  'simulation': {
    icon: Zap,
    label: 'Running simulation',
    getDetail: (data) => data?.scenario ? `Scenario: ${data.scenario}` : 'Modeling impact...',
    color: 'fuchsia'
  },
  'narrative_generation': {
    icon: MessageSquare,
    label: 'Generating response',
    getDetail: () => 'Synthesizing insights...',
    color: 'indigo'
  },
  'tool_execution': {
    icon: Zap,
    label: 'Gathering data',
    getDetail: (tool) => tool ? `Using: ${tool}` : 'Executing tools...',
    color: 'slate'
  }
};

const TaskStep = ({ task, isActive, isComplete, isFailed, progress }) => {
  const def = TASK_DEFINITIONS[task.type] || TASK_DEFINITIONS.tool_execution;
  const Icon = def.icon;
  const color = def.color;
  
  const colorClasses = {
    blue: 'text-blue-400 bg-blue-500/20 border-blue-500/30',
    emerald: 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30',
    purple: 'text-purple-400 bg-purple-500/20 border-purple-500/30',
    amber: 'text-amber-400 bg-amber-500/20 border-amber-500/30',
    cyan: 'text-cyan-400 bg-cyan-500/20 border-cyan-500/30',
    orange: 'text-orange-400 bg-orange-500/20 border-orange-500/30',
    yellow: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30',
    red: 'text-red-400 bg-red-500/20 border-red-500/30',
    green: 'text-green-400 bg-green-500/20 border-green-500/30',
    fuchsia: 'text-fuchsia-400 bg-fuchsia-500/20 border-fuchsia-500/30',
    indigo: 'text-indigo-400 bg-indigo-500/20 border-indigo-500/30',
    slate: 'text-slate-400 bg-slate-500/20 border-slate-500/30'
  };

  return (
    <div className={`
      flex items-center gap-3 py-2 px-3 rounded-lg transition-all duration-300
      ${isActive ? `${colorClasses[color]} border` : 
        isComplete ? 'opacity-60' : 
        isFailed ? 'opacity-80 bg-red-500/10 border border-red-500/20' :
        'opacity-30'}
    `}>
      <div className="relative w-5 h-5 flex-shrink-0">
        {isComplete ? (
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        ) : isFailed ? (
          <AlertCircle className="w-5 h-5 text-red-400" />
        ) : isActive ? (
          <div className="relative">
            <Icon className={`w-5 h-5 text-${color}-400`} />
            {progress !== undefined && (
              <svg className="absolute -inset-0.5 w-6 h-6 -rotate-90">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-700/30" />
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" 
                  strokeDasharray={`${progress * 63} 63`} className={`text-${color}-400`} />
              </svg>
            )}
          </div>
        ) : (
          <Circle className="w-5 h-5 text-slate-600" />
        )}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium truncate ${isActive ? `text-${color}-200` : isComplete ? 'text-slate-400' : 'text-slate-600'}`}>
          {def.label}
        </div>
        {(isActive || isComplete) && task.detail && (
          <div className={`text-xs truncate ${isActive ? `text-${color}-300/70` : 'text-slate-500'}`}>
            {task.detail}
          </div>
        )}
      </div>
      
      {isActive && (
        <Loader2 className={`w-4 h-4 text-${color}-400 animate-spin flex-shrink-0`} />
      )}
    </div>
  );
};

const IntelligentAIThinking = ({ 
  query,
  streamingData,
  onClose,
  className = ''
}) => {
  const [tasks, setTasks] = useState([]);
  const [currentTaskIndex, setCurrentTaskIndex] = useState(-1);
  const [elapsed, setElapsed] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);
  const [detectedIntent, setDetectedIntent] = useState(null);

  // Generate intelligent tasks based on query analysis
  useEffect(() => {
    if (!query) return;
    
    const q = query.toLowerCase();
    const generatedTasks = [];
    
    // Always start with intent classification
    generatedTasks.push({ type: 'intent_classification', detail: 'Analyzing query...' });
    
    // Detect what tasks are needed based on query patterns
    const hasLocation = /\b(in|at|near|around|close to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b/i.test(q);
    const hasCoordinates = /\d+\.?\d*\s*,\s*\d+\.?\d*/.test(q);
    const hasNavigation = /\b(go to|show me|navigate|fly to|where is)\b/i.test(q);
    const hasPropertySearch = /\b(find|search|properties|apartments?|flats?|2bhk|3bhk)\b/i.test(q);
    const hasPrice = /\b(price|cost|worth|value|budget|under|below|lakhs?|crore)\b/i.test(q);
    const hasView = /\b(view|views|skyline|sunlight|shadow|floor)\b/i.test(q);
    const hasInvestment = /\b(invest|roi|return|appreciation|growth|potential)\b/i.test(q);
    const hasRisk = /\b(risk|flood|safe|danger|problem|issue)\b/i.test(q);
    const hasSimulation = /\b(what if|simulate|scenario|impact|if)\b/i.test(q);
    const hasComparison = /\b(compare|versus|vs|better than|difference)\b/i.test(q);
    const hasMarket = /\b(trend|market|price per sqft|average|median)\b/i.test(q);
    
    // Add geocoding if location-related
    if (hasLocation || hasCoordinates || hasNavigation) {
      generatedTasks.push({ 
        type: 'geocoding', 
        detail: hasCoordinates ? 'Resolving coordinates...' : 'Looking up address...'
      });
    }
    
    // Add spatial analysis for area queries
    if (hasLocation || hasNavigation || hasPropertySearch || hasView) {
      generatedTasks.push({ type: 'spatial_analysis', detail: 'Scanning surroundings...' });
    }
    
    // Add property search
    if (hasPropertySearch) {
      generatedTasks.push({ type: 'property_search', detail: 'Querying database...' });
    }
    
    // Add market analysis
    if (hasPrice || hasMarket || hasInvestment) {
      generatedTasks.push({ type: 'market_analysis', detail: 'Computing metrics...' });
    }
    
    // Add view/shadow analysis
    if (hasView) {
      if (q.includes('shadow') || q.includes('sunlight')) {
        generatedTasks.push({ type: 'shadow_calculation', detail: 'Computing sun angles...' });
      } else {
        generatedTasks.push({ type: 'view_analysis', detail: '3D spatial analysis...' });
      }
    }
    
    // Add risk assessment
    if (hasRisk || q.includes('flood')) {
      generatedTasks.push({ type: 'risk_assessment', detail: 'Evaluating hazards...' });
    }
    
    // Add investment analysis
    if (hasInvestment) {
      generatedTasks.push({ type: 'investment_analysis', detail: 'Computing returns...' });
    }
    
    // Add simulation
    if (hasSimulation) {
      generatedTasks.push({ type: 'simulation', detail: 'Modeling scenario...' });
    }
    
    // Always end with narrative generation
    generatedTasks.push({ type: 'narrative_generation', detail: 'Synthesizing response...' });
    
    setTasks(generatedTasks);
    setCurrentTaskIndex(0);
    setElapsed(0);
  }, [query]);

  // Update tasks based on streaming data
  useEffect(() => {
    if (!streamingData) return;
    
    // Update intent when detected
    if (streamingData.intent && !detectedIntent) {
      setDetectedIntent(streamingData.intent);
      setTasks(prev => prev.map((t, i) => 
        i === 0 ? { ...t, detail: `Detected: ${streamingData.intent.replace(/_/g, ' ')}` } : t
      ));
    }
    
    // Advance task based on streaming progress
    if (streamingData.stage) {
      const stageMap = {
        'intent': 0,
        'geocoding': 1,
        'tools': tasks.findIndex(t => t.type === 'spatial_analysis' || t.type === 'property_search'),
        'analysis': tasks.findIndex(t => t.type === 'market_analysis' || t.type === 'view_analysis'),
        'narrative': tasks.findIndex(t => t.type === 'narrative_generation')
      };
      
      const targetIndex = stageMap[streamingData.stage];
      if (targetIndex >= 0) {
        setCurrentTaskIndex(targetIndex);
      }
    }
    
    // Mark complete when done
    if (streamingData.done) {
      setCurrentTaskIndex(tasks.length);
    }
  }, [streamingData, tasks, detectedIntent]);

  // Timer
  useEffect(() => {
    if (currentTaskIndex < 0 || currentTaskIndex >= tasks.length) return;
    
    const interval = setInterval(() => {
      setElapsed(e => e + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [currentTaskIndex, tasks.length]);

  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const progress = tasks.length > 0 ? ((currentTaskIndex) / tasks.length) * 100 : 0;
  const completedTasks = currentTaskIndex;

  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="flex items-center gap-2 px-3 py-2 bg-blue-500/20 border border-blue-500/40 rounded-full text-sm hover:bg-blue-500/30 transition shadow-lg"
      >
        <Brain className="w-4 h-4 text-blue-400" />
        <span className="text-blue-200 font-medium">{completedTasks}/{tasks.length} tasks</span>
        <span className="text-slate-400">·</span>
        <Clock className="w-3 h-3 text-slate-400" />
        <span className="text-slate-400 text-xs">{formatTime(elapsed)}</span>
        <div className="w-16 h-1 bg-slate-700 rounded-full overflow-hidden ml-1">
          <div className="h-full bg-blue-400 rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
      </button>
    );
  }

  if (tasks.length === 0) return null;

  return (
    <div className={`bg-slate-800/95 border border-slate-700 rounded-xl overflow-hidden shadow-2xl backdrop-blur-sm w-full max-w-md ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 bg-slate-700/50 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Brain className="w-5 h-5 text-blue-400" />
            <span className="absolute inset-0 bg-blue-400/30 rounded-full animate-ping" />
          </div>
          <div>
            <span className="text-sm font-semibold text-white">AI Processing</span>
            {detectedIntent && (
              <span className="ml-2 text-xs text-blue-300/70 px-2 py-0.5 bg-blue-500/20 rounded-full">
                {detectedIntent.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded-lg transition"
          >
            <div className="w-4 h-0.5 bg-current rounded" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="px-4 pt-3">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
          <span>Progress</span>
          <span className="font-medium text-blue-400">{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-emerald-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Query Preview */}
      {query && (
        <div className="px-4 py-2 border-b border-slate-700/50">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Query</p>
          <p className="text-sm text-slate-300 truncate" title={query}>
            "{query.length > 60 ? query.slice(0, 60) + '...' : query}"
          </p>
        </div>
      )}

      {/* Task List */}
      <div className="px-2 py-2 space-y-1 max-h-64 overflow-y-auto">
        {tasks.map((task, index) => (
          <TaskStep
            key={`${task.type}-${index}`}
            task={task}
            isActive={index === currentTaskIndex}
            isComplete={index < currentTaskIndex}
            isFailed={task.failed}
            progress={index === currentTaskIndex ? (elapsed % 10) / 10 : undefined}
          />
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-slate-700/30 border-t border-slate-700 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400">{formatTime(elapsed)} elapsed</span>
        </div>
        
        {streamingData?.confidence && (
          <span className={`
            px-2 py-1 rounded-full text-xs font-medium
            ${streamingData.confidence > 0.8 ? 'bg-emerald-500/20 text-emerald-300' :
              streamingData.confidence > 0.6 ? 'bg-amber-500/20 text-amber-300' :
              'bg-red-500/20 text-red-300'}
          `}>
            {(streamingData.confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </div>
    </div>
  );
};

export default IntelligentAIThinking;
