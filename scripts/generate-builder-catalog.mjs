import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Box3, Matrix4, Quaternion, Vector3 } from 'three';

const root = fileURLToPath(new URL('../', import.meta.url));
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const title = name => name.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const clean = value => value?.map(({ id, interactionId, ...rest }) => rest);
const modelDocuments = new Map();

function modelDocument(model) {
  if (modelDocuments.has(model)) return modelDocuments.get(model);
  const fd = fs.openSync(path.join(root, 'public/assets/models', model), 'r');
  try {
    const header = Buffer.alloc(20);
    fs.readSync(fd, header, 0, 20, 0);
    if (header.toString('utf8', 0, 4) !== 'glTF') throw new Error('Model is not a materialized GLB');
    const bytes = Buffer.alloc(header.readUInt32LE(12));
    if (fs.readSync(fd, bytes, 0, bytes.length, 20) !== bytes.length) throw new Error('Incomplete model metadata');
    const document = JSON.parse(bytes.toString('utf8'));
    modelDocuments.set(model, document);
    return document;
  } finally { fs.closeSync(fd); }
}

function reviewedLods(asset) {
  if (!asset?.model) return [];
  let qc;
  try { qc = read(`public/assets/models/${asset.qc}`); } catch { /* Legacy reviewed assets may only record their base model. */ }
  const records = qc?.builtLods ?? qc?.lods;
  if (Array.isArray(records)) {
    const base = records.findIndex(item => item.model === asset.model);
    return records.slice(Math.max(0, base) + 1).map(item => item.model)
      .filter(model => typeof model === 'string' && fs.existsSync(path.join(root, 'public/assets/models', model)));
  }
  return [1, 2].map(lod => asset.model.replace(/(?:_lod0)?\.glb$/, `_lod${lod}.glb`))
    .filter(model => fs.existsSync(path.join(root, 'public/assets/models', model)));
}

function assetAnimation(model) {
  try {
    const gltf = modelDocument(model);
    return gltf.animations?.some(clip => clip.name === 'idle') ? 'idle' : undefined;
  } catch { return undefined; }
}

function builderMetadata() {
  const metadata = {};
  for (const directory of fs.readdirSync(path.join(root, 'authoring/blender'), { withFileTypes: true })) {
    if (!directory.isDirectory()) continue;
    const filename = path.join(root, 'authoring/blender', directory.name, 'builder-metadata.json');
    if (!fs.existsSync(filename)) continue;
    const source = JSON.parse(fs.readFileSync(filename, 'utf8'));
    for (const [key, value] of Object.entries(source.assets ?? {})) metadata[key] = value;
  }
  return metadata;
}

function modelBounds(model) {
  if (!model) return undefined;
  try {
    const gltf = modelDocument(model);
    const bounds = new Box3();
    const visit = (index, parent) => {
      const node = gltf.nodes[index];
      const matrix = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
        new Vector3().fromArray(node.translation ?? [0, 0, 0]),
        new Quaternion().fromArray(node.rotation ?? [0, 0, 0, 1]), new Vector3().fromArray(node.scale ?? [1, 1, 1]));
      matrix.premultiply(parent);
      for (const primitive of gltf.meshes?.[node.mesh]?.primitives ?? []) {
        const accessor = gltf.accessors[primitive.attributes.POSITION];
        if (accessor.min && accessor.max) bounds.union(new Box3(new Vector3().fromArray(accessor.min), new Vector3().fromArray(accessor.max)).applyMatrix4(matrix));
      }
      for (const child of node.children ?? []) visit(child, matrix);
    };
    for (const index of gltf.scenes[gltf.scene ?? 0].nodes) visit(index, new Matrix4());
    if (bounds.isEmpty()) return undefined;
    return bounds;
  } catch { return undefined; } // Missing or LFS-only files retain usable fallback footprints.
}

function modelFootprint(model) {
  const size = modelBounds(model)?.getSize(new Vector3());
  return size ? { width: Math.max(.1, Number(size.x.toFixed(3))), depth: Math.max(.1, Number(size.z.toFixed(3))), chainAxis: size.x > size.z ? 'x' : 'z' } : undefined;
}

