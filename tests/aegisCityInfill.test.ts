import fs from 'node:fs';
import { describe, expect, test } from 'vitest';
import { addAegisCityInfill, infillFootprint, infillPositionClear } from '../scripts/campaign/aegis-city-infill.mjs';
import { cityHeightAt } from '../src/world/CityElevation';
import { cityPositionBlocked } from '../src/world/CityNavigation';
import { propCollidersFromObject } from '../src/world/editor/WorldEditorRuntime';
import { prefabDefinitionForKind } from '../src/world/editor/PrefabCatalog';
import type { WorldPropObject } from '../src/services/types';
import type { PropSpawn, ZoneDefinition } from '../src/world/ZoneLoader';

type Expansion = {version: string; houses: number; trees: number; flowerbeds: number;
  districtCounts: Record<string, {houses: number; trees: number; flowerbeds: number}>};
const zone = JSON.parse(fs.readFileSync('public/assets/maps/aegis_capital.json', 'utf8')) as ZoneDefinition & {cityExpansion: Expansion};
const infill = zone.props.filter(p => p.id?.startsWith('aegis_infill_'));
const ground = (x: number, z: number) => cityHeightAt(zone.cityElevation!, zone.size, x, z);
const definition = (p: PropSpawn): WorldPropObject => ({ ...p, id: p.id!, type: 'prop', createdAt: 0, updatedAt: 0,
  transform: { position: { x: p.x, y: ground(p.x,p.z) + (p.y ?? 0), z: p.z }, rotation: { x: 0, y: p.rotY ?? 0, z: 0 },
    scale: { x: (p.scale ?? 1)*(p.scaleX ?? 1), y: (p.scale ?? 1)*(p.scaleY ?? 1), z: (p.scale ?? 1)*(p.scaleZ ?? 1) } } });
const newColliders = infill.flatMap(p => propCollidersFromObject(definition(p)));

