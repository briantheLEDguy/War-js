import { fileURLToPath } from 'node:url';
import { defineConfig, normalizePath } from 'vite';
import react from '@vitejs/plugin-react';
// @ts-expect-error The local review server is a Node-only ESM module.
import { localRosterReviewPlugin } from './scripts/blender-character-pipeline/tools/local-roster-review-plugin.mjs';

const projectDirectory = normalizePath(fileURLToPath(new URL('.', import.meta.url)));

export default defineConfig({
  plugins: [react(), localRosterReviewPlugin()],
  server: {
    port: 5173,
    host: true,
    // Blender can lock working files while saving; only runtime assets need HMR.
    watch: { ignored: [`${projectDirectory}authoring/**`, `${projectDirectory}blends/**`] },
  },
  build: {
    target: 'es2022',
    sourcemap: true,
  },
});
