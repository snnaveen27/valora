/**
 * MessageFeedback - Feedback popup for chat messages with auto-save and credit rewards
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { MessageSquare, X, Sparkles, Loader2, CheckCircle, Coins, AlertCircle } from 'lucide-react'
import { API_URL } from '../../apiConfig'

// Credit rewards based on feedback quality
const CREDIT_REWARDS = {
  minimal: 0,      // < 10 characters
  basic: 1,        // 10-50 characters
  good: 3,         // 50-150 characters
  excellent: 5,    // 150+ characters
}

// Calculate credit reward based on content
function calculateCreditReward(content) {
  const length = content.trim().length
  if (length < 10) return CREDIT_REWARDS.minimal
  if (length < 50) return CREDIT_REWARDS.basic
  if (length < 150) return CREDIT_REWARDS.good
  return CREDIT_REWARDS.excellent
}

// Feedback popup component
export default function MessageFeedback({ 
  isOpen, 
  onClose, 
  messageId, 
  messageContent,
  position = 'right',
  onFeedbackSubmitted,
  userCredits 
}) {
  const [feedback, setFeedback] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState(null)
  const [creditsEarned, setCreditsEarned] = useState(0)
  const [showReward, setShowReward] = useState(false)
  const [error, setError] = useState(null)
  
  const textareaRef = useRef(null)
  const saveTimeoutRef = useRef(null)
  const isMountedRef = useRef(true)

  // Auto-focus textarea when opened
  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isOpen])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  // Auto-save functionality
  const autoSave = useCallback(async (content) => {
    if (!content.trim() || !messageId) return
    
    setIsSaving(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_URL}/api/feedback/auto-save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          content: content.trim(),
          timestamp: new Date().toISOString(),
          partial: true
        })
      })
      
      if (!response.ok) throw new Error('Failed to save')
      
      if (isMountedRef.current) {
        setLastSaved(new Date())
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError('Auto-save failed')
      }
    } finally {
      if (isMountedRef.current) {
        setIsSaving(false)
      }
    }
  }, [messageId])

  // Handle feedback text change with debounced auto-save
  const handleFeedbackChange = (e) => {
    const newContent = e.target.value
    setFeedback(newContent)
    
    // Update credit preview
    const reward = calculateCreditReward(newContent)
    setCreditsEarned(reward)
    
    // Debounced auto-save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    
    saveTimeoutRef.current = setTimeout(() => {
      autoSave(newContent)
    }, 1500) // Auto-save after 1.5s of inactivity
  }

  // Submit final feedback
  const handleSubmit = async () => {
    if (!feedback.trim() || !messageId) return
    
    setIsSaving(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_URL}/api/feedback/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          message_content: messageContent?.substring(0, 500), // Include context
          feedback: feedback.trim(),
          quality_score: calculateCreditReward(feedback),
          credits_earned: calculateCreditReward(feedback),
          timestamp: new Date().toISOString()
        })
      })
      
      if (!response.ok) throw new Error('Failed to submit')
      
      const result = await response.json()
      
      if (isMountedRef.current) {
        setShowReward(true)
        onFeedbackSubmitted?.(result.credits_earned || creditsEarned)
        
        // Close after showing reward
        setTimeout(() => {
          if (isMountedRef.current) {
            setShowReward(false)
            onClose()
            setFeedback('') // Reset for next time
          }
        }, 2000)
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError('Failed to submit feedback')
      }
    } finally {
      if (isMountedRef.current) {
        setIsSaving(false)
      }
    }
  }

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div 
      className="absolute right-0 top-full mt-2 z-[100] w-72"
      style={{ 
        animation: 'fadeInSlide 200ms ease-out',
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="bg-surface-secondary rounded-lg shadow-2xl shadow-primary-900/40 border border-primary-700/50 overflow-hidden backdrop-blur-md">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 bg-surface-tertiary/80 border-b border-primary-700/30">
          <div className="flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5 text-primary-400" />
            <span className="text-xs font-medium text-primary-100">Feedback</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-primary-700/50 rounded text-primary-300 hover:text-white transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-3 space-y-3">
          {showReward ? (
            // Reward animation
            <div className="text-center py-4 animate-in zoom-in duration-300">
              <CheckCircle className="w-10 h-10 text-accent-purple mx-auto mb-2" />
              <p className="text-sm font-medium text-primary-100 mb-1">Thank you!</p>
              <div className="flex items-center justify-center gap-1 text-accent-fuchsia">
                <Coins className="w-4 h-4" />
                <span className="text-sm font-bold">+{creditsEarned} credits</span>
              </div>
              <p className="text-xs text-primary-300/70 mt-1">Your feedback helps us improve</p>
            </div>
          ) : (
            <>
              {/* Instructions */}
              <p className="text-[10px] text-primary-300/70">
                Help us improve and get free credits! What did you think of this response?
              </p>
              
              {/* Textarea */}
              <textarea
                ref={textareaRef}
                value={feedback}
                onChange={handleFeedbackChange}
                placeholder="Was this helpful? Accurate? What could be better?"
                className="w-full h-20 px-2.5 py-2 text-xs bg-dark-900 border border-primary-700/50 rounded resize-none focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/30 text-primary-100 placeholder:text-primary-500/50"
                maxLength={500}
              />
              
              {/* Character count & quality indicator */}
              <div className="flex items-center justify-between text-[10px]">
                <span className={`${
                  feedback.length < 10 ? 'text-primary-400/50' :
                  feedback.length < 50 ? 'text-primary-400' :
                  feedback.length < 150 ? 'text-accent-purple' : 'text-accent-fuchsia'
                }`}>
                  {feedback.length}/500
                  {feedback.length >= 150 && <Sparkles className="w-3 h-3 inline ml-1" />}
                </span>
                
                {creditsEarned > 0 && (
                  <span className="text-accent-fuchsia font-medium">
                    +{creditsEarned} credits
                  </span>
                )}
              </div>
              
              {/* Auto-save status */}
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-primary-400/60">
                  {isSaving ? (
                    <span className="flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin text-primary-400" />
                      Saving...
                    </span>
                  ) : lastSaved ? (
                    <span className="text-accent-purple">
                      Saved at {lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  ) : (
                    <span>Auto-saves as you type</span>
                  )}
                </span>
              </div>
              
              {/* Error message */}
              {error && (
                <div className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 p-1.5 rounded">
                  <AlertCircle className="w-3 h-3" />
                  <span>{error}</span>
                </div>
              )}
              
              {/* Submit button */}
              <button
                onClick={handleSubmit}
                disabled={!feedback.trim() || isSaving}
                className="w-full py-2 px-3 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 disabled:bg-surface-tertiary disabled:text-primary-400/50 text-white text-xs font-medium rounded transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-primary-900/30"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    Submit Feedback
                    {creditsEarned > 0 && ` (+${creditsEarned})`}
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// Hook for managing feedback state
export function useMessageFeedback() {
  const [activeFeedbackId, setActiveFeedbackId] = useState(null)
  const [userCredits, setUserCredits] = useState(0)

  const openFeedback = (messageId) => {
    setActiveFeedbackId(messageId)
  }

  const closeFeedback = () => {
    setActiveFeedbackId(null)
  }

  const handleFeedbackSubmitted = (credits) => {
    setUserCredits(prev => prev + credits)
    // Could trigger a toast notification here
  }

  return {
    activeFeedbackId,
    userCredits,
    openFeedback,
    closeFeedback,
    handleFeedbackSubmitted,
    isOpen: (messageId) => activeFeedbackId === messageId
  }
}
