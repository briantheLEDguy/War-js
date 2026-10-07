import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1, T1_REGIONS, validateT1 } from '../scripts/unreal/t1-layouts';
import { topologyDrawing } from '../scripts/unreal/t1-candidate';
import { terrainHeight, validateContentSeparation, worldOrigins } from '../scripts/unreal/world-portals';
import { containsSpatialPoint, resolveZoneSpatial, spatialSegmentInside } from '../shared/worldSpatial';
import { createOrvrGridHeightSampler } from '../shared/orvrTerrain';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';

const load = (id: string) => JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition;
describe('T1 landscape candidates', () => {
  for (const id of Object.keys(T1_REGIONS)) it(`${id} preserves identities and authors supported physical routes`, () => {
    const source = load(id), before = JSON.stringify(source), zone = redesignT1(source), layout = zone.orvrLayout!;
    expect(JSON.stringify(source)).toBe(before);
    for (const key of ['npcs', 'enemies', 'resourceNodes', 'craftingStations', 'rvrObjectives', 'zoneTriggers'] as const)
      expect(zone[key]?.map(row => row.id).sort()).toEqual(source[key]?.map(row => row.id).sort());
    for (const key of ['npcs', 'enemies', 'resourceNodes', 'craftingStations'] as const)
      for (const entity of zone[key] ?? []) expect(containsSpatialPoint(zone.spatial!, entity)).toBe(true);
    expect(layout.caravanRoutes.map(r => r.id)).toEqual(source.orvrLayout!.caravanRoutes.map(r => r.id));
    expect(layout.stagingCamps.every(c => !c.capturable)).toBe(true);
    expect(layout.terrain.chunks).toHaveLength(12);
    expect(zone.paths!.slice(0, 5).map(p => p.width)).toEqual([12, 12, 12, 12, 12]);
    const sampler = createOrvrGridHeightSampler(layout.terrain, zone.size, zone.segments, zone.spatial);
    for (const path of zone.paths!) for (let i = 1;i < path.points.length;i++) {
      const a = path.points[i - 1], b = path.points[i], distance = Math.hypot(b.x - a.x, b.z - a.z), steps = Math.ceil(distance / 2);
      for (const side of [-path.width / 2, 0, path.width / 2]) {
        let prior: number | undefined;
        for (let j = 0;j <= steps;j++) {
          const x = a.x + (b.x - a.x) * j / steps - (b.z - a.z) / distance * side, z = a.z + (b.z - a.z) * j / steps + (b.x - a.x) / distance * side, h = sampler(x, z);
          if (prior !== undefined) expect(Math.abs(h - prior) / (distance / steps)).toBeLessThan(.22);
          prior = h;
        }
      }
    }
    for (const path of zone.paths!.slice(0, 5)) for (let i = 1;i < path.points.length;i++) {
      const a = path.points[i - 1], b = path.points[i];
      expect(spatialSegmentInside(zone.spatial!, a, b, 9)).toBe(true);
      const distance = Math.hypot(b.x - a.x, b.z - a.z);
      expect(Math.abs((b.y ?? 0) - (a.y ?? 0)) / distance).toBeLessThan(.14);
      for (const t of [.1, .5, .9]) {
        const x = a.x + (b.x - a.x) * t, z = a.z + (b.z - a.z) * t;
        expect(sampler(x, z)).toBeCloseTo(terrainHeight(zone, x, z), 3);
      }
    }
    for (const keep of layout.keeps) {
      const original = source.orvrLayout!.keeps.find(k => k.objectiveId === keep.objectiveId)!;
      for (let i = 0;i < keep.gates.length;i++) {
        expect(keep.gates[i].x - keep.x).toBeCloseTo(original.gates[i].x - original.x);
        expect(keep.gates[i].z - keep.z).toBeCloseTo(original.gates[i].z - original.z);
        const prop = zone.props!.find(p => p.id === keep.gates[i].propId);
        const oldProp = source.props!.find(p => p.id === keep.gates[i].propId);
        expect(prop?.colliders).toEqual(oldProp?.colliders);
      }
      if (keep.postern) expect(keep.postern.inside.x - keep.x).toBeCloseTo(original.postern!.inside.x - original.x);
      expect(keep.commander.y).toBeCloseTo(terrainHeight(zone, keep.commander.x, keep.commander.z));
    }
    const capital = zone.zoneTriggers!.find(t => t.targetZoneId.endsWith('_capital'))!;
    expect(Math.hypot(capital.x - zone.spawnPoint!.x, capital.z - zone.spawnPoint!.z)).toBeLessThan(80);
    expect(containsSpatialPoint(zone.spatial!, capital.arrivalPoint!, 1)).toBe(true);
    expect(topologyDrawing(zone)).toContain('20 building target');
    expect(() => validateT1(zone)).not.toThrow();
  });
  it('keeps enlarged content envelopes separate and rejects conflicting origins', () => {
    const maps = Object.keys(T1_REGIONS).map(id => redesignT1(load(id)));
    expect(() => validateContentSeparation(maps)).not.toThrow();
    const old = worldOrigins.brightfen_approach;
    try { worldOrigins.brightfen_approach = worldOrigins.sunmeadow_march; expect(() => validateContentSeparation(maps)).toThrow('Overlapping'); }
    finally { worldOrigins.brightfen_approach = old; }
  });
});
describe('shared spatial contract', () => {
  const spatial = {
bounds: { minX: 0, maxX: 100, minZ: 0, maxZ: 60 }, terrainGrid: { segmentsX: 10, segmentsZ: 6 },
    playableOutline: [{ x: 0, z: 0 }, { x: 100, z: 0 }, { x: 100, z: 60 }, { x: 60, z: 60 }, { x: 60, z: 20 }, { x: 40, z: 20 }, { x: 40, z: 60 }, { x: 0, z: 60 }]
};
  it('rejects concave shortcuts whose endpoints are both on ground', () => {
    expect(containsSpatialPoint(spatial, { x: 20, z: 40 })).toBe(true);
    expect(containsSpatialPoint(spatial, { x: 80, z: 40 })).toBe(true);
    expect(spatialSegmentInside(spatial, { x: 20, z: 40 }, { x: 80, z: 40 })).toBe(false);
    expect(spatialSegmentInside(spatial, { x: 20, z: 10 }, { x: 80, z: 10 }, 9)).toBe(true);
    expect(spatialSegmentInside(spatial, { x: 20, z: 19 }, { x: 80, z: 19 }, 2)).toBe(false);
  });
  it('rejects malformed, crossing and nonfinite contracts', () => {
    expect(() => resolveZoneSpatial({ size: 100, segments: 10, spatial })).not.toThrow();
    expect(() => resolveZoneSpatial({ size: 100, segments: 10, spatial: { ...spatial, terrainGrid: { segmentsX: NaN, segmentsZ: 6 } } })).toThrow();
    expect(() => resolveZoneSpatial({ size: 100, segments: 10, spatial: { ...spatial, playableOutline: [{ x: 0, z: 0 }, { x: 100, z: 60 }, { x: 0, z: 60 }, { x: 100, z: 0 }] } })).toThrow();
  });
  it('retains legacy square boundaries', () => {
    const old = resolveZoneSpatial({ size: 800, segments: 32 });
    expect(old.bounds).toEqual({ minX: -400, maxX: 400, minZ: -400, maxZ: 400 });
    expect(old.terrainGrid).toEqual({ segmentsX: 32, segmentsZ: 32 });
  });
});
