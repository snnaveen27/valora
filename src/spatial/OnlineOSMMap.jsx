import { useEffect, useRef, useState } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import '../styles/cesium.css'
import DrawingTools from '../components/DrawingTools'
import { API_URL } from '../apiConfig'

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

// Photorealistic tile cache settings (RAM-efficient with GPU optimization)
const PHOTOREALISTIC_CACHE_CONFIG = {
  maximumScreenSpaceError: 2, // Balanced quality vs performance (default: 2)
  maximumMemoryUsage: 512, // 512MB RAM-efficient (default: 512MB)
  preloadWhenHidden: false, // Save memory - only load visible tiles
  preloadFlightDestinations: false, // Save memory
  dynamicScreenSpaceError: true,
  dynamicScreenSpaceErrorDensity: 0.005, // Less aggressive = less RAM
  dynamicScreenSpaceErrorFactor: 4.0,
  skipLevelOfDetail: true, // Skip LODs for memory efficiency
  baseScreenSpaceError: 2048, // Higher = less detail = less RAM
  skipScreenSpaceErrorFactor: 32, // More aggressive skipping
  skipLevels: 2, // Skip more levels
  immediatelyLoadDesiredLevelOfDetail: false,
  loadSiblings: false, // Don't load adjacent tiles = save RAM
  cullWithChildrenBounds: true,
  cullRequestsWhileMoving: true,
  cullRequestsWhileMovingMultiplier: 120.0, // More aggressive culling
  progressiveResolutionHeightFraction: 0.5, // Less progressive detail
  foveatedScreenSpaceError: true, // GPU optimization - focus on center
  foveatedConeSize: 0.2, // Smaller cone = less detail outside center
  foveatedMinimumScreenSpaceErrorRelaxation: 0.5, // More relaxed outside center
  foveatedInterpolationCallback: undefined,
  foveatedTimeDelay: 0.1
}

// Backend API for local 3D buildings
const API_BASE = API_URL
const TILES_API = `${API_BASE}/api/tiles/viewport`
const POLYGON_ANALYZE_API = `${API_BASE}/api/spatial/polygon-analyze`
const BUFFER_ANALYZE_API = `${API_BASE}/api/spatial/buffer-analyze`

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
const DEFAULT_ORBIT_DISTANCE = 800
const DEFAULT_ORBIT_PITCH_DEG = -45

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

