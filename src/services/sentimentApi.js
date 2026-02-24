/**
 * Sentiment Dashboard API Service
 * Handles all API calls for the Community Pulse Sentiment Dashboard (Phase 3).
 * 
 * Signal Recording (No credit required):
 *   POST   /api/sentiment/signal                    - Record user interaction signal
 * 
 * Market Sentiment (5 credits):
 *   GET    /api/sentiment/locality/{locality_id}    - Get sentiment for locality
 *   GET    /api/sentiment/city/{city}              - Get sentiment for city
 *   GET    /api/sentiment/investment-score/{locality_id} - Get investment score
 * 
 * Price Analysis:
 *   GET    /api/sentiment/price-momentum/{locality_id}   - Get price momentum
 *   GET    /api/sentiment/price-history/{locality_id}     - Get price history
 * 
 * Market Metrics:
 *   GET    /api/sentiment/rental-yield/{locality_id}     - Get rental yield
 *   GET    /api/sentiment/days-on-market/{locality_id}   - Get average days on market
 * 
 * Trends:
 *   GET    /api/sentiment/trending               - Get trending localities
 *   GET    /api/sentiment/trends/{locality_id}   - Get historical trends (10 credits)
 * 
 * Credit Management:
 *   GET    /api/credits/check                     - Check available credits
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
  
  const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

/**
 * Handle API response
 * @param {Response} response - Fetch response object
 * @returns {Promise<Object>} Parsed JSON response
 */
const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'An error occurred' }));
    
    // Check for credit-related errors
    if (response.status === 402 || error.requires_credits) {
      throw new Error(error.message || 'Insufficient credits');
    }
    
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    
    throw new Error(error.message || `API error: ${response.status}`);
  }
  
  return response.json();
};

/**
 * Build query string for GET requests
 * @param {Object} params - Query parameters
 * @returns {string} Query string
 */
const buildQueryString = (params) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, value);
    }
  });
  return searchParams.toString();
};

// ============================================================================
// SIGNAL RECORDING (No credit required)
// ============================================================================

/**
 * Record user interaction signal
 * @param {string} signalType - Type of signal (property_view, property_save, property_share, analysis_request, search)
 * @param {string} [localityId] - Locality ID (optional)
 * @param {string} [propertyId] - Property ID (optional)
 * @param {Object} [signalData] - Additional signal data
 * @returns {Promise<Object>} Signal recording response
 */
export const recordSignal = async (signalType, localityId, propertyId, signalData = {}) => {
  try {
    const response = await fetch(`${API_URL}/api/sentiment/signal`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        signal_type: signalType,
        locality_id: localityId,
        property_id: propertyId,
        signal_data: signalData,
      }),
    });
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error recording signal:', error);
    throw error;
  }
};

// ============================================================================
// MARKET SENTIMENT (5 credits)
// ============================================================================

/**
 * Get sentiment for a locality
 * @param {string} localityId - Locality ID
 * @param {boolean} [forceRefresh] - Force recalculation
 * @returns {Promise<Object>} Sentiment data for locality
 */
