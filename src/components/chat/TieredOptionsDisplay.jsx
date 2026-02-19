/**
 * TieredOptionsDisplay - Displays tiered analysis options for locality evaluation
 * 
 * Features:
 * - Displays options as clickable cards
 * - Shows credit cost for each option
 * - Highlights unavailable options (insufficient credits) with disabled state
 * - Shows user's current credit balance
 * - Handles option selection with appropriate actions
 */

import { memo, useState } from 'react'
import { Search, BarChart3, TrendingUp, Lock, Check, Coins, MapPin, Zap, FileText, AlertCircle } from 'lucide-react'

// Icon mapping for option types
const OPTION_ICONS = {
  quick_overview: Search,
  area_analysis: BarChart3,
  investment_report: TrendingUp,
}

// Emoji mapping for visual appeal
const OPTION_EMOJIS = {
  quick_overview: '🔍',
  area_analysis: '📊',
  investment_report: '📈',
}

// Default icons/emojis if not found
const DEFAULT_ICON = Zap
const DEFAULT_EMOJI = '⚡'

/**
 * Individual option card component
 */
const OptionCard = memo(function OptionCard({ 
  option, 
  userCredits, 
  onSelect, 
  isProcessing,
  locality 
}) {
  const isAvailable = option.available && userCredits >= option.credits
  const isFree = option.credits === 0
  const Icon = OPTION_ICONS[option.id] || DEFAULT_ICON
  const emoji = OPTION_EMOJIS[option.id] || DEFAULT_EMOJI
  
  const handleClick = () => {
    if (!isAvailable || isProcessing) return
    onSelect(option)
  }
  
  return (
    <button
      onClick={handleClick}
      disabled={!isAvailable || isProcessing}
      className={`
        w-full text-left p-3 rounded-lg border transition-all duration-200 group
        ${isAvailable 
          ? 'bg-surface-secondary/80 hover:bg-primary-700/40 border-primary-600/40 hover:border-primary-500/60 cursor-pointer' 
          : 'bg-dark-800/50 border-primary-700/20 cursor-not-allowed opacity-60'
        }
        ${isProcessing ? 'pointer-events-none' : ''}
      `}
    >
      <div className="flex items-start gap-3">
        {/* Icon/Emoji */}
        <div className={`
          shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-lg
          ${isAvailable 
            ? 'bg-primary-700/50 group-hover:bg-primary-600/50' 
            : 'bg-dark-700/50'
          }
        `}>
          <span role="img" aria-label={option.label}>{emoji}</span>
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h4 className={`text-sm font-medium ${isAvailable ? 'text-white' : 'text-primary-400/70'}`}>
              {option.label}
            </h4>
            {isFree && (
              <span className="px-1.5 py-0.5 text-[10px] font-medium bg-emerald-500/20 text-emerald-400 rounded">
                FREE
              </span>
            )}
          </div>
          <p className="text-xs text-primary-300/80 line-clamp-2">
            {option.description}
          </p>
        </div>
        
        {/* Credit cost / Status */}
        <div className="shrink-0 text-right">
          {!isFree && (
            <div className={`flex items-center gap-1 ${isAvailable ? 'text-amber-400' : 'text-red-400/70'}`}>
              {isAvailable ? (
                <>
                  <Coins className="w-3 h-3" />
                  <span className="text-xs font-medium">{option.credits}</span>
                </>
              ) : (
                <>
                  <Lock className="w-3 h-3" />
                  <span className="text-xs">{option.credits}</span>
                </>
              )}
            </div>
          )}
          {isFree && (
            <div className="flex items-center gap-1 text-emerald-400">
              <Check className="w-3 h-3" />
              <span className="text-xs">Free</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Unavailable reason */}
      {!isAvailable && !isFree && userCredits < option.credits && (
        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-red-400/80">
          <AlertCircle className="w-3 h-3" />
          <span>Need {option.credits - userCredits} more credits</span>
        </div>
      )}
    </button>
  )
})

/**
 * Main TieredOptionsDisplay component
 */
const TieredOptionsDisplay = memo(function TieredOptionsDisplay({
  options,
  locality,
  lat,
  lng,
  userCredits = 0,
  onSelectOption,
  isProcessing = false,
}) {
  const [selectedOption, setSelectedOption] = useState(null)
  
  // Sort options by credit cost (free first, then ascending)
  const sortedOptions = [...options].sort((a, b) => a.credits - b.credits)
  
  const handleSelect = (option) => {
    setSelectedOption(option.id)
    if (onSelectOption) {
      onSelectOption({
        ...option,
        locality,
        lat,
        lng,
      })
    }
  }
  
  return (
    <div className="space-y-3">
      {/* Header with locality */}
      {locality && (
        <div className="flex items-center gap-2 text-primary-300/80">
          <MapPin className="w-3.5 h-3.5" />
          <span className="text-xs">Analyzing: <strong className="text-white">{locality}</strong></span>
        </div>
      )}
      
      {/* Options list */}
      <div className="space-y-2">
        {sortedOptions.map((option) => (
          <OptionCard
            key={option.id}
            option={option}
            userCredits={userCredits}
            onSelect={handleSelect}
            isProcessing={isProcessing}
            locality={locality}
          />
        ))}
      </div>
      
      {/* Credit balance footer */}
      <div className="flex items-center justify-between pt-2 border-t border-primary-700/30">
        <div className="flex items-center gap-1.5 text-xs text-primary-400/70">
          <Coins className="w-3 h-3" />
          <span>Your balance:</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-amber-400">{userCredits}</span>
          <span className="text-xs text-primary-400/70">credits</span>
        </div>
      </div>
      
      {/* Processing indicator */}
      {isProcessing && selectedOption && (
        <div className="flex items-center gap-2 text-xs text-primary-300 animate-pulse">
          <div className="w-3 h-3 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
          <span>Processing {options.find(o => o.id === selectedOption)?.label}...</span>
        </div>
      )}
    </div>
  )
})

export default TieredOptionsDisplay
