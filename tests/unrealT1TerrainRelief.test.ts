import { expect,it } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { battlefieldLandscape } from '../scripts/unreal/t1-battlefield-landscape';
import { landscapePockets } from '../scripts/unreal/t1-landscape-pockets';
import { localTerrainTransitions } from '../scripts/unreal/t1-local-terrain-transitions';
import { tacticalSpurs } from '../scripts/unreal/t1-tactical-spurs';
import { sampleTerrainRelief,validateTerrainRelief,type TerrainRelief } from '../shared/terrainRelief';
import { terrainFieldHeight,validateTerrainField,type TerrainField } from '../shared/terrainField';
import { createOrvrGridHeightSampler } from '../shared/orvrTerrain';

const relief: TerrainRelief={bounds:{minX:-100,maxX:100,minZ:-50,maxZ:50},segmentsX:2,segmentsZ:1,samples:[0,10,20,20,30,40],edgeFade:10,ridgeMaskHeight:40};
it('rectangular row-major relief interpolates exact interior vertices and bilinear heights',()=>{
 validateTerrainRelief(relief);expect(sampleTerrainRelief(relief,0,0)).toBe(20);expect(sampleTerrainRelief(relief,-50,0)).toBe(15);expect(sampleTerrainRelief(relief,50,25)).toBe(30);
 expect(sampleTerrainRelief(JSON.parse(JSON.stringify(relief)),17,-8)).toBe(sampleTerrainRelief(relief,17,-8));
});
it('compact relief has zero support outside and smooth envelope transitions',()=>{
 for(const [x,z] of [[-100,0],[100,0],[0,-50],[0,50],[101,0],[0,51],[NaN,0],[0,Infinity]])expect(sampleTerrainRelief(relief,x,z)).toBe(0);
 expect(Math.abs(sampleTerrainRelief(relief,-100+.0001,0))).toBeLessThan(1e-8);
 expect(Math.abs(sampleTerrainRelief(relief,-90-.0001,0)-sampleTerrainRelief(relief,-90+.0001,0))).toBeLessThan(.0001);
});
it('relief rejects missing coverage, invalid extents, budgets and nonfinite heights',()=>{
 for(const value of [{...relief,bounds:{...relief.bounds,minX:100}},{...relief,segmentsX:513},{...relief,segmentsZ:1.5},
  {...relief,samples:[1,2]},{...relief,samples:Array(6)},{...relief,samples:[0,10,20,20,30,NaN]},{...relief,samples:[0,10,20,20,30,41]},
  {...relief,edgeFade:0},{...relief,edgeFade:51},{...relief,ridgeMaskHeight:9}])expect(()=>validateTerrainRelief(value)).toThrow('bounded terrain relief');
});
const field:TerrainField={version:1,baseHeight:4,seed:2,rolls:[],ridges:[],channels:[]};
it('relief remains absent on legacy fields and suppresses detail in lowlands',()=>{
 expect(terrainFieldHeight(field,0,0)).toBe(4);expect(terrainFieldHeight({...field,relief},0,0)).toBe(4);
 const ridge={id:'crest',profile:'rounded' as const,points:[{x:-40,z:0,width:30,height:20},{x:40,z:0,width:30,height:20}]};
 const f={...field,ridges:[ridge],relief};validateTerrainField(f);expect(terrainFieldHeight(f,0,0)).toBe(34);
 expect(terrainFieldHeight({...f,ridges:[{...ridge,points:ridge.points.map(p=>({...p,height:80}))}]},0,0)).toBe(104);
 expect(()=>validateTerrainField({...field,relief:{...relief,samples:[]}})).toThrow();
});
it('native grid and shared authority use the same float vertices and triangle diagonal with relief',()=>{
 const f={...field,ridges:[{id:'crest',profile:'rounded' as const,points:[{x:-100,z:0,width:100,height:60},{x:100,z:0,width:100,height:60}]}],relief:{...relief,samples:[0,10,30,20,-10,40]}};
 const spatial={bounds:{minX:-60,maxX:60,minZ:-30,maxZ:30},playableOutline:[{x:-60,z:-30},{x:60,z:-30},{x:60,z:30},{x:-60,z:30}],terrainGrid:{segmentsX:3,segmentsZ:2}};
 const terrain={sourceVersion:'relief-test',naturalField:f,landforms:[],flattenAreas:[],clearCorridors:[]};const sample=createOrvrGridHeightSampler(terrain,120,3,spatial);
 const h=(x:number,z:number)=>Math.fround(terrainFieldHeight(f,x,z));
 expect(sample(-40,-15)).toBeCloseTo((h(-20,-30)+h(-60,0))/2,5);
 expect(sample(-30,-6)).toBeCloseTo(h(-20,0)+.25*(h(-60,0)-h(-20,0))+.2*(h(-20,-30)-h(-20,0)),5);
 expect(sample(-50,-24)).toBeCloseTo(h(-60,-30)+.25*(h(-20,-30)-h(-60,-30))+.2*(h(-60,0)-h(-60,-30)),5);
});
import { protectReliefGrounding,sourceTerrainRelief } from '../scripts/unreal/t1-source-relief';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
it('detail protection includes paths without grading corridors and leaves inputs untouched',()=>{
 const r:TerrainRelief={bounds:{minX:-100,maxX:100,minZ:-100,maxZ:100},segmentsX:20,segmentsZ:20,samples:Array(441).fill(8),edgeFade:5,ridgeMaskHeight:40};
 const zone={id:'sunmeadow_march',spatial:{bounds:r.bounds,terrainGrid:{segmentsX:20,segmentsZ:20}},paths:[{width:4,points:[{x:-90,z:0},{x:90,z:0}]}],orvrLayout:{caravanRoutes:[],terrain:{clearCorridors:[],flattenAreas:[]}}} as unknown as ZoneDefinition;
 const before=structuredClone(r),zBefore=structuredClone(zone),p=protectReliefGrounding(zone,r);
 expect(r).toEqual(before);expect(zone).toEqual(zBefore);expect(p.samples).not.toBe(r.samples);
 expect(sampleTerrainRelief(p,0,0)).toBe(0);expect(sampleTerrainRelief(p,0,20)).toBe(0);
 expect(sampleTerrainRelief(p,0,40)).toBeCloseTo(8*.72*.72*(3-2*.72),8);expect(sampleTerrainRelief(p,80,80)).toBe(8);
 expect(()=>protectReliefGrounding({} as ZoneDefinition,r)).toThrow('explicit grounding');
});
it('source relief refuses later batches and existing derivations',()=>{
 expect(()=>sourceTerrainRelief({id:'brightfen_approach'} as ZoneDefinition,relief)).toThrow('first-pair');
 const z={id:'sunmeadow_march',spatial:{},paths:[],orvrLayout:{terrain:{naturalField:{relief}}}} as unknown as ZoneDefinition;
 expect(()=>sourceTerrainRelief(z,relief)).toThrow('Preserve existing');
});

