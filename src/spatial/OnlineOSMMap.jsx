import { useEffect, useRef, useState } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import '../styles/cesium.css'
import DrawingTools from '../components/DrawingTools'
import { API_URL } from '../apiConfig'

window.CESIUM_BASE_URL = '/cesium/'

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

export function OnlineOSMMap({ agentData, setAgentData, onAnalysisUpdate }) {
  const cesiumContainerRef = useRef(null)
  const viewerRef = useRef(null)
  const loadedTilesRef = useRef(new Set())  // Track loaded tile IDs
  const tileEntitiesRef = useRef({})  // Map of tile_id -> entities[]
  const tileCentersRef = useRef({})  // Map of tile_id -> {lat, lng} for distance-based eviction
  const cameraMoveTimeoutRef = useRef(null)
  const selectedBuildingEntityRef = useRef(null)  // Track currently highlighted building
  const keyDownHandlerRef = useRef(null) // Track key handler so we can remove it on cleanup
  const lastCameraViewRef = useRef(null)
  const placeMarkerRef = useRef(null)
  const rotationIntervalRef = useRef(null)
  const rotationTargetRef = useRef(null)
  const placesDataSourceRef = useRef(null)
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
  
  // Enhanced layer visibility controls - buildings and shadows always on
  const [showBuildings, setShowBuildings] = useState(true)
  const [showShadows, setShowShadows] = useState(true)
  const [showTerrain, setShowTerrain] = useState(false) // Start flat, enable for terrain analysis
  const [buildingQuality, setBuildingQuality] = useState('high') // low, medium, high
  
  // Real-time clock state
  const [currentTime, setCurrentTime] = useState(new Date())
  
  // Basemap toggle: 'osm', 'mapbox_streets', 'mapbox_satellite', 'mapbox_satellite_streets', 'mapbox_dark', 'mapbox_light', 'mapbox_outdoors'
  const [basemapType, setBasemapType] = useState('osm')
  
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

  // Auto-rotate camera 360° around target during analysis loading
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || viewer.isDestroyed()) return

    const isAnalyzing = agentData?.buildingAnalysisLoading || agentData?.locationAnalysisLoading

    if (isAnalyzing && !rotationIntervalRef.current && rotationTargetRef.current) {
      // Start 360° orbit rotation around target at medium distance (250m)
      console.log('🎥 Starting 360° camera orbit')
      const target = rotationTargetRef.current
      const orbitDistance = 250 // Medium distance for better building view
      const pitch = Cesium.Math.toRadians(-45) // 45° downward angle
      
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
    
    // Update shadow map and globe lighting
    if (viewer.scene && viewer.shadowMap) {
      viewer.shadowMap.enabled = showShadows
      viewer.scene.globe.enableLighting = showShadows
      viewer.shadows = showShadows
    }
  }, [showBuildings, showShadows])

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
      const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
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
      const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
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
            extrudedHeight: height,
            height: 0,
            shadows: Cesium.ShadowMode.ENABLED
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
      }
      
      viewer.entities.resumeEvents()
      
      // Store entities for this tile
      tileEntitiesRef.current[tileId] = entities
      loadedTilesRef.current.add(tileId)

      // Store tile center for distance-based eviction
      if (entities.length > 0 && centroidLat && centroidLng) {
        tileCentersRef.current[tileId] = {
          lat: centroidLat,
          lng: centroidLng
        }
      }
      
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
    const MAX_TILES_IN_MEMORY = 30  // Reduced from 40 for faster cleanup
    const loadRadiusKm = loadRadius * 111.0
    const evictionDistanceKm = loadRadiusKm * 3  // Reduced from 4x for more aggressive cleanup
    
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
    
    // Evict tiles that are too far OR if we have too many tiles
    const tilesToEvict = tilesWithDistance.filter(t => 
      t.distance > evictionDistanceKm || 
      (loadedTilesRef.current.size > MAX_TILES_IN_MEMORY && t.distance > loadRadiusKm * 1.5)
    )
    
    if (tilesToEvict.length > 0) {
      tilesToEvict.forEach(({ id }) => {
        const entities = tileEntitiesRef.current[id]
        if (entities) {
          entities.forEach(e => viewer.entities.remove(e))
          delete tileEntitiesRef.current[id]
        }
        delete tileCentersRef.current[id]
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

        // Create viewer with online OSM tiles
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
          shadows: true,
          shouldAnimate: true,
          imageryProvider: false,
          terrainProvider: new Cesium.EllipsoidTerrainProvider(),
          skyBox: false,
          skyAtmosphere: false
        })

        viewerRef.current = viewer

        // Configure shadow map
        viewer.shadowMap.enabled = true
        viewer.shadowMap.darkness = 0.6
        viewer.shadowMap.size = 2048
        viewer.shadowMap.softShadows = true

        // Remove default layers and add OSM tiles with proper configuration
        viewer.imageryLayers.removeAll(true)
        
        // Use OSM tiles with CORS proxy configuration for production
        const osmProvider = new Cesium.OpenStreetMapImageryProvider({
          url: 'https://tile.openstreetmap.org/',
          credit: '© OpenStreetMap contributors',
          enablePickFeatures: false
        })
        
        // Add error handling for tile loading
        osmProvider.errorEvent.addEventListener((error) => {
          console.warn('OSM tile loading error:', error)
        })
        
        const imageryLayer = viewer.imageryLayers.addImageryProvider(osmProvider)
        imageryLayer.alpha = 1.0
        imageryLayer.brightness = 1.0
        
        console.log('🗺️ Using OSM tiles')

        // Configure globe with lighting for shadows
        viewer.scene.globe.show = true
        viewer.scene.globe.enableLighting = true
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#f0f0f0')
        viewer.scene.globe.depthTestAgainstTerrain = false

        // Set Cesium clock to current real time for accurate sun position & shadows
        viewer.clock.currentTime = Cesium.JulianDate.now()
        viewer.clock.shouldAnimate = true
        viewer.clock.multiplier = 1 // Real-time

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

            // Zoom to street-level view of building (150m orbit distance)
            const lat = buildingData.coordinates.lat
            const lng = buildingData.coordinates.lng
            const height = buildingData.height || 10
            const orbitDistance = 300
            const orbitPitch = Cesium.Math.toRadians(-45)
            
            // Target is center of building
            const target = Cesium.Cartesian3.fromDegrees(lng, lat, height / 2)
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
          const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
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
              
              // Target is ground level at clicked location
              const target = Cesium.Cartesian3.fromDegrees(clickLng, clickLat, 0)
              rotationTargetRef.current = target
              const orbitDistance = 300
              const orbitPitch = Cesium.Math.toRadians(-45)
              
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

      // Animate camera
      if (scene.camera) {
        const { lat, lng, height, heading, pitch, duration } = scene.camera
        const destination = Cesium.Cartesian3.fromDegrees(
          lng || DEFAULT_LOCATION.lng,
          lat || DEFAULT_LOCATION.lat,
          height || 500
        )

        await new Promise((resolve) => {
          viewer.camera.flyTo({
            destination,
            orientation: {
              heading: Cesium.Math.toRadians(heading || 0),
              pitch: Cesium.Math.toRadians(pitch || -35),
              roll: 0
            },
            duration: (duration || 3000) / 1000,
            complete: resolve
          })
        })
      }

      // Wait for scene duration
      const waitTime = scene.duration || 3000
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

      const localityName = e.detail?.locality
      if (!localityName) return

      // Fetch locality coordinates from API
      try {
        const resp = await fetch(`${API_BASE}/api/city-intelligence/locality/${encodeURIComponent(localityName)}`)
        if (resp.ok) {
          const data = await resp.json()
          if (data.profile?.coordinates) {
            const { lat, lng } = data.profile.coordinates
            
            // Fly to locality with storytelling animation
            viewer.camera.flyTo({
              destination: Cesium.Cartesian3.fromDegrees(lng, lat, 800),
              orientation: {
                heading: Cesium.Math.toRadians(45),
                pitch: Cesium.Math.toRadians(-35),
                roll: 0
              },
              duration: 2.0,
              complete: () => {
                // Orbit around locality
                const target = Cesium.Cartesian3.fromDegrees(lng, lat, 50)
                rotationTargetRef.current = target
                
                // Start gentle orbit
                let orbitHeading = 45
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
                      Cesium.Math.toRadians(-35),
                      600
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

      {/* Basemap Selector - Top Center Bar */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-40">
        <div className="bg-slate-800/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700 px-2 py-1.5 flex items-center gap-1">
          <button
            onClick={() => switchBasemap('osm')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'osm' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="OpenStreetMap"
          >
            Street Map
          </button>
          <button
            onClick={() => switchBasemap('mapbox_streets')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'mapbox_streets' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="Mapbox Streets"
          >
            Streets
          </button>
          <button
            onClick={() => switchBasemap('mapbox_satellite')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'mapbox_satellite' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="Mapbox Satellite Imagery"
          >
            Satellite
          </button>
          <button
            onClick={() => switchBasemap('mapbox_satellite_streets')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'mapbox_satellite_streets' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="Mapbox Satellite with Street Labels"
          >
            Hybrid
          </button>
          <button
            onClick={() => switchBasemap('mapbox_dark')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'mapbox_dark' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="Mapbox Dark Theme"
          >
            Dark
          </button>
          <button
            onClick={() => switchBasemap('mapbox_light')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'mapbox_light' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="Mapbox Light Theme"
          >
            Light
          </button>
          <button
            onClick={() => switchBasemap('mapbox_outdoors')}
            className={`px-3 py-1.5 rounded transition-colors text-[11px] font-semibold whitespace-nowrap ${
              basemapType === 'mapbox_outdoors' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-300 hover:bg-slate-700'
            }`}
            title="Mapbox Outdoors with Terrain"
          >
            Outdoors
          </button>
        </div>
      </div>

      {/* Drawing Tools - Bottom Left */}
      <div className="absolute bottom-4 left-4 z-40">
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

      {/* Navigation Controls - Top Right (Dark Theme) */}
      <div className="absolute top-4 right-4 z-40 flex flex-col gap-2">
        <div className="bg-slate-800/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700 overflow-hidden flex flex-col">
          <button
            onClick={goBackToLastView}
            disabled={!canGoBack}
            className="w-9 h-9 flex items-center justify-center hover:bg-slate-700 active:bg-slate-600 transition-colors border-b border-slate-700 disabled:opacity-40 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            title="Back to last view"
          >
            <svg className="w-5 h-5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <button
            onClick={resetView}
            className="w-9 h-9 flex items-center justify-center hover:bg-slate-700 active:bg-slate-600 transition-colors"
            title="Reset view"
          >
            <svg className="w-5 h-5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l9-9 9 9M4 10v10a1 1 0 001 1h5m4 0h5a1 1 0 001-1V10" />
            </svg>
          </button>
        </div>

        <div className="bg-slate-800/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700 overflow-hidden flex flex-col">
          <button
            onClick={zoomIn}
            className="w-9 h-9 flex items-center justify-center hover:bg-slate-700 active:bg-slate-600 transition-colors border-b border-slate-700"
            title="Zoom In"
          >
            <svg className="w-5 h-5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
          <button
            onClick={zoomOut}
            className="w-9 h-9 flex items-center justify-center hover:bg-slate-700 active:bg-slate-600 transition-colors"
            title="Zoom Out"
          >
            <svg className="w-5 h-5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
        </div>

        <div className="bg-slate-800/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700 overflow-hidden flex flex-col">
          <button
            onClick={resetNorth}
            className="w-9 h-9 flex items-center justify-center hover:bg-slate-700 active:bg-slate-600 transition-colors border-b border-slate-700 relative"
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
            className="w-9 h-9 flex items-center justify-center hover:bg-slate-700 active:bg-slate-600 transition-colors text-xs font-bold text-slate-300"
            title={is3DMode ? 'Switch to 2D' : 'Switch to 3D'}
          >
            {is3DMode ? '2D' : '3D'}
          </button>
        </div>

      </div>

      {/* Real-time Clock & Status - Bottom Right */}
      <div className="absolute bottom-4 right-4 z-30 flex flex-col gap-2">
        {/* Live Clock with Bangalore Timezone */}
        <div className="bg-slate-900/90 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700/50 px-3 py-2">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-right">
              <div className="text-sm font-mono font-semibold text-white">
                {currentTime.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
              </div>
              <div className="text-[10px] text-slate-400">
                {currentTime.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: 'numeric', month: 'short' })} • IST
              </div>
            </div>
          </div>
        </div>

        {/* Buildings Status */}
        <div className="bg-slate-900/90 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700/50 px-3 py-2 text-xs">
          <div className="flex items-center gap-2">
            {loadingBuildings ? (
              <>
                <svg className="w-4 h-4 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-slate-300">Loading buildings...</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-slate-300 font-medium">{buildingsCount.toLocaleString()} buildings</span>
              </>
            )}
          </div>
        </div>
      </div>


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
