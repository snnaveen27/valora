/**
 * ChatMessage - Production-grade message component with copy, edit, regenerate
 */

import { useState, useEffect, memo } from 'react'
import { Bot, User, Copy, Check, RotateCcw, Pencil, ChevronDown, ChevronRight, Brain, Loader2, Sparkles, Wrench, MessageSquare } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

// Code block with syntax highlighting and copy button
function CodeBlock({ children, className, ...props }) {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : ''
  const code = String(children).replace(/\n$/, '')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!match) {
    return <code className="bg-dark-800/70 px-1.5 py-0.5 rounded text-sm text-primary-200" {...props}>{children}</code>
  }

  return (
    <div className="relative group my-3">
      <div className="absolute right-2 top-2 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-xs text-primary-400/70">{language}</span>
        <button
          onClick={handleCopy}
          className="p-1.5 bg-dark-700 hover:bg-primary-700 rounded text-primary-300 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-accent-purple" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: '0.5rem',
          fontSize: '0.8rem',
        }}
        {...props}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

// Thinking/Reasoning display - Ollama style (always visible while streaming)
const ThinkingDisplay = memo(function ThinkingDisplay({ thought, thinkingTime, isStreaming, streamingThought }) {
  const [expanded, setExpanded] = useState(false)  // Start collapsed, expand during streaming
  
  const displayThought = streamingThought || thought
  const displayTime = thinkingTime || 0
  
  // Auto-expand during streaming, auto-collapse after streaming stops
  useEffect(() => {
    if (isStreaming) {
      setExpanded(true)  // Always expand during streaming
    } else if (thought && !streamingThought) {
      setExpanded(false)  // Collapse after streaming completes
    }
  }, [isStreaming, thought, streamingThought])
  
  // Early return must come after all hooks
  if (!displayThought) return null
  
  return (
    <div className="mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 px-2 py-1 text-[10px] text-violet-400 hover:text-violet-300 hover:bg-violet-500/5 rounded transition-colors"
      >
        <Brain className={`w-3 h-3 ${isStreaming ? 'animate-pulse' : ''}`} />
        <span className="font-medium">
          {isStreaming ? `Thinking... ${displayTime.toFixed(1)}s` : `Thought (${displayTime.toFixed(1)}s)`}
        </span>
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>
      
      {expanded && displayThought && (
        <div className="mt-1 p-2 bg-dark-900/60 rounded border border-primary-700/30">
          <div className="text-[10px] text-primary-200 leading-relaxed whitespace-pre-wrap font-mono">
            {displayThought}
            {isStreaming && <span className="animate-pulse">▌</span>}
          </div>
        </div>
      )}
    </div>
  )
})

