import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

function vendorChunk(id: string) {
  const moduleId = id.replaceAll('\\', '/')
  if (!moduleId.includes('/node_modules/')) return undefined

  if (
    moduleId.includes('/react/') ||
    moduleId.includes('/react-dom/') ||
    moduleId.includes('/react-router') ||
    moduleId.includes('/scheduler/')
  ) {
    return 'react-vendor'
  }

  if (
    moduleId.includes('/recharts/') ||
    moduleId.includes('/d3-') ||
    moduleId.includes('/victory-vendor/') ||
    moduleId.includes('/decimal.js-light/') ||
    moduleId.includes('/react-is/')
  ) {
    return 'charts-vendor'
  }

  if (moduleId.includes('/lucide-react/')) return 'icons-vendor'
  if (moduleId.includes('/axios/')) return 'http-vendor'
  if (moduleId.includes('/react-hot-toast/')) return 'toast-vendor'

  return undefined
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@shared': path.resolve(import.meta.dirname, '../frontend-shared'),
      'react/jsx-runtime': path.resolve(import.meta.dirname, 'node_modules/react/jsx-runtime.js'),
    },
    dedupe: ['react', 'react-dom'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: vendorChunk,
      },
    },
  },
  server: {
    port: 5176,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8080',
        changeOrigin: true,
      }
    }
  }
})

