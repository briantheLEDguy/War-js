import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { buildCapitalProps, CAPITAL_HOUSE_PROFILES, capitalPropPlacement } from '../scripts/unreal/capital-props';

describe('authored capital prop placement', () => {
  it('restores all 36 authored rowhouses without losing the other capital identities', () => {
    const map = JSON.parse(readFileSync(new URL('../public/assets/maps/aegis_capital.json', import.meta.url), 'utf8'));
    const result = buildCapitalProps(map);
    expect(result.objects).toHaveLength(1880);
    expect(result.housePlacements).toHaveLength(145);
    for (const profile of ['aegis_rowhouse_1', 'aegis_rowhouse_2']) {
      const actual = result.housePlacements.filter(row => row.profileKey === profile);
      expect(actual).toHaveLength(18);
      expect(actual.every(row => row.colliders.length > 0 && row.source.model === `prop_${profile}.glb`)).toBe(true);
    }
  });
  it('retains every identity while admitting only explicit house and rowhouse variants', () => {
    const props = [...CAPITAL_HOUSE_PROFILES.map((profile, index) => ({ id: `house-${index}`, kind: profile,
      assetKey: profile, x: 0, z: 0, rotY: 0 })),
      { id: 'pending-building', kind: 'other', x: 0, z: 0, rotY: 0 },
      { id: 'technical-collision', kind: 'water-collider', x: 0, z: 0, rotY: 0, visible: false }];
    const map = { id: 'aegis_capital', size: 4, cityElevation: { segments: 1, heights: [0, 0, 0, 0] }, props };
    const result = buildCapitalProps(map);
    expect(result.objects.map(row => row.source)).toEqual(props);
    expect(result.housePlacements.map(row => row.profileKey)).toEqual(CAPITAL_HOUSE_PROFILES);
    expect(result.capitalReady).toBe(false);
    expect(() => buildCapitalProps({ ...map, props: [...props, props[0]] })).toThrow('duplicate');
  });
  it('converts asymmetric FBX points through the source world transform', () => {
    for (const yaw of [0, Math.PI / 2, Math.PI, 0.37]) {
      const prop = { id: 'house', kind: 'house', x: 7, z: 11, y: 2, rotY: yaw, scaleX: 2, scaleY: 3, scaleZ: 4 };
      const result = capitalPropPlacement(prop, 5);
      const sourcePoint = { x: 1.25, y: 2.5, z: -3.75 };
      const raw = [sourcePoint.x * 100, sourcePoint.z * 100, sourcePoint.y * 100];
      const angle = result.yawDegrees * Math.PI / 180;
      const x = raw[0] * result.scale[0], y = raw[1] * result.scale[1];
      expect(result.position.X + x * Math.cos(angle) - y * Math.sin(angle)).toBeCloseTo(
        (prop.z - sourcePoint.x * 2 * Math.sin(yaw) + sourcePoint.z * 4 * Math.cos(yaw)) * 100);
      expect(result.position.Y + x * Math.sin(angle) + y * Math.cos(angle)).toBeCloseTo(
        (prop.x + sourcePoint.x * 2 * Math.cos(yaw) + sourcePoint.z * 4 * Math.sin(yaw)) * 100);
      expect(result.position.Z + raw[2] * result.scale[2]).toBeCloseTo((7 + sourcePoint.y * 3) * 100);
    }
  });
  it('retains legacy versus model collision yaw and absolute placement', () => {
    const prop = { id: 'house', kind: 'house', x: 0, z: 0, y: 10, rotY: Math.PI / 2,
      heightMode: 'absolute' as const, colliders: [{ x: 2, z: 3, width: 4, depth: 6, minY: -1, maxY: 5 }] };
    const legacy = capitalPropPlacement(prop, 99), model = capitalPropPlacement({ ...prop, colliderSpace: 'model' }, 99);
    expect(legacy.position.Z).toBe(1000);
    expect(legacy.colliders[0].center.X).toBeCloseTo(200);
    expect(model.colliders[0].center.X).toBeCloseTo(-200);
    expect(legacy.colliders[0].yawDegrees).toBe(-90);
    expect(model.colliders[0].yawDegrees).toBe(90);
    expect(model.colliders[0].halfSize).toEqual([300, 200, 300]);
  });
  it('rejects unsupported transforms rather than dropping them', () => {
    const prop = { id: 'house', kind: 'house', x: 0, z: 0, rotY: 0 };
    expect(() => capitalPropPlacement({ ...prop, rotX: 1 }, 0)).toThrow('supported');
    expect(() => capitalPropPlacement({ ...prop, scale: 0 }, 0)).toThrow('scale');
    expect(() => capitalPropPlacement({ ...prop, x: NaN }, 0)).toThrow('finite');
    expect(() => capitalPropPlacement({ ...prop, colliders: [{ width: 2, depth: 2 }] }, 0)).toThrow('bounds');
  });
});