export const getSentiment = async (localityId, forceRefresh = false) => {
  try {
    const queryString = buildQueryString({ force_refresh: forceRefresh });
    const response = await fetch(
      `${API_URL}/api/sentiment/locality/${localityId}${queryString ? `?${queryString}` : ''}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching locality sentiment:', error);
    throw error;
  }
};

/**
 * Get sentiment for a city
 * @param {string} city - City name
 * @returns {Promise<Object>} Sentiment data for city
 */
export const getCitySentiment = async (city) => {
  try {
    const response = await fetch(`${API_URL}/api/sentiment/city/${encodeURIComponent(city)}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching city sentiment:', error);
    throw error;
  }
};

/**
 * Get investment score for a locality
 * @param {string} localityId - Locality ID
 * @returns {Promise<Object>} Investment score data
 */
export const getInvestmentScore = async (localityId) => {
  try {
    const response = await fetch(
      `${API_URL}/api/sentiment/investment-score/${localityId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching investment score:', error);
    throw error;
  }
};

// ============================================================================
// PRICE ANALYSIS
// ============================================================================

/**
 * Get price momentum for a locality
 * @param {string} localityId - Locality ID
 * @param {string} [period] - Time period (1mo, 3mo, 6mo, 1yr)
 * @returns {Promise<Object>} Price momentum data
 */
export const getPriceMomentum = async (localityId, period = '3mo') => {
  try {
    const queryString = buildQueryString({ period });
    const response = await fetch(
      `${API_URL}/api/sentiment/price-momentum/${localityId}${queryString ? `?${queryString}` : ''}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching price momentum:', error);
    throw error;
  }
};

/**
 * Get price history for a locality
 * @param {string} localityId - Locality ID
 * @param {string} [period] - Time period (1mo, 3mo, 6mo, 1yr)
 * @returns {Promise<Object>} Price history data
 */
export const getPriceHistory = async (localityId, period = '1yr') => {
  try {
    const queryString = buildQueryString({ period });
    const response = await fetch(
      `${API_URL}/api/sentiment/price-history/${localityId}${queryString ? `?${queryString}` : ''}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching price history:', error);
    throw error;
  }
};

// ============================================================================
// MARKET METRICS
// ============================================================================

/**
 * Get rental yield for a locality
 * @param {string} localityId - Locality ID
 * @returns {Promise<Object>} Rental yield data
 */
export const getRentalYield = async (localityId) => {
  try {
    const response = await fetch(
      `${API_URL}/api/sentiment/rental-yield/${localityId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching rental yield:', error);
    throw error;
  }
};

/**
 * Get average days on market for a locality
 * @param {string} localityId - Locality ID
 * @returns {Promise<Object>} Days on market data
 */
export const getDaysOnMarket = async (localityId) => {
  try {
    const response = await fetch(
      `${API_URL}/api/sentiment/days-on-market/${localityId}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching days on market:', error);
    throw error;
  }
};

// ============================================================================
// TRENDS
// ============================================================================

/**
 * Get trending localities
 * @param {string} [city] - Filter by city (optional)
 * @param {number} [limit] - Number of results (default: 10)
 * @returns {Promise<Object>} Trending localities data
 */
export const getTrending = async (city, limit = 10) => {
  try {
    const queryString = buildQueryString({ city, limit });
    const response = await fetch(
      `${API_URL}/api/sentiment/trending${queryString ? `?${queryString}` : ''}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching trending localities:', error);
    throw error;
  }
};

/**
 * Get historical trends for a locality (10 credits)
 * @param {string} localityId - Locality ID
 * @param {string} [period] - Time period (3mo, 6mo, 1yr, 2yr)
 * @returns {Promise<Object>} Historical trends data
 */
export const getTrends = async (localityId, period = '1yr') => {
  try {
    const queryString = buildQueryString({ period });
    const response = await fetch(
      `${API_URL}/api/sentiment/trends/${localityId}${queryString ? `?${queryString}` : ''}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error fetching trends:', error);
    throw error;
  }
};

// ============================================================================
// CREDIT MANAGEMENT
// ============================================================================

/**
 * Check available credits
 * @returns {Promise<Object>} Credit balance information
 */
export const checkCredits = async () => {
  try {
    const response = await fetch(`${API_URL}/api/credits/check`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    return handleResponse(response);
  } catch (error) {
    console.error('Error checking credits:', error);
    throw error;
  }
};

// ============================================================================
// COMBINED DATA FETCHERS
// ============================================================================

/**
 * Get all sentiment data for a locality
 * @param {string} localityId - Locality ID
 * @returns {Promise<Object>} Combined sentiment data
 */
export const getFullSentimentData = async (localityId) => {
  try {
    const [sentiment, investmentScore, priceMomentum, rentalYield, daysOnMarket] = await Promise.all([
      getSentiment(localityId).catch(err => ({ error: err.message })),
      getInvestmentScore(localityId).catch(err => ({ error: err.message })),
      getPriceMomentum(localityId).catch(err => ({ error: err.message })),
      getRentalYield(localityId).catch(err => ({ error: err.message })),
      getDaysOnMarket(localityId).catch(err => ({ error: err.message })),
    ]);
    
    return {
      sentiment,
      investmentScore,
      priceMomentum,
      rentalYield,
      daysOnMarket,
      fetchedAt: new Date().toISOString(),
    };
  } catch (error) {
    console.error('Error fetching full sentiment data:', error);
    throw error;
  }
};

/**
 * Get price data with history
 * @param {string} localityId - Locality ID
 * @param {string} period - Time period
 * @returns {Promise<Object>} Price momentum and history
 */
export const getPriceData = async (localityId, period = '1yr') => {
  try {
    const [momentum, history] = await Promise.all([
      getPriceMomentum(localityId, period),
      getPriceHistory(localityId, period),
    ]);
    
    return {
      momentum,
      history,
      fetchedAt: new Date().toISOString(),
    };
  } catch (error) {
    console.error('Error fetching price data:', error);
    throw error;
  }
};

// ============================================================================
// DEFAULT EXPORT
// ============================================================================

export default {
  recordSignal,
  getSentiment,
  getCitySentiment,
  getInvestmentScore,
  getPriceMomentum,
  getPriceHistory,
  getRentalYield,
  getDaysOnMarket,
  getTrending,
  getTrends,
  checkCredits,
  getFullSentimentData,
  getPriceData,
};
