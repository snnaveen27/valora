/**
 * Review API Service
 * Handles all API calls for the Community Pulse Phase 2: Locality Reviews feature.
 * 
 * Endpoints:
 *   Locality Reviews:
 *     POST   /api/reviews/locality                    - Submit locality review
 *     GET    /api/reviews/locality/{locality_id}    - Get reviews for locality
 *     GET    /api/reviews/locality/{locality_id}/stats - Get review statistics
 *     PUT    /api/reviews/locality/{review_id}      - Update review
 *     DELETE /api/reviews/locality/{review_id}      - Delete review
 * 
 *   Builder Profiles:
 *     POST   /api/reviews/builder                   - Create builder profile (admin)
 *     GET    /api/reviews/builder/{builder_id}      - Get builder profile
 *     GET    /api/reviews/builders                  - Search builders
 *     PUT    /api/reviews/builder/{builder_id}     - Update builder profile
 * 
 *   Builder Reviews:
 *     POST   /api/reviews/builder/{builder_id}/review - Submit builder review
 *     GET    /api/reviews/builder/{builder_id}/reviews - Get builder reviews
 *     PUT    /api/reviews/builder/review/{review_id} - Update review
 *     DELETE /api/reviews/builder/review/{review_id} - Delete review
 * 
 *   Helpful System:
 *     POST   /api/reviews/{review_type}/{review_id}/helpful - Mark helpful
 *     DELETE /api/reviews/{review_type}/{review_id}/helpful - Remove helpful
 * 
 *   RERA Verification:
 *     GET    /api/rera/verify/{rera_id}             - Verify RERA ID
 *     POST   /api/rera/refresh/{rera_id}            - Force refresh RERA data
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
// LOCALITY REVIEWS
// ============================================================================

/**
 * Submit a locality review
 * @param {Object} reviewData - Review data
 * @param {string} reviewData.locality_id - Locality ID
 * @param {string} reviewData.locality_name - Locality name
 * @param {number} reviewData.overall_rating - Overall rating (1-5)
 * @param {number} [reviewData.vastu_rating] - Vastu compliance rating
 * @param {string} [reviewData.vastu_notes] - Vastu notes
 * @param {number} [reviewData.school_rating] - School proximity rating
 * @param {string} [reviewData.school_notes] - School notes
 * @param {Object} [reviewData.religious_proximity] - Religious place distances
 * @param {number} [reviewData.transport_rating] - Transport connectivity rating
 * @param {string} [reviewData.transport_notes] - Transport notes
 * @param {number} [reviewData.safety_rating] - Safety rating
 * @param {string} [reviewData.safety_notes] - Safety notes
 * @param {number} [reviewData.amenities_rating] - Amenities rating
 * @param {string} [reviewData.amenities_notes] - Amenities notes
 * @param {number} [reviewData.water_supply_rating] - Water supply rating
 * @param {number} [reviewData.power_supply_rating] - Power supply rating
 * @param {string[]} [reviewData.pros] - List of pros
 * @param {string[]} [reviewData.cons] - List of cons
 * @param {string} [reviewData.review_text] - Full review text
 * @param {string} [reviewData.verification_type] - Verification type (resident/owner/visitor)
 * @returns {Promise<Object>} Created review data
 */
export const submitLocalityReview = async (reviewData) => {
  return apiRequest('/api/reviews/locality', {
    method: 'POST',
    body: JSON.stringify(reviewData),
  });
};

/**
 * Get reviews for a locality
 * @param {string} localityId - Locality ID
 * @param {Object} [params] - Query parameters
 * @param {number} [params.rating] - Filter by rating
 * @param {string} [params.verification_type] - Filter by verification type
 * @param {string} [params.sort_by] - Sort by (created_at, helpful_count, overall_rating)
 * @param {string} [params.sort_order] - Sort order (asc, desc)
 * @param {number} [params.limit] - Maximum number of reviews
 * @param {number} [params.offset] - Offset for pagination
 * @returns {Promise<Object[]>} Array of locality reviews
 */