/** Generate reusable defaults from authored local geometry, never world positions or IDs. */
export function generateBuilderCatalog() {
  modelDocuments.clear();
  const index = read('public/assets/models/asset-index.json');
  const registry = index.staticProps;
  const metadata = builderMetadata();
  const names = new Map(fs.readdirSync(path.join(root, 'scripts/blender-character-pipeline/data/asset-blueprints'))
    .filter(file => file.endsWith('.asset.json')).map(file => {
      const blueprint = read(`scripts/blender-character-pipeline/data/asset-blueprints/${file}`);
      return [blueprint.assetId, blueprint.displayName];
    }));
  for (const file of fs.readdirSync(path.join(root, 'scripts/blender-character-pipeline/data/approved-assets')).filter(file => file.endsWith('.approved.json'))) {
    const approved = read(`scripts/blender-character-pipeline/data/approved-assets/${file}`);
    if (approved.displayName) names.set(approved.assetId, approved.displayName);
  }
  const props = fs.readdirSync(path.join(root, 'public/assets/maps')).filter(f => f.endsWith('.json')).sort()
    .flatMap(file => read(`public/assets/maps/${file}`).props ?? []).filter(p => p.visible !== false);
  const entries = new Map();
  for (const p of props) {
    const key = JSON.stringify([p.kind, p.model, p.assetKey, p.interaction?.type, p.interaction?.interiorVariant]);
    const candidates = entries.get(key) ?? [];
    candidates.push(p);
    entries.set(key, candidates);
  }
  const used = new Set();
  const result = [];
  for (const candidates of entries.values()) {
    // Prefer an unscaled source instance; local collision dimensions already precede scale.
    candidates.sort((a, b) => Math.abs((a.scale ?? 1) - 1) - Math.abs((b.scale ?? 1) - 1));
    const p = candidates[0];
    let kind = p.kind;
    if (used.has(kind)) kind += `__${result.filter(e => e.sourceKind === p.kind).length + 1}`;
    used.add(kind);
    const colliders = clean(p.colliders);
    const walkableSurfaces = clean(p.walkableSurfaces);
    const shapes = [...colliders ?? [], ...walkableSurfaces ?? []];
    const width = Math.max(1, ...shapes.map(s => s.width + 2 * Math.abs(s.x ?? 0)));
    const depth = Math.max(1, ...shapes.map(s => s.depth + 2 * Math.abs(s.z ?? 0)));
    const { id, ...interaction } = p.interaction ?? {};
    result.push({ kind, sourceKind: p.kind, label: title(p.kind) + (kind !== p.kind ? ` (${p.interaction?.interiorVariant ?? p.model ?? 'variant'})` : ''),
      group: p.kind.startsWith('riftspire_') ? 'Riftspire City' : p.kind.startsWith('aegis_') ? 'Aegis City' : p.kind.startsWith('pnw_') ? 'Nature' : 'World Scenery',
      model: p.model, assetKey: p.assetKey, fallbackKind: p.kind,
      lodModels: p.lodModels, footprint: modelFootprint(p.model) ?? { width, depth, chainAxis: width > depth ? 'x' : 'z' },
      ...(p.colliderSpace ? { colliderSpace: p.colliderSpace } : {}),
      colliders, walkableSurfaces, cameraSolid: Boolean(colliders?.length),
      interaction: p.interaction ? interaction : undefined });
  }
  for (const [key, asset] of Object.entries(registry)) {
    if (!asset.runtimeReady || result.some(e => e.assetKey === key)) continue;
    // The spare room module shares the fourth residence shell, including its
    // doorway and floor. Keep it usable when placed independently by the GM.
    const roomSource = key === 'riftspire_room' ? result.find(e => e.kind === 'riftspire_house_4') : undefined;
    result.push({ kind: used.has(key) ? `${key}__asset` : key, label: title(key),
      group: key.startsWith('riftspire_') ? 'Riftspire City' : key.startsWith('aegis_') ? 'Aegis City' : 'Registered Assets',
      model: asset.model, assetKey: key, fallbackKind: key,
      ...(roomSource ? { colliderSpace: roomSource.colliderSpace, colliders: roomSource.colliders, walkableSurfaces: roomSource.walkableSurfaces } : {}),
      lodModels: reviewedLods(asset),
      footprint: modelFootprint(asset.model) ?? { width: 4, depth: 4, chainAxis: 'z' } });
  }
  for (const [key, asset] of Object.entries(index.characterProfiles ?? {})) {
    if (!asset.runtimeReady) continue;
    result.push({ kind: `character__${key}`, label: names.get(asset.assetId) ?? title(key), group: key.startsWith('enemy_') ? 'Enemies' : 'Characters and NPCs',
      model: asset.model, assetKey: key, assetCategory: 'characterProfiles', defaultAnimation: 'idle',
      lodModels: reviewedLods(asset), footprint: modelFootprint(asset.model) ?? { width: 1, depth: 1, chainAxis: 'z' } });
  }
  for (const entry of result) {
    const asset = (entry.assetCategory === 'characterProfiles' ? index.characterProfiles : registry)[entry.assetKey];
    if (!asset?.runtimeReady) continue;
    entry.model ??= asset.model;
    entry.footprint = modelFootprint(entry.model) ?? entry.footprint;
    entry.label = names.get(asset.assetId) ?? entry.label;
    if (entry.assetKey?.startsWith('frontier_')) {
      entry.assetCategory ??= 'staticProps';
      entry.group = /terrain/.test(entry.assetKey) ? 'Frontier Terrain' : /roe_deer|hare|fox|skylark|wolf|horse/.test(entry.assetKey) ? 'Frontier Wildlife'
        : /oak|ash$|hawthorn|wheat|meadow$|limestone/.test(entry.assetKey) ? 'Frontier Nature'
          : /wagon|ram|oil|catapult/.test(entry.assetKey) ? 'Frontier Siege and Supplies' : 'Frontier Buildings';
      entry.lodModels = reviewedLods(asset);
      entry.defaultAnimation = assetAnimation(asset.model);
      if (entry.group === 'Frontier Terrain') {
        const center = modelBounds(asset.model)?.getCenter(new Vector3());
        if (center) {
          entry.modelOffset = { x: -center.x || 0, y: 0, z: -center.z || 0 };
          entry.groundSurface = 'mesh';
          entry.cameraSolid = true;
        }
      }
    }
    const defaults = metadata[entry.assetKey];
    if (defaults?.runtimeReady === true && defaults.modelSha256 === asset.modelSha256) {
      // Measured package defaults may describe placement, never override registry identity/approval.
      for (const field of ['label', 'group', 'footprint', 'defaultScale', 'colliderSpace', 'colliders', 'walkableSurfaces', 'cameraSolid', 'interaction', 'defaultAnimation', 'modelOffset', 'groundSurface']) {
        if (defaults[field] !== undefined) entry[field] = structuredClone(defaults[field]);
      }
    }
  }
  // Include procedurally scattered nature and road pieces absent from serialized map props.
  const fallbackSource = fs.readFileSync(path.join(root, 'src/world/Props.ts'), 'utf8');
  for (const match of fallbackSource.matchAll(/case '(\w+)':/g)) {
    const kind = match[1];
    if (result.some(e => e.kind === kind)) continue;
    result.push({ kind, label: title(kind), group: kind.startsWith('pnw_') ? 'Nature' : 'World Scenery',
      fallbackKind: kind, footprint: { width: 1, depth: 1, chainAxis: 'z' } });
  }
  return result.sort((a, b) => a.kind.localeCompare(b.kind));
}

export function writeBuilderCatalog() {
  const catalog = generateBuilderCatalog();
  fs.writeFileSync(path.join(root, 'src/world/editor/prefabs.generated.json'), `${JSON.stringify(catalog, null, 2)}\n`);
  return catalog.length;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const output = `${JSON.stringify(generateBuilderCatalog(), null, 2)}\n`;
  const target = path.join(root, 'src/world/editor/prefabs.generated.json');
  if (process.argv.includes('--check')) {
    if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8').replaceAll('\r\n', '\n') !== output) {
      throw new Error('GM catalog is stale. Run npm run builder:generate.');
    }
  } else fs.writeFileSync(target, output);
  console.log(`GM catalog: ${JSON.parse(output).length} generated scenery definitions.`);
}
