import { mergeConfig } from 'vite';
import base from '../../../vite.config.ts';
// Keep a long city/model review stable while the authoring tools write previews.
export default mergeConfig(base, { server: { hmr: false, port: 5175, host: '127.0.0.1' } });
