import { useEffect, useRef, useState, memo, useCallback } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import '../styles/cesium.css'
import DrawingTools from '../components/DrawingTools'
import { API_URL } from '../apiConfig'

// Throttle helper to reduce React re-renders
const throttle = (fn, wait) => {
  let lastTime = 0
  return (...args) => {
    const now = Date.now()
    if (now - lastTime >= wait) {
      lastTime = now
      fn(...args)
    }
  }
}

window.CESIUM_BASE_URL = '/cesium/'

const ION_TOKEN =
  import.meta.env.VITE_CESIUM_ION_API_KEY ||
  import.meta.env.VITE_CESIUM_ION_API ||
  import.meta.env.VITE_CESIUM_ION_TOKEN ||
  import.meta.env.VITE_CESIUM_TOKEN ||
  import.meta.env.CESIUM_ION_API_KEY ||
  import.meta.env.CESIUM_ION_API

if (ION_TOKEN) {
  Cesium.Ion.defaultAccessToken = ION_TOKEN
}

const HAS_ION_TOKEN = Boolean(ION_TOKEN)
const ION_TERRAIN_ASSET_ID = (() => {
  const raw = Number(
    import.meta.env.VITE_CESIUM_ION_TERRAIN_ASSET_ID ||
      import.meta.env.CESIUM_ION_TERRAIN_ASSET_ID ||
      1
  )
  return Number.isFinite(raw) ? raw : 1
})()

const ION_PHOTOREALISTIC_ASSET_ID = (() => {
  const raw = Number(
    import.meta.env.VITE_CESIUM_ION_PHOTOREALISTIC_ASSET_ID ||
      import.meta.env.CESIUM_ION_PHOTOREALISTIC_ASSET_ID
  )
  return Number.isFinite(raw) ? raw : null
})()

const HAS_ION_PHOTOREALISTIC = Boolean(ION_PHOTOREALISTIC_ASSET_ID)

// Ion OSM Buildings asset
const ION_OSM_BUILDINGS_ASSET_ID = (() => {
  const raw = Number(
    import.meta.env.VITE_CESIUM_ION_OSM_BUILDINGS_ASSET_ID ||
      import.meta.env.CESIUM_ION_OSM_BUILDINGS_ASSET_ID
  )
  return Number.isFinite(raw) ? raw : null
})()

const HAS_ION_OSM_BUILDINGS = Boolean(ION_OSM_BUILDINGS_ASSET_ID)

// Ion Imagery asset IDs (Google/Bing basemaps)
const ION_IMAGERY_ASSETS = {
  googleSatellite: Number(import.meta.env.VITE_CESIUM_ION_GOOGLE_SATELLITE_ASSET_ID) || null,
  googleSatelliteLabels: Number(import.meta.env.VITE_CESIUM_ION_GOOGLE_SATELLITE_LABELS_ASSET_ID) || null,
  googleRoadmap: Number(import.meta.env.VITE_CESIUM_ION_GOOGLE_ROADMAP_ASSET_ID) || null,
  googleLabels: Number(import.meta.env.VITE_CESIUM_ION_GOOGLE_LABELS_ASSET_ID) || null,
  googleContour: Number(import.meta.env.VITE_CESIUM_ION_GOOGLE_CONTOUR_ASSET_ID) || null,
  bingAerial: Number(import.meta.env.VITE_CESIUM_ION_BING_AERIAL_ASSET_ID) || null,
  bingAerialLabels: Number(import.meta.env.VITE_CESIUM_ION_BING_AERIAL_LABELS_ASSET_ID) || null,
  bingRoad: Number(import.meta.env.VITE_CESIUM_ION_BING_ROAD_ASSET_ID) || null,
}

const HAS_ION_IMAGERY = HAS_ION_TOKEN && Object.values(ION_IMAGERY_ASSETS).some(Boolean)

// Local tileset URL override (for self-hosted photorealistic tiles)
const LOCAL_PHOTOREALISTIC_TILESET_URL = import.meta.env.VITE_LOCAL_PHOTOREALISTIC_TILESET_URL || null
const USE_LOCAL_PHOTOREALISTIC = Boolean(LOCAL_PHOTOREALISTIC_TILESET_URL)

// Photorealistic tile cache settings - CONSERVATIVE for smooth performance
const PHOTOREALISTIC_CACHE_CONFIG = {
  maximumScreenSpaceError: 4, // Higher = less detail but better performance
  maximumMemoryUsage: 512, // 512MB only - reduced to prevent lag
  cacheBytes: 536870912, // 512MB in bytes
  preloadWhenHidden: false, // Don't preload - causes lag
  preloadFlightDestinations: false, // Don't preload - causes lag
  dynamicScreenSpaceError: true,
  dynamicScreenSpaceErrorDensity: 0.01, // Less dense
  dynamicScreenSpaceErrorFactor: 2.0,
  skipLevelOfDetail: true, // Skip LODs for performance
  baseScreenSpaceError: 2048, // Higher = less detail
  skipScreenSpaceErrorFactor: 32, // More aggressive skipping
  skipLevels: 2, // Skip more levels
  immediatelyLoadDesiredLevelOfDetail: false, // Load gradually
  loadSiblings: false, // Don't load siblings - saves memory
  cullWithChildrenBounds: true,
  cullRequestsWhileMoving: true, // Cull while moving for smooth panning
  cullRequestsWhileMovingMultiplier: 10.0, // Aggressive culling while moving
  progressiveResolutionHeightFraction: 0.5, // Less progressive detail
  foveatedScreenSpaceError: true,
  foveatedConeSize: 0.1, // Smaller cone
  foveatedMinimumScreenSpaceErrorRelaxation: 0.5, // More relaxed outside center
  foveatedTimeDelay: 0.2 // Slower updates
}

// Backend API for local 3D buildings
const API_BASE = API_URL
const TILES_API = `${API_BASE}/api/tiles/viewport`
const POLYGON_ANALYZE_API = `${API_BASE}/api/spatial/polygon-analyze`
const BUFFER_ANALYZE_API = `${API_BASE}/api/spatial/buffer-analyze`

// Building display limits for performance optimization
const MAX_BUILDINGS_DISPLAY = 30000 // Hard limit for building count
const BUILDING_LOAD_RADIUS_KM = 0.5 // 500m radius for click-based loading
const BUILDING_HIGH_QUALITY_RADIUS_KM = 0.5 // 500m for high quality buildings
const MAX_TILES_IN_MEMORY = 100 // Reduced for better memory usage
const EVICTION_GRACE_PERIOD_MS = 30000 // Don't evict tiles loaded less than 30s ago
const EVICTION_RADIUS_KM = 3.0 // Only evict tiles beyond 3km (always > load radius)

// Memory pressure thresholds
const MEMORY_PRESSURE_WARNING = 0.7 // 70% of heap limit
const MEMORY_PRESSURE_CRITICAL = 0.85 // 85% of heap limit - aggressive cleanup

// Bangalore areas for navigation
const BANGALORE_AREAS = {
  indiranagar: { lng: 77.6412, lat: 12.9716, name: 'Indiranagar', icon: '🏘️' },
  hebbal: { lng: 77.5946, lat: 13.0359, name: 'Hebbal', icon: '🌳' },
  whitefield: { lng: 77.7499, lat: 12.9698, name: 'Whitefield', icon: '🏢' },
  koramangala: { lng: 77.6245, lat: 12.9352, name: 'Koramangala', icon: '🍽️' },
  jayanagar: { lng: 77.5800, lat: 12.9250, name: 'Jayanagar', icon: '🏛️' },
  mgroad: { lng: 77.6066, lat: 12.9758, name: 'MG Road', icon: '🛍️' },
  electroniccity: { lng: 77.6600, lat: 12.8456, name: 'Electronic City', icon: '💻' },
  malleshwaram: { lng: 77.5685, lat: 13.0035, name: 'Malleshwaram', icon: '🕉️' }
}

// Default location: Indiranagar, Bangalore
const DEFAULT_LOCATION = {
  lng: 77.6412,
  lat: 12.9716,
  height: 1500
}

const MAP_PREFS_KEY = 'valora.mapPreferences'
// Closer orbit distance for better building/location inspection (was 500m, now 200m for closer view)
const DEFAULT_ORBIT_DISTANCE = 200
const DEFAULT_ORBIT_PITCH_DEG = -35

