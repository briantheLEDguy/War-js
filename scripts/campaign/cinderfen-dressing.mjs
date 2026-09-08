import { readFileSync } from 'node:fs';
import { WORLD_LIFE_FOOTPRINTS } from './world-life-source.mjs';
import { reviewedSceneryModelBounds } from './aegis-reviewed-scenery.mjs';

// Neutral carpentry from the reviewed city kit suits the fen's trading village.
// Regional signs, lighting, benches and hearths await their own authored package.
export const CINDERFEN_DRESSING = Object.freeze({
  life_crate_stack: { key: 'aegis_crate_stack', height: 1.55 },
  life_barrels: { key: 'aegis_barrel_cluster', height: 1.2 },
  life_handcart: { key: 'aegis_handcart', height: 1.45 },
  life_clothesline: { key: 'aegis_washing_line', height: 2.3 },
  life_planter: { key: 'aegis_planter', height: 1.05 },
});
const keys = new Set(Object.values(CINDERFEN_DRESSING).map(entry => entry.key));
export const isCinderfenFurniture = prop => Boolean(WORLD_LIFE_FOOTPRINTS[prop.kind]) || keys.has(prop.kind);
const registry = JSON.parse(readFileSync(new URL('../../public/assets/models/asset-index.json', import.meta.url), 'utf8'));

export function fitCinderfenDressing(zone) {
  if (zone.id !== 'cinderfen_outskirts') return;
  for (const prop of zone.props) {
    if (!prop.id?.startsWith(`${zone.id}_life_`) || prop.assetKey || prop.model) continue;
    const replacement = CINDERFEN_DRESSING[prop.kind];
    if (!replacement) continue;
    const asset = registry.staticProps[replacement.key];
    if (!asset?.runtimeReady || asset.approvalState !== 'approved') continue;
    const bounds = reviewedSceneryModelBounds(asset.model);
    if (!bounds) continue;
    const width = bounds.max.x - bounds.min.x, depth = bounds.max.z - bounds.min.z;
    const height = bounds.max.y - bounds.min.y;
    const radius = Math.hypot(Math.max(Math.abs(bounds.min.x), Math.abs(bounds.max.x)),
      Math.max(Math.abs(bounds.min.z), Math.abs(bounds.max.z)));
    const scale = Math.min(replacement.height / height, WORLD_LIFE_FOOTPRINTS[prop.kind] / radius);
    const oldScale = prop.scale ?? 1;
    prop.scale = oldScale * scale;
    prop.y = (prop.y ?? 0) - bounds.min.y * prop.scale;
    prop.kind = replacement.key;
    prop.assetKey = replacement.key;
    prop.colliderSpace = 'model';
    // Preserve nonblocking garden/cloth dressing; solid cargo uses its visible envelope.
    if (prop.colliders?.length) prop.colliders = [{
      x: (bounds.min.x + bounds.max.x) / 2, z: (bounds.min.z + bounds.max.z) / 2,
      width, depth, minY: bounds.min.y, maxY: bounds.max.y,
    }];
  }
}
