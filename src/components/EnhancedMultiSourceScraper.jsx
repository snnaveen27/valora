import React, { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../apiConfig';

const EnhancedMultiSourceScraper = () => {
  // State
  const [platforms, setPlatforms] = useState([]);
  const [activePlatform, setActivePlatform] = useState('magicbricks');
  const [allStatus, setAllStatus] = useState({});
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('scrape');
  const [showUrlPreview, setShowUrlPreview] = useState(true);

  // Form configs - one per platform
  const [configs, setConfigs] = useState({
    magicbricks: {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'flat',
      max_items: 500,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null,
      custom_url: '',
      proxy_enabled: true,
      proxy_country: 'US'
    },
    housing: {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'flat',
      max_items: 500,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null,
      custom_url: '',
      proxy_enabled: false,
      proxy_country: 'IN'
    },
    '99acres': {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'flat',
      max_items: 500,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null,
      custom_url: '',
      sort_by: 'relevance'
    },
    nobroker: {
      search_type: 'buy',
      location: 'Bangalore',
      property_type: 'flat',
      max_items: 500,
      min_price: null,
      max_price: null,
      min_bedrooms: null,
      max_bedrooms: null,
      custom_url: '',
      proxy_enabled: true,
      proxy_country: 'US'
    }
  });

  // Platform-specific options
  const platformOptions = {
    magicbricks: {
      property_subtypes: [
        { value: 'Multistorey-Apartment', label: 'Multi-storey Apartment' },
        { value: 'Builder-Floor-Apartment', label: 'Builder Floor' },
        { value: 'Penthouse', label: 'Penthouse' },
        { value: 'Villa', label: 'Villa' },
        { value: 'Residential-House', label: 'House' }
      ],
      proxy_countries: [
        { value: 'US', label: 'United States' },
        { value: 'IN', label: 'India' },
        { value: 'SG', label: 'Singapore' }
      ]
    },
    '99acres': {
      sort_options: [
        { value: 'relevance', label: 'Relevance' },
        { value: 'price-asc', label: 'Price: Low to High' },
        { value: 'price-desc', label: 'Price: High to Low' },
        { value: 'date', label: 'Recently Added' }
      ]
    },
    nobroker: {
      proxy_countries: [
        { value: 'US', label: 'United States' },
        { value: 'IN', label: 'India' }
      ]
    }
  };

  // Common dropdown options
  const options = {
    search_types: [
      { value: 'buy', label: '🏠 Buy' },
      { value: 'rent', label: '🔑 Rent' },
      { value: 'pg', label: '🛏️ PG/Co-living' }
    ],
    property_types: [
      // Residential
      { value: 'flat', label: '🏢 Flat/Apartment', category: 'Residential' },
      { value: 'house', label: '🏠 Independent House', category: 'Residential' },
      { value: 'villa', label: '🏡 Villa', category: 'Residential' },
      { value: 'penthouse', label: '🌆 Penthouse', category: 'Residential' },
      { value: 'studio-apartment', label: '🛏️ Studio Apartment', category: 'Residential' },
      { value: 'builder-floor', label: '�️ Builder Floor', category: 'Residential' },
      
      // Commercial
      { value: 'office', label: '💼 Office Space', category: 'Commercial' },
      { value: 'commercial-shop', label: '� Shop/Showroom', category: 'Commercial' },
      { value: 'commercial-space', label: '�� Commercial Space', category: 'Commercial' },
      { value: 'coworking', label: '👥 Coworking Space', category: 'Commercial' },
      { value: 'warehouse', label: '📦 Warehouse/Godown', category: 'Commercial' },
      { value: 'industrial-building', label: '🏭 Industrial Building', category: 'Commercial' },
      
      // Land/Plot
      { value: 'plot', label: '🌳 Residential Plot', category: 'Land' },
      { value: 'commercial-land', label: '🏗️ Commercial Land', category: 'Land' },
      { value: 'agricultural-land', label: '🌾 Agricultural Land', category: 'Land' },
      { value: 'industrial-land', label: '⚙️ Industrial Land', category: 'Land' },
      
      // Co-living & PG
      { value: 'pg', label: '🛏️ PG (Paying Guest)', category: 'Co-living' },
      { value: 'coliving', label: '🏘️ Co-living Space', category: 'Co-living' },
      { value: 'hostel', label: '🎓 Student Hostel', category: 'Co-living' },
      { value: 'luxury-pg', label: '✨ Luxury PG', category: 'Co-living' }
    ],
    locations: [
      { value: 'Bangalore', label: 'Bangalore (Bengaluru)' },
      { value: 'Mumbai', label: 'Mumbai' },
      { value: 'Delhi', label: 'Delhi' },
      { value: 'New-Delhi', label: 'New Delhi' },
      { value: 'Hyderabad', label: 'Hyderabad' },
      { value: 'Chennai', label: 'Chennai' },
      { value: 'Pune', label: 'Pune' },
      { value: 'Kolkata', label: 'Kolkata' },
      { value: 'Ahmedabad', label: 'Ahmedabad' },
      { value: 'Gurgaon', label: 'Gurgaon' },
      { value: 'Noida', label: 'Noida' },
      { value: 'Goa', label: 'Goa' }
    ],
    max_items_options: [
      { value: 50, label: '50 (Quick Test)', color: 'green' },
      { value: 100, label: '100 (Small)', color: 'green' },
      { value: 500, label: '500 (Recommended)', color: 'blue' },
      { value: 1000, label: '1,000 (Medium)', color: 'blue' },
      { value: 2500, label: '2,500 (Large)', color: 'orange' },
      { value: 5000, label: '5,000 (Very Large)', color: 'orange' },
      { value: 10000, label: '10,000 (Maximum)', color: 'red' }
    ],
    bedroom_options: [
      { value: null, label: 'Any Bedrooms' },
      { value: 1, label: '1 BHK' },
      { value: 2, label: '2 BHK' },
      { value: 3, label: '3 BHK' },
      { value: 4, label: '4 BHK' },
      { value: 5, label: '5+ BHK' }
    ],
    price_ranges: {
      buy: [
        { min: null, max: 5000000, label: 'Under ₹50 Lac' },
        { min: 5000000, max: 10000000, label: '₹50L - ₹1Cr' },
        { min: 10000000, max: 15000000, label: '₹1Cr - ₹1.5Cr' },
        { min: 15000000, max: 30000000, label: '₹1.5Cr - ₹3Cr' },
        { min: 30000000, max: null, label: 'Above ₹3Cr' },
        { min: null, max: null, label: 'Any Price' }
      ],
      rent: [
        { min: null, max: 10000, label: 'Under ₹10,000' },
        { min: 10000, max: 15000, label: '₹10K - ₹15K' },
        { min: 15000, max: 25000, label: '₹15K - ₹25K' },
        { min: 25000, max: 50000, label: '₹25K - ₹50K' },
        { min: 50000, max: null, label: 'Above ₹50K' },
        { min: null, max: null, label: 'Any Price' }
      ]
    }
  };

  // Filter property types based on search_type
  const getFilteredPropertyTypes = () => {
    const config = configs[activePlatform];
    const searchType = config.search_type;

    // MagicBricks specific filtering
    if (activePlatform === 'magicbricks') {
      if (searchType === 'buy') {
        // Buy: flat, house, villa, plot, penthouse, builder-floor
        return options.property_types.filter(pt => 
          ['flat', 'house', 'villa', 'plot', 'penthouse', 'builder-floor', 'studio-apartment'].includes(pt.value)
        );
      } else if (searchType === 'rent') {
        // Rent: flat, house only
        return options.property_types.filter(pt => 
          ['flat', 'house', 'villa', 'pg', 'coliving'].includes(pt.value)
        );
      }
    }

    // For other platforms, show all for now (will be customized later)
    return options.property_types;
  };

  // Generate URL preview
  const getUrlPreview = () => {
    const config = configs[activePlatform];
    const location = config.location.replace(' ', '-');
    const searchType = config.search_type;

    if (activePlatform === 'magicbricks') {
      const bedroom = config.min_bedrooms ? `&bedroom=${config.min_bedrooms}` : '';
      return `magicbricks.com/property-for-${searchType}/residential-real-estate?cityName=${location}${bedroom}`;
    } else if (activePlatform === 'housing') {
      const action = searchType === 'buy' ? 'buy' : 'rent';
      return `housing.com/in/${action}/projects/${location.toLowerCase()}`;
    } else if (activePlatform === '99acres') {
      return `99acres.com/search/property/${searchType}/residential-property/${location.toLowerCase()}`;
    } else if (activePlatform === 'nobroker') {
      const action = searchType === 'buy' ? 'sale' : 'rent';
      return `nobroker.in/property/${action}/${location.toLowerCase()}`;
    }
    return '';
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

  // Validation
  const validateConfig = () => {
    const config = configs[activePlatform];
    const errors = [];

    if (!config.location) errors.push('Please select a location');
    if (!config.search_type) errors.push('Please select search type (Buy/Rent)');
    if (config.max_items < 10) errors.push('Minimum 10 items required');
    if (config.max_items > 10000) errors.push('Maximum 10,000 items allowed');
    
    if (config.min_price && config.max_price && config.min_price >= config.max_price) {
      errors.push('Min price must be less than max price');
    }

    return errors;
  };

  // Start scrape
  const handleStart = async (platform) => {
    const errors = validateConfig();
    if (errors.length > 0) {
      setError(errors.join('. '));
      return;
    }

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

  // Apply price range preset
  const applyPriceRange = (range) => {
    updateConfig(activePlatform, 'min_price', range.min);
    updateConfig(activePlatform, 'max_price', range.max);
  };

  // Update config
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

  const formatPrice = (price) => {
    if (!price) return '';
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(1)}Cr`;
    if (price >= 100000) return `₹${(price / 100000).toFixed(1)}L`;
    return `₹${price.toLocaleString()}`;
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
        <p className="text-indigo-100 text-sm mt-1">High-quality real estate data from 4 major platforms</p>
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
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700 font-bold">×</button>
          </div>
        )}

        {/* SCRAPE VIEW */}
        {activeView === 'scrape' && (
          <div className="space-y-6">
            {/* URL Preview */}
            {showUrlPreview && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    <span className="font-semibold text-blue-900">Preview URL</span>
                  </div>
                  <button
                    onClick={() => setShowUrlPreview(false)}
                    className="text-blue-500 hover:text-blue-700"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <code className="text-sm text-blue-800 bg-blue-100 px-3 py-2 rounded block overflow-x-auto">
                  {getUrlPreview()}
                </code>
                <p className="text-xs text-blue-600 mt-2">
                  This is the URL that will be scraped. Adjust filters below to refine.
                </p>
              </div>
            )}

            {/* Status Card */}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
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
                    <span className="font-bold">{Math.round(currentStatus.progress_percent || 0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden shadow-inner">
                    <div
                      className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-4 rounded-full transition-all duration-500 relative"
                      style={{ width: `${currentStatus.progress_percent || 0}%` }}
                    >
                      <div className="absolute inset-0 bg-white/30 animate-pulse"></div>
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span className="flex items-center gap-3">
                      <span>📦 {currentStatus.items_found || 0} found</span>
                      {currentStatus.items_valid > 0 && (
                        <span className="text-green-600 font-semibold">✅ {currentStatus.items_valid} valid</span>
                      )}
                      {currentStatus.items_new > 0 && (
                        <span className="text-blue-600 font-semibold">➕ {currentStatus.items_new} new</span>
                      )}
                    </span>
                    <span className="flex items-center gap-4">
                      <span>⏱️ {formatTime(currentStatus.elapsed_seconds)}</span>
                      {currentStatus.eta_seconds > 0 && (
                        <span className="text-indigo-600 font-semibold">🏁 ETA: {formatTime(currentStatus.eta_seconds)}</span>
                      )}
                    </span>
                  </div>
                </div>
              )}

              {/* Completed status */}
              {currentStatus.status === 'completed' && (
                <div className="mt-2 text-green-700 bg-green-50 rounded-md p-3 border border-green-200">
                  <div className="font-medium flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {currentStatus.message}
                  </div>
                  <div className="text-sm mt-2 grid grid-cols-3 gap-2">
                    <div>Duration: <span className="font-bold">{formatTime(currentStatus.elapsed_seconds)}</span></div>
                    <div>Valid: <span className="font-bold text-green-600">{currentStatus.items_valid || 0}</span></div>
                    <div>New: <span className="font-bold text-blue-600">{currentStatus.items_new || 0}</span></div>
                  </div>
                </div>
              )}

              {/* Failed status */}
              {currentStatus.status === 'failed' && (
                <div className="mt-2 text-red-700 bg-red-50 rounded-md p-3 border border-red-200">
                  <div className="font-medium flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {currentStatus.message}
                  </div>
                  {currentStatus.errors?.length > 0 && (
                    <ul className="text-sm mt-2 list-disc ml-6 space-y-1">
                      {currentStatus.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Configuration Form */}
            <div className="bg-gradient-to-br from-gray-50 to-white rounded-lg p-5 border border-gray-200">
              <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
                Search Configuration
              </h3>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {/* Location */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    📍 Location <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={currentConfig.location}
                    onChange={(e) => updateConfig(activePlatform, 'location', e.target.value)}
                    disabled={isRunning}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    {options.locations.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                {/* Search Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    🔍 Search Type <span className="text-red-500">*</span>
                  </label>
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

                {/* Property Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5 flex items-center gap-2">
                    🏘️ Property Type
                    {activePlatform === 'magicbricks' && (
                      <span className="text-xs text-blue-600 font-normal">
                        ({currentConfig.search_type === 'buy' ? '7 types' : '5 types'} for {currentConfig.search_type})
                      </span>
                    )}
                  </label>
                  <select
                    value={currentConfig.property_type}
                    onChange={(e) => updateConfig(activePlatform, 'property_type', e.target.value)}
                    disabled={isRunning}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                  >
                    {getFilteredPropertyTypes().map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  {activePlatform === 'magicbricks' && (
                    <p className="text-xs text-gray-500 mt-1">
                      {currentConfig.search_type === 'buy' 
                        ? 'Buy: Flat, House, Villa, Plot, Penthouse, Builder Floor, Studio' 
                        : 'Rent: Flat, House, Villa, PG, Co-living'}
                    </p>
                  )}
                </div>

                {/* Max Items */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    📊 Max Items <span className="text-red-500">*</span>
                  </label>
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
                  <p className="text-xs text-gray-500 mt-1">Recommended: 500 for balance</p>
                </div>

                {/* Min Bedrooms */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    🛏️ Min Bedrooms
                  </label>
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

                {/* Max Bedrooms */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    🛏️ Max Bedrooms
                  </label>
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

              {/* Price Range Presets */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  💰 Price Range (Quick Select)
                </label>
                <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
                  {(currentConfig.search_type === 'rent' ? options.price_ranges.rent : options.price_ranges.buy).map((range, idx) => (
                    <button
                      key={idx}
                      onClick={() => applyPriceRange(range)}
                      disabled={isRunning}
                      className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                        currentConfig.min_price === range.min && currentConfig.max_price === range.max
                          ? 'bg-indigo-100 border-indigo-500 text-indigo-700 font-semibold'
                          : 'bg-white border-gray-300 text-gray-700 hover:border-indigo-300'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {range.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Price Range */}
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Min Price (₹)
                  </label>
                  <input
                    type="number"
                    placeholder="e.g., 5000000"
                    value={currentConfig.min_price || ''}
                    onChange={(e) => updateConfig(activePlatform, 'min_price', e.target.value ? parseInt(e.target.value) : null)}
                    disabled={isRunning}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                  />
                  {currentConfig.min_price && (
                    <p className="text-xs text-gray-500 mt-1">{formatPrice(currentConfig.min_price)}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Max Price (₹)
                  </label>
                  <input
                    type="number"
                    placeholder="e.g., 50000000"
                    value={currentConfig.max_price || ''}
                    onChange={(e) => updateConfig(activePlatform, 'max_price', e.target.value ? parseInt(e.target.value) : null)}
                    disabled={isRunning}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                  />
                  {currentConfig.max_price && (
                    <p className="text-xs text-gray-500 mt-1">{formatPrice(currentConfig.max_price)}</p>
                  )}
                </div>
              </div>

              {/* Platform-specific options */}
              {activePlatform === 'magicbricks' && platformOptions.magicbricks && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <label className="block text-sm font-medium text-blue-900 mb-2">
                    🏠 MagicBricks Specific: Proxy Settings
                  </label>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={currentConfig.proxy_enabled}
                        onChange={(e) => updateConfig(activePlatform, 'proxy_enabled', e.target.checked)}
                        disabled={isRunning}
                        className="rounded text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-blue-800">Enable Proxy</span>
                    </label>
                    {currentConfig.proxy_enabled && (
                      <select
                        value={currentConfig.proxy_country}
                        onChange={(e) => updateConfig(activePlatform, 'proxy_country', e.target.value)}
                        disabled={isRunning}
                        className="px-3 py-1 text-sm border border-blue-300 rounded-lg bg-white"
                      >
                        {platformOptions.magicbricks.proxy_countries.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>
              )}

              {activePlatform === '99acres' && platformOptions['99acres'] && (
                <div className="mt-4 p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <label className="block text-sm font-medium text-orange-900 mb-2">
                    🏗️ 99acres Specific: Sort By
                  </label>
                  <select
                    value={currentConfig.sort_by || 'relevance'}
                    onChange={(e) => updateConfig(activePlatform, 'sort_by', e.target.value)}
                    disabled={isRunning}
                    className="w-full px-3 py-2 border border-orange-300 rounded-lg bg-white"
                  >
                    {platformOptions['99acres'].sort_options.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Custom URL Input */}
              <div className="mt-4 p-4 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  <div className="flex-1">
                    <h4 className="font-semibold text-purple-900 mb-1">Custom URL (Optional)</h4>
                    <p className="text-xs text-purple-700 mb-2">
                      Paste a direct link from {getPlatformName(activePlatform)} to scrape that specific search
                    </p>
                  </div>
                </div>
                <input
                  type="text"
                  placeholder={`e.g., ${getUrlPreview()}`}
                  value={currentConfig.custom_url}
                  onChange={(e) => updateConfig(activePlatform, 'custom_url', e.target.value)}
                  disabled={isRunning}
                  className="w-full px-3 py-2 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 text-sm"
                />
                {currentConfig.custom_url && (
                  <div className="mt-2 flex items-center gap-2">
                    <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs text-green-700 font-medium">Custom URL will override auto-generated search</span>
                  </div>
                )}
              </div>
            </div>

            {/* Data Quality Notice */}
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="font-semibold text-green-900 mb-1">Data Quality Assurance</h4>
                  <ul className="text-sm text-green-800 space-y-1">
                    <li>✅ All properties validated for coordinates</li>
                    <li>✅ Duplicate detection and removal</li>
                    <li>✅ Price and area validation</li>
                    <li>✅ Invalid entries automatically filtered</li>
                  </ul>
                </div>
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
                  Stop Scraping
                </button>
              )}
              <button
                onClick={fetchAllStatus}
                className="px-4 py-3 border-2 border-indigo-300 rounded-lg text-indigo-600 hover:bg-indigo-50 transition-colors font-semibold"
                title="Refresh Status"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              {!showUrlPreview && (
                <button
                  onClick={() => setShowUrlPreview(true)}
                  className="px-4 py-3 border-2 border-blue-300 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors font-semibold"
                  title="Show URL Preview"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        )}

        {/* HISTORY VIEW - Same as before */}
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
                  <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-100 hover:border-indigo-300 transition-colors">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-gray-800 flex items-center gap-2">
                          <span className="text-lg">{getPlatformIcon(entry.platform)}</span>
                          {getPlatformName(entry.platform)} - {entry.location} - {entry.category}
                        </div>
                        <div className="text-sm text-gray-600 mt-1 flex items-center gap-3">
                          <span>📦 {entry.items_scraped} scraped</span>
                          <span className="text-green-600">✅ {entry.items_valid} valid</span>
                          <span className="text-blue-600">➕ {entry.items_new} new</span>
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

        {/* STATS VIEW - Same as before */}
        {activeView === 'stats' && stats && (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg p-6 text-white">
              <div className="text-4xl font-bold">{stats.total_properties?.toLocaleString() || 0}</div>
              <div className="text-indigo-100 mt-1">Total Properties in Database</div>
            </div>

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
          <span>Quality-first scraping from {platforms.length} platforms</span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            Data validated & deduplicated
          </span>
        </div>
      </div>
    </div>
  );
};

export default EnhancedMultiSourceScraper;
