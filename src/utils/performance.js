/**
 * Frontend Performance Optimizations
 * Lazy loading, code splitting, and optimization strategies
 */

import { lazy, Suspense, useState, useEffect, memo } from 'react';

// Lazy load heavy components
export const Cesium3DMap = lazy(() => import('../spatial/Cesium3DMap'));
export const AnalysisPanel = lazy(() => import('../components/AnalysisPanel'));
export const AdminDashboard = lazy(() => import('../components/AdminDashboard'));

// Loading fallback
export const LoadingFallback = () => (
  <div className="flex items-center justify-center h-full">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
  </div>
);

// Memoized component wrapper

export const MemoizedChatMessage = memo(({ message }) => {
  return (
    <div className="message">
      <div className="content">{message.content}</div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison - only re-render if content changed
  return prevProps.message.id === nextProps.message.id &&
         prevProps.message.content === nextProps.message.content;
});

// Virtual list for long chat histories
export const VirtualizedMessageList = ({ messages }) => {
  // Implement virtual scrolling for messages > 50
  const visibleMessages = messages.slice(-50); // Only show last 50
  
  return (
    <div className="message-list">
      {messages.length > 50 && (
        <div className="text-center text-gray-500 py-2">
          {messages.length - 50} older messages hidden
        </div>
      )}
      {visibleMessages.map(msg => (
        <MemoizedChatMessage key={msg.id} message={msg} />
      ))}
    </div>
  );
};

// Debounced search input
export const useDebouncedValue = (value, delay = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  
  return debouncedValue;
};

// API request caching
const apiCache = new Map();

export const cachedApiCall = async (endpoint, options = {}, ttl = 60000) => {
  const cacheKey = `${endpoint}:${JSON.stringify(options)}`;
  const cached = apiCache.get(cacheKey);
  
  if (cached && Date.now() - cached.timestamp < ttl) {
    return cached.data;
  }
  
  const response = await fetch(endpoint, options);
  const data = await response.json();
  
  apiCache.set(cacheKey, { data, timestamp: Date.now() });
  return data;
};

// Clear cache by pattern
export const clearApiCache = (pattern) => {
  for (const key of apiCache.keys()) {
    if (key.includes(pattern)) {
      apiCache.delete(key);
    }
  }
};
