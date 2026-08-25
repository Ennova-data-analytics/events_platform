import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// vite-plugin-vue-devtools touches localStorage as soon as it is imported while
// the config is loaded in Node. Node 22+ ships an experimental `localStorage`
// global that is present (so the plugin's `typeof localStorage !== 'undefined'`
// guard passes) but not functional, which crashes config load with
// "localStorage.getItem is not a function". We therefore import it lazily and
// only when localStorage genuinely works, so `npm run dev` runs on any Node
// version. Set DISABLE_DEVTOOLS=1 to force it off regardless.
async function optionalDevtools() {
  if (process.env.DISABLE_DEVTOOLS) return []
  try {
    if (typeof localStorage !== 'undefined') localStorage.getItem('__probe__')
  } catch {
    console.warn('[vite] Vue devtools disabled: localStorage unavailable in this Node runtime.')
    return []
  }
  const { default: vueDevTools } = await import('vite-plugin-vue-devtools')
  return [vueDevTools()]
}

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: [
    vue(),
    ...(await optionalDevtools()),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
}))
