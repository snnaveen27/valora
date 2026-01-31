import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { normalizePath } from 'vite'
import path from 'path'
import sirv from 'sirv'

const isProduction = process.env.NODE_ENV === 'production'
const basePath = isProduction ? '/valora/' : '/'

export default defineConfig({
  base: basePath,
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
    CESIUM_BASE_URL: JSON.stringify(isProduction ? '/valora/cesium/' : '/cesium/')
  },
  server: {
    port: 3000,
    open: true
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false
  }
})
