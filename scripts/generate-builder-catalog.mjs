import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Box3, Matrix4, Quaternion, Vector3 } from 'three';

const root = fileURLToPath(new URL('../', import.meta.url));
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const title = name => name.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const clean = value => value?.map(({ id, interactionId, ...rest }) => rest);

function modelFootprint(model) {
  if (!model) return undefined;
  try {
    const bytes = fs.readFileSync(path.join(root, 'public/assets/models', model));
    if (bytes.toString('utf8', 0, 4) !== 'glTF') return undefined;
    const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
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
    const size = bounds.getSize(new Vector3());
    return { width: Math.max(.1, Number(size.x.toFixed(3))), depth: Math.max(.1, Number(size.z.toFixed(3))), chainAxis: size.x > size.z ? 'x' : 'z' };
  } catch { return undefined; } // Missing or LFS-only files retain usable fallback footprints.
}

/** Generate reusable defaults from authored local geometry, never world positions or IDs. */
export function generateBuilderCatalog() {
  const registry = read('public/assets/models/asset-index.json').staticProps;
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
      group: p.kind.startsWith('aegis_') ? 'Aegis City' : p.kind.startsWith('pnw_') ? 'Nature' : 'World Scenery',
      model: p.model, assetKey: p.assetKey, fallbackKind: p.kind,
      lodModels: p.lodModels, footprint: modelFootprint(p.model) ?? { width, depth, chainAxis: width > depth ? 'x' : 'z' },
      ...(p.colliderSpace ? { colliderSpace: p.colliderSpace } : {}),
      colliders, walkableSurfaces, cameraSolid: Boolean(colliders?.length),
      interaction: p.interaction ? interaction : undefined });
  }
  for (const [key, asset] of Object.entries(registry)) {
    if (!asset.runtimeReady || result.some(e => e.assetKey === key)) continue;
    result.push({ kind: used.has(key) ? `${key}__asset` : key, label: title(key),
      group: key.startsWith('aegis_') ? 'Aegis City' : 'Registered Assets',
      model: asset.model, assetKey: key, fallbackKind: key,
      lodModels: [1, 2].map(lod => asset.model.replace('.glb', `_lod${lod}.glb`)).filter(model => fs.existsSync(path.join(root, 'public/assets/models', model))),
      footprint: modelFootprint(asset.model) ?? { width: 4, depth: 4, chainAxis: 'z' } });
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
