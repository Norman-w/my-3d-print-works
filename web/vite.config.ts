import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiPort = process.env.SP_API_PORT ?? '8000';
const stlPort = process.env.SP_STL_PORT ?? '8765';
const webPort = Number(process.env.SP_WEB_PORT ?? '5173');
/** 板子 LAN 地址；改 IP 后重启 dev（与 Live 页「设备」一致） */
const deviceHost = process.env.SP_DEVICE_HOST ?? '192.168.7.90';

export default defineConfig({
  plugins: [react()],
  server: {
    port: webPort,
    strictPort: true,
    proxy: {
      '/ws': { target: `ws://127.0.0.1:${apiPort}`, ws: true },
      '/api': { target: `http://127.0.0.1:${apiPort}` },
      '/stl': {
        target: `http://127.0.0.1:${stlPort}`,
        rewrite: (path) => path.replace(/^\/stl/, ''),
      },
      '/device': {
        target: `http://${deviceHost}`,
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/device/, ''),
      },
    },
  },
});
