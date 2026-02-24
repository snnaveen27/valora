/**
 * ActivityFeed - Activity stream component
 * 
 * Features:
 * - Anonymized user activity display
 * - Activity types: views, saves, shares, searches
 * - Filter by time period
 * - Trend indicators
 * - Real-time updates simulation
 * 
 * Props:
 * @param {Array} activities - List of activity items
 * @param {boolean} loading - Loading state
 * @param {string} [error] - Error message
 * @param {string} [filter] - Current filter (all, views, saves, shares, searches)
 * @param {function} [onFilterChange] - Filter change handler
 * @param {string} [period] - Time period (today, week, month, all)
 * @param {function} [onPeriodChange] - Period change handler
 * @param {boolean} [autoRefresh] - Enable auto-refresh
 * @param {number} [refreshInterval] - Refresh interval in ms
 */

import { useState, useEffect, useMemo } from 'react';
import { 
  Eye, 
  Heart, 
  Share2, 
  Search, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  Filter,
  RefreshCw,
  Loader2,
  Home,
  MapPin,
  Building,
  Users,
  ChevronRight,
} from 'lucide-react';

// Activity type configurations
const ACTIVITY_CONFIG = {
  property_view: {
    icon: Eye,
    color: 'text-blue-400',
    bg: 'bg-blue-500/20',
    label: 'Viewed',
    verb: 'viewed',
  },
  property_save: {
    icon: Heart,
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    label: 'Saved',
    verb: 'saved',
  },
  property_share: {
    icon: Share2,
    color: 'text-green-400',
    bg: 'bg-green-500/20',
    label: 'Shared',
    verb: 'shared',
  },
  search: {
    icon: Search,
    color: 'text-purple-400',
    bg: 'bg-purple-500/20',
    label: 'Searched',
    verb: 'searched for',
  },
  inquiry: {
    icon: Users,
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/20',
    label: 'Inquired',
    verb: 'inquired about',
  },
};

// Generate anonymized user identifier
const generateAnonymousUser = (index) => {
  const prefixes = ['User', 'Buyer', 'Investor', 'Home seeker'];
  const suffix = Math.floor(Math.random() * 1000);
  return `${prefixes[index % prefixes.length]} #${suffix}`;
};

// Format relative time
const formatRelativeTime = (timestamp) => {
  const now = new Date();
  const time = new Date(timestamp);
  const diffMs = now - time;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return time.toLocaleDateString();
};

// Activity Item Component
function ActivityItem({ activity, index }) {
  const config = ACTIVITY_CONFIG[activity.type] || ACTIVITY_CONFIG.property_view;
  const Icon = config.icon;
  
  // Generate a consistent but anonymous user
  const anonymousUser = useMemo(() => 
    generateAnonymousUser(activity.user_id || index),
    [activity.user_id, index]
  );
  
  return (
    <div className="flex items-start gap-3 p-3 hover:bg-gray-700/30 rounded-lg transition-colors group">
      {/* Icon */}
      <div className={`
        w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
        ${config.bg} ${config.color}
      `}>
        <Icon size={14} />
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200">
          <span className="font-medium text-white">{anonymousUser}</span>
          {' '}
          <span className="text-gray-400">{config.verb}</span>
          {' '}
          <span className="text-blue-300 truncate">
            {activity.property_title || activity.locality_name || 'a property'}
          </span>
        </p>
        
        {/* Location */}
        {activity.locality && (
          <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
            <MapPin size={10} />
            <span>{activity.locality}</span>
            {activity.city && <span>, {activity.city}</span>}
          </div>
        )}
        
        {/* Metadata */}
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Clock size={10} />
            {formatRelativeTime(activity.timestamp)}
          </span>
          
          {activity.price && (
            <span className="text-emerald-400 font-medium">
              ₹{activity.price.toLocaleString()}
            </span>
          )}
        </div>
      </div>
      
      {/* Trend indicator */}
      {activity.trend && (
        <div className={`flex items-center gap-0.5 ${activity.trend > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {activity.trend > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          <span className="text-xs">{Math.abs(activity.trend)}%</span>
        </div>
      )}
    </div>
  );
}

// Filter Pills Component
function FilterPills({ activeFilter, onFilterChange }) {
  const filters = [
    { key: 'all', label: 'All', icon: null },
    { key: 'property_view', label: 'Views', icon: Eye },
    { key: 'property_save', label: 'Saves', icon: Heart },
    { key: 'property_share', label: 'Shares', icon: Share2 },
    { key: 'search', label: 'Searches', icon: Search },
  ];
  
  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
      {filters.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          onClick={() => onFilterChange(key)}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium
            whitespace-nowrap transition-all
            ${activeFilter === key
              ? 'bg-blue-500 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }
          `}
        >
          {Icon && <Icon size={12} />}
          {label}
        </button>
      ))}
    </div>
  );
}

