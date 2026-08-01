import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/ws': { target: 'ws://localhost:8000', ws: true },
      '/api': { target: 'http://localhost:8000' },
      '/stl': {
        target: 'http://127.0.0.1:8765',
        rewrite: (path) => path.replace(/^\/stl/, ''),
      },
    },
  },
});
