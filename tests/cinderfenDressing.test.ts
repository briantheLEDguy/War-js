import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
// @ts-expect-error Native ESM campaign authoring module.
import { fitCinderfenDressing } from '../scripts/campaign/cinderfen-dressing.mjs';
// @ts-expect-error Native ESM geometry survey module.
import { reviewedSceneryModelBounds } from '../scripts/campaign/aegis-reviewed-scenery.mjs';

describe('Cinderfen village cargo replacement', () => {
  test('preserves explicit models and gameplay records across repeated composition', () => {
    const zone = JSON.parse(readFileSync('public/assets/maps/cinderfen_outskirts.json', 'utf8')) as ZoneDefinition;
    zone.props.push({ id: `${zone.id}_life_custom_cargo`, kind: 'life_crate_stack', model: 'custom.glb', x: 1, z: 2 });
    const before = structuredClone(zone);
    fitCinderfenDressing(zone); fitCinderfenDressing(zone);
    expect(zone).toEqual(before);
  });

  test('places delivered cargo bottoms on the ground and collision around the visible meshes', () => {
    const zone = JSON.parse(readFileSync('public/assets/maps/cinderfen_outskirts.json', 'utf8')) as ZoneDefinition;
    const registry = JSON.parse(readFileSync('public/assets/models/asset-index.json', 'utf8'));
    const cargo = zone.props.filter(prop => prop.id?.startsWith(`${zone.id}_life_`)
      && ['aegis_crate_stack', 'aegis_barrel_cluster', 'aegis_handcart'].includes(prop.assetKey ?? ''));
    expect(cargo.length).toBeGreaterThanOrEqual(12);
    for (const prop of cargo) {
      const asset = registry.staticProps[prop.assetKey!];
      expect(asset.runtimeReady).toBe(true); expect(asset.approvalState).toBe('approved');
      const bounds = reviewedSceneryModelBounds(asset.model), scale = prop.scale ?? 1;
      expect((prop.y ?? 0) + bounds.min.y * scale, prop.id).toBeCloseTo(0, 6);
      const collider = prop.colliders![0];
      expect(collider.x! - collider.width / 2, prop.id).toBeCloseTo(bounds.min.x, 6);
      expect(collider.z! + collider.depth / 2, prop.id).toBeCloseTo(bounds.max.z, 6);
      expect(collider.maxY, prop.id).toBeCloseTo(bounds.max.y, 6);
    }
  });
});