export const getLocalityReviews = async (localityId, params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.rating) queryParams.append('rating', params.rating);
  if (params.verification_type) queryParams.append('verification_type', params.verification_type);
  if (params.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params.sort_order) queryParams.append('sort_order', params.sort_order);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset) queryParams.append('offset', params.offset);
  
  const queryString = queryParams.toString();
  return apiRequest(`/api/reviews/locality/${localityId}${queryString ? `?${queryString}` : ''}`);
};

/**
 * Get review statistics for a locality
 * @param {string} localityId - Locality ID
 * @returns {Promise<Object>} Locality review statistics
 */
export const getLocalityStats = async (localityId) => {
  return apiRequest(`/api/reviews/locality/${localityId}/stats`);
};

/**
 * Update a locality review
 * @param {string} reviewId - Review ID
 * @param {Object} updateData - Data to update
 * @returns {Promise<Object>} Updated review data
 */
export const updateLocalityReview = async (reviewId, updateData) => {
  return apiRequest(`/api/reviews/locality/${reviewId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
};

/**
 * Delete a locality review
 * @param {string} reviewId - Review ID
 * @returns {Promise<Object>} Success response
 */
export const deleteLocalityReview = async (reviewId) => {
  return apiRequest(`/api/reviews/locality/${reviewId}`, {
    method: 'DELETE',
  });
};

// ============================================================================
// BUILDER PROFILES
// ============================================================================

/**
 * Create a builder profile (admin only)
 * @param {Object} builderData - Builder profile data
 * @param {string} builderData.name - Builder name
 * @param {string} [builderData.description] - Builder description
 * @param {string} [builderData.logo_url] - URL to builder logo
 * @param {string} [builderData.website] - Builder website
 * @param {number} [builderData.established_year] - Year established
 * @param {string[]} [builderData.cities_operating] - List of cities
 * @param {boolean} [builderData.rera_registered] - RERA registration status
 * @param {string[]} [builderData.rera_ids] - RERA registration IDs
 * @param {string} [builderData.contact_phone] - Contact phone
 * @param {string} [builderData.contact_email] - Contact email
 * @param {string} [builderData.address] - Office address
 * @returns {Promise<Object>} Created builder profile
 */
export const createBuilder = async (builderData) => {
  return apiRequest('/api/reviews/builder', {
    method: 'POST',
    body: JSON.stringify(builderData),
  });
};

/**
 * Get a builder profile by ID
 * @param {string} builderId - Builder ID
 * @returns {Promise<Object>} Builder profile data
 */
export const getBuilder = async (builderId) => {
  return apiRequest(`/api/reviews/builder/${builderId}`);
};

/**
 * Search builders
 * @param {Object} [params] - Search parameters
 * @param {string} [params.query] - Search query
 * @param {string} [params.city] - Filter by city
 * @param {number} [params.limit] - Maximum number of results
 * @param {number} [params.offset] - Offset for pagination
 * @returns {Promise<Object[]>} Array of builder profiles
 */
export const searchBuilders = async (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.query) queryParams.append('query', params.query);
  if (params.city) queryParams.append('city', params.city);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset) queryParams.append('offset', params.offset);
  
  const queryString = queryParams.toString();
  return apiRequest(`/api/reviews/builders${queryString ? `?${queryString}` : ''}`);
};

/**
 * Update a builder profile (admin only)
 * @param {string} builderId - Builder ID
 * @param {Object} updateData - Data to update
 * @returns {Promise<Object>} Updated builder profile
 */
export const updateBuilder = async (builderId, updateData) => {
  return apiRequest(`/api/reviews/builder/${builderId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
};

// ============================================================================
// BUILDER REVIEWS
// ============================================================================

/**
 * Submit a builder review
 * @param {string} builderId - Builder ID
 * @param {Object} reviewData - Review data
 * @param {number} reviewData.overall_rating - Overall rating (1-5)
 * @param {string} [reviewData.project_name] - Project name
 * @param {string} [reviewData.project_location] - Project location
 * @param {number} [reviewData.construction_quality] - Construction quality rating
 * @param {number} [reviewData.timely_delivery] - Timely delivery rating
 * @param {number} [reviewData.after_sales_service] - After-sales service rating
 * @param {number} [reviewData.value_for_money] - Value for money rating
 * @param {number} [reviewData.transparency] - Transparency rating
 * @param {string[]} [reviewData.pros] - List of pros
 * @param {string[]} [reviewData.cons] - List of cons
 * @param {string} [reviewData.review_text] - Full review text
 * @param {boolean} [reviewData.is_verified_buyer] - Verified buyer status
 * @param {string} [reviewData.purchase_date] - Date of purchase
 * @returns {Promise<Object>} Created review data
 */
export const submitBuilderReview = async (builderId, reviewData) => {
  return apiRequest(`/api/reviews/builder/${builderId}/review`, {
    method: 'POST',
    body: JSON.stringify(reviewData),
  });
};

/**
 * Get reviews for a builder
 * @param {string} builderId - Builder ID
 * @param {Object} [params] - Query parameters
 * @param {number} [params.rating] - Filter by rating
 * @param {string} [params.sort_by] - Sort by (created_at, helpful_count, overall_rating)
 * @param {string} [params.sort_order] - Sort order (asc, desc)
 * @param {number} [params.limit] - Maximum number of reviews
 * @param {number} [params.offset] - Offset for pagination
 * @returns {Promise<Object[]>} Array of builder reviews
 */
export const getBuilderReviews = async (builderId, params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.rating) queryParams.append('rating', params.rating);
  if (params.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params.sort_order) queryParams.append('sort_order', params.sort_order);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset) queryParams.append('offset', params.offset);
  
  const queryString = queryParams.toString();
  return apiRequest(`/api/reviews/builder/${builderId}/reviews${queryString ? `?${queryString}` : ''}`);
};

