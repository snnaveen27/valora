/**
 * LanguageContext - App-wide language state management
 * 
 * Provides language selection and translation function to all components
 * Persists language choice to localStorage
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { t as translate, LANGUAGES, getAvailableLanguages } from '../i18n/translations'

// Create the context
const LanguageContext = createContext(null)

// Storage key for persisting language preference
const LANGUAGE_STORAGE_KEY = 'valora_language'

/**
 * LanguageProvider - Wraps the app to provide language state
 */
export function LanguageProvider({ children }) {
  // Initialize language from localStorage or default to 'en'
  const [language, setLanguageState] = useState(() => {
    const saved = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    // Validate that the saved language is supported
    if (saved && LANGUAGES[saved]) {
      return saved
    }
    return 'en'
  })

  // Persist language changes to localStorage
  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  }, [language])

  // Set language with validation
  const setLanguage = useCallback((newLang) => {
    if (LANGUAGES[newLang]) {
      setLanguageState(newLang)
    } else {
      console.warn(`Language "${newLang}" is not supported. Falling back to English.`)
      setLanguageState('en')
    }
  }, [])

  // Translation function bound to current language
  const t = useCallback((key) => {
    return translate(key, language)
  }, [language])

  // Get language info (name, native name, flag, direction)
  const languageInfo = LANGUAGES[language] || LANGUAGES.en

  // Get all available languages for the selector
  const availableLanguages = getAvailableLanguages()

  // Context value
  const value = {
    language,
    setLanguage,
    t,
    languageInfo,
    availableLanguages,
    // Helper to check if current language is RTL
    isRTL: languageInfo.dir === 'rtl',
  }

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

/**
 * useLanguage - Hook to access language context
 * 
 * @returns {Object} { language, setLanguage, t, languageInfo, availableLanguages, isRTL }
 * 
 * @example
 * const { t, language, setLanguage } = useLanguage()
 * 
 * // Get translated string
 * const buttonText = t('newChat') // Returns "New chat" (en) or "नई चैट" (hi)
 * 
 * // Change language
 * setLanguage('hi')
 */
export function useLanguage() {
  const context = useContext(LanguageContext)
  
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  
  return context
}

/**
 * useTranslation - Alternative hook name for compatibility
 * Same as useLanguage but returns only translation-related values
 */
export function useTranslation() {
  const { t, language, languageInfo, availableLanguages } = useLanguage()
  return { t, language, languageInfo, availableLanguages }
}

// Export the context for advanced use cases
export default LanguageContext
