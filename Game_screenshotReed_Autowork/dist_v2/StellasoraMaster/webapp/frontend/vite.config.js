import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// Build output will go to ../static so Flask can serve the files directly
export default defineConfig({
  plugins: [vue()],
  root: '.',
  base: '/',
  server: {
    // Proxy API requests during development to the Flask backend
    proxy: {
      '/capture': 'http://127.0.0.1:5000',
      '/tap': 'http://127.0.0.1:5000',
      '/start_game': 'http://127.0.0.1:5000',
      '/auto_recruit': 'http://127.0.0.1:5000',
      '/dailytasks': 'http://127.0.0.1:5000',
      '/logs': 'http://127.0.0.1:5000',
      '/config': 'http://127.0.0.1:5000'
    }
  },
  build: {
    outDir: path.resolve(__dirname, '../static'),
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'index.html')
    }
  }
})
