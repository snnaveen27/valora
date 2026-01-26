import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

const ScrapeController = () => {
  // State
  const [options, setOptions] = useState(null);
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('scrape'); // scrape, history, stats

  // Form state
  const [config, setConfig] = useState({
    search_type: 'buy',
    location: 'Bangalore',
    property_type: 'residential',
    max_items: 1000,
    min_price: null,
    max_price: null,
    min_bedrooms: null,
    max_bedrooms: null,
    category: 'residential'
  });

  // Fetch options on mount
  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/scrape/options`);
        if (res.ok) {
          const data = await res.json();
          setOptions(data);
        }
      } catch (err) {
        console.error('Failed to fetch options:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchOptions();
  }, []);

  // Poll status when scraping
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scrape/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        setError(null);
      }
    } catch (err) {
      setError('Failed to fetch status');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

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
  const handleStart = async () => {
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/api/scrape/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start');
      fetchStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  // Stop scrape
  const handleStop = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scrape/stop`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to stop');
      }
      fetchStatus();
    } catch (err) {
      setError(err.message);
    }
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

  const isRunning = status?.status === 'running' || status?.status === 'starting';

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-32 bg-gray-100 rounded"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          Data Scraper - MagicBricks
        </h2>
        <p className="text-indigo-100 text-sm mt-1">Collect real estate data for Valora analysis</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex -mb-px">
          {[
            { id: 'scrape', label: 'Scrape', icon: '🔄' },
            { id: 'history', label: 'History', icon: '📜' },
            { id: 'stats', label: 'Data Stats', icon: '📊' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-3 px-4 text-center font-medium text-sm border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-1">{tab.icon}</span> {tab.label}
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

        {/* SCRAPE TAB */}
        {activeTab === 'scrape' && (
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(status?.status)} ${isRunning ? 'animate-pulse' : ''}`}></div>
                  <span className="font-semibold text-gray-800 capitalize">
                    {status?.status || 'Idle'}
                  </span>
                </div>
                {status?.timestamp && (
                  <span className="text-xs text-gray-500">
                    Updated: {new Date(status.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>

              {/* Progress Bar */}
              {isRunning && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>{status?.message}</span>
                    <span>{Math.round(status?.progress_percent || 0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-indigo-500 to-purple-500 h-3 rounded-full transition-all duration-500 relative"
                      style={{ width: `${status?.progress_percent || 0}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>
                      📦 {status?.items_found || 0} items found
                      {status?.items_valid > 0 && ` (${status.items_valid} valid)`}
                    </span>
                    <span className="flex items-center gap-4">
                      <span>⏱️ Elapsed: {formatTime(status?.elapsed_seconds)}</span>
                      {status?.eta_seconds > 0 && (
                        <span>🏁 ETA: {formatTime(status?.eta_seconds)}</span>
                      )}
                    </span>
                  </div>
                </div>
              )}

              {/* Completed status */}
              {status?.status === 'completed' && (
                <div className="mt-2 text-green-700 bg-green-50 rounded-md p-3">
                  <div className="font-medium">✅ {status?.message}</div>
                  <div className="text-sm mt-1">
                    Total time: {formatTime(status?.elapsed_seconds)} | 
                    Valid items: {status?.items_valid || 0}
                  </div>
                </div>
              )}

              {/* Failed status */}
              {status?.status === 'failed' && (
                <div className="mt-2 text-red-700 bg-red-50 rounded-md p-3">
                  <div className="font-medium">❌ {status?.message}</div>
                  {status?.errors?.length > 0 && (
                    <ul className="text-sm mt-1 list-disc ml-4">
                      {status.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Configuration Form */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {/* Location */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                <select
                  value={config.location}
                  onChange={(e) => setConfig({ ...config, location: e.target.value })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options?.locations?.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* Search Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Search Type</label>
                <select
                  value={config.search_type}
                  onChange={(e) => setConfig({ ...config, search_type: e.target.value })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options?.search_types?.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* Property Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Property Type</label>
                <select
                  value={config.property_type}
                  onChange={(e) => setConfig({ ...config, property_type: e.target.value, category: e.target.value })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options?.property_types?.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* Max Items */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Items</label>
                <select
                  value={config.max_items}
                  onChange={(e) => setConfig({ ...config, max_items: parseInt(e.target.value) })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options?.max_items_options?.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* Min Bedrooms */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Bedrooms</label>
                <select
                  value={config.min_bedrooms || ''}
                  onChange={(e) => setConfig({ ...config, min_bedrooms: e.target.value ? parseInt(e.target.value) : null })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options?.bedroom_options?.map(opt => (
                    <option key={opt.value || 'any'} value={opt.value || ''}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* Max Bedrooms */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Bedrooms</label>
                <select
                  value={config.max_bedrooms || ''}
                  onChange={(e) => setConfig({ ...config, max_bedrooms: e.target.value ? parseInt(e.target.value) : null })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                >
                  {options?.bedroom_options?.map(opt => (
                    <option key={opt.value || 'any'} value={opt.value || ''}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Price Range (optional) */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Price (₹)</label>
                <input
                  type="number"
                  placeholder="e.g., 5000000"
                  value={config.min_price || ''}
                  onChange={(e) => setConfig({ ...config, min_price: e.target.value ? parseInt(e.target.value) : null })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Price (₹)</label>
                <input
                  type="number"
                  placeholder="e.g., 50000000"
                  value={config.max_price || ''}
                  onChange={(e) => setConfig({ ...config, max_price: e.target.value ? parseInt(e.target.value) : null })}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              {!isRunning ? (
                <button
                  onClick={handleStart}
                  className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Start Scraping
                </button>
              ) : (
                <button
                  onClick={handleStop}
                  className="flex-1 bg-red-500 text-white py-3 px-6 rounded-lg font-semibold hover:bg-red-600 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                  </svg>
                  Stop Scraping
                </button>
              )}
              <button
                onClick={fetchStatus}
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

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
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
                        <div className="font-medium text-gray-800">
                          {entry.location} - {entry.category}
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

        {/* STATS TAB */}
        {activeTab === 'stats' && stats && (
          <div className="space-y-6">
            {/* Total Properties */}
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg p-6 text-white">
              <div className="text-4xl font-bold">{stats.total_properties?.toLocaleString() || 0}</div>
              <div className="text-indigo-100 mt-1">Total Properties in Database</div>
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

            {/* Files */}
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">Data Files</h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {stats.files?.map((file, idx) => (
                  <div key={idx} className="flex justify-between items-center text-sm bg-gray-50 rounded px-3 py-2">
                    <span className="font-mono text-gray-700">{file.name}</span>
                    <span className="text-gray-500">{file.count.toLocaleString()} items</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 text-xs text-gray-500">
        <div className="flex justify-between items-center">
          <span>Actor: ecomscrape~magicbricks-property-search-scraper</span>
          <span>Data stored locally for offline Valora analysis</span>
        </div>
      </div>
    </div>
  );
};

export default ScrapeController;
