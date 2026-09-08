import { readFileSync, readdirSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import { mapFeature, mapFeatureRole, mapFeatureVisible, zoneMapFeatures } from '../src/ui/hud/zoneMapGeometry';
import { applyZonePaths } from '../src/world/PathKit';
import type { ZoneDefinition } from '../src/world/ZoneLoader';

const load = (name: string) => JSON.parse(readFileSync(`public/assets/maps/${name}.json`, 'utf8')) as ZoneDefinition;

describe('automatic zone map geometry', () => {
  test('projects collider footprints with local offsets, rotation and combined scales', () => {
    const feature = mapFeature({ kind: 'aegis_house_1', x: 100, z: 50, rotY: Math.PI / 2, scale: 2, scaleX: 3, scaleZ: 0.5,
      colliders: [{ x: 2, z: 3, width: 10, depth: 4 }] });
    expect(feature.width).toBe(60);
    expect(feature.depth).toBe(4);
    expect(feature.center.x).toBeCloseTo(103);
    expect(feature.center.z).toBeCloseTo(38);
    expect(feature.corners[0].x).toBeCloseTo(101);
    expect(feature.corners[0].z).toBeCloseTo(68);
  });

  test('shows buildings and streets while suppressing collision helpers and street dressing', () => {
    const prop = { x: 0, z: 0 };
    expect(mapFeatureRole({ ...prop, kind: 'city_water_collision' })).toBe('hidden');
    expect(mapFeatureRole({ ...prop, kind: 'aegis_house_1', visible: false })).toBe('hidden');
    expect(mapFeatureRole({ ...prop, kind: 'aegis_civic_wall_lantern' })).toBe('detail');
    expect(mapFeatureRole({ ...prop, kind: 'riftspire_chain' })).toBe('detail');
    expect(mapFeatureRole({ ...prop, kind: 'riftspire_deck' })).toBe('ground');
    expect(mapFeatureRole({ ...prop, kind: 'new_custom_asset', colliders: [{ width: 20, depth: 10 }] })).toBe('building');
    const detail = mapFeature({ ...prop, kind: 'aegis_barrel_cluster' });
    expect(mapFeatureVisible(detail, 0.5)).toBe(false);
    expect(mapFeatureVisible(detail, 2)).toBe(true);
  });

  test.each(['aegis_capital', 'riftspire_capital'])('keeps %s readable without a hand-authored map', name => {
    const zone = applyZonePaths(load(name));
    const features = zoneMapFeatures(zone);
    expect(features.filter(f => f.role !== 'ground' && mapFeatureVisible(f, 0.5)).length).toBeLessThan(zone.props.length / 2);
    expect(features.some(f => f.role === 'building' && f.prop.kind.includes('house'))).toBe(true);
    expect(features.every(f => !f.prop.kind.startsWith('path_'))).toBe(true);
    expect(features.every(f => f.prop.visible !== false)).toBe(true);
  });

  test('derives finite geometry for every checked-in zone, including optional lairs', () => {
    const files = readdirSync('public/assets/maps').filter(file => file.endsWith('.json'));
    expect(files.length).toBeGreaterThan(30);
    for (const file of files) {
      const zone = applyZonePaths(load(file.replace('.json', '')));
      for (const feature of zoneMapFeatures(zone)) {
        expect(feature.width, `${file}: ${feature.prop.id}`).toBeGreaterThan(0);
        expect(feature.depth, `${file}: ${feature.prop.id}`).toBeGreaterThan(0);
        expect(feature.corners.every(p => Number.isFinite(p.x) && Number.isFinite(p.z))).toBe(true);
      }
    }
  });
});
