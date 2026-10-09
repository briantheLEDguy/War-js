import { expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { terrainFieldHeight, validateTerrainField, type TerrainField } from '../shared/terrainField';
import { traceDrainage } from '../scripts/unreal/t1-drainage-trace';
import { drainageIncisions, drainageSeeds } from '../scripts/unreal/t1-drainage-incisions';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { battlefieldLandscape } from '../scripts/unreal/t1-battlefield-landscape';
import { landscapePockets } from '../scripts/unreal/t1-landscape-pockets';
import { localTerrainTransitions } from '../scripts/unreal/t1-local-terrain-transitions';
import { tacticalSpurs } from '../scripts/unreal/t1-tactical-spurs';
import { createOrvrGridHeightSampler } from '../shared/orvrTerrain';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';

const empty: TerrainField = { version:1, baseHeight:10, seed:1, rolls:[], ridges:[], channels:[] };
const cut = { id:'drain', points:[{x:-40,z:0,width:20,height:4},{x:40,z:0,width:20,height:8}] };
it('compact cuts preserve absent fields, have exact support and join without stacking', () => {
 const f={...empty,incisions:[cut]};validateTerrainField(f);
 expect(terrainFieldHeight(f,0,0)).toBe(4);
 expect(terrainFieldHeight({...f,incisions:[cut,{...cut,id:'branch'}]},0,0)).toBe(4);
 for(const p of [[0,20],[0,30],[-100,0],[100,0]]) expect(terrainFieldHeight(f,p[0],p[1])).toBe(terrainFieldHeight(empty,p[0],p[1]));
 for(const z of [-20,20]) expect(Math.abs(terrainFieldHeight(f,0,z-.001)-terrainFieldHeight(f,0,z+.001))).toBeLessThan(.00001);
 expect(terrainFieldHeight(JSON.parse(JSON.stringify(f)),7,-3)).toBe(terrainFieldHeight(f,7,-3));
});
it('compact incision validation rejects duplicate IDs, excessive controls and malformed points', () => {
 for(const incisions of [[cut,cut],Array.from({length:65},(_,i)=>({...cut,id:String(i)})),[{...cut,points:[{...cut.points[0],height:25},cut.points[1]]}],[{...cut,points:[{...cut.points[0],width:0},cut.points[1]]}]])
  expect(()=>validateTerrainField({...empty,incisions})).toThrow();
 expect(()=>validateTerrainField({...empty,channels:[cut],incisions:[cut]})).toThrow();
});
const seed={id:'course',x:0,z:0,width:20,depth:6,maximumLength:160};
it('bounded tracing follows descending terrain with tapered non-uphill controls and stable results', () => {
 const height=(x:number,z:number)=>100-x*.4+z*.03,inside=(x:number,z:number,r:number)=>Math.abs(x)+r<500&&Math.abs(z)+r<500;
 const before=structuredClone(seed),row=traceDrainage(seed,height,inside)!;expect(row).not.toBeNull();expect(seed).toEqual(before);expect(row).toEqual(traceDrainage(seed,height,inside));
 expect(row.points.length).toBeLessThanOrEqual(50);expect(row.length).toBeLessThanOrEqual(seed.maximumLength);expect(row.points[0].height).toBe(0);expect(row.points.at(-1)!.height).toBe(0);
 for(let i=1;i<row.points.length;i++){
  const a=row.points[i-1],b=row.points[i];expect(height(b.x,b.z)).toBeLessThan(height(a.x,a.z));
  expect(height(b.x,b.z)-b.height).toBeLessThanOrEqual(height(a.x,a.z)-a.height);
  expect(b.height).toBeLessThanOrEqual(seed.depth);expect(inside(b.x,b.z,seed.width*1.25)).toBe(true);
 }
});
it('tracing refuses flat/unsupported ground, invalid budgets and nonfinite samples', () => {
 expect(traceDrainage(seed,()=>1,()=>true)).toBeNull();expect(traceDrainage(seed,()=>1,()=>false)).toBeNull();
 expect(()=>traceDrainage({...seed,maximumLength:401},()=>1,()=>true)).toThrow('bounded');
 expect(()=>traceDrainage(seed,()=>NaN,()=>true)).toThrow('Nonfinite');
 expect(()=>traceDrainage(seed,(x)=>x===0?100:NaN,()=>true)).toThrow('Nonfinite');
});
for(const id of ['sunmeadow_march','cinderfen_outskirts']) it(id+' incisions retain gameplay routes, complete military assemblies and safe grades',()=>{
 const base=JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition;
 const pockets=landscapePockets(battlefieldLandscape(redesignT1(base)));
 const original=tacticalSpurs(localTerrainTransitions(pockets.zone).zone).zone,before=structuredClone(original),result=drainageIncisions(original),z=result.zone;
 expect(original).toEqual(before);expect(z.paths).toEqual(original.paths);
 for(const key of ['keeps','battlefieldObjectives','stagingCamps','caravanRoutes'] as const) expect(z.orvrLayout![key]).toEqual(original.orvrLayout![key]);
 expect(result.flowChecks.length).toBeGreaterThanOrEqual(3);expect(result.flowChecks.every(p=>p.maximumCentrelineRisePerMetre<=.35)).toBe(true);
 expect(Math.max(...result.grades.map(g=>g.maximumGrade))).toBeLessThanOrEqual(.22);
 const h=createOrvrGridHeightSampler(z.orvrLayout!.terrain,z.size,z.segments,z.spatial);
 for(const p of pockets.pockets)expect(h(p.x,p.z)).toBeCloseTo(p.bedY,2);
 expect(result.nativeBuilt).toBe(false);expect(result.appearanceApproved).toBe(false);
 expect(()=>drainageIncisions(z)).toThrow('Preserve existing');
});
it('drainage authoring refuses later batches',()=>expect(()=>drainageSeeds('brightfen_approach')).toThrow());
