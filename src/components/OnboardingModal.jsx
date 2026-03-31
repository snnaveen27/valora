/**
 * OnboardingModal - New user preference collection modal
 * 
 * Features:
 * - Identity selection (broker/developer/buyer) - Layer 1
 * - Intent selection (buy/sell/both) - for Buyers
 * - Workspace selection (individual/team) - Layer 2
 * - Preferred areas/localities
 * - Budget range selection
 * - Language preference (English, Hindi, Kannada, Tamil)
 * - Stores preferences in localStorage and sends to backend
 * 
 * 4-Layer Identity Model:
 * 1. Identity Layer - WHO they are (broker/developer/buyer)
 * 2. Intent Layer - WHAT they want (buy/sell/both)
 * 3. Workspace Layer - HOW they operate (individual/team)
 * 4. Workspace Role - WHO can do what (manager/member) - set based on workspace
 * 5. Subscription Plan - WHAT they can access (free/pro/team)
 */

import { useState, useEffect } from 'react'
import { Home, Building2, TrendingUp, MapPin, Wallet, Languages, ChevronRight, Check, Sparkles, Users, User, Tag, Search } from 'lucide-react'
import { API_URL } from '../apiConfig'

// Layer 1: Identity Options
const IDENTITY_OPTIONS = [
  { id: 'broker', label: 'Broker', icon: TrendingUp, description: 'Deals, clients, listings, workflows. Your core engine.' },
  { id: 'developer', label: 'Developer', icon: Building2, description: 'Project planning, land acquisition, pricing strategy.' },
  { id: 'buyer', label: 'Buyer', icon: Home, description: 'Home buyers, investors, NRI users. Personal decisions.' }
]

// Intent Options (Buyers can also sell)
const INTENT_OPTIONS = [
  { id: 'buy', label: 'Buy', icon: Search, description: 'Looking to purchase a property' },
  { id: 'sell', label: 'Sell', icon: Tag, description: 'Want to list and sell my property' },
  { id: 'both', label: 'Both', icon: TrendingUp, description: 'Buy and sell - complete transactions' }
]

// Layer 2: Workspace Options
const WORKSPACE_OPTIONS = [
  { id: 'individual', label: 'Individual', icon: User, description: 'Solo operator. Own workspace, own data, own limits.' },
  { id: 'team', label: 'Team', icon: Users, description: 'Agency, developer org, or family. Shared workspace with team members.' }
]

const BUDGET_OPTIONS = [
  { id: 'budget', label: 'Budget', range: 'Under ₹50 Lakhs' },
  { id: 'mid', label: 'Mid-Range', range: '₹50 Lakhs - ₹1 Crore' },
  { id: 'premium', label: 'Premium', range: '₹1 Crore - ₹3 Crore' },
  { id: 'luxury', label: 'Luxury', range: 'Above ₹3 Crore' }
]

