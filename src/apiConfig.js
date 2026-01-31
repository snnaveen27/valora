/**
 * Centralized API configuration for Valora AI
 * Handles switching between local development and production environments
 */

const getApiUrl = () => {
  // Check if explicit URL is provided in environment
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // Auto-detect based on hostname
  if (typeof window !== 'undefined') {
    const isLocal = window.location.hostname === 'localhost' || 
                    window.location.hostname === '127.0.0.1';
    
    if (isLocal) {
      return 'http://localhost:8000';
    }
  }

  // Default production path (proxied via Nginx)
  return '/valora/api';
};

export const API_URL = getApiUrl();
export default API_URL;
