import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { normalizePath } from 'vite'
import path from 'path'
import sirv from 'sirv'
import { visualizer } from 'rollup-plugin-visualizer'
import viteCompression from 'vite-plugin-compression'

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
    },
    isProduction && visualizer({
      filename: './dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true
    }),
    isProduction && viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 10240,
      deleteOriginFile: false
    }),
    isProduction && viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 10240,
      deleteOriginFile: false
    })
  ].filter(Boolean),
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
    sourcemap: false,
    target: 'es2020',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: isProduction,
        drop_debugger: isProduction,
        pure_funcs: isProduction ? ['console.log', 'console.info', 'console.debug'] : []
      },
      format: {
        comments: false
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-cesium': ['cesium', 'resium'],
          'vendor-charts': ['recharts'],
          'vendor-ui': ['lucide-react'],
          'vendor-utils': ['axios', 'react-markdown', 'remark-gfm']
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    },
    chunkSizeWarningLimit: 1000,
    cssCodeSplit: true,
    assetsInlineLimit: 4096
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'cesium', 'axios'],
    exclude: ['@loaders.gl/3d-tiles']
  }
})