describe('Aegis garden and housing infill', () => {
  test('adds substantial houses, trees and flowerbeds across all five existing districts', () => {
    expect(zone.cityExpansion.houses).toBeGreaterThanOrEqual(20);
    expect(zone.cityExpansion.trees).toBeGreaterThanOrEqual(50);
    expect(zone.cityExpansion.flowerbeds).toBeGreaterThanOrEqual(75);
    expect(infill).toHaveLength(zone.cityExpansion.houses + zone.cityExpansion.trees + zone.cityExpansion.flowerbeds);
    expect(new Set(infill.map(p => p.id)).size).toBe(infill.length);
    expect(Object.keys(zone.cityExpansion.districtCounts).sort()).toEqual(zone.cityDistricts!.map(d => d.id).sort());
    for (const counts of Object.values(zone.cityExpansion.districtCounts)) {
      expect(counts.houses).toBeGreaterThanOrEqual(2);
      expect(counts.trees).toBeGreaterThanOrEqual(5);
      expect(counts.flowerbeds).toBeGreaterThanOrEqual(6);
    }
    const houses = infill.filter(p => /house/.test(p.kind));
    expect(new Set(houses.map(p => p.kind)).size).toBeGreaterThanOrEqual(6);
    expect(new Set(houses.map(p => p.scale)).size).toBeGreaterThanOrEqual(3);
    expect(new Set(infill.filter(p => /garden_/.test(p.kind)).map(p => p.rotY)).size).toBeGreaterThan(20);
    for (const kind of ['garden_linden', 'garden_cypress', 'flowerbed_roses', 'flowerbed_violets'])
      expect(infill.filter(p => p.kind === `aegis_${kind}`).length).toBeGreaterThanOrEqual(15);
  });

  test('preserves full envelopes, canal margins, standing spaces and existing street widths', () => {
    for (const p of infill) expect(infillPositionClear(zone,p), `${p.id} placement clearance`).toBe(true);
    for (const path of zone.paths!) for (let i = 1; i < path.points.length; i++) {
      const a = path.points[i-1], b = path.points[i], length = Math.hypot(b.x-a.x,b.z-a.z);
      if (!length) continue;
      const normal = {x:-(b.z-a.z)/length,z:(b.x-a.x)/length};
      for (let step = 0; step <= Math.ceil(length); step++) {
        const t = Math.min(1,step/length);
        for (const side of [-1,0,1]) {
          const x = a.x+(b.x-a.x)*t+normal.x*side*path.width/2;
          const z = a.z+(b.z-a.z)*t+normal.z*side*path.width/2;
          expect(cityPositionBlocked({x,z,y:ground(x,z)+.1},newColliders,.5), `${path.id} ${x}/${z}`).toBe(false);
        }
      }
    }
    for (const p of [zone.spawnPoint, ...zone.npcs!, ...zone.craftingStations!, ...zone.resourceNodes!])
      expect(cityPositionBlocked({x:p.x,z:p.z,y:ground(p.x,p.z)+.1},newColliders,2), `standing place ${p.x}/${p.z}`).toBe(false);
  });

  test('places every house and raised bed on its existing level foundation', () => {
    for (const p of infill.filter(p => !p.kind.includes('garden_'))) {
      const box = infillFootprint(p), base = ground(p.x,p.z), cos = Math.cos(box.angle), sin = Math.sin(box.angle);
      for (const x of [-box.width/2,0,box.width/2]) for (const z of [-box.depth/2,0,box.depth/2]) {
        const y = ground(p.x+x*cos-z*sin,p.z+x*sin+z*cos);
        expect(Math.abs(y-base), `${p.id} foundation corner`).toBeLessThanOrEqual(.046);
      }
      expect(p.y ?? 0).toBe(0);
    }
    for (const p of infill.filter(p => /house/.test(p.kind))) {
      const box = infillFootprint(p), distance = box.depth/2+1;
      const x = p.x-Math.sin(box.angle)*distance, z = p.z+Math.cos(box.angle)*distance;
      expect(cityPositionBlocked({x,z,y:ground(x,z)+.1},newColliders,.65), `${p.id} clear frontage`).toBe(false);
    }
  });

  test('retains clear 18-versus-18 courtyard staging and the whole citadel enclosure', () => {
    expect(zone.cityBattlefield!.playersPerTeam).toBe(18);
    for (const points of Object.values(zone.cityBattlefield!.staging)) {
      expect(points).toHaveLength(18);
      for (const p of points) expect(cityPositionBlocked({...p,y:42},newColliders,1)).toBe(false);
    }
    for (const p of infill) {
      const box = infillFootprint(p), radius = Math.hypot(box.width,box.depth)/2;
      if (p.z+radius > 125) expect(Math.abs(p.x)-radius, `${p.id} military buffer`).toBeGreaterThanOrEqual(98);
      expect(p.z+radius).toBeLessThanOrEqual(238);
    }
  });

  test('respects native model-space and legacy rotated collider offsets', () => {
    const candidate = {id:'candidate',kind:'aegis_flowerbed_roses',x:8,z:0,scale:1,rotY:0};
    const fixture = {spawnPoint:{x:100,z:100},npcs:[],enemies:[],craftingStations:[],resourceNodes:[],explorationPlaces:[],
      rvrObjectives:[],zoneTriggers:[],canals:[],paths:[] as Array<{width:number;points:Array<{x:number;z:number}>}>,props:[{id:'wall',kind:'wall',x:5,z:0,rotY:Math.PI/2,colliderSpace:'model' as 'model' | undefined,
        colliders:[{z:3,width:1,depth:1,minY:0,maxY:3}]}]};
    expect(infillPositionClear(fixture,candidate)).toBe(false);
    fixture.props[0].colliderSpace=undefined;
    expect(infillPositionClear(fixture,candidate)).toBe(true);
    fixture.paths=[{width:6,points:[{x:0,z:-10},{x:10,z:10}]}];
    expect(infillPositionClear(fixture,candidate)).toBe(false);
  });

  test('regeneration is deterministic and does not move existing people, terrain or scenery', () => {
    const copy = structuredClone(zone), originalProps = zone.props.filter(p => !p.id?.startsWith('aegis_infill_'));
    addAegisCityInfill(copy);
    expect(copy.cityExpansion).toEqual(zone.cityExpansion);
    expect(copy.props.filter(p => p.id?.startsWith('aegis_infill_'))).toEqual(infill);
    expect(copy.props.filter(p => !p.id?.startsWith('aegis_infill_'))).toEqual(originalProps);
    expect(copy.npcs).toEqual(zone.npcs);
    expect(copy.paths).toEqual(zone.paths);
    expect(copy.cityElevation).toEqual(zone.cityElevation);
    const rift = {id:'riftspire_capital',props:[{id:'existing'}]}, before = structuredClone(rift);
    addAegisCityInfill(rift); expect(rift).toEqual(before);
  }, 20_000);

  test('retains original life-scenery clearance after fitting a smaller reviewed model', () => {
    const candidate = {id:'candidate',kind:'aegis_flowerbed_roses',x:3.2,z:0,scale:1,rotY:0};
    const fixture = {id:'aegis_capital',spawnPoint:{x:100,z:100},paths:[],props:[{
      id:'aegis_capital_life_supplies_1',kind:'aegis_crate_stack',model:'prop_aegis_crate_stack.glb',
      x:0,z:0,scale:.01,rotY:0,
    }]};
    expect(infillPositionClear(fixture,candidate)).toBe(false);
    fixture.props[0].id='ordinary-small-crate';
    expect(infillPositionClear(fixture,candidate)).toBe(true);
  });

  test('all added scenery retains reviewed LOD assets and GM placement definitions', () => {
    for (const kind of new Set(infill.map(p => p.kind))) {
      const prefab = prefabDefinitionForKind(kind)!;
      expect(prefab,kind).toBeDefined();
      expect(prefab.assetKey).toBe(kind);
      expect(prefab.lodModels).toHaveLength(2);
      for (const model of [prefab.model,...prefab.lodModels!]) {
        expect(fs.existsSync(`public/assets/models/${model}`),model).toBe(true);
        const qc = JSON.parse(fs.readFileSync(`public/assets/models/${model!.replace('.glb','.qc.json')}`,'utf8'));
        expect(qc.qcPassed).toBe(true);
      }
    }
  });
});
