// Valora Tile Cache Service Worker
// Automatically caches Cesium Ion photorealistic tiles AND local building tiles

const ION_CACHE_NAME = 'valora-ion-tiles-v1'
const BUILDING_CACHE_NAME = 'valora-building-tiles-v1'
const METADATA_CACHE = 'valora-cache-metadata-v1'

// Patterns for Ion tile requests
const ION_TILE_PATTERNS = [
  /tile\.googleapis\.com\/v1\/3dtiles/,
  /ion\.cesium\.com.*\.b3dm/,
  /ion\.cesium\.com.*\.glb/,
  /ion\.cesium\.com.*\.gltf/,
  /ion\.cesium\.com.*tileset\.json/,
  /\.b3dm$/,
  /\.glb$/,
  /\.gltf$/,
  /subtree/
]

// Patterns for local building tile requests
const BUILDING_TILE_PATTERNS = [
  /\/api\/tiles\/viewport/,
  /\/api\/buildings/,
  /\/api\/spatial/
]

// Track cache stats
let ionCacheStats = {
  totalTiles: 0,
  totalSize: 0,
  lastUpdate: Date.now()
}

let buildingCacheStats = {
  totalTiles: 0,
  totalSize: 0,
  lastUpdate: Date.now()
}

// Cache size limits (in number of tiles)
const MAX_ION_TILES = 200 // Reduced from 500
const MAX_BUILDING_TILES = 5000 // Reduced from 10000

// Building display limits for performance optimization
const MAX_BUILDINGS_DISPLAY = 20000 // Reduced from 50000
const BUILDING_LOAD_RADIUS_KM = 1 // Reduced from 2km
const MAX_TILES_IN_MEMORY = 100 // Reduced from 200

// LRU tracking for cache eviction
const tileAccessTimes = new Map()

// Photorealistic tile cache settings - CONSERVATIVE for smooth performance
const PHOTOREALISTIC_CACHE_CONFIG = {
  maximumScreenSpaceError: 4, // Higher = less detail but better performance
  maximumMemoryUsage: 512, // 512MB only - reduced from 2GB to prevent lag
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

// Check if URL matches Ion tile patterns
function isIonTileRequest(url) {
  return ION_TILE_PATTERNS.some(pattern => pattern.test(url))
}

// Check if URL matches building tile patterns
function isBuildingTileRequest(url) {
  return BUILDING_TILE_PATTERNS.some(pattern => pattern.test(url))
}

// Manage cache size with LRU eviction
async function manageCacheSize(cacheName, maxItems) {
  const cache = await caches.open(cacheName)
  const keys = await cache.keys()
  
  if (keys.length <= maxItems) return
  
  // Sort by access time (oldest first)
  const sortedKeys = keys.sort((a, b) => {
    const timeA = tileAccessTimes.get(a.url) || 0
    const timeB = tileAccessTimes.get(b.url) || 0
    return timeA - timeB
  })
  
  // Delete oldest items until under limit
  const toDelete = sortedKeys.slice(0, keys.length - maxItems)
  for (const request of toDelete) {
    await cache.delete(request)
    tileAccessTimes.delete(request.url)
  }
  
  console.log(`🧹 Cache cleaned: removed ${toDelete.length} old tiles`)
}

// Update access time for LRU tracking
function updateTileAccessTime(url) {
  tileAccessTimes.set(url, Date.now())
  // Clean up old entries periodically
  if (tileAccessTimes.size > 2000) {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000 // 24 hours
    for (const [key, time] of tileAccessTimes) {
      if (time < cutoff) tileAccessTimes.delete(key)
    }
  }
}

// Get cache size estimate
async function getCacheSize() {
  if ('storage' in navigator && 'estimate' in navigator.storage) {
    const estimate = await navigator.storage.estimate()
    return {
      usage: estimate.usage || 0,
      quota: estimate.quota || 0,
      percentage: estimate.quota ? ((estimate.usage / estimate.quota) * 100).toFixed(2) : 0
    }
  }
  return null
}

// Update cache stats
async function updateCacheStats() {
  const ionCache = await caches.open(ION_CACHE_NAME)
  const buildingCache = await caches.open(BUILDING_CACHE_NAME)
  const ionKeys = await ionCache.keys()
  const buildingKeys = await buildingCache.keys()
  const sizeInfo = await getCacheSize()
  
  ionCacheStats = {
    totalTiles: ionKeys.length,
    totalSize: sizeInfo?.usage || 0,
    quota: sizeInfo?.quota || 0,
    percentage: sizeInfo?.percentage || 0,
    lastUpdate: Date.now()
  }
  
  buildingCacheStats = {
    totalTiles: buildingKeys.length,
    totalSize: 0, // Approximate from total usage
    lastUpdate: Date.now()
  }
  
  // Store stats in metadata cache
  const metaCache = await caches.open(METADATA_CACHE)
  const statsResponse = new Response(JSON.stringify({ ion: ionCacheStats, building: buildingCacheStats }))
  await metaCache.put('/cache-stats', statsResponse)
  
  console.log('📊 Cache Stats - Ion:', ionCacheStats.totalTiles, 'Building:', buildingCacheStats.totalTiles)
}

// Install event - setup caches
self.addEventListener('install', (event) => {
  console.log('🔧 Tile Cache Service Worker installing...')
  event.waitUntil(
    Promise.all([
      caches.open(ION_CACHE_NAME),
      caches.open(BUILDING_CACHE_NAME),
      caches.open(METADATA_CACHE)
    ]).then(() => {
      console.log('✅ Tile Cache Service Worker installed')
      self.skipWaiting()
    })
  )
})

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  console.log('🚀 Tile Cache Service Worker activating...')
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => 
            (name.startsWith('valora-ion-') || name.startsWith('valora-building-') || name.startsWith('valora-cache-')) && 
            name !== ION_CACHE_NAME && 
            name !== BUILDING_CACHE_NAME && 
            name !== METADATA_CACHE
          )
          .map(name => {
            console.log('🗑️ Deleting old cache:', name)
            return caches.delete(name)
          })
      )
    }).then(() => {
      console.log('✅ Tile Cache Service Worker activated')
      return self.clients.claim()
    })
  )
})

