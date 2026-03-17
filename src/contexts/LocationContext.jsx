/**
 * LocationContext - Unified location state management for Valora
 * 
 * Provides a single source of truth for current location information
 * across the entire app (SmartPanel, Chat Panel, Community tabs, etc.)
 * 
 * Location structure:
 * - coordinates: { lat, lng }
 * - locality: string (e.g., "Defence Colony")
 * - place: string (e.g., "Koramangala, Bangalore")
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { API_URL } from '../apiConfig'

const LocationContext = createContext(null)

// Default location (Bangalore, India - use a neutral central location)
const DEFAULT_LOCATION = {
  coordinates: { lat: 12.9716, lng: 77.5946 },
  locality: 'Bangalore',
  place: 'Bangalore, Karnataka'
}

export function LocationProvider({ children }) {
  const [location, setLocation] = useState(DEFAULT_LOCATION)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  /**
   * Reverse geocode coordinates to get locality and place name
   */
  const reverseGeocode = useCallback(async (lat, lng) => {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}`
      )
      
      if (!response.ok) {
        throw new Error('Reverse geocoding failed')
      }

      const data = await response.json()
      const address = data.address || {}

      // Extract locality (suburb, neighborhood, village, town, city)
      const locality = 
        address.suburb || 
        address.neighbourhood || 
        address.village || 
        address.town || 
        address.city || 
        address.county || 
        address.state ||
        'Unknown Area'

      // Extract place (city, state or more detailed)
      const place = 
        (address.city || address.town || address.village || address.county) && address.state
          ? `${address.city || address.town || address.village || address.county}, ${address.state}`
          : locality

      return { locality, place }
    } catch (err) {
      console.warn('[LocationContext] Reverse geocoding error:', err)
      return { locality: 'Unknown Area', place: 'Unknown Location' }
    }
  }, [])

  /**
   * Update location from coordinates (e.g., map click)
   */
  const updateLocationFromCoordinates = useCallback(async (lat, lng) => {
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      console.warn('[LocationContext] Invalid coordinates:', { lat, lng })
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const { locality, place } = await reverseGeocode(lat, lng)
      
      const newLocation = {
        coordinates: { lat, lng },
        locality,
        place
      }

      setLocation(newLocation)
      
      // Dispatch event for other components to listen
      window.dispatchEvent(new CustomEvent('valora-location-changed', {
        detail: newLocation
      }))

      console.log('[LocationContext] Location updated:', newLocation)
    } catch (err) {
      console.error('[LocationContext] Failed to update location:', err)
      setError(err.message)
      
      // Still update with coordinates even if geocoding fails
      const newLocation = {
        coordinates: { lat, lng },
        locality: 'Unknown Area',
        place: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
      }
      setLocation(newLocation)
    } finally {
      setIsLoading(false)
    }
  }, [reverseGeocode])

  /**
   * Update location from a text query (e.g., user types "Koramangala")
   */
  const updateLocationFromQuery = useCallback(async (query) => {
    if (!query || typeof query !== 'string') {
      console.warn('[LocationContext] Invalid query:', query)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      // Geocode the query
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=jsonv2&q=${encodeURIComponent(query)}&limit=1`
      )

      if (!response.ok) {
        throw new Error('Geocoding failed')
      }

      const results = await response.json()

      if (!results || results.length === 0) {
        throw new Error('Location not found')
      }

      const result = results[0]
      const lat = parseFloat(result.lat)
      const lng = parseFloat(result.lon)

      // Get more details via reverse geocoding
      const { locality, place } = await reverseGeocode(lat, lng)

      const newLocation = {
        coordinates: { lat, lng },
        locality: result.address?.suburb || result.address?.city || locality,
        place: place || result.display_name?.split(',').slice(0, 2).join(',')
      }

      setLocation(newLocation)
      
      // Dispatch event for other components to listen
      window.dispatchEvent(new CustomEvent('valora-location-changed', {
        detail: newLocation
      }))

      console.log('[LocationContext] Location updated from query:', newLocation)
    } catch (err) {
      console.error('[LocationContext] Failed to geocode query:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [reverseGeocode])

  /**
   * Update location with explicit values (for backend analysis results)
   */
  const setExplicitLocation = useCallback((locationData) => {
    if (!locationData) return

    const newLocation = {
      coordinates: locationData.coordinates || location.location || { lat: locationData.lat, lng: locationData.lng },
      locality: locationData.locality || locationData.area_name || location.locality,
      place: locationData.place || locationData.display_name || location.place
    }

    // Ensure coordinates are valid
    if (!Number.isFinite(newLocation.coordinates?.lat) || !Number.isFinite(newLocation.coordinates?.lng)) {
      console.warn('[LocationContext] Invalid explicit location coordinates:', newLocation)
      return
    }

    setLocation(newLocation)
    
    // Dispatch event for other components to listen
    window.dispatchEvent(new CustomEvent('valora-location-changed', {
      detail: newLocation
    }))

    console.log('[LocationContext] Explicit location set:', newLocation)
  }, [])

  /**
   * Listen for location changes from other components (map, chat)
   */
  useEffect(() => {
    const handleLocationChange = async (e) => {
      const { coordinates, locality, place } = e.detail || {}
      
      if (coordinates && Number.isFinite(coordinates.lat) && Number.isFinite(coordinates.lng)) {
        // If locality/place not provided, reverse geocode to get them
        let resolvedLocality = locality
        let resolvedPlace = place
        
        if (!locality && !place) {
          try {
            const geoResult = await reverseGeocode(coordinates.lat, coordinates.lng)
            resolvedLocality = geoResult.locality
            resolvedPlace = geoResult.place
          } catch (err) {
            console.warn('[LocationContext] Reverse geocoding failed:', err)
          }
        }
        
        setLocation(prev => ({
          coordinates,
          locality: resolvedLocality || prev.locality,
          place: resolvedPlace || prev.place
        }))
      }
    }

    window.addEventListener('valora-location-changed', handleLocationChange)
    return () => window.removeEventListener('valora-location-changed', handleLocationChange)
  }, [])

  const value = {
    // Current location state
    location,
    coordinates: location.coordinates,
    locality: location.locality,
    place: location.place,
    
    // Loading and error states
    isLoading,
    error,
    
    // Update functions
    updateLocationFromCoordinates,
    updateLocationFromQuery,
    setExplicitLocation,
    
    // Utility
    isDefaultLocation: location.coordinates.lat === DEFAULT_LOCATION.coordinates.lat && 
                       location.coordinates.lng === DEFAULT_LOCATION.coordinates.lng
  }

  return (
    <LocationContext.Provider value={value}>
      {children}
    </LocationContext.Provider>
  )
}

/**
 * Hook to access the unified location context
 */
export function useLocation() {
  const context = useContext(LocationContext)
  
  if (!context) {
    // Return default values if not wrapped in provider (backward compatibility)
    console.warn('[useLocation] Not wrapped in LocationProvider, using defaults')
    return {
      location: DEFAULT_LOCATION,
      coordinates: DEFAULT_LOCATION.coordinates,
      locality: DEFAULT_LOCATION.locality,
      place: DEFAULT_LOCATION.place,
      isLoading: false,
      error: null,
      updateLocationFromCoordinates: () => {},
      updateLocationFromQuery: () => {},
      setExplicitLocation: () => {},
      isDefaultLocation: true
    }
  }
  
  return context
}

/**
 * Helper function to get location string for display
 */
export function getLocationString(location) {
  if (!location) return 'No location'
  
  const { locality, place, coordinates } = location
  
  if (locality && place) {
    return `${locality} (${place})`
  }
  
  if (place) {
    return place
  }
  
  if (coordinates && Number.isFinite(coordinates.lat) && Number.isFinite(coordinates.lng)) {
    return `${coordinates.lat.toFixed(4)}, ${coordinates.lng.toFixed(4)}`
  }
  
  return 'Unknown location'
}

export default LocationContext