/**
 * Update a builder review
 * @param {string} reviewId - Review ID
 * @param {Object} updateData - Data to update
 * @returns {Promise<Object>} Updated review data
 */
export const updateBuilderReview = async (reviewId, updateData) => {
  return apiRequest(`/api/reviews/builder/review/${reviewId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
};

/**
 * Delete a builder review
 * @param {string} reviewId - Review ID
 * @returns {Promise<Object>} Success response
 */
export const deleteBuilderReview = async (reviewId) => {
  return apiRequest(`/api/reviews/builder/review/${reviewId}`, {
    method: 'DELETE',
  });
};

// ============================================================================
// HELPFUL SYSTEM
// ============================================================================

/**
 * Mark a review as helpful
 * @param {string} reviewType - Type of review (locality, builder)
 * @param {string} reviewId - Review ID
 * @returns {Promise<Object>} Helpful mark data
 */
export const markHelpful = async (reviewType, reviewId) => {
  return apiRequest(`/api/reviews/${reviewType}/${reviewId}/helpful`, {
    method: 'POST',
  });
};

/**
 * Remove helpful mark from a review
 * @param {string} reviewType - Type of review (locality, builder)
 * @param {string} reviewId - Review ID
 * @returns {Promise<Object>} Success response
 */
export const unmarkHelpful = async (reviewType, reviewId) => {
  return apiRequest(`/api/reviews/${reviewType}/${reviewId}/helpful`, {
    method: 'DELETE',
  });
};

// ============================================================================
// RERA VERIFICATION
// ============================================================================

/**
 * Verify a RERA ID
 * @param {string} reraId - RERA ID to verify
 * @returns {Promise<Object>} RERA verification data
 */
export const verifyRera = async (reraId) => {
  return apiRequest(`/api/rera/verify/${reraId}`);
};

/**
 * Force refresh RERA data
 * @param {string} reraId - RERA ID to refresh
 * @returns {Promise<Object>} Updated RERA verification data
 */
export const refreshRera = async (reraId) => {
  return apiRequest(`/api/rera/refresh/${reraId}`, {
    method: 'POST',
  });
};

// ============================================================================
// EXPORT ALL
// ============================================================================

export default {
  // Locality Reviews
  submitLocalityReview,
  getLocalityReviews,
  getLocalityStats,
  updateLocalityReview,
  deleteLocalityReview,
  
  // Builder Profiles
  createBuilder,
  getBuilder,
  searchBuilders,
  updateBuilder,
  
  // Builder Reviews
  submitBuilderReview,
  getBuilderReviews,
  updateBuilderReview,
  deleteBuilderReview,
  
  // Helpful System
  markHelpful,
  unmarkHelpful,
  
  // RERA Verification
  verifyRera,
  refreshRera,
};
