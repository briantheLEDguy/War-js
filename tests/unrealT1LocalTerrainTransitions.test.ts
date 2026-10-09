import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { battlefieldLandscape } from '../scripts/unreal/t1-battlefield-landscape';
import { localTerrainTransitions } from '../scripts/unreal/t1-local-terrain-transitions';
import { createOrvrGridHeightSampler } from '../shared/orvrTerrain';

for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) it(id + ' exposes more flank relief while preserving routes and military identities', () => {
  const original = battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/' + id + '.json', 'utf8')) as ZoneDefinition));
  const before = structuredClone(original), result = localTerrainTransitions(original), z = result.zone;
  expect(original).toEqual(before);
  expect(z.paths).toEqual(original.paths); expect(z.orvrLayout!.keeps).toEqual(original.orvrLayout!.keeps);
  expect(z.orvrLayout!.battlefieldObjectives).toEqual(original.orvrLayout!.battlefieldObjectives);
  expect(z.orvrLayout!.stagingCamps).toEqual(original.orvrLayout!.stagingCamps);
  expect(z.orvrLayout!.caravanRoutes).toEqual(original.orvrLayout!.caravanRoutes);
  expect(result.changes.length).toBeGreaterThan(5);expect(Math.max(...result.grades.map(g=>g.maximumGrade))).toBeLessThanOrEqual(.22);
  const oldHeight=createOrvrGridHeightSampler(original.orvrLayout!.terrain,original.size,original.segments,original.spatial);
  const height=createOrvrGridHeightSampler(z.orvrLayout!.terrain,z.size,z.segments,z.spatial);
  let changed=0;
  for(let x=-450;x<=450;x+=20)for(let z0=-400;z0<=300;z0+=20) if(Math.abs(height(x,z0)-oldHeight(x,z0))>1)changed++;
  expect(changed).toBeGreaterThan(70);expect(result.nativeBuilt).toBe(false);expect(result.appearanceApproved).toBe(false);
});
it('rejects later regions and absent grading contracts',()=>{
 const source=redesignT1(JSON.parse(readFileSync('public/assets/maps/brightfen_approach.json','utf8')) as ZoneDefinition);
 expect(()=>localTerrainTransitions(source)).toThrow();
 expect(()=>localTerrainTransitions({...source,id:'sunmeadow_march'})).toThrow();
});
