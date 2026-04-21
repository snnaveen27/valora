/**
 * Centralized API configuration for Valora AI
 * Handles switching between local development and production environments
 */

const getApiUrl = () => {
  // In development (Vite), use relative path to leverage Vite proxy
  if (import.meta.env.DEV) {
    return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
  }
  // Check if explicit URL is provided in environment
  if (import.meta.env.VITE_API_URL) {
    const configuredApiUrl = import.meta.env.VITE_API_URL.replace(/\/$/, '');
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
      const isEnvLocal = /localhost|127\.0\.0\.1/.test(configuredApiUrl);
      if (!isLocalHost && isEnvLocal) {
        // Ignore local API URL when running on a non-local host
      } else {
        return configuredApiUrl;
      }
    } else {
      return configuredApiUrl;
    }
  }

  // Auto-detect based on hostname
  if (typeof window !== 'undefined') {
    const isLocal = window.location.hostname === 'localhost' || 
                    window.location.hostname === '127.0.0.1';
    
    if (isLocal) {
      // Backend runs on port 8000 in development
      return 'http://localhost:8000';
    }
  }

  // Default production API to same-origin root.
  // The frontend bundle may live under /valora/, but backend routes are served at /api/*.
  return '';
};

export const API_URL = getApiUrl();
export default API_URL;