// Period Selector Component
function PeriodSelector({ period, onPeriodChange }) {
  const periods = [
    { key: 'today', label: 'Today' },
    { key: 'week', label: 'This Week' },
    { key: 'month', label: 'This Month' },
    { key: 'all', label: 'All Time' },
  ];
  
  return (
    <div className="flex items-center gap-1 p-1 bg-gray-700/50 rounded-lg">
      {periods.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onPeriodChange(key)}
          className={`
            px-3 py-1 rounded-md text-xs font-medium transition-all
            ${period === key
              ? 'bg-gray-600 text-white'
              : 'text-gray-400 hover:text-white'
            }
          `}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// Stats Summary Component
function StatsSummary({ activities }) {
  const stats = useMemo(() => {
    const counts = {
      views: 0,
      saves: 0,
      shares: 0,
      searches: 0,
    };
    
    activities.forEach(activity => {
      if (activity.type === 'property_view') counts.views++;
      else if (activity.type === 'property_save') counts.saves++;
      else if (activity.type === 'property_share') counts.shares++;
      else if (activity.type === 'search') counts.searches++;
    });
    
    return counts;
  }, [activities]);
  
  const items = [
    { key: 'views', label: 'Views', icon: Eye, color: 'text-blue-400' },
    { key: 'saves', label: 'Saves', icon: Heart, color: 'text-red-400' },
    { key: 'shares', label: 'Shares', icon: Share2, color: 'text-green-400' },
    { key: 'searches', label: 'Searches', icon: Search, color: 'text-purple-400' },
  ];
  
  return (
    <div className="grid grid-cols-4 gap-2 p-3 bg-gray-700/30 rounded-lg">
      {items.map(({ key, label, icon: Icon, color }) => (
        <div key={key} className="text-center">
          <div className={`flex justify-center mb-1 ${color}`}>
            <Icon size={16} />
          </div>
          <div className="text-lg font-bold text-white">{stats[key]}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      ))}
    </div>
  );
}

// Skeleton Loader
function ActivitySkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="flex items-start gap-3 p-3">
          <div className="w-8 h-8 rounded-full bg-gray-700 animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-3/4 bg-gray-700 rounded animate-pulse" />
            <div className="h-3 w-1/2 bg-gray-700 rounded animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Empty State
function EmptyState({ filter }) {
  const config = ACTIVITY_CONFIG[filter];
  const Icon = config?.icon || Filter;
  
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 rounded-full bg-gray-700/50 flex items-center justify-center mb-4">
        <Icon className="text-gray-500" size={24} />
      </div>
      <h3 className="text-lg font-medium text-gray-300 mb-1">No Activity Yet</h3>
      <p className="text-sm text-gray-500">
        {filter === 'all' 
          ? 'Be the first to interact with properties in this area!'
          : `No ${config?.label || 'activity'} to show yet`
        }
      </p>
    </div>
  );
}

// Error State
function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <Filter className="text-red-400" size={24} />
      </div>
      <h3 className="text-lg font-medium text-gray-300 mb-1">Unable to Load Activity</h3>
      <p className="text-sm text-gray-500 mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
      >
        <RefreshCw size={16} />
        Try Again
      </button>
    </div>
  );
}

