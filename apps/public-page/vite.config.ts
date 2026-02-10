import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { nxViteTsPaths } from '@nx/vite/plugins/nx-tsconfig-paths.plugin';
import { resolve } from 'path';

export default defineConfig({
  root: __dirname,
  cacheDir: '../../node_modules/.vite/apps/public-page',

  plugins: [react(), nxViteTsPaths()],

  resolve: {
    alias: {
      '@shared-ui': resolve(__dirname, '../../libs/shared-ui/src'),
    },
  },

  server: {
    port: 4200,
    host: 'localhost',
  },

  preview: {
    port: 4300,
    host: 'localhost',
  },

  build: {
    outDir: '../../dist/apps/public-page',
    emptyOutDir: true,
    reportCompressedSize: true,
  },
});
