/**
 * Family Hub API Service
 * Handles all API calls for the Community Pulse Family Hub feature.
 * 
 * Endpoints:
 *   Session Management:
 *     POST   /api/family/session                    - Create a new family session
 *     GET    /api/family/sessions                   - Get all sessions for current user
 *     GET    /api/family/session/{session_id}       - Get specific session details
 *     PUT    /api/family/session/{session_id}       - Update session settings
 *     DELETE /api/family/session/{session_id}       - Archive/delete session
 *   
 *   Member Management:
 *     POST   /api/family/session/{session_id}/invite      - Invite a family member
 *     GET    /api/family/session/{session_id}/members     - Get all members
 *     PUT    /api/family/session/{session_id}/member/{member_id} - Update member role
 *     DELETE /api/family/session/{session_id}/member/{member_id} - Remove member
 *     POST   /api/family/session/{session_id}/join        - Accept invitation
 *   
 *   Watchlist Management:
 *     POST   /api/family/session/{session_id}/watchlist   - Add property to watchlist
 *     GET    /api/family/session/{session_id}/watchlist   - Get watchlist
 *     PUT    /api/family/session/{session_id}/watchlist/{item_id} - Update watchlist item
 *     DELETE /api/family/session/{session_id}/watchlist/{item_id} - Remove from watchlist
 *   
 *   Voting System:
 *     POST   /api/family/session/{session_id}/vote        - Cast vote on property
 *     GET    /api/family/session/{session_id}/votes       - Get all votes
 *     GET    /api/family/session/{session_id}/votes/{property_id} - Get votes for property
 *     GET    /api/family/session/{session_id}/vote-summary - Get vote summary
 *   
 *   Timeline & Statistics:
 *     GET    /api/family/session/{session_id}/timeline    - Get timeline events
 *     GET    /api/family/session/{session_id}/statistics  - Get session statistics
 *   
 *   Sharing:
 *     POST   /api/family/session/{session_id}/share       - Generate share link/token
 */

import { API_URL } from '../apiConfig';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get authentication headers for API requests
 * @returns {Object} Headers object with auth token if available
 */
const getAuthHeaders = () => {
  const headers = {
    'Content-Type': 'application/json',
  };
  
  // Get token from localStorage if available
  const token = localStorage.getItem('valora_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

/**
 * Make an authenticated API request
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }
  
  return response.json();
};

// ============================================================================
// SESSION MANAGEMENT
// ============================================================================

/**
 * Create a new family session
 * @param {Object} sessionData - Session creation data
 * @param {string} sessionData.family_name - Name for the family session
 * @param {string} [sessionData.description] - Optional description
 * @param {string} [sessionData.target_locality] - Target area/locality
 * @param {number} [sessionData.budget_min] - Minimum budget
 * @param {number} [sessionData.budget_max] - Maximum budget
 * @param {string[]} [sessionData.property_types] - List of preferred property types
 * @param {Object} [sessionData.settings] - Additional settings
 * @returns {Promise<Object>} Created session data
 */
export const createSession = async (sessionData) => {
  return apiRequest('/api/family/session', {
    method: 'POST',
    body: JSON.stringify(sessionData),
  });
};

/**
 * Get all sessions for the current user
 * @param {Object} [params] - Query parameters
 * @param {string} [params.status] - Filter by status (active, archived, completed)
 * @param {number} [params.limit] - Maximum number of sessions to return
 * @param {number} [params.offset] - Offset for pagination
 * @returns {Promise<Object[]>} Array of sessions
 */
export const getSessions = async (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.status) queryParams.append('status', params.status);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset) queryParams.append('offset', params.offset);
  
  const queryString = queryParams.toString();
  return apiRequest(`/api/family/sessions${queryString ? `?${queryString}` : ''}`);
};

/**
 * Get a specific session by ID
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} Session data
 */
export const getSession = async (sessionId) => {
  return apiRequest(`/api/family/session/${sessionId}`);
};

/**
 * Update a session
 * @param {string} sessionId - Session ID
 * @param {Object} updateData - Data to update
 * @returns {Promise<Object>} Updated session data
 */
