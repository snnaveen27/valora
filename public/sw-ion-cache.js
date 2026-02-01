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

// Check if URL matches Ion tile patterns
function isIonTileRequest(url) {
  return ION_TILE_PATTERNS.some(pattern => pattern.test(url))
}

// Check if URL matches building tile patterns
function isBuildingTileRequest(url) {
  return BUILDING_TILE_PATTERNS.some(pattern => pattern.test(url))
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
          console.log(`📦 ${tileType} from cache:`, url.substring(url.lastIndexOf('/') + 1))
          return cachedResponse
        }
        
        // Fetch from network and cache
        return fetch(event.request).then(networkResponse => {
          // Only cache successful responses
          if (networkResponse && networkResponse.ok) {
            // Clone response before caching
            const responseToCache = networkResponse.clone()
            
            cache.put(event.request, responseToCache).then(() => {
              console.log(`💾 Cached ${tileType} tile:`, url.substring(url.lastIndexOf('/') + 1))
              updateCacheStats()
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
