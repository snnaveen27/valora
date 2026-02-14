/**
 * Chat Session Manager - Handles conversation persistence and session management
 * Production-grade conversation history with localStorage persistence
 */

import { getDefaultWelcomeMessage } from './ChatConfig'

const STORAGE_KEY = 'valora_chat_sessions'
const CURRENT_SESSION_KEY = 'valora_current_session'

export function generateSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export function createNewSession(title = null) {
  const id = generateSessionId()
  return {
    id,
    title: title || 'New Chat',
    messages: [getDefaultWelcomeMessage()],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    model: null
  }
}

export function loadSessions() {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    if (!data) return []
    const sessions = JSON.parse(data)
    return Array.isArray(sessions) ? sessions : []
  } catch (e) {
    console.warn('[ChatSessionManager] Failed to load sessions:', e)
    return []
  }
}

export function saveSessions(sessions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.warn('[ChatSessionManager] Failed to save sessions:', e)
  }
}

export function getCurrentSessionId() {
  try {
    return localStorage.getItem(CURRENT_SESSION_KEY) || null
  } catch {
    return null
  }
}

export function setCurrentSessionId(id) {
  try {
    if (id) {
      localStorage.setItem(CURRENT_SESSION_KEY, id)
    } else {
      localStorage.removeItem(CURRENT_SESSION_KEY)
    }
  } catch {}
}

export function saveSession(session) {
  const sessions = loadSessions()
  const idx = sessions.findIndex(s => s.id === session.id)
  
  const updatedSession = {
    ...session,
    updatedAt: new Date().toISOString()
  }
  
  if (idx >= 0) {
    sessions[idx] = updatedSession
  } else {
    sessions.unshift(updatedSession)
  }
  
  saveSessions(sessions)
  return updatedSession
}

export function deleteSession(sessionId) {
  const sessions = loadSessions().filter(s => s.id !== sessionId)
  saveSessions(sessions)
  
  if (getCurrentSessionId() === sessionId) {
    setCurrentSessionId(null)
  }
  
  return sessions
}

export function generateSessionTitle(messages) {
  const userMessages = messages.filter(m => m.role === 'user')
  if (userMessages.length === 0) return 'New Chat'
  
  const firstUserMsg = userMessages[0].content || ''
  const title = firstUserMsg.slice(0, 40).trim()
  return title.length < firstUserMsg.length ? `${title}...` : title || 'New Chat'
}

export function exportSession(session, format = 'json') {
  if (format === 'json') {
    return JSON.stringify(session, null, 2)
  }
  
  if (format === 'markdown') {
    let md = `# ${session.title}\n\n`
    md += `*Created: ${new Date(session.createdAt).toLocaleString()}*\n\n---\n\n`
    
    for (const msg of session.messages) {
      const role = msg.role === 'user' ? '**You**' : '**Valora**'
      md += `${role}:\n\n${msg.content}\n\n---\n\n`
    }
    
    return md
  }
  
  return ''
}
