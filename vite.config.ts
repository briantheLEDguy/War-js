import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { createHash } from 'node:crypto';
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import {
  BATTLE_PRELATE_DEVELOPMENT_REVISION,
  BATTLE_PRELATE_DEVELOPMENT_ROUTE,
  BATTLE_PRELATE_DEVELOPMENT_SHA256,
} from './src/config/developmentModelCandidates';

const BATTLE_PRELATE_DEVELOPMENT_ARTIFACT =
  'artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb';

const REVIEW_MODULES = [
  'arm_civic_humanoid_v2_battle_prelate_v1_head_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_shoulders_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_chest_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_hands_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_waist_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_legs_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_feet_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_back_m.glb',
  'arm_civic_humanoid_v2_battle_prelate_v1_tabard_m.glb',
] as const;

function streamModel(
  res: import('node:http').ServerResponse,
  candidates: string[],
): void {
  const model = candidates
    .map((candidate) => path.resolve(process.cwd(), candidate))
    .find(existsSync);
  if (!model) {
    res.statusCode = 404;
    res.end('Run the local body/armor pilot generator first.');
    return;
  }
  res.setHeader('Content-Type', 'model/gltf-binary');
  res.setHeader('Cache-Control', 'no-store');
  const stream = createReadStream(model);
  stream.on('error', () => {
    if (!res.headersSent) {
      res.statusCode = 500;
      res.end('The local review model could not be read.');
      return;
    }
    res.destroy();
  });
  res.on('close', () => stream.destroy());
  stream.pipe(res);
}

function streamPinnedDevelopmentModel(
  req: import('node:http').IncomingMessage,
  res: import('node:http').ServerResponse,
): void {
  const model = path.resolve(process.cwd(), BATTLE_PRELATE_DEVELOPMENT_ARTIFACT);
  if (!existsSync(model)) {
    res.statusCode = 404;
    res.end(`Generate the Battle Prelate ${BATTLE_PRELATE_DEVELOPMENT_REVISION} animation candidate first.`);
    return;
  }

  const actualSha256 = createHash('sha256').update(readFileSync(model)).digest('hex');
  if (actualSha256 !== BATTLE_PRELATE_DEVELOPMENT_SHA256) {
    res.statusCode = 409;
    res.end(
      `Battle Prelate ${BATTLE_PRELATE_DEVELOPMENT_REVISION} does not match the pinned development-review hash.`,
    );
    return;
  }

  const size = statSync(model).size;
  res.setHeader('Content-Type', 'model/gltf-binary');
  res.setHeader('Content-Length', String(size));
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-War-Asset-Lifecycle', 'development-review');
  res.setHeader('X-War-Model-Sha256', actualSha256);
  if (req.method === 'HEAD') {
    res.end();
    return;
  }

  const stream = createReadStream(model);
  stream.on('error', () => res.destroy());
  res.on('close', () => stream.destroy());
  stream.pipe(res);
}

function localModelReview(): Plugin {
  return {
    name: 'war-js-local-model-review',
    configureServer(server) {
      server.middlewares.use(BATTLE_PRELATE_DEVELOPMENT_ROUTE, (req, res) => {
        streamPinnedDevelopmentModel(req, res);
      });
      server.middlewares.use('/__model-review/battle-prelate-m.glb', (_req, res) => {
        streamModel(res, [
          'artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb',
          'artifacts/model-jobs/local-armor-pilot-v19/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb',
          'artifacts/model-jobs/local-armor-pilot-v18/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb',
          'artifacts/model-jobs/local-armor-pilot-v3/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb',
          'artifacts/model-jobs/local-armor-pilot-v2/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb',
          'artifacts/model-jobs/local-armor-pilot-v2/civic_humanoid_v2_m/battle_preplate_m_equipped_review.glb',
          'artifacts/model-jobs/local-armor-pilot/civic_humanoid_v2_m/battle_preplate_m_equipped_review.glb',
          'artifacts/model-jobs/local-armor-pilot/civic_humanoid_v2_m/equipped/battle_prelate_m_equipped_review.glb',
          'artifacts/model-jobs/local-pilot/civic_humanoid_v2_m/body_civic_humanoid_v2_m.glb',
        ]);
      });
      server.middlewares.use('/__model-review/body.glb', (_req, res) => {
        streamModel(res, [
          'artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/body/body_civic_humanoid_v2_m.glb',
          'artifacts/model-jobs/local-armor-pilot-v19/civic_humanoid_v2_m/body/body_civic_humanoid_v2_m.glb',
          'artifacts/model-jobs/body-roundtrip-final/civic_m/body_civic_humanoid_v2_m.glb',
          'artifacts/model-jobs/local-pilot/civic_humanoid_v2_m/body_civic_humanoid_v2_m.glb',
        ]);
      });
      server.middlewares.use('/__model-review/modules', (req, res) => {
        let fileName = '';
        try {
          fileName = decodeURIComponent((req.url ?? '').split('?')[0]).replace(/^\/+/, '');
        } catch {
          res.statusCode = 400;
          res.end('Malformed review module path.');
          return;
        }
        if (!REVIEW_MODULES.includes(fileName as (typeof REVIEW_MODULES)[number])) {
          res.statusCode = 404;
          res.end('Unknown review module.');
          return;
        }
        streamModel(res, [
          `artifacts/model-jobs/local-armor-pilot-v18/civic_humanoid_v2_m/modules/${fileName}`,
          `artifacts/model-jobs/local-armor-pilot-v3/civic_humanoid_v2_m/modules/${fileName}`,
          `artifacts/model-jobs/local-armor-pilot-v2/civic_humanoid_v2_m/modules/${fileName}`,
          `artifacts/model-jobs/local-armor-pilot/civic_humanoid_v2_m/modules/${fileName}`,
        ]);
      });
      server.middlewares.use('/__model-review/weapon.glb', (_req, res) => {
        streamModel(res, [
          'artifacts/model-jobs/weapon-attachment-pilot/run_20260711t141724438z/battle_prelate_hammer/wep_civic_battle_prelate_dawn_maul_draft.glb',
        ]);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), localModelReview()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    target: 'es2022',
    sourcemap: true,
  },
});
