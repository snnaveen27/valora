/**
 * FamilyHub - Main container component for Community Pulse Phase 1
 * 
 * Features:
 * - Tab-based navigation (Sessions, Watchlist, Voting, Timeline)
 * - Session selector/creator
 * - Summary statistics display
 * - Responsive layout for mobile/desktop
 * 
 * Props:
 * @param {boolean} isOpen - Whether the hub modal/panel is open
 * @param {function} onClose - Callback to close the hub
 * @param {string} [initialTab] - Initial tab to display (sessions, watchlist, voting, timeline)
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Heart,
  ThumbsUp,
  Clock,
  Plus,
  ChevronDown,
  Settings,
  LogOut,
  Home,
  Building2,
  TrendingUp,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  UserPlus,
  BarChart3,
} from 'lucide-react';

import { 
  getSessions, 
  getSession, 
  getStatistics,
  createSession,
  deleteSession,
} from '../../services/familyApi';

import FamilySessionCreate from './FamilySessionCreate';
import FamilyInviteModal from './FamilyInviteModal';
import FamilyWatchlist from './FamilyWatchlist';
import FamilyVotingPanel from './FamilyVotingPanel';
import FamilyTimeline from './FamilyTimeline';

// Tab configuration
const TABS = [
  { id: 'sessions', label: 'Sessions', icon: Users },
  { id: 'watchlist', label: 'Watchlist', icon: Heart },
  { id: 'voting', label: 'Voting', icon: ThumbsUp },
  { id: 'timeline', label: 'Timeline', icon: Clock },
];

// Status badge colors
const STATUS_COLORS = {
  active: 'bg-green-500/20 text-green-400 border-green-500/30',
  archived: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

export default function FamilyHub({ isOpen, onClose, initialTab = 'sessions' }) {
  // State management
  const [activeTab, setActiveTab] = useState(initialTab);
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Modal states
  const [showCreateSession, setShowCreateSession] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showSessionDropdown, setShowSessionDropdown] = useState(false);

  // Load sessions on mount
  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen]);

  // Load statistics when session changes
  useEffect(() => {
    if (currentSession) {
      loadStatistics();
    }
  }, [currentSession]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setShowSessionDropdown(false);
    if (showSessionDropdown) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showSessionDropdown]);

  /**
   * Load all sessions for the current user
   */
  const loadSessions = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await getSessions({ status: 'active' });
      setSessions(data || []);
      
      // Auto-select first session if available and none selected
      if (data && data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (err) {
      console.error('[FamilyHub] Failed to load sessions:', err);
      setError('Failed to load sessions. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Load statistics for the current session
   */
  const loadStatistics = async () => {
    if (!currentSession) return;
    
    try {
      const stats = await getStatistics(currentSession.id);
      setStatistics(stats);
    } catch (err) {
      console.error('[FamilyHub] Failed to load statistics:', err);
    }
  };

  /**
   * Handle session creation
   */
  const handleSessionCreated = async (newSession) => {
    setSessions(prev => [newSession, ...prev]);
    setCurrentSession(newSession);
    setShowCreateSession(false);
    setActiveTab('watchlist');
  };

  /**
   * Handle session selection
   */
  const handleSessionSelect = (session) => {
    setCurrentSession(session);
    setShowSessionDropdown(false);
  };

  /**
   * Handle session archive
   */
  const handleArchiveSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(sessions.find(s => s.id !== sessionId) || null);
      }
    } catch (err) {
      console.error('[FamilyHub] Failed to archive session:', err);
      setError('Failed to archive session.');
    }
  };

  /**
   * Format budget for display
   */
  const formatBudget = (min, max) => {
    const formatNum = (n) => {
      if (n >= 10000000) return `₹${(n / 10000000).toFixed(1)}Cr`;
      if (n >= 100000) return `₹${(n / 100000).toFixed(0)}L`;
      return `₹${n?.toLocaleString()}`;
    };
    
    if (min && max) return `${formatNum(min)} - ${formatNum(max)}`;
    if (min) return `From ${formatNum(min)}`;
    if (max) return `Up to ${formatNum(max)}`;
    return 'Budget not set';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-6xl max-h-[90vh] bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Users className="w-6 h-6 text-purple-400" />
              <h2 className="text-xl font-semibold text-white">Family Hub</h2>
            </div>
            
            {/* Session Selector */}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowSessionDropdown(!showSessionDropdown);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg border border-slate-600/50 transition-colors"
              >
                {currentSession ? (
                  <>
                    <span className="text-white font-medium">{currentSession.family_name}</span>
                    <span className={`px-2 py-0.5 text-xs rounded-full border ${STATUS_COLORS[currentSession.status] || STATUS_COLORS.active}`}>
                      {currentSession.status}
                    </span>
                  </>
                ) : (
                  <span className="text-slate-400">Select a session</span>
                )}
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showSessionDropdown ? 'rotate-180' : ''}`} />
              </button>
              
              {/* Session Dropdown */}
              {showSessionDropdown && (
                <div className="absolute top-full left-0 mt-2 w-72 bg-slate-800 rounded-lg border border-slate-700 shadow-xl z-10 overflow-hidden">
                  <div className="max-h-64 overflow-y-auto">
                    {sessions.length === 0 ? (
                      <div className="px-4 py-3 text-slate-400 text-center">
                        No sessions yet. Create one to get started!
                      </div>
                    ) : (
                      sessions.map(session => (
                        <button
                          key={session.id}
                          onClick={() => handleSessionSelect(session)}
                          className={`w-full px-4 py-3 text-left hover:bg-slate-700/50 transition-colors ${
                            currentSession?.id === session.id ? 'bg-purple-500/20' : ''
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-white">{session.family_name}</span>
                            <span className={`px-2 py-0.5 text-xs rounded-full border ${STATUS_COLORS[session.status] || STATUS_COLORS.active}`}>
                              {session.status}
                            </span>
                          </div>
                          {session.target_locality && (
                            <p className="text-sm text-slate-400 mt-1">{session.target_locality}</p>
                          )}
                        </button>
                      ))
                    )}
                  </div>
                  
                  {/* Create New Session Button */}
                  <div className="border-t border-slate-700">
                    <button
                      onClick={() => {
                        setShowCreateSession(true);
                        setShowSessionDropdown(false);
                      }}
                      className="w-full px-4 py-3 flex items-center gap-2 text-purple-400 hover:bg-purple-500/10 transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Create New Session</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Header Actions */}
          <div className="flex items-center gap-2">
            {currentSession && (
              <button
                onClick={() => setShowInviteModal(true)}
                className="flex items-center gap-2 px-3 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                <span className="hidden sm:inline">Invite</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
            >
              <XCircle className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </div>

        {/* Statistics Bar */}
        {currentSession && statistics && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 px-6 py-4 bg-slate-800/30 border-b border-slate-700/50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Users className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{statistics.member_count || 0}</p>
                <p className="text-xs text-slate-400">Members</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-pink-500/20 rounded-lg">
                <Heart className="w-5 h-5 text-pink-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{statistics.watchlist?.total || 0}</p>
                <p className="text-xs text-slate-400">Properties</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <ThumbsUp className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{statistics.votes?.total || 0}</p>
                <p className="text-xs text-slate-400">Votes</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <BarChart3 className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{statistics.watchlist?.shortlisted || 0}</p>
                <p className="text-xs text-slate-400">Shortlisted</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-700/50 bg-slate-800/30">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 transition-colors relative ${
                activeTab === tab.id
                  ? 'text-purple-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/30'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span className="font-medium">{tab.label}</span>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500" />
              )}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="h-[calc(90vh-280px)] min-h-[400px] overflow-y-auto">
          {/* Error Display */}
          {error && (
            <div className="mx-6 mt-4 p-4 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <p className="text-red-400">{error}</p>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-400 hover:text-red-300"
              >
                <XCircle className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            </div>
          )}

          {/* No Session State */}
          {!isLoading && !currentSession && (
            <div className="flex flex-col items-center justify-center h-64 text-center px-6">
              <Users className="w-16 h-16 text-slate-600 mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No Session Selected</h3>
              <p className="text-slate-400 mb-6 max-w-md">
                Create a family session to start collaborating on property decisions with your family members.
              </p>
              <button
                onClick={() => setShowCreateSession(true)}
                className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
              >
                <Plus className="w-5 h-5" />
                <span>Create Family Session</span>
              </button>
            </div>
          )}

          {/* Tab Content */}
          {!isLoading && currentSession && (
            <>
              {activeTab === 'sessions' && (
                <div className="p-6">
                  <SessionDetails
                    session={currentSession}
                    onArchive={handleArchiveSession}
                    formatBudget={formatBudget}
                  />
                </div>
              )}
              
              {activeTab === 'watchlist' && (
                <FamilyWatchlist
                  sessionId={currentSession.id}
                  onUpdate={loadStatistics}
                />
              )}
              
              {activeTab === 'voting' && (
                <FamilyVotingPanel
                  sessionId={currentSession.id}
                  watchlist={[]} // Will be loaded internally
                />
              )}
              
              {activeTab === 'timeline' && (
                <FamilyTimeline
                  sessionId={currentSession.id}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Create Session Modal */}
      {showCreateSession && (
        <FamilySessionCreate
          isOpen={showCreateSession}
          onClose={() => setShowCreateSession(false)}
          onCreated={handleSessionCreated}
        />
      )}

      {/* Invite Modal */}
      {showInviteModal && currentSession && (
        <FamilyInviteModal
          isOpen={showInviteModal}
          onClose={() => setShowInviteModal(false)}
          sessionId={currentSession.id}
          sessionName={currentSession.family_name}
        />
      )}
    </div>
  );
}

/**
 * Session Details Component
 */
function SessionDetails({ session, onArchive, formatBudget }) {
  return (
    <div className="space-y-6">
      {/* Session Info Card */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-semibold text-white">{session.family_name}</h3>
            {session.description && (
              <p className="text-slate-400 mt-1">{session.description}</p>
            )}
          </div>
          <span className={`px-3 py-1 text-sm rounded-full border ${STATUS_COLORS[session.status] || STATUS_COLORS.active}`}>
            {session.status}
          </span>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {session.target_locality && (
            <div className="flex items-center gap-2">
              <Home className="w-4 h-4 text-slate-400" />
              <span className="text-slate-300">{session.target_locality}</span>
            </div>
          )}
          
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-slate-400" />
            <span className="text-slate-300">{formatBudget(session.budget_min, session.budget_max)}</span>
          </div>
          
          {session.property_types && session.property_types.length > 0 && (
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-slate-400" />
              <span className="text-slate-300">{session.property_types.join(', ')}</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => onArchive(session.id)}
          className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Archive Session</span>
        </button>
      </div>
    </div>
  );
}
