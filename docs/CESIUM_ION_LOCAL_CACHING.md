# Cesium Ion Photorealistic Tiles - Local Caching Guide (Education Use)

**⚠️ License Notice:** Google Photorealistic 3D Tiles are copyrighted. This guide is for **education and research purposes only**. Do not use cached tiles for commercial applications.

---

## Overview

Valora now supports:
1. **Enhanced in-memory cache** (2GB, 5000 tiles) for Ion streaming
2. **Local tileset URL override** for self-hosted tiles

---

## Option 1: Enhanced In-Memory Cache (Automatic)

**Already enabled!** When you load photorealistic tiles, Valora uses:

```javascript
maximumMemoryUsage: 2048 MB (default: 512 MB)
maximumScreenSpaceError: 1.5 (sharper, default: 2)
preloadWhenHidden: true
dynamicScreenSpaceError: true
```

**Benefits:**
- Tiles stay in memory longer during session
- Sharper visuals (lower screen space error)
- Aggressive preloading for smoother navigation

**Limitations:**
- Cache clears when you close the browser
- Requires active Ion connection

---

## Option 2: Self-Host Tiles Locally (Advanced)

### Step 1: Capture Tiles from Ion

1. **Open browser DevTools** (F12)
2. **Go to Network tab**
3. **Enable photorealistic tiles** in Valora
4. **Navigate around** the area you want to cache
5. **Filter by** `3d-tile` or `.b3dm` or `.glb`
6. **Right-click each tile** → Save

**What you'll see:**
```
https://tile.googleapis.com/v1/3dtiles/datasets/...
- tileset.json (root metadata)
- 0.b3dm, 1.b3dm, 2.b3dm (tile files)
- subtree files
```

### Step 2: Organize Locally

Create folder structure:
```
windsurf-project/
└── public/
    └── ion-cache/
        └── bangalore-photorealistic/
            ├── tileset.json
            ├── 0.b3dm
            ├── 1.b3dm
            ├── 2.b3dm
            └── ... (all captured tiles)
```

### Step 3: Fix tileset.json URLs

Open `tileset.json` and replace Ion URLs with local paths:

**Before:**
```json
{
  "root": {
    "content": {
      "uri": "https://tile.googleapis.com/v1/3dtiles/datasets/.../0.b3dm"
    }
  }
}
```

**After:**
```json
{
  "root": {
    "content": {
      "uri": "./0.b3dm"
    }
  }
}
```

Use relative paths (`./<filename>`) for all tile references.

### Step 4: Configure Valora

Edit `.env`:
```bash
VITE_LOCAL_PHOTOREALISTIC_TILESET_URL=/ion-cache/bangalore-photorealistic/tileset.json
```

### Step 5: Test

1. Restart dev server: `npm run dev`
2. Open Layers panel
3. Toggle **Photorealistic 3D (Ion)**
4. Check console for: `📦 Loading local photorealistic tileset from: /ion-cache/...`

---

## Option 3: Service Worker Cache (Browser)

Create `public/sw.js`:

```javascript
const CACHE_NAME = 'valora-ion-cache-v1'
const ION_TILE_PATTERNS = [
  /tile\.googleapis\.com\/v1\/3dtiles/,
  /\.b3dm$/,
  /\.glb$/,
  /tileset\.json$/
]

self.addEventListener('fetch', (event) => {
  const url = event.request.url
  
  // Only cache Ion tile requests
  if (!ION_TILE_PATTERNS.some(pattern => pattern.test(url))) {
    return
  }

  event.respondWith(
    caches.open(CACHE_NAME).then(cache => {
      return cache.match(event.request).then(response => {
        if (response) {
          console.log('📦 Serving from cache:', url)
          return response
        }

        return fetch(event.request).then(networkResponse => {
          // Cache successful responses
          if (networkResponse.ok) {
            cache.put(event.request, networkResponse.clone())
          }
          return networkResponse
        })
      })
    })
  )
})
```

Register in `index.html`:
```html
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
  }
</script>
```

**Benefits:**
- Automatic caching as you navigate
- Works offline after first visit
- No manual tile capture

**Limitations:**
- Browser cache limits (varies by browser)
- Still requires initial Ion connection

---

## Comparison

| Method | Offline | Persistent | Setup | Memory |
|--------|---------|------------|-------|--------|
| **In-Memory Cache** | ❌ | ❌ | ✅ Auto | 2GB RAM |
| **Self-Hosted** | ✅ | ✅ | 🔧 Manual | Disk |
| **Service Worker** | ✅ | ✅ | 🔧 Code | Browser cache |

---

## Best Practices

### For Education/Research:
1. **Cache only what you need** (specific areas)
2. **Document tile sources** in your research
3. **Don't redistribute** cached tiles
4. **Use for offline demos** at conferences/classes

### For Production:
1. **Use Ion streaming** (respects license)
2. **Rely on in-memory cache** (already optimized)
3. **Consider Cesium OSM Buildings** (more permissive license)

---

## Troubleshooting

### Tiles not loading locally
- Check browser console for 404 errors
- Verify `tileset.json` paths are relative
- Ensure files are in `public/` folder
- Check CORS if serving from external server

### High memory usage
- Reduce `maximumMemoryUsage` in `PHOTOREALISTIC_CACHE_CONFIG`
- Lower `maximumScreenSpaceError` (trades quality for memory)
- Disable `preloadWhenHidden`

### Tiles look blurry
- Decrease `maximumScreenSpaceError` (1.5 → 1.0)
- Increase `baseScreenSpaceError`
- Enable `foveatedScreenSpaceError`

---

## Legal Disclaimer

**Google Photorealistic 3D Tiles Terms:**
- Licensed for use via Cesium Ion
- Caching for offline use may violate terms
- Education/research use typically allowed
- Commercial use requires proper licensing

**Recommendation:** For production apps, use Ion streaming with enhanced in-memory cache (already configured).

---

## Additional Resources

- [Cesium 3D Tiles Spec](https://github.com/CesiumGS/3d-tiles)
- [Cesium Ion Documentation](https://cesium.com/docs/cesiumjs-ref-doc/Cesium3DTileset.html)
- [Google Maps Platform Terms](https://cloud.google.com/maps-platform/terms)