export function OnlineOSMMap({ agentData, setAgentData, onAnalysisUpdate, toggleMapFullscreen, isMapFullscreen }) {
  const cesiumContainerRef = useRef(null)
  const viewerRef = useRef(null)
  const loadedTilesRef = useRef(new Set())  // Track loaded tile IDs
  const tileEntitiesRef = useRef({})  // Map of tile_id -> entities[]
  const tileCentersRef = useRef({})  // Map of tile_id -> {lat, lng} for distance-based eviction
  const tileLoadTimesRef = useRef({})  // Map of tile_id -> timestamp to prevent immediate eviction
  const cameraMoveTimeoutRef = useRef(null)
  const selectedBuildingEntityRef = useRef(null)  // Track currently highlighted building
  const keyDownHandlerRef = useRef(null) // Track key handler so we can remove it on cleanup
  const lastCameraViewRef = useRef(null)
  const placeMarkerRef = useRef(null)
  const rotationIntervalRef = useRef(null)
  const rotationTargetRef = useRef(null)
  const ionPhotorealisticTilesetRef = useRef(null)
  const ionOsmBuildingsTilesetRef = useRef(null)
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
  const [tilesLoaded, setTilesLoaded] = useState(0)
  const [clickRipple, setClickRipple] = useState(null)
  const [canGoBack, setCanGoBack] = useState(false)
  
  // Enhanced layer visibility controls - optimized for RAM efficiency
  const [showBuildings, setShowBuildings] = useState(() => initialPrefsRef.current.showBuildings ?? true)
  const [showShadows, setShowShadows] = useState(() => initialPrefsRef.current.showShadows ?? false) // Shadows OFF by default (RAM save)
  const [showTerrainShadows, setShowTerrainShadows] = useState(() => initialPrefsRef.current.showTerrainShadows ?? false) // Terrain shadows OFF
  const [showTerrain, setShowTerrain] = useState(() => initialPrefsRef.current.showTerrain ?? true) // Terrain enabled by default
  const [terrainExaggeration, setTerrainExaggeration] = useState(() => initialPrefsRef.current.terrainExaggeration ?? 1)
  const [showIonPhotorealistic, setShowIonPhotorealistic] = useState(() => initialPrefsRef.current.showIonPhotorealistic ?? false)
  const [showIonOsmBuildings, setShowIonOsmBuildings] = useState(() => initialPrefsRef.current.showIonOsmBuildings ?? false)
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
  const [showWeatherDropdown, setShowWeatherDropdown] = useState(false)
  
  // Weather effects
  const [showRain, setShowRain] = useState(false)
  const [showSnow, setShowSnow] = useState(false)
  const [showClouds, setShowClouds] = useState(false)
  const [showWind, setShowWind] = useState(false)
  const [realtimeWeather, setRealtimeWeather] = useState(null)
  const [enableRealtimeWeather, setEnableRealtimeWeather] = useState(false)
  const rainSystemRef = useRef(null)
  const snowSystemRef = useRef(null)
  
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

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed() || !viewer.scene?.globe) return
    viewer.scene.globe.terrainExaggeration = terrainExaggeration
    viewer.scene.globe.terrainExaggerationRelativeHeight = 0.0
  }, [terrainExaggeration])

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

  // Aggressive tile eviction for RAM efficiency
  useEffect(() => {
    if (!showBuildings) return

    const evictionInterval = setInterval(() => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return

      const cameraPos = viewer.camera.positionCartographic
      const centerLat = Cesium.Math.toDegrees(cameraPos.latitude)
      const centerLng = Cesium.Math.toDegrees(cameraPos.longitude)

      const MAX_TILES = 50 // Aggressive limit for RAM
      const EVICTION_DISTANCE_KM = 5 // Evict tiles > 5km away

      const loadedTiles = Array.from(loadedTilesRef.current)
      if (loadedTiles.length > MAX_TILES) {
        // Calculate distances and evict furthest tiles
        const tilesWithDistance = loadedTiles.map(tileId => {
          const center = tileCentersRef.current[tileId]
          if (!center) return { tileId, distance: Infinity }
          
          const dx = (center.lng - centerLng) * 111
          const dy = (center.lat - centerLat) * 111
          const distance = Math.sqrt(dx * dx + dy * dy)
          
          return { tileId, distance }
        })

        tilesWithDistance.sort((a, b) => b.distance - a.distance)

        // Evict furthest tiles beyond limit
        const tilesToEvict = tilesWithDistance.slice(MAX_TILES)
        tilesToEvict.forEach(({ tileId, distance }) => {
          if (distance > EVICTION_DISTANCE_KM) {
            const entities = tileEntitiesRef.current[tileId] || []
            entities.forEach(entity => {
              try {
                viewer.entities.remove(entity)
              } catch (e) {}
            })
            delete tileEntitiesRef.current[tileId]
            delete tileCentersRef.current[tileId]
            delete tileLoadTimesRef.current[tileId]
            loadedTilesRef.current.delete(tileId)
          }
        })

        const evicted = tilesToEvict.filter(t => t.distance > EVICTION_DISTANCE_KM).length
        if (evicted > 0) {
          console.log(`🗑️ RAM optimization: Evicted ${evicted} distant tiles`)
        }
      }
    }, 5000) // Check every 5 seconds

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

    const fetchWeather = async () => {
      try {
        // Using OpenWeatherMap API (you'll need to add API key to .env)
        const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || 'demo'
        const response = await fetch(
          `https://api.openweathermap.org/data/2.5/weather?lat=${DEFAULT_LOCATION.lat}&lon=${DEFAULT_LOCATION.lng}&appid=${API_KEY}`
        )
        if (response.ok) {
          const data = await response.json()
          setRealtimeWeather(data)
          
          // Auto-apply weather effects based on real conditions
          const weatherCondition = data.weather[0]?.main?.toLowerCase()
          if (weatherCondition === 'rain' || weatherCondition === 'drizzle' || weatherCondition === 'thunderstorm') {
            setShowRain(true)
            setShowSnow(false)
          } else if (weatherCondition === 'snow') {
            setShowSnow(true)
            setShowRain(false)
          } else if (weatherCondition === 'clouds') {
            setShowClouds(true)
          } else {
            setShowRain(false)
            setShowSnow(false)
          }
          
          console.log('🌦️ Realtime weather applied:', weatherCondition)
        }
      } catch (err) {
        console.warn('Failed to fetch realtime weather:', err)
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
          console.log('✅ Local photorealistic tileset loaded with enhanced cache')
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
        setAgentData(prev => ({
          ...prev,
          polygonAnalysisPending: false,
          polygonAnalysis: null,
          polygonAnalysisError: 'Polygon has insufficient points'
        }))
        return
      }

      setAgentData(prev => ({
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
        setAgentData(prev => ({
          ...prev,
          polygonAnalysisPending: false,
          polygonAnalysisLoading: false,
          polygonAnalysis: data?.data || null,
          polygonAnalysisError: null,
        }))
      } catch (e) {
        setAgentData(prev => ({
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
        setAgentData(prev => ({
          ...prev,
          bufferAnalysisPending: false,
          bufferAnalysis: null,
          bufferAnalysisError: 'Buffer center or radius missing'
        }))
        return
      }

      setAgentData(prev => ({
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
        setAgentData(prev => ({
          ...prev,
          bufferAnalysisPending: false,
          bufferAnalysisLoading: false,
          bufferAnalysis: data?.data || null,
          bufferAnalysisError: null,
        }))
      } catch (e) {
        setAgentData(prev => ({
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
    let maxDistance = 35000

    if (kind === 'city') {
      fontPx = 18
      maxDistance = 250000
    } else if (kind === 'town') {
      fontPx = 16
      maxDistance = 180000
    } else if (kind === 'county') {
      fontPx = 16
      maxDistance = 350000
    } else if (kind === 'suburb') {
      fontPx = 14
      maxDistance = 70000
    } else if (kind === 'neighbourhood' || kind === 'quarter') {
      fontPx = 12
      maxDistance = 30000
    } else if (kind === 'village') {
      fontPx = 13
      maxDistance = 90000
    }

    const label = new Cesium.LabelGraphics({
      text: name,
      font: `600 ${fontPx}px Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`,
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.fromCssColorString('#0b1220'),
      outlineWidth: 4,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      showBackground: true,
      backgroundColor: Cesium.Color.fromCssColorString('#0b1220').withAlpha(0.45),
      backgroundPadding: new Cesium.Cartesian2(8, 4),
      pixelOffset: new Cesium.Cartesian2(0, -12),
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, maxDistance),
      scaleByDistance: new Cesium.NearFarScalar(1500.0, 1.0, maxDistance, 0.6),
      translucencyByDistance: new Cesium.NearFarScalar(800.0, 1.0, maxDistance, 0.0),
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    })

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
    if (newState && buildingsCount === 0) {
      console.log('[Buildings] Enabling - loading buildings for current viewport...')
      loadTilesForViewport()
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

    if (scene.pickPositionSupported) {
      const pickPosition = scene.pickPosition(screenPosition)
      if (Cesium.defined(pickPosition)) return pickPosition
    }

    const ray = viewer.camera.getPickRay(screenPosition)
    if (ray) {
      const globePosition = scene.globe.pick(ray, scene)
      if (Cesium.defined(globePosition)) return globePosition
    }

    return viewer.camera.pickEllipsoid(screenPosition, scene.globe.ellipsoid)
  }

  // Auto-rotate camera 360° around target during analysis loading
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const isAnalyzing = agentData?.buildingAnalysisLoading || agentData?.locationAnalysisLoading

    if (isAnalyzing && !rotationIntervalRef.current && rotationTargetRef.current) {
      // Start 360° orbit rotation around target at medium distance (800m)
      console.log('🎥 Starting 360° camera orbit')
      const target = rotationTargetRef.current
      const orbitDistance = DEFAULT_ORBIT_DISTANCE // Consistent distance across terrain/flat modes
      const pitch = Cesium.Math.toRadians(DEFAULT_ORBIT_PITCH_DEG)
      
      // Stop rotation on any user input (mouse/touch/wheel)
      const stopOnInput = () => {
        stopRotation()
        document.removeEventListener('mousedown', stopOnInput)
        document.removeEventListener('wheel', stopOnInput)
        document.removeEventListener('touchstart', stopOnInput)
      }
      document.addEventListener('mousedown', stopOnInput)
      document.addEventListener('wheel', stopOnInput)
      document.addEventListener('touchstart', stopOnInput)
      
      rotationIntervalRef.current = setInterval(() => {
        if (viewer && !viewer.isDestroyed() && target) {
          // Orbit around target by rotating heading (slower: 0.2° per frame for smoother look)
          viewer.camera.lookAt(
            target,
            new Cesium.HeadingPitchRange(
              viewer.camera.heading + Cesium.Math.toRadians(0.2),
              pitch,
              orbitDistance
            )
          )
          viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
        }
      }, 16) // ~60fps
    } else if (!isAnalyzing) {
      stopRotation()
    }

    return () => {
      stopRotation()
    }
  }, [agentData?.buildingAnalysisLoading, agentData?.locationAnalysisLoading])

  // Apply layer visibility controls
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    // Apply buildings visibility and shadow settings
    Object.values(tileEntitiesRef.current).forEach(entities => {
      entities.forEach(e => {
        if (e && e.polygon) {
          e.show = showBuildings
          if (e.polygon.shadows) {
            e.polygon.shadows = showShadows ? Cesium.ShadowMode.ENABLED : Cesium.ShadowMode.DISABLED
          }
        }
      })
    })
    
    // Update shadow map (but not globe lighting - terrain stays simple 3D)
    if (viewer.scene && viewer.shadowMap) {
      viewer.shadowMap.enabled = showShadows
      viewer.scene.globe.enableLighting = false  // Always disabled for simple 3D terrain
      viewer.scene.globe.shadows = (showTerrain && showTerrainShadows) ? Cesium.ShadowMode.RECEIVE_ONLY : Cesium.ShadowMode.DISABLED
      viewer.shadows = showShadows
    }
  }, [showBuildings, showShadows, showTerrain, showTerrainShadows])

  // Real-time clock - updates every second
  useEffect(() => {
    const clockInterval = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(clockInterval)
  }, [])

  // Place labels disabled - AI handles labels
  // useEffect(() => {
  //   if (placesDataSourceRef.current) {
  //     placesDataSourceRef.current.show = showPlaces
  //   }
  // }, [showPlaces])


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
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString('#3b82f6'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
      },
      label: {
        text: area.name,
        font: '14px sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.fromCssColorString('#111827'),
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -24),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
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
        setTimeout(loadTilesForViewport, 500)
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
        setTimeout(loadTilesForViewport, 500)
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
      setAgentData(prev => ({
        ...prev,
        drawnPolygon: polygonPoints,
        polygonAnalysisPending: true
      }))
    }
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
      setAgentData(prev => ({
        ...prev,
        drawnBuffer: { center: { lat, lng }, radius: bufferRadius },
        bufferAnalysisPending: true
      }))
    }
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
      setAgentData(prev => ({
        ...prev,
        drawnPolygon: null,
        drawnBuffer: null,
        polygonAnalysisPending: false,
        bufferAnalysisPending: false
      }))
    }
  }

  // Load a single tile and add buildings to scene
  const loadTile = async (tileId, tileUrl) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return false
    if (loadedTilesRef.current.has(tileId)) return false // Already loaded

    try {
      // Handle both relative and absolute URLs
      const url = tileUrl.startsWith('/api/') ? `${API_BASE}${tileUrl}` : `${API_BASE}${tileUrl}`
      const response = await fetch(url)
      if (!response.ok) return false

      const data = await response.json()
      
      // Add buildings from this tile/database response
      const entities = []
      viewer.entities.suspendEvents()
      
      // Track tile center from first building (for distance-based eviction)
      let tileCenterLat = null
      let tileCenterLng = null
      
      const features = data.features || []
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

        // Enhanced color scheme by building type and height
        const buildingType = props.building || props.type || 'building'
        const levels = props.levels || Math.round(height / 3)
        
        let color = '#d1d5db' // Default gray
        let alpha = 0.95
        
        // Color by building type first, then refine by height
        if (buildingType.includes('residential') || buildingType.includes('apartments') || buildingType.includes('house')) {
          // Residential: warm tones
          if (height > 30) color = '#9ca3af' // High-rise apartments
          else if (height > 15) color = '#bfbfbf' // Mid-rise
          else color = '#d4d4d4' // Low-rise houses
        } else if (buildingType.includes('commercial') || buildingType.includes('retail') || buildingType.includes('shop')) {
          // Commercial: blue-gray
          color = '#94a3b8'
        } else if (buildingType.includes('office')) {
          // Office: darker gray
          color = '#64748b'
        } else if (buildingType.includes('industrial')) {
          // Industrial: brownish
          color = '#92857c'
        } else {
          // Generic by height
          if (height > 50) color = '#8b92a0'
          else if (height > 30) color = '#a1a8b5'
          else if (height > 15) color = '#b8bfc9'
          else if (height > 8) color = '#cbd2db'
        }

        const entity = viewer.entities.add({
          name: props.name || `Building`,
          polygon: {
            hierarchy: polygonHierarchy,
            material: Cesium.Color.fromCssColorString(color).withAlpha(alpha),
            outline: true,
            outlineColor: Cesium.Color.fromCssColorString('#ffffff').withAlpha(0.15),
            outlineWidth: 1,
            height: 0,
            extrudedHeight: height,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            extrudedHeightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
            perPositionHeight: false,
            closeTop: true,
            closeBottom: true,
            shadows: showShadows ? Cesium.ShadowMode.ENABLED : Cesium.ShadowMode.DISABLED
          },
          properties: {
            height: height,
            levels: levels,
            type: buildingType,
            name: props.name || null,
            address: props.address || props['addr:street'] || null,
            lng: centroidLng,
            lat: centroidLat,
            area: props.area || 225 // Default ~15m x 15m
          }
        })
        entities.push(entity)
        
        // Store first building's centroid as tile center
        if (tileCenterLat === null && centroidLat && centroidLng) {
          tileCenterLat = centroidLat
          tileCenterLng = centroidLng
        }
      }
      
      viewer.entities.resumeEvents()
      
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

  // Load tiles for current viewport (progressive, persistent)
  const loadTilesForViewport = async () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    // Get camera position and height for aggressive LOD
    const cameraCartographic = Cesium.Cartographic.fromCartesian(viewer.camera.position)
    const cameraHeight = cameraCartographic.height
    const cameraLng = Cesium.Math.toDegrees(cameraCartographic.longitude)
    const cameraLat = Cesium.Math.toDegrees(cameraCartographic.latitude)

    // Don't load buildings when too far out (performance)
    if (cameraHeight > 10000) {
      setLoadingBuildings(false)
      return
    }

    // Aggressive LOD: only load tiles near camera based on height (FASTER LOADING - smaller radius)
    let loadRadius = 0.008 // ~800m default (reduced from 1km)
    if (cameraHeight < 500) loadRadius = 0.003      // 300m when very close (reduced)
    else if (cameraHeight < 1000) loadRadius = 0.006  // 600m (reduced)
    else if (cameraHeight < 2000) loadRadius = 0.01   // 1km (reduced)
    else if (cameraHeight < 5000) loadRadius = 0.015  // 1.5km (reduced)
    else loadRadius = 0.02  // 2km when far (reduced)

    // Load only tiles within radius of camera center (not entire viewport)
    const bbox = {
      min_lng: cameraLng - loadRadius,
      min_lat: cameraLat - loadRadius,
      max_lng: cameraLng + loadRadius,
      max_lat: cameraLat + loadRadius
    }

    // RAM Optimization: Distance-based eviction - release buildings far from camera
    const MAX_TILES_IN_MEMORY = 50  // Increased to prevent premature eviction
    const loadRadiusKm = loadRadius * 111.0
    const evictionDistanceKm = loadRadiusKm * 5  // Increased to 5x to keep buildings visible longer
    const MIN_TILE_AGE_MS = 10000  // Don't evict tiles loaded less than 10 seconds ago
    
    // Calculate distance from camera to each tile center
    const haversineDistance = (lat1, lng1, lat2, lng2) => {
      const R = 6371 // Earth radius in km
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLng = (lng2 - lng1) * Math.PI / 180
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLng/2) * Math.sin(dLng/2)
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    }
    
    // Distance-based eviction: Remove tiles far from current camera position
    const allTileIds = Array.from(loadedTilesRef.current)
    const tilesWithDistance = allTileIds.map(id => {
      const center = tileCentersRef.current[id]
      if (!center) return { id, distance: Infinity }
      const dist = haversineDistance(cameraLat, cameraLng, center.lat, center.lng)
      return { id, distance: dist }
    })
    
    // Sort by distance (farthest first) and evict tiles beyond eviction distance
    tilesWithDistance.sort((a, b) => b.distance - a.distance)
    
    // Evict tiles that are too far OR if we have too many tiles, BUT not if recently loaded
    const currentTime = Date.now()
    const tilesToEvict = tilesWithDistance.filter(t => {
      const loadTime = tileLoadTimesRef.current[t.id] || 0
      const tileAge = currentTime - loadTime
      
      // Don't evict tiles younger than MIN_TILE_AGE_MS
      if (tileAge < MIN_TILE_AGE_MS) return false
      
      // Evict if too far OR if we have too many tiles
      return t.distance > evictionDistanceKm || 
        (loadedTilesRef.current.size > MAX_TILES_IN_MEMORY && t.distance > loadRadiusKm * 2)
    })
    
    if (tilesToEvict.length > 0) {
      tilesToEvict.forEach(({ id }) => {
        const entities = tileEntitiesRef.current[id]
        if (entities) {
          entities.forEach(e => viewer.entities.remove(e))
          delete tileEntitiesRef.current[id]
        }
        delete tileCentersRef.current[id]
        delete tileLoadTimesRef.current[id]
        loadedTilesRef.current.delete(id)
      })
      console.log(`🧹 Released ${tilesToEvict.length} distant tiles from RAM (${loadedTilesRef.current.size} tiles remaining)`)
    }

    try {
      // Get tiles for viewport
      const params = new URLSearchParams(bbox)
      const response = await fetch(`${TILES_API}?${params}`)
      
      if (!response.ok) {
        console.warn('Tiles API not available:', response.status)
        return
      }

      const data = await response.json()
      
      // Filter to only unloaded tiles
      const newTiles = data.tiles.filter(t => !loadedTilesRef.current.has(t.id))
      
      if (newTiles.length === 0) return // All tiles already loaded
      
      // Limit total tiles to load at once for performance (INCREASED for faster loading)
      const maxTilesPerLoad = 24  // Increased from 16
      const tilesToLoad = newTiles.slice(0, maxTilesPerLoad)
      
      if (tilesToLoad.length === 0) return
      
      setLoadingBuildings(true)
      
      // Update agentData loading state
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          loadingBuildings: true
        }))
      }
      
      // Load tiles in parallel batches (INCREASED for faster loading)
      const batchSize = 8  // Increased from 4 for faster parallel loading
      let loadedCount = 0
      
      for (let i = 0; i < tilesToLoad.length; i += batchSize) {
        const batch = tilesToLoad.slice(i, i + batchSize)
        const results = await Promise.all(
          batch.map(tile => loadTile(tile.id, tile.url))
        )
        loadedCount += results.filter(r => r).length
      }
      
      // Update counts
      const totalBuildings = Object.values(tileEntitiesRef.current)
        .reduce((sum, entities) => sum + entities.length, 0)
      
      setBuildingsCount(totalBuildings)
      setTilesLoaded(loadedTilesRef.current.size)
      setBuildingsLoaded(true)
      setLoadingBuildings(false)
      
      // Update agentData with building stats
      if (setAgentData) {
        setAgentData(prev => ({
          ...prev,
          buildingsCount: totalBuildings,
          loadingBuildings: false
        }))
      }
      
      if (loadedCount > 0) {
        console.log(`🏢 Loaded ${loadedCount} new tiles (${totalBuildings} buildings total, ${loadedTilesRef.current.size} tiles)`)
      }
    } catch (err) {
      console.warn('Failed to load tiles:', err.message)
      setLoadingBuildings(false)
    }
  }

  // Handle flyTo commands from chat
  useEffect(() => {
    if (agentData?.flyTo && viewerRef.current) {
      const { lat, lng, zoom } = agentData.flyTo
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return

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
      
      // height calculation for closer zoom (production grade)
      const height = zoom ? Math.max(50, 15000000 / Math.pow(2, zoom)) : 400
      
      if (placeMarkerRef.current) {
        viewer.entities.remove(placeMarkerRef.current)
        placeMarkerRef.current = null
      }

      const placeName = agentData?.selectedPlace?.name || agentData?.selectedPlace?.display_name?.split(',')?.[0] || 'Selected location'
      placeMarkerRef.current = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lngNum, latNum),
        point: {
          pixelSize: 10,
          color: Cesium.Color.fromCssColorString('#3b82f6'),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        },
        label: {
          text: placeName,
          font: '14px sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.fromCssColorString('#111827'),
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cesium.Cartesian2(0, -24),
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      })

      // Terrain-aware camera height
      const terrainHeight = getTerrainHeight(lngNum, latNum)
      const adjustedHeight = height + terrainHeight
      
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lngNum, latNum, adjustedHeight),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-45),
          roll: 0
        },
        duration: 2.5,
        complete: () => {
          // Load buildings after flyTo completes
          setTimeout(loadTilesForViewport, 500)
        }
      })
      setTimeout(() => { if (setAgentData) setAgentData(prev => ({ ...prev, flyTo: null })) }, 3000)
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
        
        // Add new property markers
        properties.forEach((prop, index) => {
          if (!prop.lat || !prop.lng) return
          
          const priceLabel = prop.price ? `₹${(prop.price / 100000).toFixed(1)}L` : ''
          const bhkLabel = prop.bedrooms ? `${prop.bedrooms}BHK` : ''
          const label = [bhkLabel, priceLabel].filter(Boolean).join(' • ') || `Property ${index + 1}`
          
          const marker = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(prop.lng, prop.lat),
            point: {
              pixelSize: 12,
              color: Cesium.Color.fromCssColorString('#22c55e'),
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 2,
              heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
            },
            label: {
              text: label,
              font: '12px sans-serif',
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.fromCssColorString('#111827'),
              outlineWidth: 2,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              pixelOffset: new Cesium.Cartesian2(0, -20),
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
              showBackground: true,
              backgroundColor: Cesium.Color.fromCssColorString('#22c55e').withAlpha(0.8),
              backgroundPadding: new Cesium.Cartesian2(6, 3)
            }
          })
          propertyMarkersRef.current.push(marker)
        })
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
            pixelSize: 10,
            color: Cesium.Color.fromCssColorString('#3b82f6'),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
          },
          label: {
            text: 'Selected location',
            font: '14px sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.fromCssColorString('#111827'),
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(0, -24),
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        })

        const height = zoom ? Math.max(100, 20000 / Math.pow(2, zoom)) : 600
        // Terrain-aware camera height
        const terrainHeight = getTerrainHeight(lngNum, latNum)
        const adjustedHeight = height + terrainHeight
        
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lngNum, latNum, adjustedHeight),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
            roll: 0
          },
          duration: 2.5
        })
      }
    }
    
    window.addEventListener('valora-map-command', handleMapCommand)
    window.addEventListener('valora-ui-command', handleMapCommand)
    
    return () => {
      window.removeEventListener('valora-map-command', handleMapCommand)
      window.removeEventListener('valora-ui-command', handleMapCommand)
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
        const gpuVendor = hasGPU ? gl.getParameter(gl.VENDOR) : 'Unknown'
        const gpuRenderer = hasGPU ? gl.getParameter(gl.RENDERER) : 'Unknown'
        
        // Detect if dedicated GPU (NVIDIA, AMD) vs integrated (Intel)
        const isDedicatedGPU = gpuRenderer.toLowerCase().includes('nvidia') || 
                               gpuRenderer.toLowerCase().includes('amd') || 
                               gpuRenderer.toLowerCase().includes('radeon') ||
                               gpuRenderer.toLowerCase().includes('geforce') ||
                               gpuRenderer.toLowerCase().includes('rtx') ||
                               gpuRenderer.toLowerCase().includes('gtx')
        
        console.log(`🎮 GPU Detected: ${gpuVendor} - ${gpuRenderer}`)
        console.log(`🚀 GPU Type: ${isDedicatedGPU ? 'DEDICATED (High Performance Mode)' : 'INTEGRATED (Balanced Mode)'}`)
        
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
          shadows: true,
          shouldAnimate: true,
          terrainShadows: Cesium.ShadowMode.DISABLED,
          requestRenderMode: true, // RAM optimization - only render when needed
          maximumRenderTimeChange: 0.0, // GPU optimization - render every frame change
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

        // Auto-configure quality based on GPU type
        if (isDedicatedGPU) {
          console.log('🚀 DEDICATED GPU: Enabling high-end graphics for better simulations & storytelling')
          
          // High-quality shadows for dedicated GPU
          viewer.shadowMap.enabled = true
          viewer.shadowMap.darkness = 0.7
          viewer.shadowMap.size = 4096 // 4K shadow maps
          viewer.shadowMap.softShadows = true
          
          // Enable building shadows by default
          setShowShadows(true)
          
          // Set high building quality
          setBuildingQuality('high')
          
          // Higher resolution scale for sharper rendering
          viewer.resolutionScale = window.devicePixelRatio || 1.0
          
          console.log('✅ High-end graphics enabled: 4K shadows, high quality buildings, enhanced rendering')
        } else {
          console.log('⚖️ INTEGRATED GPU: Using balanced graphics settings')
          
          // Balanced shadows for integrated GPU
          viewer.shadowMap.enabled = true
          viewer.shadowMap.darkness = 0.6
          viewer.shadowMap.size = 2048
          viewer.shadowMap.softShadows = false // Disable soft shadows for performance
          
          // Shadows off by default for integrated GPU
          setShowShadows(false)
          
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

        // Configure globe - disable lighting to prevent dark terrain appearance
        viewer.scene.globe.show = true
        viewer.scene.globe.enableLighting = false  // Disabled to keep terrain bright
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#f0f0f0')
        viewer.scene.globe.terrainExaggeration = terrainExaggeration
        viewer.scene.globe.terrainExaggerationRelativeHeight = 0.0
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

        // Track camera changes
        viewer.camera.changed.addEventListener(updateHeading)
        
        // Track camera movement end to load buildings and update mapCenter (FASTER TRIGGER)
        viewer.camera.moveEnd.addEventListener(() => {
          clearTimeout(cameraMoveTimeoutRef.current)
          cameraMoveTimeoutRef.current = setTimeout(() => {
            // Only load tiles if buildings are enabled
            if (showBuildings) {
              loadTilesForViewport()
            }
            
            // Update mapCenter in agentData for viewport analysis
            if (setAgentData && viewer && !viewer.isDestroyed()) {
              try {
                const cameraCartographic = Cesium.Cartographic.fromCartesian(viewer.camera.position)
                const centerLat = Cesium.Math.toDegrees(cameraCartographic.latitude)
                const centerLng = Cesium.Math.toDegrees(cameraCartographic.longitude)
                const height = cameraCartographic.height
                
                if (Number.isFinite(centerLat) && Number.isFinite(centerLng)) {
                  setAgentData(prev => ({
                    ...prev,
                    mapCenter: { lat: centerLat, lng: centerLng, height }
                  }))
                }
              } catch (e) {
                console.warn('Failed to update mapCenter:', e)
              }
            }
          }, 200)  // Reduced from 500ms to 200ms for faster loading
        })

        // Function to deselect building
        const deselectBuilding = () => {
          if (selectedBuildingEntityRef.current && selectedBuildingEntityRef.current.polygon) {
            const entity = selectedBuildingEntityRef.current
            const height = entity.properties?.height?.getValue() || 10
            let color = '#e8e8e8'
            if (height > 50) color = '#9ca3af'
            else if (height > 30) color = '#a8a8a8'
            else if (height > 15) color = '#c4c4c4'
            else if (height > 8) color = '#d4d4d4'
            entity.polygon.material = Cesium.Color.fromCssColorString(color).withAlpha(0.9)
            entity.polygon.outline = false
            selectedBuildingEntityRef.current = null
          }
          
          if (setAgentData) {
            setAgentData(prev => ({
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

        // Auto-trigger building analysis when clicked
        const analyzeBuildingAsync = async (buildingData) => {
          if (!buildingData?.coordinates?.lat || !buildingData?.coordinates?.lng) return
          
          // Set loading state
          if (setAgentData) {
            setAgentData(prev => ({
              ...prev,
              buildingAnalysisLoading: true,
              buildingAnalysis: null
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
                setAgentData(prev => ({
                  ...prev,
                  buildingAnalysisLoading: false,
                  buildingAnalysis: analysis
                }))
              }
              console.log('🏢 Building analysis complete:', analysis)
            } else {
              console.warn('Building analysis failed:', response.status)
              if (setAgentData) {
                setAgentData(prev => ({
                  ...prev,
                  buildingAnalysisLoading: false
                }))
              }
            }
          } catch (err) {
            console.error('Building analysis error:', err)
            if (setAgentData) {
              setAgentData(prev => ({
                ...prev,
                buildingAnalysisLoading: false
              }))
            }
          }
        }

        // Click handler - select building instantly, otherwise deselect
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

          const pickedObject = viewer.scene.pick(click.position)

          // If building picked, select it
          if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.properties) {
            const entity = pickedObject.id
            const props = entity.properties

            const buildingData = {
              type: 'building_selected',
              name: props.name?.getValue() || 'Building',
              height: props.height?.getValue() || 10,
              levels: props.levels?.getValue() || 1,
              buildingType: props.type?.getValue() || 'building',
              address: props.address?.getValue() || null,
              coordinates: {
                lat: props.lat?.getValue(),
                lng: props.lng?.getValue()
              },
              area: props.area?.getValue() || 0
            }

            // Reset previously selected building
            deselectBuilding()

            // Highlight selected building (persistent)
            if (entity.polygon) {
              entity.polygon.material = Cesium.Color.fromCssColorString('#3b82f6').withAlpha(0.9)
              entity.polygon.outline = true
              entity.polygon.outlineColor = Cesium.Color.WHITE
              entity.polygon.outlineWidth = 2
              selectedBuildingEntityRef.current = entity
            }

            // Zoom to building with medium distance for better view
            const lat = buildingData.coordinates.lat
            const lng = buildingData.coordinates.lng
            const height = buildingData.height || 10
            const orbitDistance = DEFAULT_ORBIT_DISTANCE  // Medium distance for better building view
            const orbitPitch = Cesium.Math.toRadians(DEFAULT_ORBIT_PITCH_DEG)
            
            // Target is center of building
            const target = getTerrainAwareTarget(lng, lat, height / 2)
            rotationTargetRef.current = target
            
            // Fly to orbit position using lookAt
            viewer.camera.flyToBoundingSphere(
              new Cesium.BoundingSphere(target, orbitDistance / 2),
              {
                duration: 1.5,
                offset: new Cesium.HeadingPitchRange(0, orbitPitch, orbitDistance),
                complete: () => {
                  // Ensure exact orbit position after fly
                  viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(0, orbitPitch, orbitDistance))
                  viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
                }
              }
            )

            if (onAnalysisUpdate) {
              onAnalysisUpdate(buildingData)
            }

            if (setAgentData) {
              setAgentData(prev => ({
                ...prev,
                selectedBuilding: buildingData
              }))
            }

            // Auto-trigger comprehensive building analysis
            analyzeBuildingAsync(buildingData)
            
            // Dispatch event for chat panel to auto-respond
            window.dispatchEvent(new CustomEvent('valora-building-clicked', {
              detail: {
                building: buildingData,
                query: `Analyze this ${buildingData.type || 'building'} at ${buildingData.coordinates?.lat?.toFixed(5)}, ${buildingData.coordinates?.lng?.toFixed(5)}. It's ${buildingData.height || 'unknown'}m tall with ${buildingData.levels || 'unknown'} floors. Provide deep insights on valuation, investment potential, and nearby amenities.`
              }
            }))

            return
          }

          // Clicked empty ground: analyze location (for properties, lands, etc.)
          deselectBuilding()
          
          // Get the clicked position on the globe
          const cartesian = getGroundPositionFromScreen(click.position)
          if (cartesian) {
            const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
            const clickLat = Cesium.Math.toDegrees(cartographic.latitude)
            const clickLng = Cesium.Math.toDegrees(cartographic.longitude)
            
            if (Number.isFinite(clickLat) && Number.isFinite(clickLng)) {
              // Update selected location in agentData
              const locationData = {
                type: 'location_selected',
                coordinates: { lat: clickLat, lng: clickLng }
              }
              
              if (setAgentData) {
                setAgentData(prev => ({
                  ...prev,
                  selectedLocation: locationData.coordinates,
                  selectedBuilding: null,
                  buildingAnalysis: null
                }))
              }
              
              // Target is ground level at clicked location (terrain-aware)
              const target = getTerrainAwareTarget(clickLng, clickLat)
              rotationTargetRef.current = target
              const orbitDistance = DEFAULT_ORBIT_DISTANCE  // Medium distance for location view
              const orbitPitch = Cesium.Math.toRadians(DEFAULT_ORBIT_PITCH_DEG)
              
              // Fly to orbit position using lookAt
              viewer.camera.flyToBoundingSphere(
                new Cesium.BoundingSphere(target, orbitDistance / 2),
                {
                  duration: 1.5,
                  offset: new Cesium.HeadingPitchRange(0, orbitPitch, orbitDistance),
                  complete: () => {
                    // Ensure exact orbit position after fly
                    viewer.camera.lookAt(target, new Cesium.HeadingPitchRange(0, orbitPitch, orbitDistance))
                    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY)
                  }
                }
              )
              
              // Trigger location analysis
              analyzeLocationAsync(clickLat, clickLng)
            }
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
        
        // Analyze any clicked location (properties, lands, empty areas)
        const analyzeLocationAsync = async (lat, lng) => {
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
          
          // Set loading state
          if (setAgentData) {
            setAgentData(prev => ({
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
                setAgentData(prev => ({
                  ...prev,
                  locationAnalysisLoading: false,
                  locationAnalysis: analysis
                }))
              }
              console.log('📍 Location analysis complete:', analysis)
            } else {
              console.warn('Location analysis failed:', response.status)
              if (setAgentData) {
                setAgentData(prev => ({
                  ...prev,
                  locationAnalysisLoading: false
                }))
              }
            }
          } catch (err) {
            console.error('Location analysis error:', err)
            if (setAgentData) {
              setAgentData(prev => ({
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
          setAgentData(prev => ({
            ...prev,
            mapCenter: { lat: DEFAULT_LOCATION.lat, lng: DEFAULT_LOCATION.lng },
            mapLoaded: true
          }))
        }

        // Load initial buildings only when enabled
        if (showBuildings) {
          setTimeout(() => loadTilesForViewport(), 1500)
        }

        // Initialize terrain if enabled by default
        if (showTerrain) {
          setTimeout(async () => {
            try {
              if (viewer && !viewer.isDestroyed()) {
                // Switch to 3D globe mode for terrain
                viewer.scene.mode = Cesium.SceneMode.SCENE3D
                
                // Load Cesium Ion terrain
                viewer.terrainProvider = await Cesium.CesiumTerrainProvider.fromIonAssetId(ION_TERRAIN_ASSET_ID, {
                  requestWaterMask: true,
                  requestVertexNormals: true
                })
                
                // Terrain shadows controlled by separate checkbox
                viewer.scene.globe.shadows = showTerrainShadows ? Cesium.ShadowMode.RECEIVE_ONLY : Cesium.ShadowMode.DISABLED
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

  // Weather effects - Clouds (atmospheric effect)
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    if (showClouds) {
      viewer.scene.fog.enabled = true
      viewer.scene.fog.density = 0.0002
      viewer.scene.fog.minimumBrightness = 0.7
    } else {
      viewer.scene.fog.enabled = false
    }
  }, [showClouds])

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

          // Load buildings for this area
          setTimeout(loadTilesForViewport, 2500)
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

          {/* Divider */}
          <div className="h-4 w-px bg-slate-700" />

          {/* Weather Dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setShowWeatherDropdown(!showWeatherDropdown)
                setShowLayerPanel(false)
                setShowBasemapDropdown(false)
                setShowSearchResults(false)
              }}
              className={`flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold transition ${
                showWeatherDropdown ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
              </svg>
              <span>Weather</span>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Weather Dropdown Menu */}
            {showWeatherDropdown && (
              <div className="absolute top-full left-0 mt-1 bg-slate-900 border border-slate-700 shadow-2xl min-w-[180px] z-[60] rounded-sm p-2">
                <div className="text-[10px] text-slate-500 mb-2 font-semibold">Weather Effects</div>
                
                {/* Realtime Weather Toggle */}
                <label className="flex items-center gap-2 cursor-pointer text-xs text-blue-400 hover:text-blue-300 mb-2 pb-2 border-b border-slate-700">
                  <input
                    type="checkbox"
                    checked={enableRealtimeWeather}
                    onChange={(e) => setEnableRealtimeWeather(e.target.checked)}
                    className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                  />
                  <div className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span>Realtime Weather</span>
                  </div>
                </label>
                
                {/* Current Weather Info */}
                {realtimeWeather && (
                  <div className="mb-2 pb-2 border-b border-slate-700">
                    <div className="text-[9px] text-slate-400 space-y-0.5">
                      <div className="flex justify-between">
                        <span>Condition:</span>
                        <span className="text-slate-300 capitalize">{realtimeWeather.weather[0]?.description}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Temp:</span>
                        <span className="text-slate-300">{(realtimeWeather.main?.temp - 273.15).toFixed(1)}°C</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Manual Controls */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                    <input
                      type="checkbox"
                      checked={showRain}
                      onChange={(e) => setShowRain(e.target.checked)}
                      className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                    />
                    Rain
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                    <input
                      type="checkbox"
                      checked={showSnow}
                      onChange={(e) => setShowSnow(e.target.checked)}
                      className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                    />
                    Snow
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                    <input
                      type="checkbox"
                      checked={showClouds}
                      onChange={(e) => setShowClouds(e.target.checked)}
                      className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                    />
                    Clouds
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                    <input
                      type="checkbox"
                      checked={showWind}
                      onChange={(e) => setShowWind(e.target.checked)}
                      className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                    />
                    Wind
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Performance & Cache Info */}
          <div className="flex items-center gap-3 text-[10px] text-slate-400 mr-2">
            {/* GPU Type Badge */}
            {gpuInfo.isDedicated && (
              <div className="flex items-center gap-1 px-1.5 py-0.5 bg-purple-600/20 border border-purple-500/30 rounded">
                <svg className="w-3 h-3 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="font-semibold text-purple-300">Dedicated GPU</span>
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
              <div className="flex items-center gap-1">
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
                {/* 3D Layers */}
                <div className="mb-2">
                  <div className="text-[10px] text-slate-500 mb-1.5 font-semibold">3D Layers</div>
                  <div className="space-y-1.5">
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showBuildings}
                        onChange={(e) => {
                          setShowBuildings(e.target.checked)
                          const viewer = viewerRef.current
                          if (viewer && !viewer.isDestroyed()) {
                            viewer.entities.values.forEach(entity => {
                              if (entity.polygon) entity.show = e.target.checked
                            })
                          }
                        }}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Buildings
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showShadows}
                        onChange={(e) => {
                          setShowShadows(e.target.checked)
                          const viewer = viewerRef.current
                          if (viewer && !viewer.isDestroyed()) {
                            viewer.shadows = e.target.checked
                            viewer.shadowMap.enabled = e.target.checked
                          }
                        }}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Building Shadows
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showTerrainShadows}
                        onChange={(e) => {
                          setShowTerrainShadows(e.target.checked)
                          const viewer = viewerRef.current
                          if (viewer && !viewer.isDestroyed()) {
                            viewer.scene.globe.shadows = (showTerrain && e.target.checked) ? Cesium.ShadowMode.RECEIVE_ONLY : Cesium.ShadowMode.DISABLED
                          }
                        }}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Terrain Shadows
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showTerrain}
                        onChange={async (e) => {
                          setShowTerrain(e.target.checked)
                          const viewer = viewerRef.current
                          if (viewer && !viewer.isDestroyed()) {
                            if (e.target.checked) {
                              try {
                                // Switch to 3D globe mode for terrain
                                viewer.scene.mode = Cesium.SceneMode.SCENE3D
                                
                                // Load Cesium Ion terrain (basemap stays as selected)
                                viewer.terrainProvider = await Cesium.CesiumTerrainProvider.fromIonAssetId(ION_TERRAIN_ASSET_ID, {
                                  requestWaterMask: true,
                                  requestVertexNormals: true
                                })
                                
                                // Terrain shadows controlled by separate checkbox
                                viewer.scene.globe.shadows = showTerrainShadows ? Cesium.ShadowMode.RECEIVE_ONLY : Cesium.ShadowMode.DISABLED
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
                              } catch (err) {
                                console.error('Failed to load Cesium Ion terrain:', err)
                                viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider()
                              }
                            } else {
                              // Switch back to flat terrain (basemap stays as selected)
                              viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider()
                              
                              // Disable depth test for flat terrain
                              viewer.scene.globe.depthTestAgainstTerrain = false
                              
                              // Terrain has no shadows - simple 3D only
                              viewer.scene.globe.shadows = Cesium.ShadowMode.DISABLED
                              
                              // Disable sky and atmosphere for flat terrain
                              viewer.scene.skyBox = undefined
                              viewer.scene.skyAtmosphere = undefined
                              
                              console.log('✅ Flat terrain enabled with current basemap')
                            }
                          }
                        }}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Terrain
                    </label>
                    <div className="mt-2">
                      <div className="text-[10px] text-slate-500 mb-1">Terrain Exaggeration</div>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="0.5"
                          max="5"
                          step="0.5"
                          value={terrainExaggeration}
                          onChange={(e) => {
                            const viewer = viewerRef.current
                            const newValue = Number(e.target.value)
                            setTerrainExaggeration(newValue)
                            if (viewer && !viewer.isDestroyed() && viewer.scene?.globe) {
                              viewer.scene.globe.terrainExaggeration = newValue
                            }
                          }}
                          className="w-full accent-blue-600"
                        />
                        <span className="text-[10px] text-slate-300 w-9 text-right">
                          {terrainExaggeration.toFixed(1)}x
                        </span>
                      </div>
                    </div>
                    <label className="mt-2 flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
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
                
                {/* Weather Effects */}
                <div className="mb-2 pt-2 border-t border-slate-700">
                  <div className="text-[10px] text-slate-500 mb-1.5 font-semibold">Weather Effects</div>
                  <div className="space-y-1.5">
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showRain}
                        onChange={(e) => setShowRain(e.target.checked)}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Rain
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showSnow}
                        onChange={(e) => setShowSnow(e.target.checked)}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Snow
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showClouds}
                        onChange={(e) => setShowClouds(e.target.checked)}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Clouds
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white">
                      <input
                        type="checkbox"
                        checked={showWind}
                        onChange={(e) => setShowWind(e.target.checked)}
                        className="w-3 h-3 rounded bg-slate-700 border-slate-600 text-blue-600"
                      />
                      Wind
                    </label>
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
                    setTimeout(loadTilesForViewport, 2500)
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

export default OnlineOSMMap
