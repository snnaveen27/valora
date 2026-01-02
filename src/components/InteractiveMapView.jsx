import { useEffect, useRef, useState, useCallback } from 'react'
import { 
  MapPin, Navigation, Layers, Pentagon, Square, Circle, 
  Trash2, Move, Ruler, Info, Target, Edit2, X, Minus, Home, Building, TrendingUp, ChevronDown,
  Undo2, Redo2, Grid, Save, Maximize2, Maximize, Plus, Type
} from 'lucide-react'
import './MapView.css'
import { EnhancedDrawingSystem } from './EnhancedDrawingSystem'

const InteractiveMapView = ({ mapProvider = 'mappls' }) => {
  // Locked to Mappls only - no other map providers supported
  const mapContainerRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const drawingManagerRef = useRef(null)
  
  // Layer management
  const [layers, setLayers] = useState({
    properties: true,
    zones: true,
    polygons: true,
    heatmap: false,
    transit: false
  })
  
  // Drawing state
  const [drawingMode, setDrawingMode] = useState(null) // 'polygon', 'polyline', 'circle', 'rectangle', 'marker'
  const [drawnShapes, setDrawnShapes] = useState([])
  const [selectedShape, setSelectedShape] = useState(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const drawingStateRef = useRef({ points: [], tempMarkers: [], tempShape: null })
  
  // Map state
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isGeocoding, setIsGeocoding] = useState(false)
  const [mapCenter, setMapCenter] = useState([12.9716, 77.5946]) // Bangalore default
  const [mapZoom, setMapZoom] = useState(12)
  const [properties, setProperties] = useState([])
  const [showProperties, setShowProperties] = useState(false)
  const [is3DView, setIs3DView] = useState(false)
  const [showDrawDropdown, setShowDrawDropdown] = useState(false)
  const [showLayersDropdown, setShowLayersDropdown] = useState(false)
  const [showEnhancedTools, setShowEnhancedTools] = useState(false)
  const [undoStack, setUndoStack] = useState([])
  const [redoStack, setRedoStack] = useState([])
  const [sizeSlider, setSizeSlider] = useState(100)
  
  // Filter dropdowns state
  const [showPropertyTypeDropdown, setShowPropertyTypeDropdown] = useState(false)
  const [showPriceRangeDropdown, setShowPriceRangeDropdown] = useState(false)
  const [showAreaDropdown, setShowAreaDropdown] = useState(false)
  const [selectedPropertyTypes, setSelectedPropertyTypes] = useState([])
  const [selectedPriceRange, setSelectedPriceRange] = useState('All')
  const [selectedArea, setSelectedArea] = useState('All')

  // State from EnhancedMapTools
  const [measureMode, setMeasureMode] = useState(null) // 'distance' | 'area' | null
  const [editMode, setEditMode] = useState(null) // 'move' | 'rotate' | 'scale' | null
  const [snapToGrid, setSnapToGrid] = useState(false)
  const [showCoordinates, setShowCoordinates] = useState(true)
  const [colorPicker, setColorPicker] = useState(false)
  const [selectedColor, setSelectedColor] = useState('#3b82f6')
  const measurePointsRef = useRef([])
  const historyRef = useRef({ undo: [], redo: [] })
  
  const pushUndoSnapshot = (prevShapes) => {
    try {
      const deep = JSON.parse(JSON.stringify(prevShapes))
      historyRef.current.undo.push(deep)
      historyRef.current.redo = []
    } catch (_) {}
  }

  
  
  const handleUndo = () => {
    const u = historyRef.current.undo
    if (!u.length) return
    try {
      const current = JSON.parse(JSON.stringify(drawnShapes))
      historyRef.current.redo.push(current)
      const snapshot = u.pop()
      setDrawnShapes(snapshot)
      saveShapesToStorage(snapshot)
      setSelectedShape(null)
      setTimeout(() => syncShapesToCurrentView(), 0)
    } catch (_) {}
  }
  
  const handleRedo = () => {
    const r = historyRef.current.redo
    if (!r.length) return
    try {
      const current = JSON.parse(JSON.stringify(drawnShapes))
      historyRef.current.undo.push(current)
      const snapshot = r.pop()
      setDrawnShapes(snapshot)
      saveShapesToStorage(snapshot)
      setSelectedShape(null)
      setTimeout(() => syncShapesToCurrentView(), 0)
    } catch (_) {}
  }
  
  const resizeSelected = (factor) => {
    if (!selectedShape) return
    setDrawnShapes(prev => {
      pushUndoSnapshot(prev)
      const updated = prev.map(s => {
        if (s.id !== selectedShape.id) return s
        if (s.type === 'text') {
          const newFont = Math.max(8, Math.round((s.fontSize || 14) * factor))
          return { ...s, fontSize: newFont }
        }
        if (s.type === 'circle') {
          const newRadius = Math.max(10, Math.round((s.radius || 1000) * factor))
          return { ...s, radius: newRadius }
        }
        if (s.type === 'polygon' || s.type === 'rectangle' || s.type === 'polyline') {
          const pts = s.points || []
          if (!pts.length) return s
          const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length
          const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length
          const newPts = pts.map(p => [cx + (p[0] - cx) * factor, cy + (p[1] - cy) * factor])
          return { ...s, points: newPts }
        }
        return s
      })
      const newSel = updated.find(s => s.id === selectedShape.id)
      if (newSel) setSelectedShape(newSel)
      saveShapesToStorage(updated)
      setTimeout(() => syncShapesToCurrentView(), 0)
      return updated
    })
  }
  
  useEffect(() => {
    const onKeyDown = (e) => {
      const ae = document.activeElement
      if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.isContentEditable)) {
        return
      }
      if (isDrawing && e.key === 'Escape') {
        e.preventDefault()
        try {
          if (activeClickHandlerRef.current && mapInstanceRef.current) {
            mapInstanceRef.current.off('click', activeClickHandlerRef.current)
          }
        } catch (_) {}
        try { (drawingStateRef.current.tempMarkers || []).forEach(m => safeRemove(m)) } catch (_) {}
        drawingStateRef.current.tempMarkers = []
        setIsDrawing(false)
        setDrawingMode(null)
        return
      }
      if (e.ctrlKey && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault()
        handleUndo()
        return
      }
      if ((e.ctrlKey && e.key.toLowerCase() === 'y') || (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'z')) {
        e.preventDefault()
        handleRedo()
        return
      }
      if (e.key === 'Delete') {
        e.preventDefault()
        deleteSelectedShape()
        return
      }
      if (selectedShape && (e.key === '+' || e.key === '=')) {
        e.preventDefault()
        resizeSelected(1.1)
        return
      }
      if (selectedShape && e.key === '-') {
        e.preventDefault()
        resizeSelected(0.9)
        return
      }
      if (!e.ctrlKey && !e.metaKey) {
        const k = e.key.toLowerCase()
        if (k === 'p') {
          e.preventDefault()
          if (mapProvider === 'mappls' && drawingManagerRef.current) {
            setDrawingMode('polygon')
            drawingManagerRef.current.startPolygon()
          } else {
            setDrawingMode('polygon')
          }
          return
        }
        if (k === 'c') {
          e.preventDefault()
          if (mapProvider === 'mappls') startCircleDrawing(window.mappls)
          else setDrawingMode('circle')
          return
        }
        if (k === 'r') {
          e.preventDefault()
          if (mapProvider === 'mappls') startRectangleDrawing(window.mappls)
          else setDrawingMode('rectangle')
          return
        }
        if (k === 'l') {
          e.preventDefault()
          if (mapProvider === 'mappls' && drawingManagerRef.current) drawingManagerRef.current.startPolyline()
          else setDrawingMode('polyline')
          return
        }
        if (k === 'm') {
          e.preventDefault()
          if (mapProvider === 'mappls') startMarkerDrawing(window.mappls)
          else setDrawingMode('marker')
          return
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedShape, drawnShapes, isDrawing])
  
  useEffect(() => {
    setSizeSlider(100)
  }, [selectedShape])
  
  const togglePropertyType = useCallback((type) => {
    setSelectedPropertyTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type])
  }, [])
  
  const clearPropertyTypes = () => {
    setSelectedPropertyTypes([])
  }
  
  const applyPropertyTypes = () => {
    refreshPropertyMarkers()
    setShowPropertyTypeDropdown(false)
  }

  const propertyTypeLabel = selectedPropertyTypes.length === 0
    ? 'All'
    : (selectedPropertyTypes.length <= 2
      ? selectedPropertyTypes.join(', ')
      : `${selectedPropertyTypes.length} selected`)
  
  const normalizeText = (s) => (s || '').toString().toLowerCase()
  const getBedrooms = (p) => Number(p?.bedrooms ?? 0)
  const getPrice = (p) => Number(p?.price ?? 0)
  const getArea = (p) => Number(p?.covered_area ?? 0)
  
  const matchesAnyType = (property, types) => {
    if (!types || types.length === 0) return true
    const name = normalizeText(property?.name)
    const url = normalizeText(property?.url)
    const text = `${name} ${url}`
    const bhk = getBedrooms(property)
    
    const checkType = (t) => {
      const tLower = normalizeText(t)
      switch (tLower) {
        case 'flat':
          return text.includes('apartment') || text.includes('flat')
        case 'house/villa':
          return text.includes('house') || text.includes('villa')
        case 'plot':
          return text.includes('plot')
        case '1 bhk': return bhk === 1
        case '2 bhk': return bhk === 2
        case '3 bhk': return bhk === 3
        case '4 bhk': return bhk === 4
        case '5 bhk': return bhk === 5
        case '5+ bhk': return bhk >= 5
        case 'office space':
          return text.includes('office')
        case 'shop/showroom':
          return text.includes('shop') || text.includes('showroom')
        case 'commercial land':
          return text.includes('commercial land') || text.includes('commercial-land')
        case 'warehouse/godown':
          return text.includes('warehouse') || text.includes('godown')
        case 'industrial building':
          return text.includes('industrial building')
        case 'industrial shed':
          return text.includes('industrial shed')
        case 'agricultural land':
          return text.includes('agricult')
        case 'farm house':
          return text.includes('farm house') || text.includes('farmhouse')
        default:
          return false
      }
    }
    
    return types.some(checkType)
  }
  
  const withinPriceRange = (property, rangeLabel) => {
    if (!rangeLabel || rangeLabel === 'All') return true
    const price = getPrice(property)
    const L = 100000
    const CR = 10000000
    const ranges = {
      'Under 50L': [0, 50 * L],
      '50L - 1Cr': [50 * L, 1 * CR],
      '1Cr - 2Cr': [1 * CR, 2 * CR],
      '2Cr - 3Cr': [2 * CR, 3 * CR],
      'Above 3Cr': [3 * CR + 1, Number.MAX_SAFE_INTEGER],
    }
    const [minP, maxP] = ranges[rangeLabel] || [0, Number.MAX_SAFE_INTEGER]
    return price >= minP && price <= maxP
  }
  
  const withinAreaRange = (property, areaLabel) => {
    if (!areaLabel || areaLabel === 'All') return true
    const area = getArea(property)
    const map = {
      '500 - 1000': [500, 1000],
      '1000 - 1500': [1000, 1500],
      '1500 - 2000': [1500, 2000],
      '2000 - 2500': [2000, 2500],
      '2500+': [2500, Number.MAX_SAFE_INTEGER]
    }
    const [minA, maxA] = map[areaLabel] || [0, Number.MAX_SAFE_INTEGER]
    return area >= minA && area <= maxA
  }
  
  const filterProperties = useCallback((list) => {
    if (!Array.isArray(list)) return []
    return list.filter(p =>
      matchesAnyType(p, selectedPropertyTypes) &&
      withinPriceRange(p, selectedPriceRange) &&
      withinAreaRange(p, selectedArea)
    )
  }, [selectedArea, selectedPriceRange, selectedPropertyTypes])

  const toFiniteNumber = (value) => {
    if (value === null || value === undefined) return null
    const num = Number(value)
    return Number.isFinite(num) ? num : null
  }

  const sanitizeLabelText = (text) => {
    if (!text) return ''
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  const formatPriceLabel = (price, currency = '₹') => {
    const amount = Number(price)
    if (!Number.isFinite(amount) || amount <= 0) {
      return `${currency}—`
    }
    const crore = 10000000
    const lakh = 100000
    if (amount >= crore) {
      return `${currency}${(amount / crore).toFixed(1)}Cr`
    }
    if (amount >= lakh) {
      return `${currency}${(amount / lakh).toFixed(1)}L`
    }
    return `${currency}${Math.round(amount).toLocaleString('en-IN')}`
  }

  const encodeSvgToDataUri = (svg) => {
    try {
      if (typeof window !== 'undefined' && typeof window.btoa === 'function') {
        return `data:image/svg+xml;base64,${window.btoa(unescape(encodeURIComponent(svg)))}`
      }
    } catch (err) {
      console.warn('SVG encode fallback engaged:', err)
    }
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  }

  const createPriceMarkerIcon = (priceLabel, displayLabel = '', options = {}) => {
    if (typeof window === 'undefined') return null
    const { labelKind = 'none', zoom = 12 } = options
    
    // Match Mappls native label growth using zoom stops with linear interpolation (more pronounced)
    const zoomStopScale = (z) => {
      const stops = [
        [10, 0.95],
        [12, 1.15],
        [14, 1.60],
        [16, 2.20],
        [18, 3.00],
        [20, 4.00],
      ]
      for (let i = 0; i < stops.length - 1; i++) {
        const [z0, s0] = stops[i]
        const [z1, s1] = stops[i + 1]
        if (z <= z1) {
          const t = (z - z0) / Math.max(1, (z1 - z0))
          return s0 + (s1 - s0) * Math.max(0, Math.min(1, t))
        }
      }
      return stops[stops.length - 1][1]
    }
    const zoomScaleFactor = zoomStopScale(zoom)

    const baseText = (displayLabel || '').trim()
    const maxChars = 14
    const trimmed = baseText.length > maxChars
      ? `${baseText.slice(0, maxChars - 1)}…`
      : baseText
    // Always sanitize the text; previous logic returned empty for non-trimmed values
    const primaryText = sanitizeLabelText(trimmed)
    const hasLabel = labelKind !== 'none' && primaryText.length > 0

    // Zillow-like white pill styling
    const labelFill = '#ffffff'
    const labelStroke = '#d1d5db'
    const textColor = '#111827'

    // Apply zoom scaling to base label size
    const labelScale = hasLabel ? zoomScaleFactor : 1

    // Compute sizes to fit text with padding (no overflow) based on scale
    const baseFontPx = 12
    const fontSize = hasLabel ? Math.round(baseFontPx * zoomScaleFactor) : 0
    const padY = hasLabel ? Math.max(3, Math.round(3.5 * zoomScaleFactor)) : 0
    const padX = hasLabel ? Math.max(6, Math.round(8 * zoomScaleFactor)) : 0
    const charW = hasLabel ? fontSize * 0.62 : 0
    const lineH = hasLabel ? Math.round(fontSize * 1.15) : 0
    const labelHeight = hasLabel ? lineH + padY * 2 : 0
    const labelWidth = hasLabel ? Math.round(padX * 2 + charW * primaryText.length) : 0

    // Enforce minimum dimensions to prevent fallback to default brown pins
    const totalWidth = Math.max(20, labelWidth)
    const totalHeight = Math.max(16, labelHeight)

    const svgParts = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${totalWidth}" height="${totalHeight}" viewBox="0 0 ${totalWidth} ${totalHeight}">`,
      `  <g fill="none" stroke="none">`
    ]

    if (hasLabel) {
      const labelX = 0
      const labelY = 0
      const textX = totalWidth / 2
      const textY = totalHeight / 2 // Center text vertically
      
      // Border radius for pill
      const borderRadius = Math.round(Math.max(10, labelHeight * 0.45))
      
      // Better contrast text stroke - proportional to font size
      const strokeOpacity = 0.0
      const strokeWidth = 0

      svgParts.push(
        `    <rect x="${labelX}" y="${labelY}" width="${totalWidth}" height="${totalHeight}" rx="${borderRadius}" fill="${labelFill}" stroke="${labelStroke}" stroke-width="1"/>`,
        `    <text x="${textX}" y="${textY}" text-anchor="middle" dominant-baseline="central" font-family="'Inter', 'Segoe UI', sans-serif" font-size="${fontSize}" font-weight="700" fill="${textColor}">${primaryText}</text>`
      )
    }

    svgParts.push('  </g>', '</svg>')

    const svg = svgParts.join('\n')
    const iconUrl = encodeSvgToDataUri(svg)
    return {
      iconUrl,
      iconSize: [totalWidth, totalHeight],
      anchor: [Math.round(totalWidth / 2), Math.round(totalHeight / 2)]
    }
  }

  const resolvePropertyCoordinates = (property) => {
    if (!property || typeof property !== 'object') return null

    const lat = toFiniteNumber(property.latitude ?? property.lat)
    const lng = toFiniteNumber(property.longitude ?? property.lon)
    if (lat !== null && lng !== null) {
      return { lat, lng }
    }

    const nestedCoords = property.location?.coordinates || property.location?.coord || property.location?.center
    if (nestedCoords && typeof nestedCoords === 'object') {
      const nestedLat = toFiniteNumber(nestedCoords.lat ?? nestedCoords.latitude ?? nestedCoords[0])
      const nestedLng = toFiniteNumber(nestedCoords.lon ?? nestedCoords.lng ?? nestedCoords.longitude ?? nestedCoords[1])
      if (nestedLat !== null && nestedLng !== null) {
        return { lat: nestedLat, lng: nestedLng }
      }
    }

    const locationStr = property.location || property.centroid || property.center
    if (typeof locationStr === 'string' && locationStr.includes(',')) {
      const [latStr, lngStr] = locationStr.split(',').map(part => part.trim())
      const parsedLat = toFiniteNumber(latStr)
      const parsedLng = toFiniteNumber(lngStr)
      if (parsedLat !== null && parsedLng !== null) {
        return { lat: parsedLat, lng: parsedLng }
      }
    }

    if (Array.isArray(property.location) && property.location.length >= 2) {
      const parsedLat = toFiniteNumber(property.location[0])
      const parsedLng = toFiniteNumber(property.location[1])
      if (parsedLat !== null && parsedLng !== null) {
        return { lat: parsedLat, lng: parsedLng }
      }
    }

    return null
  }
  
  // Enhanced cluster icon with tiered colors and shadow effects
  const createClusterIcon = (count, options = {}) => {
    // Enhanced cluster sizing based on count (reduced)
    const baseSize = 26
    const countDigits = String(count).length
    const sizeBoost = Math.min(18, countDigits * 5)
    const size = baseSize + sizeBoost
    const r = Math.round(size / 2)
    
    // Tiered colors based on cluster size for visual hierarchy
    const getClusterColor = (n) => {
      if (n >= 100) return { fill: '#dc2626', stroke: '#991b1b', ring: '#fca5a5' }
      if (n >= 50) return { fill: '#ea580c', stroke: '#c2410c', ring: '#fdba74' }
      if (n >= 20) return { fill: '#f59e0b', stroke: '#d97706', ring: '#fcd34d' }
      if (n >= 10) return { fill: '#0ea5e9', stroke: '#0369a1', ring: '#7dd3fc' }
      return { fill: '#06b6d4', stroke: '#0e7490', ring: '#67e8f9' }
    }
    const { fill, stroke, ring } = getClusterColor(count)
    const text = '#ffffff'
    
    // Enhanced SVG with ring effect and drop shadow
    const svg = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`,
      `  <defs>`,
      `    <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">`,
      `      <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>`,
      `      <feOffset dx="0" dy="2" result="offsetblur"/>`,
      `      <feComponentTransfer><feFuncA type="linear" slope="0.3"/></feComponentTransfer>`,
      `      <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>`,
      `    </filter>`,
      `  </defs>`,
      `  <circle cx="${r}" cy="${r}" r="${r - 1}" fill="${ring}" opacity="0.3"/>`,
      `  <circle cx="${r}" cy="${r}" r="${r - 4}" fill="${fill}" stroke="${stroke}" stroke-width="2.5" filter="url(#shadow)"/>`,
      `  <text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" font-family="'Inter','Segoe UI',sans-serif" font-size="${Math.max(10, Math.round(r * 0.60))}" font-weight="700" fill="${text}">${count}</text>`,
      `</svg>`
    ].join('\n')
    const iconUrl = encodeSvgToDataUri(svg)
    return { iconUrl, iconSize: [size, size], anchor: [r, r] }
  }

  // Adaptive clustering bucket by zoom level for smoother transitions
  const getClusterBucketSize = (zoom) => {
    if (zoom <= 8) return 0.12    // ~12+ km
    if (zoom <= 9) return 0.08    // ~8-10 km
    if (zoom <= 10) return 0.05   // ~5-6 km
    if (zoom <= 11) return 0.03   // ~3 km
    if (zoom <= 12) return 0.015  // ~1.5 km
    if (zoom <= 13) return 0.008  // ~800 m
    return 0.004                   // ~400 m
  }

  // Group properties into clusters using a simple lat/lng bucketing strategy
  const buildClusters = (list, zoom) => {
    const bucket = getClusterBucketSize(zoom)
    const map = new Map()
    for (const p of list) {
      const coords = resolvePropertyCoordinates(p)
      if (!coords) continue
      const key = `${Math.floor(coords.lat / bucket)}:${Math.floor(coords.lng / bucket)}`
      if (!map.has(key)) {
        map.set(key, { items: [], latSum: 0, lngSum: 0, minLat: coords.lat, maxLat: coords.lat, minLng: coords.lng, maxLng: coords.lng })
      }
      const g = map.get(key)
      g.items.push(p)
      g.latSum += coords.lat
      g.lngSum += coords.lng
      g.minLat = Math.min(g.minLat, coords.lat)
      g.maxLat = Math.max(g.maxLat, coords.lat)
      g.minLng = Math.min(g.minLng, coords.lng)
      g.maxLng = Math.max(g.maxLng, coords.lng)
    }
    return Array.from(map.values()).map(g => ({
      count: g.items.length,
      items: g.items,
      center: { lat: g.latSum / g.items.length, lng: g.lngSum / g.items.length },
      bbox: [[g.minLat, g.minLng], [g.maxLat, g.maxLng]]
    }))
  }
  
  // Store displayPropertiesOnMap in a ref to avoid referencing it before declaration
  const displayPropertiesOnMapRef = useRef(null)
  
  const refreshPropertyMarkers = useCallback(() => {
    if (!layers.properties) return
    if (!properties || properties.length === 0) return
    const filtered = filterProperties(properties)
    
    // Clear current markers first
    markersRef.current.forEach(m => safeRemove(m))
    markersRef.current = []
    
    // Small timeout to ensure clean rendering
    setTimeout(() => {
      const fn = displayPropertiesOnMapRef.current || displayPropertiesOnMap
      try {
        fn && fn(filtered)
      } catch (e) {
        console.error('refreshPropertyMarkers render error:', e)
      }
    }, 20)
  }, [filterProperties, layers.properties, properties])
  
  useEffect(() => {
    refreshPropertyMarkers()
  }, [refreshPropertyMarkers, mapZoom])
  
  // Store references to map objects
  const markersRef = useRef([])
  const polygonsRef = useRef([])
  const polylinesRef = useRef([])
  const overlaysRef = useRef([])
  const shapeObjectsRef = useRef(new Map()) // Map of shape ID to Mappls object
  const enhancedDrawingRef = useRef(null) // Enhanced drawing system
  const activeClickHandlerRef = useRef(null)
  const zoomRefreshTimeoutRef = useRef(null)

  // Backend URL from env
  const backendURL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

  // Initialize map
  useEffect(() => {
    const initializeMap = async () => {
      console.log('Initializing interactive map...')
      
      // Mappls-only
      initializeMapplsMap()
    }
    
    initializeMap()
    
    return () => {
      if (mapInstanceRef.current) {
        cleanupMap()
      }
    }
  }, [mapProvider])

  // Initialize Mappls Map
  const initializeMapplsMap = () => {
    const mapplsApiKey =
      import.meta.env.VITE_MAPPLS_API_KEY ||
      import.meta.env.VITE_MAPPLS_STATIC_KEY ||
      import.meta.env.VITE_MAPPLE_STATIC_KEY ||
      ''
    
    console.log('Initializing Mappls map with key:', mapplsApiKey ? 'Found' : 'Missing')
    
    if (!mapplsApiKey) {
      setError('Mappls key missing. Set one of: VITE_MAPPLS_API_KEY, VITE_MAPPLS_STATIC_KEY, or VITE_MAPPLE_STATIC_KEY')
      setIsLoading(false)
      return
    }

    // Ensure container has ID
    if (mapContainerRef.current && !mapContainerRef.current.id) {
      mapContainerRef.current.id = 'mappls-map-container'
    }

    // Check if script already exists
    const existingScript = document.querySelector(`script[src*="mappls.com"]`)
    if (existingScript) {
      console.log('Mappls script already loaded, initializing map...')
      if (window.mappls) {
        initMapWithMappls()
      } else {
        existingScript.addEventListener('load', initMapWithMappls)
      }
      return
    }

    const script = document.createElement('script')
    script.src = `https://apis.mappls.com/advancedmaps/api/${mapplsApiKey}/map_sdk?layer=vector&v=3.0`
    script.async = true
    
    script.onload = () => {
      console.log('Mappls SDK script loaded')
      if (window.mappls) {
        initMapWithMappls()
      } else {
        console.error('Mappls SDK loaded but window.mappls not available')
        setError('Mappls SDK loaded incorrectly')
        setIsLoading(false)
      }
    }
    
    script.onerror = (e) => {
      console.error('Failed to load Mappls SDK:', e)
      setError('Failed to load Mappls SDK. Check API key and network connection.')
      setIsLoading(false)
    }
    
    document.head.appendChild(script)
  }

  const initMapWithMappls = () => {
    if (!window.mappls || !mapContainerRef.current) {
      console.error('Mappls or container not ready')
      return
    }

    try {
      const mappls = window.mappls
      
      const mapOptions = {
        center: {lat: mapCenter[0], lng: mapCenter[1]},
        zoom: mapZoom,
        zoomControl: false,
        rotateControl: true,
        scaleControl: true,
        fullscreenControl: true
      }
      
      console.log('Creating Mappls map instance with center:', {lat: mapCenter[0], lng: mapCenter[1]}, '(expected Bangalore: {lat: 12.9716, lng: 77.5946})')
      mapInstanceRef.current = new mappls.Map(mapContainerRef.current.id || mapContainerRef.current, mapOptions)
      
      mapInstanceRef.current.on('load', () => {
        console.log('✅ Mappls map initialized successfully')
        setIsLoading(false)
        
        // Setup drawing tools
        setTimeout(() => {
          setupDrawingManager()
          if (enhancedDrawingRef.current) {
            enhancedDrawingRef.current.initialize(mapInstanceRef.current)
          }
          
          // Load saved shapes after a short delay
          setTimeout(() => {
            loadSavedShapes()
          }, 500)
          
          // Load properties if layer is enabled
          if (layers.properties) {
            loadProperties()
          }
        }, 1000)
        
        // Aggressively disable ALL Mappls popups and controls
        setTimeout(() => {
          try {
            // Disable attribution
            const attributionControl = document.querySelector('.mappls-ctrl-attrib')
            if (attributionControl) {
              attributionControl.style.display = 'none'
              attributionControl.remove()
            }
            // Disable logo
            const mapplsLogo = document.querySelector('.mappls-ctrl-logo')
            if (mapplsLogo) {
              mapplsLogo.style.display = 'none'
              mapplsLogo.remove()
            }
            // Remove all anchor tags linking to Mappls
            document.querySelectorAll('a[href*="mappls"], a[href*="mapmyindia"]').forEach(el => {
              el.style.display = 'none'
              el.remove()
            })
            // Disable all popups
            const style = document.createElement('style')
            style.textContent = `
              .mappls-popup, .mapboxgl-popup, .leaflet-popup,
              .mappls-ctrl-attrib, .mappls-ctrl-logo,
              a[href*="mappls"], a[href*="mapmyindia"] {
                display: none !important;
                pointer-events: none !important;
              }
            `
            document.head.appendChild(style)
            // Hide POI layers (brown default markers) from base style
            try {
              const styleObj = mapInstanceRef.current.getStyle && mapInstanceRef.current.getStyle()
              const layers = (styleObj && styleObj.layers) || []
              layers.forEach((layer) => {
                const id = String(layer.id || '')
                if (/poi|poi-label|poi-icon|place-poi|poi-/.test(id)) {
                  try { mapInstanceRef.current.setLayoutProperty(id, 'visibility', 'none') } catch (_) {}
                }
              })
            } catch (e2) {
              console.log('Could not hide POI layers:', e2)
            }
          } catch (e) {
            console.log('Popup disable error:', e)
          }
        }, 1000)
      
      try {
        mapInstanceRef.current.on('styledata', () => {
          try {
            const styleObj = mapInstanceRef.current.getStyle && mapInstanceRef.current.getStyle()
            const layers = (styleObj && styleObj.layers) || []
            layers.forEach((layer) => {
              const id = String(layer.id || '')
              if (/poi|poi-label|poi-icon|place-poi|poi-/.test(id)) {
                try { mapInstanceRef.current.setLayoutProperty(id, 'visibility', 'none') } catch (_) {}
              }
            })
          } catch (_) {}
        })
      } catch (_) {}
        
        setIsLoading(false)
        setupMappls()
      })

      mapInstanceRef.current.on('error', (e) => {
        console.error('Mappls map error:', e)
        const errorMsg = e?.error?.message || e?.message || 'Map initialization error'
        // Don't show transient errors, only critical ones
        if (errorMsg.includes('401') || errorMsg.includes('403') || errorMsg.includes('key')) {
          setError(`API Key error: ${errorMsg}`)
          setIsLoading(false)
        } else {
          console.warn('Non-critical map error:', errorMsg)
          // Clear error after brief display for non-critical errors
          setError(errorMsg)
          setTimeout(() => setError(null), 3000)
        }
      })
      
      // Update markers on zoom change to ensure proper scaling
      // Use both zoomend and zoom events for smoother updates
      mapInstanceRef.current.on('zoomend', () => {
        const newZoom = mapInstanceRef.current.getZoom();
        console.log(`📏 Map zoom changed (end): ${newZoom}`);
        setMapZoom(newZoom);
        
        // Immediate refresh with no delay for better responsiveness
        if (mapInstanceRef.current && properties.length > 0) {
          console.log('Refreshing property markers after zoom');
          refreshPropertyMarkers();
        }
      });
      
      // Also listen to zoom events (during zooming) to update marker sizes dynamically
      mapInstanceRef.current.on('zoom', () => {
        if (!mapInstanceRef.current) return
        const z = mapInstanceRef.current.getZoom()
        setMapZoom(z)
        // Debounce refresh to ~8-10 fps; only update when not clustering
        const clusterThreshold = 11
        clearTimeout(zoomRefreshTimeoutRef.current)
        zoomRefreshTimeoutRef.current = setTimeout(() => {
          try {
            if (z >= clusterThreshold && properties.length > 0) {
              refreshPropertyMarkers()
            }
          } catch (_) {}
        }, 100)
      })
    } catch (error) {
      console.error('Error creating Mappls map:', error)
      setError(`Map creation failed: ${error.message}`)
      setIsLoading(false)
    }
  }

  // Mapbox removed: initializeMapboxMap disabled

  // Setup drawing tools for Mappls
  const setupMappls = () => {
    if (!window.mappls || !mapInstanceRef.current) return
    
    const mappls = window.mappls
    
    // Initialize enhanced drawing system
    enhancedDrawingRef.current = EnhancedDrawingSystem.initializeDrawing(mapInstanceRef.current, mappls)
    
    // Custom drawing manager
    drawingManagerRef.current = {
      startPolygon: () => startPolygonDrawing(mappls),
      startPolyline: () => startPolylineDrawing(mappls),
      startCircle: () => startCircleDrawing(mappls),
      startRectangle: () => startRectangleDrawing(mappls),
      startMarker: () => startMarkerDrawing(mappls),
      clearAll: () => clearAllShapes(),
      // Enhanced methods
      drawBuffer: (location, radius, context) => enhancedDrawingRef.current.drawBufferZone(mapInstanceRef.current, mappls, { location, radius, ...context }),
      startPropertyBoundary: () => enhancedDrawingRef.current.startPropertyBoundary(mapInstanceRef.current, mappls, {}),
      startCatchmentArea: (amenityType) => enhancedDrawingRef.current.startCatchmentArea(mapInstanceRef.current, mappls, { amenityType }),
      compareZones: (zones) => enhancedDrawingRef.current.compareZones(mapInstanceRef.current, mappls, zones)
    }
    
    // Load saved shapes from localStorage
    setTimeout(() => {
      loadSavedShapes()
      loadEnhancedShapes()
    }, 500)
  }

  // Mapbox removed: setupMapboxDrawingTools disabled

  // Helper function to safely remove markers/shapes (works with both Mappls and Mapbox)
  const safeRemove = (obj) => {
    if (!obj) return
    try {
      if (typeof obj.remove === 'function') {
        obj.remove()
      } else if (typeof obj.setMap === 'function') {
        obj.setMap(null)
      }
    } catch (e) {
      console.warn('Could not remove object:', e)
    }
  }

  // Handle Mapbox draw updates (safe no-op if draw not present)
  const updateDrawnFeatures = () => {
    try {
      const draw = drawingManagerRef.current
      const data = draw && draw.getAll ? draw.getAll() : null
      if (data && data.features && data.features.length) {
        // Optionally, dispatch overlays or analyze polygon
        // console.log('Draw features:', data)
      }
    } catch (_) {}
  }

  // Start polygon drawing (Mappls) - Enhanced with double-click and right-click
  const startPolygonDrawing = (mappls) => {
    if (!mapInstanceRef.current) return
    setDrawingMode('polygon')
    setIsDrawing(true)
    drawingStateRef.current = { points: [], tempMarkers: [], tempShape: null }
    
    console.log('🎨 Polygon drawing started - Click to add points, Right-click or Double-click to finish')
    
    const clickHandler = (e) => {
      console.log('🖱️ Click detected at:', e)
      
      // Handle different event structures from Mappls API
      let lat, lng
      if (e.latlng) {
        lat = e.latlng.lat
        lng = e.latlng.lng
      } else if (e.lngLat) {
        lat = e.lngLat.lat
        lng = e.lngLat.lng
      } else if (e.position) {
        lat = e.position.lat
        lng = e.position.lng
      } else if (e.center) {
        lat = e.center.lat
        lng = e.center.lng
      } else {
        console.error('Unable to get coordinates from event:', e)
        return
      }
      
      const point = [lat, lng]
      drawingStateRef.current.points.push(point)
      
      // Create visible marker at click point
      try {
        const marker = new window.mappls.Marker({
          map: mapInstanceRef.current,
          position: {lat: lat, lng: lng},
          fitbounds: false,
          icon: window.mappls.Marker.prototype.createIcon({
            iconSize: [20, 20],
            iconUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTAiIGN5PSIxMCIgcj0iOCIgZmlsbD0iIzNiODJmNiIgc3Ryb2tlPSIjMjU2M2ViIiBzdHJva2Utd2lkdGg9IjIiLz4KPC9zdmc+'
          })
        })
        drawingStateRef.current.tempMarkers.push(marker)
        console.log(`✅ Added point ${drawingStateRef.current.points.length} at [${lat}, ${lng}]`)
      } catch (err) {
        console.error('Marker error:', err)
      }
      
      if (drawingStateRef.current.points.length >= 2) {
        if (drawingStateRef.current.tempShape) {
          safeRemove(drawingStateRef.current.tempShape)
        }
        
        try {
          // Mappls expects array of objects with lat/lng keys
          const formattedPoints = drawingStateRef.current.points.map(p => ({
            lat: p[0],
            lng: p[1]
          }))
          
          const polygon = new window.mappls.Polygon({
            map: mapInstanceRef.current,
            paths: formattedPoints,
            fillcolor: '#6366f1',  // lowercase 'c' per Mappls docs
            fillOpacity: 0.4,
            strokeColor: '#4f46e5',
            strokeOpacity: 0.9
          })
          drawingStateRef.current.tempShape = polygon
          console.log(`📐 Preview polygon updated (${drawingStateRef.current.points.length} points)`)
        } catch (err) {
          console.error('❌ Polygon preview error:', err, err.message)
        }
      }
    }
    
    const finishDrawing = () => {
      const points = drawingStateRef.current.points
      
      mapInstanceRef.current.off('click', clickHandler)
      mapInstanceRef.current.off('dblclick', finishDrawing)
      mapInstanceRef.current.off('rightclick', finishDrawing)
      
      drawingStateRef.current.tempMarkers.forEach(m => safeRemove(m))
      if (drawingStateRef.current.tempShape) {
        safeRemove(drawingStateRef.current.tempShape)
      }
      
      setDrawingMode(null)
      setIsDrawing(false)
      
      if (points.length >= 3) {
        const shapeId = `polygon-${Date.now()}`
        const shape = {
          id: shapeId,
          type: 'polygon',
          points,
          area: calculatePolygonArea(points),
          fillColor: '#6366f1',
          strokeColor: '#4f46e5',
          created: new Date().toISOString()
        }
        
        // Mappls expects array of objects with lat/lng keys
        const formattedPoints = points.map(p => ({
          lat: p[0],
          lng: p[1]
        }))
        
        const polygon = new window.mappls.Polygon({
          map: mapInstanceRef.current,
          paths: formattedPoints,
          fillcolor: shape.fillColor,  // lowercase 'c' per Mappls docs
          fillOpacity: 0.4,
          strokeColor: shape.strokeColor,
          strokeOpacity: 0.9,
          fitbounds: false
        })
        
        shapeObjectsRef.current.set(shapeId, polygon)
        polygonsRef.current.push(polygon)
        
        try {
          polygon.addListener('click', () => selectShape(shape))
        } catch (e) {
          console.log('Could not add click listener:', e)
        }
        
        setDrawnShapes(prev => {
          pushUndoSnapshot(prev)
          const updated = [...prev, shape]
          saveShapesToStorage(updated)
          return updated
        })
        
        console.log(`✅ POLYGON CREATED: ${points.length} points, Area: ${shape.area.toFixed(2)} sq km`)
      } else if (points.length > 0) {
        console.log(`⚠️ Need at least 3 points (you have ${points.length})`)
      }
      
      drawingStateRef.current = { points: [], tempMarkers: [], tempShape: null }
    }
    
    mapInstanceRef.current.on('click', clickHandler)
    mapInstanceRef.current.on('dblclick', finishDrawing)
    mapInstanceRef.current.on('rightclick', finishDrawing)
  }

  // Calculate polygon area
  const calculatePolygonArea = (points) => {
    // Simplified area calculation (would use proper geodesic calculation in production)
    let area = 0
    for (let i = 0; i < points.length; i++) {
      const j = (i + 1) % points.length
      area += points[i][1] * points[j][0]
      area -= points[j][1] * points[i][0]
    }
    return Math.abs(area / 2) * 111 * 111 // Convert to approximate sq km
  }

  // Analyze drawn polygon
  const analyzePolygon = async (shape) => {
    try {
      const response = await fetch(`${backendURL}/api/agent/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          polygon: shape.points,
          area_sqkm: shape.area,
          analysis_type: 'zone_analysis'
        })
      })
      
      const data = await response.json()
      
      window.dispatchEvent(new CustomEvent('polygon-analysis', {
        detail: { shape, analysis: data }
      }))
    } catch (error) {
      console.error('Polygon analysis failed:', error)
    }
  }

  // Start polyline drawing - NEW TOOL for distance measurement
  const startPolylineDrawing = (mappls) => {
    if (!mapInstanceRef.current) return
    setDrawingMode('polyline')
    setIsDrawing(true)
    drawingStateRef.current = { points: [], tempMarkers: [], tempShape: null }
    
    console.log('📏 Polyline drawing started - Click to add points, Right-click or Double-click to finish')
    
    const clickHandler = (e) => {
      // Handle different event structures from Mappls API
      let lat, lng
      if (e.latlng) {
        lat = e.latlng.lat
        lng = e.latlng.lng
      } else if (e.lngLat) {
        lat = e.lngLat.lat
        lng = e.lngLat.lng
      } else if (e.position) {
        lat = e.position.lat
        lng = e.position.lng
      } else if (e.center) {
        lat = e.center.lat
        lng = e.center.lng
      } else {
        console.error('Unable to get coordinates from event:', e)
        return
      }
      
      const point = [lat, lng]
      drawingStateRef.current.points.push(point)
      
      try {
        const marker = new mappls.Marker({
          map: mapInstanceRef.current,
          position: {lat: lat, lng: lng},
          icon_size: 8
        })
        drawingStateRef.current.tempMarkers.push(marker)
        console.log(`✓ Point ${drawingStateRef.current.points.length} added`)
      } catch (err) {
        console.error('Marker error:', err)
      }
      
      if (drawingStateRef.current.points.length >= 2) {
        if (drawingStateRef.current.tempShape) {
          safeRemove(drawingStateRef.current.tempShape)
        }
        
        try {
          const polyline = new mappls.Polyline({
            map: mapInstanceRef.current,
            path: drawingStateRef.current.points,
            strokeColor: '#10b981',
            strokeWeight: 3
          })
          drawingStateRef.current.tempShape = polyline
        } catch (err) {
          console.error('Polyline error:', err)
        }
      }
    }
    
    const finishPolyline = () => {
      const points = drawingStateRef.current.points
      
      mapInstanceRef.current.off('click', clickHandler)
      mapInstanceRef.current.off('dblclick', finishPolyline)
      mapInstanceRef.current.off('rightclick', finishPolyline)
      
      drawingStateRef.current.tempMarkers.forEach(m => safeRemove(m))
      if (drawingStateRef.current.tempShape) {
        safeRemove(drawingStateRef.current.tempShape)
      }
      
      setDrawingMode(null)
      setIsDrawing(false)
      
      if (points.length >= 2) {
        const shapeId = `polyline-${Date.now()}`
        const distance = calculatePolylineDistance(points)
        const shape = {
          id: shapeId,
          type: 'polyline',
          points,
          distance,
          strokeColor: '#10b981',
          created: new Date().toISOString()
        }
        
        const polyline = new mappls.Polyline({
          map: mapInstanceRef.current,
          path: points,
          strokeColor: shape.strokeColor,
          strokeWeight: 3
        })
        
        shapeObjectsRef.current.set(shapeId, polyline)
        polylinesRef.current.push(polyline)
        polyline.addListener('click', () => selectShape(shape))
        
        setDrawnShapes(prev => {
          const updated = [...prev, shape]
          saveShapesToStorage(updated)
          return updated
        })
        
        console.log(`✅ POLYLINE CREATED: ${points.length} points, Distance: ${distance.toFixed(2)} km`)
      } else if (points.length > 0) {
        console.log(`⚠️ Need at least 2 points (you have ${points.length})`)
      }
      
      drawingStateRef.current = { points: [], tempMarkers: [], tempShape: null }
    }
    
    mapInstanceRef.current.on('click', clickHandler)
    mapInstanceRef.current.on('dblclick', finishPolyline)
    mapInstanceRef.current.on('rightclick', finishPolyline)
  }

  // Calculate polyline distance using Haversine formula
  const calculatePolylineDistance = (points) => {
    let distance = 0
    for (let i = 0; i < points.length - 1; i++) {
      const [lat1, lng1] = points[i]
      const [lat2, lng2] = points[i + 1]
      const R = 6371 // Earth radius in km
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLng = (lng2 - lng1) * Math.PI / 180
      const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLng / 2) * Math.sin(dLng / 2)
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
      distance += R * c
    }
    return distance
  }

  // Smooth map center helper function with animation and zoom arc effect
  const smoothCenterMap = (lat, lng, zoom = 15) => {
    if (!mapInstanceRef.current) return
    
    // Show geocoding indicator during animation
    setIsGeocoding(true)
    
    if (window.mappls) {
      // Mappls: Create zoom arc effect - zoom out, pan, zoom in
      const currentZoom = mapInstanceRef.current.getZoom?.() || 12
      const minZoom = Math.max(10, currentZoom - 2) // Zoom out by 2 levels
      
      // Step 1: Zoom out
      if (mapInstanceRef.current.setZoom) {
        mapInstanceRef.current.setZoom(minZoom)
      }
      
      // Step 2: Pan to new location (after 300ms)
      setTimeout(() => {
        if (mapInstanceRef.current.panTo) {
          mapInstanceRef.current.panTo({lat: lat, lng: lng})
        } else {
          mapInstanceRef.current.setCenter({lat: lat, lng: lng})
        }
      }, 300)
      
      // Step 3: Zoom back in (after 800ms)
      setTimeout(() => {
        if (mapInstanceRef.current.setZoom) {
          mapInstanceRef.current.setZoom(zoom)
        }
        setIsGeocoding(false)
      }, 1200)
      
      console.log(`Smoothly navigating Mappls map to {lat: ${lat}, lng: ${lng}} with arc effect`)
    }
  }

  // Ensure shapes are visible in current view mode (2D/3D)
  useEffect(() => {
    if (mapInstanceRef.current && drawnShapes.length > 0 && mapProvider === 'mappls') {
      // Small delay to ensure map is ready
      const timer = setTimeout(() => {
        console.log(`📍 Ensuring ${drawnShapes.length} shapes are visible in ${is3DView ? '3D' : '2D'} view`)
        // Shapes should already be drawn, but this ensures they persist
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [drawnShapes.length, is3DView, mapProvider])

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (showDrawDropdown || showLayersDropdown || showEnhancedTools || showPropertyTypeDropdown || showPriceRangeDropdown || showAreaDropdown) {
        const target = e.target
        const isDropdownClick = target.closest('.dropdown-container')
        if (!isDropdownClick) {
          setShowDrawDropdown(false)
          setShowLayersDropdown(false)
          setShowEnhancedTools(false)
          setShowPropertyTypeDropdown(false)
          setShowPriceRangeDropdown(false)
          setShowAreaDropdown(false)
        }
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showDrawDropdown, showLayersDropdown, showEnhancedTools, showPropertyTypeDropdown, showPriceRangeDropdown, showAreaDropdown])

  // Handle map commands from AI agent
  useEffect(() => {
    const handleMapCommand = async (event) => {
      const command = event.detail
      console.log('Map command received:', command)
      
      try {
        switch (command.action) {
          case 'center':
            // Use coordinates directly if available, otherwise geocode
            if (command.coordinates && command.coordinates.length === 2) {
              const [lat, lng] = command.coordinates
              smoothCenterMap(lat, lng, 15)
            } else {
              await geocodeAndCenter(command.location)
            }
            break

          case 'showProperties': {
            const mappedProperties = Array.isArray(command.properties)
              ? command.properties
                  .map((item) => {
                    const lat = Number(item.latitude ?? item.lat)
                    const lng = Number(item.longitude ?? item.lng)
                    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
                    return {
                      name: item.name || item.zone_name || 'Property',
                      latitude: lat,
                      longitude: lng,
                      price: Number(item.price) || null,
                      price_label: item.price_label,
                      highlight: item.highlight,
                      builder: item.builder,
                      configuration: item.configuration,
                      investment_grade: item.investment_grade
                    }
                  })
                  .filter(Boolean)
              : []

            if (mappedProperties.length > 0) {
              setShowProperties(true)
              setProperties(mappedProperties)
              displayPropertiesOnMap(mappedProperties)

              const center = Array.isArray(command.center) && command.center.length === 2
                ? command.center
                : [mappedProperties[0].latitude, mappedProperties[0].longitude]
              const zoomLevel = Number(command.zoom) || mapInstanceRef.current?.getZoom?.() || 13

              if (center && Number.isFinite(center[0]) && Number.isFinite(center[1])) {
                smoothCenterMap(center[0], center[1], zoomLevel)
              }
            } else {
              let center = null
              if (Array.isArray(command.center) && command.center.length === 2) {
                center = command.center
              } else if (Array.isArray(command.coordinates) && command.coordinates.length === 2) {
                center = command.coordinates
              }

              if (!center && command.location) {
                try {
                  const resp = await fetch(`${backendURL}/api/maps/geocode?address=${encodeURIComponent(command.location)}`)
                  const gj = await resp.json()
                  if (Array.isArray(gj.coordinates) && gj.coordinates.length === 2) {
                    center = gj.coordinates
                  }
                } catch (_) {}
              }

              if (center) {
                try {
                  const currentZoom = mapInstanceRef.current?.getZoom?.() || 13
                  const propsResp = await fetch(`${backendURL}/api/properties?limit=0&zoom=${encodeURIComponent(currentZoom)}`)
                  const propsData = await propsResp.json()
                  const list = Array.isArray(propsData.properties) ? propsData.properties : []

                  const toNum = (v) => (Number.isFinite(Number(v)) ? Number(v) : null)
                  const [clat, clng] = [Number(center[0]), Number(center[1])]
                  const distKm = (aLat, aLng, bLat, bLng) => {
                    const R = 6371
                    const dLat = (bLat - aLat) * Math.PI / 180
                    const dLng = (bLng - aLng) * Math.PI / 180
                    const s1 = Math.sin(dLat/2)
                    const s2 = Math.sin(dLng/2)
                    const aa = s1*s1 + Math.cos(aLat*Math.PI/180) * Math.cos(bLat*Math.PI/180) * s2*s2
                    const c = 2 * Math.atan2(Math.sqrt(aa), Math.sqrt(1-aa))
                    return R * c
                  }

                  const filtered = list
                    .map((p) => {
                      let lat = toNum(p.latitude)
                      let lng = toNum(p.longitude)
                      if ((lat === null || lng === null) && typeof p.location === 'string' && p.location.includes(',')) {
                        const parts = p.location.split(',').map(s => s.trim())
                        const la = toNum(parts[0])
                        const lo = toNum(parts[1])
                        if (la !== null && lo !== null) { lat = la; lng = lo }
                      }
                      if (lat === null || lng === null) return null
                      const d = distKm(clat, clng, lat, lng)
                      return { p, lat, lng, d }
                    })
                    .filter(Boolean)
                    .sort((a, b) => a.d - b.d)
                    .filter(x => x.d <= 5)
                    .slice(0, 300)
                    .map(x => ({
                      ...x.p,
                      latitude: x.lat,
                      longitude: x.lng
                    }))

                  if (filtered.length > 0) {
                    setShowProperties(true)
                    setProperties(filtered)
                    displayPropertiesOnMap(filtered)
                    const z = Number(command.zoom) || currentZoom || 13
                    smoothCenterMap(clat, clng, z)
                  } else {
                    const z = Number(command.zoom) || 13
                    smoothCenterMap(clat, clng, z)
                  }
                } catch (err) {
                  console.warn('showProperties fetch failed:', err)
                }
              }
            }
            break
          }

          case 'drawPolygon':
            if (drawingManagerRef.current) {
              setDrawingMode('polygon')
              drawingManagerRef.current.startPolygon()
            }
            break
          
          case 'drawCircle':
            if (drawingManagerRef.current) {
              setDrawingMode('circle')
              drawingManagerRef.current.startCircle?.()
            }
            break

          case 'drawRectangle':
            if (drawingManagerRef.current) {
              setDrawingMode('rectangle')
              drawingManagerRef.current.startRectangle?.()
            }
            break

          case 'startMarker':
            if (drawingManagerRef.current) {
              setDrawingMode('marker')
              drawingManagerRef.current.startMarker?.()
            }
            break

          case 'addMarker':
            await geocodeAndAddMarker(command.location)
            break
          
          case 'drawBuffer':
            // Use enhanced drawing system for buffers
            if (enhancedDrawingRef.current) {
              const result = await enhancedDrawingRef.current.drawBufferZone(
                mapInstanceRef.current, 
                window.mappls,
                {
                  location: command.location,
                  radius: command.radius || 2,
                  purpose: command.purpose || 'analysis'
                }
              )
              if (result.success) {
                console.log('✅ Buffer drawn:', result.message)
                // Center map on buffer
                if (result.shape && result.shape.center) {
                  smoothCenterMap(result.shape.center[0], result.shape.center[1], 13)
                }
              } else {
                console.error('Buffer failed:', result.error)
              }
            } else {
              // Fallback to old method
              await drawBuffer(command.location, command.radius)
            }
            break
            
          case 'drawPropertyBoundary':
            if (drawingManagerRef.current) {
              drawingManagerRef.current.startPropertyBoundary()
            }
            break
            
          case 'drawCatchmentArea':
            if (drawingManagerRef.current) {
              drawingManagerRef.current.startCatchmentArea(command.amenityType || 'general')
            }
            break
            
          case 'compareZones':
            if (drawingManagerRef.current && command.zones) {
              await drawingManagerRef.current.compareZones(command.zones)
            }
            break
          
          case 'addLayer':
            toggleLayer(command.layerType, true)
            break

          case 'setLayer':
            toggleLayer(command.layerType, !!command.visible)
            break

          case 'clearShapes':
            clearAllShapes()
            break
          
          case 'compareAreas':
            await compareMultipleAreas(command.areas)
            break
        }
      } catch (error) {
        console.error('Map command error:', error)
        setError(`Map command failed: ${error.message}`)
        setTimeout(() => setError(null), 3000)
      }
    }
    
    const handleAnalysisUpdate = (event) => {
      const analysis = event.detail
      
      if (analysis.top_properties) {
        const list = Array.isArray(analysis.top_properties) ? analysis.top_properties : []
        setProperties(list)
        displayPropertiesOnMap(filterProperties(list))
      }
      
      if (analysis.hotspots) {
        showHotspotHeatmap(analysis.hotspots)
      }
    }
    
    const handleOverlayUpdate = (event) => {
      const overlay = event.detail
      
      if (overlay.geojson) {
        addGeoJSONOverlay(overlay.geojson)
      }
      
      if (overlay.center) {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setCenter(overlay.center)
        }
      }
    }
    
    console.log('Setting up map event listeners...')
    window.addEventListener('valora-map-command', handleMapCommand)
    window.addEventListener('valora-analysis', handleAnalysisUpdate)
    window.addEventListener('update-map-overlay', handleOverlayUpdate)
    
    return () => {
      console.log('Cleaning up map event listeners...')
      window.removeEventListener('valora-map-command', handleMapCommand)
      window.removeEventListener('valora-analysis', handleAnalysisUpdate)
      window.removeEventListener('update-map-overlay', handleOverlayUpdate)
    }
  }, [backendURL, mapProvider]) // Add dependencies

  // Geocode location and center map
  const geocodeAndCenter = async (location) => {
    setIsGeocoding(true)
    try {
      console.log(`Geocoding location: ${location}`)
      const response = await fetch(`${backendURL}/api/maps/geocode?address=${encodeURIComponent(location)}`)
      const data = await response.json()
      
      console.log('Geocode response:', data)
      
      if (data.coordinates && data.coordinates.length === 2) {
        const [lat, lng] = data.coordinates
        
        if (mapInstanceRef.current) {
          // Use smooth animation
          smoothCenterMap(lat, lng, 15)
          
          // Show success message
          if (data.source === 'default') {
            setError(data.message || 'Showing approximate location')
            setTimeout(() => setError(null), 2000)
          }
        }
      } else {
        console.warn('Invalid coordinates received:', data)
        setError('Location not found')
        setTimeout(() => setError(null), 3000)
      }
    } catch (error) {
      console.error('Geocoding failed:', error)
      setError(`Could not find location: ${location}`)
      setTimeout(() => setError(null), 3000)
    } finally {
      setIsGeocoding(false)
    }
  }

  // Geocode and add marker
  const geocodeAndAddMarker = async (location) => {
    try {
      console.log(`Adding marker at: ${location}`)
      const response = await fetch(`${backendURL}/api/maps/geocode?address=${encodeURIComponent(location)}`)
      const data = await response.json()
      
      console.log('Marker geocode response:', data)
      
      if (data.coordinates && data.coordinates.length === 2) {
        const [lat, lng] = data.coordinates
        
        if (window.mappls && mapInstanceRef.current) {
          const pin = document.createElement('div')
          pin.style.cssText = 'display:inline-block; pointer-events:auto;'
          const size = 10
          pin.innerHTML = [
            `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`,
            `  <circle cx="${size/2}" cy="${size/2}" r="${(size/2)-1}" fill="#111827" stroke="#ffffff" stroke-width="2"/>`,
            `</svg>`
          ].join('')
          const marker = new window.mappls.Marker({
            map: mapInstanceRef.current,
            position: { lat: lat, lng: lng },
            fitbounds: true,
            element: pin
          })
          markersRef.current.push(marker)
          console.log(`Added custom pin at [${lat}, ${lng}]`)
        }
      }
    } catch (error) {
      console.error('Geocoding failed:', error)
      setError(`Could not add marker: ${location}`)
      setTimeout(() => setError(null), 3000)
    }
  }

  // Draw buffer zone
  const drawBuffer = async (location, radius) => {
    try {
      console.log(`Drawing buffer at ${location} with radius ${radius}km`)
      const response = await fetch(`${backendURL}/api/maps/geocode?address=${encodeURIComponent(location)}`)
      const data = await response.json()
      
      console.log('Buffer geocode response:', data)
      
      if (data.coordinates && data.coordinates.length === 2) {
        const [lat, lng] = data.coordinates
        
        if (window.mappls && mapInstanceRef.current) {
          const circle = new window.mappls.Circle({
            map: mapInstanceRef.current,
            center: {lat: lat, lng: lng},
            radius: radius * 1000, // Convert km to meters
            fillColor: '#3b82f6',
            fillOpacity: 0.2,
            strokeColor: '#1d4ed8',
            strokeOpacity: 0.8,
            strokeWeight: 2
          })
          overlaysRef.current.push(circle)
          console.log(`Drew Mappls buffer at [${lat}, ${lng}] with radius ${radius}km`)
          // Center on buffer with smooth animation
          smoothCenterMap(lat, lng, 13)
        }
      }
    } catch (error) {
      console.error('Buffer drawing failed:', error)
      setError(`Could not draw buffer: ${location}`)
      setTimeout(() => setError(null), 3000)
    }
  }

  // Calculate appropriate zoom level for radius
  const calculateZoomForRadius = (radiusKm) => {
    if (radiusKm <= 1) return 16
    if (radiusKm <= 5) return 14
    if (radiusKm <= 10) return 13
    if (radiusKm <= 20) return 12
    return 11
  }

  // Compare multiple areas
  const compareMultipleAreas = async (areas) => {
    const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444']
    
    for (let i = 0; i < areas.length; i++) {
      const area = areas[i]
      const color = colors[i % colors.length]
      
      // Draw a circle for each area
      await drawBuffer(area, 2) // 2km radius for comparison
    }
  }

  // Add property markers
  const addPropertyMarkers = (properties) => {
    if (!window.mappls || !mapInstanceRef.current) return

    // Clear existing property markers
    markersRef.current.forEach(m => safeRemove(m))
    markersRef.current = []

    const currentZoom = mapInstanceRef.current.getZoom()
    const showDetails = currentZoom > 14 // Show more details when zoomed in beyond level 14

    properties.forEach(property => {
      if (property.latitude && property.longitude) {
        try {
          // Create custom marker element with price
          const el = document.createElement('div')
          el.className = 'property-marker'

          const priceLabel = sanitizeLabelText(
            property.price_label || formatPriceLabel(property.price, '₹')
          )
          const detailLabel = showDetails
            ? sanitizeLabelText(
                property.configuration || property.name || property.builder || ''
              )
            : ''

          let content = `<div class="price-tag">${priceLabel}</div>`
          if (detailLabel) {
            content += `<div class="property-details">${detailLabel}</div>`
          }
          el.innerHTML = content

          const marker = new window.mappls.Marker({
            map: mapInstanceRef.current,
            position: { lat: property.latitude, lng: property.longitude },
            element: el
          });
          
          marker.addListener('click', () => {
            window.dispatchEvent(new CustomEvent('property-selected', { detail: property }))
          });
          
          markersRef.current.push(marker);
        } catch (err) {
          console.error('Failed to create property marker:', err);
        }
      }
    });
    
    console.log(`📍 Displayed ${markersRef.current.length} property markers at zoom ${currentZoom}`)
  }

  // Apply proper zoom-dependent icon scaling
  const displayPropertiesOnMap = useCallback((propertyList) => {
    if (!window.mappls || !mapInstanceRef.current) return

    markersRef.current.forEach(m => safeRemove(m))
    markersRef.current = []

    const currentZoom = mapInstanceRef.current.getZoom()
    console.log(`🔍 Rendering markers at zoom ${currentZoom}`)
    // Always show price chips at mid/high zoom; cluster when zoomed out
    const clusterThreshold = 11  // Zillow-like: cluster more when zoomed out
    const usingClusters = currentZoom < clusterThreshold

    if (usingClusters) {
      const clusters = buildClusters(propertyList, currentZoom)
      clusters.forEach(cluster => {
        const iconCfg = createClusterIcon(cluster.count)
        const markerOptions = {
          map: mapInstanceRef.current,
          position: cluster.center,
          fitbounds: false,
          icon_url: iconCfg.iconUrl,
          icon_size: iconCfg.iconSize,
          icon_anchor: iconCfg.anchor
        }
        const marker = new window.mappls.Marker(markerOptions)
        try {
          marker.addListener('click', () => {
            const z = Math.min(18, (mapInstanceRef.current.getZoom?.() || 10) + 2)
            if (mapInstanceRef.current.panTo) mapInstanceRef.current.panTo(cluster.center)
            if (mapInstanceRef.current.setZoom) mapInstanceRef.current.setZoom(z)
          })
        } catch (_) {}
        markersRef.current.push(marker)
      })
      console.log(`📍 Displayed ${markersRef.current.length} clusters at zoom ${currentZoom}`)
      return
    }

    const showPriceLabels = true

    propertyList.forEach(property => {
      const coords = resolvePropertyCoordinates(property)
      if (!coords) return

      try {
        const priceLabel = formatPriceLabel(property.price, property.currency)

        const zoomStopScale = (z) => {
          const stops = [[10,0.8],[12,1.0],[14,1.25],[16,1.6],[18,2.0],[20,2.4]]
          for (let i = 0; i < stops.length - 1; i++) {
            const [z0,s0] = stops[i]; const [z1,s1] = stops[i+1]
            if (z <= z1) { const t = (z - z0) / Math.max(1,(z1 - z0)); return s0 + (s1 - s0) * Math.max(0,Math.min(1,t)) }
          }
          return stops[stops.length-1][1]
        }
        const scale = Math.min(2.4, Math.max(0.85, zoomStopScale(currentZoom)))

        const baseFont = 11
        const padY = 3
        const padX = 8
        const textW = Math.ceil(priceLabel.length * baseFont * 0.62)
        const width = textW + padX * 2
        const height = Math.round(baseFont * 1.15 + padY * 2)
        const rx = Math.round(height * 0.45)

        const wrapper = document.createElement('div')
        wrapper.style.cssText = `display:inline-block; transform-origin:center; transform:scale(${scale}); will-change:transform; pointer-events:auto;`
        wrapper.innerHTML = [
          `<svg xmlns='http://www.w3.org/2000/svg' width='${width}' height='${height}' viewBox='0 0 ${width} ${height}'>`,
          `  <rect x='0' y='0' width='${width}' height='${height}' rx='${rx}' fill='#ffffff' stroke='#d1d5db' stroke-width='1'/>`,
          `  <text x='50%' y='50%' text-anchor='middle' dominant-baseline='central' font-family="'Inter','Segoe UI',sans-serif" font-size='${baseFont}' font-weight='700' fill='#111827'>${priceLabel}</text>`,
          `</svg>`
        ].join('')

        const marker = new window.mappls.Marker({
          map: mapInstanceRef.current,
          position: coords,
          fitbounds: false,
          element: wrapper
        })

        try {
          marker.addListener('click', () => {
            window.dispatchEvent(new CustomEvent('property-selected', { detail: property }))
          })
        } catch (listenerErr) {
          console.warn('Marker click listener failed:', listenerErr)
        }

        markersRef.current.push(marker)
      } catch (err) {
        console.error('Failed to create property marker:', err)
      }
    })

    console.log(`📍 Displayed ${markersRef.current.length} property markers at zoom ${currentZoom}`)
  }, [])

  // Keep ref in sync after declaration to avoid TDZ
  useEffect(() => {
    displayPropertiesOnMapRef.current = displayPropertiesOnMap
  }, [displayPropertiesOnMap])

  // Load properties from backend
  const loadProperties = useCallback(async () => {
    if (!mapInstanceRef.current) return

    try {
      console.log('🔄 Loading properties from backend...')
      const zoomLevel = typeof mapInstanceRef.current?.getZoom === 'function'
        ? mapInstanceRef.current.getZoom()
        : mapZoom
      const params = new URLSearchParams()
      params.set('limit', '300') // Changed from 0 to explicit limit
      if (zoomLevel != null) {
        params.set('zoom', String(zoomLevel))
      }

      const url = `${backendURL}/api/properties?${params.toString()}`
      console.log(`🌐 Fetching properties from: ${url}`)
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Failed to fetch properties: HTTP ${response.status} ${response.statusText}`)
      }
      let data
      try {
        data = await response.json()
        console.log(`✅ Properties fetch successful: ${data?.properties?.length || 0} properties received`)
      } catch (e) {
        throw new Error(`Invalid JSON from /api/properties: ${e.message}`)
      }

      // If data structure isn't as expected, provide fallback data structure
      if (!data) {
        console.warn('Empty response from properties API')
        data = { properties: [] }
      }
      
      // If properties field is missing, create it
      if (!data.properties) {
        console.warn('Response missing properties array, reconstructing:', data)
        
        // If it's an array at the top level, treat it as the properties
        if (Array.isArray(data)) {
          data = { properties: data }
        } else {
          data.properties = []
        }
      }
      
      if (Array.isArray(data.properties) && data.properties.length > 0) {
        console.log(`✅ Got ${data.properties.length} properties, sample:`, data.properties[0])
        setProperties(data.properties)
        displayPropertiesOnMap(filterProperties(data.properties))
        console.log(`✅ Loaded ${data.properties.length} properties`)
      } else {
        console.warn('No properties found in response')
        setProperties([])
        displayPropertiesOnMap([])
      }
    } catch (error) {
      // More detailed error logging
      console.error('❌ Failed to load properties:', error.message || error)
      console.error('Error details:', {
        message: error.message, 
        stack: error.stack,
        name: error.name,
        url: backendURL + '/api/properties'
      })
      
      // Do not use any fallback. Show no markers until real backend is available
      setProperties([])
      displayPropertiesOnMap([])
    }
  }, [backendURL, displayPropertiesOnMap, filterProperties, mapZoom])

  // Show heatmap overlay
  const showHotspotHeatmap = (hotspots) => {
    if (!mapInstanceRef.current || !Array.isArray(hotspots)) return
    
    // Mapbox heatmap implementation
    if (!window.mappls && mapInstanceRef.current.getSource) {
      try {
        const map = mapInstanceRef.current
        const sourceId = 'valora-heatmap'
        const layerId = 'valora-heatmap-layer'
        
        const features = hotspots
          .filter(h => isFinite(h?.latitude ?? h?.lat) && isFinite(h?.longitude ?? h?.lng))
          .map(h => ({
            type: 'Feature',
            properties: {
              weight: h.investment_score || 1
            },
            geometry: {
              type: 'Point',
              coordinates: [h.longitude ?? h.lng, h.latitude ?? h.lat]
            }
          }))
        const data = { type: 'FeatureCollection', features }
        
        if (map.getLayer(layerId)) map.removeLayer(layerId)
        if (map.getSource(sourceId)) map.removeSource(sourceId)
        
        map.addSource(sourceId, { type: 'geojson', data })
        map.addLayer({
          id: layerId,
          type: 'heatmap',
          source: sourceId,
          maxzoom: 15,
          paint: {
            'heatmap-weight': ['interpolate', ['linear'], ['get', 'weight'], 0, 0, 100, 1],
            'heatmap-intensity': 1,
            'heatmap-color': [
              'interpolate', ['linear'], ['heatmap-density'],
              0, 'rgba(0,0,0,0)',
              0.2, 'rgba(59,130,246,0.5)',
              0.4, 'rgba(124,58,237,0.6)',
              0.6, 'rgba(16,185,129,0.7)',
              0.8, 'rgba(245,158,11,0.8)',
              1, 'rgba(239,68,68,0.9)'
            ],
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 15, 15, 30],
            'heatmap-opacity': 0.8
          }
        })
      } catch (e) {
        console.warn('Mapbox heatmap failed:', e?.message)
      }
      return
    }
    
    // Mappls path: not available natively; placeholders/log
    console.log('Heatmap for Mappls not implemented; using markers instead')
  }

  // Enhanced circle drawing with persistence
  const startCircleDrawing = (mappls) => {
    if (!mapInstanceRef.current) return
    setDrawingMode('circle')
    setIsDrawing(true)
    console.log('⭕ Circle drawing started - Click to place center')
    
    const clickHandler = (e) => {
      console.log('🖱️ Click event structure:', e)
      
      // Handle different event structures from Mappls API
      let lat, lng
      if (e.latlng) { lat = e.latlng.lat; lng = e.latlng.lng }
      else if (e.lngLat) { lat = e.lngLat.lat; lng = e.lngLat.lng }
      else if (e.position) { lat = e.position.lat; lng = e.position.lng }
      else if (e.center) { lat = e.center.lat; lng = e.center.lng }
      else { console.error('Unable to get coordinates from event:', e); return }
      
      const shapeId = `circle-${Date.now()}`
      const center = [lat, lng]
      const radius = 1000 // Default 1km radius
      
      const shape = {
        id: shapeId,
        type: 'circle',
        center,
        radius,
        fillColor: '#3b82f6',
        strokeColor: '#2563eb',
        created: new Date().toISOString()
      }
      
      try {
        const circle = new window.mappls.Circle({
          map: mapInstanceRef.current,
          center: {lat: center[0], lng: center[1]},
          radius: radius,
          fillColor: shape.fillColor,
          fillOpacity: 0.2,
          strokeColor: shape.strokeColor,
          strokeWeight: 2
        })
        
        shapeObjectsRef.current.set(shapeId, circle)
        overlaysRef.current.push(circle)
        circle.addListener('click', () => selectShape(shape))
        
        setDrawnShapes(prev => {
          pushUndoSnapshot(prev)
          const updated = [...prev, shape]
          saveShapesToStorage(updated)
          return updated
        })
        
        console.log(`✅ CIRCLE CREATED: center [${center[0].toFixed(4)}, ${center[1].toFixed(4)}], radius ${(radius/1000).toFixed(2)} km`)
      } catch (err) {
        console.error('❌ Circle creation failed:', err)
      }
      
      mapInstanceRef.current.off('click', clickHandler)
      activeClickHandlerRef.current = null
      setDrawingMode(null)
      setIsDrawing(false)
    }
    
    activeClickHandlerRef.current = clickHandler
    mapInstanceRef.current.on('click', clickHandler)
  }

  const startTextDrawing = (mappls) => {
    if (!mapInstanceRef.current) return
    setDrawingMode('text')
    setIsDrawing(true)
    console.log('🔤 Text drawing started - Click to place text label')
    
    const clickHandler = (e) => {
      let lat, lng
      if (e.latlng) { lat = e.latlng.lat; lng = e.latlng.lng }
      else if (e.lngLat) { lat = e.lngLat.lat; lng = e.lngLat.lng }
      else if (e.position) { lat = e.position.lat; lng = e.position.lng }
      else if (e.center) { lat = e.center.lat; lng = e.center.lng }
      else { console.error('Unable to get coordinates from event:', e); return }
      
      const content = window.prompt('Enter text label', 'Label')
      if (content === null) {
        mapInstanceRef.current.off('click', clickHandler)
        setDrawingMode(null)
        setIsDrawing(false)
        return
      }
      
      const shapeId = `text-${Date.now()}`
      const position = [lat, lng]
      const shape = {
        id: shapeId,
        type: 'text',
        position,
        text: content,
        fontSize: 14,
        color: '#e5e7eb',
        created: new Date().toISOString()
      }
      
      try {
        const size = 10
        const dotSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${size/2}" cy="${size/2}" r="${(size/2)-1}" fill="#111827" stroke="#ffffff" stroke-width="2"/></svg>`
        const dot = encodeSvgToDataUri(dotSvg)
        const marker = new mappls.Marker({
          map: mapInstanceRef.current,
          position: {lat: position[0], lng: position[1]},
          icon_url: dot,
          icon_size: size
        })
        const popupHtml = `<div style="padding:2px 4px; font-size:${shape.fontSize}px; color:${shape.color}; background: rgba(0,0,0,0.0);">${shape.text}</div>`
        try { marker.setPopup(popupHtml) } catch(_) {}
        try { marker.openPopup && marker.openPopup() } catch(_) {}
        shapeObjectsRef.current.set(shapeId, marker)
        markersRef.current.push(marker)
        marker.addListener?.('click', () => selectShape(shape))
        
        setDrawnShapes(prev => {
          pushUndoSnapshot(prev)
          const updated = [...prev, shape]
          saveShapesToStorage(updated)
          return updated
        })
        
        console.log(`✅ TEXT PLACED at [${position[0].toFixed(4)}, ${position[1].toFixed(4)}]`)
      } catch (err) {
        console.error('❌ Text creation failed:', err)
      }
      
      mapInstanceRef.current.off('click', clickHandler)
      activeClickHandlerRef.current = null
      setDrawingMode(null)
      setIsDrawing(false)
    }
    
    activeClickHandlerRef.current = clickHandler
    mapInstanceRef.current.on('click', clickHandler)
  }

  const startRectangleDrawing = (mappls) => {
    if (!mapInstanceRef.current) return
    setDrawingMode('rectangle')
    setIsDrawing(true)
    console.log('▢ Rectangle drawing started - Click first corner, then opposite corner')
    
    let firstCorner = null
    let tempMarker = null
    
    const clickHandler = (e) => {
      // Handle different event structures from Mappls API
      let lat, lng
      if (e.latlng) {
        lat = e.latlng.lat
        lng = e.latlng.lng
      } else if (e.lngLat) {
        lat = e.lngLat.lat
        lng = e.lngLat.lng
      } else if (e.position) {
        lat = e.position.lat
        lng = e.position.lng
      } else if (e.center) {
        lat = e.center.lat
        lng = e.center.lng
      } else {
        console.error('Unable to get coordinates from event:', e)
        return
      }
      
      if (!firstCorner) {
        firstCorner = [lat, lng]
        tempMarker = new mappls.Marker({
          map: mapInstanceRef.current,
          position: {lat: lat, lng: lng},
          icon_size: 8
        })
        console.log('✓ First corner set')
        return
      }
      
      const secondCorner = [lat, lng]
      const bounds = [
        [firstCorner[0], firstCorner[1]],
        [secondCorner[0], firstCorner[1]],
        [secondCorner[0], secondCorner[1]],
        [firstCorner[0], secondCorner[1]],
        [firstCorner[0], firstCorner[1]]
      ]
      
      const shapeId = `rectangle-${Date.now()}`
      const shape = {
        id: shapeId,
        type: 'rectangle',
        points: bounds,
        bounds: [firstCorner, secondCorner],
        fillColor: '#22c55e',
        strokeColor: '#16a34a',
        created: new Date().toISOString()
      }
      
      try {
        const polygon = new window.mappls.Polygon({
          map: mapInstanceRef.current,
          paths: bounds,
          fillColor: shape.fillColor,
          fillOpacity: 0.2,
          strokeColor: shape.strokeColor,
          strokeWeight: 2
        })
        
        shapeObjectsRef.current.set(shapeId, polygon)
        polygonsRef.current.push(polygon)
        polygon.addListener('click', () => selectShape(shape))
        
        setDrawnShapes(prev => {
          const updated = [...prev, shape]
          saveShapesToStorage(updated)
          return updated
        })
        
        console.log(`✅ RECTANGLE CREATED`)
      } catch (err) {
        console.error('❌ Rectangle creation failed:', err)
      }
      
      // Remove temporary marker
      safeRemove(tempMarker)
      mapInstanceRef.current.off('click', clickHandler)
      activeClickHandlerRef.current = null
      setDrawingMode(null)
      setIsDrawing(false)
    }
    
    activeClickHandlerRef.current = clickHandler
    mapInstanceRef.current.on('click', clickHandler)
  }

  const startMarkerDrawing = (mappls) => {
    if (!mapInstanceRef.current) return
    setDrawingMode('marker')
    setIsDrawing(true)
    console.log('📍 Marker drawing started - Click to place marker')
    
    const clickHandler = (e) => {
      // Handle different event structures from Mappls API
      let lat, lng
      if (e.latlng) {
        lat = e.latlng.lat
        lng = e.latlng.lng
      } else if (e.lngLat) {
        lat = e.lngLat.lat
        lng = e.lngLat.lng
      } else if (e.position) {
        lat = e.position.lat
        lng = e.position.lng
      } else if (e.center) {
        lat = e.center.lat
        lng = e.center.lng
      } else {
        console.error('Unable to get coordinates from event:', e)
        return
      }
      
      const shapeId = `marker-${Date.now()}`
      const position = [lat, lng]
      
      const shape = {
        id: shapeId,
        type: 'marker',
        position,
        created: new Date().toISOString()
      }
      
      try {
        const purpleMarkerSvg = `data:image/svg+xml;base64,${btoa('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40"><path fill="#9333ea" stroke="#7c3aed" stroke-width="2" d="M16 0C9.373 0 4 5.373 4 12c0 8.5 12 28 12 28s12-19.5 12-28c0-6.627-5.373-12-12-12z"/><circle cx="16" cy="12" r="5" fill="white"/></svg>')}`
        const marker = new window.mappls.Marker({
          map: mapInstanceRef.current,
          position: {lat: position[0], lng: position[1]},
          icon_url: purpleMarkerSvg,
          icon_size: 32,
          draggable: false
        })
        
        shapeObjectsRef.current.set(shapeId, marker)
        markersRef.current.push(marker)
        marker.addListener('click', () => selectShape(shape))
        
        setDrawnShapes(prev => {
          const updated = [...prev, shape]
          saveShapesToStorage(updated)
          return updated
        })
        
        console.log(`✅ MARKER PLACED at [${position[0].toFixed(4)}, ${position[1].toFixed(4)}]`)
      } catch (err) {
        console.error('❌ Marker creation failed:', err)
      }
      
      mapInstanceRef.current.off('click', clickHandler)
      setDrawingMode(null)
      setIsDrawing(false)
    }
    
    mapInstanceRef.current.on('click', clickHandler)
  }

  // Add GeoJSON overlay
  const addGeoJSONOverlay = (geojson) => {
    if (!mapInstanceRef.current || !geojson) return
    
    // Mappls path: add markers for points
    if (window.mappls && mapInstanceRef.current && typeof window.mappls.Marker === 'function') {
      try {
        if (geojson.features) {
          geojson.features.forEach(feature => {
            if (feature.geometry?.type === 'Point') {
              const [lng, lat] = feature.geometry.coordinates || []
              if (isFinite(lat) && isFinite(lng)) {
                const size = 10
                const dotSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${size/2}" cy="${size/2}" r="${(size/2)-1}" fill="#111827" stroke="#ffffff" stroke-width="2"/></svg>`
                const dot = encodeSvgToDataUri(dotSvg)
                const marker = new window.mappls.Marker({
                  map: mapInstanceRef.current,
                  position: {lat: lat, lng: lng},
                  icon_url: dot,
                  icon_size: size,
                  title: feature.properties?.name || 'Location'
                })
                markersRef.current.push(marker)
              }
            }
          })
        }
      } catch (_) {}
      return
    }
    
    // Mapbox path: add a GeoJSON source and layers
    try {
      const map = mapInstanceRef.current
      if (!map.getSource) return
      const sourceId = 'valora-geojson'
      const circleLayerId = 'valora-geojson-circles'
      const symbolLayerId = 'valora-geojson-symbols'
      
      if (map.getLayer(circleLayerId)) map.removeLayer(circleLayerId)
      if (map.getLayer(symbolLayerId)) map.removeLayer(symbolLayerId)
      if (map.getSource(sourceId)) map.removeSource(sourceId)
      
      map.addSource(sourceId, {
        type: 'geojson',
        data: geojson
      })
      
      // Circles for points
      map.addLayer({
        id: circleLayerId,
        type: 'circle',
        source: sourceId,
        paint: {
          'circle-radius': 6,
          'circle-color': '#7c3aed',
          'circle-opacity': 0.8,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff'
        },
        filter: ['==', ['geometry-type'], 'Point']
      })
      
      // Labels if name exists
      map.addLayer({
        id: symbolLayerId,
        type: 'symbol',
        source: sourceId,
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 12,
          'text-offset': [0, 1]
        },
        paint: {
          'text-color': '#e5e7eb'
        }
      })
    } catch (e) {
      console.warn('Mapbox overlay add failed:', e?.message)
    }
  }

  // Toggle layer visibility
  const toggleLayer = (layerType, visible) => {
    setLayers(prev => ({ ...prev, [layerType]: visible }))
    
    if (mapInstanceRef.current) {
      console.log(`Toggling layer ${layerType}: ${visible}`)
      
      // Handle properties layer
      if (layerType === 'properties') {
        if (visible) {
          loadProperties()
        } else {
          // Hide property markers
          markersRef.current.forEach(m => safeRemove(m))
          markersRef.current = []
        }
      }
    }
  }

  // Select shape for editing/deletion
  const selectShape = (shape) => {
    console.log('🎯 Selected shape:', shape.type, shape.id)
    setSelectedShape(shape)
  }

  // Delete selected shape
  const deleteSelectedShape = () => {
    if (!selectedShape) {
      console.warn('⚠️ No shape selected to delete')
      return
    }
    
    console.log(`🗑️ Attempting to delete ${selectedShape.type}: ${selectedShape.id}`)
    const mapObj = shapeObjectsRef.current.get(selectedShape.id)
    
    if (!mapObj) {
      console.warn(`⚠️ Map object not found for ${selectedShape.id}`)
    }
    
    safeRemove(mapObj)
    shapeObjectsRef.current.delete(selectedShape.id)
    
    switch (selectedShape.type) {
      case 'circle':
        overlaysRef.current = overlaysRef.current.filter(o => o !== mapObj)
        break
      case 'polygon':
      case 'rectangle':
        polygonsRef.current = polygonsRef.current.filter(p => p !== mapObj)
        break
      case 'polyline':
        polylinesRef.current = polylinesRef.current.filter(p => p !== mapObj)
        break
      case 'marker':
        markersRef.current = markersRef.current.filter(m => m !== mapObj)
        break
      case 'text':
        markersRef.current = markersRef.current.filter(m => m !== mapObj)
        break
    }
    
    setDrawnShapes(prev => {
      pushUndoSnapshot(prev)
      const updated = prev.filter(s => s.id !== selectedShape.id)
      saveShapesToStorage(updated)
      return updated
    })
    setSelectedShape(null)
    setTimeout(() => syncShapesToCurrentView(), 0)
  }

  // Save shapes to localStorage
  const saveShapesToStorage = (shapes) => {
    try {
      localStorage.setItem('valora-drawn-shapes', JSON.stringify(shapes))
      console.log(`💾 Saved ${shapes.length} shapes`)
    } catch (err) {
      console.error('Failed to save shapes:', err)
    }
  }

  // Load shapes from localStorage
  const loadSavedShapes = () => {
    try {
      const saved = localStorage.getItem('valora-drawn-shapes')
      if (!saved) return
      
      const shapes = JSON.parse(saved)
      console.log(`📂 Loading ${shapes.length} saved shapes`)
      
      shapes.forEach(shape => {
        recreateShape(shape)
      })
      
      setDrawnShapes(shapes)
    } catch (err) {
      console.error('Failed to load shapes:', err)
    }
  }

  // Load enhanced shapes from localStorage
  const loadEnhancedShapes = () => {
    try {
      const saved = localStorage.getItem('valora-enhanced-shapes')
      if (!saved) return
      
      const shapes = JSON.parse(saved)
      console.log(`📂 Loading ${shapes.length} enhanced shapes`)
      
      shapes.forEach(shape => {
        recreateEnhancedShape(shape)
      })
    } catch (err) {
      console.error('Failed to load enhanced shapes:', err)
    }
  }

  // Recreate enhanced shape on map
  const recreateEnhancedShape = (shape) => {
    if (!window.mappls || !mapInstanceRef.current) return
    
    try {
      if (shape.type === 'buffer') {
        const circle = new window.mappls.Circle({
          map: mapInstanceRef.current,
          center: {lat: shape.center[0], lng: shape.center[1]},
          radius: shape.radius * 1000,
          fillColor: shape.metadata?.color?.fill || '#3b82f6',
          fillOpacity: 0.2,
          strokeColor: shape.metadata?.color?.stroke || '#2563eb',
          strokeWeight: 2
        })
        shapeObjectsRef.current.set(shape.id, circle)
        overlaysRef.current.push(circle)
      }
    } catch (err) {
      console.error(`Failed to recreate enhanced shape ${shape.id}:`, err)
    }
  }

  // Recreate shape on map from saved data
  const recreateShape = (shape) => {
    if (!window.mappls || !mapInstanceRef.current) return
    
    try {
      let mapObj
      
      switch (shape.type) {
        case 'polygon':
        case 'rectangle':
          mapObj = new window.mappls.Polygon({
            map: mapInstanceRef.current,
            paths: shape.points,
            fillColor: shape.fillColor || '#6366f1',
            fillOpacity: 0.3,
            strokeColor: shape.strokeColor || '#4f46e5',
            strokeWeight: 2
          })
          polygonsRef.current.push(mapObj)
          break
          
        case 'polyline':
          mapObj = new window.mappls.Polyline({
            map: mapInstanceRef.current,
            path: shape.points,
            strokeColor: shape.strokeColor || '#10b981',
            strokeWeight: 3
          })
          polylinesRef.current.push(mapObj)
          break
          
        case 'circle':
          mapObj = new window.mappls.Circle({
            map: mapInstanceRef.current,
            center: {lat: shape.center[0], lng: shape.center[1]},
            radius: shape.radius,
            fillColor: shape.fillColor || '#3b82f6',
            fillOpacity: 0.2,
            strokeColor: shape.strokeColor || '#2563eb',
            strokeWeight: 2
          })
          overlaysRef.current.push(mapObj)
          break
          
        case 'marker':
          const purpleMarkerSvg = `data:image/svg+xml;base64,${btoa('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40"><path fill="#9333ea" stroke="#7c3aed" stroke-width="2" d="M16 0C9.373 0 4 5.373 4 12c0 8.5 12 28 12 28s12-19.5 12-28c0-6.627-5.373-12-12-12z"/><circle cx="16" cy="12" r="5" fill="white"/></svg>')}`
          mapObj = new window.mappls.Marker({
            map: mapInstanceRef.current,
            position: {lat: shape.position[0], lng: shape.position[1]},
            icon_url: purpleMarkerSvg,
            icon_size: 32
          })
          markersRef.current.push(mapObj)
          break
      }
      
      if (mapObj) {
        shapeObjectsRef.current.set(shape.id, mapObj)
        mapObj.addListener?.('click', () => selectShape(shape))
      }
    } catch (err) {
      console.error(`Failed to recreate ${shape.type}:`, err)
    }
  }

  // Toggle 3D View (Mappls only)
  const toggle3DView = () => {
    if (mapProvider !== 'mappls' || !mapInstanceRef.current) return
    
    const new3DState = !is3DView
    setIs3DView(new3DState)
    
    try {
      if (new3DState) {
        // Enable 3D view
        mapInstanceRef.current.setPitch(60) // Tilt camera
        mapInstanceRef.current.setBearing(0) // North up
        console.log('🏙️ Switched to 3D view')
      } else {
        // Disable 3D view
        mapInstanceRef.current.setPitch(0) // Flat view
        mapInstanceRef.current.setBearing(0)
        console.log('🗺️ Switched to 2D view')
      }
      
      // Re-sync all shapes to ensure they appear in the new view
      syncShapesToCurrentView()
    } catch (err) {
      console.error('Failed to toggle 3D view:', err)
    }
  }

  // Sync all shapes to current view (redraw them)
  const syncShapesToCurrentView = () => {
    if (!mapInstanceRef.current) return
    
    console.log(`🔄 Syncing ${drawnShapes.length} shapes to ${is3DView ? '3D' : '2D'} view`)
    
    // Clear all existing shape objects
    shapeObjectsRef.current.forEach((obj) => safeRemove(obj))
    shapeObjectsRef.current.clear()
    polygonsRef.current = []
    polylinesRef.current = []
    overlaysRef.current = []
    
    // Recreate all shapes
    drawnShapes.forEach(shape => {
      recreateShape(shape)
    })
    
    console.log('✅ Shapes synced successfully')
  }

  // Clear all shapes
  const clearAllShapes = () => {
    markersRef.current.forEach(m => safeRemove(m))
    polygonsRef.current.forEach(p => safeRemove(p))
    polylinesRef.current.forEach(p => safeRemove(p))
    overlaysRef.current.forEach(o => safeRemove(o))
    
    markersRef.current = []
    polygonsRef.current = []
    polylinesRef.current = []
    overlaysRef.current = []
    shapeObjectsRef.current.clear()
    
    setDrawnShapes([])
    setSelectedShape(null)
    saveShapesToStorage([])
    console.log('🧹 Cleared all shapes')
  }

  // Cleanup map
  const cleanupMap = () => {
    clearAllShapes()
    
    if (mapInstanceRef.current) {
      if (mapProvider === 'mappls') {
        // Mappls cleanup
      } else if (mapProvider === 'mapbox') {
        mapInstanceRef.current.remove()
      }
      mapInstanceRef.current = null
    }
  }

  // Functions from EnhancedMapTools - Measure tool implementation
  const startMeasurement = (type) => {
    if (!mapInstanceRef.current) return
    setMeasureMode(type)
    measurePointsRef.current = []
    
    const clickHandler = (e) => {
      const point = extractCoordinates(e)
      if (!point) return
      
      measurePointsRef.current.push(point)
      
      if (type === 'distance') {
        displayDistanceMeasurement()
      } else if (type === 'area' && measurePointsRef.current.length >= 3) {
        displayAreaMeasurement()
      }
    }
    
    const finishHandler = () => {
      setMeasureMode(null)
      mapInstanceRef.current.off('click', clickHandler)
      mapInstanceRef.current.off('dblclick', finishHandler)
    }
    
    mapInstanceRef.current.on('click', clickHandler)
    mapInstanceRef.current.on('dblclick', finishHandler)
  }

  // Extract coordinates from different event types
  const extractCoordinates = (e) => {
    if (e.latlng) return [e.latlng.lat, e.latlng.lng]
    if (e.lngLat) return [e.lngLat.lat, e.lngLat.lng]
    if (e.position) return [e.position.lat, e.position.lng]
    if (e.center) return [e.center.lat, e.center.lng]
    return null
  }

  // Calculate distance between points (Haversine formula)
  const calculateDistance = (point1, point2) => {
    const R = 6371 // Earth's radius in km
    const dLat = (point2[0] - point1[0]) * Math.PI / 180
    const dLon = (point2[1] - point1[1]) * Math.PI / 180
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(point1[0] * Math.PI / 180) * Math.cos(point2[0] * Math.PI / 180) *
      Math.sin(dLon/2) * Math.sin(dLon/2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    return R * c
  }

  // Display distance measurement
  const displayDistanceMeasurement = () => {
    const points = measurePointsRef.current
    if (points.length < 2) return
    
    let totalDistance = 0
    for (let i = 1; i < points.length; i++) {
      totalDistance += calculateDistance(points[i-1], points[i])
    }
    
    console.log(`📏 Total Distance: ${totalDistance.toFixed(2)} km`)
    
    // Display on map
    if (window.mappls && mapInstanceRef.current) {
      const polyline = new window.mappls.Polyline({
        map: mapInstanceRef.current,
        path: points.map(p => ({lat: p[0], lng: p[1]})),
        strokeColor: '#ef4444',
        strokeWeight: 2,
        strokeOpacity: 0.8
      })
    }
  }

  // Calculate polygon area (Shoelace formula)
  const calculateEnhancedPolygonArea = (points) => {
    let area = 0
    for (let i = 0; i < points.length; i++) {
      const j = (i + 1) % points.length
      area += points[i][1] * points[j][0]
      area -= points[j][1] * points[i][0]
    }
    return Math.abs(area / 2) * 111 * 111 // Convert to sq km (approximate)
  }

  // Display area measurement
  const displayAreaMeasurement = () => {
    const points = measurePointsRef.current
    const area = calculateEnhancedPolygonArea(points)
    
    console.log(`📐 Total Area: ${area.toFixed(2)} sq km`)
    
    // Display on map
    if (window.mappls && mapInstanceRef.current) {
      const polygon = new window.mappls.Polygon({
        map: mapInstanceRef.current,
        paths: points.map(p => ({lat: p[0], lng: p[1]})),
        fillcolor: '#ef4444',
        fillOpacity: 0.2,
        strokeColor: '#ef4444',
        strokeWeight: 2,
        strokeOpacity: 0.8
      })
    }
  }

  

  

  // Edit shape functionality
  const startEditMode = (mode) => {
    if (!selectedShape) {
      alert('Please select a shape to edit')
      return
    }
    
    setEditMode(mode)
    console.log(`✏️ Edit mode: ${mode}`)
    
    // Implementation would depend on shape type and edit mode
    if (mode === 'move') {
      enableShapeMovement(selectedShape)
    } else if (mode === 'rotate') {
      enableShapeRotation(selectedShape)
    } else if (mode === 'scale') {
      enableShapeScaling(selectedShape)
    } else if (mode === 'resize') {
      enableShapeResizing(selectedShape)
    }
  }

  const enableShapeMovement = (shape) => {
    // Add drag handlers to move the shape
    console.log('🔄 Shape movement enabled')
  }

  const enableShapeRotation = (shape) => {
    // Add rotation controls
    console.log('🔄 Shape rotation enabled')
  }

  const enableShapeScaling = (shape) => {
    // Add scale handles
    console.log('🔄 Shape scaling enabled')
  }

  const enableShapeResizing = (shape) => {
    // Add resize handles
    console.log('🔄 Shape resizing enabled')
  }

  // Snap to grid functionality
  const toggleSnapToGrid = () => {
    setSnapToGrid(!snapToGrid)
    console.log(`📐 Snap to grid: ${!snapToGrid ? 'ON' : 'OFF'}`)
  }

  // Export shapes as GeoJSON
  const exportShapes = () => {
    const geojson = {
      type: 'FeatureCollection',
      features: drawnShapes.map(shape => ({
        type: 'Feature',
        properties: {
          id: shape.id,
          type: shape.type,
          area: shape.area,
          distance: shape.distance,
          created: shape.created
        },
        geometry: shapeToGeoJSON(shape)
      }))
    }
    
    const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `valora-shapes-${Date.now()}.geojson`
    a.click()
    
    console.log('💾 Exported shapes as GeoJSON')
  }

  const shapeToGeoJSON = (shape) => {
    switch(shape.type) {
      case 'polygon':
      case 'rectangle':
        return {
          type: 'Polygon',
          coordinates: [shape.points.map(p => [p[1], p[0]])]
        }
      case 'polyline':
        return {
          type: 'LineString',
          coordinates: shape.points.map(p => [p[1], p[0]])
        }
      case 'circle':
        // Convert circle to polygon approximation
        const numPoints = 32
        const coords = []
        for (let i = 0; i < numPoints; i++) {
          const angle = (i / numPoints) * 2 * Math.PI
          const lat = shape.center[0] + (shape.radius / 111000) * Math.sin(angle)
          const lng = shape.center[1] + (shape.radius / (111000 * Math.cos(shape.center[0] * Math.PI / 180))) * Math.cos(angle)
          coords.push([lng, lat])
        }
        coords.push(coords[0]) // Close the polygon
        return { type: 'Polygon', coordinates: [coords] }
      case 'marker':
        return {
          type: 'Point',
          coordinates: [shape.position[1], shape.position[0]]
        }
      default:
        return null
    }
  }

  return (
    <div className="relative w-full h-full bg-[#0a0612] overflow-hidden">
      {/* Map Container */}
      <div 
        ref={mapContainerRef}
        id="mappls-map-container"
        className="absolute inset-0 w-full h-full"
        style={{ minHeight: '400px', cursor: (isDrawing && drawingMode === 'marker') ? 'crosshair' : 'default' }}
      />
      
      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0a0612]/95 z-10">
          <div className="text-white text-center">
            <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p>Loading interactive map...</p>
          </div>
        </div>
      )}
      
      {/* Error Overlay */}
      {error && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-30">
          <div className="bg-purple-900 border border-purple-700 text-white px-4 py-2 rounded-lg shadow-lg">
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}
      
      {/* Navigation Indicator */}
      {isGeocoding && (
        <div className="absolute top-4 right-4 z-30 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-full shadow-xl flex items-center gap-2 animate-fade-in">
          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
          <span className="text-sm font-medium">🗺️ Navigating...</span>
        </div>
      )}
      
      
      {/* Bottom Bar: Compact with Dropdowns */}
      <div className="absolute left-0 right-0 bottom-0 z-20 pb-3 px-4 pointer-events-none">
        <div className="mx-auto max-w-3xl pointer-events-auto">
          <div className="flex items-center justify-center gap-4 px-3 py-2">
            {/* Combined Drawing Tools */}
            <div className="relative dropdown-container">
              <button
                onClick={() => {
                  setShowDrawDropdown(!showDrawDropdown)
                  setShowEnhancedTools(false)
                  setShowLayersDropdown(false)
                  setShowPropertyTypeDropdown(false)
                  setShowPriceRangeDropdown(false)
                  setShowAreaDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-purple-900 text-purple-200 hover:text-white hover:bg-purple-700 border border-purple-700"
              >
                <span className="text-[11px]">Draw</span>
                <ChevronDown size={14} className={`transition-transform ${showDrawDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showDrawDropdown && (
                <div className="absolute bottom-full mb-2 left-0 bg-[#100820] border border-purple-700 rounded-lg shadow-2xl py-1 min-w-[200px]">
                  {/* Basic Shapes */}
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Basic Shapes</div>
                  <button
                    onClick={() => {
                      if (mapProvider === 'mappls' && drawingManagerRef.current) {
                        setDrawingMode('polygon')
                        drawingManagerRef.current.startPolygon()
                      } else {
                        setDrawingMode('polygon')
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Pentagon size={16} />
                    <span>Polygon</span>
                  </button>
                  <button
                    onClick={() => {
                      if (mapProvider === 'mappls' && drawingManagerRef.current) {
                        drawingManagerRef.current.startPolyline()
                      } else {
                        setDrawingMode('polyline')
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Minus size={16} />
                    <span>Polyline</span>
                  </button>
                  <button
                    onClick={() => {
                      if (mapProvider === 'mappls') {
                        startCircleDrawing(window.mappls)
                      } else {
                        setDrawingMode('circle')
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Circle size={16} />
                    <span>Circle</span>
                  </button>
                  <button
                    onClick={() => {
                      if (mapProvider === 'mappls') {
                        startRectangleDrawing(window.mappls)
                      } else {
                        setDrawingMode('rectangle')
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Square size={16} />
                    <span>Rectangle</span>
                  </button>
                  <button
                    onClick={() => {
                      if (mapProvider === 'mappls') {
                        startMarkerDrawing(window.mappls)
                      } else {
                        setDrawingMode('marker')
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <MapPin size={16} />
                    <span>Marker</span>
                  </button>
                  
                  {/* Real Estate Tools */}
                  <div className="border-t border-purple-700 my-1"></div>
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Real Estate</div>
                  <button
                    onClick={() => {
                      if (drawingManagerRef.current) {
                        drawingManagerRef.current.startPropertyBoundary()
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Home size={16} />
                    <span>Property Boundary</span>
                  </button>
                  <button
                    onClick={() => {
                      if (drawingManagerRef.current) {
                        drawingManagerRef.current.startCatchmentArea('metro')
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Building size={16} />
                    <span>Catchment Area</span>
                  </button>
                  <button
                    onClick={() => {
                      // Start investment zone analysis
                      if (drawingManagerRef.current) {
                        drawingManagerRef.current.startPolygon()
                      }
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <TrendingUp size={16} />
                    <span>Investment Zone</span>
                  </button>
                  
                  {/* Actions */}
                  <div className="border-t border-purple-700 my-1"></div>
                  <button
                    onClick={() => {
                      clearAllShapes()
                      setShowDrawDropdown(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-300 hover:bg-purple-800 hover:text-white transition-colors"
                  >
                    <Trash2 size={16} />
                    <span>Clear All</span>
                  </button>
                </div>
              )}
            </div>

            {/* Tools Dropdown */}
            <div className="relative dropdown-container">
              <button
                onClick={() => {
                  setShowEnhancedTools(!showEnhancedTools)
                  setShowDrawDropdown(false)
                  setShowLayersDropdown(false)
                  setShowPropertyTypeDropdown(false)
                  setShowPriceRangeDropdown(false)
                  setShowAreaDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-purple-900 text-purple-200 hover:text-white hover:bg-purple-700 border border-purple-700"
              >
                <span className="text-[11px]">Tools</span>
                <ChevronDown size={14} className={`transition-transform ${showEnhancedTools ? 'rotate-180' : ''}`} />
              </button>
              {showEnhancedTools && (
                <div className="absolute bottom-full mb-2 right-0 bg-[#100820] border border-purple-700 rounded-lg shadow-2xl py-1 min-w-[200px]">
                  {/* Measure Tools */}
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Measure</div>
                  <button
                    onClick={() => {
                      startMeasurement('distance')
                      setShowEnhancedTools(false)
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs ${measureMode === 'distance' ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                  >
                    <Ruler size={16} />
                    <span>Measure Distance</span>
                  </button>
                  <button
                    onClick={() => {
                      startMeasurement('area')
                      setShowEnhancedTools(false)
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs ${measureMode === 'area' ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                  >
                    <Maximize2 size={16} />
                    <span>Measure Area</span>
                  </button>

                  {/* Edit Tools */}
                  <div className="border-t border-purple-700 my-1"></div>
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Edit</div>
                  <button
                    onClick={() => {
                      handleUndo()
                      setShowEnhancedTools(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Undo2 size={16} />
                    <span>Undo</span>
                  </button>
                  <button
                    onClick={() => {
                      handleRedo()
                      setShowEnhancedTools(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Redo2 size={16} />
                    <span>Redo</span>
                  </button>

                  <button
                    onClick={() => {
                      deleteSelectedShape()
                      setShowEnhancedTools(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-300 hover:bg-purple-800 hover:text-white transition-colors"
                  >
                    <Trash2 size={16} />
                    <span>Delete Selected</span>
                  </button>

                  <div className="flex items-center gap-2 px-3 py-2">
                    <button
                      onClick={() => resizeSelected(0.9)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors border border-purple-700 rounded"
                    >
                      <Minus size={16} />
                      <span>Size -</span>
                    </button>
                    <button
                      onClick={() => resizeSelected(1.1)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors border border-purple-700 rounded"
                    >
                      <Plus size={16} />
                      <span>Size +</span>
                    </button>
                  </div>

                  {/* Utility Tools */}
                  <div className="border-t border-purple-700 my-1"></div>
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Utilities</div>
                  <button
                    onClick={() => {
                      toggleSnapToGrid()
                      setShowEnhancedTools(false)
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs ${snapToGrid ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                  >
                    <Grid size={16} />
                    <span>Snap to Grid</span>
                  </button>
                  <button
                    onClick={() => {
                      exportShapes()
                      setShowEnhancedTools(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                  >
                    <Save size={16} />
                    <span>Export GeoJSON</span>
                  </button>
                </div>
              )}
            </div>

            {/* Layers Dropdown */}
            <div className="relative dropdown-container">
              <button
                onClick={() => {
                  setShowLayersDropdown(!showLayersDropdown)
                  setShowDrawDropdown(false)
                  setShowEnhancedTools(false)
                  setShowPropertyTypeDropdown(false)
                  setShowPriceRangeDropdown(false)
                  setShowAreaDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-purple-900 text-purple-200 hover:text-white hover:bg-purple-700 border border-purple-700"
              >
                <span className="text-[11px]">Layers</span>
                <ChevronDown size={14} className={`transition-transform ${showLayersDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showLayersDropdown && (
                <div className="absolute bottom-full mb-2 right-0 bg-[#100820] border border-purple-700 rounded-lg shadow-2xl py-1 min-w-[160px]">
                  {Object.entries(layers).map(([key, value]) => (
                    <button
                      key={key}
                      onClick={() => {
                        toggleLayer(key, !value)
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 text-xs text-neutral-300 hover:bg-purple-600 hover:text-white transition-colors"
                    >
                      <span className="capitalize">{key === 'heatmap' ? 'Heatmap' : key}</span>
                      <div className={`w-4 h-4 rounded border-2 ${value ? 'bg-purple-600 border-purple-600' : 'border-neutral-500'} flex items-center justify-center`}>
                        {value && <span className="text-white text-[10px]">✓</span>}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Property Type Dropdown */}
            <div className="relative dropdown-container">
              <button
                onClick={() => {
                  setShowPropertyTypeDropdown(!showPropertyTypeDropdown)
                  setShowDrawDropdown(false)
                  setShowEnhancedTools(false)
                  setShowLayersDropdown(false)
                  setShowPriceRangeDropdown(false)
                  setShowAreaDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-purple-900 text-purple-200 hover:text-white hover:bg-purple-700 border border-purple-700"
              >
                <Home size={14} />
                <span className="text-[11px]">{propertyTypeLabel}</span>
                <ChevronDown size={14} className={`transition-transform ${showPropertyTypeDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showPropertyTypeDropdown && (
                <div className="fixed left-1/2 bottom-24 transform -translate-x-1/2 bg-[#100820] border border-purple-700 rounded-lg shadow-2xl py-2 min-w-[640px] z-50">
                  <div className="px-4 pb-2 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Property Type</div>
                  <div className="px-3 pb-2">
                    <button
                      onClick={clearPropertyTypes}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-md ${selectedPropertyTypes.length === 0 ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                    >
                      <span>All</span>
                      {selectedPropertyTypes.length === 0 && <span className="text-[10px]">✓</span>}
                    </button>
                  </div>
                  <div className="border-t border-purple-700"></div>
                  <div className="grid grid-cols-3 gap-3 px-3 py-3">
                    <div>
                      <div className="px-2 pb-1 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Residential</div>
                      <div className="flex flex-col gap-1">
                        {['Flat','House/Villa','Plot','1 Bhk','2 Bhk','3 Bhk','4 Bhk','5 Bhk','5+ Bhk'].map((type) => (
                          <button
                            key={type}
                            onClick={() => togglePropertyType(type)}
                            className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-md ${selectedPropertyTypes.includes(type) ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                          >
                            <span>{type}</span>
                            {selectedPropertyTypes.includes(type) && <span className="text-[10px]">✓</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="px-2 pb-1 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Commercial</div>
                      <div className="flex flex-col gap-1">
                        {['Office Space','Shop/Showroom','Commercial Land','Warehouse/Godown','Industrial Building','Industrial Shed'].map((type) => (
                          <button
                            key={type}
                            onClick={() => togglePropertyType(type)}
                            className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-md ${selectedPropertyTypes.includes(type) ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                          >
                            <span>{type}</span>
                            {selectedPropertyTypes.includes(type) && <span className="text-[10px]">✓</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="px-2 pb-1 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Other Property Types</div>
                      <div className="flex flex-col gap-1">
                        {['Agricultural Land','Farm House'].map((type) => (
                          <button
                            key={type}
                            onClick={() => togglePropertyType(type)}
                            className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-md ${selectedPropertyTypes.includes(type) ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                          >
                            <span>{type}</span>
                            {selectedPropertyTypes.includes(type) && <span className="text-[10px]">✓</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-purple-700"></div>
                  <div className="flex items-center justify-between gap-3 px-3 py-2">
                    <button
                      onClick={clearPropertyTypes}
                      className="px-3 py-1.5 text-xs rounded-md border border-purple-700 text-purple-200 hover:bg-purple-800"
                    >
                      Clear
                    </button>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-neutral-400">{selectedPropertyTypes.length} selected</span>
                      <button
                        onClick={applyPropertyTypes}
                        className="px-3 py-1.5 text-xs rounded-md bg-purple-600 hover:bg-purple-500 text-white"
                      >
                        Apply
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Price Range Dropdown */}
            <div className="relative dropdown-container">
              <button
                onClick={() => {
                  setShowPriceRangeDropdown(!showPriceRangeDropdown)
                  setShowDrawDropdown(false)
                  setShowEnhancedTools(false)
                  setShowLayersDropdown(false)
                  setShowPropertyTypeDropdown(false)
                  setShowAreaDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-purple-900 text-purple-200 hover:text-white hover:bg-purple-700 border border-purple-700"
              >
                <span className="text-[12px]">₹</span>
                <span className="text-[11px]">{selectedPriceRange}</span>
                <ChevronDown size={14} className={`transition-transform ${showPriceRangeDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showPriceRangeDropdown && (
                <div className="absolute bottom-full mb-2 right-0 bg-[#100820] border border-purple-700 rounded-lg shadow-2xl py-1 min-w-[160px]">
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Price Range</div>
                  {['All', 'Under 50L', '50L - 1Cr', '1Cr - 2Cr', '2Cr - 3Cr', 'Above 3Cr'].map((range) => (
                    <button
                      key={range}
                      onClick={() => {
                        setSelectedPriceRange(range)
                        setShowPriceRangeDropdown(false)
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs ${selectedPriceRange === range ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                    >
                      <span>{range}</span>
                      {selectedPriceRange === range && <span className="text-[10px]">✓</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Area Dropdown */}
            <div className="relative dropdown-container">
              <button
                onClick={() => {
                  setShowAreaDropdown(!showAreaDropdown)
                  setShowDrawDropdown(false)
                  setShowEnhancedTools(false)
                  setShowLayersDropdown(false)
                  setShowPropertyTypeDropdown(false)
                  setShowPriceRangeDropdown(false)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md bg-purple-900 text-purple-200 hover:text-white hover:bg-purple-700 border border-purple-700"
              >
                <Maximize size={14} />
                <span className="text-[11px]">{selectedArea}</span>
                <ChevronDown size={14} className={`transition-transform ${showAreaDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showAreaDropdown && (
                <div className="absolute bottom-full mb-2 right-0 bg-[#100820] border border-purple-700 rounded-lg shadow-2xl py-1 min-w-[180px]">
                  <div className="px-3 py-1.5 text-[10px] text-purple-400 font-medium uppercase tracking-wide">Area (Sq.Ft)</div>
                  {['All', '500 - 1000', '1000 - 1500', '1500 - 2000', '2000 - 2500', '2500+'].map((area) => (
                    <button
                      key={area}
                      onClick={() => {
                        setSelectedArea(area)
                        setShowAreaDropdown(false)
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs ${selectedArea === area ? 'bg-purple-600 text-white' : 'text-neutral-300 hover:bg-purple-600 hover:text-white'} transition-colors`}
                    >
                      <span>{area}</span>
                      {selectedArea === area && <span className="text-[10px]">✓</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Drawing Mode Indicator */}
      {isDrawing && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-50 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-3 rounded-lg shadow-2xl border-2 border-white/30">
          <div className="text-center">
            <div className="text-lg font-bold mb-1">
              {drawingMode === 'polygon' && '📐 Drawing Polygon'}
              {drawingMode === 'polyline' && '📏 Drawing Polyline'}
              {drawingMode === 'circle' && '⭕ Drawing Circle'}
              {drawingMode === 'rectangle' && '▢ Drawing Rectangle'}
              {drawingMode === 'marker' && '📍 Placing Marker'}
            </div>
            <div className="text-xs opacity-90">
              {drawingMode === 'polygon' && `Click map to add points • ${drawingStateRef.current.points.length} points • Right-click or Double-click to finish • Press Esc to cancel`}
              {drawingMode === 'polyline' && `Click map to add points • ${drawingStateRef.current.points.length} points • Right-click or Double-click to finish • Press Esc to cancel`}
              {drawingMode === 'circle' && 'Click once to place 1km radius circle • Press Esc to cancel'}
              {drawingMode === 'rectangle' && (drawingStateRef.current.points.length === 0 ? 'Click first corner • Press Esc to cancel' : 'Click opposite corner • Press Esc to cancel')}
              {drawingMode === 'marker' && 'Click once to place marker • Press Esc to cancel'}
            </div>
          </div>
        </div>
      )}

      {/* Info Panel for Selected Shape */}
      {selectedShape && (
        <div className="absolute bottom-20 left-4 z-20">
          <div className="bg-purple-900 rounded-lg p-4 shadow-xl border border-purple-700 max-w-sm">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-white capitalize">📐 {selectedShape.type}</h4>
              <button
                onClick={() => setSelectedShape(null)}
                className="text-gray-400 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>
            <div className="text-xs text-gray-300 space-y-2">
              {selectedShape.area && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Area:</span>
                  <span className="font-medium">{selectedShape.area.toFixed(2)} sq km</span>
                </div>
              )}
              {selectedShape.distance && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Distance:</span>
                  <span className="font-medium">{selectedShape.distance.toFixed(2)} km</span>
                </div>
              )}
              {selectedShape.radius && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Radius:</span>
                  <span className="font-medium">{(selectedShape.radius / 1000).toFixed(2)} km</span>
                </div>
              )}
              {selectedShape.points && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Points:</span>
                  <span className="font-medium">{selectedShape.points.length}</span>
                </div>
              )}
              {selectedShape.position && (
                <div className="text-gray-400 text-[10px]">
                  {selectedShape.position[0].toFixed(5)}, {selectedShape.position[1].toFixed(5)}
                </div>
              )}
              {(selectedShape.type === 'circle' || selectedShape.type === 'polygon' || selectedShape.type === 'rectangle' || selectedShape.type === 'polyline' || selectedShape.type === 'text') && (
                <div className="mt-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-gray-400">Size</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          const newVal = Math.max(10, sizeSlider - 10)
                          const factor = newVal / sizeSlider
                          resizeSelected(factor)
                          setSizeSlider(newVal)
                        }}
                        className="px-2 py-1 rounded bg-purple-800 hover:bg-purple-700 text-white"
                        title="Decrease size"
                      >
                        <Minus size={12} />
                      </button>
                      <input
                        type="range"
                        min={10}
                        max={300}
                        value={sizeSlider}
                        onChange={(e) => {
                          const val = parseInt(e.target.value, 10)
                          const factor = val / sizeSlider
                          resizeSelected(factor)
                          setSizeSlider(val)
                        }}
                        className="w-40 accent-purple-500"
                      />
                      <button
                        onClick={() => {
                          const newVal = Math.min(300, sizeSlider + 10)
                          const factor = newVal / sizeSlider
                          resizeSelected(factor)
                          setSizeSlider(newVal)
                        }}
                        className="px-2 py-1 rounded bg-purple-800 hover:bg-purple-700 text-white"
                        title="Increase size"
                      >
                        <Plus size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <button
                onClick={deleteSelectedShape}
                className="w-full mt-2 px-3 py-1.5 bg-purple-700 hover:bg-purple-600 text-white rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-1"
              >
                <Trash2 size={14} />
                Delete Shape
              </button>
            </div>
          </div>
        </div>
      )}
      
      
      
      {/* Current Location Button */}
      <button
        onClick={() => {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              const coords = [position.coords.latitude, position.coords.longitude]
              if (mapInstanceRef.current) {
                // Use smooth animation to current location
                smoothCenterMap(coords[0], coords[1], 15)
              }
            },
            (error) => console.error('Location error:', error)
          )
        }}
        className="absolute bottom-4 right-4 z-20 p-3 bg-purple-600 hover:bg-purple-700 
                 text-white rounded-full shadow-xl transition-all transform hover:scale-110"
        title="Current Location"
      >
        <Navigation size={20} />
      </button>
    </div>
  )
}

export default InteractiveMapView