const LANGUAGE_OPTIONS = [
  { id: 'en', label: 'English', native: 'English' },
  { id: 'hi', label: 'Hindi', native: 'हिंदी' },
  { id: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
  { id: 'ta', label: 'Tamil', native: 'தமிழ்' }
]

const BANGALORE_AREAS = [
  'Whitefield', 'Electronic City', 'Koramangala', 'Indiranagar', 'HSR Layout',
  'JP Nagar', 'Jayanagar', 'BTM Layout', 'Marathahalli', 'Bellandur',
  'Sarjapur', 'Hebbal', 'Yelahanka', 'Kengeri', 'Banashankari',
  'Malleshwaram', 'Rajajinagar', 'Vijayanagar', 'RT Nagar', 'HBR Layout'
]

export default function OnboardingModal({ isOpen, onComplete }) {
  // Steps: 1: Identity, 2: Intent (for Buyers), 3: Workspace, 4: Areas, 5: Budget, 6: Language
  const [step, setStep] = useState(1)
  const [preferences, setPreferences] = useState({
    identityRole: '', // Layer 1: broker/developer/buyer
    intent: '', // buy/sell/both (for Buyers only)
    workspaceType: '', // Layer 3: individual/team
    workspaceRole: '', // Layer 4: manager/member (derived from workspace)
    preferredAreas: [],
    budgetRange: '',
    language: 'en'
  })
  const [areaInput, setAreaInput] = useState('')
  const [filteredAreas, setFilteredAreas] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Filter areas based on input
  useEffect(() => {
    if (areaInput.length > 0) {
      const filtered = BANGALORE_AREAS.filter(area => 
        area.toLowerCase().includes(areaInput.toLowerCase()) &&
        !preferences.preferredAreas.includes(area)
      )
      setFilteredAreas(filtered.slice(0, 5))
    } else {
      setFilteredAreas([])
    }
  }, [areaInput, preferences.preferredAreas])

  const handleIdentitySelect = (identityId) => {
    setPreferences(prev => ({ ...prev, identityRole: identityId }))
  }

  const handleIntentSelect = (intentId) => {
    setPreferences(prev => ({ ...prev, intent: intentId }))
  }

  const handleWorkspaceSelect = (workspaceId) => {
    // Layer 3: workspace role is derived from workspace type
    // Individual = manager (full access)
    // Team = member initially (can be promoted to manager later)
    const workspaceRole = workspaceId === 'team' ? 'member' : 'manager'
    setPreferences(prev => ({ 
      ...prev, 
      workspaceType: workspaceId,
      workspaceRole 
    }))
  }

  const handleAreaAdd = (area) => {
    if (!preferences.preferredAreas.includes(area) && preferences.preferredAreas.length < 5) {
      setPreferences(prev => ({ 
        ...prev, 
        preferredAreas: [...prev.preferredAreas, area] 
      }))
    }
    setAreaInput('')
    setFilteredAreas([])
  }

  const handleAreaRemove = (area) => {
    setPreferences(prev => ({ 
      ...prev, 
      preferredAreas: prev.preferredAreas.filter(a => a !== area) 
    }))
  }

  const handleBudgetSelect = (budgetId) => {
    setPreferences(prev => ({ ...prev, budgetRange: budgetId }))
  }

  const handleLanguageSelect = (langId) => {
    setPreferences(prev => ({ ...prev, language: langId }))
  }

  const handleNext = () => {
    // Steps: 1: Identity, 2: Intent, 3: Workspace, 4: Areas, 5: Budget, 6: Language
    if (step === 1 && preferences.identityRole) {
      // Skip intent step for developers - they're always selling
      if (preferences.identityRole === 'developer') {
        setPreferences(prev => ({ ...prev, intent: 'sell' }))
        setStep(3)
      } else {
        setStep(2)
      }
    } else if (step === 2 && preferences.intent) {
      setStep(3)
    } else if (step === 3 && preferences.workspaceType) {
      setStep(4)
    } else if (step === 4) {
      setStep(5)
    } else if (step === 5 && preferences.budgetRange) {
      setStep(6)
    }
  }

  const handleBack = () => {
    if (step > 1) setStep(step - 1)
  }

  const handleComplete = async () => {
    setIsSubmitting(true)
    setError(null)
    
    try {
      // Get user ID from localStorage or generate one
      const userId = localStorage.getItem('valora_user_id') || `user_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`
      localStorage.setItem('valora_user_id', userId)
      
      // Send preferences to backend
      try {
        await fetch(`${API_URL}/api/user/preferences`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            preferences: preferences
          })
        })
      } catch (apiError) {
        console.warn('[Onboarding] Failed to save preferences to backend, saving locally only:', apiError)
      }
      
      // Save to localStorage
      localStorage.setItem('valora_preferences', JSON.stringify({
        ...preferences,
        completedAt: new Date().toISOString()
      }))
      
      // Mark onboarding as completed
      localStorage.setItem('valora_onboarding_complete', 'true')
      
      onComplete(preferences)
    } catch (err) {
      console.error('[Onboarding] Error saving preferences:', err)
      setError('Failed to save preferences. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSkip = () => {
    // Save default preferences
    const defaultPreferences = {
      identityRole: 'buyer',
      intent: 'buy',
      workspaceType: 'individual',
      workspaceRole: 'manager',
      preferredAreas: [],
      budgetRange: 'mid',
      language: 'en'
    }
    localStorage.setItem('valora_preferences', JSON.stringify({
      ...defaultPreferences,
      skippedAt: new Date().toISOString()
    }))
    localStorage.setItem('valora_onboarding_complete', 'true')
    onComplete(defaultPreferences)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="bg-dark-900 border border-primary-700/50 rounded-2xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-accent-purple p-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Sparkles className="w-6 h-6 text-yellow-300" />
            <h2 className="text-xl font-bold text-white">Welcome to Valora!</h2>
            <Sparkles className="w-6 h-6 text-yellow-300" />
          </div>
          <p className="text-primary-100 text-sm">Let's personalize your real estate experience</p>
          
          {/* Progress indicator */}
          <div className="flex items-center justify-center gap-2 mt-4">
            {[1, 2, 3, 4, 5, 6].map((s) => (
              <div 
                key={s} 
                className={`w-5 h-1.5 rounded-full transition-all ${
                  s <= step ? 'bg-white' : 'bg-white/30'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step 1: Identity Role */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-2">How would you describe yourself?</h3>
              <p className="text-sm text-primary-400 mb-4">This determines your AI assistant and dashboard features</p>
              <div className="grid grid-cols-1 gap-3">
                {IDENTITY_OPTIONS.map((option) => {
                  const Icon = option.icon
                  const isSelected = preferences.identityRole === option.id
                  return (
                    <button
                      key={option.id}
                      onClick={() => handleIdentitySelect(option.id)}
                      className={`p-4 rounded-xl border-2 transition-all text-left ${
                        isSelected 
                          ? 'border-primary-500 bg-primary-500/20' 
                          : 'border-primary-700/50 hover:border-primary-500/50 bg-dark-800/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-primary-500' : 'bg-primary-700/30'}`}>
                          <Icon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-primary-300'}`} />
                        </div>
                        <div>
                          <p className={`font-medium ${isSelected ? 'text-white' : 'text-primary-200'}`}>
                            {option.label}
                          </p>
                          <p className="text-xs text-primary-400 mt-0.5">{option.description}</p>
                        </div>
                        {isSelected && <Check className="w-5 h-5 text-primary-400 ml-auto" />}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 2: Intent (Buy/Sell/Both) */}
          {step === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-2">What do you want to do?</h3>
              <p className="text-sm text-primary-400 mb-4">Choose your primary intent</p>
              <div className="grid grid-cols-1 gap-3">
                {INTENT_OPTIONS.map((option) => {
                  const Icon = option.icon
                  const isSelected = preferences.intent === option.id
                  return (
                    <button
                      key={option.id}
                      onClick={() => handleIntentSelect(option.id)}
                      className={`p-4 rounded-xl border-2 transition-all text-left ${
                        isSelected 
                          ? 'border-primary-500 bg-primary-500/20' 
                          : 'border-primary-700/50 hover:border-primary-500/50 bg-dark-800/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-primary-500' : 'bg-primary-700/30'}`}>
                          <Icon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-primary-300'}`} />
                        </div>
                        <div>
                          <p className={`font-medium ${isSelected ? 'text-white' : 'text-primary-200'}`}>
                            {option.label}
                          </p>
                          <p className="text-xs text-primary-400 mt-0.5">{option.description}</p>
                        </div>
                        {isSelected && <Check className="w-5 h-5 text-primary-400 ml-auto" />}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 3: Workspace Type */}
          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-2">How do you operate?</h3>
              <p className="text-sm text-primary-400 mb-4">Select your workspace type</p>
              <div className="grid grid-cols-1 gap-3">
                {WORKSPACE_OPTIONS.map((option) => {
                  const Icon = option.icon
                  const isSelected = preferences.workspaceType === option.id
                  return (
                    <button
                      key={option.id}
                      onClick={() => handleWorkspaceSelect(option.id)}
                      className={`p-4 rounded-xl border-2 transition-all text-left ${
                        isSelected 
                          ? 'border-primary-500 bg-primary-500/20' 
                          : 'border-primary-700/50 hover:border-primary-500/50 bg-dark-800/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-primary-500' : 'bg-primary-700/30'}`}>
                          <Icon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-primary-300'}`} />
                        </div>
                        <div>
                          <p className={`font-medium ${isSelected ? 'text-white' : 'text-primary-200'}`}>
                            {option.label}
                          </p>
                          <p className="text-xs text-primary-400 mt-0.5">{option.description}</p>
                        </div>
                        {isSelected && <Check className="w-5 h-5 text-primary-400 ml-auto" />}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 4: Preferred Areas */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-2">Preferred areas in Bangalore</h3>
              <p className="text-sm text-primary-400 mb-4">Select up to 5 areas you're interested in</p>
              
              {/* Selected areas */}
              {preferences.preferredAreas.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {preferences.preferredAreas.map((area) => (
                    <span 
                      key={area}
                      className="px-3 py-1.5 bg-primary-600/30 border border-primary-500/50 rounded-full text-sm text-primary-200 flex items-center gap-2"
                    >
                      {area}
                      <button 
                        onClick={() => handleAreaRemove(area)}
                        className="text-primary-400 hover:text-white"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
              
              {/* Area input */}
              <div className="relative">
                <input
                  type="text"
                  value={areaInput}
                  onChange={(e) => setAreaInput(e.target.value)}
                  placeholder="Type to search areas..."
                  className="w-full px-4 py-3 bg-dark-800 border border-primary-700/50 rounded-xl text-white placeholder-primary-500 focus:outline-none focus:border-primary-500"
                />
                
                {/* Area suggestions */}
                {filteredAreas.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-dark-800 border border-primary-700/50 rounded-xl overflow-hidden z-10">
                    {filteredAreas.map((area) => (
                      <button
                        key={area}
                        onClick={() => handleAreaAdd(area)}
                        className="w-full px-4 py-2 text-left text-primary-200 hover:bg-primary-700/30 flex items-center gap-2"
                      >
                        <MapPin className="w-4 h-4 text-primary-400" />
                        {area}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Quick select */}
              <div className="mt-4">
                <p className="text-xs text-primary-500 mb-2">Popular areas:</p>
                <div className="flex flex-wrap gap-2">
                  {['Whitefield', 'Koramangala', 'Electronic City', 'Indiranagar', 'HSR Layout']
                    .filter(area => !preferences.preferredAreas.includes(area))
                    .slice(0, 5 - preferences.preferredAreas.length)
                    .map((area) => (
                      <button
                        key={area}
                        onClick={() => handleAreaAdd(area)}
                        className="px-3 py-1 bg-dark-800 border border-primary-700/30 rounded-full text-xs text-primary-300 hover:border-primary-500/50 hover:text-white transition-colors"
                      >
                        + {area}
                      </button>
                    ))
                  }
                </div>
              </div>
            </div>
          )}

          {/* Step 5: Budget Range */}
          {step === 5 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-2">What's your budget range?</h3>
              <p className="text-sm text-primary-400 mb-4">This helps us show you relevant properties</p>
              
              <div className="space-y-3">
                {BUDGET_OPTIONS.map((option) => {
                  const isSelected = preferences.budgetRange === option.id
                  return (
                    <button
                      key={option.id}
                      onClick={() => handleBudgetSelect(option.id)}
                      className={`w-full p-4 rounded-xl border-2 transition-all text-left flex items-center justify-between ${
                        isSelected 
                          ? 'border-primary-500 bg-primary-500/20' 
                          : 'border-primary-700/50 hover:border-primary-500/50 bg-dark-800/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Wallet className={`w-5 h-5 ${isSelected ? 'text-primary-400' : 'text-primary-500'}`} />
                        <div>
                          <p className={`font-medium ${isSelected ? 'text-white' : 'text-primary-200'}`}>
                            {option.label}
                          </p>
                          <p className="text-sm text-primary-400">{option.range}</p>
                        </div>
                      </div>
                      {isSelected && <Check className="w-5 h-5 text-primary-400" />}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 6: Language Preference */}
          {step === 6 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-2">Preferred language</h3>
              <p className="text-sm text-primary-400 mb-4">We'll try to respond in your preferred language</p>
              
              <div className="grid grid-cols-2 gap-3">
                {LANGUAGE_OPTIONS.map((option) => {
                  const isSelected = preferences.language === option.id
                  return (
                    <button
                      key={option.id}
                      onClick={() => handleLanguageSelect(option.id)}
                      className={`p-4 rounded-xl border-2 transition-all ${
                        isSelected 
                          ? 'border-primary-500 bg-primary-500/20' 
                          : 'border-primary-700/50 hover:border-primary-500/50 bg-dark-800/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Languages className={`w-5 h-5 ${isSelected ? 'text-primary-400' : 'text-primary-500'}`} />
                        <div className="text-left">
                          <p className={`font-medium ${isSelected ? 'text-white' : 'text-primary-200'}`}>
                            {option.label}
                          </p>
                          <p className="text-sm text-primary-400">{option.native}</p>
                        </div>
                        {isSelected && <Check className="w-5 h-5 text-primary-400 ml-auto" />}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-dark-800/50 border-t border-primary-700/30 flex items-center justify-between">
          <button
            onClick={handleSkip}
            className="text-sm text-primary-400 hover:text-white transition-colors"
          >
            Skip for now
          </button>
          
          <div className="flex items-center gap-3">
            {step > 1 && (
              <button
                onClick={handleBack}
                className="px-4 py-2 text-sm text-primary-300 hover:text-white transition-colors"
              >
                Back
              </button>
            )}
            
            {step < 6 ? (
              <button
                onClick={handleNext}
                disabled={
                  (step === 1 && !preferences.identityRole) ||
                  (step === 2 && !preferences.intent) ||
                  (step === 3 && !preferences.workspaceType)
                }
                className={`px-6 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                  (step === 1 && !preferences.identityRole) ||
                  (step === 2 && !preferences.intent) ||
                  (step === 3 && !preferences.workspaceType)
                    ? 'bg-primary-700/30 text-primary-400 cursor-not-allowed'
                    : 'bg-primary-500 hover:bg-primary-400 text-white'
                }`}
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleComplete}
                disabled={isSubmitting}
                className="px-6 py-2 bg-gradient-to-r from-primary-500 to-accent-purple rounded-lg text-sm font-medium text-white hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Get Started
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
