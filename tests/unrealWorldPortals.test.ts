import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CAMPAIGN_NODES } from '../shared/data/campaign.generated';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
import { outdoorTerrain, outdoorRoads, portalPlan, worldPoint, worldOrigins, terrainHeight, sourceHeight } from '../scripts/unreal/world-portals';
import { orvrHeightAt } from '../shared/orvrTerrain';

const maps = () => CAMPAIGN_NODES.map(node => JSON.parse(readFileSync(`public/assets/maps/${node.id}.json`, 'utf8')) as ZoneDefinition);
describe('native campaign world', () => {
  it('preserves all campaign routes and reciprocal native arrival coordinates', () => {
    const plan = portalPlan(maps());
    expect(plan.zones).toHaveLength(32);
    expect(plan.routes).toHaveLength(70);
    expect(plan.routes.filter(route => route.built)).toHaveLength(70);
    for (const route of plan.routes) {
      const reverse = plan.routes.find(candidate => candidate.id === route.reverseId)!;
      expect(reverse.targetZoneId).toBe(route.zoneId);
      expect(reverse.reverseId).toBe(route.id);
      if (route.built) expect(route.arrival?.every(Number.isFinite)).toBe(true);
      else expect(route.arrival).toBeNull();
    }
  });
  it('fails on broken routes, missing landing coordinates and duplicate identities', () => {
    let source = maps(); source[0].zoneTriggers![0].targetZoneId = 'missing';
    expect(() => portalPlan(source)).toThrow(/reverse/);
    source = maps(); source[0].zoneTriggers![0].targetSpawn = undefined;
    expect(() => portalPlan(source)).toThrow(/arrival/);
    source = maps(); source.push(source[0]);
    expect(() => portalPlan(source)).toThrow(/Duplicate zone/);
  });
  it('converts axes and applies each zone offset only once', () => {
    expect(worldPoint('brightfen_approach', { x: 4, y: 2, z: 3 })).toEqual([200300,400,200]);
    expect(() => worldPoint('missing', { x: 0, z: 0 })).toThrow(/Unknown zone/);
  });
  it('retains the source outdoor heightfield and valid upward normals', () => {
    const map = maps().find(map => map.id === 'brightfen_approach')!;
    const terrain = outdoorTerrain(map);
    expect(terrain.positions).toHaveLength((map.segments + 1) ** 2);
    for (let i = 0; i < terrain.positions.length; i += 123) {
      const [x,y,z] = terrain.positions[i];
      expect(z / 100).toBeCloseTo(orvrHeightAt(map.orvrLayout!.terrain,y / 100,x / 100),4);
      expect(terrain.normals[i][2]).toBeGreaterThan(0);
    }
    expect(terrain.indices).toHaveLength(map.segments * map.segments * 6);
  });
  it('keeps every zone footprint separate and makes the entire graph reachable', () => {
    const source = maps(), plan = portalPlan(source), reached = new Set(['aegis_capital']);
    for (let iteration = 0; iteration < source.length; iteration++)
      for (const route of plan.routes) if (reached.has(route.zoneId)) reached.add(route.targetZoneId);
    expect(reached.size).toBe(32);
    for (const [index,a] of source.entries()) for (const b of source.slice(index+1)) {
      const pa=worldOrigins[a.id], pb=worldOrigins[b.id];
      expect(Math.max(Math.abs(pa[0]-pb[0]), Math.abs(pa[1]-pb[1]))).toBeGreaterThan((a.size+b.size)*50);
    }
  });
  it('preserves the lair surface, and refuses to flatten either authored capital', () => {
    const source=maps(), lair=source.find(map=>map.id==='mireglass_den')!;
    const mesh=outdoorTerrain(lair);
    expect(mesh.positions.length).toBe((lair.segments+1)**2);
    expect(terrainHeight(lair,0,0)).toBeCloseTo(sourceHeight(lair,0,0));
    for (const id of ['aegis_capital','riftspire_capital']) expect(()=>outdoorTerrain(source.find(map=>map.id===id)!)).toThrow(/Unsupported/);
  });
  it('places source road ribbons directly above the exported ground triangles', () => {
    const map=maps().find(map=>map.id==='brightfen_approach')!, roads=outdoorRoads(map)!;
    expect(roads.indices.length).toBeGreaterThan(0);
    for (let i=0;i<roads.positions.length;i+=137) {
      const [x,y,z]=roads.positions[i];
      expect(z/100-terrainHeight(map,y/100,x/100)).toBeCloseTo(.045,3);
    }
  });
});
