import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'CIMARRON_')
  const backendUrl = env.CIMARRON_BACKEND_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: '127.0.0.1',
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api(?=\/|$)/, '') || '/',
          proxyTimeout: 180000
        }
      }
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom']
          }
        }
      }
    }
  }
})
