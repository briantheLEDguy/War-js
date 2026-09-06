import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Box3, Matrix4, Quaternion, Vector3 } from 'three';

const modelRoot = fileURLToPath(new URL('../../public/assets/models/', import.meta.url));
const measured = new Map();

// Existing primitive envelopes, measured around the original placement origin.
// Uniform fitting retains each replacement's carved/forged proportions while
// keeping it inside the space already reserved for the old scenery.
export const AEGIS_REVIEWED_SCENERY = Object.freeze({
  vendor_stall: { kind: 'aegis_stall', model: 'prop_aegis_stall.glb', envelope: [3, 1.9, 2.45] },
  statue: { kind: 'aegis_citadel_oath_statue', model: 'prop_aegis_citadel_oath_statue.glb', envelope: [1.9, 1.6, 4.4] },
  life_crate_stack: { kind: 'aegis_crate_stack', model: 'prop_aegis_crate_stack.glb', envelope: [1.8, 1.15, 1.55] },
  life_barrels: { kind: 'aegis_barrel_cluster', model: 'prop_aegis_barrel_cluster.glb', envelope: [1.6, 2, 1.05] },
  life_handcart: { kind: 'aegis_handcart', model: 'prop_aegis_handcart.glb', envelope: [1.8, 4.6, 1.6] },
  life_bench: { kind: 'aegis_civic_bench', model: 'prop_aegis_civic_bench.glb', envelope: [2.05, .72, 1.15] },
  life_lantern: { kind: 'aegis_civic_streetlight', model: 'prop_aegis_civic_streetlight.glb', envelope: [1.45, .6, 2.5] },
  life_signpost: { kind: 'aegis_civic_waymarker', model: 'prop_aegis_civic_waymarker.glb', envelope: [1.85, .4, 2.3] },
  life_planter: { kind: 'aegis_planter', model: 'prop_aegis_planter.glb', envelope: [1.5, .9, 1.2] },
  life_clothesline: { kind: 'aegis_washing_line', model: 'prop_aegis_washing_line.glb', envelope: [3.6, .7, 2.3] },
  // Delivery shelters keep the old tent footprint and collision, now with cloth awnings.
  life_supply_tent: { kind: 'aegis_awning_1', model: 'prop_aegis_awning_1.glb', envelope: [3.8, 3.5, 2.3] },
  life_campfire: { kind: 'aegis_fortress_brazier', model: 'prop_town_fortress_brazier.glb', assetKey: 'town_fortress_brazier', envelope: [1.7, 1.7, 1.15], singleLod: true },
  banner_post: { kind: 'aegis_fortress_banner', model: 'prop_town_fortress_banner.glb', assetKey: 'town_fortress_banner', envelope: [2.9, .8, 6.5], singleLod: true },
  rock: { kind: 'aegis_crate_stack', model: 'prop_aegis_crate_stack.glb', envelope: [1.6, 1.6, 1.6] },
  pnw_mossy_boulder: { kind: 'aegis_crate_stack', model: 'prop_aegis_crate_stack.glb', envelope: [2.2, 2.2, 1.8] },
  pnw_grass_clump: { kind: 'aegis_flowerbed_violets', model: 'prop_aegis_flowerbed_violets.glb', fit: .5 },
  pnw_wildflower_clump: { kind: 'aegis_flowerbed_violets', model: 'prop_aegis_flowerbed_violets.glb', fit: .5 },
  pnw_low_shrub: { kind: 'aegis_fountain', model: 'prop_aegis_fountain.glb', fit: .35 },
});

