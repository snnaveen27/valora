import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { normalizePath } from 'vite'
import path from 'path'
import sirv from 'sirv'

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          src: normalizePath(path.resolve(__dirname, 'node_modules/cesium/Build/Cesium')),
          dest: 'cesium'
        }
      ]
    }),
    {
      name: 'serve-cesium-assets',
      configureServer(server) {
        server.middlewares.use(
          '/cesium',
          sirv(path.resolve(__dirname, 'node_modules/cesium/Build/Cesium'), {
            dev: true,
            etag: true
          })
        )
      }
    }
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium/')
  },
  server: {
    port: 3000,
    open: true
  }
})
