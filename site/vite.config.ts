import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Project Pages: https://cynacons.github.io/powerplan/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/powerplan/',
  build: {
    outDir: 'dist',
  },
})
