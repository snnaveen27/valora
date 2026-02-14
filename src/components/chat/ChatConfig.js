/**
 * Chat Configuration - Dynamic greetings and messages
 * Configurable via environment variables or runtime config
 */

// Load from environment or use defaults
const getConfig = () => ({
  // Branding
  assistantName: import.meta.env?.VITE_ASSISTANT_NAME || 'Valora',
  assistantEmoji: import.meta.env?.VITE_ASSISTANT_EMOJI || '👋',
  
  // Greeting variants - randomized for variety
  greetings: [
    "Hey there!",
    "Hello!",
    "Hi!",
    "Welcome!",
    "Good to see you!"
  ],
  
  // Location context (could be loaded from user settings)
  location: import.meta.env?.VITE_DEFAULT_LOCATION || 'Bangalore',
  
  // Capabilities list
  capabilities: [
    { emoji: '🏠', title: 'Finding properties', example: '3BHK in Whitefield under 1.5Cr' },
    { emoji: '📍', title: 'Exploring areas', example: 'Tell me about Koramangala' },
    { emoji: '💰', title: 'Investment advice', example: 'Is Hebbal a good investment?' },
    { emoji: '📊', title: 'Market trends', example: 'Price trends in HSR Layout' },
    { emoji: '🔮', title: 'What-if scenarios', example: 'What if metro comes to Sarjapur?' }
  ],
  
  // Closing message
  closingMessage: "Just ask naturally — I understand casual conversation too!"
})

export function getDynamicWelcomeMessage() {
  const config = getConfig()
  
  // Random greeting for variety
  const greeting = config.greetings[Math.floor(Math.random() * config.greetings.length)]
  
  const capabilitiesList = config.capabilities.map(
    cap => `${cap.emoji} **${cap.title}** — "${cap.example}"`
  ).join('\n')
  
  return {
    role: 'assistant',
    content: `${greeting} ${config.assistantEmoji} I'm **${config.assistantName}**, your AI assistant for ${config.location} real estate.

I can help you with:

${capabilitiesList}

${config.closingMessage}`,
    timestamp: new Date().toISOString(),
    isFastResponse: true
  }
}

export function getDynamicWelcomeTitle() {
  const config = getConfig()
  const greeting = config.greetings[Math.floor(Math.random() * config.greetings.length)]
  return `${greeting} ${config.assistantEmoji} I'm ${config.assistantName}`
}

export function getDynamicWelcomeSubtitle() {
  const config = getConfig()
  return `Your AI assistant for ${config.location} real estate. Ask me anything about properties, areas, or investments!`
}

export function getClosingMessage() {
  return getConfig().closingMessage
}

// For compatibility with existing code
export function getDefaultWelcomeMessage() {
  return getDynamicWelcomeMessage()
}