const loadMapPreferences = () => {
  if (typeof window === 'undefined') return {}
  try {
    const raw = window.localStorage.getItem(MAP_PREFS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch (err) {
    console.warn('Failed to load map preferences:', err)
    return {}
  }
}

const saveMapPreferences = (prefs) => {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(MAP_PREFS_KEY, JSON.stringify(prefs))
  } catch (err) {
    console.warn('Failed to save map preferences:', err)
  }
}

// Memory pressure detection helper
const getMemoryPressure = () => {
  // performance.memory is only available in Chromium browsers
  const memory = performance.memory
  if (!memory) {
    return { level: 'unknown', usedJSHeapSize: 0, totalJSHeapSize: 0, jsHeapSizeLimit: 0 }
  }
  
  const usedRatio = memory.usedJSHeapSize / memory.jsHeapSizeLimit
  let level = 'normal'
  if (usedRatio >= MEMORY_PRESSURE_CRITICAL) {
    level = 'critical'
  } else if (usedRatio >= MEMORY_PRESSURE_WARNING) {
    level = 'warning'
  }
  
  return {
    level,
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
    usedRatio: usedRatio.toFixed(2)
  }
}

export function OnlineOSMMap({ agentData, setAgentData, onAnalysisUpdate, toggleMapFullscreen, isMapFullscreen, userLocation, gpsEnabled }) {
  // Throttle setAgentData to reduce React re-renders (max 1 update per 100ms)
  const throttledSetAgentData = useRef(null)
  if (!throttledSetAgentData.current) {
    throttledSetAgentData.current = throttle((updateFn) => {
      setAgentData(updateFn)
    }, 100)
  }
  // Use throttled version for frequent updates
  const updateAgentData = throttledSetAgentData.current

  const cesiumContainerRef = useRef(null)
  const viewerRef = useRef(null)
  const loadedTilesRef = useRef(new Set())  // Track loaded tile IDs
  const tileEntitiesRef = useRef({})  // Map of tile_id -> entities[]
  const tileCentersRef = useRef({})  // Map of tile_id -> {lat, lng} for distance-based eviction
  const tileLoadTimesRef = useRef({})  // Map of tile_id -> timestamp to prevent immediate eviction
  const tileBuildingCountsRef = useRef({}) // Map of tile_id -> building count for limit tracking
  const cameraMoveTimeoutRef = useRef(null)
  const selectedBuildingEntityRef = useRef(null)  // Track currently highlighted building
  const keyDownHandlerRef = useRef(null) // Track key handler so we can remove it on cleanup
  const lastCameraViewRef = useRef(null)
  const placeMarkerRef = useRef(null)
  const placeMarkerClickTimeRef = useRef(null) // Track when user clicked to avoid overwriting
  const rotationIntervalRef = useRef(null)
  const rotationTargetRef = useRef(null)
  const ionPhotorealisticTilesetRef = useRef(null)
  const ionOsmBuildingsTilesetRef = useRef(null)

  // Primitive API refs for performant building rendering
  const buildingPrimitiveRef = useRef(null)  // Main building primitive
  const selectionPrimitiveRef = useRef(null)  // Highlighted building primitive
  const buildingDataStoreRef = useRef({
    metadata: new Map(),  // buildingId -> { height, levels, type, name, address, lat, lng, area, coordinates }
    idCounter: 0  // Counter for generating unique IDs
  })

  const selectedLocationRef = useRef(null)
  const selectedBuildingCoordsRef = useRef(null)

  useEffect(() => {
    selectedLocationRef.current = agentData?.selectedLocation || null
  }, [agentData?.selectedLocation])

  useEffect(() => {
    selectedBuildingCoordsRef.current = agentData?.selectedBuilding?.coordinates || null
  }, [agentData?.selectedBuilding])
  const ionImageryLayerRef = useRef(null)
  const placesDataSourceRef = useRef(null)
  const initialPrefsRef = useRef(loadMapPreferences())
  const [isLoading, setIsLoading] = useState(true)
  const [is3DMode, setIs3DMode] = useState(true)
  const [heading, setHeading] = useState(0)
  const [selectedArea, setSelectedArea] = useState('indiranagar')
  const [buildingsLoaded, setBuildingsLoaded] = useState(false)
  const [buildingsCount, setBuildingsCount] = useState(0)
  const [loadingBuildings, setLoadingBuildings] = useState(false)
  const loadingBuildingsRef = useRef(false) // Ref-based guard for stale closures
  const [tilesLoaded, setTilesLoaded] = useState(0)
  const [clickRipple, setClickRipple] = useState(null)
  
  // Debug: Log buildings count changes
  useEffect(() => {
    console.log(`[Debug] Buildings count updated: ${buildingsCount}`)
  }, [buildingsCount])
  const [canGoBack, setCanGoBack] = useState(false)
  
  // Enhanced layer visibility controls - optimized for RAM efficiency
  const [showBuildings, setShowBuildings] = useState(() => initialPrefsRef.current.showBuildings ?? true) // Buildings ON by default
  const showBuildingsRef = useRef(true) // Ref for camera listener closure
  const [showShadows, setShowShadows] = useState(true) // Shadows always on
  const [showTerrainShadows, setShowTerrainShadows] = useState(true) // Terrain shadows always on
  const [showTerrain, setShowTerrain] = useState(() => initialPrefsRef.current.showTerrain ?? true) // Terrain enabled by default
  const [terrainExaggeration, setTerrainExaggeration] = useState(() => initialPrefsRef.current.terrainExaggeration ?? 1)
  const [showIonPhotorealistic, setShowIonPhotorealistic] = useState(() => initialPrefsRef.current.showIonPhotorealistic ?? false)
  const [showIonOsmBuildings, setShowIonOsmBuildings] = useState(() => (initialPrefsRef.current.showIonOsmBuildings ?? true) && HAS_ION_TOKEN && HAS_ION_OSM_BUILDINGS)
  const [ionImageryType, setIonImageryType] = useState(() => initialPrefsRef.current.ionImageryType ?? 'none') // 'none', 'googleSatellite', 'googleSatelliteLabels', 'bingAerial', etc.
  const [buildingQuality, setBuildingQuality] = useState(() => initialPrefsRef.current.buildingQuality ?? 'medium') // low, medium, high - MEDIUM default for RAM
  
  // Performance monitoring
  const [fps, setFps] = useState(60)
  const [memoryUsage, setMemoryUsage] = useState(0)
  const [showPerformancePanel, setShowPerformancePanel] = useState(false)
  const [gpuInfo, setGpuInfo] = useState({ vendor: 'Unknown', renderer: 'Unknown', isDedicated: false })
  
  // Cache stats
  const [ionCacheStats, setIonCacheStats] = useState({ totalTiles: 0, totalSize: 0, percentage: 0 })
  const [buildingCacheStats, setBuildingCacheStats] = useState({ totalTiles: 0, totalSize: 0 })
  const [showCachePanel, setShowCachePanel] = useState(false)
  
  // Real-time clock state
  const [currentTime, setCurrentTime] = useState(new Date())
  
  // Time simulation controls
  const [timeMultiplier, setTimeMultiplier] = useState(1) // 1 = real-time
  const [showTimeControls, setShowTimeControls] = useState(false)
  const [simulatedTime, setSimulatedTime] = useState(null)
  
  // Layer controls panel
  const [showLayerPanel, setShowLayerPanel] = useState(false)
  const [showBasemapDropdown, setShowBasemapDropdown] = useState(false)
  
  // Building info popup
  const [selectedBuilding, setSelectedBuilding] = useState(null)
  const [buildingPopupPosition, setBuildingPopupPosition] = useState(null)
  
  // Search bar
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const searchDebounceRef = useRef(null)
  
  // Basemap toggle: 'osm', 'mapbox_streets', 'mapbox_satellite', 'mapbox_satellite_streets', 'mapbox_dark', 'mapbox_light', 'mapbox_outdoors'
  const [basemapType, setBasemapType] = useState(() => initialPrefsRef.current.basemapType ?? 'osm')
  
  // Weather effects
  const [showRain, setShowRain] = useState(false)
  const [showSnow, setShowSnow] = useState(false)
  const [showClouds, setShowClouds] = useState(false)
  const [showWind, setShowWind] = useState(false)
  const [realtimeWeather, setRealtimeWeather] = useState(null)
  const [enableRealtimeWeather, setEnableRealtimeWeather] = useState(false)
  const [weatherError, setWeatherError] = useState(null)
  const [weatherLastUpdated, setWeatherLastUpdated] = useState(null)
  const [weatherMetrics, setWeatherMetrics] = useState({
    tempC: null,
    feelsLikeC: null,
    humidity: null,
    windSpeedMps: null,
    windDeg: null,
    cloudsPct: null,
    rainMm1h: null,
    snowMm1h: null,
    conditionMain: null,
    conditionDesc: null
  })
  const rainSystemRef = useRef(null)
  const snowSystemRef = useRef(null)
  const weatherAppliedRef = useRef({ lastKey: null })

  useEffect(() => {
    const lat = Number(userLocation?.lat)
    const lng = Number(userLocation?.lng)
    const hasGps = Boolean(gpsEnabled) && Number.isFinite(lat) && Number.isFinite(lng)
    setEnableRealtimeWeather(hasGps)
    if (!hasGps) {
      setRealtimeWeather(null)
      setWeatherError(null)
      setWeatherLastUpdated(null)
      setShowRain(false)
      setShowSnow(false)
      setShowClouds(false)
      setShowWind(false)
      weatherAppliedRef.current.lastKey = null
      if (setAgentData) {
        updateAgentData(prev => ({
          ...prev,
          weather: null
        }))
      }
    }
  }, [gpsEnabled, userLocation?.lat, userLocation?.lng])
  
  // Drawing tools state
  const [isDrawing, setIsDrawing] = useState(false)
  const [drawMode, setDrawMode] = useState(null) // 'polygon' or 'buffer'
  const [polygonPoints, setPolygonPoints] = useState([])
  const [bufferRadius, setBufferRadius] = useState(500) // meters
  const [drawnEntities, setDrawnEntities] = useState([])
  const drawingHandlerRef = useRef(null)
  const bufferEntityRef = useRef(null)
  const polygonEntityRef = useRef(null)

  useEffect(() => {
    saveMapPreferences({
      showBuildings,
      showShadows,
      showTerrainShadows,
      showTerrain,
      terrainExaggeration,
      showIonPhotorealistic,
      showIonOsmBuildings,
      ionImageryType,
      basemapType,
      buildingQuality
    })
  }, [showBuildings, showShadows, showTerrainShadows, showTerrain, terrainExaggeration, showIonPhotorealistic, showIonOsmBuildings, ionImageryType, basemapType, buildingQuality])

  // Terrain exaggeration effect - production grade with proper validation
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || !viewer.scene?.globe) return
    
    // Only apply exaggeration if terrain is actually enabled
    if (!showTerrain) {
      console.log('[Terrain] Exaggeration update skipped - terrain disabled')
      return
    }
    
    // Check if terrain provider is loaded (not EllipsoidTerrainProvider which is flat)
    const hasRealTerrain = viewer.terrainProvider && 
      !(viewer.terrainProvider instanceof Cesium.EllipsoidTerrainProvider)
    
    if (!hasRealTerrain) {
      console.warn('[Terrain] Cannot apply exaggeration - no real terrain provider loaded')
      return
    }
    
    // Apply exaggeration
    viewer.scene.globe.terrainExaggeration = terrainExaggeration
    viewer.scene.globe.terrainExaggerationRelativeHeight = 0.0
    
    // Force terrain to rebuild with new exaggeration
    viewer.scene.globe.tileCache.clear()
    viewer.scene.requestRender()
    
    console.log(`[Terrain] Exaggeration updated to ${terrainExaggeration}x`)
  }, [terrainExaggeration, showTerrain])

  // Service Worker cache stats updater
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    const updateCacheStats = async () => {
      try {
        const registration = await navigator.serviceWorker.ready
        const messageChannel = new MessageChannel()
        
        messageChannel.port1.onmessage = (event) => {
          if (event.data) {
            if (event.data.ion) {
              setIonCacheStats({
                totalTiles: event.data.ion.totalTiles || 0,
                totalSize: event.data.ion.totalSize || 0,
                percentage: event.data.ion.percentage || 0
              })
            }
            if (event.data.building) {
              setBuildingCacheStats({
                totalTiles: event.data.building.totalTiles || 0,
                totalSize: event.data.building.totalSize || 0
              })
            }
          }
        }
        
        registration.active?.postMessage({ type: 'GET_CACHE_STATS' }, [messageChannel.port2])
      } catch (err) {
        console.warn('Failed to get cache stats:', err)
      }
    }

    // Update stats when photorealistic tiles are enabled OR buildings are shown
    if (showIonPhotorealistic || showBuildings) {
      updateCacheStats()
      const interval = setInterval(updateCacheStats, 10000) // Update every 10s
      return () => clearInterval(interval)
    }
  }, [showIonPhotorealistic, showBuildings])

  // Performance monitoring - FPS and Memory
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    let frameCount = 0
    let lastTime = performance.now()

    const measurePerformance = () => {
      frameCount++
      const currentTime = performance.now()
      const elapsed = currentTime - lastTime

      if (elapsed >= 1000) {
        const currentFps = Math.round((frameCount * 1000) / elapsed)
        setFps(currentFps)
        frameCount = 0
        lastTime = currentTime

        // Memory usage (if available)
        if (performance.memory) {
          const usedMB = Math.round(performance.memory.usedJSHeapSize / 1048576)
          setMemoryUsage(usedMB)
        }
      }

      requestAnimationFrame(measurePerformance)
    }

    const rafId = requestAnimationFrame(measurePerformance)

    return () => cancelAnimationFrame(rafId)
  }, [])

  // Aggressive tile eviction for RAM efficiency and building limit management
  useEffect(() => {
    if (!showBuildings) return

    const evictionInterval = setInterval(() => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return
      
      // Skip eviction if camera is moving for smoother experience
      if (viewer.camera._isMoving) return

      // Use camera look-at ground point for eviction distance (same as loading)
      let centerLat, centerLng
      const evictCanvas = viewer.scene.canvas
      const evictRay = viewer.camera.getPickRay(new Cesium.Cartesian2(evictCanvas.clientWidth / 2, evictCanvas.clientHeight / 2))
      if (evictRay) {
        const gp = viewer.scene.globe.pick(evictRay, viewer.scene)
        if (gp) {
          const gc = Cesium.Cartographic.fromCartesian(gp)
          centerLat = Cesium.Math.toDegrees(gc.latitude)
          centerLng = Cesium.Math.toDegrees(gc.longitude)
        }
      }
      if (centerLat == null) {
        const cameraPos = viewer.camera.positionCartographic
        centerLat = Cesium.Math.toDegrees(cameraPos.latitude)
        centerLng = Cesium.Math.toDegrees(cameraPos.longitude)
      }

      // Calculate current building count
      let currentBuildingCount = Object.values(tileEntitiesRef.current)
        .reduce((sum, entities) => sum + entities.length, 0)

      // Haversine distance calculator
      const haversineDistance = (lat1, lng1, lat2, lng2) => {
        const R = 6371
        const dLat = (lat2 - lat1) * Math.PI / 180
        const dLng = (lng2 - lng1) * Math.PI / 180
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLng/2) * Math.sin(dLng/2)
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
      }

      // EVICTION PRIORITY 1: Building count over limit
      if (currentBuildingCount > MAX_BUILDINGS_DISPLAY) {
        const allTileIds = Array.from(loadedTilesRef.current)
        const tilesWithDistance = allTileIds.map(tileId => {
          const center = tileCentersRef.current[tileId]
          if (!center) return { tileId, distance: Infinity, count: 0 }
          const dist = haversineDistance(centerLat, centerLng, center.lat, center.lng)
          const count = tileBuildingCountsRef.current[tileId] || 0
          return { tileId, distance: dist, count }
        })

        // Sort by distance (farthest first)
        tilesWithDistance.sort((a, b) => b.distance - a.distance)

        // Evict tiles until under limit - protect tiles within view radius and recently loaded
        let buildingsToEvict = currentBuildingCount - MAX_BUILDINGS_DISPLAY + 200
        const tilesToEvict = []
        const now = Date.now()

        for (const tile of tilesWithDistance) {
          if (buildingsToEvict <= 0) break
          // Never evict tiles within eviction protection radius
          if (tile.distance < EVICTION_RADIUS_KM) continue
          // Don't evict recently loaded tiles (grace period)
          const loadTime = tileLoadTimesRef.current[tile.tileId] || 0
          if (now - loadTime < EVICTION_GRACE_PERIOD_MS) continue

          tilesToEvict.push(tile.tileId)
          buildingsToEvict -= tile.count
        }

        tilesToEvict.forEach(tileId => {
          const entities = tileEntitiesRef.current[tileId] || []
          entities.forEach(entity => {
            try {
              viewer.entities.remove(entity)
            } catch (e) {}
          })
          delete tileEntitiesRef.current[tileId]
          delete tileCentersRef.current[tileId]
          delete tileLoadTimesRef.current[tileId]
          delete tileBuildingCountsRef.current[tileId]
          loadedTilesRef.current.delete(tileId)
        })

        if (tilesToEvict.length > 0) {
          console.log(`🗑️ Building limit eviction: Removed ${tilesToEvict.length} tiles`)
        }
      }
    }, 10000) // Check every 10 seconds (less aggressive)

    return () => clearInterval(evictionInterval)
  }, [showBuildings])

  // Auto-search with debounce
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    // Clear previous debounce
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current)
    }

    // Debounce search by 500ms
    searchDebounceRef.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(searchQuery + ', Bangalore, India')}&format=json&limit=5`
        )
        const results = await resp.json()
        setSearchResults(results)
        setShowSearchResults(true)
      } catch (err) {
        console.warn('Auto-search failed:', err)
        setSearchResults([])
      }
      setIsSearching(false)
    }, 500)

    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current)
      }
    }
  }, [searchQuery])

  // Fetch realtime weather for Bangalore
  useEffect(() => {
    if (!enableRealtimeWeather) return

    const lat = Number(userLocation?.lat)
    const lng = Number(userLocation?.lng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return

    const fetchWeather = async () => {
      try {
        // Vite only exposes env vars that start with VITE_
        const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || import.meta.env.VITE_OPENWEATHER_API || null

        if (!API_KEY) {
          setWeatherError('missing_api_key')
          setRealtimeWeather(null)
          return
        }

        const response = await fetch(
          `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lng}&appid=${encodeURIComponent(API_KEY)}&units=metric`
        )

        if (response.status === 401) {
          setWeatherError('invalid_api_key')
          setRealtimeWeather(null)
          return
        }

        if (response.ok) {
          const data = await response.json()
          const updatedAt = Date.now()
          setRealtimeWeather(data)
          setWeatherError(null)
          setWeatherLastUpdated(updatedAt)

          const conditionMain = data.weather?.[0]?.main?.toLowerCase() || null
          const conditionDesc = data.weather?.[0]?.description || null
          const tempC = Number.isFinite(data.main?.temp) ? data.main.temp : null
          const feelsLikeC = Number.isFinite(data.main?.feels_like) ? data.main.feels_like : null
          const humidity = Number.isFinite(data.main?.humidity) ? data.main.humidity : null
          const windSpeedMps = Number.isFinite(data.wind?.speed) ? data.wind.speed : null
          const windDeg = Number.isFinite(data.wind?.deg) ? data.wind.deg : null
          const cloudsPct = Number.isFinite(data.clouds?.all) ? data.clouds.all : null
          const rainMm1h = Number.isFinite(data.rain?.['1h']) ? data.rain['1h'] : null
          const snowMm1h = Number.isFinite(data.snow?.['1h']) ? data.snow['1h'] : null

          const metrics = {
            tempC,
            feelsLikeC,
            humidity,
            windSpeedMps,
            windDeg,
            cloudsPct,
            rainMm1h,
            snowMm1h,
            conditionMain,
            conditionDesc
          }

          setWeatherMetrics(metrics)

          if (setAgentData) {
            updateAgentData(prev => ({
              ...prev,
              weather: {
                updatedAt,
                error: null,
                metrics,
                raw: data
              }
            }))
          }

          // Auto-apply weather effects based on real conditions
          const key = `${conditionMain}|${Math.round((cloudsPct ?? 0) / 10)}|${Math.round((windSpeedMps ?? 0) * 2)}|${Math.round((rainMm1h ?? 0) * 10)}|${Math.round((snowMm1h ?? 0) * 10)}`
          if (weatherAppliedRef.current.lastKey !== key) {
            const isRain = conditionMain === 'rain' || conditionMain === 'drizzle' || conditionMain === 'thunderstorm' || (rainMm1h != null && rainMm1h > 0)
            const isSnow = conditionMain === 'snow' || (snowMm1h != null && snowMm1h > 0)
            const isCloudy = (cloudsPct != null && cloudsPct >= 40) || conditionMain === 'clouds' || conditionMain === 'mist' || conditionMain === 'haze' || conditionMain === 'fog'
            const isWindy = windSpeedMps != null && windSpeedMps >= 4

            setShowRain(isRain)
            setShowSnow(isSnow)
            setShowClouds(isCloudy)
            setShowWind(isWindy)

            weatherAppliedRef.current.lastKey = key
          }
        }
      } catch (err) {
        setWeatherError('fetch_failed')
        if (setAgentData) {
          updateAgentData(prev => ({
            ...prev,
            weather: {
              updatedAt: Date.now(),
              error: 'fetch_failed',
              metrics: null,
              raw: null
            }
          }))
        }
      }
    }

    fetchWeather()
    // Refresh weather every 30 minutes
    const interval = setInterval(fetchWeather, 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [enableRealtimeWeather])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const removeTileset = () => {
      if (ionPhotorealisticTilesetRef.current) {
        try {
          viewer.scene.primitives.remove(ionPhotorealisticTilesetRef.current)
        } catch (err) {
          console.warn('Failed to remove Ion photorealistic tileset:', err)
        }
        ionPhotorealisticTilesetRef.current = null
      }
    }

    if (!showIonPhotorealistic) {
      removeTileset()
      return undefined
    }

    // Check for local tileset URL first (self-hosted for education)
    if (USE_LOCAL_PHOTOREALISTIC) {
      if (ionPhotorealisticTilesetRef.current) return undefined

      let cancelled = false

      const loadLocalTileset = async () => {
        try {
          console.log(`📦 Loading local photorealistic tileset from: ${LOCAL_PHOTOREALISTIC_TILESET_URL}`)
          const tileset = await Cesium.Cesium3DTileset.fromUrl(LOCAL_PHOTOREALISTIC_TILESET_URL)
          if (cancelled || !viewer || viewer.isDestroyed()) return

          // Apply advanced cache config
          Object.assign(tileset, PHOTOREALISTIC_CACHE_CONFIG)

          viewer.scene.primitives.add(tileset)
          ionPhotorealisticTilesetRef.current = tileset
          console.log('✅ Ion photorealistic tileset loaded with 2GB in-memory cache')
        } catch (err) {
          console.error('Failed to load local photorealistic tileset:', err)
          if (!cancelled) {
            setShowIonPhotorealistic(false)
          }
        }
      }

      loadLocalTileset()

      return () => {
        cancelled = true
      }
    }

    // Fall back to Ion streaming
    if (!HAS_ION_TOKEN || !HAS_ION_PHOTOREALISTIC) {
      console.warn('Ion token or photorealistic asset ID missing; disabling photorealistic tiles.')
      setShowIonPhotorealistic(false)
      return undefined
    }

    if (ionPhotorealisticTilesetRef.current) return undefined

    let cancelled = false

    const loadTileset = async () => {
      try {
        console.log(`🌐 Loading Ion photorealistic tileset (asset ${ION_PHOTOREALISTIC_ASSET_ID}) with enhanced cache`)
        const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(ION_PHOTOREALISTIC_ASSET_ID)
        if (cancelled || !viewer || viewer.isDestroyed()) return

        // Apply advanced cache config for better performance
        Object.assign(tileset, PHOTOREALISTIC_CACHE_CONFIG)

        viewer.scene.primitives.add(tileset)
        ionPhotorealisticTilesetRef.current = tileset
        console.log('✅ Ion photorealistic tileset loaded with 2GB in-memory cache')
      } catch (err) {
        console.error('Failed to load Ion photorealistic tileset:', err)
        if (!cancelled) {
          setShowIonPhotorealistic(false)
        }
      }
    }

    loadTileset()

    return () => {
      cancelled = true
    }
  }, [showIonPhotorealistic])

  // Ion OSM Buildings tileset effect
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const removeTileset = () => {
      if (ionOsmBuildingsTilesetRef.current) {
        try {
          viewer.scene.primitives.remove(ionOsmBuildingsTilesetRef.current)
        } catch (err) {
          console.warn('Failed to remove Ion OSM buildings tileset:', err)
        }
        ionOsmBuildingsTilesetRef.current = null
      }
    }

    if (!showIonOsmBuildings) {
      removeTileset()
      return undefined
    }

    if (!HAS_ION_TOKEN || !HAS_ION_OSM_BUILDINGS) {
      console.warn('Ion token or OSM buildings asset ID missing; disabling Ion OSM buildings.')
      setShowIonOsmBuildings(false)
      return undefined
    }

    if (ionOsmBuildingsTilesetRef.current) return undefined

    let cancelled = false

    const loadTileset = async () => {
      try {
        const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(ION_OSM_BUILDINGS_ASSET_ID)
        if (cancelled || !viewer || viewer.isDestroyed()) return

        tileset.style = new Cesium.Cesium3DTileStyle({
          color: "color('white', 0.8)",
        })

        viewer.scene.primitives.add(tileset)
        ionOsmBuildingsTilesetRef.current = tileset
        console.log('✅ Ion OSM Buildings loaded')
      } catch (err) {
        console.error('Failed to load Ion OSM buildings tileset:', err)
        if (!cancelled) {
          setShowIonOsmBuildings(false)
        }
      }
    }

    loadTileset()

    return () => {
      cancelled = true
    }
  }, [showIonOsmBuildings])

  // Ion Imagery layer effect
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const removeImageryLayer = () => {
      if (ionImageryLayerRef.current) {
        try {
          viewer.imageryLayers.remove(ionImageryLayerRef.current, true)
        } catch (err) {
          console.warn('Failed to remove Ion imagery layer:', err)
        }
        ionImageryLayerRef.current = null
      }
    }

    if (ionImageryType === 'none' || !ionImageryType) {
      removeImageryLayer()
      return undefined
    }

    const assetId = ION_IMAGERY_ASSETS[ionImageryType]
    if (!HAS_ION_TOKEN || !assetId) {
      console.warn('Ion token or imagery asset ID missing; disabling Ion imagery.')
      setIonImageryType('none')
      return undefined
    }

    // Remove existing before loading new
    removeImageryLayer()

    let cancelled = false

    const loadImagery = async () => {
      try {
        const provider = await Cesium.IonImageryProvider.fromAssetId(assetId)
        if (cancelled || !viewer || viewer.isDestroyed()) return

        const layer = viewer.imageryLayers.addImageryProvider(provider)
        ionImageryLayerRef.current = layer
        console.log(`✅ Ion imagery layer loaded: ${ionImageryType}`)
      } catch (err) {
        console.error('Failed to load Ion imagery layer:', err)
        if (!cancelled) {
          setIonImageryType('none')
        }
      }
    }

    loadImagery()

    return () => {
      cancelled = true
    }
  }, [ionImageryType])

  useEffect(() => {
    const runPolygonAnalysis = async () => {
      if (!setAgentData) return

      const points = agentData?.drawnPolygon
      if (!Array.isArray(points) || points.length < 3) {
        updateAgentData(prev => ({
          ...prev,
          polygonAnalysisPending: false,
          polygonAnalysis: null,
          polygonAnalysisError: 'Polygon has insufficient points'
        }))
        return
      }

      updateAgentData(prev => ({
        ...prev,
        polygonAnalysisLoading: true,
        polygonAnalysisError: null,
      }))

      try {
        const coordinates = points.map(p => [p.lng, p.lat])
        const resp = await fetch(POLYGON_ANALYZE_API, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ coordinates })
        })

        if (!resp.ok) {
          throw new Error(`Polygon analyze failed: ${resp.status}`)
        }

        const data = await resp.json()
        updateAgentData(prev => ({
          ...prev,
          polygonAnalysisPending: false,
          polygonAnalysisLoading: false,
          polygonAnalysis: data?.data || null,
          polygonAnalysisError: null,
        }))
      } catch (e) {
        updateAgentData(prev => ({
          ...prev,
          polygonAnalysisPending: false,
          polygonAnalysisLoading: false,
          polygonAnalysis: null,
          polygonAnalysisError: e?.message || String(e)
        }))
      }
    }

    if (agentData?.polygonAnalysisPending) {
      runPolygonAnalysis()
    }
  }, [agentData?.polygonAnalysisPending, agentData?.drawnPolygon, setAgentData])


  useEffect(() => {
    const runBufferAnalysis = async () => {
      if (!setAgentData) return
      const buf = agentData?.drawnBuffer
      const center = buf?.center
      const radius = buf?.radius
      if (!center?.lat || !center?.lng || !radius) {
        updateAgentData(prev => ({
          ...prev,
          bufferAnalysisPending: false,
          bufferAnalysis: null,
          bufferAnalysisError: 'Buffer center or radius missing'
        }))
        return
      }

      updateAgentData(prev => ({
        ...prev,
        bufferAnalysisLoading: true,
        bufferAnalysisError: null,
      }))

      try {
        const resp = await fetch(BUFFER_ANALYZE_API, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ center, radius_m: radius })
        })

        if (!resp.ok) {
          throw new Error(`Buffer analyze failed: ${resp.status}`)
        }

        const data = await resp.json()
        updateAgentData(prev => ({
          ...prev,
          bufferAnalysisPending: false,
          bufferAnalysisLoading: false,
          bufferAnalysis: data?.data || null,
          bufferAnalysisError: null,
        }))
      } catch (e) {
        updateAgentData(prev => ({
          ...prev,
          bufferAnalysisPending: false,
          bufferAnalysisLoading: false,
          bufferAnalysis: null,
          bufferAnalysisError: e?.message || String(e)
        }))
      }
    }

    if (agentData?.bufferAnalysisPending) {
      runBufferAnalysis()
    }
  }, [agentData?.bufferAnalysisPending, agentData?.drawnBuffer, setAgentData])


  const applyPlaceLabelStyle = (entity, subtype) => {
    if (!entity) return
    const name = entity?.properties?.name?.getValue?.() || entity?.name
    if (!name) return

    const kind = String(subtype || '').toLowerCase()
    let fontPx = 12
    let maxDistance = 20000
    let minDistance = 0

    if (kind === 'city') {
      fontPx = 18
      maxDistance = 200000
      minDistance = 5000
    } else if (kind === 'town') {
      fontPx = 15
      maxDistance = 120000
      minDistance = 2000
    } else if (kind === 'county') {
      fontPx = 15
      maxDistance = 250000
      minDistance = 10000
    } else if (kind === 'suburb') {
      fontPx = 13
      maxDistance = 40000
      minDistance = 500
    } else if (kind === 'neighbourhood' || kind === 'quarter') {
      fontPx = 11
      maxDistance = 15000
      minDistance = 200
    } else if (kind === 'village') {
      fontPx = 12
      maxDistance = 60000
      minDistance = 1000
    }

    const label = new Cesium.LabelGraphics({
      text: name,
      font: `600 ${fontPx}px Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`,
      fillColor: Cesium.Color.fromCssColorString('#e2e8f0'),
      outlineColor: Cesium.Color.fromCssColorString('#0f172a'),
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      showBackground: true,
      backgroundColor: Cesium.Color.fromCssColorString('#0f172a').withAlpha(0.55),
      backgroundPadding: new Cesium.Cartesian2(8, 4),
      pixelOffset: new Cesium.Cartesian2(0, -8),
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(minDistance, maxDistance),
      scaleByDistance: new Cesium.NearFarScalar(2000.0, 1.0, maxDistance, 0.5),
      translucencyByDistance: new Cesium.NearFarScalar(1500.0, 1.0, maxDistance * 0.8, 0.0),
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    })

    // Remove default GeoJSON billboard/point graphics (causes pink overlapping markers)
    entity.billboard = undefined
    entity.point = undefined
    entity.polygon = undefined
    entity.polyline = undefined
    entity.label = label
  }

  const ensurePlacesLabelsLoaded = async () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    if (placesDataSourceRef.current) return

    try {
      const ds = await Cesium.GeoJsonDataSource.load('/data/osm_extracted/places.geojson', {
        clampToGround: true
      })

      ds.name = 'valora-places-labels'
      placesDataSourceRef.current = ds
      viewer.dataSources.add(ds)

      const entities = ds.entities.values
      for (const e of entities) {
        const subtype = e?.properties?.subtype?.getValue?.() || e?.properties?.place?.getValue?.()
        applyPlaceLabelStyle(e, subtype)
      }
    } catch (err) {
      console.warn('Failed to load places labels:', err)
    }
  }

  // Toggle layer visibility - loads buildings if enabling and none loaded
  const toggleBuildingsLayer = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    const newState = !showBuildings
    setShowBuildings(newState)
    
    // Toggle all existing building entities
    Object.values(tileEntitiesRef.current).forEach(entities => {
      entities.forEach(e => {
        if (e && e.polygon) e.show = newState
      })
    })
    
    // If enabling and no buildings loaded yet, trigger load
    // DISABLED: Viewport-based loading disabled - only query-based loading from chat
    if (newState && buildingsCount === 0) {
      console.log('[Buildings] Enabling - waiting for query-based loading from chat...')
      // loadTilesForViewport() // Disabled - use query-based loading instead
    }
  }

  const togglePlacesLayer = () => {
    // Place labels disabled - AI handles labels in cinematic mode
    // const viewer = viewerRef.current
    // if (!viewer || viewer.isDestroyed()) return
    // if (!placesDataSourceRef.current) return
    // 
    // const newState = !showPlaces
    // setShowPlaces(newState)
    // placesDataSourceRef.current.show = newState
  }

  const toggleTransportLayer = () => {
    // setShowTransport(prev => !prev)
    // Transport layer implementation pending
  }


  // Stop rotation helper function
  const stopRotation = () => {
    if (rotationIntervalRef.current) {
      console.log('🎥 Stopping camera orbit')
      clearInterval(rotationIntervalRef.current)
      rotationIntervalRef.current = null
      rotationTargetRef.current = null
    }
  }

  const getTerrainHeight = (lng, lat) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || !showTerrain) return 0
    const cartographic = Cesium.Cartographic.fromDegrees(lng, lat)
    const height = viewer.scene?.globe?.getHeight(cartographic)
    return Number.isFinite(height) ? height : 0
  }

  const getTerrainAwareTarget = (lng, lat, heightOffset = 0) => {
    const terrainHeight = getTerrainHeight(lng, lat)
    return Cesium.Cartesian3.fromDegrees(lng, lat, terrainHeight + heightOffset)
  }

  const getGroundPositionFromScreen = (screenPosition) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return null
    const scene = viewer.scene
    if (!scene) return null

    // FIX: Prioritize globe.pick (ground position) over pickPosition (entity surface)
    // This ensures clicking on buildings still returns the ground position, not the building surface
    const ray = viewer.camera.getPickRay(screenPosition)
    if (ray) {
      const globePosition = scene.globe.pick(ray, scene)
      if (Cesium.defined(globePosition)) return globePosition
    }

    // Fallback to pickPosition for non-ground picks (e.g., when globe is not visible)
    if (scene.pickPositionSupported) {
      const pickPosition = scene.pickPosition(screenPosition)
      if (Cesium.defined(pickPosition)) return pickPosition
    }

    return viewer.camera.pickEllipsoid(screenPosition, scene.globe.ellipsoid)
  }

  // Auto-rotate camera 360° around target during analysis loading
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const isAnalyzing = agentData?.buildingAnalysisLoading || agentData?.locationAnalysisLoading

    if (isAnalyzing && !rotationIntervalRef.current && rotationTargetRef.current) {
      console.log('🎥 Starting 360° camera orbit')
      const target = rotationTargetRef.current
      const orbitDistance = DEFAULT_ORBIT_DISTANCE
      const pitch = Cesium.Math.toRadians(DEFAULT_ORBIT_PITCH_DEG)
      let heading = viewer.camera.heading || 0
      
      // Lock camera to orbit initially
      try {
        viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(heading, pitch, orbitDistance))
      } catch (_) {}
      
      // Stop rotation on any user input (mouse/touch/wheel)
      const stopOnInput = () => {
        stopRotation()
        // Release camera lock when user intervenes
        try { viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY) } catch (_) {}
        document.removeEventListener('mousedown', stopOnInput)
        document.removeEventListener('wheel', stopOnInput)
        document.removeEventListener('touchstart', stopOnInput)
      }
      document.addEventListener('mousedown', stopOnInput)
      document.addEventListener('wheel', stopOnInput)
      document.addEventListener('touchstart', stopOnInput)
      
      rotationIntervalRef.current = setInterval(() => {
        if (viewer && !viewer.isDestroyed() && target) {
          heading += Cesium.Math.toRadians(0.15)
          // Keep camera locked to lookAt — do NOT release transform each frame
          viewer.camera.lookAt(
            target,
            new Cesium.HeadingPitchRange(heading, pitch, orbitDistance)
          )
        }
      }, 16) // ~60fps
    } else if (!isAnalyzing && rotationIntervalRef.current) {
      stopRotation()
      // Release camera lock when analysis completes
      try { viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY) } catch (_) {}
    }

    return () => {
      stopRotation()
      try { if (viewer && !viewer.isDestroyed()) viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY) } catch (_) {}
    }
  }, [agentData?.buildingAnalysisLoading, agentData?.locationAnalysisLoading])

  // Apply layer visibility controls
  // Buildings, shadows, terrain are always-on — no toggle sync needed

  // Real-time clock - updates every second
  useEffect(() => {
    const clockInterval = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(clockInterval)
  }, [])

  // Buildings now load on click — no auto-load on state change needed


  const flyToArea = (areaKey, height = 1200) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    const area = BANGALORE_AREAS[areaKey]
    if (!area) return
    
    setSelectedArea(areaKey)

    const camera = viewer.camera
    lastCameraViewRef.current = {
      destination: Cesium.Cartesian3.clone(camera.position),
      heading: camera.heading,
      pitch: camera.pitch,
      roll: camera.roll
    }
    setCanGoBack(true)

    if (placeMarkerRef.current) {
      viewer.entities.remove(placeMarkerRef.current)
      placeMarkerRef.current = null
    }

    placeMarkerRef.current = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(area.lng, area.lat),
      point: {
        pixelSize: 12,
        color: Cesium.Color.fromCssColorString('#3b82f6'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
    
    // Terrain-aware camera height
    const terrainHeight = getTerrainHeight(area.lng, area.lat)
    const adjustedHeight = height + terrainHeight
    
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(area.lng, area.lat, adjustedHeight),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-35),
        roll: 0
      },
      duration: 1.5
    })
  }

  const resetView = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const camera = viewer.camera
    lastCameraViewRef.current = {
      destination: Cesium.Cartesian3.clone(camera.position),
      heading: camera.heading,
      pitch: camera.pitch,
      roll: camera.roll
    }
    setCanGoBack(true)

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(DEFAULT_LOCATION.lng, DEFAULT_LOCATION.lat, DEFAULT_LOCATION.height),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-35),
        roll: 0
      },
      duration: 1.5,
      complete: () => {
        // DISABLED: Initial building load at DEFAULT_LOCATION - buildings should only load
        // via query-based loading from chat (valora-load-buildings event)
        // setTimeout(() => loadBuildingsAtPoint(DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lng, BUILDING_LOAD_RADIUS_KM), 500)
      }
    })
  }

  const goBackToLastView = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    if (!lastCameraViewRef.current) return

    const last = lastCameraViewRef.current
    viewer.camera.flyTo({
      destination: last.destination,
      orientation: {
        heading: last.heading,
        pitch: last.pitch,
        roll: last.roll
      },
      duration: 1.2,
      complete: () => {
        // DISABLED: Building load on flyTo completion - only query-based loading from chat
        // const carto = Cesium.Cartographic.fromCartesian(last.destination)
        // if (carto) {
        //   const lat = Cesium.Math.toDegrees(carto.latitude)
        //   const lng = Cesium.Math.toDegrees(carto.longitude)
        //   setTimeout(() => loadBuildingsAtPoint(lat, lng, BUILDING_LOAD_RADIUS_KM), 500)
        // }
      }
    })
  }

  const zoomIn = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const camera = viewer.camera
    const height = Cesium.Cartographic.fromCartesian(camera.position).height
    camera.zoomIn(height * 0.3)
  }

  const zoomOut = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const camera = viewer.camera
    const height = Cesium.Cartographic.fromCartesian(camera.position).height
    camera.zoomOut(height * 0.3)
  }

  const resetNorth = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const camera = viewer.camera
    camera.flyTo({
      destination: camera.position,
      orientation: {
        heading: 0,
        pitch: camera.pitch,
        roll: 0
      },
      duration: 0.5
    })
    setHeading(0)
  }

  const toggle3D = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const newMode = !is3DMode
    setIs3DMode(newMode)
    
    viewer.camera.flyTo({
      destination: viewer.camera.position,
      orientation: {
        heading: newMode ? viewer.camera.heading : 0,
        pitch: Cesium.Math.toRadians(newMode ? -35 : -90),
        roll: 0
      },
      duration: 1.0
    })
  }

  // Switch basemap between OSM and Mapbox styles
  const switchBasemap = async (type) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    console.log(`🔄 Switching to ${type} basemap...`)
    
    try {
      let provider
      
      if (type.startsWith('mapbox_')) {
        // Fetch config for Mapbox keys
        const configResp = await fetch(`${API_BASE}/api/config`)
        if (!configResp.ok) {
          throw new Error('Failed to fetch Mapbox config')
        }
        const config = await configResp.json()
        
        // Determine which API key to use and which style
        let mapboxKey = config.mapbox_api_key
        let styleId
        
        switch(type) {
          case 'mapbox_streets':
            mapboxKey = config.mapbox_street_api_key || config.mapbox_api_key
            styleId = 'streets-v12'
            break
          case 'mapbox_satellite':
            mapboxKey = config.mapbox_macro_api_key || config.mapbox_api_key
            styleId = 'satellite-v9'
            break
          case 'mapbox_satellite_streets':
            mapboxKey = config.mapbox_macro_api_key || config.mapbox_api_key
            styleId = 'satellite-streets-v12'
            break
          case 'mapbox_dark':
            mapboxKey = config.mapbox_api_key
            styleId = 'dark-v11'
            break
          case 'mapbox_light':
            mapboxKey = config.mapbox_api_key
            styleId = 'light-v11'
            break
          case 'mapbox_outdoors':
            mapboxKey = config.mapbox_api_key
            styleId = 'outdoors-v12'
            break
          default:
            styleId = 'streets-v12'
        }
        
        if (!mapboxKey) {
          console.warn('Mapbox key not found, falling back to OSM')
          provider = new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
          setBasemapType('osm')
        } else {
          provider = new Cesium.UrlTemplateImageryProvider({
            url: `https://api.mapbox.com/styles/v1/mapbox/${styleId}/tiles/{z}/{x}/{y}?access_token=${mapboxKey}`,
            credit: '© Mapbox'
          })
        }
      } else {
        // Default OSM
        provider = new Cesium.OpenStreetMapImageryProvider({
          url: 'https://tile.openstreetmap.org/'
        })
      }

      if (!provider) {
        throw new Error('No imagery provider created')
      }

      if (provider.readyPromise) {
        await provider.readyPromise
      }

      const applyOsmFallback = () => {
        try {
          viewer.imageryLayers.removeAll(true)
          const osmProvider = new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
          viewer.imageryLayers.addImageryProvider(osmProvider)
          setBasemapType('osm')
        } catch (e) {
          console.error('Failed to apply OSM fallback:', e)
        }
      }

      if (provider.errorEvent && type !== 'osm') {
        provider.errorEvent.addEventListener((err) => {
          console.error(`Basemap imagery error for ${type}:`, err)
          applyOsmFallback()
        })
      }

      viewer.imageryLayers.removeAll(true)
      viewer.imageryLayers.addImageryProvider(provider)
      setBasemapType(type)
      console.log(`✅ Switched to ${type} basemap`)
    } catch (err) {
      console.error(`Failed to switch to ${type} basemap:`, err)
      // Fallback to OSM on error
      const osmProvider = new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
      viewer.imageryLayers.addImageryProvider(osmProvider)
      setBasemapType('osm')
    }
  }

  const updateHeading = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const headingDeg = Cesium.Math.toDegrees(viewer.camera.heading)
    setHeading(Math.round((headingDeg + 360) % 360))
  }

  // Drawing functions
  const startPolygonDraw = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    setIsDrawing(true)
    setDrawMode('polygon')
    setPolygonPoints([])
    
    // Create handler for polygon drawing
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
    drawingHandlerRef.current = handler
    
    handler.setInputAction((click) => {
      const cartesian = getGroundPositionFromScreen(click.position)
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
        const lng = Cesium.Math.toDegrees(cartographic.longitude)
        const lat = Cesium.Math.toDegrees(cartographic.latitude)
        
        setPolygonPoints(prev => {
          const newPoints = [...prev, { lng, lat }]
          updatePolygonPreview(newPoints)
          return newPoints
        })
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
    
    handler.setInputAction(() => {
      finishPolygonDraw()
    }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)
  }
  
  const updatePolygonPreview = (points) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || points.length < 2) return
    
    // Remove existing preview
    if (polygonEntityRef.current) {
      viewer.entities.remove(polygonEntityRef.current)
    }
    
    const positions = points.flatMap(p => [p.lng, p.lat])
    
    polygonEntityRef.current = viewer.entities.add({
      polygon: {
        hierarchy: Cesium.Cartesian3.fromDegreesArray(positions),
        material: Cesium.Color.BLUE.withAlpha(0.3),
        outline: true,
        outlineColor: Cesium.Color.BLUE,
        outlineWidth: 2,
        height: 0
      }
    })
  }
  
  const finishPolygonDraw = () => {
    if (polygonPoints.length < 3) {
      cancelDrawing()
      return
    }
    
    // Clean up handler
    if (drawingHandlerRef.current) {
      drawingHandlerRef.current.destroy()
      drawingHandlerRef.current = null
    }
    
    setIsDrawing(false)
    setDrawMode(null)
    
    // Dispatch event for polygon analysis
    window.dispatchEvent(new CustomEvent('valora-polygon-drawn', {
      detail: { points: polygonPoints, type: 'polygon' }
    }))
    
    // Update agentData with polygon
    if (setAgentData) {
      updateAgentData(prev => ({
        ...prev,
        drawnPolygon: polygonPoints,
        polygonAnalysisPending: true
      }))
    }
    
    // Auto-dispatch chat query to analyze the drawn area
    const centroid = polygonPoints.reduce(
      (acc, p) => ({ lat: acc.lat + p.lat / polygonPoints.length, lng: acc.lng + p.lng / polygonPoints.length }),
      { lat: 0, lng: 0 }
    )
    window.dispatchEvent(new CustomEvent('valora-area-clicked', {
      detail: {
        coordinates: centroid,
        query: `Analyze this custom drawn area at ${centroid.lat.toFixed(4)}, ${centroid.lng.toFixed(4)}. It covers ${polygonPoints.length} boundary points. Provide investment analysis, spatial quality, and market data for this zone.`
      }
    }))
  }
  
  const startBufferDraw = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    setIsDrawing(true)
    setDrawMode('buffer')
    
    // Create handler for buffer placement
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
    drawingHandlerRef.current = handler
    
    handler.setInputAction((click) => {
      const cartesian = getGroundPositionFromScreen(click.position)
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
        const lng = Cesium.Math.toDegrees(cartographic.longitude)
        const lat = Cesium.Math.toDegrees(cartographic.latitude)
        
        createBufferZone(lat, lng, bufferRadius)
        finishBufferDraw(lat, lng)
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  }
  
  const createBufferZone = (lat, lng, radiusMeters) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    // Remove existing buffer
    if (bufferEntityRef.current) {
      viewer.entities.remove(bufferEntityRef.current)
    }
    
    bufferEntityRef.current = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lng, lat),
      ellipse: {
        semiMajorAxis: radiusMeters,
        semiMinorAxis: radiusMeters,
        material: Cesium.Color.BLUE.withAlpha(0.2),
        outline: true,
        outlineColor: Cesium.Color.BLUE,
        outlineWidth: 2,
        height: 0
      },
      point: {
        pixelSize: 10,
        color: Cesium.Color.BLUE,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2
      }
    })
  }
  
  const finishBufferDraw = (lat, lng) => {
    // Clean up handler
    if (drawingHandlerRef.current) {
      drawingHandlerRef.current.destroy()
      drawingHandlerRef.current = null
    }
    
    setIsDrawing(false)
    setDrawMode(null)
    
    // Dispatch event for buffer analysis
    window.dispatchEvent(new CustomEvent('valora-buffer-drawn', {
      detail: { center: { lat, lng }, radius: bufferRadius, type: 'buffer' }
    }))
    
    // Update agentData with buffer
    if (setAgentData) {
      updateAgentData(prev => ({
        ...prev,
        drawnBuffer: { center: { lat, lng }, radius: bufferRadius },
        bufferAnalysisPending: true
      }))
    }

    // Auto-dispatch chat query to analyze the drawn buffer
    window.dispatchEvent(new CustomEvent('valora-area-clicked', {
      detail: {
        coordinates: { lat, lng },
        query: `Analyze the ${bufferRadius}m radius around ${lat.toFixed(4)}, ${lng.toFixed(4)}. Provide investment analysis, spatial quality, and market data for this buffer zone.`
      }
    }))
  }
  
  const cancelDrawing = () => {
    if (drawingHandlerRef.current) {
      drawingHandlerRef.current.destroy()
      drawingHandlerRef.current = null
    }
    
    // Remove preview entities
    const viewer = viewerRef.current
    if (viewer && !viewer.isDestroyed()) {
      if (polygonEntityRef.current) {
        viewer.entities.remove(polygonEntityRef.current)
        polygonEntityRef.current = null
      }
    }
    
    setIsDrawing(false)
    setDrawMode(null)
    setPolygonPoints([])
  }
  
  const clearDrawings = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    // Remove all drawn entities
    if (polygonEntityRef.current) {
      viewer.entities.remove(polygonEntityRef.current)
      polygonEntityRef.current = null
    }
    if (bufferEntityRef.current) {
      viewer.entities.remove(bufferEntityRef.current)
      bufferEntityRef.current = null
    }
    
    setPolygonPoints([])
    
    // Clear from agentData
    if (setAgentData) {
      updateAgentData(prev => ({
        ...prev,
        drawnPolygon: null,
        drawnBuffer: null,
        polygonAnalysisPending: false,
        bufferAnalysisPending: false
      }))
    }
  }

  // Calculate distance between two points in kilometers using Haversine formula
  const getDistanceKm = (lat1, lng1, lat2, lng2) => {
    const R = 6371
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLng = (lng2 - lng1) * Math.PI / 180
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2)
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  }

  // Load a single tile and add buildings to scene using Entity API (with terrain clamping)
  // Supports two-level LOD: high quality within BUILDING_HIGH_QUALITY_RADIUS_KM, lower quality beyond
  const loadTile = async (tileId, tileUrl, centerLat = null, centerLng = null) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || !viewer.entities) return false
    if (loadedTilesRef.current.has(tileId)) return false // Already loaded

    try {
      // Handle both relative and absolute URLs
      const url = tileUrl.startsWith('/api/') ? `${API_BASE}${tileUrl}` : `${API_BASE}${tileUrl}`
      const response = await fetch(url)
      if (!response.ok) return false

      const data = await response.json()
      
      // Double-check viewer is still valid before adding entities
      if (!viewer || viewer.isDestroyed() || !viewer.entities) {
        console.warn(`Viewer destroyed while loading tile ${tileId}`)
        return false
      }
      
      // Add buildings from this tile/database response
      const entities = []
      
      // Track tile center from first building (for distance-based eviction)
      let tileCenterLat = null
      let tileCenterLng = null
      
      const features = data.features || []
      
      // Pre-allocate entity data for batch creation
      const entityDataList = []
      
      for (const feature of features) {
        const geomType = feature.geometry?.type
        const coords = feature.geometry?.coordinates
        const props = feature.properties || {}
        const height = Math.max(props.height || 10, 3)
        
        let centroidLng, centroidLat, polygonHierarchy
        
        if (geomType === 'Point' && coords) {
          // Database returns points - create simple building footprint
          centroidLng = coords[0]
          centroidLat = coords[1]
          // Create a simple square footprint (~15m x 15m)
          const size = 0.00015 // ~15m in degrees
          polygonHierarchy = Cesium.Cartesian3.fromDegreesArray([
            centroidLng - size, centroidLat - size,
            centroidLng + size, centroidLat - size,
            centroidLng + size, centroidLat + size,
            centroidLng - size, centroidLat + size
          ])
        } else if (geomType === 'Polygon' && coords?.[0]) {
          // File-based tiles have polygon coordinates
          const ring = coords[0]
          const lons = ring.map(c => c[0])
          const lats = ring.map(c => c[1])
          centroidLng = lons.reduce((a, b) => a + b, 0) / lons.length
          centroidLat = lats.reduce((a, b) => a + b, 0) / lats.length
          polygonHierarchy = Cesium.Cartesian3.fromDegreesArray(ring.flat())
        } else {
          continue // Skip invalid geometry
        }

        // Calculate distance from center for LOD determination
        let isHighQuality = true
        if (centerLat !== null && centerLng !== null) {
          const distanceKm = getDistanceKm(centerLat, centerLng, centroidLat, centroidLng)
          isHighQuality = distanceKm <= BUILDING_HIGH_QUALITY_RADIUS_KM
        }

        // Light purple theme color scheme for buildings - production grade
        const buildingType = props.building || props.type || 'building'
        const levels = props.levels || Math.round(height / 3)
        
        // Light pastel purple gradient based on building height
        // LOD: Lower quality buildings get reduced alpha and simpler appearance
        let color = '#c4b5fd'  // Default light purple
        let alpha = 0.75
        
        if (isHighQuality) {
          // High quality buildings (within 500m) - full detail
          if (height > 50) {
            color = '#a78bfa'  // Medium purple (skyscrapers)
            alpha = 0.85
          } else if (height > 30) {
            color = '#b8a5f8'  // Light-medium purple
            alpha = 0.80
          } else if (height > 15) {
            color = '#c4b5fd'  // Light purple
            alpha = 0.75
          } else if (height > 8) {
            color = '#d8cdf7'  // Very light purple
            alpha = 0.70
          } else {
            color = '#e9e3f8'  // Pale lavender
            alpha = 0.65
          }
        } else {
          // Lower quality buildings (500m-1km) - reduced detail for performance
          if (height > 50) {
            color = '#a78bfa'
            alpha = 0.55  // Reduced alpha
          } else if (height > 30) {
            color = '#b8a5f8'
            alpha = 0.50
          } else if (height > 15) {
            color = '#c4b5fd'
            alpha = 0.45
          } else if (height > 8) {
            color = '#d8cdf7'
            alpha = 0.40
          } else {
            color = '#e9e3f8'
            alpha = 0.35
          }
        }

        entityDataList.push({
          name: props.name || `Building`,
          polygon: {
            hierarchy: polygonHierarchy,
            material: Cesium.Color.fromCssColorString(color).withAlpha(alpha),
            outline: isHighQuality,  // Only show outline for high quality buildings
            outlineColor: Cesium.Color.fromCssColorString('#8b5cf6').withAlpha(0.5),
            outlineWidth: 1,
            height: 0,
            extrudedHeight: height,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            extrudedHeightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
            perPositionHeight: false,
            closeTop: isHighQuality,  // Only close top for high quality
            closeBottom: false,
            // High quality buildings cast shadows, lower quality buildings don't for performance
            shadows: isHighQuality ? Cesium.ShadowMode.CAST_ONLY : Cesium.ShadowMode.DISABLED
          },
          properties: {
            height: height,
            levels: levels,
            type: buildingType,
            name: props.name || null,
            address: props.address || props['addr:street'] || null,
            lng: centroidLng,
            lat: centroidLat,
            area: props.area || 225, // Default ~15m x 15m
            isHighQuality: isHighQuality
          }
        })
        
        // Store first building's centroid as tile center
        if (tileCenterLat === null && centroidLat && centroidLng) {
          tileCenterLat = centroidLat
          tileCenterLng = centroidLng
        }
      }
      
      // Batch add all entities at once for better performance
      viewer.entities.suspendEvents()
      try {
        for (const entityData of entityDataList) {
          const entity = viewer.entities.add(entityData)
          entities.push(entity)
        }
      } finally {
        viewer.entities.resumeEvents()
      }
      
      // Store entities for this tile
      tileEntitiesRef.current[tileId] = entities
      loadedTilesRef.current.add(tileId)

      // Store tile center for distance-based eviction
      if (entities.length > 0 && tileCenterLat !== null && tileCenterLng !== null) {
        tileCentersRef.current[tileId] = {
          lat: tileCenterLat,
          lng: tileCenterLng
        }
      }
      
      // Track load time to prevent immediate eviction
      tileLoadTimesRef.current[tileId] = Date.now()
      
      return true
    } catch (err) {
      console.warn(`Failed to load tile ${tileId}:`, err.message)
      return false
    }
  }

  // Preload in progress flag to prevent concurrent executions
  const preloadInProgressRef = useRef(false)

  // Preload adjacent tiles for smoother panning (background operation)
  const preloadAdjacentTiles = async () => {
    if (preloadInProgressRef.current) return
    preloadInProgressRef.current = true
    
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) {
      preloadInProgressRef.current = false
      return
    }
    
    // Get camera look-at ground point for preloading (same as main loading)
    let cameraLat, cameraLng
    const preCanvas = viewer.scene.canvas
    const preRay = viewer.camera.getPickRay(new Cesium.Cartesian2(preCanvas.clientWidth / 2, preCanvas.clientHeight / 2))
    if (preRay) {
      const gp = viewer.scene.globe.pick(preRay, viewer.scene)
      if (gp) {
        const gc = Cesium.Cartographic.fromCartesian(gp)
        cameraLat = Cesium.Math.toDegrees(gc.latitude)
        cameraLng = Cesium.Math.toDegrees(gc.longitude)
      }
    }
    if (cameraLat == null) {
      const cameraCartographic = Cesium.Cartographic.fromCartesian(viewer.camera.position)
      cameraLng = Cesium.Math.toDegrees(cameraCartographic.longitude)
      cameraLat = Cesium.Math.toDegrees(cameraCartographic.latitude)
    }
    
    // Double the radius for preloading
    const preloadRadius = (BUILDING_LOAD_RADIUS_KM * 2) / 111.0
    
    const bbox = {
      min_lng: cameraLng - preloadRadius,
      min_lat: cameraLat - preloadRadius,
      max_lng: cameraLng + preloadRadius,
      max_lat: cameraLat + preloadRadius
    }
    
    try {
      const params = new URLSearchParams(bbox)
      const response = await fetch(`${TILES_API}?${params}`)
      if (!response.ok) return
      
      const data = await response.json()
      const unloadedTiles = data.tiles.filter(t => !loadedTilesRef.current.has(t.id))
      
      if (unloadedTiles.length === 0) return
      
      // Only preload up to 5 tiles to avoid overwhelming
      const tilesToPreload = unloadedTiles.slice(0, 5)
      
      // Load sequentially to avoid blocking main thread
      for (const tile of tilesToPreload) {
        if (!viewer.isDestroyed()) {
          await loadTile(tile.id, tile.url, cameraLat, cameraLng)
        }
      }
      
      if (tilesToPreload.length > 0) {
        console.log(`🔮 Preloaded ${tilesToPreload.length} adjacent tiles`)
      }
    } catch (err) {
      // Silently fail for preloading - not critical
    } finally {
      preloadInProgressRef.current = false
    }
  }

  // Load tiles for current viewport (progressive, persistent) with building limit
  const loadTilesForViewport = async () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    if (loadingBuildingsRef.current) return // Ref-based guard for stale closures

    // Get camera look-at point on ground (not eye position) for correct building loading
    let cameraLat, cameraLng, cameraHeight
    
    // Try to get the point the camera is looking at on the ground
    const canvas = viewer.scene.canvas
    const centerRay = viewer.camera.getPickRay(new Cesium.Cartesian2(canvas.clientWidth / 2, canvas.clientHeight / 2))
    if (centerRay) {
      const groundPoint = viewer.scene.globe.pick(centerRay, viewer.scene)
      if (groundPoint) {
        const groundCarto = Cesium.Cartographic.fromCartesian(groundPoint)
        cameraLat = Cesium.Math.toDegrees(groundCarto.latitude)
        cameraLng = Cesium.Math.toDegrees(groundCarto.longitude)
        cameraHeight = Cesium.Cartographic.fromCartesian(viewer.camera.position).height
      }
    }
    
    // Fallback to camera eye position if pick fails
    if (cameraLat == null || cameraLng == null) {
      const cameraCartographic = Cesium.Cartographic.fromCartesian(viewer.camera.position)
      cameraHeight = cameraCartographic.height
      cameraLng = Cesium.Math.toDegrees(cameraCartographic.longitude)
      cameraLat = Cesium.Math.toDegrees(cameraCartographic.latitude)
    }

    // Adaptive load radius based on camera height
    const baseRadius = BUILDING_LOAD_RADIUS_KM / 111.0
    const heightFactor = Math.min(cameraHeight / 5000, 2.0) // Scale up for higher views
    const loadRadius = baseRadius * Math.max(0.5, heightFactor)

    // Load only tiles within radius of camera look-at point
    const bbox = {
      min_lng: cameraLng - loadRadius,
      min_lat: cameraLat - loadRadius,
      max_lng: cameraLng + loadRadius,
      max_lat: cameraLat + loadRadius
    }

    // Haversine distance calculator for prioritizing tiles by distance
    const haversineDistance = (lat1, lng1, lat2, lng2) => {
      const R = 6371 // Earth radius in km
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLng = (lng2 - lng1) * Math.PI / 180
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLng/2) * Math.sin(dLng/2)
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    }

    // Calculate current total building count
    let currentBuildingCount = Object.values(tileEntitiesRef.current)
      .reduce((sum, entities) => sum + entities.length, 0)

    try {
      // Get tiles for viewport
      const params = new URLSearchParams(bbox)
      const response = await fetch(`${TILES_API}?${params}`)

      if (!response.ok) {
        console.warn('Tiles API not available:', response.status)
        return
      }

      const data = await response.json()

      // FIX Issue 1: Filter out empty tiles (count === 0) and already-loaded tiles
      let newTiles = (data.tiles || []).filter(t => t.count > 0 && !loadedTilesRef.current.has(t.id))

      if (newTiles.length === 0) {
        console.log(`[Buildings] All ${data.tiles.length} tiles already loaded, ${currentBuildingCount} buildings showing`)
        return // All tiles already loaded
      }

      // Sort tiles by distance from camera (closest first for priority loading)
      newTiles = newTiles.map(tile => {
        const tileLng = (tile.min_lng + tile.max_lng) / 2
        const tileLat = (tile.min_lat + tile.max_lat) / 2
        const distance = haversineDistance(cameraLat, cameraLng, tileLat, tileLng)
        return { ...tile, distance }
      }).sort((a, b) => a.distance - b.distance)

      // Calculate how many buildings we can still load
      const remainingBuildingSlots = MAX_BUILDINGS_DISPLAY - currentBuildingCount
      if (remainingBuildingSlots <= 0) {
        console.log(`⛔ Building limit reached (${MAX_BUILDINGS_DISPLAY}). Not loading new tiles.`)
        return
      }

      // Estimate buildings per tile (average ~50 per tile)
      const avgBuildingsPerTile = 50
      const maxTilesToLoad = Math.min(
        Math.ceil(remainingBuildingSlots / avgBuildingsPerTile),
        20 // Max 20 tiles per load for better coverage
      )

      const tilesToLoad = newTiles.slice(0, maxTilesToLoad)

      if (tilesToLoad.length === 0) return

      setLoadingBuildings(true)
      loadingBuildingsRef.current = true

      // Update agentData loading state
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          loadingBuildings: true
        }))
      }

      // Load tiles in parallel batches - conservative batch size for stability
      const batchSize = 6 // Balanced for speed without overwhelming
      let loadedCount = 0
      let buildingsLoaded = 0

      for (let i = 0; i < tilesToLoad.length; i += batchSize) {
        // Check if we're approaching the limit
        const currentCount = Object.values(tileEntitiesRef.current)
          .reduce((sum, entities) => sum + entities.length, 0)
        if (currentCount >= MAX_BUILDINGS_DISPLAY) {
          console.log(`⛔ Stopping tile load: Building limit reached`)
          break
        }

        const batch = tilesToLoad.slice(i, i + batchSize)
        const results = await Promise.all(
          batch.map(tile => loadTile(tile.id, tile.url, cameraLat, cameraLng))
        )
        loadedCount += results.filter(r => r).length

        // Count buildings in this batch
        batch.forEach(tile => {
          const entities = tileEntitiesRef.current[tile.id]
          if (entities) {
            buildingsLoaded += entities.length
            tileBuildingCountsRef.current[tile.id] = entities.length
          }
        })
      }

      // Update counts
      const totalBuildings = Object.values(tileEntitiesRef.current)
        .reduce((sum, entities) => sum + entities.length, 0)

      setBuildingsCount(totalBuildings)
      setTilesLoaded(loadedTilesRef.current.size)
      setBuildingsLoaded(true)
      setLoadingBuildings(false)
      loadingBuildingsRef.current = false

      // Update agentData with building stats
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          buildingsCount: totalBuildings,
          loadingBuildings: false
        }))
      }

      if (loadedCount > 0) {
        console.log(`🏢 Loaded ${loadedCount} tiles (${buildingsLoaded} new buildings, ${totalBuildings} total)`)
      }
    } catch (err) {
      console.warn('Failed to load tiles:', err.message)
      setLoadingBuildings(false)
      loadingBuildingsRef.current = false
    }
  }

  // Clear ALL loaded building tiles from the scene
  const clearAllBuildings = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return 0
    let cleared = 0
    viewer.entities.suspendEvents()
    try {
      for (const tileId of loadedTilesRef.current) {
        const entities = tileEntitiesRef.current[tileId] || []
        entities.forEach(entity => { try { viewer.entities.remove(entity) } catch (_) {} })
        cleared += entities.length
      }
      tileEntitiesRef.current = {}
      tileCentersRef.current = {}
      tileLoadTimesRef.current = {}
      tileBuildingCountsRef.current = {}
      loadedTilesRef.current.clear()
    } finally {
      viewer.entities.resumeEvents()
    }
    if (cleared > 0) {
      setBuildingsCount(0)
      setTilesLoaded(0)
      console.log(`🗑️ Cleared all ${cleared} buildings from scene`)
    }
    return cleared
  }

  // Enforce building limit and memory pressure - returns number of buildings cleared
  const enforceBuildingLimits = (currentCenterLat, currentCenterLng) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return 0
    
    const totalBuildings = Object.values(tileEntitiesRef.current)
      .reduce((sum, entities) => sum + entities.length, 0)
    
    // Check memory pressure
    const memPressure = getMemoryPressure()
    let needsAggressiveCleanup = memPressure.level === 'critical'
    let needsModerateCleanup = memPressure.level === 'warning'
    
    if (memPressure.level !== 'unknown' && memPressure.level !== 'normal') {
      console.log(`[Memory] ⚠️ Memory pressure: ${memPressure.level} (${memPressure.usedRatio} used)`)
    }
    
    // Check if we're over the building limit
    const overLimit = totalBuildings > MAX_BUILDINGS_DISPLAY
    
    if (!overLimit && !needsAggressiveCleanup && !needsModerateCleanup) {
      return 0 // No cleanup needed
    }
    
    // Calculate how many buildings to remove
    let targetRemoval = 0
    if (overLimit) {
      targetRemoval = totalBuildings - MAX_BUILDINGS_DISPLAY + 5000 // Remove extra buffer
    }
    if (needsAggressiveCleanup) {
      targetRemoval = Math.max(targetRemoval, Math.floor(totalBuildings * 0.4)) // Remove 40%
    } else if (needsModerateCleanup) {
      targetRemoval = Math.max(targetRemoval, Math.floor(totalBuildings * 0.2)) // Remove 20%
    }
    
    if (targetRemoval === 0) return 0
    
    console.log(`[Memory] 🧹 Enforcing limits: ${totalBuildings} buildings, removing ~${targetRemoval}`)
    
    // Sort tiles by distance from current center (furthest first)
    const tileDistances = []
    for (const [tileId, center] of Object.entries(tileCentersRef.current)) {
      if (currentCenterLat && currentCenterLng) {
        const dist = getDistanceKm(currentCenterLat, currentCenterLng, center.lat, center.lng)
        tileDistances.push({ tileId, distance: dist, count: tileBuildingCountsRef.current[tileId] || 0 })
      }
    }
    
    // Sort by distance (furthest first)
    tileDistances.sort((a, b) => b.distance - a.distance)
    
    let removed = 0
    const tilesToRemove = []
    
    for (const tile of tileDistances) {
      if (removed >= targetRemoval) break
      tilesToRemove.push(tile.tileId)
      removed += tile.count
    }
    
    // Remove the tiles
    viewer.entities.suspendEvents()
    try {
      for (const tileId of tilesToRemove) {
        const entities = tileEntitiesRef.current[tileId] || []
        entities.forEach(entity => { try { viewer.entities.remove(entity) } catch (_) {} })
        
        delete tileEntitiesRef.current[tileId]
        delete tileCentersRef.current[tileId]
        delete tileLoadTimesRef.current[tileId]
        delete tileBuildingCountsRef.current[tileId]
        loadedTilesRef.current.delete(tileId)
      }
    } finally {
      viewer.entities.resumeEvents()
    }
    
    const newTotal = Object.values(tileEntitiesRef.current)
      .reduce((sum, entities) => sum + entities.length, 0)
    
    setBuildingsCount(newTotal)
    setTilesLoaded(loadedTilesRef.current.size)
    
    console.log(`[Memory] ✅ Cleaned ${removed} buildings from ${tilesToRemove.length} tiles (${newTotal} remaining)`)
    
    return removed
  }

  // AbortController for cancelling in-progress building loads
  const buildingLoadAbortControllerRef = useRef(null)
  
  // Track current building center for incremental loading
  const currentBuildingCenterRef = useRef(null)

  // Update LOD quality for existing buildings based on new center
  const updateBuildingsLOD = (newCenterLat, newCenterLng) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || !viewer.entities) return 0
    
    let updatedCount = 0
    viewer.entities.suspendEvents()
    try {
      viewer.entities.values.forEach(entity => {
        if (entity.properties && entity.properties.lng && entity.properties.lat) {
          const entityLng = entity.properties.lng.getValue()
          const entityLat = entity.properties.lat.getValue()
          const distanceKm = getDistanceKm(newCenterLat, newCenterLng, entityLat, entityLng)
          const shouldBeHighQuality = distanceKm <= BUILDING_HIGH_QUALITY_RADIUS_KM
          
          // Only update if LOD status changed
          if (entity.properties.isHighQuality && entity.properties.isHighQuality.getValue() !== shouldBeHighQuality) {
            entity.properties.isHighQuality.setValue(shouldBeHighQuality)
            
            // Update polygon appearance
            if (entity.polygon) {
              const height = entity.properties.height ? entity.properties.height.getValue() : 10
              let color = '#c4b5fd'
              let alpha = 0.75
              
              if (shouldBeHighQuality) {
                // High quality colors
                if (height > 50) { color = '#a78bfa'; alpha = 0.85 }
                else if (height > 30) { color = '#b8a5f8'; alpha = 0.80 }
                else if (height > 15) { color = '#c4b5fd'; alpha = 0.75 }
                else if (height > 8) { color = '#d8cdf7'; alpha = 0.70 }
                else { color = '#e9e3f8'; alpha = 0.65 }
                
                entity.polygon.outline = true
                entity.polygon.closeTop = true
                entity.polygon.shadows = Cesium.ShadowMode.CAST_ONLY
              } else {
                // Lower quality colors
                if (height > 50) { color = '#a78bfa'; alpha = 0.55 }
                else if (height > 30) { color = '#b8a5f8'; alpha = 0.50 }
                else if (height > 15) { color = '#c4b5fd'; alpha = 0.45 }
                else if (height > 8) { color = '#d8cdf7'; alpha = 0.40 }
                else { color = '#e9e3f8'; alpha = 0.35 }
                
                entity.polygon.outline = false
                entity.polygon.closeTop = false
                entity.polygon.shadows = Cesium.ShadowMode.DISABLED
              }
              
              entity.polygon.material = Cesium.Color.fromCssColorString(color).withAlpha(alpha)
            }
            updatedCount++
          }
        }
      })
    } finally {
      viewer.entities.resumeEvents()
    }
    return updatedCount
  }

  // Clear buildings that are too far from the new center
  const clearDistantBuildings = (newCenterLat, newCenterLng, maxDistanceKm) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return 0
    
    let cleared = 0
    const tilesToRemove = []
    
    viewer.entities.suspendEvents()
    try {
      // Check each tile's center distance
      for (const tileId of loadedTilesRef.current) {
        const tileCenter = tileCentersRef.current[tileId]
        if (tileCenter) {
          const distance = getDistanceKm(newCenterLat, newCenterLng, tileCenter.lat, tileCenter.lng)
          if (distance > maxDistanceKm * 1.5) { // Add 50% buffer to avoid thrashing
            tilesToRemove.push(tileId)
          }
        }
      }
      
      // Remove distant tiles
      for (const tileId of tilesToRemove) {
        const entities = tileEntitiesRef.current[tileId] || []
        entities.forEach(entity => { 
          try { viewer.entities.remove(entity) } catch (_) {} 
        })
        cleared += entities.length
        
        delete tileEntitiesRef.current[tileId]
        delete tileCentersRef.current[tileId]
        delete tileLoadTimesRef.current[tileId]
        delete tileBuildingCountsRef.current[tileId]
        loadedTilesRef.current.delete(tileId)
      }
    } finally {
      viewer.entities.resumeEvents()
    }
    
    if (cleared > 0) {
      console.log(`🗑️ Cleared ${cleared} buildings from ${tilesToRemove.length} distant tiles`)
    }
    return cleared
  }

  // Load buildings in specified radius around a point (incremental implementation)
  // @param {number} centerLat - Latitude of center point
  // @param {number} centerLng - Longitude of center point
  // @param {number} radiusKm - Radius in kilometers (default 1.0)
  const loadBuildingsAtPoint = async (centerLat, centerLng, radiusKm = 1.0) => {
    console.log(`[loadBuildingsAtPoint] 🚀 START - lat: ${centerLat}, lng: ${centerLng}, radius: ${radiusKm}km`)
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) {
      console.log('[loadBuildingsAtPoint] ❌ ABORT - viewer not ready')
      return
    }

    // Validate coordinates
    if (!Number.isFinite(centerLat) || !Number.isFinite(centerLng)) {
      console.error('[loadBuildingsAtPoint] ❌ Invalid coordinates:', centerLat, centerLng)
      return
    }

    // Check if this is an incremental update (nearby location)
    const prevCenter = currentBuildingCenterRef.current
    let isIncrementalUpdate = false
    let distanceFromPrevCenter = 0
    
    if (prevCenter) {
      distanceFromPrevCenter = getDistanceKm(prevCenter.lat, prevCenter.lng, centerLat, centerLng)
      // If new center is within the load radius, this is an incremental update
      isIncrementalUpdate = distanceFromPrevCenter < radiusKm * 0.5
      console.log(`[loadBuildingsAtPoint] 📍 Distance from previous center: ${distanceFromPrevCenter.toFixed(2)}km (incremental: ${isIncrementalUpdate})`)
    }

    // Cancel any in-progress load
    if (buildingLoadAbortControllerRef.current) {
      buildingLoadAbortControllerRef.current.abort()
      buildingLoadAbortControllerRef.current = null
    }
    loadingBuildingsRef.current = false
    setLoadingBuildings(false)

    // For incremental updates: keep nearby buildings, only clear distant ones
    if (isIncrementalUpdate) {
      console.log('[loadBuildingsAtPoint] 🔄 Incremental update - keeping nearby buildings')
      clearDistantBuildings(centerLat, centerLng, radiusKm)
      
      // Update LOD for existing buildings based on new center
      const updatedLOD = updateBuildingsLOD(centerLat, centerLng)
      if (updatedLOD > 0) {
        console.log(`[loadBuildingsAtPoint] 🎨 Updated LOD for ${updatedLOD} buildings`)
      }
    } else {
      // Full clear for distant locations
      console.log('[loadBuildingsAtPoint] 🧹 Full clear - location too far from previous')
      clearAllBuildings()
    }
    
    // Update current center
    currentBuildingCenterRef.current = { lat: centerLat, lng: centerLng }
    
    // Check memory pressure before loading - enforce limits if needed
    const memPressure = getMemoryPressure()
    if (memPressure.level === 'critical') {
      console.log(`[loadBuildingsAtPoint] ⚠️ Critical memory pressure (${memPressure.usedRatio}) - aggressive cleanup before loading`)
      enforceBuildingLimits(centerLat, centerLng)
    }
    
    // Create new AbortController
    buildingLoadAbortControllerRef.current = new AbortController()
    const signal = buildingLoadAbortControllerRef.current.signal

    const radiusDeg = radiusKm / 111.0
    const bbox = {
      min_lng: centerLng - radiusDeg,
      min_lat: centerLat - radiusDeg,
      max_lng: centerLng + radiusDeg,
      max_lat: centerLat + radiusDeg
    }

    try {
      const params = new URLSearchParams(bbox)
      const tilesUrl = `${TILES_API}?${params}`
      console.log(`[loadBuildingsAtPoint] 📡 Fetching tiles from: ${tilesUrl}`)
      
      const response = await fetch(tilesUrl, { signal })
      if (response.ok === false) {
        console.error(`[loadBuildingsAtPoint] ❌ Failed to fetch tiles: ${response.status} ${response.statusText}`)
        return
      }

      const data = await response.json()
      const allTiles = data.tiles || []
      // Filter out empty tiles (count === 0) and already loaded tiles
      const nonEmptyTiles = allTiles.filter(t => t.count > 0 && !loadedTilesRef.current.has(t.id))
      console.log(`[loadBuildingsAtPoint] 📦 Found ${allTiles.length} tiles (${nonEmptyTiles.length} new to load, ${loadedTilesRef.current.size} already loaded)`)
      
      if (nonEmptyTiles.length === 0) {
        console.log(`[loadBuildingsAtPoint] ✅ All tiles already loaded for this area`)
        return
      }

      // Sort by distance from center (closest first)
      const sortedTiles = nonEmptyTiles.map(tile => {
        const tileLng = (tile.min_lng + tile.max_lng) / 2
        const tileLat = (tile.min_lat + tile.max_lat) / 2
        return { ...tile, distance: getDistanceKm(centerLat, centerLng, tileLat, tileLng) }
      }).sort((a, b) => a.distance - b.distance)

      // Load up to 25 tiles
      const tilesToLoad = sortedTiles.slice(0, 25)
      console.log(`[loadBuildingsAtPoint] 🔄 Loading ${tilesToLoad.length} new tiles...`)

      setLoadingBuildings(true)
      loadingBuildingsRef.current = true
      if (setAgentData) setAgentData(prev => ({ ...prev, loadingBuildings: true }))

      let loadedCount = 0
      let buildingsAdded = 0

      // Load tiles in batches - pass center coordinates for LOD calculation
      const batchSize = 6
      for (let i = 0; i < tilesToLoad.length; i += batchSize) {
        const batch = tilesToLoad.slice(i, i + batchSize)
        const results = await Promise.all(batch.map(tile => loadTile(tile.id, tile.url, centerLat, centerLng)))
        loadedCount += results.filter(r => r).length

        batch.forEach(tile => {
          const entities = tileEntitiesRef.current[tile.id]
          if (entities) {
            buildingsAdded += entities.length
          }
        })
      }

      const totalBuildings = Object.values(tileEntitiesRef.current).reduce((s, e) => s + e.length, 0)
      
      // Enforce building limits and memory pressure after loading
      enforceBuildingLimits(centerLat, centerLng)
      
      const finalTotal = Object.values(tileEntitiesRef.current).reduce((s, e) => s + e.length, 0)
      
      console.log(`[loadBuildingsAtPoint] ✅ COMPLETE - ${loadedCount} tiles, ${buildingsAdded} buildings loaded, ${finalTotal} total`)
      
      setBuildingsCount(finalTotal)
      setTilesLoaded(loadedTilesRef.current.size)
      setBuildingsLoaded(true)
      setLoadingBuildings(false)
      loadingBuildingsRef.current = false
      
      if (setAgentData) {
        setAgentData(prev => ({ 
          ...prev, 
          buildingsCount: finalTotal, 
          loadingBuildings: false,
          tilesLoaded: loadedTilesRef.current.size 
        }))
      }
    } catch (err) {
      // Handle abort gracefully - don't treat as an error
      if (err.name === 'AbortError') {
        console.log('[loadBuildingsAtPoint] ⚠️ Load was aborted (likely by a new query)')
      } else {
        console.error('[loadBuildingsAtPoint] ❌ ERROR:', err.message, err.stack)
      }
      setLoadingBuildings(false)
      loadingBuildingsRef.current = false
    }
  }

  // Keep refs in sync for camera listener closure
  const loadBuildingsAtPointRef = useRef(loadBuildingsAtPoint)
  const loadTilesForViewportRef = useRef(loadTilesForViewport)
  const preloadAdjacentTilesRef = useRef(preloadAdjacentTiles)
  useEffect(() => {
    loadBuildingsAtPointRef.current = loadBuildingsAtPoint
    loadTilesForViewportRef.current = loadTilesForViewport
    preloadAdjacentTilesRef.current = preloadAdjacentTiles
  })
  useEffect(() => {
    showBuildingsRef.current = showBuildings
  }, [showBuildings])

  // Handle flyTo commands from chat
  useEffect(() => {
    if (agentData?.flyTo && viewerRef.current) {
      // Skip flyTo only if user recently left-clicked on map (within 3 seconds)
      // But allow flyTo for building right-clicks (which set selectedLocation)
      const timeSinceBuildingClick = Date.now() - (placeMarkerClickTimeRef.current || 0)
      const isBuildingSelection = agentData?.selectedLocation && !agentData?.clickedLocation
      
      if (agentData?.clickedLocation && timeSinceBuildingClick < 3000 && !isBuildingSelection) {
        console.log('[Map] ⏭️ Skipping flyTo - user recently clicked on map')
        // Clear the flyTo so it doesn't trigger again
        setTimeout(() => { if (setAgentData) setAgentData(prev => ({ ...prev, flyTo: null })) }, 100)
        return
      }
      
      const { lat, lng, zoom } = agentData.flyTo
      console.log(`[Map] flyTo useEffect triggered: lat=${lat}, lng=${lng}, zoom=${zoom}`)
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return

      const latNum = Number(lat)
      const lngNum = Number(lng)
      console.log(`[Map] flyTo coordinates: latNum=${latNum}, lngNum=${lngNum}`)
      if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) {
        console.warn('[Map] flyTo ABORT - invalid coordinates')
        return
      }

      // Stop any active rotation before flying to new location
      stopRotation()
      try { viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY) } catch (_) {}

      const camera = viewer.camera
      lastCameraViewRef.current = {
        destination: Cesium.Cartesian3.clone(camera.position),
        heading: camera.heading,
        pitch: camera.pitch,
        roll: camera.roll
      }
      setCanGoBack(true)
      
      // height calculation for closer zoom (production grade)
      const height = zoom ? Math.max(50, 15000000 / Math.pow(2, zoom)) : 400
      
      // FIX: Don't overwrite marker if user recently clicked (within 5 seconds)
      const timeSinceLastClick = Date.now() - (placeMarkerClickTimeRef.current || 0)
      const skipMarkerUpdate = timeSinceLastClick < 5000 // 5 seconds grace period
      
      if (placeMarkerRef.current && !skipMarkerUpdate) {
        viewer.entities.remove(placeMarkerRef.current)
        placeMarkerRef.current = null
      }

      // Only create new marker if user hasn't recently clicked
      if (!skipMarkerUpdate) {
        placeMarkerRef.current = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lngNum, latNum),
        point: {
          pixelSize: 12,
          color: Cesium.Color.fromCssColorString('#8b5cf6'),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      })
      } // end if (!skipMarkerUpdate)

      // Terrain-aware camera height
      const terrainHeight = getTerrainHeight(lngNum, latNum)
      const adjustedHeight = height + terrainHeight
      
      // Set rotation target for orbit during analysis
      rotationTargetRef.current = getTerrainAwareTarget(lngNum, latNum)
      
      // Ensure buildings layer is ON so loaded buildings are visible
      if (!showBuildingsRef.current) {
        setShowBuildings(true)
        showBuildingsRef.current = true
      }

      // Force-reset loading guard in case a previous load got stuck
      loadingBuildingsRef.current = false

      // Load buildings at the flyTo location
      const triggerBuildingLoad = () => {
        console.log(`[Map] 🏢 Loading buildings at flyTo location: lat=${latNum}, lng=${lngNum}`)
        loadBuildingsAtPointRef.current(latNum, lngNum, BUILDING_LOAD_RADIUS_KM)
      }

      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lngNum, latNum, adjustedHeight),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-45),
          roll: 0
        },
        duration: 2.0,
        complete: () => {
          // Load buildings after camera arrives
          setTimeout(triggerBuildingLoad, 300)
        }
      })
      // Fallback disabled: only query-based loading
      // setTimeout(triggerBuildingLoad, 2800)
      // Clear flyTo after camera flight + building load completes
      setTimeout(() => { if (setAgentData) setAgentData(prev => ({ ...prev, flyTo: null })) }, 5000)
    }
  }, [agentData?.flyTo, setAgentData])

  // Track property markers for highlighting
  const propertyMarkersRef = useRef([])

  // Listen for map commands
  useEffect(() => {
    const handleMapCommand = (e) => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return
      
      const { action, coordinates, zoom, properties } = e.detail || {}
      
      // Handle highlightProperties action for map sync
      if (action === 'highlightProperties' && properties && Array.isArray(properties)) {
        // Clear previous property markers
        propertyMarkersRef.current.forEach(entity => {
          try { viewer.entities.remove(entity) } catch {}
        })
        propertyMarkersRef.current = []
        
        // Create canvas-rendered property billboard
        const createPropertyCanvas = (index, bhk, price, type) => {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          const dpr = 2 // High-DPI
          
          // Layout
          const priceText = price ? `₹${price >= 10000000 ? (price / 10000000).toFixed(1) + 'Cr' : (price / 100000).toFixed(0) + 'L'}` : ''
          const bhkText = bhk ? `${bhk}BHK` : ''
          const typeText = type ? String(type).substring(0, 12) : ''
          const line1 = [bhkText, typeText].filter(Boolean).join(' · ') || `Property ${index + 1}`
          const line2 = priceText
          
          ctx.font = `bold ${13 * dpr}px Inter, system-ui, sans-serif`
          const w1 = ctx.measureText(line1).width
          ctx.font = `bold ${15 * dpr}px Inter, system-ui, sans-serif`
          const w2 = line2 ? ctx.measureText(line2).width : 0
          
          const padX = 14 * dpr
          const padY = 8 * dpr
          const gap = line2 ? 4 * dpr : 0
          const lineH1 = 16 * dpr
          const lineH2 = line2 ? 18 * dpr : 0
          const indexW = 24 * dpr
          const w = Math.max(w1, w2) + padX * 2 + indexW + 8 * dpr
          const h = padY * 2 + lineH1 + gap + lineH2
          const pointerH = 8 * dpr
          
          canvas.width = w
          canvas.height = h + pointerH
          
          // Background with subtle gradient
          const grad = ctx.createLinearGradient(0, 0, 0, h)
          grad.addColorStop(0, 'rgba(15, 23, 42, 0.95)')
          grad.addColorStop(1, 'rgba(30, 41, 59, 0.95)')
          
          // Rounded rect
          const r = 6 * dpr
          ctx.beginPath()
          ctx.moveTo(r, 0)
          ctx.lineTo(w - r, 0)
          ctx.quadraticCurveTo(w, 0, w, r)
          ctx.lineTo(w, h - r)
          ctx.quadraticCurveTo(w, h, w - r, h)
          ctx.lineTo(w / 2 + pointerH, h)
          ctx.lineTo(w / 2, h + pointerH)
          ctx.lineTo(w / 2 - pointerH, h)
          ctx.lineTo(r, h)
          ctx.quadraticCurveTo(0, h, 0, h - r)
          ctx.lineTo(0, r)
          ctx.quadraticCurveTo(0, 0, r, 0)
          ctx.closePath()
          ctx.fillStyle = grad
          ctx.fill()
          
          // Left accent border
          ctx.fillStyle = '#8b5cf6'
          ctx.fillRect(0, 6 * dpr, 3 * dpr, h - 12 * dpr)
          
          // Index badge
          const badgeX = padX - 2 * dpr
          const badgeY = padY
          const badgeR = 10 * dpr
          ctx.beginPath()
          ctx.arc(badgeX + badgeR, badgeY + badgeR, badgeR, 0, Math.PI * 2)
          ctx.fillStyle = '#8b5cf6'
          ctx.fill()
          ctx.font = `bold ${11 * dpr}px Inter, system-ui, sans-serif`
          ctx.fillStyle = '#ffffff'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(String(index + 1), badgeX + badgeR, badgeY + badgeR)
          
          // Line 1: BHK · Type
          const textX = badgeX + badgeR * 2 + 8 * dpr
          ctx.textAlign = 'left'
          ctx.textBaseline = 'top'
          ctx.font = `600 ${13 * dpr}px Inter, system-ui, sans-serif`
          ctx.fillStyle = '#e2e8f0'
          ctx.fillText(line1, textX, padY + 2 * dpr)
          
          // Line 2: Price (if exists)
          if (line2) {
            ctx.font = `bold ${15 * dpr}px Inter, system-ui, sans-serif`
            ctx.fillStyle = '#a78bfa'
            ctx.fillText(line2, textX, padY + lineH1 + gap)
          }
          
          return canvas
        }
        
        // Add new property markers with modern design
        // Group properties by coordinate so overlapping ones stack vertically
        const coordGroups = {}
        properties.forEach((prop, index) => {
          if (!prop.lat || !prop.lng) return
          const key = `${Number(prop.lat).toFixed(5)}_${Number(prop.lng).toFixed(5)}`
          if (!coordGroups[key]) coordGroups[key] = []
          coordGroups[key].push({ ...prop, _originalIndex: index })
        })

        let firstProp = null
        Object.values(coordGroups).forEach(group => {
          group.forEach((prop, stackIndex) => {
            if (!firstProp) firstProp = prop
            const index = prop._originalIndex
            
            const canvas = createPropertyCanvas(
              index,
              prop.bedrooms,
              prop.price,
              prop.property_type || prop.type
            )
            
            // Stack vertically: each card at same coord gets 60m height offset
            const verticalOffset = stackIndex * 60
            
            const marker = viewer.entities.add({
              name: `property_marker_${index}`,
              position: Cesium.Cartesian3.fromDegrees(prop.lng, prop.lat, verticalOffset),
              billboard: {
                image: canvas,
                width: canvas.width / 2,
                height: canvas.height / 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
                heightReference: verticalOffset > 0 ? Cesium.HeightReference.RELATIVE_TO_GROUND : Cesium.HeightReference.CLAMP_TO_GROUND,
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
                scaleByDistance: new Cesium.NearFarScalar(500, 1.0, 15000, 0.5),
                translucencyByDistance: new Cesium.NearFarScalar(500, 1.0, 25000, 0.3),
                eyeOffset: new Cesium.Cartesian3(0, 0, -(index * 0.5))
              },
              properties: {
                isPropertyMarker: true,
                propertyIndex: index,
                propertyData: JSON.stringify(prop)
              }
            })
            propertyMarkersRef.current.push(marker)
          })
        })
        
        // Also trigger building load at the center of properties
        if (firstProp && loadBuildingsAtPointRef.current) {
          loadingBuildingsRef.current = false
          loadBuildingsAtPointRef.current(Number(firstProp.lat), Number(firstProp.lng), BUILDING_LOAD_RADIUS_KM)
        }
        return
      }
      
      if (action === 'center' && coordinates && coordinates.length === 2) {
        const [lat, lng] = coordinates
        const latNum = Number(lat)
        const lngNum = Number(lng)
        if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) return

        const camera = viewer.camera
        lastCameraViewRef.current = {
          destination: Cesium.Cartesian3.clone(camera.position),
          heading: camera.heading,
          pitch: camera.pitch,
          roll: camera.roll
        }
        setCanGoBack(true)

        if (placeMarkerRef.current) {
          viewer.entities.remove(placeMarkerRef.current)
          placeMarkerRef.current = null
        }

        placeMarkerRef.current = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(lngNum, latNum),
          point: {
            pixelSize: 12,
            color: Cesium.Color.fromCssColorString('#8b5cf6'),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        })

        const height = zoom ? Math.max(100, 20000 / Math.pow(2, zoom)) : 600
        // Terrain-aware camera height
        const terrainHeight = getTerrainHeight(lngNum, latNum)
        const adjustedHeight = height + terrainHeight
        
        // Ensure buildings layer is ON
        if (!showBuildingsRef.current) {
          setShowBuildings(true)
          showBuildingsRef.current = true
        }
        loadingBuildingsRef.current = false

        let centerBuildingsTriggered = false
        const triggerCenterBuildings = () => {
          if (centerBuildingsTriggered) return
          centerBuildingsTriggered = true
          loadBuildingsAtPointRef.current(latNum, lngNum, BUILDING_LOAD_RADIUS_KM)
        }

        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lngNum, latNum, adjustedHeight),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
            roll: 0
          },
          duration: 2.5,
          complete: () => setTimeout(triggerCenterBuildings, 500)
        })
        setTimeout(triggerCenterBuildings, 3500)
      }
    }
    
    // Agentic step visual feedback — pulse ring on map during autonomous reasoning
    const pulseEntityRef = { current: null }
    const handleAgenticStep = (e) => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return

      const selectedLoc = selectedLocationRef.current || selectedBuildingCoordsRef.current
      if (!selectedLoc?.lat || !selectedLoc?.lng) return

      // Remove previous pulse
      if (pulseEntityRef.current) {
        try { viewer.entities.remove(pulseEntityRef.current) } catch (_) {}
      }

      // Add expanding pulse ring at analysis location
      const center = Cesium.Cartesian3.fromDegrees(selectedLoc.lng, selectedLoc.lat)
      pulseEntityRef.current = viewer.entities.add({
        position: center,
        ellipse: {
          semiMajorAxis: 200,
          semiMinorAxis: 200,
          height: 0,
          material: Cesium.Color.fromCssColorString('#8b5cf6').withAlpha(0.15),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#8b5cf6').withAlpha(0.6),
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        }
      })

      // Auto-remove pulse after 2 seconds
      setTimeout(() => {
        if (pulseEntityRef.current) {
          try { viewer.entities.remove(pulseEntityRef.current) } catch (_) {}
          pulseEntityRef.current = null
        }
      }, 2000)
    }

    window.addEventListener('valora-map-command', handleMapCommand)
    window.addEventListener('valora-ui-command', handleMapCommand)
    window.addEventListener('valora-agentic-step', handleAgenticStep)
    
    // FIX Issue 2 & 3: Listen for new query events to clear old markers and reset state
    const handleNewQuery = (e) => {
      console.log('[Map] 🔄 New query detected - clearing old property markers and place marker')
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return
      
      // Check if this query was triggered by a map click
      const isMapClickQuery = e?.detail?.source === 'map-click' || 
                              (e?.detail?.coordinates && e?.detail?.skipFlyTo)
      
      // Clear all property markers from previous query
      propertyMarkersRef.current.forEach(entity => {
        try { viewer.entities.remove(entity) } catch {}
      })
      propertyMarkersRef.current = []
      
      // Clear place marker from previous query - BUT NOT if just placed by map click
      // Check if marker was placed in the last 5 seconds (prevents clearing during map click flow)
      const timeSinceClick = Date.now() - (placeMarkerClickTimeRef.current || 0)
      if (placeMarkerRef.current && timeSinceClick > 5000) {
        try { viewer.entities.remove(placeMarkerRef.current) } catch {}
        placeMarkerRef.current = null
      } else if (placeMarkerRef.current) {
        console.log('[Map] Preserving place marker - was just placed by map click', timeSinceClick, 'ms ago')
      }
      
      // DON'T abort building loads if this is a map-click triggered query
      // The map click handler already started loading buildings at the clicked location
      if (isMapClickQuery) {
        console.log('[Map] 🏢 Skipping building load abort - query triggered by map click')
        return
      }
      
      // Cancel any in-progress building loads (only for non-map-click queries)
      if (buildingLoadAbortControllerRef.current) {
        buildingLoadAbortControllerRef.current.abort()
        buildingLoadAbortControllerRef.current = null
      }
      loadingBuildingsRef.current = false
      setLoadingBuildings(false)
    }
    window.addEventListener('valora-new-query', handleNewQuery)

    // Listen for building load commands from Task Planner
    const handleLoadBuildings = (e) => {
      console.log('[Map] 📨 Received valora-load-buildings event:', e.detail)
      const { lat, lng, radius_km } = e.detail || {}
      if (lat != null && lng != null) {
        const radius = radius_km || 2.0
        console.log(`[Map] Loading buildings from Task Planner (FORCE): ${lat.toFixed(4)}, ${lng.toFixed(4)}, radius: ${radius}km`)
        // Use force=true to cancel any in-progress loads and load at the new location
        loadBuildingsAtPointRef.current(lat, lng, radius)
      } else {
        console.warn('[Map] ❌ Invalid coordinates in load_buildings event:', e.detail)
      }
    }
    window.addEventListener('valora-load-buildings', handleLoadBuildings)
    
    return () => {
      window.removeEventListener('valora-new-query', handleNewQuery)
      window.removeEventListener('valora-map-command', handleMapCommand)
      window.removeEventListener('valora-ui-command', handleMapCommand)
      window.removeEventListener('valora-agentic-step', handleAgenticStep)
      window.removeEventListener('valora-load-buildings', handleLoadBuildings)
      if (pulseEntityRef.current) {
        try { viewerRef.current?.entities?.remove(pulseEntityRef.current) } catch (_) {}
      }
    }
  }, [])

  useEffect(() => {
    if (!cesiumContainerRef.current || viewerRef.current) return

    let cancelled = false
    let resizeObserver = null

    const initCesium = async () => {
      try {
        // Detect GPU capabilities for optimization
        const canvas = document.createElement('canvas')
        const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
        const hasGPU = !!gl
        
        // Get GPU info - use UNMASKED_RENDERER_WEBGL for actual GPU name
        let gpuVendor = hasGPU ? gl.getParameter(gl.VENDOR) : 'Unknown'
        let gpuRenderer = hasGPU ? gl.getParameter(gl.RENDERER) : 'Unknown'
        
        // Try to get unmasked GPU info (actual GPU name, not "WebGL")
        let debugInfoAvailable = false
        if (hasGPU) {
          const debugInfo = gl.getExtension('WEBGL_debug_renderer_info')
          if (debugInfo) {
            debugInfoAvailable = true
            const unmaskedVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)
            const unmaskedRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
            if (unmaskedVendor) gpuVendor = unmaskedVendor
            if (unmaskedRenderer) gpuRenderer = unmaskedRenderer
            
            // Debug logging for GPU detection
            console.log('🔍 RAW GPU Detection:', {
              vendor: unmaskedVendor,
              renderer: unmaskedRenderer,
              standardVendor: gl.getParameter(gl.VENDOR),
              standardRenderer: gl.getParameter(gl.RENDERER),
              hasNVIDIA: unmaskedRenderer?.toLowerCase().includes('nvidia'),
              hasAMD: unmaskedRenderer?.toLowerCase().includes('amd') || unmaskedRenderer?.toLowerCase().includes('radeon'),
              hasIntel: unmaskedRenderer?.toLowerCase().includes('intel')
            })
          } else {
            console.warn('⚠️ WEBGL_debug_renderer_info not available - GPU detection may be inaccurate')
          }
        }
        
        // GPU detection - AMD optimized as default for best APU performance
        const gpuRendererLower = gpuRenderer.toLowerCase()
        const isNVIDIA = gpuRendererLower.includes('nvidia') || 
                         gpuRendererLower.includes('geforce') || 
                         gpuRendererLower.includes('rtx') || 
                         gpuRendererLower.includes('gtx') ||
                         gpuRendererLower.includes('quadro') ||
                         gpuRendererLower.includes('tesla')
        const isAMD = gpuRendererLower.includes('amd') || 
                      gpuRendererLower.includes('radeon') ||
                      gpuRendererLower.includes('ati')
        const isIntel = gpuRendererLower.includes('intel')
        
        // AMD is now treated as dedicated GPU for optimal APU performance
        const isDedicatedGPU = isNVIDIA || isAMD
        const isAPU = isAMD // AMD APUs are optimized for this workload
        
        // Log GPU detection for debugging
        console.log('%c🎮 GPU DETECTION RESULT:', 'font-size: 14px; font-weight: bold; color: #8b5cf6;')
        console.log(`   Vendor: ${gpuVendor}`)
        console.log(`   Renderer: ${gpuRenderer}`)
        console.log(`   Type: ${isAMD ? 'AMD APU (Optimized)' : isNVIDIA ? 'NVIDIA (Dedicated)' : isIntel ? 'Intel (Integrated)' : 'Unknown'}`)
        console.log(`   Is APU: ${isAPU}`)
        console.log(`   Is Dedicated: ${isDedicatedGPU}`)
        
        // AMD APU optimization message
        if (isAMD) {
          console.log('%c🚀 AMD APU detected - using optimized settings for shared memory architecture', 'color: #10b981;')
        }
        
        const viewer = new Cesium.Viewer(cesiumContainerRef.current, {
          animation: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: false,
          timeline: false,
          navigationHelpButton: false,
          creditContainer: document.createElement('div'),
          shadows: false, // Controlled by showShadows state
          shouldAnimate: true,
          terrainShadows: Cesium.ShadowMode.DISABLED,
          requestRenderMode: false, // DISABLED: Smooth continuous rendering for panning (was causing lag even at 60fps)
          // maximumRenderTimeChange removed - not needed when requestRenderMode is false
          contextOptions: {
            webgl: {
              alpha: false, // GPU optimization - no alpha channel
              depth: true,
              stencil: false,
              antialias: hasGPU, // GPU-dependent antialiasing
              powerPreference: 'high-performance', // Use dedicated GPU if available
              preserveDrawingBuffer: false,
              failIfMajorPerformanceCaveat: false
            }
          }
        })

        viewerRef.current = viewer
        
        // Store GPU info for UI display
        setGpuInfo({
          vendor: gpuVendor,
          renderer: gpuRenderer,
          isDedicated: isDedicatedGPU
        })

        // Auto-configure quality based on GPU type - AMD APU optimized
        if (isAPU) {
          console.log('🚀 AMD APU: Enabling optimized settings for shared memory architecture')
          
          // AMD APU optimized shadow settings - lower resolution for shared memory
          viewer.shadowMap.enabled = true
          viewer.shadowMap.darkness = 0.75
          viewer.shadowMap.size = 2048 // 2K shadows optimal for AMD APUs
          viewer.shadowMap.softShadows = false // Disable soft shadows for APU performance
          viewer.shadows = true
          
          // High building quality for AMD APUs (they handle it well)
          setBuildingQuality('high')
          
          // Native resolution scale for sharp rendering
          viewer.resolutionScale = window.devicePixelRatio || 1.0
          
          // AMD APU specific optimizations
          viewer.scene.globe.tileCacheSize = 1024 // Larger cache for AMD APUs
          viewer.scene.fog.enabled = false // Disable fog for better performance
          
          console.log('✅ AMD APU optimized: 2K shadows, high quality, shared memory optimized')
        } else if (isDedicatedGPU) {
          console.log('🚀 DEDICATED GPU: Enabling high-end graphics for better simulations & storytelling')
          
          // High-quality shadow configuration for dedicated GPU
          viewer.shadowMap.enabled = true
          viewer.shadowMap.darkness = 0.7
          viewer.shadowMap.size = 4096 // 4K shadow maps
          viewer.shadowMap.softShadows = true
          viewer.shadows = true
          
          // Set high building quality
          setBuildingQuality('high')
          
          // Higher resolution scale for sharper rendering
          viewer.resolutionScale = window.devicePixelRatio || 1.0
          
          console.log('✅ High-end graphics enabled: 4K shadows, high quality buildings, enhanced rendering')
        } else {
          console.log('⚖️ INTEGRATED GPU: Using balanced graphics settings')
          
          // Balanced shadow configuration for integrated GPU
          viewer.shadowMap.enabled = true
          viewer.shadowMap.darkness = 0.6
          viewer.shadowMap.size = 2048
          viewer.shadowMap.softShadows = false // Disable soft shadows for performance
          viewer.shadows = true
          
          // Medium building quality
          setBuildingQuality('medium')
          
          // Standard resolution
          viewer.resolutionScale = 1.0
          
          console.log('✅ Balanced graphics enabled: 2K shadows, medium quality buildings')
        }

        // Remove default layers and add OSM tiles with proper configuration
        viewer.imageryLayers.removeAll(true)
        
        // Use OSM tiles with CORS proxy configuration for production
        const osmProvider = new Cesium.OpenStreetMapImageryProvider({
          url: 'https://tile.openstreetmap.org/',
          credit: '© OpenStreetMap contributors',
          enablePickFeatures: false
        })
        
        // Suppress CORS error logging (errors are expected but handled gracefully)
        osmProvider.errorEvent.addEventListener(() => {
          // Silently ignore tile loading errors - CORS is expected
        })
        
        const imageryLayer = viewer.imageryLayers.addImageryProvider(osmProvider)
        imageryLayer.alpha = 1.0
        imageryLayer.brightness = 1.0
        
        console.log('🗺️ Using OSM tiles')

        if (basemapType && basemapType !== 'osm') {
          switchBasemap(basemapType)
        }

        // Configure globe with maximum cache for smooth performance
        viewer.scene.globe.show = true
        viewer.scene.globe.enableLighting = false  // Disabled to keep terrain bright
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#f0f0f0')
        viewer.scene.globe.terrainExaggeration = terrainExaggeration
        viewer.scene.globe.terrainExaggerationRelativeHeight = 0.0
        
        // MAXIMUM CACHE SETTINGS for smooth panning
        viewer.scene.globe.tileCacheSize = 512 // Maximum tile cache (was default ~20MB)
        viewer.scene.globe.lodUpdateInterval = 0 // Update LOD immediately for smoother transitions
        // Disable depth test against terrain so buildings at height 0 are visible
        // (buildings are extruded from ellipsoid surface, not terrain surface)
        viewer.scene.globe.depthTestAgainstTerrain = false
        
        // Ensure terrain is rendered below buildings
        viewer.scene.screenSpaceCameraController.enableCollisionDetection = true

        // Set Cesium clock to current real time for accurate sun position & shadows
        viewer.clock.currentTime = Cesium.JulianDate.now()
        viewer.clock.shouldAnimate = true
        viewer.clock.multiplier = 1 // Real-time

        // Performance settings - GPU-optimized
        if (isDedicatedGPU) {
          // High-end graphics for dedicated GPU
          viewer.scene.fog.enabled = true
          viewer.scene.fog.density = 0.0001
          viewer.scene.fog.screenSpaceErrorFactor = 2.0
          
          // Enhanced atmosphere for better visuals
          viewer.scene.skyAtmosphere.hueShift = 0.0
          viewer.scene.skyAtmosphere.saturationShift = 0.0
          viewer.scene.skyAtmosphere.brightnessShift = 0.0
        } else {
          // Balanced settings for integrated GPU
          viewer.scene.fog.enabled = false
        }

        // Setup resize observer
        resizeObserver = new ResizeObserver(() => {
          if (viewerRef.current && !viewerRef.current.isDestroyed()) {
            viewerRef.current.resize()
          }
        })
        
        if (cesiumContainerRef.current) {
          resizeObserver.observe(cesiumContainerRef.current)
        }

        // Set initial view to Bangalore
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(DEFAULT_LOCATION.lng, DEFAULT_LOCATION.lat, DEFAULT_LOCATION.height),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-35),
            roll: 0
          }
        })

        // Place labels disabled - AI will handle labels in cinematic storyboard
        // await ensurePlacesLabelsLoaded()

        // Camera movement tracking for performance optimization
        let isCameraMoving = false
        let cameraMoveStartTime = 0
        const CAMERA_MOVE_DELAY_MS = 50 // Reduced from 100ms for faster building display
        
        // Preload timeout ref for predictive loading
        const preloadTimeoutRef = { current: null }
        
        // Track camera movement start - pause expensive operations
        viewer.camera.moveStart.addEventListener(() => {
          isCameraMoving = true
          cameraMoveStartTime = Date.now()
          
          // Keep shadows enabled for better visuals during movement
          // Don't disable - it causes flickering
          
          // Cancel any pending building load
          clearTimeout(cameraMoveTimeoutRef.current)
        })
        
        // Track camera movement end with throttling
        let lastMoveEndTime = 0
        const MOVE_END_THROTTLE_MS = 25 // Reduced from 50ms for faster response
        
        viewer.camera.moveEnd.addEventListener(() => {
          const now = Date.now()
          
          // Throttle moveEnd processing
          if (now - lastMoveEndTime < MOVE_END_THROTTLE_MS) {
            return
          }
          lastMoveEndTime = now
          
          clearTimeout(cameraMoveTimeoutRef.current)
          clearTimeout(preloadTimeoutRef.current)
          
          cameraMoveTimeoutRef.current = setTimeout(() => {
            isCameraMoving = false
            
            // Buildings now load on click only (not on camera move) for better performance
            
            // Update mapCenter in agentData for viewport analysis
            if (setAgentData && viewer && !viewer.isDestroyed()) {
              try {
                const cameraCartographic = Cesium.Cartographic.fromCartesian(viewer.camera.position)
                const centerLat = Cesium.Math.toDegrees(cameraCartographic.latitude)
                const centerLng = Cesium.Math.toDegrees(cameraCartographic.longitude)
                const height = cameraCartographic.height
                
                if (Number.isFinite(centerLat) && Number.isFinite(centerLng)) {
                  // Compute viewport bounds for viewport-aware context
                  let viewportBounds = null
                  try {
                    const canvas = viewer.scene.canvas
                    const topLeft = viewer.camera.pickEllipsoid(new Cesium.Cartesian2(0, 0), viewer.scene.globe.ellipsoid)
                    const bottomRight = viewer.camera.pickEllipsoid(new Cesium.Cartesian2(canvas.clientWidth, canvas.clientHeight), viewer.scene.globe.ellipsoid)
                    if (topLeft && bottomRight) {
                      const tlCarto = Cesium.Cartographic.fromCartesian(topLeft)
                      const brCarto = Cesium.Cartographic.fromCartesian(bottomRight)
                      viewportBounds = {
                        north: Cesium.Math.toDegrees(tlCarto.latitude),
                        south: Cesium.Math.toDegrees(brCarto.latitude),
                        west: Cesium.Math.toDegrees(tlCarto.longitude),
                        east: Cesium.Math.toDegrees(brCarto.longitude)
                      }
                    }
                  } catch (_) {}

                  updateAgentData(prev => ({
                    ...prev,
                    mapCenter: { lat: centerLat, lng: centerLng, height },
                    viewportBounds
                  }))
                }
              } catch (e) {
                console.warn('Failed to update mapCenter:', e)
              }
            }
          }, CAMERA_MOVE_DELAY_MS)
        })

        // Function to deselect building
        const deselectBuilding = () => {
          if (selectedBuildingEntityRef.current && selectedBuildingEntityRef.current.polygon) {
            const entity = selectedBuildingEntityRef.current
            const height = entity.properties?.height?.getValue() || 10
            const isHighQuality = entity.properties?.isHighQuality?.getValue() ?? true
            
            // Restore original color based on height and LOD quality
            let color = '#c4b5fd'  // Default light purple
            let alpha = 0.75
            
            if (isHighQuality) {
              // High quality colors
              if (height > 50) { color = '#a78bfa'; alpha = 0.85 }
              else if (height > 30) { color = '#b8a5f8'; alpha = 0.80 }
              else if (height > 15) { color = '#c4b5fd'; alpha = 0.75 }
              else if (height > 8) { color = '#d8cdf7'; alpha = 0.70 }
              else { color = '#e9e3f8'; alpha = 0.65 }
            } else {
              // Lower quality colors (for buildings beyond 500m)
              if (height > 50) { color = '#a78bfa'; alpha = 0.55 }
              else if (height > 30) { color = '#b8a5f8'; alpha = 0.50 }
              else if (height > 15) { color = '#c4b5fd'; alpha = 0.45 }
              else if (height > 8) { color = '#d8cdf7'; alpha = 0.40 }
              else { color = '#e9e3f8'; alpha = 0.35 }
            }
            
            entity.polygon.material = Cesium.Color.fromCssColorString(color).withAlpha(alpha)
            entity.polygon.outline = isHighQuality
            entity.polygon.outlineColor = Cesium.Color.fromCssColorString('#8b5cf6').withAlpha(0.5)
            selectedBuildingEntityRef.current = null
          }
          
          if (setAgentData) {
            updateAgentData(prev => ({
              ...prev,
              selectedBuilding: null,
              buildingAnalysis: null,
              buildingAnalysisLoading: false
            }))
          }
          
          if (onAnalysisUpdate) {
            onAnalysisUpdate(null)
          }
        }

        // Function to select and highlight a building (for right-click)
        const selectBuilding = (entity) => {
          // Deselect previous building first
          deselectBuilding()
          
          if (!entity || !entity.polygon) return null
          
          // Store reference to selected entity
          selectedBuildingEntityRef.current = entity
          
          // Highlight with amber color for visibility
          entity.polygon.material = Cesium.Color.fromCssColorString('#fbbf24').withAlpha(0.9) // Amber highlight
          entity.polygon.outline = true
          entity.polygon.outlineColor = Cesium.Color.fromCssColorString('#f59e0b')
          
          // Get building data from entity properties
          const buildingData = {
            coordinates: {
              lat: entity.properties?.lat?.getValue(),
              lng: entity.properties?.lng?.getValue()
            },
            height: entity.properties?.height?.getValue() || 10,
            levels: entity.properties?.levels?.getValue() || 3,
            buildingType: entity.properties?.type?.getValue() || 'building',
            area: entity.properties?.area?.getValue() || 225,
            name: entity.properties?.name?.getValue() || 'Building'
          }
          
          // Update agentData with selected building
          if (setAgentData) {
            updateAgentData(prev => ({
              ...prev,
              selectedBuilding: buildingData
            }))
          }
          
          return buildingData
        }

        // Auto-trigger building analysis when clicked
        const analyzeBuildingAsync = async (buildingData) => {
          if (!buildingData?.coordinates?.lat || !buildingData?.coordinates?.lng) return
          
          // Set loading state
          if (setAgentData) {
            updateAgentData(prev => ({
              ...prev,
              buildingAnalysisLoading: true,
              buildingAnalysis: null
            }))
          }
          
          // Start rotation immediately for better UX
          // (rotation is managed by the useEffect that watches buildingAnalysisLoading)
          // No need to duplicate rotation logic here — setting the loading state triggers it
          
          // Open analysis panel
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'openPanel', value: 'insights' }
          }))
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'switchTab', value: 'insights' }
          }))
          
          try {
            const response = await fetch(`${API_BASE}/api/building/analyze`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                lat: buildingData.coordinates.lat,
                lng: buildingData.coordinates.lng,
                height: buildingData.height,
                levels: buildingData.levels,
                buildingType: buildingData.buildingType,
                area: buildingData.area,
                name: buildingData.name
              })
            })
            
            if (response.ok) {
              const analysis = await response.json()
              if (setAgentData) {
                updateAgentData(prev => ({
                  ...prev,
                  buildingAnalysisLoading: false,
                  buildingAnalysis: analysis
                }))
              }
              console.log('🏢 Building analysis complete:', analysis)
            } else {
              console.warn('Building analysis failed:', response.status)
              if (setAgentData) {
                updateAgentData(prev => ({
                  ...prev,
                  buildingAnalysisLoading: false
                }))
              }
            }
          } catch (err) {
            console.error('Building analysis error:', err)
            if (setAgentData) {
              updateAgentData(prev => ({
                ...prev,
                buildingAnalysisLoading: false
              }))
            }
          }
        }

        // Detailed building analysis for right-click (3D reasoning)
        const analyzeBuildingDetailed = async (buildingData) => {
          if (!buildingData?.coordinates?.lat || !buildingData?.coordinates?.lng) return
          
          console.log('[Building Detailed] 🏢 Starting detailed analysis for:', buildingData)
          
          // Set loading state - use setAgentData directly for immediate update
          if (setAgentData) {
            setAgentData(prev => ({
              ...prev,
              buildingAnalysisLoading: true,
              buildingAnalysis: null
            }))
          }
          
          // Open smart tab (where building analysis is displayed)
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'openPanel', value: 'smart' }
          }))
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'switchTab', value: 'smart' }
          }))
          
          try {
            // Call the detailed analysis endpoint
            const response = await fetch(`${API_BASE}/api/building/detailed`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                lat: buildingData.coordinates.lat,
                lng: buildingData.coordinates.lng,
                height: buildingData.height,
                levels: buildingData.levels,
                buildingType: buildingData.buildingType,
                area: buildingData.area,
                name: buildingData.name
              })
            })
            
            if (response.ok) {
              const analysis = await response.json()
              console.log('[Building Detailed] 📊 API response:', analysis)
              
              // Use setAgentData directly for immediate update
              if (setAgentData) {
                setAgentData(prev => {
                  const newState = {
                    ...prev,
                    buildingAnalysisLoading: false,
                    buildingAnalysis: analysis
                  }
                  console.log('[Building Detailed] 🔄 Updated agentData.buildingAnalysis:', newState.buildingAnalysis)
                  return newState
                })
              }
              console.log('[Building Detailed] ✅ Analysis complete')
            } else {
              // Fallback to basic analysis if detailed endpoint not available
              console.warn('[Building Detailed] ⚠️ Detailed endpoint not available, falling back to basic analysis')
              const basicResponse = await fetch(`${API_BASE}/api/building/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  lat: buildingData.coordinates.lat,
                  lng: buildingData.coordinates.lng,
                  height: buildingData.height,
                  levels: buildingData.levels,
                  buildingType: buildingData.buildingType,
                  area: buildingData.area,
                  name: buildingData.name
                })
              })
              
              if (basicResponse.ok) {
                const basicAnalysis = await basicResponse.json()
                // Add flag to indicate this is from right-click (detailed request)
                basicAnalysis.isDetailedRequest = true
                if (setAgentData) {
                  setAgentData(prev => ({
                    ...prev,
                    buildingAnalysisLoading: false,
                    buildingAnalysis: basicAnalysis
                  }))
                }
              } else {
                throw new Error('Both detailed and basic analysis failed')
              }
            }
          } catch (err) {
            console.error('[Building Detailed] ❌ Error:', err)
            if (setAgentData) {
              setAgentData(prev => ({
                ...prev,
                buildingAnalysisLoading: false
              }))
            }
          }
        }

        // Click handler - handle entity clicks (any clickable location on map)
        viewer.screenSpaceEventHandler.setInputAction((click) => {
          // Visual ripple feedback at cursor (game-like)
          if (click?.position) {
            setClickRipple({
              x: click.position.x,
              y: click.position.y,
              id: Date.now()
            })
            setTimeout(() => setClickRipple(null), 650)
          }

          // Clicked entity/location: analyze the selected point
          deselectBuilding()
          
          // Get the clicked position on the globe
          const cartesian = getGroundPositionFromScreen(click.position)
          if (cartesian) {
            const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
            const clickLat = Cesium.Math.toDegrees(cartographic.latitude)
            const clickLng = Cesium.Math.toDegrees(cartographic.longitude)
            
            if (Number.isFinite(clickLat) && Number.isFinite(clickLng)) {
              console.log(`[Map Click] Entity clicked at: ${clickLat.toFixed(5)}, ${clickLng.toFixed(5)}`)
              
              // Update selected location in agentData
              const locationData = {
                type: 'location_selected',
                coordinates: { lat: clickLat, lng: clickLng }
              }
              
              // Remove existing place marker before adding new one
              if (placeMarkerRef.current) {
                try {
                  viewer.entities.remove(placeMarkerRef.current)
                } catch (e) {
                  console.warn('[Map Click] Failed to remove existing marker:', e)
                }
                placeMarkerRef.current = null
              }
              
              // Track when user clicked to prevent other effects from overwriting
              placeMarkerClickTimeRef.current = Date.now()
              
              // Create marker at the EXACT clicked coordinates
              const markerPosition = Cesium.Cartesian3.fromDegrees(clickLng, clickLat)
              placeMarkerRef.current = viewer.entities.add({
                position: markerPosition,
                point: {
                  pixelSize: 12,
                  color: Cesium.Color.fromCssColorString('#8b5cf6'),
                  outlineColor: Cesium.Color.WHITE,
                  outlineWidth: 2,
                  heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                  disableDepthTestDistance: Number.POSITIVE_INFINITY
                }
              })
              
              console.log('[Map Click] Marker placed at:', clickLng, clickLat)
              
              // Stop any active rotation before flying
              stopRotation()
              try { viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY) } catch (_) {}
              
              // Store last camera view for back button
              const camera = viewer.camera
              lastCameraViewRef.current = {
                destination: Cesium.Cartesian3.clone(camera.position),
                heading: camera.heading,
                pitch: camera.pitch,
                roll: camera.roll
              }
              setCanGoBack(true)
              
              // Target is the EXACT clicked coordinates (terrain-aware for proper height)
              const target = getTerrainAwareTarget(clickLng, clickLat)
              rotationTargetRef.current = target
              const orbitDistance = DEFAULT_ORBIT_DISTANCE
              const orbitPitch = Cesium.Math.toRadians(DEFAULT_ORBIT_PITCH_DEG)
              
              // Fly to the clicked location - camera orbits around the target point
              viewer.camera.flyToBoundingSphere(
                new Cesium.BoundingSphere(target, orbitDistance / 2),
                {
                  duration: 1.5,
                  offset: new Cesium.HeadingPitchRange(0, orbitPitch, orbitDistance),
                  complete: () => {
                    // Ensure camera stays focused on the clicked point
                    viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(0, orbitPitch, orbitDistance))
                    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
                    console.log('[Map Click] Camera focused on target')
                  }
                }
              )
              
              // Update agentData AFTER marker and camera are set up
              if (setAgentData) {
                updateAgentData(prev => ({
                  ...prev,
                  selectedLocation: locationData.coordinates,
                  selectedBuilding: null,
                  buildingAnalysis: null,
                  flyTo: null // Clear any pending flyTo to prevent conflicts
                }))
              }
              
              // Load neighbourhood buildings around the clicked point (2km radius)
              console.log('[Map Click] 🏢 Loading buildings at clicked point:', { clickLat, clickLng, radius: BUILDING_LOAD_RADIUS_KM })
              loadBuildingsAtPointRef.current(clickLat, clickLng, BUILDING_LOAD_RADIUS_KM)
              
              // Trigger location analysis
              analyzeLocationAsync(clickLat, clickLng)
              
              // Dispatch event for chat panel to auto-analyze the area
              window.dispatchEvent(new CustomEvent('valora-area-clicked', {
                detail: {
                  source: 'map-click', // Identify this as a map-click triggered query
                  coordinates: { lat: clickLat, lng: clickLng },
                  skipFlyTo: true, // Prevent backend flyTo from overriding clicked location
                  query: `Analyze the area around coordinates ${clickLat.toFixed(5)}, ${clickLng.toFixed(5)}. Provide insights on property values, neighbourhood quality, nearby amenities, connectivity, investment potential, and growth trajectory.`
                }
              }))
            }
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
        
        // Right-click handler for building selection and detailed analysis
        viewer.screenSpaceEventHandler.setInputAction((click) => {
          // Check if clicked on a building entity
          const pickedObject = viewer.scene.pick(click.position)
          
          if (pickedObject && pickedObject.id && pickedObject.id.polygon) {
            // Right-clicked on a building - select and highlight it
            const buildingData = selectBuilding(pickedObject.id)
            
            if (buildingData && buildingData.coordinates.lat && buildingData.coordinates.lng) {
              console.log('[Right Click] 🏢 Building selected:', buildingData)
              
              // Set click time to prevent backend flyTo from overriding
              placeMarkerClickTimeRef.current = Date.now()
              
              // Update selectedLocation in agentData
              if (setAgentData) {
                setAgentData(prev => ({
                  ...prev,
                  selectedLocation: {
                    lat: buildingData.coordinates.lat,
                    lng: buildingData.coordinates.lng,
                    name: buildingData.name || 'Selected Building'
                  }
                }))
              }
              
              // Fly to the building
              const buildingLat = buildingData.coordinates.lat
              const buildingLng = buildingData.coordinates.lng
              const buildingHeight = buildingData.height || 15
              
              // Stop any active rotation before flying
              if (rotationIntervalRef.current) {
                clearInterval(rotationIntervalRef.current)
                rotationIntervalRef.current = null
              }
              try { viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY) } catch (_) {}
              
              // Get terrain-aware target at building center (terrain height + half building height)
              const terrainHeight = getTerrainHeight(buildingLng, buildingLat)
              const targetHeight = terrainHeight + (buildingHeight / 2)
              const target = Cesium.Cartesian3.fromDegrees(buildingLng, buildingLat, targetHeight)
              
              // Calculate camera distance based on building height
              const cameraDistance = Math.max(150, buildingHeight * 4)
              
              // Fly to building with close-up view
              viewer.camera.flyToBoundingSphere(
                new Cesium.BoundingSphere(target, cameraDistance / 2),
                {
                  duration: 1.5,
                  offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-30), cameraDistance),
                  complete: () => {
                    console.log('[Right Click] 🎥 Camera focused on building')
                  }
                }
              )
              
              // Remove existing place marker - building highlight is enough
              if (placeMarkerRef.current) {
                try {
                  viewer.entities.remove(placeMarkerRef.current)
                } catch (e) {
                  console.warn('[Right Click] Could not remove old marker:', e)
                }
                placeMarkerRef.current = null
              }
              // No marker needed - building is already highlighted with amber color
              
              // Visual feedback
              if (click?.position) {
                setClickRipple({
                  x: click.position.x,
                  y: click.position.y,
                  id: Date.now()
                })
                setTimeout(() => setClickRipple(null), 650)
              }
              
              // Trigger detailed building analysis via API
              analyzeBuildingDetailed(buildingData)
              
              // Also dispatch event for chat panel to analyze the building through task planner
              const buildingQuery = `Analyze this building at coordinates ${buildingData.coordinates.lat.toFixed(5)}, ${buildingData.coordinates.lng.toFixed(5)}. Building details: ${buildingData.height || '?'}m tall, ${buildingData.levels || '?'} floors, ${buildingData.buildingType || 'building'} type${buildingData.area ? `, ~${buildingData.area}m² area` : ''}. Provide detailed insights on: 1) Property valuation and price estimate 2) Investment potential and ROI 3) Neighbourhood quality and amenities 4) Structural analysis and view quality 5) Solar potential and energy efficiency 6) Risk assessment and recommendations.`
              
              window.dispatchEvent(new CustomEvent('valora-building-clicked', {
                detail: {
                  source: 'building-right-click',
                  coordinates: buildingData.coordinates,
                  building: {
                    type: buildingData.buildingType || 'building',
                    height: buildingData.height,
                    levels: buildingData.levels,
                    area: buildingData.area,
                    lat: buildingData.coordinates.lat,
                    lng: buildingData.coordinates.lng,
                    name: buildingData.name
                  },
                  query: buildingQuery
                }
              }))
            }
          } else {
            // Right-clicked on empty area - deselect building
            deselectBuilding()
          }
        }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)
        
        // Hover handler: change cursor to pointer on interactive entities
        viewer.screenSpaceEventHandler.setInputAction((movement) => {
          const canvas = viewer.scene.canvas
          const picked = viewer.scene.pick(movement.endPosition)
          if (Cesium.defined(picked) && picked.id?.properties?.isPropertyMarker?.getValue?.()) {
            canvas.style.cursor = 'pointer'
          } else if (Cesium.defined(picked) && picked.id?.polygon) {
            canvas.style.cursor = 'pointer'
          } else {
            canvas.style.cursor = 'default'
          }
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)
        
        // Analyze any clicked location (properties, lands, empty areas)
        const analyzeLocationAsync = async (lat, lng) => {
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
          
          // Set loading state
          if (setAgentData) {
            updateAgentData(prev => ({
              ...prev,
              locationAnalysisLoading: true,
              locationAnalysis: null
            }))
          }
          
          // Open analysis panel
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'openPanel', value: 'insights' }
          }))
          window.dispatchEvent(new CustomEvent('valora-ui-command', {
            detail: { action: 'switchTab', value: 'insights' }
          }))
          
          try {
            const response = await fetch(`${API_BASE}/api/location/analyze`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ lat, lng })
            })
            
            if (response.ok) {
              const analysis = await response.json()
              if (setAgentData) {
                updateAgentData(prev => ({
                  ...prev,
                  locationAnalysisLoading: false,
                  locationAnalysis: analysis
                }))
              }
              console.log('📍 Location analysis complete:', analysis)
            } else {
              console.warn('Location analysis failed:', response.status)
              if (setAgentData) {
                updateAgentData(prev => ({
                  ...prev,
                  locationAnalysisLoading: false
                }))
              }
            }
          } catch (err) {
            console.error('Location analysis error:', err)
            if (setAgentData) {
              updateAgentData(prev => ({
                ...prev,
                locationAnalysisLoading: false
              }))
            }
          }
        }

        // ESC key handler - deselect building (with cleanup)
        const onKeyDown = (e) => {
          if (e.key === 'Escape') {
            deselectBuilding()
          }
        }
        keyDownHandlerRef.current = onKeyDown
        document.addEventListener('keydown', onKeyDown)

        if (cancelled || viewer.isDestroyed()) return

        setIsLoading(false)

        // Update agentData
        if (setAgentData) {
          updateAgentData(prev => ({
            ...prev,
            mapCenter: { lat: DEFAULT_LOCATION.lat, lng: DEFAULT_LOCATION.lng },
            mapLoaded: true
          }))
        }

        // Buildings load on click/navigation — NOT auto-loaded at startup
        // This prevents buildings from appearing at wrong location

        // Initialize terrain if enabled by default
        if (showTerrain) {
          setTimeout(async () => {
            try {
              if (viewer && !viewer.isDestroyed()) {
                // Switch to 3D globe mode for terrain
                viewer.scene.mode = Cesium.SceneMode.SCENE3D
                
                // Load Cesium Ion terrain with validation
                if (!HAS_ION_TOKEN) {
                  console.warn('[Terrain] No Cesium Ion token — terrain disabled. Set VITE_CESIUM_TOKEN in .env')
                } else {
                  viewer.terrainProvider = await Cesium.CesiumTerrainProvider.fromIonAssetId(ION_TERRAIN_ASSET_ID, {
                    requestWaterMask: true,
                    requestVertexNormals: true
                  })
                  console.log('✅ Cesium Ion terrain loaded (asset', ION_TERRAIN_ASSET_ID, ')')
                }
                
                // Terrain shadows always on
                viewer.scene.globe.shadows = Cesium.ShadowMode.RECEIVE_ONLY
                viewer.scene.globe.enableLighting = false  // No day/night effects
                viewer.scene.globe.terrainExaggeration = terrainExaggeration
                viewer.scene.globe.terrainExaggerationRelativeHeight = 0.0
                
                // Enable depth test so buildings with heightReference properly clamp to terrain
                viewer.scene.globe.depthTestAgainstTerrain = true
                
                // Enable sky and atmosphere for 3D globe
                viewer.scene.skyBox = new Cesium.SkyBox({
                  sources: {
                    positiveX: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_px.jpg'),
                    negativeX: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_mx.jpg'),
                    positiveY: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_py.jpg'),
                    negativeY: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_my.jpg'),
                    positiveZ: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_pz.jpg'),
                    negativeZ: Cesium.buildModuleUrl('Assets/Textures/SkyBox/tycho2t3_80_mz.jpg')
                  }
                })
                viewer.scene.skyAtmosphere = new Cesium.SkyAtmosphere()
                
                console.log('✅ 3D terrain enabled - receives building shadows only')
              }
            } catch (err) {
              console.error('Failed to load Cesium Ion terrain on startup:', err)
              if (viewer && !viewer.isDestroyed()) {
                viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider()
              }
            }
          }, 1000)
        }

      } catch (err) {
        console.error('Cesium initialization failed:', err)
        setIsLoading(false)
      }
    }

    initCesium()

    return () => {
      cancelled = true
      if (resizeObserver) resizeObserver.disconnect()
      if (keyDownHandlerRef.current) {
        document.removeEventListener('keydown', keyDownHandlerRef.current)
        keyDownHandlerRef.current = null
      }
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        try {
          viewerRef.current.destroy()
          viewerRef.current = null
        } catch (err) {
          console.error('Error destroying viewer:', err)
        }
      }
    }
  }, [])

  // Weather effects - Rain
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    if (showRain && !rainSystemRef.current) {
      // Create rain particle system
      rainSystemRef.current = viewer.scene.primitives.add(new Cesium.ParticleSystem({
        image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAQCAYAAADXnxW3AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAIGNIUk0AAHolAACAgwAA+f8AAIDpAAB1MAAA6mAAADqYAAAXb5JfxUYAAAASSURBVHjaYvj//z8DQIABgAEAEhgBwcZx7NgAAAAASUVORK5CYII=',
        startColor: Cesium.Color.WHITE.withAlpha(0.3),
        endColor: Cesium.Color.WHITE.withAlpha(0.0),
        startScale: 1.0,
        endScale: 0.5,
        particleLife: 3.0,
        speed: 15.0,
        imageSize: new Cesium.Cartesian2(2, 10),
        emissionRate: 1000,
        lifetime: 1000000.0,
        emitter: new Cesium.BoxEmitter(new Cesium.Cartesian3(2000, 2000, 0)),
        modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(viewer.camera.positionWC),
        emitterModelMatrix: new Cesium.Matrix4()
      }))
    } else if (!showRain && rainSystemRef.current) {
      viewer.scene.primitives.remove(rainSystemRef.current)
      rainSystemRef.current = null
    }
  }, [showRain])

  // Weather effects - Snow
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    if (showSnow && !snowSystemRef.current) {
      // Create snow particle system
      snowSystemRef.current = viewer.scene.primitives.add(new Cesium.ParticleSystem({
        image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAIGNIUk0AAHolAACAgwAA+f8AAIDpAAB1MAAA6mAAADqYAAAXb5JfxUYAAABXSURBVHjaYvz//z8DlWGAKGT8//8/IwMVFTIyMjIyMjIy/v//nwEkzsj4HyrOyMj4/z9MnJGR8T9YnJHxPxs6gZGREVkBIyMjI9D9TAwUAKpFhgEAHhIbCZT8pzMAAAAASUVORK5CYII=',
        startColor: Cesium.Color.WHITE.withAlpha(0.9),
        endColor: Cesium.Color.WHITE.withAlpha(0.0),
        startScale: 1.5,
        endScale: 1.0,
        particleLife: 8.0,
        speed: 3.0,
        imageSize: new Cesium.Cartesian2(8, 8),
        emissionRate: 300,
        lifetime: 1000000.0,
        emitter: new Cesium.BoxEmitter(new Cesium.Cartesian3(2000, 2000, 0)),
        modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(viewer.camera.positionWC),
        emitterModelMatrix: new Cesium.Matrix4()
      }))
    } else if (!showSnow && snowSystemRef.current) {
      viewer.scene.primitives.remove(snowSystemRef.current)
      snowSystemRef.current = null
    }
  }, [showSnow])

  // Realtime weather → effect intensity
  useEffect(() => {
    if (!enableRealtimeWeather) return

    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const cloudsPct = weatherMetrics.cloudsPct
    const rainMm1h = weatherMetrics.rainMm1h
    const snowMm1h = weatherMetrics.snowMm1h
    const windSpeedMps = weatherMetrics.windSpeedMps

    // Clouds: scale fog density based on cloud cover
    if (showClouds && Number.isFinite(cloudsPct)) {
      const pct = Math.max(0, Math.min(100, cloudsPct))
      viewer.scene.fog.enabled = true
      viewer.scene.fog.density = 0.00008 + (0.00035 * (pct / 100))
      viewer.scene.fog.minimumBrightness = 0.65
    }

    // Rain: scale emission rate based on mm/hr (rough heuristic)
    if (showRain && rainSystemRef.current) {
      const mm = Number.isFinite(rainMm1h) ? rainMm1h : 1
      const intensity = Math.max(0.2, Math.min(1.0, mm / 5))
      rainSystemRef.current.emissionRate = Math.round(800 + 3200 * intensity)
      rainSystemRef.current.speed = 12 + 10 * intensity
    }

    // Snow: scale emission rate based on mm/hr (rough heuristic)
    if (showSnow && snowSystemRef.current) {
      const mm = Number.isFinite(snowMm1h) ? snowMm1h : 1
      const intensity = Math.max(0.2, Math.min(1.0, mm / 3))
      snowSystemRef.current.emissionRate = Math.round(200 + 900 * intensity)
      snowSystemRef.current.speed = 2 + 2 * intensity
    }

    // Wind: simple heuristic (affects 'wind' toggle + slightly increases particle speed)
    if (showWind && Number.isFinite(windSpeedMps)) {
      if (rainSystemRef.current) rainSystemRef.current.speed = Math.max(rainSystemRef.current.speed, 12 + windSpeedMps)
      if (snowSystemRef.current) snowSystemRef.current.speed = Math.max(snowSystemRef.current.speed, 2 + (windSpeedMps / 3))
    }
  }, [enableRealtimeWeather, weatherMetrics, showClouds, showRain, showSnow, showWind])

  // Weather effects - Clouds (atmospheric effect)
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    if (showClouds) {
      viewer.scene.fog.enabled = true
      if (enableRealtimeWeather && Number.isFinite(weatherMetrics.cloudsPct)) {
        const pct = Math.max(0, Math.min(100, weatherMetrics.cloudsPct))
        viewer.scene.fog.density = 0.00008 + (0.00035 * (pct / 100))
        viewer.scene.fog.minimumBrightness = 0.65
      } else {
        viewer.scene.fog.density = 0.0002
        viewer.scene.fog.minimumBrightness = 0.7
      }
    } else {
      viewer.scene.fog.enabled = false
    }
  }, [showClouds, enableRealtimeWeather, weatherMetrics.cloudsPct])

  // Hide Cesium logo
  useEffect(() => {
    const hideCesiumLogo = () => {
      const logoContainer = document.querySelector('.cesium-credit-logoContainer')
      const textContainer = document.querySelector('.cesium-credit-textContainer')
      if (logoContainer) logoContainer.style.display = 'none'
      if (textContainer) textContainer.style.display = 'none'
    }
    hideCesiumLogo()
    const timer = setTimeout(hideCesiumLogo, 1000)
    return () => clearTimeout(timer)
  }, [])

  // Storyboard state for animated storytelling
  const [storyboardPlaying, setStoryboardPlaying] = useState(false)
  const [currentNarration, setCurrentNarration] = useState(null)
  const storyboardAbortRef = useRef(false)

  // Animated storytelling - play storyboard sequences
  const playStoryboard = async (storyboard) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || !storyboard?.scenes) return

    setStoryboardPlaying(true)
    storyboardAbortRef.current = false

    for (const scene of storyboard.scenes) {
      if (storyboardAbortRef.current) break

      // Show narration
      if (scene.narration) {
        setCurrentNarration(scene.narration)
        window.dispatchEvent(new CustomEvent('valora-narration', { 
          detail: { text: scene.narration, duration: scene.duration || 4000 }
        }))
      }

      // Fly to scene location with terrain-aware height
      if (scene.location) {
        const { heading = 0, pitch = -45 } = scene.orientation || {}
        
        // Terrain-aware camera height for storyboard
        const terrainHeight = getTerrainHeight(scene.location.lng, scene.location.lat)
        const sceneHeight = (scene.location.height || 800) + terrainHeight
        
        const destination = Cesium.Cartesian3.fromDegrees(
          scene.location.lng,
          scene.location.lat,
          sceneHeight
        )

        await new Promise((resolve) => {
          viewer.camera.flyTo({
            destination,
            orientation: {
              heading: Cesium.Math.toRadians(heading || 0),
              pitch: Cesium.Math.toRadians(pitch || -45),
              roll: 0
            },
            duration: scene.duration || 3,
            complete: resolve
          })
        })
      }

      // Wait for scene duration
      const waitTime = scene.wait || 2000
      await new Promise(resolve => setTimeout(resolve, waitTime))
    }

    setStoryboardPlaying(false)
    setCurrentNarration(null)
  }

  // Stop storyboard playback
  const stopStoryboard = () => {
    storyboardAbortRef.current = true
    setStoryboardPlaying(false)
    setCurrentNarration(null)
  }

  // Listen for storyboard events from AI
  useEffect(() => {
    const handleStoryboard = (e) => {
      if (e.detail) {
        playStoryboard(e.detail)
      }
    }

    const handleFlyToLocality = async (e) => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return

      try {
        const data = e.detail
        if (data?.profile?.coordinates) {
          const { lat, lng } = data.profile.coordinates
          
          // Fly to locality with storytelling animation (terrain-aware)
          const terrainHeight = getTerrainHeight(lng, lat)
          const adjustedHeight = 800 + terrainHeight
          
          viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(lng, lat, adjustedHeight),
            orientation: {
              heading: Cesium.Math.toRadians(45),
              pitch: Cesium.Math.toRadians(-30),
              roll: 0
            },
            duration: 2.5,
            complete: () => {
              // Orbit around locality
              const target = getTerrainAwareTarget(lng, lat, 50)
              rotationTargetRef.current = target
              
              // Start gentle orbit
              let orbitHeading = 45
              const orbitDistance = DEFAULT_ORBIT_DISTANCE
              const orbitInterval = setInterval(() => {
                if (!viewer || viewer.isDestroyed()) {
                  clearInterval(orbitInterval)
                  return
                }
                orbitHeading += 0.3
                viewer.camera.lookAt(
                  target,
                  new Cesium.HeadingPitchRange(
                    Cesium.Math.toRadians(orbitHeading),
                    Cesium.Math.toRadians(DEFAULT_ORBIT_PITCH_DEG),
                    orbitDistance
                  )
                )
                viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
              }, 50)

              // Stop after 8 seconds
              setTimeout(() => clearInterval(orbitInterval), 8000)
            }
          })

          // DISABLED: Building load on flyToLocality - only query-based loading from chat
          // const { lat: aLat, lng: aLng } = data.profile.coordinates
          // setTimeout(() => loadBuildingsAtPoint(aLat, aLng, BUILDING_LOAD_RADIUS_KM), 2500)
        }
      } catch (err) {
        console.warn('Failed to fly to locality:', err)
      }
    }

    window.addEventListener('valora-storyboard', handleStoryboard)
    window.addEventListener('valora-fly-to-locality', handleFlyToLocality)
    
    return () => {
      window.removeEventListener('valora-storyboard', handleStoryboard)
      window.removeEventListener('valora-fly-to-locality', handleFlyToLocality)
    }
  }, [])

  return (
    <div className="relative w-full h-full">
      <div
        ref={cesiumContainerRef}
        className="w-full h-full"
        style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}
      />

      {clickRipple && (
        <div
          key={clickRipple.id}
          className="absolute pointer-events-none z-50"
          style={{ left: clickRipple.x, top: clickRipple.y, transform: 'translate(-50%, -50%)' }}
        >
          <div className="w-3 h-3 bg-blue-400 rounded-full opacity-80" />
          <div className="absolute inset-0 w-10 h-10 border-2 border-blue-400 rounded-full animate-ping opacity-60" style={{ left: -14, top: -14 }} />
        </div>
      )}

      {/* Top Bar - Search + Basemap + Navigation + Layers */}
      <div className="absolute top-0 left-0 right-0 z-50">
        <div className="bg-slate-900 border-b border-slate-700 px-2 py-1 flex items-center gap-2">
          {/* Search Bar with Auto-Results */}
          <div className="relative flex items-center bg-slate-800/80 border border-slate-700 px-2 py-0.5 w-48">
            <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type to search..."
              className="flex-1 bg-transparent border-none text-white text-xs placeholder-slate-400 focus:outline-none ml-1"
            />
            {isSearching && (
              <svg className="animate-spin h-3 w-3 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
          </div>
          
          {/* Basemap Dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setShowBasemapDropdown(!showBasemapDropdown)
                setShowSearchResults(false)
              }}
              className={`flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold transition ${
                showBasemapDropdown ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              <span className="capitalize">{basemapType.replace('mapbox_', '').replace('_', ' ')}</span>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Basemap Dropdown */}
            {showBasemapDropdown && (
              <div className="absolute top-full left-0 mt-1 bg-slate-900 border border-slate-700 shadow-2xl min-w-[120px] z-[60] rounded-sm">
                {[
                  { id: 'osm', label: 'OSM Street' },
                  { id: 'mapbox_streets', label: 'Mapbox Street' },
                  { id: 'mapbox_satellite', label: 'Satellite' },
                  { id: 'mapbox_satellite_streets', label: 'Hybrid' },
                  { id: 'mapbox_dark', label: 'Dark' },
                  { id: 'mapbox_light', label: 'Light' },
                  { id: 'mapbox_outdoors', label: 'Outdoors' }
                ].map(({ id, label }) => (
                  <button
                    key={id}
                    onClick={() => {
                      switchBasemap(id)
                      setShowBasemapDropdown(false)
                    }}
                    className={`w-full px-3 py-1.5 text-left text-xs transition rounded-sm ${
                      basemapType === id 
                        ? 'bg-blue-600 text-white font-semibold' 
                        : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="h-4 w-px bg-slate-700" />

          {/* Navigation Tools */}
          <div className="flex items-center gap-0.5">
            <button
              onClick={goBackToLastView}
              disabled={!canGoBack}
              className="w-6 h-6 flex items-center justify-center hover:bg-slate-800 transition disabled:opacity-30"
              title="Back"
            >
              <svg className="w-3 h-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <button onClick={resetView} className="w-6 h-6 flex items-center justify-center hover:bg-slate-800 transition" title="Home">
              <svg className="w-3 h-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l9-9 9 9M4 10v10a1 1 0 001 1h5m4 0h5a1 1 0 001-1V10" />
              </svg>
            </button>
            <button onClick={zoomIn} className="w-6 h-6 flex items-center justify-center hover:bg-slate-800 transition" title="Zoom In">
              <svg className="w-3 h-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </button>
            <button onClick={zoomOut} className="w-6 h-6 flex items-center justify-center hover:bg-slate-800 transition" title="Zoom Out">
              <svg className="w-3 h-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
            </button>
            <button onClick={resetNorth} className="w-6 h-6 flex items-center justify-center hover:bg-slate-800 transition relative" title="North">
              <div style={{ transform: `rotate(${-heading}deg)` }}>
                <div className="w-0.5 h-2.5 bg-red-500 rounded-t-sm"></div>
              </div>
            </button>
            <button
              onClick={toggle3D}
              className="w-6 h-6 flex items-center justify-center hover:bg-slate-800 transition text-[10px] font-bold text-slate-300"
              title={is3DMode ? '2D' : '3D'}
            >
              {is3DMode ? '2D' : '3D'}
            </button>
          </div>


          {/* Spacer */}
          <div className="flex-1" />

          {/* Performance & Cache Info */}
          <div className="flex items-center gap-3 text-[10px] text-slate-400 mr-2">
            {gpuInfo.isDedicated ? (
              <div className="flex items-center gap-1 px-1.5 py-0.5 bg-purple-600/20 border border-purple-500/30 rounded" title={`${gpuInfo.vendor} - ${gpuInfo.renderer}`}>
                <svg className="w-3 h-3 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="font-semibold text-purple-300 truncate max-w-[140px]">
                  {gpuInfo.renderer.includes('NVIDIA') || gpuInfo.renderer.includes('GeForce') || gpuInfo.renderer.includes('RTX') || gpuInfo.renderer.includes('GTX') ? 'NVIDIA' : 
                   gpuInfo.renderer.includes('AMD') || gpuInfo.renderer.includes('Radeon') ? 'AMD' : 
                   gpuInfo.renderer.includes('Intel') ? 'Intel' : 
                   gpuInfo.renderer.split(' ')[0]}
                </span>
              </div>
            ) : gpuInfo.renderer !== 'Unknown' && (
              <div className="flex items-center gap-1 px-1.5 py-0.5 bg-slate-700/50 rounded" title={gpuInfo.renderer}>
                <span className="font-mono text-slate-300">{gpuInfo.renderer.split(' ')[0]}</span>
              </div>
            )}
            <div className="flex items-center gap-1">
              <span className={fps >= 30 ? 'text-green-400 font-mono' : 'text-red-400 font-mono'}>{fps} FPS</span>
            </div>
            {memoryUsage > 0 && (
              <div className="flex items-center gap-1">
                <span className="font-mono">{memoryUsage} MB</span>
              </div>
            )}
            <div className="flex items-center gap-1">
              <span className="font-mono">{tilesLoaded} tiles</span>
            </div>
            {(ionCacheStats.totalTiles > 0 || buildingCacheStats.totalTiles > 0) && (
              <div className="flex items-center gap-1" title={`Ion: ${(ionCacheStats.totalSize/1048576).toFixed(1)}MB, Buildings: ${(buildingCacheStats.totalSize/1048576).toFixed(1)}MB`}>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                <span className="font-mono text-blue-400">
                  {((ionCacheStats.totalSize + buildingCacheStats.totalSize) / 1048576).toFixed(0)}MB cached
                </span>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="h-4 w-px bg-slate-700" />

          {/* Layers Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowLayerPanel(!showLayerPanel)}
              className={`flex items-center gap-1 px-2 py-1 text-[10px] font-semibold transition ${
                showLayerPanel ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span>Layers</span>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Layers Dropdown Panel */}
            {showLayerPanel && (
              <div className="absolute top-full left-0 mt-1 bg-slate-900 border border-slate-700 shadow-2xl p-3 min-w-[220px] z-[60] rounded-sm">
                {/* Always-on 3D status */}
                <div className="mb-2">
                  <div className="text-[10px] text-slate-500 mb-1.5 font-semibold">3D Layers (Always On)</div>
                  <div className="space-y-1 text-[10px] text-slate-400">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span>Buildings &bull; {buildingsCount} loaded</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span>Shadows &bull; Terrain</span>
                    </div>
                    <div className="text-[9px] text-slate-500 mt-1">Click on map to load neighbourhood buildings</div>
                  </div>
                </div>

                {/* Ion Layers */}
                <div className="pt-2 border-t border-slate-700 mb-2">
                  <div className="text-[10px] text-slate-500 mb-1.5 font-semibold">Ion Layers</div>
                  <div className="space-y-1.5">
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showIonPhotorealistic}
                        disabled={!HAS_ION_TOKEN || !HAS_ION_PHOTOREALISTIC}
                        onChange={(e) => setShowIonPhotorealistic(e.target.checked)}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600 disabled:opacity-50"
                      />
                      Photorealistic 3D (Ion)
                    </label>
                    {!HAS_ION_PHOTOREALISTIC && (
                      <div className="text-[10px] text-slate-500 mt-1">
                        Set VITE_CESIUM_ION_PHOTOREALISTIC_ASSET_ID to enable.
                      </div>
                    )}
                    <label className="mt-2 flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showIonOsmBuildings}
                        disabled={!HAS_ION_TOKEN || !HAS_ION_OSM_BUILDINGS}
                        onChange={(e) => setShowIonOsmBuildings(e.target.checked)}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600 disabled:opacity-50"
                      />
                      OSM Buildings (Ion)
                    </label>
                    {HAS_ION_IMAGERY && (
                      <div className="mt-2">
                        <div className="text-[10px] text-slate-500 mb-1">Ion Imagery Overlay</div>
                        <select
                          value={ionImageryType}
                          onChange={(e) => setIonImageryType(e.target.value)}
                          className="w-full bg-slate-700 text-xs text-slate-200 rounded px-2 py-1 border border-slate-600 focus:outline-none focus:border-blue-500"
                        >
                          <option value="none">None (Use basemap)</option>
                          {ION_IMAGERY_ASSETS.googleSatellite && <option value="googleSatellite">Google Satellite</option>}
                          {ION_IMAGERY_ASSETS.googleSatelliteLabels && <option value="googleSatelliteLabels">Google Satellite + Labels</option>}
                          {ION_IMAGERY_ASSETS.googleRoadmap && <option value="googleRoadmap">Google Roadmap</option>}
                          {ION_IMAGERY_ASSETS.bingAerial && <option value="bingAerial">Bing Aerial</option>}
                          {ION_IMAGERY_ASSETS.bingAerialLabels && <option value="bingAerialLabels">Bing Aerial + Labels</option>}
                          {ION_IMAGERY_ASSETS.bingRoad && <option value="bingRoad">Bing Road</option>}
                        </select>
                      </div>
                    )}
                    {(showIonPhotorealistic || showBuildings) && (
                      <div className="mt-2 p-2 bg-slate-800 rounded border border-slate-700">
                        <div className="flex items-center justify-between mb-1">
                          <div className="text-[10px] text-slate-400 font-semibold">Auto-Cache Active</div>
                          <button
                            onClick={() => setShowCachePanel(!showCachePanel)}
                            className="text-[10px] text-blue-400 hover:text-blue-300"
                          >
                            {showCachePanel ? 'Hide' : 'Details'}
                          </button>
                        </div>
                        {showCachePanel && (
                          <div className="space-y-2 text-[10px] text-slate-300">
                            {showIonPhotorealistic && (
                              <div className="pb-2 border-b border-slate-700">
                                <div className="text-slate-400 font-semibold mb-1">Ion Tiles</div>
                                <div className="flex justify-between">
                                  <span>Cached:</span>
                                  <span className="font-mono">{ionCacheStats.totalTiles}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>Size:</span>
                                  <span className="font-mono">{(ionCacheStats.totalSize / 1024 / 1024).toFixed(1)} MB</span>
                                </div>
                              </div>
                            )}
                            {showBuildings && (
                              <div className="pb-2 border-b border-slate-700">
                                <div className="text-slate-400 font-semibold mb-1">Building Tiles</div>
                                <div className="flex justify-between">
                                  <span>Cached:</span>
                                  <span className="font-mono">{buildingCacheStats.totalTiles}</span>
                                </div>
                              </div>
                            )}
                            <div className="flex justify-between text-slate-400 font-semibold">
                              <span>Total Storage:</span>
                              <span className="font-mono">{ionCacheStats.percentage}%</span>
                            </div>
                            <button
                              onClick={async () => {
                                if (confirm('Clear all cached tiles? They will be re-downloaded when needed.')) {
                                  const registration = await navigator.serviceWorker.ready
                                  const messageChannel = new MessageChannel()
                                  messageChannel.port1.onmessage = () => {
                                    setIonCacheStats({ totalTiles: 0, totalSize: 0, percentage: 0 })
                                    setBuildingCacheStats({ totalTiles: 0, totalSize: 0 })
                                    alert('Cache cleared!')
                                  }
                                  registration.active?.postMessage({ type: 'CLEAR_ALL_CACHE' }, [messageChannel.port2])
                                }
                              }}
                              className="w-full mt-2 px-2 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-[10px]"
                            >
                              Clear All Cache
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Performance Monitor (Layers Panel - Removed, moved to floating panel) */}
                
                {/* Building Quality */}
                <div className="pt-2 border-t border-slate-700">
                  <div className="text-[10px] text-slate-500 mb-1">Quality</div>
                  <div className="flex gap-1">
                    {['low', 'medium', 'high'].map((q) => (
                      <button
                        key={q}
                        onClick={() => setBuildingQuality(q)}
                        className={`px-2 py-0.5 text-[10px] capitalize ${
                          buildingQuality === q ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Search Results Dropdown */}
        {showSearchResults && searchResults.length > 0 && (
          <div className="absolute top-full left-2 mt-0 w-80 bg-slate-900 border border-slate-700 shadow-2xl max-h-48 overflow-y-auto z-[60] rounded-sm">
            {searchResults.map((result, idx) => (
              <button
                key={idx}
                onClick={() => {
                  const viewer = viewerRef.current
                  if (viewer && !viewer.isDestroyed()) {
                    const lon = parseFloat(result.lon)
                    const lat = parseFloat(result.lat)
                    const terrainHeight = getTerrainHeight(lon, lat)
                    const adjustedHeight = 800 + terrainHeight
                    
                    viewer.camera.flyTo({
                      destination: Cesium.Cartesian3.fromDegrees(lon, lat, adjustedHeight),
                      orientation: { heading: Cesium.Math.toRadians(0), pitch: Cesium.Math.toRadians(-45), roll: 0 },
                      duration: 2
                    })
                    // DISABLED: Building load on search result click - only query-based loading from chat
                    // setTimeout(() => loadBuildingsAtPoint(lat, lon, BUILDING_LOAD_RADIUS_KM), 2500)
                  }
                  setShowSearchResults(false)
                  setSearchQuery(result.display_name.split(',')[0])
                }}
                className="w-full px-3 py-1.5 text-left hover:bg-slate-800 transition border-b border-slate-800 last:border-b-0"
              >
                <div className="text-xs text-white truncate">{result.display_name.split(',')[0]}</div>
                <div className="text-[10px] text-slate-400 truncate">{result.display_name}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Bottom Bar - Drawing Tools + Time + Status + Fullscreen */}
      <div className="absolute bottom-0 left-0 right-0 z-40">
        <div className="bg-slate-900 border-t border-slate-700 px-2 py-0.5 flex items-center justify-between">
          {/* Drawing Tools */}
          <div>
            <DrawingTools
              isDrawing={isDrawing}
              drawMode={drawMode}
              onStartPolygon={startPolygonDraw}
              onStartBuffer={startBufferDraw}
              onClearDrawing={clearDrawings}
              onFinishDrawing={drawMode === 'polygon' ? finishPolygonDraw : () => {}}
              onCancelDrawing={cancelDrawing}
              bufferRadius={bufferRadius}
              onBufferRadiusChange={setBufferRadius}
              polygonPoints={polygonPoints.length}
            />
          </div>
          
          {/* Center section - Clock */}
          <button
            onClick={() => setShowTimeControls(!showTimeControls)}
            className="flex items-center gap-2 px-3 hover:bg-slate-800 transition cursor-pointer"
            title="Time simulation"
          >
            <svg className="w-3 h-3 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs font-mono text-white">
              {currentTime.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true })}
            </span>
            {timeMultiplier !== 1 && (
              <span className="text-[9px] text-orange-400">⚡{timeMultiplier}x</span>
            )}
          </button>
          
          {/* Right section - Status + Fullscreen */}
          <div className="flex items-center gap-1">
            {/* Buildings Status */}
            <div className="flex items-center gap-1 px-2 border-l border-slate-700">
              {loadingBuildings ? (
                <svg className="w-3 h-3 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
              ) : (
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
              )}
              <span className="text-[10px] text-slate-300">{buildingsCount.toLocaleString()}</span>
            </div>
            
            {/* Fullscreen Toggle */}
            {toggleMapFullscreen && (
              <button
                onClick={toggleMapFullscreen}
                className={`w-5 h-5 flex items-center justify-center transition border-l border-slate-700 pl-1 ${
                  isMapFullscreen ? 'text-purple-400' : 'text-slate-400 hover:text-white'
                }`}
                title={isMapFullscreen ? 'Exit Map Fullscreen' : 'Map Fullscreen'}
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {isMapFullscreen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  )}
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Building Info Popup */}
      {selectedBuilding && buildingPopupPosition && (
        <div
          className="absolute z-50 pointer-events-auto"
          style={{ left: buildingPopupPosition.x, top: buildingPopupPosition.y, transform: 'translate(-50%, -100%)' }}
        >
          <div className="bg-slate-900 rounded-lg shadow-xl border border-blue-500/30 p-3 min-w-[200px]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-white">Building Info</span>
              <button
                onClick={() => { setSelectedBuilding(null); setBuildingPopupPosition(null); }}
                className="text-slate-400 hover:text-white transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Type:</span>
                <span className="text-white capitalize">{selectedBuilding.type || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Height:</span>
                <span className="text-white">{selectedBuilding.height ? `${selectedBuilding.height.toFixed(1)}m` : 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Area:</span>
                <span className="text-white">{selectedBuilding.area ? `${selectedBuilding.area.toFixed(0)} m²` : 'N/A'}</span>
              </div>
              {selectedBuilding.floors && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Floors:</span>
                  <span className="text-white">{selectedBuilding.floors}</span>
                </div>
              )}
            </div>
            <div className="mt-2 pt-2 border-t border-slate-700">
              <button
                onClick={() => {
                  if (setAgentData && selectedBuilding) {
                    setAgentData(prev => ({
                      ...prev,
                      selectedBuilding: selectedBuilding,
                      clickedLocation: { lat: selectedBuilding.lat, lng: selectedBuilding.lng }
                    }))
                  }
                }}
                className="w-full py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition"
              >
                Analyze Building
              </button>
            </div>
          </div>
          {/* Arrow */}
          <div className="absolute left-1/2 bottom-0 transform -translate-x-1/2 translate-y-full">
            <div className="w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-slate-900"></div>
          </div>
        </div>
      )}

      {/* Time Simulation Controls - Bottom Center */}
      {showTimeControls && (
        <div className="absolute bottom-16 left-1/2 transform -translate-x-1/2 z-40 w-96">
          <div className="bg-slate-800/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-semibold text-white">Time Simulation</span>
              </div>
              <button
                onClick={() => setShowTimeControls(false)}
                className="text-slate-400 hover:text-white transition p-1"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Time Display */}
            <div className="mb-3 text-center">
              <div className="text-lg font-mono font-bold text-white">
                {(simulatedTime || currentTime).toLocaleTimeString('en-IN', { 
                  timeZone: 'Asia/Kolkata', 
                  hour: '2-digit', 
                  minute: '2-digit',
                  hour12: true 
                })}
              </div>
              <div className="text-xs text-slate-400">
                {(simulatedTime || currentTime).toLocaleDateString('en-IN', { 
                  timeZone: 'Asia/Kolkata', 
                  weekday: 'short', 
                  day: 'numeric', 
                  month: 'short',
                  year: 'numeric'
                })}
              </div>
            </div>

            {/* Time Presets */}
            <div className="grid grid-cols-4 gap-2 mb-3">
              {[
                { label: 'Dawn', hour: 6 },
                { label: 'Noon', hour: 12 },
                { label: 'Dusk', hour: 18 },
                { label: 'Night', hour: 0 }
              ].map(({ label, hour }) => (
                <button
                  key={label}
                  onClick={() => {
                    const viewer = viewerRef.current
                    if (!viewer || viewer.isDestroyed()) return
                    const newTime = new Date()
                    newTime.setHours(hour, 0, 0, 0)
                    setSimulatedTime(newTime)
                    viewer.clock.currentTime = Cesium.JulianDate.fromDate(newTime)
                  }}
                  className="px-2 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded transition"
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Speed Controls */}
            <div className="mb-2">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-300">Speed</span>
                <span className="text-xs text-blue-400 font-mono">{timeMultiplier}x</span>
              </div>
              <div className="grid grid-cols-5 gap-1">
                {[0, 1, 60, 3600, 86400].map((speed) => (
                  <button
                    key={speed}
                    onClick={() => {
                      const viewer = viewerRef.current
                      if (!viewer || viewer.isDestroyed()) return
                      setTimeMultiplier(speed)
                      viewer.clock.multiplier = speed
                      if (speed === 0) {
                        viewer.clock.shouldAnimate = false
                      } else {
                        viewer.clock.shouldAnimate = true
                      }
                    }}
                    className={`px-2 py-1 text-xs rounded transition ${
                      timeMultiplier === speed
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                    }`}
                  >
                    {speed === 0 ? 'Pause' : speed === 1 ? '1x' : speed === 60 ? '1m' : speed === 3600 ? '1h' : '1d'}
                  </button>
                ))}
              </div>
            </div>

            {/* Reset Button */}
            <button
              onClick={() => {
                const viewer = viewerRef.current
                if (!viewer || viewer.isDestroyed()) return
                setSimulatedTime(null)
                setTimeMultiplier(1)
                viewer.clock.currentTime = Cesium.JulianDate.now()
                viewer.clock.multiplier = 1
                viewer.clock.shouldAnimate = true
              }}
              className="w-full mt-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded transition"
            >
              Reset to Real-time
            </button>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 shadow-lg">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Loading Map...</p>
          </div>
        </div>
      )}

      {/* Storyboard Narration Overlay */}
      {storyboardPlaying && currentNarration && (
        <div className="absolute bottom-20 left-1/2 transform -translate-x-1/2 z-50 max-w-2xl">
          <div className="bg-slate-900/90 backdrop-blur-sm rounded-xl px-6 py-4 shadow-2xl border border-blue-500/30">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-white text-sm leading-relaxed">{currentNarration}</p>
              </div>
              <button 
                onClick={stopStoryboard}
                className="text-slate-400 hover:text-white transition p-1"
                title="Stop"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500 animate-pulse" style={{ width: '100%' }}></div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default memo(OnlineOSMMap)
