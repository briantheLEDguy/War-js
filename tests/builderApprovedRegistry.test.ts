import fs from 'node:fs';
import path from 'node:path';
import { webcrypto } from 'node:crypto';
import { afterEach, expect, it, vi } from 'vitest';
import { AssetLoader } from '../src/game/AssetLoader';
import { WORLD_EDITOR_PREFABS } from '../src/world/editor/PrefabCatalog';

afterEach(() => vi.unstubAllGlobals());

it('every reviewed GM entry resolves its actual on-disk approval and LOD records', async () => {
  const root = path.resolve('public');
  vi.stubGlobal('crypto', webcrypto);
  vi.stubGlobal('fetch', async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost');
    const filename = path.resolve(root, '.' + decodeURIComponent(url.pathname));
    if (!filename.startsWith(root + path.sep) || !fs.existsSync(filename)) return new Response(null, { status: 404 });
    return new Response(fs.readFileSync(filename));
  });
  const loader = new AssetLoader(), failed = [];
  for (const prefab of WORLD_EDITOR_PREFABS) {
    if (!prefab.assetKey || !prefab.assetCategory) continue;
    const models = await loader.resolveApprovedAssetModels(prefab.assetKey, prefab.assetCategory);
    if (models[0] !== prefab.model) failed.push({ kind: prefab.kind, models, expected: prefab.model });
  }
  loader.dispose();
  expect(failed).toEqual([]);
});
