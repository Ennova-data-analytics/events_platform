import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Kept apart from vite.config.js, which loads the devtools plugin lazily.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.js'],
    setupFiles: ['src/test/setup.js'],
    // Vuetify ships untranspiled CSS imports; let Vite handle them.
    server: { deps: { inline: ['vuetify'] } },
    restoreMocks: true,
  },
})
