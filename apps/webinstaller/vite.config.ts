import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { nxViteTsPaths } from '@nx/vite/plugins/nx-tsconfig-paths.plugin';
import { resolve } from 'path';

export default defineConfig({
  root: __dirname,
  cacheDir: '../../node_modules/.vite/apps/webinstaller',

  plugins: [react(), nxViteTsPaths()],

  resolve: {
    alias: {
      '@shared-ui': resolve(__dirname, '../../libs/shared-ui/src'),
    },
  },

  server: {
    port: 4201,
    host: 'localhost',
    proxy: {
      '/api': {
        target: 'https://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  preview: {
    port: 4301,
    host: 'localhost',
  },

  build: {
    outDir: '../../dist/apps/webinstaller',
    emptyOutDir: true,
    reportCompressedSize: true,
  },
});