export const updateSession = async (sessionId, updateData) => {
  return apiRequest(`/api/family/session/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
};

/**
 * Archive/delete a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} Success response
 */
export const deleteSession = async (sessionId) => {
  return apiRequest(`/api/family/session/${sessionId}`, {
    method: 'DELETE',
  });
};

// ============================================================================
// MEMBER MANAGEMENT
// ============================================================================

/**
 * Invite a family member to a session
 * @param {string} sessionId - Session ID
 * @param {Object} inviteData - Invitation data
 * @param {string} inviteData.name - Member's name
 * @param {string} [inviteData.email] - Email for invitation
 * @param {string} [inviteData.phone] - Phone for invitation
 * @param {string} [inviteData.role] - Member role (admin, member, viewer)
 * @returns {Promise<Object>} Created member data with invite token
 */
export const inviteMember = async (sessionId, inviteData) => {
  return apiRequest(`/api/family/session/${sessionId}/invite`, {
    method: 'POST',
    body: JSON.stringify(inviteData),
  });
};

/**
 * Get all members of a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object[]>} Array of members
 */
export const getMembers = async (sessionId) => {
  return apiRequest(`/api/family/session/${sessionId}/members`);
};

/**
 * Update a member's role
 * @param {string} sessionId - Session ID
 * @param {string} memberId - Member ID
 * @param {Object} updateData - Data to update
 * @param {string} [updateData.role] - New role
 * @param {string} [updateData.name] - Updated name
 * @returns {Promise<Object>} Updated member data
 */
export const updateMember = async (sessionId, memberId, updateData) => {
  return apiRequest(`/api/family/session/${sessionId}/member/${memberId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
};

/**
 * Remove a member from a session
 * @param {string} sessionId - Session ID
 * @param {string} memberId - Member ID
 * @returns {Promise<Object>} Success response
 */
export const removeMember = async (sessionId, memberId) => {
  return apiRequest(`/api/family/session/${sessionId}/member/${memberId}`, {
    method: 'DELETE',
  });
};

/**
 * Accept an invitation and join a session
 * @param {string} sessionId - Session ID
 * @param {Object} joinData - Join data
 * @param {string} [joinData.invite_token] - Invitation token
 * @param {string} [joinData.name] - Display name
 * @returns {Promise<Object>} Member data
 */
export const joinSession = async (sessionId, joinData) => {
  return apiRequest(`/api/family/session/${sessionId}/join`, {
    method: 'POST',
    body: JSON.stringify(joinData),
  });
};

// ============================================================================
// WATCHLIST MANAGEMENT
// ============================================================================

/**
 * Add a property to the watchlist
 * @param {string} sessionId - Session ID
 * @param {Object} propertyData - Property data
 * @param {string} [propertyData.property_id] - Property ID (if from database)
 * @param {string} [propertyData.property_title] - Property title
 * @param {string} [propertyData.locality] - Property locality
 * @param {number} [propertyData.latitude] - Property latitude
 * @param {number} [propertyData.longitude] - Property longitude
 * @param {number} [propertyData.price] - Property price
 * @param {string} [propertyData.notes] - Notes about the property
 * @param {string} [propertyData.priority] - Priority level (high, medium, low)
 * @returns {Promise<Object>} Created watchlist item
 */
export const addToWatchlist = async (sessionId, propertyData) => {
  return apiRequest(`/api/family/session/${sessionId}/watchlist`, {
    method: 'POST',
    body: JSON.stringify(propertyData),
  });
};

/**
 * Get the watchlist for a session
 * @param {string} sessionId - Session ID
 * @param {Object} [params] - Query parameters
 * @param {string} [params.status] - Filter by status
 * @param {string} [params.priority] - Filter by priority
 * @returns {Promise<Object[]>} Array of watchlist items
 */
export const getWatchlist = async (sessionId, params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.status) queryParams.append('status', params.status);
  if (params.priority) queryParams.append('priority', params.priority);
  
  const queryString = queryParams.toString();
  return apiRequest(`/api/family/session/${sessionId}/watchlist${queryString ? `?${queryString}` : ''}`);
};

/**
 * Update a watchlist item
 * @param {string} sessionId - Session ID
 * @param {string} itemId - Watchlist item ID
 * @param {Object} updateData - Data to update
 * @param {string} [updateData.notes] - Updated notes
 * @param {string} [updateData.priority] - Updated priority
 * @param {string} [updateData.status] - Updated status
 * @returns {Promise<Object>} Updated watchlist item
 */
export const updateWatchlistItem = async (sessionId, itemId, updateData) => {
  return apiRequest(`/api/family/session/${sessionId}/watchlist/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
};

/**
 * Remove a property from the watchlist
 * @param {string} sessionId - Session ID
 * @param {string} itemId - Watchlist item ID
 * @returns {Promise<Object>} Success response
 */
export const removeFromWatchlist = async (sessionId, itemId) => {
  return apiRequest(`/api/family/session/${sessionId}/watchlist/${itemId}`, {
    method: 'DELETE',
  });
};

// ============================================================================
// VOTING SYSTEM
// ============================================================================

/**
 * Cast a vote on a property
 * @param {string} sessionId - Session ID
 * @param {Object} voteData - Vote data
 * @param {string} voteData.property_id - Property ID
 * @param {string} voteData.vote - Vote value (up, down, maybe)
 * @param {Object} [voteData.aspects] - Aspect-level votes
 * @param {string} [voteData.comment] - Optional comment
 * @returns {Promise<Object>} Created/updated vote
 */
export const castVote = async (sessionId, voteData) => {
  return apiRequest(`/api/family/session/${sessionId}/vote`, {
    method: 'POST',
    body: JSON.stringify(voteData),
  });
};

/**
 * Get all votes for a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object[]>} Array of votes
 */
export const getVotes = async (sessionId) => {
  return apiRequest(`/api/family/session/${sessionId}/votes`);
};

/**
 * Get votes for a specific property
 * @param {string} sessionId - Session ID
 * @param {string} propertyId - Property ID
 * @returns {Promise<Object[]>} Array of votes for the property
 */
export const getPropertyVotes = async (sessionId, propertyId) => {
  return apiRequest(`/api/family/session/${sessionId}/votes/${propertyId}`);
};

/**
 * Get vote summary for a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} Vote summary with counts and aspects
 */
export const getVoteSummary = async (sessionId) => {
  return apiRequest(`/api/family/session/${sessionId}/vote-summary`);
};

// ============================================================================
// TIMELINE & STATISTICS
// ============================================================================

/**
 * Get timeline events for a session
 * @param {string} sessionId - Session ID
 * @param {Object} [params] - Query parameters
 * @param {string} [params.event_type] - Filter by event type
 * @param {number} [params.limit] - Maximum number of events
 * @returns {Promise<Object[]>} Array of timeline events
 */
export const getTimeline = async (sessionId, params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.event_type) queryParams.append('event_type', params.event_type);
  if (params.limit) queryParams.append('limit', params.limit);
  
  const queryString = queryParams.toString();
  return apiRequest(`/api/family/session/${sessionId}/timeline${queryString ? `?${queryString}` : ''}`);
};

/**
 * Get statistics for a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} Session statistics
 */
export const getStatistics = async (sessionId) => {
  return apiRequest(`/api/family/session/${sessionId}/statistics`);
};

// ============================================================================
// SHARING
// ============================================================================

/**
 * Generate a share link for a session
 * @param {string} sessionId - Session ID
 * @param {Object} [shareOptions] - Share options
 * @param {number} [shareOptions.expiry_hours] - Hours until link expires (default: 72)
 * @param {number} [shareOptions.max_uses] - Maximum number of uses
 * @returns {Promise<Object>} Share link data with token and URL
 */
export const generateShareLink = async (sessionId, shareOptions = {}) => {
  return apiRequest(`/api/family/session/${sessionId}/share`, {
    method: 'POST',
    body: JSON.stringify(shareOptions),
  });
};

// ============================================================================
// EXPORT ALL
// ============================================================================

export default {
  // Session Management
  createSession,
  getSessions,
  getSession,
  updateSession,
  deleteSession,
  
  // Member Management
  inviteMember,
  getMembers,
  updateMember,
  removeMember,
  joinSession,
  
  // Watchlist Management
  addToWatchlist,
  getWatchlist,
  updateWatchlistItem,
  removeFromWatchlist,
  
  // Voting System
  castVote,
  getVotes,
  getPropertyVotes,
  getVoteSummary,
  
  // Timeline & Statistics
  getTimeline,
  getStatistics,
  
  // Sharing
  generateShareLink,
};