/** Read delivered GLB bounds including node transforms, without loading textures. */
export function reviewedSceneryModelBounds(model) {
  if (measured.has(model)) return measured.get(model).clone();
  let doc;
  try {
    const bytes = readFileSync(modelRoot + model);
    doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
  } catch {
    // Missing delivery assets leave the original primitive fallback available.
    return null;
  }
  const box = new Box3();
  const visit = (index, parent) => {
    const node = doc.nodes[index];
    const local = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
      new Vector3().fromArray(node.translation ?? [0, 0, 0]),
      new Quaternion().fromArray(node.rotation ?? [0, 0, 0, 1]),
      new Vector3().fromArray(node.scale ?? [1, 1, 1]));
    const world = parent.clone().multiply(local);
    for (const primitive of doc.meshes?.[node.mesh]?.primitives ?? []) {
      const position = doc.accessors[primitive.attributes.POSITION];
      if (position.min && position.max) box.union(new Box3(new Vector3().fromArray(position.min),
        new Vector3().fromArray(position.max)).applyMatrix4(world));
    }
    for (const child of node.children ?? []) visit(child, world);
  };
  for (const root of doc.scenes?.[doc.scene ?? 0]?.nodes ?? []) visit(root, new Matrix4());
  if (box.isEmpty()) return null;
  measured.set(model, box);
  return box.clone();
}

/** Reserve the actual visible envelope independently of gameplay collision. */
export function reviewedSceneryFootprint(prop) {
  if (!Object.values(AEGIS_REVIEWED_SCENERY).some(entry => entry.kind === prop.kind && entry.model === prop.model)) return null;
  const box = reviewedSceneryModelBounds(prop.model);
  if (!box) return null;
  const center = box.getCenter(new Vector3()), size = box.getSize(new Vector3());
  const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1), sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1), angle = -(prop.rotY ?? 0);
  return { x: prop.x + center.x * sx * Math.cos(angle) - center.z * sz * Math.sin(angle),
    z: prop.z + center.x * sx * Math.sin(angle) + center.z * sz * Math.cos(angle),
    width: size.x * sx, depth: size.z * sz, angle };
}

export function replaceAegisPrimitiveScenery(zone) {
  if (zone.id !== 'aegis_capital') return;
  for (const prop of zone.props) {
    const replacement = AEGIS_REVIEWED_SCENERY[prop.kind];
    // Explicit authored choices and invisible navigation/water geometry stay intact.
    if (!replacement || prop.visible === false || prop.model || prop.assetKey) continue;
    const bounds = reviewedSceneryModelBounds(replacement.model);
    if (!bounds) continue;
    const anchoredWidth = 2 * Math.max(Math.abs(bounds.min.x), Math.abs(bounds.max.x));
    const anchoredDepth = 2 * Math.max(Math.abs(bounds.min.z), Math.abs(bounds.max.z));
    const height = bounds.max.y - bounds.min.y;
    const fit = replacement.fit ?? Math.min(replacement.envelope[0] / anchoredWidth,
      replacement.envelope[1] / anchoredDepth, replacement.envelope[2] / height);
    const oldScale = prop.scale ?? 1;
    prop.scale = oldScale * fit;
    prop.y = (prop.y ?? 0) - bounds.min.y * prop.scale * (prop.scaleY ?? 1);
    // Rescale local physics inversely: every existing collider/walkable world
    // extent remains identical, including stacked-floor offsets and gate states.
    for (const collider of prop.colliders ?? []) {
      collider.width /= fit; collider.depth /= fit;
      if (collider.x !== undefined) collider.x /= fit;
      if (collider.z !== undefined) collider.z /= fit;
      if (collider.minY !== undefined) collider.minY = collider.minY / fit + bounds.min.y;
      if (collider.maxY !== undefined) collider.maxY = collider.maxY / fit + bounds.min.y;
    }
    for (const surface of prop.walkableSurfaces ?? []) {
      surface.width /= fit; surface.depth /= fit;
      if (surface.x !== undefined) surface.x /= fit;
      if (surface.z !== undefined) surface.z /= fit;
      surface.fromY = (surface.fromY ?? 0) / fit + bounds.min.y;
      surface.toY = (surface.toY ?? 0) / fit + bounds.min.y;
    }
    prop.kind = replacement.kind;
    prop.assetKey = replacement.assetKey ?? replacement.kind;
    prop.model = replacement.model;
    if (!replacement.singleLod) prop.lodModels = [1, 2].map(level => replacement.model.replace('.glb', `_lod${level}.glb`));
  }
  for (const node of zone.resourceNodes ?? []) {
    // The capital receives ore deliveries; extraction remains a field activity.
    if (node.kind === 'ore' && zone.props.some(prop => prop.id === node.visualPropId && prop.kind === 'aegis_crate_stack')) {
      node.label = 'Aegis Ore Shipment';
    }
  }
}
