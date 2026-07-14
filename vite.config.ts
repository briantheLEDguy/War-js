import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// @ts-expect-error The local review server is a Node-only ESM module.
import { localRosterReviewPlugin } from './scripts/blender-character-pipeline/tools/local-roster-review-plugin.mjs';

export default defineConfig({
  plugins: [react(), localRosterReviewPlugin()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    target: 'es2022',
    sourcemap: true,
  },
});
