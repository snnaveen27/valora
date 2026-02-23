/**
 * ChatSidebar - Session history sidebar with Open WebUI-style design
 */

import { useState } from 'react'
import { MessageSquarePlus, Trash2, Edit3, Check, X, Download, MoreHorizontal, Clock, Search, Trash } from 'lucide-react'
import { useLanguage } from '../../contexts/LanguageContext'

export default function ChatSidebar({ 
  sessions, 
  currentSessionId, 
  onSelectSession, 
  onNewChat, 
  onDeleteSession, 
  onDeleteAllSessions,
  onRenameSession,
  onExportSession,
  isOpen,
  onClose
}) {
  const { t } = useLanguage()
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [menuOpenId, setMenuOpenId] = useState(null)
  
  const filteredSessions = sessions.filter(s => 
    s.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.messages?.some(m => m.content?.toLowerCase().includes(searchQuery.toLowerCase()))
  )
  
  const handleStartEdit = (session) => {
    setEditingId(session.id)
    setEditTitle(session.title)
    setMenuOpenId(null)
  }
  
  const handleSaveEdit = (sessionId) => {
    if (editTitle.trim()) {
      onRenameSession(sessionId, editTitle.trim())
    }
    setEditingId(null)
    setEditTitle('')
  }
  
  const handleCancelEdit = () => {
    setEditingId(null)
    setEditTitle('')
  }
  
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now - date
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return t('today')
    if (diffDays === 1) return t('yesterday')
    if (diffDays < 7) return `${diffDays} ${t('daysAgo')}`
    return date.toLocaleDateString()
  }
  
  // Group sessions by date
  const groupedSessions = filteredSessions.reduce((groups, session) => {
    const dateLabel = formatDate(session.updatedAt || session.createdAt)
    if (!groups[dateLabel]) groups[dateLabel] = []
    groups[dateLabel].push(session)
    return groups
  }, {})
  
  return (
    <div className={`${isOpen ? 'w-72' : 'w-0'} transition-all duration-300 overflow-hidden bg-surface-primary/95 border-r border-primary-700/30 flex flex-col h-full backdrop-blur-sm`}>
      {/* Header */}
      <div className="p-3 border-b border-primary-700/30">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-primary-600 to-accent-purple hover:from-primary-500 hover:to-accent-purple/90 text-white rounded-xl font-medium text-sm transition-all shadow-lg shadow-primary-900/30"
        >
          <MessageSquarePlus className="w-4 h-4" />
          {t('newChat')}
        </button>
        
        {/* Delete all chats button */}
        {sessions.length > 0 && (
          <button
            onClick={() => {
              if (confirm(t('deleteAllConfirm'))) {
                onDeleteAllSessions?.()
              }
            }}
            className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg text-xs font-medium transition-all border border-red-500/30"
          >
            <Trash className="w-3.5 h-3.5" />
            {t('deleteAllChats')}
          </button>
        )}
      </div>
      
      {/* Search */}
      <div className="p-3 border-b border-primary-700/30">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary-400/50" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('searchChats')}
            className="w-full bg-dark-800/50 border border-primary-700/50 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-primary-400/50 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/30"
          />
        </div>
      </div>
      
      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {Object.entries(groupedSessions).map(([dateLabel, dateSessions]) => (
          <div key={dateLabel}>
            <div className="px-2 py-1 text-xs text-primary-400/60 font-medium flex items-center gap-1.5">
              <Clock className="w-3 h-3" />
              {dateLabel}
            </div>
            <div className="space-y-1">
              {dateSessions.map(session => (
                <div
                  key={session.id}
                  className={`relative group rounded-lg transition-all ${
                    currentSessionId === session.id 
                      ? 'bg-primary-600/20 border border-primary-500/40' 
                      : 'hover:bg-primary-700/20 border border-transparent'
                  }`}
                >
                  {editingId === session.id ? (
                    <div className="flex items-center gap-1 p-2">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveEdit(session.id)
                          if (e.key === 'Escape') handleCancelEdit()
                        }}
                        className="flex-1 bg-dark-700 border border-primary-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-primary-500"
                        autoFocus
                      />
                      <button
                        onClick={() => handleSaveEdit(session.id)}
                        className="p-1 text-accent-purple hover:text-accent-fuchsia"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="p-1 text-primary-400 hover:text-primary-300"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        onSelectSession(session.id)
                      }}
                      className="w-full text-left p-2 pr-8"
                    >
                      <div className="text-sm text-white truncate font-medium">
                        {session.title || t('newChat')}
                      </div>
                      <div className="text-xs text-primary-400/50 truncate mt-0.5">
                        {session.messages?.length || 0} {t('messages')}
                      </div>
                    </button>
                  )}
                  
                  {/* Menu button */}
                  {editingId !== session.id && (
                    <div className="absolute right-1 top-1/2 -translate-y-1/2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setMenuOpenId(menuOpenId === session.id ? null : session.id)
                        }}
                        className="p-1.5 text-accent-purple hover:text-accent-fuchsia opacity-0 group-hover:opacity-100 transition-opacity rounded hover:bg-accent-purple/30"
                      >
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                      
                      {/* Dropdown menu */}
                      {menuOpenId === session.id && (
                        <div className="absolute right-0 top-full mt-1 bg-surface-secondary border border-accent-purple/50 rounded-lg shadow-xl shadow-accent-purple/20 z-50 py-1 min-w-[140px]">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleStartEdit(session)
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-accent-purple hover:bg-accent-purple/30"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            {t('rename')}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              onExportSession(session)
                              setMenuOpenId(null)
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-accent-purple hover:bg-accent-purple/30"
                          >
                            <Download className="w-3.5 h-3.5" />
                            {t('export')}
                          </button>
                          <div className="border-t border-accent-purple/50 my-1" />
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              onDeleteSession(session.id)
                              setMenuOpenId(null)
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            {t('delete')}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        
        {filteredSessions.length === 0 && (
          <div className="text-center py-8 text-primary-400/50 text-sm">
            {searchQuery ? t('noMatchingChats') : t('noChats')}
          </div>
        )}
      </div>
    </div>
  )
}
