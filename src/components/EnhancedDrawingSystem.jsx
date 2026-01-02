// Enhanced Drawing System for Real Estate Analysis
// This module provides advanced drawing capabilities with AI integration

export const EnhancedDrawingSystem = {
  // Real Estate Specific Drawing Modes
  DRAWING_MODES: {
    PROPERTY_BOUNDARY: 'property-boundary',
    CATCHMENT_AREA: 'catchment-area',
    BUFFER_ZONE: 'buffer-zone',
    COMPARISON_ZONE: 'comparison-zone',
    INVESTMENT_HOTSPOT: 'investment-hotspot',
    POLYGON: 'polygon',
    POLYLINE: 'polyline',
    CIRCLE: 'circle',
    RECTANGLE: 'rectangle',
    MARKER: 'marker'
  },

  // Colors for different zone types
  ZONE_COLORS: {
    residential: { fill: '#10b981', stroke: '#059669' },
    commercial: { fill: '#3b82f6', stroke: '#2563eb' },
    industrial: { fill: '#f59e0b', stroke: '#d97706' },
    investment: { fill: '#8b5cf6', stroke: '#7c3aed' },
    catchment: { fill: '#06b6d4', stroke: '#0891b2' },
    comparison: { fill: '#ec4899', stroke: '#db2777' }
  },

  // Initialize enhanced drawing system
  initializeDrawing(mapInstance, mappls) {
    const drawingState = {
      mode: null,
      isDrawing: false,
      points: [],
      tempMarkers: [],
      tempShape: null,
      zoneType: 'residential',
      metadata: {}
    }

    return {
      drawingState,
      
      // Start drawing with AI context
      startDrawingWithContext(mode, context = {}) {
        console.log(`🎨 Starting ${mode} drawing with context:`, context)
        drawingState.mode = mode
        drawingState.isDrawing = true
        drawingState.metadata = context
        
        // Disable map interactions
        this.disableMapInteractions(mapInstance)
        
        switch(mode) {
          case this.DRAWING_MODES.PROPERTY_BOUNDARY:
            return this.startPropertyBoundary(mapInstance, mappls, context)
          case this.DRAWING_MODES.CATCHMENT_AREA:
            return this.startCatchmentArea(mapInstance, mappls, context)
          case this.DRAWING_MODES.BUFFER_ZONE:
            return this.drawBufferZone(mapInstance, mappls, context)
          case this.DRAWING_MODES.POLYGON:
            return this.startEnhancedPolygon(mapInstance, mappls, context)
          default:
            console.warn(`Unknown drawing mode: ${mode}`)
        }
      },

      // Enhanced polygon drawing with real estate metadata
      startEnhancedPolygon(mapInstance, mappls, context) {
        const points = []
        const tempMarkers = []
        let tempPolygon = null
        
        const clickHandler = (e) => {
          const point = [e.latlng.lat, e.latlng.lng]
          points.push(point)
          
          // Add numbered marker
          const marker = new mappls.Marker({
            map: mapInstance,
            position: { lat: e.latlng.lat, lng: e.latlng.lng },
            icon_size: 10,
            label: String(points.length)
          })
          tempMarkers.push(marker)
          
          // Update preview polygon
          if (points.length >= 3) {
            if (tempPolygon) tempPolygon.setMap(null)
            
            const colors = this.getColorForContext(context)
            tempPolygon = new mappls.Polygon({
              map: mapInstance,
              paths: points,
              fillColor: colors.fill,
              fillOpacity: 0.3,
              strokeColor: colors.stroke,
              strokeWeight: 2,
              strokeOpacity: 0.8
            })
          }
          
          // Show area in real-time
          if (points.length >= 3) {
            const area = this.calculateArea(points)
            this.showDrawingInfo(`Area: ${area.toFixed(2)} sq km, ${points.length} points`)
          }
        }
        
        const dblClickHandler = (e) => {
          if (points.length >= 3) {
            this.finishPolygon(mapInstance, mappls, points, tempMarkers, tempPolygon, context)
          }
          mapInstance.off('click', clickHandler)
          mapInstance.off('dblclick', dblClickHandler)
          this.enableMapInteractions(mapInstance)
        }
        
        mapInstance.on('click', clickHandler)
        mapInstance.on('dblclick', dblClickHandler)
      },

      // Draw buffer zone (for AI commands like "draw 2km radius around Manyata")
      async drawBufferZone(mapInstance, mappls, context) {
        const { location, radius = 2, purpose = 'analysis' } = context
        
        try {
          // Get coordinates for location
          let coordinates
          if (typeof location === 'string') {
            coordinates = await this.geocodeLocation(location)
          } else {
            coordinates = location
          }
          
          if (!coordinates) {
            throw new Error(`Could not find location: ${location}`)
          }
          
          const [lat, lng] = coordinates
          const colors = this.ZONE_COLORS[purpose] || this.ZONE_COLORS.catchment
          
          const circle = new mappls.Circle({
            map: mapInstance,
            center: { lat, lng },
            radius: radius * 1000, // km to meters
            fillColor: colors.fill,
            fillOpacity: 0.2,
            strokeColor: colors.stroke,
            strokeOpacity: 0.8,
            strokeWeight: 2
          })
          
          // Save to storage with metadata
          const shape = {
            id: `buffer-${Date.now()}`,
            type: 'buffer',
            center: [lat, lng],
            radius: radius,
            location: location,
            purpose: purpose,
            metadata: {
              ...context,
              createdBy: 'AI',
              timestamp: new Date().toISOString()
            }
          }
          
          this.saveShape(shape)
          
          // Return shape for AI response
          return {
            success: true,
            shape: shape,
            message: `Drew ${radius}km buffer around ${location}`
          }
        } catch (error) {
          console.error('Buffer zone error:', error)
          return {
            success: false,
            error: error.message
          }
        }
      },

      // Property boundary drawing with area calculation
      startPropertyBoundary(mapInstance, mappls, context) {
        context.zoneType = 'property'
        context.calculatePrice = true
        return this.startEnhancedPolygon(mapInstance, mappls, context)
      },

      // Catchment area for amenities
      startCatchmentArea(mapInstance, mappls, context) {
        const { amenityType, radius = 1 } = context
        context.zoneType = 'catchment'
        
        // For catchment, we can use circle or polygon
        if (context.useCircle) {
          return this.drawBufferZone(mapInstance, mappls, { ...context, radius })
        } else {
          return this.startEnhancedPolygon(mapInstance, mappls, context)
        }
      },

      // Compare multiple zones
      async compareZones(mapInstance, mappls, zones) {
        const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        const results = []
        
        for (let i = 0; i < zones.length; i++) {
          const zone = zones[i]
          const color = colors[i % colors.length]
          
          const result = await this.drawBufferZone(mapInstance, mappls, {
            location: zone.location,
            radius: zone.radius || 2,
            purpose: 'comparison',
            color: { fill: color, stroke: color }
          })
          
          results.push(result)
        }
        
        return results
      },

      // Helper functions
      disableMapInteractions(map) {
        try {
          if (map.dragPan) map.dragPan.disable()
          if (map.scrollZoom) map.scrollZoom.disable()
          if (map.boxZoom) map.boxZoom.disable()
          if (map.dragRotate) map.dragRotate.disable()
          if (map.doubleClickZoom) map.doubleClickZoom.disable()
        } catch (e) {
          console.log('Could not disable interactions:', e)
        }
      },

      enableMapInteractions(map) {
        try {
          if (map.dragPan) map.dragPan.enable()
          if (map.scrollZoom) map.scrollZoom.enable()
          if (map.boxZoom) map.boxZoom.enable()
          if (map.dragRotate) map.dragRotate.enable()
          if (map.doubleClickZoom) map.doubleClickZoom.enable()
        } catch (e) {
          console.log('Could not enable interactions:', e)
        }
      },

      getColorForContext(context) {
        if (context.color) return context.color
        if (context.zoneType) {
          return this.ZONE_COLORS[context.zoneType] || this.ZONE_COLORS.residential
        }
        return this.ZONE_COLORS.residential
      },

      calculateArea(points) {
        // Simplified area calculation (would use geodesic in production)
        let area = 0
        for (let i = 0; i < points.length; i++) {
          const j = (i + 1) % points.length
          area += points[i][1] * points[j][0]
          area -= points[j][1] * points[i][0]
        }
        return Math.abs(area / 2) * 111 * 111 // Convert to sq km
      },

      async geocodeLocation(address) {
        const backendURL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
        try {
          const response = await fetch(`${backendURL}/api/maps/geocode?address=${encodeURIComponent(address)}`)
          const data = await response.json()
          return data.coordinates
        } catch (error) {
          console.error('Geocoding failed:', error)
          return null
        }
      },

      saveShape(shape) {
        try {
          const savedShapes = JSON.parse(localStorage.getItem('valora-enhanced-shapes') || '[]')
          savedShapes.push(shape)
          localStorage.setItem('valora-enhanced-shapes', JSON.stringify(savedShapes))
          console.log(`💾 Saved shape: ${shape.id}`)
          
          // Dispatch event for UI update
          window.dispatchEvent(new CustomEvent('shape-saved', { detail: shape }))
        } catch (error) {
          console.error('Failed to save shape:', error)
        }
      },

      finishPolygon(mapInstance, mappls, points, tempMarkers, tempPolygon, context) {
        // Clean up temp elements
        tempMarkers.forEach(m => m.setMap(null))
        if (tempPolygon) tempPolygon.setMap(null)
        
        // Create final polygon
        const colors = this.getColorForContext(context)
        const polygon = new mappls.Polygon({
          map: mapInstance,
          paths: points,
          fillColor: colors.fill,
          fillOpacity: 0.3,
          strokeColor: colors.stroke,
          strokeWeight: 2
        })
        
        // Calculate metrics
        const area = this.calculateArea(points)
        
        // Save with metadata
        const shape = {
          id: `polygon-${Date.now()}`,
          type: context.zoneType || 'polygon',
          points: points,
          area: area,
          metadata: {
            ...context,
            timestamp: new Date().toISOString(),
            propertyValue: context.calculatePrice ? area * 50000 : null // Example pricing
          }
        }
        
        this.saveShape(shape)
        
        // Show analysis
        this.showAnalysis(shape)
        
        return shape
      },

      showDrawingInfo(message) {
        // Create or update info overlay
        const infoDiv = document.getElementById('drawing-info') || document.createElement('div')
        infoDiv.id = 'drawing-info'
        infoDiv.className = 'absolute top-20 left-1/2 transform -translate-x-1/2 bg-purple-600 text-white px-4 py-2 rounded-lg shadow-lg z-50'
        infoDiv.textContent = message
        
        if (!document.getElementById('drawing-info')) {
          document.body.appendChild(infoDiv)
        }
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
          infoDiv.remove()
        }, 3000)
      },

      showAnalysis(shape) {
        const analysis = {
          type: shape.type,
          area: `${shape.area.toFixed(2)} sq km`,
          perimeter: this.calculatePerimeter(shape.points),
          estimatedValue: shape.metadata.propertyValue,
          nearbyAmenities: [] // Would fetch from backend
        }
        
        window.dispatchEvent(new CustomEvent('shape-analysis', { detail: analysis }))
      },

      calculatePerimeter(points) {
        let perimeter = 0
        for (let i = 0; i < points.length; i++) {
          const j = (i + 1) % points.length
          const distance = this.haversineDistance(points[i], points[j])
          perimeter += distance
        }
        return perimeter.toFixed(2)
      },

      haversineDistance(point1, point2) {
        const [lat1, lng1] = point1
        const [lat2, lng2] = point2
        const R = 6371 // Earth radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180
        const dLng = (lng2 - lng1) * Math.PI / 180
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLng / 2) * Math.sin(dLng / 2)
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
        return R * c
      }
    }
  }
}

export default EnhancedDrawingSystem