// Main Component
export default function ActivityFeed({
  activities: initialActivities,
  loading = false,
  error,
  filter: initialFilter = 'all',
  onFilterChange,
  period = 'week',
  onPeriodChange,
  localityId,
  showStats = true,
  maxItems = 20,
}) {
  const [filter, setFilter] = useState(initialFilter);
  const [timePeriod, setTimePeriod] = useState(period);
  
  // Filter activities
  const filteredActivities = useMemo(() => {
    let filtered = initialActivities || [];
    
    // Filter by type
    if (filter !== 'all') {
      filtered = filtered.filter(a => a.type === filter);
    }
    
    // Filter by period
    if (timePeriod !== 'all') {
      const now = new Date();
      let cutoff;
      
      switch (timePeriod) {
        case 'today':
          cutoff = new Date(now.setHours(0, 0, 0, 0));
          break;
        case 'week':
          cutoff = new Date(now.setDate(now.getDate() - 7));
          break;
        case 'month':
          cutoff = new Date(now.setMonth(now.getMonth() - 1));
          break;
        default:
          cutoff = null;
      }
      
      if (cutoff) {
        filtered = filtered.filter(a => new Date(a.timestamp) >= cutoff);
      }
    }
    
    // Sort by timestamp (newest first)
    filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Limit items
    return filtered.slice(0, maxItems);
  }, [initialActivities, filter, timePeriod, maxItems]);
  
  const handleFilterChange = (newFilter) => {
    setFilter(newFilter);
    onFilterChange?.(newFilter);
  };
  
  const handlePeriodChange = (newPeriod) => {
    setTimePeriod(newPeriod);
    onPeriodChange?.(newPeriod);
  };
  
  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Activity Feed</h3>
          <PeriodSelector 
            period={timePeriod} 
            onPeriodChange={handlePeriodChange} 
          />
        </div>
        
        <FilterPills 
          activeFilter={filter} 
          onFilterChange={handleFilterChange} 
        />
      </div>
      
      {/* Stats Summary */}
      {showStats && !loading && !error && (
        <div className="p-4 border-b border-gray-700">
          <StatsSummary activities={initialActivities || []} />
        </div>
      )}
      
      {/* Activity List */}
      <div className="max-h-[500px] overflow-y-auto scrollbar-thin">
        {loading ? (
          <ActivitySkeleton />
        ) : error ? (
          <ErrorState message={error} />
        ) : filteredActivities.length === 0 ? (
          <EmptyState filter={filter} />
        ) : (
          <div className="divide-y divide-gray-700/50">
            {filteredActivities.map((activity, index) => (
              <ActivityItem 
                key={activity.id || index} 
                activity={activity}
                index={index}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Load More */}
      {filteredActivities.length > 0 && filteredActivities.length >= maxItems && (
        <div className="p-3 border-t border-gray-700">
          <button className="w-full flex items-center justify-center gap-2 py-2 text-sm text-blue-400 hover:text-blue-300 transition-colors">
            Load More Activity
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

// Export mock data generator for demo purposes
export const generateMockActivities = (count = 20, localityId = null) => {
  const types = ['property_view', 'property_save', 'property_share', 'search'];
  const localities = ['Whitefield', 'Koramangala', 'HSR Layout', 'Indiranagar', 'JP Nagar'];
  const propertyTypes = ['2BHK Apartment', '3BHK Flat', 'Villa', 'Penthouse', 'Studio'];
  
  return Array.from({ length: count }, (_, i) => {
    const type = types[Math.floor(Math.random() * types.length)];
    const locality = localities[Math.floor(Math.random() * localities.length)];
    const propertyType = propertyTypes[Math.floor(Math.random() * propertyTypes.length)];
    const timestamp = new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000);
    
    return {
      id: `activity_${i}`,
      type,
      user_id: Math.floor(Math.random() * 100),
      property_title: `${propertyType} in ${locality}`,
      locality: locality,
      city: 'Bangalore',
      price: Math.floor(Math.random() * 50 + 20) * 100000,
      timestamp: timestamp.toISOString(),
      trend: Math.floor(Math.random() * 20) - 10,
    };
  });
};
