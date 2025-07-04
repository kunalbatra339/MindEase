    import { defineConfig } from 'vite'
    import react from '@vitejs/plugin-react'

    // https://vitejs.dev/config/
    export default defineConfig({
      plugins: [react()],
      css: { // <-- ADD THIS BLOCK
        postcss: './postcss.config.js', // Explicitly tell Vite to use this PostCSS config
      },
      server: {
        port: 5177, // Keep this if you want to use 5177, otherwise remove for default 5173
        strictPort: true,
      }
    })
    