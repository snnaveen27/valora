/**
 * FamilyTimeline - Decision timeline for Family Hub
 * 
 * Features:
 * - Vertical timeline visualization
 * - Event type icons and colors
 * - Event details display
 * - Filter by event type
 * - Responsive layout
 * 
 * Props:
 * @param {string} sessionId - Current session ID
 */

import { useState, useEffect } from 'react';
import {
  Clock,
  Users,
  Heart,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  Building2,
  Filter,
  ChevronDown,
  Loader2,
  AlertCircle,
  UserPlus,
  Settings,
  Star,
  Eye,
  XCircle,
  CheckCircle,
  MessageCircle,
} from 'lucide-react';

import { getTimeline } from '../../services/familyApi';

// Event type configurations
const EVENT_TYPES = [
  { 
    id: 'session_created', 
    label: 'Session Created', 
    icon: Building2, 
    color: 'bg-purple-500',
    textColor: 'text-purple-400',
    borderColor: 'border-purple-500/30',
  },
  { 
    id: 'member_joined', 
    label: 'Member Joined', 
    icon: UserPlus, 
    color: 'bg-blue-500',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
  },
  { 
    id: 'member_left', 
    label: 'Member Left', 
    icon: Users, 
    color: 'bg-gray-500',
    textColor: 'text-gray-400',
    borderColor: 'border-gray-500/30',
  },
  { 
    id: 'property_added', 
    label: 'Property Added', 
    icon: Heart, 
    color: 'bg-pink-500',
    textColor: 'text-pink-400',
    borderColor: 'border-pink-500/30',
  },
  { 
    id: 'property_removed', 
    label: 'Property Removed', 
    icon: XCircle, 
    color: 'bg-red-500',
    textColor: 'text-red-400',
    borderColor: 'border-red-500/30',
  },
  { 
    id: 'property_status_changed', 
    label: 'Status Changed', 
    icon: Star, 
    color: 'bg-yellow-500',
    textColor: 'text-yellow-400',
    borderColor: 'border-yellow-500/30',
  },
  { 
    id: 'vote_cast', 
    label: 'Vote Cast', 
    icon: ThumbsUp, 
    color: 'bg-green-500',
    textColor: 'text-green-400',
    borderColor: 'border-green-500/30',
  },
  { 
    id: 'comment_added', 
    label: 'Comment Added', 
    icon: MessageCircle, 
    color: 'bg-cyan-500',
    textColor: 'text-cyan-400',
    borderColor: 'border-cyan-500/30',
  },
  { 
    id: 'settings_changed', 
    label: 'Settings Updated', 
    icon: Settings, 
    color: 'bg-orange-500',
    textColor: 'text-orange-400',
    borderColor: 'border-orange-500/30',
  },
];

// Get event type config
const getEventTypeConfig = (typeId) => {
  return EVENT_TYPES.find(t => t.id === typeId) || {
    id: typeId,
    label: typeId?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    icon: Clock,
    color: 'bg-slate-500',
    textColor: 'text-slate-400',
    borderColor: 'border-slate-500/30',
  };
};

