import React, { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../apiConfig';

const PropertyTypeScraper = () => {
  const [platforms, setPlatforms] = useState([]);
  const [activePlatform, setActivePlatform] = useState('magicbricks');
  const [allStatus, setAllStatus] = useState({});
  const [allJobs, setAllJobs] = useState({});  // Track all jobs for per-property-type status
  const [configLoaded, setConfigLoaded] = useState(false);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('scrape');
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importRunId, setImportRunId] = useState('');
  const [importPlatform, setImportPlatform] = useState('magicbricks');

  // Default configuration structure
  const getDefaultConfig = () => ({
    magicbricks: {
      residential: {
        location: 'Bangalore',
        buy: {
          flat: { max_items: 500, custom_url: '' },
          'house-villa': { max_items: 500, custom_url: '' },
          plot: { max_items: 500, custom_url: '' }
        },
        rent: {
          flat: { max_items: 500, custom_url: '' },
          'house-villa': { max_items: 500, custom_url: '' },
          plot: { max_items: 500, custom_url: '' }
        },
        pg: {
          pg: { max_items: 500, custom_url: '' },
          coliving: { max_items: 500, custom_url: '' }
        }
      },
      commercial: {
        location: 'Bangalore',
        buy: {
          office: { max_items: 500, custom_url: '' },
          shop: { max_items: 500, custom_url: '' },
          'commercial-land': { max_items: 500, custom_url: '' },
          warehouse: { max_items: 500, custom_url: '' },
          'industrial-building': { max_items: 500, custom_url: '' },
          'industrial-shed': { max_items: 500, custom_url: '' },
          'agricultural-land': { max_items: 500, custom_url: '' },
          'farm-house': { max_items: 500, custom_url: '' }
        },
        lease: {
          office: { max_items: 500, custom_url: '' },
          shop: { max_items: 500, custom_url: '' },
          'commercial-land': { max_items: 500, custom_url: '' },
          warehouse: { max_items: 500, custom_url: '' },
          'industrial-building': { max_items: 500, custom_url: '' },
          'industrial-shed': { max_items: 500, custom_url: '' },
          'agricultural-land': { max_items: 500, custom_url: '' },
          'farm-house': { max_items: 500, custom_url: '' }
        }
      }
    },
    housing: {
      residential: {
        location: 'Bangalore',
        buy: {
          apartment: { max_items: 500, custom_url: '' },
          'independent-house': { max_items: 500, custom_url: '' },
          'independent-floor': { max_items: 500, custom_url: '' },
          plot: { max_items: 500, custom_url: '' },
          studio: { max_items: 500, custom_url: '' },
          duplex: { max_items: 500, custom_url: '' },
          penthouse: { max_items: 500, custom_url: '' },
          villa: { max_items: 500, custom_url: '' },
          'agricultural-land': { max_items: 500, custom_url: '' }
        },
        rent: {
          apartment: { max_items: 500, custom_url: '' },
          'independent-house': { max_items: 500, custom_url: '' },
          'independent-floor': { max_items: 500, custom_url: '' },
          studio: { max_items: 500, custom_url: '' },
          duplex: { max_items: 500, custom_url: '' },
          penthouse: { max_items: 500, custom_url: '' },
          villa: { max_items: 500, custom_url: '' }
        },
        pg: {
          pg: { max_items: 500, custom_url: '' }
        },
        flatmates: {
          flatmates: { max_items: 500, custom_url: '' }
        }
      },
      commercial: {
        location: 'Bangalore',
        buy: {
          'ready-office': { max_items: 500, custom_url: '' },
          'bare-shell-office': { max_items: 500, custom_url: '' },
          shop: { max_items: 500, custom_url: '' },
          showroom: { max_items: 500, custom_url: '' },
          'commercial-plot': { max_items: 500, custom_url: '' },
          warehouse: { max_items: 500, custom_url: '' },
          other: { max_items: 500, custom_url: '' }
        },
        lease: {
          'ready-office': { max_items: 500, custom_url: '' },
          'bare-shell-office': { max_items: 500, custom_url: '' },
          shop: { max_items: 500, custom_url: '' },
          showroom: { max_items: 500, custom_url: '' },
          'commercial-plot': { max_items: 500, custom_url: '' },
          warehouse: { max_items: 500, custom_url: '' },
          other: { max_items: 500, custom_url: '' }
        }
      }
    },
    nobroker: {
      residential: {
        location: 'Bangalore',
        buy: {
          'full-house': { max_items: 500, custom_url: '' },
          'land-plot': { max_items: 500, custom_url: '' }
        },
        rent: {
          'full-house': { max_items: 500, custom_url: '' },
          'pg-hostel': { max_items: 500, custom_url: '' },
          flatmates: { max_items: 500, custom_url: '' }
        }
      },
      commercial: {
        location: 'Bangalore',
        buy: {
          'office-space': { max_items: 500, custom_url: '' },
          'co-working': { max_items: 500, custom_url: '' },
          shop: { max_items: 500, custom_url: '' },
          showroom: { max_items: 500, custom_url: '' },
          'industrial-building': { max_items: 500, custom_url: '' },
          'industrial-shed': { max_items: 500, custom_url: '' },
          'godown-warehouse': { max_items: 500, custom_url: '' },
          'other-business': { max_items: 500, custom_url: '' },
          'restaurant-cafe': { max_items: 500, custom_url: '' }
        },
        rent: {
          'office-space': { max_items: 500, custom_url: '' },
          'co-working': { max_items: 500, custom_url: '' },
          shop: { max_items: 500, custom_url: '' },
          showroom: { max_items: 500, custom_url: '' },
          'industrial-building': { max_items: 500, custom_url: '' },
          'industrial-shed': { max_items: 500, custom_url: '' },
          'godown-warehouse': { max_items: 500, custom_url: '' },
          'other-business': { max_items: 500, custom_url: '' },
          'restaurant-cafe': { max_items: 500, custom_url: '' }
        }
      }
    },
    '99acres': {
      residential: {
        location: 'Bangalore',
        buy: {
          'flat-apartment': { max_items: 500, custom_url: '' },
          'builder-floor': { max_items: 500, custom_url: '' },
          'independent-house-villa': { max_items: 500, custom_url: '' },
          'residential-land': { max_items: 500, custom_url: '' },
          'studio-apartment': { max_items: 500, custom_url: '' },
          'farm-house': { max_items: 500, custom_url: '' },
          'serviced-apartments': { max_items: 500, custom_url: '' },
          'other-residential': { max_items: 500, custom_url: '' }
        },
        rent: {
          'flat-apartment': { max_items: 500, custom_url: '' },
          'builder-floor': { max_items: 500, custom_url: '' },
          'independent-house-villa': { max_items: 500, custom_url: '' },
          'residential-land': { max_items: 500, custom_url: '' },
          'studio-apartment': { max_items: 500, custom_url: '' },
          'farm-house': { max_items: 500, custom_url: '' },
          'serviced-apartments': { max_items: 500, custom_url: '' },
          'other-residential': { max_items: 500, custom_url: '' }
        }
      },
      commercial: {
        location: 'Bangalore',
        buy: {
          'ready-to-move-office': { max_items: 500, custom_url: '' },
          'bare-shell-office': { max_items: 500, custom_url: '' },
          'shop-retail': { max_items: 500, custom_url: '' },
          'commercial-land': { max_items: 500, custom_url: '' },
          'agricultural-land': { max_items: 500, custom_url: '' },
          'industrial-land': { max_items: 500, custom_url: '' },
          'warehouse': { max_items: 500, custom_url: '' },
          'cold-storage': { max_items: 500, custom_url: '' },
          'factory-manufacturing': { max_items: 500, custom_url: '' },
          'hotel-resort': { max_items: 500, custom_url: '' },
          'other-commercial': { max_items: 500, custom_url: '' }
        },
        lease: {
          'office-space': { max_items: 500, custom_url: '' },
          'ready-to-move-office': { max_items: 500, custom_url: '' },
          'bare-shell-office': { max_items: 500, custom_url: '' },
          'co-working-office': { max_items: 500, custom_url: '' },
          'shop-retail': { max_items: 500, custom_url: '' },
          'other-commercial-space': { max_items: 500, custom_url: '' },
          'factory-manufacturing': { max_items: 500, custom_url: '' },
          'residential-plot': { max_items: 500, custom_url: '' },
          'commercial-plot': { max_items: 500, custom_url: '' },
          'agricultural-land': { max_items: 500, custom_url: '' },
          'industrial-plot': { max_items: 500, custom_url: '' }
        }
      }
    }
  });

  // Helper to deep merge configs while preserving user data (custom_url, max_items)
  const mergeConfigs = (defaultConfig, savedConfig) => {
    if (!savedConfig) return defaultConfig;
    
    const merged = { ...defaultConfig };
    
    // For each platform
    Object.keys(defaultConfig).forEach(platform => {
      merged[platform] = { ...defaultConfig[platform] };
      
      // For each category (residential, commercial)
      Object.keys(defaultConfig[platform]).forEach(category => {
        if (category === 'location') {
          // Preserve location
          merged[platform][category] = savedConfig[platform]?.[category] || defaultConfig[platform][category];
        } else {
          merged[platform][category] = { ...defaultConfig[platform][category] };
          
          // For each search type (buy, rent, pg, etc)
          Object.keys(defaultConfig[platform][category]).forEach(searchType => {
            if (searchType === 'location') return;
            
            merged[platform][category][searchType] = { ...defaultConfig[platform][category][searchType] };
            
            // For each property type
            Object.keys(defaultConfig[platform][category][searchType]).forEach(propertyType => {
              const defaultProp = defaultConfig[platform][category][searchType][propertyType];
              const savedProp = savedConfig[platform]?.[category]?.[searchType]?.[propertyType];
              
              // Preserve custom_url and max_items if they exist
              merged[platform][category][searchType][propertyType] = {
                max_items: savedProp?.max_items || defaultProp.max_items,
                custom_url: savedProp?.custom_url || defaultProp.custom_url
              };
            });
          });
        }
      });
    });
    
    return merged;
  };

  // Load from backend JSON file or use defaults
  const loadConfigFromStorage = () => {
    // Return defaults initially, will be replaced by useEffect fetch
    return getDefaultConfig();
  };

  // Property type configurations with individual max items
  const [propertyTypeConfigs, setPropertyTypeConfigs] = useState(loadConfigFromStorage);

  const [propertyCategory, setPropertyCategory] = useState('residential');
  const [searchType, setSearchType] = useState('buy');

  // Property type metadata
  const propertyTypeInfo = {
    // Residential - MagicBricks
    flat: { icon: '🏢', label: 'Flat', category: 'Residential' },
    'house-villa': { icon: '🏠', label: 'House/Villa', category: 'Residential' },
    plot: { icon: '🌳', label: 'Plot', category: 'Residential' },
    pg: { icon: '🛏️', label: 'PG (Paying Guest)', category: 'Residential' },
    coliving: { icon: '🏘️', label: 'Co-living Space', category: 'Residential' },
    
    // Residential - Housing.com
    apartment: { icon: '🏢', label: 'Apartment', category: 'Residential' },
    'independent-house': { icon: '🏠', label: 'Independent House', category: 'Residential' },
    'independent-floor': { icon: '🏘️', label: 'Independent Floor', category: 'Residential' },
    studio: { icon: '🏙️', label: 'Studio', category: 'Residential' },
    duplex: { icon: '🏚️', label: 'Duplex', category: 'Residential' },
    penthouse: { icon: '🌆', label: 'Penthouse', category: 'Residential' },
    villa: { icon: '🏡', label: 'Villa', category: 'Residential' },
    flatmates: { icon: '👥', label: 'Flatmates', category: 'Residential' },
    
    // Commercial - MagicBricks
    office: { icon: '💼', label: 'Office Space', category: 'Commercial' },
    shop: { icon: '🏪', label: 'Shop/Showroom', category: 'Commercial' },
    'commercial-land': { icon: '🏗️', label: 'Commercial Land', category: 'Commercial' },
    warehouse: { icon: '📦', label: 'Warehouse/Godown', category: 'Commercial' },
    'industrial-building': { icon: '🏭', label: 'Industrial Building', category: 'Commercial' },
    'industrial-shed': { icon: '🏚️', label: 'Industrial Shed', category: 'Commercial' },
    
    // Commercial - Housing.com
    'ready-office': { icon: '💼', label: 'Ready to Use Office', category: 'Commercial' },
    'bare-shell-office': { icon: '🏢', label: 'Bare Shell Office', category: 'Commercial' },
    showroom: { icon: '🏬', label: 'Showroom', category: 'Commercial' },
    'commercial-plot': { icon: '🏗️', label: 'Commercial Plot', category: 'Commercial' },
    other: { icon: '🏛️', label: 'Other Commercial', category: 'Commercial' },
    
    // Residential - NoBroker
    'full-house': { icon: '🏠', label: 'Full House', category: 'Residential' },
    'land-plot': { icon: '🌳', label: 'Land/Plot', category: 'Residential' },
    'pg-hostel': { icon: '🛏️', label: 'PG/Hostel', category: 'Residential' },
    
    // Commercial - NoBroker
    'office-space': { icon: '💼', label: 'Office Space', category: 'Commercial' },
    'co-working': { icon: '👥', label: 'Co-Working', category: 'Commercial' },
    'godown-warehouse': { icon: '📦', label: 'Godown/Warehouse', category: 'Commercial' },
    'other-business': { icon: '🏢', label: 'Other Business', category: 'Commercial' },
    'restaurant-cafe': { icon: '☕', label: 'Restaurant/Cafe', category: 'Commercial' },
    
    // Residential - 99acres
    'flat-apartment': { icon: '🏢', label: 'Flat/Apartment', category: 'Residential' },
    'builder-floor': { icon: '🏘️', label: 'Independent/Builder Floor', category: 'Residential' },
    'independent-house-villa': { icon: '🏠', label: 'Independent House/Villa', category: 'Residential' },
    'residential-land': { icon: '🌳', label: 'Residential Land', category: 'Residential' },
    'studio-apartment': { icon: '🏙️', label: '1 RK/Studio Apartment', category: 'Residential' },
    'serviced-apartments': { icon: '🏨', label: 'Serviced Apartments', category: 'Residential' },
    'other-residential': { icon: '🏛️', label: 'Other Residential', category: 'Residential' },
    
    // Commercial - 99acres
    'ready-to-move-office': { icon: '💼', label: 'Ready to Move Office', category: 'Commercial' },
    'bare-shell-office-99': { icon: '🏢', label: 'Bare Shell Office', category: 'Commercial' },
    'shop-retail': { icon: '🏪', label: 'Shop & Retail', category: 'Commercial' },
    'commercial-land-99': { icon: '🏗️', label: 'Commercial Land', category: 'Commercial' },
    'industrial-land': { icon: '🏭', label: 'Industrial Land/Plots', category: 'Commercial' },
    'cold-storage': { icon: '❄️', label: 'Cold Storage', category: 'Commercial' },
    'factory-manufacturing': { icon: '🏭', label: 'Factory & Manufacturing', category: 'Commercial' },
    'hotel-resort': { icon: '🏨', label: 'Hotel/Resort', category: 'Commercial' },
    'other-commercial': { icon: '🏛️', label: 'Other Commercial', category: 'Commercial' },
    'co-working-office': { icon: '👥', label: 'Co-Working Office', category: 'Commercial' },
    'other-commercial-space': { icon: '🏢', label: 'Other Commercial Space', category: 'Commercial' },
    'residential-plot': { icon: '🌳', label: 'Residential Plot/Land', category: 'Commercial' },
    'commercial-plot-99': { icon: '🏗️', label: 'Commercial Plot/Land', category: 'Commercial' },
    'industrial-plot': { icon: '🏭', label: 'Industrial Plot/Land', category: 'Commercial' },
    
    // Other
    'agricultural-land': { icon: '🌾', label: 'Agricultural Land', category: 'Other' },
    'farm-house': { icon: '🏡', label: 'Farm House', category: 'Other' }
  };

  const locations = [
    'Bangalore', 'Mumbai', 'Delhi', 'New-Delhi', 'Hyderabad', 
    'Chennai', 'Pune', 'Kolkata', 'Ahmedabad', 'Gurgaon', 'Noida', 'Goa'
  ];

  // Save configs to backend JSON file whenever they change
  useEffect(() => {
    if (!configLoaded) return;
    const saveConfig = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/scrape/config/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(propertyTypeConfigs)
        });
        if (res.ok) {
          console.log('✅ Configuration saved to file');
        }
      } catch (err) {
        console.error('Failed to save configs to file:', err);
      }
    };
    
    // Debounce saves to avoid too many writes
    const timer = setTimeout(saveConfig, 1000);
    return () => clearTimeout(timer);
  }, [propertyTypeConfigs, configLoaded]);

  // Load configuration from backend on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/scrape/config/load`);
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.config) {
            console.log('✅ Configuration loaded from file');
            const defaults = getDefaultConfig();
            const merged = mergeConfigs(defaults, data.config);
            setPropertyTypeConfigs(merged);
          }
        }
      } catch (err) {
        console.error('Failed to load config from file:', err);
      } finally {
        setConfigLoaded(true);
      }
    };
    loadConfig();
  }, []);

  // Fetch platforms
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

  // Poll status - now includes all_jobs for per-property-type tracking
  const fetchAllStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scrape/status`);
      if (res.ok) {
        const data = await res.json();
        console.log('📊 Status poll response:', data);
        setAllStatus(data.platforms || {});
        setAllJobs(data.all_jobs || {});  // Store all jobs for per-property-type status
        
        // Log current platform status
        if (data.platforms && data.platforms[activePlatform]) {
          const platformStatus = data.platforms[activePlatform];
          console.log(`🔍 ${activePlatform} status:`, platformStatus.status, `${platformStatus.running_jobs} running jobs`);
        }
        
        setError(null);
      }
    } catch (err) {
      console.error('❌ Status poll failed:', err);
      setError('Failed to fetch status');
    }
  }, [activePlatform]);

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

  // Update property type config
  const updatePropertyTypeConfig = (propertyType, field, value) => {
    setPropertyTypeConfigs(prev => ({
      ...prev,
      [activePlatform]: {
        ...prev[activePlatform],
        [propertyCategory]: {
          ...prev[activePlatform][propertyCategory],
          [searchType]: {
            ...prev[activePlatform][propertyCategory][searchType],
            [propertyType]: {
              ...prev[activePlatform][propertyCategory][searchType][propertyType],
              [field]: value
            }
          }
        }
      }
    }));
  };

  // Update location
  const updateLocation = (location) => {
    setPropertyTypeConfigs(prev => ({
      ...prev,
      [activePlatform]: {
        ...prev[activePlatform],
        [propertyCategory]: {
          ...prev[activePlatform][propertyCategory],
          location
        }
      }
    }));
  };

  // Start scrape for specific property type
  const handleStart = async (propertyType) => {
    console.log('🚀 Start scraping clicked for:', propertyType);
    
    const typeConfig = propertyTypeConfigs[activePlatform]?.[propertyCategory]?.[searchType]?.[propertyType];
    if (!typeConfig) {
      console.error('❌ Type config not found:', { activePlatform, propertyCategory, searchType, propertyType });
      setError('Configuration not found for this property type');
      return;
    }

    const config = {
      location: propertyTypeConfigs[activePlatform][propertyCategory].location,
      property_category: propertyCategory,
      search_type: searchType,
      property_type: propertyType,
      max_items: typeConfig.max_items,
      custom_url: typeConfig.custom_url || ''
    };

    console.log('📤 Sending config to backend:', config);
    console.log('🔗 API URL:', `${API_BASE}/api/scrape/${activePlatform}/start`);

    try {
      setError(null);
      const res = await fetch(`${API_BASE}/api/scrape/${activePlatform}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      console.log('📥 Response status:', res.status, res.statusText);
      
      const data = await res.json();
      console.log('📥 Response data:', data);
      
      if (!res.ok) {
        console.error('❌ Request failed:', data);
        throw new Error(data.detail || 'Failed to start');
      }
      
      console.log('✅ Scrape started successfully');
      fetchAllStatus();
    } catch (err) {
      console.error('❌ Error starting scrape:', err);
      setError(err.message);
    }
  };

  // Stop scrape - can stop all platform jobs or a specific job
  const handleStop = async (jobId = null) => {
    try {
      let url = `${API_BASE}/api/scrape/${activePlatform}/stop`;
      if (jobId) {
        url = `${API_BASE}/api/scrape/job/${jobId}/stop`;
      }
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to stop');
      }
      fetchAllStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  // Import external Apify run
  const handleImportRun = async () => {
    if (!importRunId.trim()) {
      setError('Please enter a run ID');
      return;
    }

    try {
      setError(null);
      const res = await fetch(`${API_BASE}/api/scrape/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: importRunId.trim(),
          platform: importPlatform,
          config: {
            location: 'Imported',
            property_category: 'residential',
            search_type: 'buy',
            property_type: 'imported'
          }
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to import run');
      }

      setShowImportDialog(false);
      setImportRunId('');
      fetchAllStatus();
      alert(`✅ Successfully imported run! Job ID: ${data.job_id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  // Helper to generate job ID (must match backend logic)
  const makeJobId = (platform, category, searchType, propertyType) => {
    const safeSlug = (s) => (s || 'unknown').toString().trim().toLowerCase().replace(/[\/\\\s]/g, '-');
    return `${safeSlug(platform)}_${safeSlug(category)}_${safeSlug(searchType)}_${safeSlug(propertyType)}`;
  };

  // Get job status for a specific property type
  const getJobStatus = (propertyType) => {
    const jobId = makeJobId(activePlatform, propertyCategory, searchType, propertyType);
    return allJobs[jobId] || null;
  };

  // Check if a specific property type is currently being scraped
  const isPropertyTypeRunning = (propertyType) => {
    const job = getJobStatus(propertyType);
    return job && (job.status === 'running' || job.status === 'starting');
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
    return platform?.icon || '';
  };

  const getPlatformName = (platformId) => {
    const platform = platforms.find(p => p.id === platformId);
    return platform?.name || platformId;
  };

  // Get available search types based on category - must be defined before useEffect
  const getSearchTypes = () => {
    if (propertyCategory === 'residential') {
      // Housing.com has flatmates option, MagicBricks doesn't
      if (activePlatform === 'housing') {
        return ['buy', 'rent', 'pg', 'flatmates'];
      }
      return ['buy', 'rent', 'pg'];
    } else if (propertyCategory === 'commercial') {
      return ['buy', 'lease'];
    }
    return ['buy'];
  };

  // Reset search type when category changes - must be before conditional returns
  useEffect(() => {
    const validTypes = getSearchTypes();
    if (!validTypes.includes(searchType)) {
      setSearchType(validTypes[0]);
    }
  }, [propertyCategory, searchType]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-32 bg-gray-100 rounded"></div>
      </div>
    );
  }

  const currentStatus = allStatus[activePlatform] || {};
  const runningJobs = currentStatus.running_jobs || 0;
  const platformJobs = currentStatus.jobs || [];
  const isAnyRunning = runningJobs > 0;
  const currentConfig = propertyTypeConfigs[activePlatform]?.[propertyCategory] || { location: 'Bangalore', buy: {}, rent: {}, pg: {}, lease: {}, flatmates: {} };
  const availableTypes = Object.keys(currentConfig[searchType] || {});
  
  // Debug logging
  console.log('🔍 Debug Info:', {
    activePlatform,
    propertyCategory,
    searchType,
    availableTypes,
    hasConfig: !!propertyTypeConfigs[activePlatform],
    hasCategoryConfig: !!propertyTypeConfigs[activePlatform]?.[propertyCategory],
    hasSearchTypeConfig: !!propertyTypeConfigs[activePlatform]?.[propertyCategory]?.[searchType]
  });

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          Property Type Scraper
        </h2>
        <p className="text-indigo-100 text-sm mt-1">Scrape each property type individually with custom settings</p>
      </div>

      {/* Platform Tabs */}
      <div className="border-b border-gray-200 bg-gray-50">
        <nav className="flex -mb-px overflow-x-auto">
          {platforms.map(platform => {
            const status = allStatus[platform.id] || {};
            const isActive = activePlatform === platform.id;
            const platformRunningJobs = status.running_jobs || 0;
            const isPlatformRunning = platformRunningJobs > 0;

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
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                      <span className="text-xs text-blue-600">{platformRunningJobs}</span>
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* View Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex -mb-px px-6 justify-between items-center">
          <div className="flex">
            {[
              { id: 'scrape', label: 'Scrape by Type', icon: '' },
              { id: 'history', label: 'History', icon: '' },
              { id: 'stats', label: 'Stats', icon: '' }
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
          </div>
          <button
            onClick={() => setShowImportDialog(true)}
            className="my-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-semibold flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
            </svg>
            Import Apify Run
          </button>
        </nav>
      </div>

      {/* Import Dialog */}
      {showImportDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-800">Import Apify Run</h3>
              <button
                onClick={() => setShowImportDialog(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Paste a run ID from Apify website to track and download it in this app.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Platform
                </label>
                <select
                  value={importPlatform}
                  onChange={(e) => setImportPlatform(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  {platforms.map(p => (
                    <option key={p.id} value={p.id}>{p.icon} {p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Run ID
                </label>
                <input
                  type="text"
                  value={importRunId}
                  onChange={(e) => setImportRunId(e.target.value)}
                  placeholder="e.g., abc123def456"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Find this in the Apify run URL or run details page
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowImportDialog(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImportRun}
                  className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold"
                >
                  Import
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
            {/* Global Settings */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
              <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
                Global Settings
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Property Category */}
                <div>
                  <label className="block text-sm font-medium text-blue-900 mb-2">
                    🏘️ Property Category
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPropertyCategory('residential')}
                      className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-all ${
                        propertyCategory === 'residential'
                          ? 'bg-green-600 text-white shadow-lg'
                          : 'bg-white text-gray-700 border border-gray-300 hover:border-green-300'
                      }`}
                    >
                      🏠 Residential
                    </button>
                    <button
                      onClick={() => setPropertyCategory('commercial')}
                      className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-all ${
                        propertyCategory === 'commercial'
                          ? 'bg-orange-600 text-white shadow-lg'
                          : 'bg-white text-gray-700 border border-gray-300 hover:border-orange-300'
                      }`}
                    >
                      🏢 Commercial
                    </button>
                  </div>
                </div>

                {/* Search Type - Dynamic based on category */}
                <div>
                  <label className="block text-sm font-medium text-blue-900 mb-2">
                    🔍 Search Type
                  </label>
                  <div className={`grid gap-2 ${
                    activePlatform === 'housing' && propertyCategory === 'residential' 
                      ? 'grid-cols-4' 
                      : propertyCategory === 'residential' 
                        ? 'grid-cols-3' 
                        : 'grid-cols-2'
                  }`}>
                    {getSearchTypes().map(type => {
                      const typeConfig = {
                        buy: { icon: '', label: 'Buy', color: 'blue' },
                        rent: { icon: '', label: 'Rent', color: 'indigo' },
                        pg: { icon: '🛏️', label: 'PG', color: 'purple' },
                        flatmates: { icon: '👥', label: 'Flatmates', color: 'pink' },
                        lease: { icon: '📋', label: 'Lease', color: 'teal' }
                      }[type];

                      return (
                        <button
                          key={type}
                          onClick={() => setSearchType(type)}
                          className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                            searchType === type
                              ? `bg-${typeConfig.color}-600 text-white shadow-lg`
                              : `bg-white text-gray-700 border border-gray-300 hover:border-${typeConfig.color}-300`
                          }`}
                        >
                          {typeConfig.icon} {typeConfig.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Location */}
                <div>
                  <label className="block text-sm font-medium text-blue-900 mb-2">
                    📍 Location
                  </label>
                  <select
                    value={currentConfig.location}
                    onChange={(e) => updateLocation(e.target.value)}
                    disabled={isAnyRunning}
                    className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 bg-white"
                  >
                    {locations.map(loc => (
                      <option key={loc} value={loc}>{loc}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Running Jobs Summary */}
            {isAnyRunning && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></div>
                    <span className="font-semibold text-blue-900">
                      {runningJobs} Active Job{runningJobs > 1 ? 's' : ''} on {getPlatformName(activePlatform)}
                    </span>
                  </div>
                  <button
                    onClick={() => handleStop()}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-semibold text-sm"
                  >
                    Stop All ({runningJobs})
                  </button>
                </div>
                {/* Show individual running jobs */}
                <div className="space-y-2">
                  {platformJobs.filter(j => j.status === 'running' || j.status === 'starting').map(job => (
                    <div key={job.job_id} className="bg-white rounded-lg p-3 border border-blue-100">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium text-blue-900 text-sm">
                          {propertyTypeInfo[job.property_type]?.icon || '📦'} {propertyTypeInfo[job.property_type]?.label || job.property_type}
                        </span>
                        <button
                          onClick={() => handleStop(job.job_id)}
                          className="px-2 py-1 text-xs bg-red-100 text-red-600 rounded hover:bg-red-200 transition-colors"
                        >
                          Stop
                        </button>
                      </div>
                      <div className="text-xs text-blue-700 mb-1">{job.message}</div>
                      <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${job.progress_percent || 0}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-blue-600 mt-1">
                        <span>📦 {job.items_found || 0} found</span>
                        <span>⏱️ {formatTime(job.elapsed_seconds)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Property Type Cards */}
            <div>
              <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Property Types - Scrape One by One
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {availableTypes.map(propertyType => {
                  const info = propertyTypeInfo[propertyType];
                  const typeConfig = currentConfig[searchType][propertyType];
                  
                  return (
                    <div key={propertyType} className="bg-gradient-to-br from-gray-50 to-white rounded-lg border-2 border-gray-200 hover:border-indigo-300 transition-all p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <span className="text-3xl">{info.icon}</span>
                          <div>
                            <h4 className="font-bold text-gray-800">{info.label}</h4>
                            <span className="text-xs text-gray-500">{info.category}</span>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {/* Max Items */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            📊 Max Items
                          </label>
                          <input
                            type="number"
                            min="50"
                            max="10000"
                            step="50"
                            value={typeConfig.max_items}
                            onChange={(e) => updatePropertyTypeConfig(propertyType, 'max_items', parseInt(e.target.value))}
                            disabled={isPropertyTypeRunning(propertyType)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                          />
                        </div>

                        {/* Custom URL */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1 flex items-center gap-2">
                            🔗 Custom URL (Optional)
                            {typeConfig.custom_url && (
                              <span className="text-green-600 text-xs flex items-center gap-1">
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Auto-saved
                              </span>
                            )}
                          </label>
                          <input
                            type="text"
                            placeholder="Paste custom URL..."
                            value={typeConfig.custom_url}
                            onChange={(e) => updatePropertyTypeConfig(propertyType, 'custom_url', e.target.value)}
                            disabled={isPropertyTypeRunning(propertyType)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                          />
                        </div>

                        {/* Job Status / Start Button */}
                        {(() => {
                          const jobStatus = getJobStatus(propertyType);
                          const isThisRunning = isPropertyTypeRunning(propertyType);
                          
                          if (isThisRunning && jobStatus) {
                            return (
                              <div className="space-y-2">
                                <div className="bg-blue-50 rounded-lg p-2">
                                  <div className="flex justify-between text-xs text-blue-700 mb-1">
                                    <span>{jobStatus.message}</span>
                                    <span className="font-bold">{Math.round(jobStatus.progress_percent || 0)}%</span>
                                  </div>
                                  <div className="w-full bg-blue-200 rounded-full h-2">
                                    <div
                                      className="bg-blue-500 h-2 rounded-full transition-all"
                                      style={{ width: `${jobStatus.progress_percent || 0}%` }}
                                    ></div>
                                  </div>
                                  <div className="text-xs text-blue-600 mt-1">
                                    📦 {jobStatus.items_found || 0} found | ⏱️ {formatTime(jobStatus.elapsed_seconds)}
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleStop(jobStatus.job_id)}
                                  className="w-full bg-red-500 text-white py-2 px-4 rounded-lg font-semibold hover:bg-red-600 transition-all flex items-center justify-center gap-2"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                                  </svg>
                                  Stop Scraping
                                </button>
                              </div>
                            );
                          }
                          
                          // Show completed/failed/resumable status
                          if (jobStatus && (jobStatus.status === 'completed' || jobStatus.status === 'failed' || jobStatus.status === 'resumable')) {
                            const isCompleted = jobStatus.status === 'completed';
                            const isResumable = jobStatus.status === 'resumable';
                            const isFailed = jobStatus.status === 'failed';
                            
                            return (
                              <div className="space-y-2">
                                <div className={`text-xs p-2 rounded-lg ${
                                  isCompleted ? 'bg-green-50 text-green-700' : 
                                  isResumable ? 'bg-yellow-50 text-yellow-700' : 
                                  'bg-red-50 text-red-700'
                                }`}>
                                  {isCompleted ? '✅' : isResumable ? '⏸️' : '❌'} {jobStatus.message}
                                </div>
                                <button
                                  onClick={() => handleStart(propertyType)}
                                  className={`w-full py-2 px-4 rounded-lg font-semibold transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2 ${
                                    isResumable 
                                      ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-white hover:from-yellow-600 hover:to-orange-600'
                                      : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-700 hover:to-purple-700'
                                  }`}
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    {isResumable ? (
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                    ) : (
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                    )}
                                  </svg>
                                  {isResumable ? 'Resume Scraping' : 'Scrape Again'}
                                </button>
                              </div>
                            );
                          }
                          
                          return (
                            <button
                              onClick={() => handleStart(propertyType)}
                              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-2 px-4 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Start Scraping
                            </button>
                          );
                        })()}
                      </div>
                    </div>
                  );
                })}
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
                    <li>✅ Each property type scraped separately for better quality</li>
                    <li>✅ Duplicate detection across all property types</li>
                    <li>✅ Coordinates, price, and area validation</li>
                    <li>✅ Structured data ready for Valora analysis</li>
                  </ul>
                </div>
              </div>
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

        {/* STATS VIEW */}
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
          <span>One-by-one scraping for maximum data quality</span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            Structured data ingestion
          </span>
        </div>
      </div>
    </div>
  );
};

export default PropertyTypeScraper;
