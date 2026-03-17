/**
 * ChatInputBar - Valora AI
 * Default: qwen3:4b-instruct local. Cloud toggle enables intelligent model routing.
 * The model router auto-selects the best model based on query complexity.
 * Includes language selector for multilingual support with UI translations.
 */

import { useRef, useEffect, useState } from 'react'
import { Send, Image, HardDrive, StopCircle, X, ChevronDown, Languages } from 'lucide-react'
import { API_URL } from '../../apiConfig'
import { t, LANGUAGES } from '../../i18n/translations'

const LANGUAGE_OPTIONS = Object.entries(LANGUAGES).map(([code, info]) => ({
  id: code,
  label: info.name,
  native: info.native,
  flag: info.flag
}))

export default function ChatInputBar({
  value,
  onChange,
  onSend,
  onStop,
  onImageAttach,
  attachedImages,
  onRemoveImage,
  isLoading,
  llmConfig,
  onConfigChange,
  credits,
  placeholder = "Ask me anything about Bangalore real estate...",
  selectedLanguage = 'en',
  onLanguageChange
}) {
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
  const [availableModels, setAvailableModels] = useState([])
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)

  // Focus input on mount
  useEffect(() => { inputRef.current?.focus() }, [])

  // Fetch available models on mount with retry
  useEffect(() => {
    const fetchModels = async (retryCount = 0) => {
      setLoadingModels(true)
      try {
        const response = await fetch(`${API_URL}/api/admin/llm-models`)
        if (response.ok) {
          const data = await response.json()
          setAvailableModels(data.local || [])
          console.log('[ChatInputBar] Loaded models:', data.local?.length || 0, 'local models')
        } else {
          console.error('[ChatInputBar] Failed to fetch models:', response.status, response.statusText)
          // Retry up to 3 times with exponential backoff
          if (retryCount < 3) {
            const delay = Math.pow(2, retryCount) * 1000 // 1s, 2s, 4s
            console.log(`[ChatInputBar] Retrying in ${delay}ms...`)
            setTimeout(() => fetchModels(retryCount + 1), delay)
          }
        }
      } catch (error) {
        console.warn('[ChatInputBar] Failed to fetch models:', error.message)
        // Retry up to 3 times with exponential backoff
        if (retryCount < 3) {
          const delay = Math.pow(2, retryCount) * 1000 // 1s, 2s, 4s
          console.log(`[ChatInputBar] Retrying in ${delay}ms...`)
          setTimeout(() => fetchModels(retryCount + 1), delay)
        }
      } finally {
        setLoadingModels(false)
      }
    }
    fetchModels()
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showModelDropdown && !event.target.closest('.model-dropdown-container')) {
        setShowModelDropdown(false)
      }
      if (showLanguageDropdown && !event.target.closest('.language-dropdown-container')) {
        setShowLanguageDropdown(false)
      }
    }

    if (showModelDropdown || showLanguageDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showModelDropdown, showLanguageDropdown])

  // Reset textarea height when value is cleared
  useEffect(() => {
    if (!value && inputRef.current) inputRef.current.style.height = 'auto'
  }, [value])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend() }
  }

  const handleInput = (e) => {
    const ta = e.target
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'
  }

  const handleFileSelect = (e) => {
    Array.from(e.target.files || []).forEach(file => {
      if (!file.type?.startsWith('image/')) return
      const reader = new FileReader()
      reader.onload = () => {
        const dataUrl = String(reader.result || '')
        const base64 = dataUrl.includes('base64,') ? dataUrl.split('base64,')[1] : dataUrl
        onImageAttach?.({ base64, mime: file.type, name: file.name })
      }
      reader.readAsDataURL(file)
    })
    e.target.value = ''
  }

  const handleModelSelect = (modelId) => {
    onConfigChange?.({ ...llmConfig, local_model: modelId })
    setShowModelDropdown(false)
    // Save to localStorage for persistence
    localStorage.setItem('valora_selected_model', modelId)
  }

  const currentModel = llmConfig.local_model || 'valora-ai-mini'
  const currentModelDisplay = availableModels.find(m => m.id === currentModel)?.name || currentModel
  const currentLanguage = LANGUAGE_OPTIONS.find(l => l.id === selectedLanguage) || LANGUAGE_OPTIONS[0]
  
  // Get translated placeholder based on selected language
  const translatedPlaceholder = t('placeholder', selectedLanguage)

  const hasImages = attachedImages && attachedImages.length > 0
  const imageCount = attachedImages?.length || 0
  
  const handleLanguageSelect = (langId) => {
    onLanguageChange?.(langId)
    setShowLanguageDropdown(false)
    // Save to localStorage for persistence
    localStorage.setItem('valora_selected_language', langId)
  }

  return (
    <div className="p-3 border-t border-primary-700/30 bg-surface-primary/50 backdrop-blur-sm">
      {/* Attached images preview */}
      {hasImages && (
        <div className="mb-2 flex flex-wrap gap-2">
          {attachedImages.map((img, idx) => (
            <div key={idx} className="flex items-center gap-2 p-2 bg-surface-secondary/50 rounded-lg border border-primary-700/30">
              <div className="w-12 h-12 bg-dark-700 rounded overflow-hidden">
                <img src={`data:${img.mime};base64,${img.base64}`} alt={`Attached ${idx + 1}`} className="w-full h-full object-cover" />
              </div>
              <div className="flex-1 min-w-0 max-w-[120px]">
                <div className="text-xs text-white truncate">{img.name}</div>
                <div className="text-[10px] text-primary-300">Image {idx + 1}</div>
              </div>
              <button onClick={() => onRemoveImage(idx)} className="p-1 text-primary-300 hover:text-white hover:bg-primary-700/30 rounded transition-colors">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Compact status row: model selector + hints */}
      <div className="relative mb-1.5">
        <div className="flex items-center gap-2">
          {/* Model selector dropdown - always visible, model selection is automated */}
          <div className="relative model-dropdown-container">
            <button
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              disabled={loadingModels}
              className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium border transition-all bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
              title="Model selection is automated based on query complexity"
            >
              <HardDrive className="w-3 h-3" />
              <span className="max-w-[80px] truncate">
                {loadingModels ? 'Loading...' : currentModelDisplay.split(':')[0]}
              </span>
              <ChevronDown className={`w-3 h-3 transition-transform ${showModelDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {/* Dropdown */}
            {showModelDropdown && (
              <div className="absolute bottom-full left-0 mb-2 w-48 bg-dark-800 border border-primary-700/50 rounded-lg shadow-lg shadow-dark-900/50 z-50 max-h-48 overflow-y-auto">
                <div className="p-2">
                  <div className="text-[10px] text-primary-400/60 font-medium mb-2 px-2">Local Models</div>
                  {availableModels.length === 0 ? (
                    <div className="text-[10px] text-primary-400/40 px-2 py-1">No models found</div>
                  ) : (
                    availableModels.map((model) => (
                      <button
                        key={model.id}
                        onClick={() => handleModelSelect(model.id)}
                        className={`w-full text-left px-2 py-1.5 rounded text-[10px] transition-colors ${
                          model.id === currentModel
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'text-primary-300 hover:bg-primary-700/30 hover:text-white'
                        }`}
                      >
                        <div className="font-medium">{model.name}</div>
                        {model.size && (
                          <div className="text-primary-400/60">{model.size}</div>
                        )}
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Language selector dropdown */}
          <div className="relative language-dropdown-container">
            <button
              onClick={() => setShowLanguageDropdown(!showLanguageDropdown)}
              className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium border transition-all bg-blue-500/10 text-blue-400 border-blue-500/30 hover:bg-blue-500/20"
              title="Select language for responses"
            >
              <Languages className="w-3 h-3" />
              <span>{currentLanguage.flag}</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${showLanguageDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {/* Language Dropdown */}
            {showLanguageDropdown && (
              <div className="absolute bottom-full left-0 mb-2 w-40 bg-dark-800 border border-primary-700/50 rounded-lg shadow-lg shadow-dark-900/50 z-50">
                <div className="p-2">
                  <div className="text-[10px] text-primary-400/60 font-medium mb-2 px-2">Response Language</div>
                  {LANGUAGE_OPTIONS.map((lang) => (
                    <button
                      key={lang.id}
                      onClick={() => handleLanguageSelect(lang.id)}
                      className={`w-full text-left px-2 py-1.5 rounded text-[10px] transition-colors flex items-center gap-2 ${
                        lang.id === selectedLanguage
                          ? 'bg-blue-500/20 text-blue-300'
                          : 'text-primary-300 hover:bg-primary-700/30 hover:text-white'
                      }`}
                    >
                      <span>{lang.flag}</span>
                      <div>
                        <div className="font-medium">{lang.label}</div>
                        <div className="text-primary-400/60">{lang.native}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Credits badge */}
          {credits && (() => {
            const tier = credits.tier || 'free'
            const rem = credits.credits?.remaining ?? '...'
            const tot = credits.credits?.total ?? '...'
            const pct = tot > 0 ? Math.round((rem / tot) * 100) : 0
            const barColor = pct > 50 ? 'bg-emerald-500' : pct > 20 ? 'bg-amber-500' : 'bg-red-500'
            const tierColor = tier === 'pro' ? 'text-amber-400' : tier === 'team' ? 'text-purple-400' : 'text-slate-400'
            return (
              <div className="flex items-center gap-1.5" title={`${tier} tier — ${rem}/${tot} credits`}>
                <span className={`text-[10px] font-semibold uppercase ${tierColor}`}>{tier}</span>
                <div className="w-10 h-1 bg-primary-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                </div>
                <span className="text-[10px] text-primary-400/70">{rem}/{tot}</span>
              </div>
            )
          })()}

          <div className="flex-1" />

          <span className="text-[10px] text-primary-400/40">
            Enter to send{imageCount > 0 ? ` • ${imageCount} img` : ''}
          </span>
        </div>
      </div>

      {/* Input row */}
      <div className="flex gap-1.5">
        <input ref={fileInputRef} type="file" accept="image/*" multiple onChange={handleFileSelect} className="hidden" />

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          className="p-2 bg-surface-tertiary/60 hover:bg-primary-700/30 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors shrink-0 relative"
          title="Attach images (multiple allowed)"
        >
          <Image className="w-4 h-4 text-primary-300" />
          {imageCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-accent-fuchsia text-white text-[10px] rounded-full flex items-center justify-center">
              {imageCount}
            </span>
          )}
        </button>

        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={translatedPlaceholder}
          disabled={isLoading}
          rows={1}
          className="flex-1 bg-dark-800/50 border border-primary-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-primary-400/50 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/30 disabled:opacity-50 min-w-0 resize-none overflow-y-auto max-h-[200px]"
        />

        {isLoading ? (
          <button type="button" onClick={onStop} className="p-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-all shadow-lg shadow-red-900/30 shrink-0" title={t('stop', selectedLanguage)}>
            <StopCircle className="w-4 h-4" />
          </button>
        ) : (
          <button type="submit" disabled={!value.trim()} className="p-2 bg-gradient-to-br from-primary-600 to-accent-purple hover:from-primary-500 hover:to-accent-purple/90 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary-900/30 shrink-0" title={t('send', selectedLanguage)}>
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}