export default function FamilyTimeline({ sessionId }) {
  // State
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Filter state
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);

  // Load timeline on mount
  useEffect(() => {
    if (sessionId) {
      loadTimeline();
    }
  }, [sessionId]);

  // Reload when filters change
  useEffect(() => {
    if (sessionId) {
      loadTimeline();
    }
  }, [selectedTypes]);

  /**
   * Load timeline events from API
   */
  const loadTimeline = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = {};
      if (selectedTypes.length === 1) {
        params.event_type = selectedTypes[0];
      }
      
      const data = await getTimeline(sessionId, params);
      setEvents(data || []);
    } catch (err) {
      console.error('[FamilyTimeline] Failed to load timeline:', err);
      setError('Failed to load timeline');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Toggle event type filter
   */
  const toggleEventTypeFilter = (typeId) => {
    setSelectedTypes(prev => {
      if (prev.includes(typeId)) {
        return prev.filter(t => t !== typeId);
      }
      return [...prev, typeId];
    });
  };

  /**
   * Clear all filters
   */
  const clearFilters = () => {
    setSelectedTypes([]);
  };

  /**
   * Format date for display
   */
  const formatEventDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  /**
   * Format full date for tooltip
   */
  const formatFullDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  /**
   * Group events by date
   */
  const groupEventsByDate = (events) => {
    const groups = {};
    
    events.forEach(event => {
      const date = new Date(event.created_at);
      const dateKey = date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(event);
    });
    
    return groups;
  };

  /**
   * Render event content based on type
   */
  const renderEventContent = (event) => {
    const data = event.event_data || {};
    
    switch (event.event_type) {
      case 'session_created':
        return (
          <div>
            <p className="text-white font-medium">Family session created</p>
            {data.family_name && (
              <p className="text-sm text-slate-400 mt-1">"{data.family_name}"</p>
            )}
          </div>
        );
        
      case 'member_joined':
        return (
          <div>
            <p className="text-white font-medium">
              {data.member_name || 'A family member'} joined
            </p>
            {data.role && (
              <p className="text-sm text-slate-400 mt-1">as {data.role}</p>
            )}
          </div>
        );
        
      case 'member_left':
        return (
          <div>
            <p className="text-white font-medium">
              {data.member_name || 'A family member'} left the session
            </p>
          </div>
        );
        
      case 'property_added':
        return (
          <div>
            <p className="text-white font-medium">
              {data.added_by_name || 'Someone'} added a property
            </p>
            {data.property_title && (
              <p className="text-sm text-slate-400 mt-1">"{data.property_title}"</p>
            )}
            {data.locality && (
              <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                <Eye className="w-3 h-3" />
                {data.locality}
              </p>
            )}
          </div>
        );
        
      case 'property_removed':
        return (
          <div>
            <p className="text-white font-medium">
              {data.removed_by_name || 'Someone'} removed a property
            </p>
            {data.property_title && (
              <p className="text-sm text-slate-400 mt-1">"{data.property_title}"</p>
            )}
          </div>
        );
        
      case 'property_status_changed':
        return (
          <div>
            <p className="text-white font-medium">Property status updated</p>
            {data.property_title && (
              <p className="text-sm text-slate-400 mt-1">"{data.property_title}"</p>
            )}
            {data.old_status && data.new_status && (
              <p className="text-xs text-slate-500 mt-1">
                {data.old_status} → {data.new_status}
              </p>
            )}
          </div>
        );
        
      case 'vote_cast':
        return (
          <div>
            <p className="text-white font-medium">
              {data.voter_name || 'Someone'} voted
            </p>
            {data.property_title && (
              <p className="text-sm text-slate-400 mt-1">on "{data.property_title}"</p>
            )}
            <div className="flex items-center gap-2 mt-2">
              {data.vote === 'up' && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full text-xs">
                  <ThumbsUp className="w-3 h-3" /> Like
                </span>
              )}
              {data.vote === 'down' && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full text-xs">
                  <ThumbsDown className="w-3 h-3" /> Dislike
                </span>
              )}
              {data.vote === 'maybe' && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full text-xs">
                  <HelpCircle className="w-3 h-3" /> Maybe
                </span>
              )}
            </div>
          </div>
        );
        
      case 'comment_added':
        return (
          <div>
            <p className="text-white font-medium">
              {data.author_name || 'Someone'} commented
            </p>
            {data.comment && (
              <p className="text-sm text-slate-400 mt-1 italic">"{data.comment}"</p>
            )}
          </div>
        );
        
      case 'settings_changed':
        return (
          <div>
            <p className="text-white font-medium">Session settings updated</p>
            {data.changes && (
              <p className="text-sm text-slate-400 mt-1">
                {Object.keys(data.changes).join(', ')}
              </p>
            )}
          </div>
        );
        
      default:
        return (
          <div>
            <p className="text-white font-medium">{event.event_type}</p>
          </div>
        );
    }
  };

  // Filter events client-side if multiple types selected
  const filteredEvents = selectedTypes.length > 0
    ? events.filter(e => selectedTypes.includes(e.event_type))
    : events;

  // Group events by date
  const groupedEvents = groupEventsByDate(filteredEvents);

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">Activity Timeline</h3>
          <span className="px-2 py-0.5 bg-slate-700/50 rounded-full text-sm text-slate-400">
            {filteredEvents.length} events
          </span>
        </div>
        
        {/* Filter Button */}
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowFilterDropdown(!showFilterDropdown);
            }}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              selectedTypes.length > 0
                ? 'bg-purple-500/20 text-purple-400'
                : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <Filter className="w-4 h-4" />
            <span className="hidden sm:inline text-sm">
              {selectedTypes.length > 0 ? `${selectedTypes.length} filters` : 'Filter'}
            </span>
            <ChevronDown className="w-3 h-3" />
          </button>
          
          {showFilterDropdown && (
            <div 
              className="absolute right-0 top-full mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10 min-w-[200px]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-2 border-b border-slate-700">
                <button
                  onClick={clearFilters}
                  className="w-full text-left text-sm text-slate-400 hover:text-white px-2 py-1"
                >
                  Clear all filters
                </button>
              </div>
              <div className="max-h-64 overflow-y-auto p-2">
                {EVENT_TYPES.map(type => (
                  <label
                    key={type.id}
                    className="flex items-center gap-2 px-2 py-2 hover:bg-slate-700/50 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(type.id)}
                      onChange={() => toggleEventTypeFilter(type.id)}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-purple-500 focus:ring-purple-500/50"
                    />
                    <type.icon className={`w-4 h-4 ${type.textColor}`} />
                    <span className="text-sm text-slate-300">{type.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredEvents.length === 0 && (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h4 className="text-lg font-medium text-slate-400 mb-2">
            {selectedTypes.length > 0 ? 'No Matching Events' : 'No Activity Yet'}
          </h4>
          <p className="text-sm text-slate-500">
            {selectedTypes.length > 0
              ? 'Try adjusting your filters'
              : 'Activity will appear here as your family collaborates'}
          </p>
        </div>
      )}

      {/* Timeline */}
      {!isLoading && filteredEvents.length > 0 && (
        <div className="relative">
          {/* Timeline Line */}
          <div className="absolute left-4 sm:left-6 top-0 bottom-0 w-0.5 bg-slate-700/50" />
          
          {/* Events by Date Group */}
          {Object.entries(groupedEvents).map(([dateKey, dateEvents]) => (
            <div key={dateKey} className="mb-8">
              {/* Date Header */}
              <div className="relative flex items-center gap-3 mb-4 pl-10 sm:pl-14">
                <div className="absolute left-2 sm:left-4 w-4 h-4 bg-slate-700 rounded-full border-2 border-slate-600" />
                <h4 className="text-sm font-medium text-slate-400">{dateKey}</h4>
              </div>
              
              {/* Events */}
              <div className="space-y-4">
                {dateEvents.map((event, index) => {
                  const config = getEventTypeConfig(event.event_type);
                  
                  return (
                    <div
                      key={event.id || index}
                      className="relative pl-10 sm:pl-14"
                    >
                      {/* Event Icon */}
                      <div className={`absolute left-2 sm:left-4 w-4 h-4 ${config.color} rounded-full flex items-center justify-center`}>
                        <config.icon className="w-2 h-2 text-white" />
                      </div>
                      
                      {/* Event Card */}
                      <div 
                        className={`bg-slate-800/50 rounded-lg border ${config.borderColor} p-4 hover:bg-slate-800/70 transition-colors`}
                        title={formatFullDate(event.created_at)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            {renderEventContent(event)}
                          </div>
                          
                          {/* Timestamp */}
                          <div className="flex items-center gap-1 text-xs text-slate-500 ml-4">
                            <Clock className="w-3 h-3" />
                            <span>{formatEventDate(event.created_at)}</span>
                          </div>
                        </div>
                        
                        {/* User Info */}
                        {event.user_id && (
                          <div className="mt-2 pt-2 border-t border-slate-700/30">
                            <p className="text-xs text-slate-500">
                              by {event.user_name || 'Family member'}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