for(const id of ['sunmeadow_march','cinderfen_outskirts'])it(id+' admits synthetic relief with retained full-width routes and anchors',()=>{
 const base=JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition;
 const original=tacticalSpurs(localTerrainTransitions(landscapePockets(battlefieldLandscape(redesignT1(base))).zone).zone).zone,before=structuredClone(original);
 const r:TerrainRelief={bounds:original.spatial!.bounds,segmentsX:128,segmentsZ:128,samples:Array(129*129).fill(4),edgeFade:30,ridgeMaskHeight:40};
 const result=sourceTerrainRelief(original,r),zone=result.zone;
 expect(original).toEqual(before);expect(zone.paths).toEqual(original.paths);
 for(const key of ['keeps','battlefieldObjectives','stagingCamps','caravanRoutes'] as const)expect(zone.orvrLayout![key]).toEqual(original.orvrLayout![key]);
 expect(Math.max(...result.grades.map(g=>g.maximumGrade))).toBeLessThan(.22);
 const old=createOrvrGridHeightSampler(original.orvrLayout!.terrain,original.size,original.segments,original.spatial);
 const next=createOrvrGridHeightSampler(zone.orvrLayout!.terrain,zone.size,zone.segments,zone.spatial);
 const b=zone.spatial!.bounds;let changed=0;
 for(let x=b.minX+50;x<b.maxX-50;x+=50)for(let z=b.minZ+50;z<b.maxZ-50;z+=50)if(Math.abs(next(x,z)-old(x,z))>.5)changed++;
 expect(changed).toBeGreaterThan(20);expect(result.nativeBuilt).toBe(false);expect(result.drivingAccepted).toBe(false);
 expect(()=>sourceTerrainRelief(zone,r)).toThrow('Preserve existing');
});
