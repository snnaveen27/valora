/**
 * Centralized API configuration for Valora AI
 * Handles switching between local development and production environments
 */

const getApiUrl = () => {
  // In development (Vite), use relative path to leverage Vite proxy
  if (import.meta.env.DEV) {
    return import.meta.env.VITE_API_URL || '';
  }
  // Check if explicit URL is provided in environment
  if (import.meta.env.VITE_API_URL) {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
      const isEnvLocal = /localhost|127\.0\.0\.1/.test(import.meta.env.VITE_API_URL);
      if (!isLocalHost && isEnvLocal) {
        // Ignore local API URL when running on a non-local host
      } else {
        return import.meta.env.VITE_API_URL;
      }
    } else {
      return import.meta.env.VITE_API_URL;
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

  // Default production path (proxied via Nginx)
  // Note: Don't include /api here - fetch calls already add /api/ prefix
  return '/valora';
};

export const API_URL = getApiUrl();
export default API_URL;