// Fetch event - cache Ion tiles and building tiles
self.addEventListener('fetch', (event) => {
  const url = event.request.url
  
  // Determine cache type
  const isIonTile = isIonTileRequest(url)
  const isBuildingTile = isBuildingTileRequest(url)
  
  if (!isIonTile && !isBuildingTile) {
    return // Let other requests pass through
  }
  
  const cacheName = isIonTile ? ION_CACHE_NAME : BUILDING_CACHE_NAME
  const tileType = isIonTile ? 'Ion' : 'Building'
  
  event.respondWith(
    caches.open(cacheName).then(cache => {
      return cache.match(event.request).then(cachedResponse => {
        if (cachedResponse) {
          // Update access time for LRU tracking
          updateTileAccessTime(event.request.url)
          console.log(`📦 ${tileType} from cache:`, url.substring(url.lastIndexOf('/') + 1))
          return cachedResponse
        }
        
        // Fetch from network and cache
        return fetch(event.request).then(networkResponse => {
          // Only cache successful responses
          if (networkResponse && networkResponse.ok) {
            // Clone response before caching
            const responseToCache = networkResponse.clone()
            
            // Manage cache size before adding new tile
            const maxItems = isIonTile ? MAX_ION_TILES : MAX_BUILDING_TILES
            
            cache.put(event.request, responseToCache).then(() => {
              updateTileAccessTime(event.request.url)
              console.log(`💾 Cached ${tileType} tile:`, url.substring(url.lastIndexOf('/') + 1))
              updateCacheStats()
              // Clean up old tiles in background
              manageCacheSize(cacheName, maxItems)
            })
          }
          
          return networkResponse
        }).catch(error => {
          console.error(`❌ ${tileType} fetch failed:`, error)
          // Return cached version if available (offline fallback)
          return cache.match(event.request)
        })
      })
    })
  )
})

// Message handler for cache management
self.addEventListener('message', (event) => {
  if (event.data.type === 'GET_CACHE_STATS') {
    updateCacheStats().then(() => {
      event.ports[0].postMessage({ ion: ionCacheStats, building: buildingCacheStats })
    })
  }
  
  if (event.data.type === 'CLEAR_ION_CACHE') {
    caches.delete(ION_CACHE_NAME).then(() => {
      console.log('🗑️ Ion cache cleared')
      ionCacheStats = {
        totalTiles: 0,
        totalSize: 0,
        lastUpdate: Date.now()
      }
      event.ports[0].postMessage({ success: true })
    })
  }
  
  if (event.data.type === 'CLEAR_BUILDING_CACHE') {
    caches.delete(BUILDING_CACHE_NAME).then(() => {
      console.log('🗑️ Building cache cleared')
      buildingCacheStats = {
        totalTiles: 0,
        totalSize: 0,
        lastUpdate: Date.now()
      }
      event.ports[0].postMessage({ success: true })
    })
  }
  
  if (event.data.type === 'CLEAR_ALL_CACHE') {
    Promise.all([
      caches.delete(ION_CACHE_NAME),
      caches.delete(BUILDING_CACHE_NAME)
    ]).then(() => {
      console.log('🗑️ All caches cleared')
      ionCacheStats = { totalTiles: 0, totalSize: 0, lastUpdate: Date.now() }
      buildingCacheStats = { totalTiles: 0, totalSize: 0, lastUpdate: Date.now() }
      event.ports[0].postMessage({ success: true })
    })
  }
  
  if (event.data.type === 'EXPORT_CACHE') {
    exportCacheToDownload().then(blob => {
      event.ports[0].postMessage({ success: true, size: blob.size })
    }).catch(error => {
      event.ports[0].postMessage({ success: false, error: error.message })
    })
  }
})

// Export cache as downloadable archive (for offline use)
async function exportCacheToDownload() {
  const cache = await caches.open(CACHE_NAME)
  const keys = await cache.keys()
  const tiles = []
  
  for (const request of keys) {
    const response = await cache.match(request)
    const blob = await response.blob()
    tiles.push({
      url: request.url,
      data: blob
    })
  }
  
  // Create a simple manifest
  const manifest = {
    version: 1,
    timestamp: Date.now(),
    tiles: tiles.map(t => ({ url: t.url, size: t.data.size }))
  }
  
  return new Blob([JSON.stringify(manifest)], { type: 'application/json' })
}
