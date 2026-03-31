import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../apiConfig';

const MultiSourceScraper = () => {
  // State
  const [platforms, setPlatforms] = useState([]);
  const [activePlatform, setActivePlatform] = useState('magicbricks');
  const [allStatus, setAllStatus] = useState({});
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('scrape'); // scrape, history, stats

  // Form configs - one per platform
  const [configs, setConfigs] = useState({
    magicbricks: {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'residential',
      max_items: 1000,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null
    },
    housing: {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'residential',
      max_items: 1000,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null
    },
    '99acres': {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'residential',
      max_items: 1000,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null
    },
    nobroker: {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'residential',
      max_items: 1000,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null
    }
  });

  // Dropdown options
  const options = {
    search_types: [
      { value: 'buy', label: 'Buy' },
      { value: 'rent', label: 'Rent' },
      { value: 'pg', label: 'PG/Co-living' }
    ],
    property_types: [
      { value: 'residential', label: 'Residential' },
      { value: 'commercial', label: 'Commercial' },
      { value: 'plot', label: 'Plot/Land' }
    ],
    locations: [
      { value: 'Bangalore', label: 'Bangalore' },
      { value: 'Mumbai', label: 'Mumbai' },
      { value: 'Delhi', label: 'Delhi' },
      { value: 'Hyderabad', label: 'Hyderabad' },
      { value: 'Chennai', label: 'Chennai' },
      { value: 'Pune', label: 'Pune' },
      { value: 'Kolkata', label: 'Kolkata' },
      { value: 'Ahmedabad', label: 'Ahmedabad' },
      { value: 'Gurgaon', label: 'Gurgaon' },
      { value: 'Noida', label: 'Noida' }
    ],
    max_items_options: [
      { value: 100, label: '100 (Quick Test)' },
      { value: 500, label: '500' },
      { value: 1000, label: '1,000' },
      { value: 2500, label: '2,500' },
      { value: 5000, label: '5,000' },
      { value: 10000, label: '10,000 (Large)' }
    ],
    bedroom_options: [
      { value: null, label: 'Any' },
      { value: 1, label: '1 BHK' },
      { value: 2, label: '2 BHK' },
      { value: 3, label: '3 BHK' },
      { value: 4, label: '4 BHK' },
      { value: 5, label: '5+ BHK' }
    ]
  };

  // Fetch platforms on mount
  useEffect(() => {
    const fetchPlatforms = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/scrape/platforms`);
        if (res.ok) {
          const data = await res.json();
          setPlatforms(data);
        }
      } catch (err) {
        console.error('Failed to fetch platforms:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlatforms();
  }, []);

  // Poll all status
  const fetchAllStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scrape/status`);
      if (res.ok) {
        const data = await res.json();
        setAllStatus(data.platforms || {});
        setError(null);
      }
    } catch (err) {
      setError('Failed to fetch status');
    }
  }, []);

  useEffect(() => {
    fetchAllStatus();
    const interval = setInterval(fetchAllStatus, 2000);
    return () => clearInterval(interval);
  }, [fetchAllStatus]);

  // Fetch history and stats
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [historyRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/scrape/history`),
          fetch(`${API_BASE}/api/scrape/stats`)
        ]);
        if (historyRes.ok) setHistory(await historyRes.json());
        if (statsRes.ok) setStats(await statsRes.json());
      } catch (err) {
        console.error('Failed to fetch data:', err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Start scrape
  const handleStart = async (platform) => {
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/api/scrape/${platform}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configs[platform])
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start');
      fetchAllStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  // Stop scrape
  const handleStop = async (platform) => {
    try {
      const res = await fetch(`${API_BASE}/api/scrape/${platform}/stop`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to stop');
      }
      fetchAllStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  // Update config for a platform
  const updateConfig = (platform, field, value) => {
    setConfigs(prev => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        [field]: value
      }
    }));
  };

  // Helpers
  const formatTime = (seconds) => {
    if (!seconds || seconds < 0) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  const getStatusColor = (s) => {
    switch (s) {
      case 'running': case 'starting': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'stopped': return 'bg-yellow-500';
      default: return 'bg-gray-400';
    }
  };

  const getPlatformIcon = (platformId) => {
    const platform = platforms.find(p => p.id === platformId);
    return platform?.icon || '🏠';
  };

  const getPlatformName = (platformId) => {
    const platform = platforms.find(p => p.id === platformId);
    return platform?.name || platformId;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-32 bg-gray-100 rounded"></div>
      </div>
    );
  }

  const currentStatus = allStatus[activePlatform] || {};
  const isRunning = currentStatus.status === 'running' || currentStatus.status === 'starting';
  const currentConfig = configs[activePlatform];

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          Multi-Source Data Scraper
        </h2>
        <p className="text-indigo-100 text-sm mt-1">Collect data from multiple real estate platforms</p>
      </div>

      {/* Platform Tabs */}
      <div className="border-b border-gray-200 bg-gray-50">
        <nav className="flex -mb-px overflow-x-auto">
          {platforms.map(platform => {
            const status = allStatus[platform.id] || {};
            const isActive = activePlatform === platform.id;
            const isPlatformRunning = status.status === 'running' || status.status === 'starting';
            
            return (
              <button
                key={platform.id}
                onClick={() => setActivePlatform(platform.id)}
                className={`flex-shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors relative ${
                  isActive
                    ? 'border-indigo-500 text-indigo-600 bg-white'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{platform.icon}</span>
                  <span>{platform.name}</span>
                  {isPlatformRunning && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  )}
                  {status.status === 'completed' && (
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  )}
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* View Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex -mb-px px-6">
          {[
            { id: 'scrape', label: 'Scrape', icon: '🔄' },
            { id: 'history', label: 'History', icon: '📜' },
            { id: 'stats', label: 'Stats', icon: '📊' }
          ].map(view => (
            <button
              key={view.id}
              onClick={() => setActiveView(view.id)}
              className={`py-3 px-4 text-center font-medium text-sm border-b-2 transition-colors ${
                activeView === view.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-1">{view.icon}</span> {view.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-6">
        {/* Error display */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">×</button>
          </div>
        )}

        {/* SCRAPE VIEW */}
        {activeView === 'scrape' && (
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(currentStatus.status)} ${isRunning ? 'animate-pulse' : ''}`}></div>
                  <span className="font-semibold text-gray-800 capitalize flex items-center gap-2">
                    <span className="text-xl">{getPlatformIcon(activePlatform)}</span>
                    {getPlatformName(activePlatform)} - {currentStatus.status || 'Idle'}
                  </span>
                </div>
                {currentStatus.timestamp && (
                  <span className="text-xs text-gray-500">
                    {new Date(currentStatus.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>

              {/* Progress Bar */}
              {isRunning && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>{currentStatus.message}</span>
                    <span>{Math.round(currentStatus.progress_percent || 0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-indigo-500 to-purple-500 h-3 rounded-full transition-all duration-500 relative"
                      style={{ width: `${currentStatus.progress_percent || 0}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>
                      📦 {currentStatus.items_found || 0} found
                      {currentStatus.items_valid > 0 && ` | ✅ ${currentStatus.items_valid} valid`}
                      {currentStatus.items_new > 0 && ` | ➕ ${currentStatus.items_new} new`}
                    </span>
                    <span className="flex items-center gap-4">
                      <span>⏱️ {formatTime(currentStatus.elapsed_seconds)}</span>
                      {currentStatus.eta_seconds > 0 && (
                        <span>🏁 ETA: {formatTime(currentStatus.eta_seconds)}</span>
                      )}
                    </span>
                  </div>
                </div>
              )}

              {/* Completed status */}
              {currentStatus.status === 'completed' && (
                <div className="mt-2 text-green-700 bg-green-50 rounded-md p-3">
                  <div className="font-medium">✅ {currentStatus.message}</div>
                  <div className="text-sm mt-1">
                    Duration: {formatTime(currentStatus.elapsed_seconds)} | 
                    Valid: {currentStatus.items_valid || 0} | 
                    New: {currentStatus.items_new || 0}
                  </div>
                </div>
              )}

              {/* Failed status */}
              {currentStatus.status === 'failed' && (
                <div className="mt-2 text-red-700 bg-red-50 rounded-md p-3">
                  <div className="font-medium">❌ {currentStatus.message}</div>
                  {currentStatus.errors?.length > 0 && (
                    <ul className="text-sm mt-1 list-disc ml-4">
                      {currentStatus.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Configuration Form */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                <select
                  value={currentConfig.location}
                  onChange={(e) => updateConfig(activePlatform, 'location', e.target.value)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options.locations.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Search Type</label>
                <select
                  value={currentConfig.search_type}
                  onChange={(e) => updateConfig(activePlatform, 'search_type', e.target.value)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options.search_types.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Property Type</label>
                <select
                  value={currentConfig.property_type}
                  onChange={(e) => updateConfig(activePlatform, 'property_type', e.target.value)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options.property_types.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Items</label>
                <select
                  value={currentConfig.max_items}
                  onChange={(e) => updateConfig(activePlatform, 'max_items', parseInt(e.target.value))}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options.max_items_options.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Bedrooms</label>
                <select
                  value={currentConfig.min_bedrooms || ''}
                  onChange={(e) => updateConfig(activePlatform, 'min_bedrooms', e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options.bedroom_options.map(opt => (
                    <option key={opt.value || 'any'} value={opt.value || ''}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Bedrooms</label>
                <select
                  value={currentConfig.max_bedrooms || ''}
                  onChange={(e) => updateConfig(activePlatform, 'max_bedrooms', e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options.bedroom_options.map(opt => (
                    <option key={opt.value || 'any'} value={opt.value || ''}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Price Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Price (₹)</label>
                <input
                  type="number"
                  placeholder="e.g., 5000000"
                  value={currentConfig.min_price || ''}
                  onChange={(e) => updateConfig(activePlatform, 'min_price', e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Price (₹)</label>
                <input
                  type="number"
                  placeholder="e.g., 50000000"
                  value={currentConfig.max_price || ''}
                  onChange={(e) => updateConfig(activePlatform, 'max_price', e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              {!isRunning ? (
                <button
                  onClick={() => handleStart(activePlatform)}
                  className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Start {getPlatformName(activePlatform)}
                </button>
              ) : (
                <button
                  onClick={() => handleStop(activePlatform)}
                  className="flex-1 bg-red-500 text-white py-3 px-6 rounded-lg font-semibold hover:bg-red-600 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                  </svg>
                  Stop
                </button>
              )}
              <button
                onClick={fetchAllStatus}
                className="px-4 py-3 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
                title="Refresh Status"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* HISTORY VIEW */}
        {activeView === 'history' && (
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-800">Recent Scrapes</h3>
            {history.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <svg className="w-12 h-12 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                No scrape history yet
              </div>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {[...history].reverse().map((entry, idx) => (
                  <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-gray-800 flex items-center gap-2">
                          <span className="text-lg">{getPlatformIcon(entry.platform)}</span>
                          {getPlatformName(entry.platform)} - {entry.location} - {entry.category}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          📦 {entry.items_scraped} scraped → ✅ {entry.items_valid} valid → ➕ {entry.items_new} new
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Total in DB: {entry.total_in_db} | Duration: {formatTime(entry.elapsed_seconds)}
                        </div>
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDate(entry.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* STATS VIEW */}
        {activeView === 'stats' && stats && (
          <div className="space-y-6">
            {/* Total Properties */}
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg p-6 text-white">
              <div className="text-4xl font-bold">{stats.total_properties?.toLocaleString() || 0}</div>
              <div className="text-indigo-100 mt-1">Total Properties in Database</div>
            </div>

            {/* By Platform */}
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">By Platform</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(stats.by_platform || {}).map(([platform, count]) => (
                  <div key={platform} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <div className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                      <span>{getPlatformIcon(platform)}</span>
                      {count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 capitalize">{getPlatformName(platform)}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* By Location */}
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">By Location</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(stats.by_location || {}).map(([loc, count]) => (
                  <div key={loc} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <div className="text-lg font-semibold text-gray-800">{count.toLocaleString()}</div>
                    <div className="text-sm text-gray-600 capitalize">{loc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* By Category */}
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">By Category</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(stats.by_category || {}).map(([cat, count]) => (
                  <div key={cat} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <div className="text-lg font-semibold text-gray-800">{count.toLocaleString()}</div>
                    <div className="text-sm text-gray-600 capitalize">{cat}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 text-xs text-gray-500">
        <div className="flex justify-between items-center">
          <span>Multi-platform scraping: {platforms.map(p => p.name).join(', ')}</span>
          <span>Data stored locally for offline Valora analysis</span>
        </div>
      </div>
    </div>
  );
};

export default MultiSourceScraper;
