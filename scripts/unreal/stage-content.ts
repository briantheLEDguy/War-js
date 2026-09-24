import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { canonicalJson, sha256 } from './content-contract';

interface StagedContent {
  source: { sha256: string };
  maps: Array<{ id: string; definition: unknown }>;
  developmentMaps: Array<{ id: string; definition: unknown }>;
}

interface WorldVisualCatalog {
  schemaVersion: number;
  sourceContentSha256: string;
  productionAccepted: boolean;
  bindings: Array<{
    purpose: string; zone: string; entity: string; visualProp: string;
    sourceModel: string; sourceSha256: string; mesh: string;
    materials: string[]; collision: string; reviewState: string;
  }>;
  packageHashes: Record<string, string>;
}

const digest = /^[a-f0-9]{64}$/;
const identity = /^(?!none$)[a-z0-9_]+$/;
const packagePath = /^\/Game\/(?:[A-Za-z0-9_]+\/)*[A-Za-z0-9_]+$/;

/** Preserve reviewed bindings across unrelated gameplay exports; never approve new assets. */
export async function reconcileWorldVisuals(catalog: WorldVisualCatalog, previous: StagedContent,
  next: StagedContent, root: string): Promise<WorldVisualCatalog> {
  if (catalog.schemaVersion !== 1 || catalog.productionAccepted !== false
    || !digest.test(catalog.sourceContentSha256) || !digest.test(next.source.sha256)
    || catalog.sourceContentSha256 !== previous.source.sha256
    || !Array.isArray(catalog.bindings) || !catalog.packageHashes || typeof catalog.packageHashes !== 'object') {
    throw new Error('World visual catalog is stale or malformed. Reconcile its reviewed source revision before staging.');
  }
  const maps = (content: StagedContent) => new Map([...content.maps, ...content.developmentMaps].map(row => [row.id, row.definition]));
  const oldMaps = maps(previous), newMaps = maps(next);
  const seen = new Set<string>();
  const checkedSources = new Map<string, string>();
  for (const row of catalog.bindings) {
    const key = `${row.purpose}:${row.zone}:${row.entity}`;
    if (!['resource', 'scenery', 'training_dummy'].includes(row.purpose) || row.reviewState !== 'development'
      || ![row.zone, row.entity, row.visualProp].every(value => typeof value === 'string' && identity.test(value))
      || seen.has(key) || !/^[A-Za-z0-9_-]+\.glb$/.test(row.sourceModel) || !digest.test(row.sourceSha256)
      || !Array.isArray(row.materials) || !row.materials.length || !row.collision) {
      throw new Error(`Invalid reviewed world visual binding: ${key}`);
    }
    seen.add(key);
    if (!oldMaps.has(row.zone) || !newMaps.has(row.zone)
      || canonicalJson(oldMaps.get(row.zone)) !== canonicalJson(newMaps.get(row.zone))) {
      throw new Error(`World visual source map changed: ${row.zone}. Review its bindings before staging.`);
    }
    if (!checkedSources.has(row.sourceModel)) {
      checkedSources.set(row.sourceModel, sha256(await readFile(path.join(root, 'public/assets/models', row.sourceModel))));
    }
    if (checkedSources.get(row.sourceModel) !== row.sourceSha256) {
      throw new Error(`Reviewed world visual source changed: ${row.sourceModel}`);
    }
    for (const asset of [row.mesh, ...row.materials]) {
      const [packageName, objectName, extra] = typeof asset === 'string' ? asset.split('.') : [];
      if (!packageName || !packagePath.test(packageName) || objectName !== packageName.split('/').at(-1)
        || extra !== undefined || !digest.test(catalog.packageHashes[packageName] ?? '')) {
        throw new Error(`World visual asset lacks a reviewed package hash: ${asset}`);
      }
    }
  }
  for (const [packageName, expected] of Object.entries(catalog.packageHashes)) {
    if (!packagePath.test(packageName) || !digest.test(expected)) throw new Error(`Invalid reviewed package: ${packageName}`);
    const filename = path.join(root, 'unreal/AegisWar/Content', `${packageName.slice('/Game/'.length)}.uasset`);
    if (sha256(await readFile(filename)) !== expected) throw new Error(`Reviewed native world visual package changed: ${packageName}`);
  }
  return { ...catalog, sourceContentSha256: next.source.sha256 };
}

export async function stageDevelopmentContent(content: StagedContent, root: string): Promise<void> {
  const directory = path.join(root, 'unreal/AegisWar/Content/Migration');
  const contentPath = path.join(directory, 'content.json');
  const worldPath = path.join(directory, 'world-visuals.json');
  const worldJson = await readFile(worldPath, 'utf8').catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'ENOENT') return null;
    throw error;
  });
  const world = worldJson === null ? null : await reconcileWorldVisuals(JSON.parse(worldJson),
    JSON.parse(await readFile(contentPath, 'utf8')), content, root);
  // Validate the entire installed catalog before replacing either live file. Runtime
  // revision matching stays fail-closed if the process is interrupted between writes.
  await mkdir(directory, { recursive: true });
  if (world) await writeFile(worldPath, canonicalJson(world));
  await writeFile(contentPath, canonicalJson(content));
  await writeFile(path.join(directory, 'DEVELOPMENT_ONLY.txt'), 'Unverified migration data. This is not release approval or a complete Unreal world.\n');
}