// Agent/Tool execution panel - compact
function AgentExecutionPanel({ agents, tools }) {
  const [expanded, setExpanded] = useState(false)
  
  if (!agents?.length && !tools?.length) return null
  
  return (
    <div className="mb-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 px-2 py-1 text-[10px] text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/5 rounded transition-colors"
      >
        <Wrench className="w-3 h-3" />
        <span className="font-medium">{agents?.length || 0} agents, {tools?.length || 0} tools</span>
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>
      
      {expanded && (
        <div className="mt-1 p-2 bg-dark-900/60 rounded border border-primary-700/30 text-[10px] space-y-1">
          {agents?.map((agent, i) => (
            <div key={i} className="flex items-center gap-2 text-primary-200">
              <span className="w-1 h-1 bg-accent-purple rounded-full" />
              <span className="font-medium text-accent-purple">{agent.name}</span>
              <span className="text-primary-300">{agent.status || 'done'}</span>
            </div>
          ))}
          {tools?.map((tool, i) => (
            <div key={i} className="flex items-center gap-2 text-primary-200">
              <span className="w-1 h-1 bg-primary-400 rounded-full" />
              <span className="font-medium text-primary-400">{tool.name}</span>
              <span className="text-primary-300">{tool.status || 'done'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Typing indicator
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-2">
      <span className="w-2 h-2 bg-primary-400/60 rounded-full animate-bounce" style={{ animationDelay: '0ms', animationDuration: '1s' }} />
      <span className="w-2 h-2 bg-primary-400/60 rounded-full animate-bounce" style={{ animationDelay: '150ms', animationDuration: '1s' }} />
      <span className="w-2 h-2 bg-primary-400/60 rounded-full animate-bounce" style={{ animationDelay: '300ms', animationDuration: '1s' }} />
    </div>
  )
}

// Main ChatMessage component
const ChatMessage = memo(function ChatMessage({ 
  message, 
  index,
  onCopy, 
  onRegenerate, 
  onEdit,
  isLast,
  isLoading,
  showFeedback,
  onToggleFeedback,
  messageId
}) {
  const [copied, setCopied] = useState(false)
  const [showActions, setShowActions] = useState(false)
  
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  
  const handleCopy = async () => {
    const text = message.content || ''
    await navigator.clipboard.writeText(text)
    setCopied(true)
    onCopy?.(text)
    setTimeout(() => setCopied(false), 2000)
  }
  
  return (
    <div 
      className={`flex gap-2 ${isUser ? 'justify-end' : 'justify-start'} w-full items-start`}
    >
      {/* Assistant side - Avatar + permanent buttons */}
      {!isUser && (
        <div className="flex flex-col items-center gap-1 shrink-0">
          {/* Avatar */}
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary-500 to-accent-purple flex items-center justify-center shadow-lg shadow-primary-900/30">
            <Bot className="w-3 h-3 text-white" />
          </div>
          
          {/* Permanent action buttons below avatar */}
          {!message.isLoading && !message.isStreaming && (
            <div className="flex flex-col gap-1 mt-1">
              <button
                onClick={handleCopy}
                className="p-1 bg-surface-secondary hover:bg-primary-700/50 rounded text-primary-300 hover:text-white transition-all shadow-sm border border-primary-700/30"
                title="Copy"
              >
                {copied ? <Check className="w-3 h-3 text-accent-purple" /> : <Copy className="w-3 h-3" />}
              </button>
              
              {isAssistant && isLast && onRegenerate && (
                <button
                  onClick={() => onRegenerate(index)}
                  className="p-1 bg-surface-secondary hover:bg-primary-700/50 rounded text-primary-300 hover:text-white transition-all shadow-sm border border-primary-700/30"
                  title="Regenerate"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              )}
              
              <button
                onClick={() => onToggleFeedback?.(messageId || index)}
                className={`p-1 rounded transition-all shadow-sm border border-primary-700/30 ${
                  showFeedback 
                    ? 'bg-primary-500 text-white' 
                    : 'bg-surface-secondary hover:bg-primary-700/50 text-primary-300 hover:text-white'
                }`}
                title="Give feedback"
              >
                <MessageSquare className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>
      )}
      
      {/* Message bubble */}
      <div className={`relative max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
        isUser 
          ? 'bg-gradient-to-br from-primary-600 to-primary-500 text-white shadow-lg shadow-primary-900/20' 
          : 'bg-surface-secondary text-primary-100 border border-primary-700/30'
      }`}>
        
        {isAssistant ? (
          <div className="space-y-1">
            {/* Thinking display - compact */}
            {(message.streamingThought || message.chainOfThought || message.isThinking || message.thought) && (
              <ThinkingDisplay 
                thought={message.thought || message.chainOfThought}
                thinkingTime={message.thinkingTime}
                isStreaming={message.isThinking}
                streamingThought={message.streamingThought}
              />
            )}
            
            {/* Agent/tool execution */}
            {(message.agents || message.tools) && (
              <AgentExecutionPanel agents={message.agents} tools={message.tools} />
            )}
            
            {/* Loading state */}
            {message.isLoading && !message.isStreaming && !message.streamingThought && !message.isThinking ? (
              <TypingIndicator />
            ) : (
              <>
                {/* Main content - compact prose */}
                {(message.content || message.streamingContent) && (
                  <div className="prose prose-invert prose-xs max-w-none prose-headings:mt-2 prose-headings:mb-1 prose-headings:text-sm prose-headings:font-semibold prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-strong:text-white prose-a:text-primary-400 prose-code:text-xs">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code: CodeBlock
                      }}
                    >
                      {message.content || message.streamingContent}
                    </ReactMarkdown>
                    {message.isStreaming && !message.isThinking && <span className="animate-pulse text-primary-400">▌</span>}
                  </div>
                )}
              </>
            )}
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
      </div>
      
      {/* User avatar - compact */}
      {isUser && (
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary-700 to-primary-800 flex items-center justify-center shrink-0 shadow-lg shadow-primary-900/20">
          <User className="w-3 h-3 text-white" />
        </div>
      )}
    </div>
  )
})

export default ChatMessage
