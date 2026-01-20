import { useEffect, useRef, useState } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import '../styles/cesium.css'

window.CESIUM_BASE_URL = '/cesium/'

// Backend API for local 3D buildings
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TILES_API = `${API_BASE}/api/tiles/viewport`

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

export function OnlineOSMMap({ agentData, setAgentData, onAnalysisUpdate }) {
  const cesiumContainerRef = useRef(null)
  const viewerRef = useRef(null)
  const loadedTilesRef = useRef(new Set())  // Track loaded tile IDs
  const tileEntitiesRef = useRef({})  // Map of tile_id -> entities[]
  const cameraMoveTimeoutRef = useRef(null)
  const selectedBuildingEntityRef = useRef(null)  // Track currently highlighted building
  const keyDownHandlerRef = useRef(null) // Track key handler so we can remove it on cleanup
  const lastCameraViewRef = useRef(null)
  const placeMarkerRef = useRef(null)
  const [isLoading, setIsLoading] = useState(true)
  const [is3DMode, setIs3DMode] = useState(true)
  const [heading, setHeading] = useState(0)
  const [selectedArea, setSelectedArea] = useState('indiranagar')
  const [buildingsLoaded, setBuildingsLoaded] = useState(false)
  const [buildingsCount, setBuildingsCount] = useState(0)
  const [loadingBuildings, setLoadingBuildings] = useState(false)
  const [tilesLoaded, setTilesLoaded] = useState(0)
  const [clickRipple, setClickRipple] = useState(null)
  const [basemap, setBasemap] = useState('osm') // 'osm' or 'mappls'
  const [hasMappls, setHasMappls] = useState(false)
  const imageryLayerRef = useRef(null)
  const [canGoBack, setCanGoBack] = useState(false)

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
    
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(area.lng, area.lat, height),
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

  const updateHeading = () => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    const headingDeg = Cesium.Math.toDegrees(viewer.camera.heading)
    setHeading(Math.round((headingDeg + 360) % 360))
  }

  // Fetch MapPLS API key from backend
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/config`)
        if (resp.ok) {
          const config = await resp.json()
          setHasMappls(Boolean(config?.has_mappls))
        }
      } catch (err) {
        console.error('Failed to fetch config:', err)
      }
    }
    fetchConfig()
  }, [])

  // Switch basemap function
  const switchBasemap = (newBasemap) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return
    
    // Remove current imagery layer
    if (imageryLayerRef.current) {
      viewer.imageryLayers.remove(imageryLayerRef.current)
      imageryLayerRef.current = null
    }
    
    // Add new imagery layer
    let provider
    if (newBasemap === 'mappls' && hasMappls) {
      // MapPLS tile provider (proxied via backend to avoid browser CORS)
      provider = new Cesium.UrlTemplateImageryProvider({
        url: `${API_BASE}/api/mappls/tiles/{z}/{x}/{y}.png`,
        maximumLevel: 19,
        credit: 'MapmyIndia'
      })
    } else {
      // OSM tile provider (default)
      provider = new Cesium.OpenStreetMapImageryProvider({
        url: 'https://tile.openstreetmap.org/'
      })
    }
    
    imageryLayerRef.current = viewer.imageryLayers.addImageryProvider(provider)
    setBasemap(newBasemap)
  }

  // Load a single tile and add buildings to scene
  const loadTile = async (tileId, tileUrl) => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return false
    if (loadedTilesRef.current.has(tileId)) return false // Already loaded

    try {
      const response = await fetch(`${API_BASE}${tileUrl}`)
      if (!response.ok) return false

      const data = await response.json()
      
      // Add buildings from this tile
      const entities = []
      viewer.entities.suspendEvents()
      
      for (const feature of data.features) {
        const coords = feature.geometry.coordinates[0]
        const props = feature.properties || {}
        const height = Math.max(props.height || 10, 3)

        // Calculate building centroid for location
        const lons = coords.map(c => c[0])
        const lats = coords.map(c => c[1])
        const centroidLng = lons.reduce((a, b) => a + b, 0) / lons.length
        const centroidLat = lats.reduce((a, b) => a + b, 0) / lats.length

        // Color by height for attractive visualization
        let color = '#e8e8e8'
        if (height > 50) color = '#9ca3af'
        else if (height > 30) color = '#a8a8a8'
        else if (height > 15) color = '#c4c4c4'
        else if (height > 8) color = '#d4d4d4'

        // Determine building type
        const buildingType = props.building || props.type || 'building'
        const levels = props.levels || Math.round(height / 3)

        const entity = viewer.entities.add({
          name: props.name || `Building`,
          polygon: {
            hierarchy: Cesium.Cartesian3.fromDegreesArray(coords.flat()),
            material: Cesium.Color.fromCssColorString(color).withAlpha(0.9),
            outline: false,
            extrudedHeight: height,
            height: 0,
            shadows: Cesium.ShadowMode.DISABLED
          },
          properties: {
            height: height,
            levels: levels,
            type: buildingType,
            name: props.name || null,
            address: props.address || props['addr:street'] || null,
            lng: centroidLng,
            lat: centroidLat,
            area: props.area || Math.round(Math.abs((coords[0][0] - coords[2][0]) * (coords[0][1] - coords[2][1]) * 111000 * 111000))
          }
        })
        entities.push(entity)
      }
      
      viewer.entities.resumeEvents()
      
      // Store entities for this tile (persistent - won't be removed)
      tileEntitiesRef.current[tileId] = entities
      loadedTilesRef.current.add(tileId)
      
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

    // Aggressive LOD: only load tiles near camera based on height
    let loadRadius = 0.005 // ~500m default
    if (cameraHeight < 500) loadRadius = 0.002      // 200m when very close
    else if (cameraHeight < 1000) loadRadius = 0.004  // 400m
    else if (cameraHeight < 2000) loadRadius = 0.006  // 600m
    else if (cameraHeight < 5000) loadRadius = 0.01   // 1km
    else loadRadius = 0.015  // 1.5km when far

    // Load only tiles within radius of camera center (not entire viewport)
    const bbox = {
      min_lng: cameraLng - loadRadius,
      min_lat: cameraLat - loadRadius,
      max_lng: cameraLng + loadRadius,
      max_lat: cameraLat + loadRadius
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
      
      // Limit total tiles to load at once for performance
      const maxTilesPerLoad = 8
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
      
      // Load tiles sequentially (2 at a time) - faster than 5 parallel
      const batchSize = 2
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
      
      // Calculate camera height based on zoom level
      // zoom 16 (street level) = 500m height
      // zoom 14 (neighborhood) = 2000m height
      // zoom 12 (city) = 8000m height
      const height = zoom ? Math.max(100, 50000 / Math.pow(2, zoom)) : 1500
      
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

      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lngNum, latNum, height),
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

  // Listen for map commands
  useEffect(() => {
    const handleMapCommand = (e) => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return
      
      const { action, coordinates, zoom } = e.detail || {}
      
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

        const height = zoom ? Math.max(100, 50000 / Math.pow(2, zoom)) : 1500
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lngNum, latNum, height),
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
        await new Promise(resolve => setTimeout(resolve, 100))
        if (cancelled) return

        // Create viewer with ONLINE OSM tiles
        const viewer = new Cesium.Viewer(cesiumContainerRef.current, {
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          animation: false,
          timeline: false,
          fullscreenButton: false,
          vrButton: false,
          infoBox: false,
          selectionIndicator: false,
          shadows: false,
          shouldAnimate: false,
          imageryProvider: false,
          terrainProvider: new Cesium.EllipsoidTerrainProvider(),
          skyBox: false,
          skyAtmosphere: false
        })

        viewerRef.current = viewer

        // Remove default layers and add ONLINE OSM tiles
        viewer.imageryLayers.removeAll()
        
        // Add OpenStreetMap online tiles (default)
        const osmProvider = new Cesium.OpenStreetMapImageryProvider({
          url: 'https://tile.openstreetmap.org/'
        })
        imageryLayerRef.current = viewer.imageryLayers.addImageryProvider(osmProvider)

        // Configure globe
        viewer.scene.globe.show = true
        viewer.scene.globe.enableLighting = false
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#f0f0f0')
        viewer.scene.globe.depthTestAgainstTerrain = false

        // Performance settings
        viewer.resolutionScale = 1.0
        viewer.scene.fog.enabled = false

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

        // Track camera changes
        viewer.camera.changed.addEventListener(updateHeading)
        
        // Track camera movement end to load buildings (longer debounce for performance)
        viewer.camera.moveEnd.addEventListener(() => {
          clearTimeout(cameraMoveTimeoutRef.current)
          cameraMoveTimeoutRef.current = setTimeout(() => {
            loadTilesForViewport()
          }, 500) // Increased from 200ms to 500ms
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

            return
          }

          // Clicked empty ground: deselect
          deselectBuilding()
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

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

        // Load initial buildings
        setTimeout(() => loadTilesForViewport(), 1500)

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

      {/* Basemap Toggle - Top Left */}
      {hasMappls && (
        <div className="absolute top-4 left-4 z-40">
          <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/50 overflow-hidden">
            <div className="flex">
              <button
                onClick={() => switchBasemap('osm')}
                className={`px-3 py-2 text-xs font-medium transition-colors ${
                  basemap === 'osm'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                title="OpenStreetMap"
              >
                OSM
              </button>
              <button
                onClick={() => switchBasemap('mappls')}
                className={`px-3 py-2 text-xs font-medium transition-colors border-l border-gray-200 ${
                  basemap === 'mappls'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                title="MapPLS"
              >
                MapPLS
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Map Controls - Top Right */}
      <div className="absolute top-4 right-4 z-40 flex flex-col gap-2">
        <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/50 overflow-hidden flex flex-col">
          <button
            onClick={goBackToLastView}
            disabled={!canGoBack}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 transition-colors border-b border-gray-100 disabled:opacity-40 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            title="Back to last view"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <button
            onClick={resetView}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 transition-colors"
            title="Reset view"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l9-9 9 9M4 10v10a1 1 0 001 1h5m4 0h5a1 1 0 001-1V10" />
            </svg>
          </button>
        </div>

        <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/50 overflow-hidden flex flex-col">
          <button
            onClick={zoomIn}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 transition-colors border-b border-gray-100"
            title="Zoom In"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
          <button
            onClick={zoomOut}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 transition-colors"
            title="Zoom Out"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
        </div>

        <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/50 overflow-hidden flex flex-col">
          <button
            onClick={resetNorth}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 transition-colors border-b border-gray-100 relative"
            title="Reset North"
          >
            <div 
              className="absolute inset-0 flex items-center justify-center transition-transform duration-300"
              style={{ transform: `rotate(${-heading}deg)` }}
            >
              <div className="w-0.5 h-3 bg-red-500 rounded-t-sm -mt-1"></div>
            </div>
          </button>
          <button
            onClick={toggle3D}
            className="w-9 h-9 flex items-center justify-center hover:bg-gray-50 active:bg-gray-100 transition-colors text-xs font-bold text-gray-700"
            title={is3DMode ? 'Switch to 2D' : 'Switch to 3D'}
          >
            {is3DMode ? '2D' : '3D'}
          </button>
        </div>
      </div>


      {isLoading && (
        <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 shadow-lg">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Loading Online Map...</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default OnlineOSMMap
