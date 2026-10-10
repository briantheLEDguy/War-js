import {expect,it} from 'vitest';
import {readFileSync} from 'node:fs';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';
import {redesignT1} from '../scripts/unreal/t1-layouts';
import {battlefieldLandscape} from '../scripts/unreal/t1-battlefield-landscape';
import {sourceTerrainSurface,protectSurfaceGrounding} from '../scripts/unreal/t1-source-surface';
import type {TerrainSurface} from '../shared/terrainSurface';
import {createOrvrGridHeightSampler} from '../shared/orvrTerrain';
for(const id of ['sunmeadow_march','cinderfen_outskirts'])it('retains '+id+' identities, full-width grades and native ground on a synthetic absolute landform',()=>{
 const original=battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/'+id+'.json','utf8')) as ZoneDefinition));
 const b=original.spatial!.bounds,grid=original.spatial!.terrainGrid;
 const surface:TerrainSurface={bounds:b,segmentsX:grid.segmentsX,segmentsZ:grid.segmentsZ,edgeFade:30,
 samples:Array.from({length:(grid.segmentsX+1)*(grid.segmentsZ+1)},(_,i)=>80+40*Math.sin(i%(grid.segmentsX+1)/grid.segmentsX*Math.PI))};
 const copy=structuredClone(original),r=sourceTerrainSurface(original,surface),z=r.zone;
 expect(original).toEqual(copy);expect(z.orvrLayout!.keeps).toEqual(original.orvrLayout!.keeps);expect(z.orvrLayout!.stagingCamps).toEqual(original.orvrLayout!.stagingCamps);
 expect(z.paths).toEqual(original.paths);expect(z.zoneTriggers).toEqual(original.zoneTriggers);expect(z.spawnPoint).toEqual(original.spawnPoint);
 expect(Math.max(...r.grades.map(g=>g.maximumGrade))).toBeLessThan(.22);
 const before=createOrvrGridHeightSampler(original.orvrLayout!.terrain,original.size,original.segments,original.spatial),after=createOrvrGridHeightSampler(z.orvrLayout!.terrain,z.size,z.segments,z.spatial);
 const keep=original.orvrLayout!.keeps[0];expect(after(keep.x,keep.z)).toBe(before(keep.x,keep.z));expect(z.orvrLayout!.terrain.naturalField!.surface!.samples).not.toEqual(surface.samples);
 expect(r.nativeBuilt||r.appearanceApproved||r.drivingAccepted).toBe(false);
 expect(()=>sourceTerrainSurface(z,surface)).toThrow('Preserve existing');
 expect(()=>protectSurfaceGrounding(original,surface,10)).toThrow('bounded explicit grounding');
});
it('refuses other regions or missing explicit terrain',()=>{
 expect(()=>sourceTerrainSurface({id:'brightfen_approach'} as ZoneDefinition,{} as TerrainSurface)).toThrow('explicit first-pair');
});

it('retains population approaches away from roads and rejects invalid support geometry',()=>{
 const original=battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json','utf8')) as ZoneDefinition));
 const b=original.spatial!.bounds,g=original.spatial!.terrainGrid;
 const surface:TerrainSurface={bounds:b,segmentsX:g.segmentsX,segmentsZ:g.segmentsZ,edgeFade:30,samples:Array((g.segmentsX+1)*(g.segmentsZ+1)).fill(120)};
 const support=[{id:'retained_resource_approach',width:4,points:[{x:500,z:80},{x:510,z:120}]}],copy=structuredClone(support);
 const result=sourceTerrainSurface(original,surface,40,support),before=createOrvrGridHeightSampler(original.orvrLayout!.terrain,original.size,original.segments,original.spatial),after=createOrvrGridHeightSampler(result.zone.orvrLayout!.terrain,result.zone.size,result.zone.segments,result.zone.spatial);
 expect(after(504,100)).toBe(before(504,100));expect(result.supportGrades).toHaveLength(1);expect(support).toEqual(copy);
 for(const bad of [{...support[0],width:1},{...support[0],points:[{x:500,z:80},{x:900,z:120}]},{...support[0],points:[{x:NaN,z:80},{x:510,z:120}]}])expect(()=>sourceTerrainSurface(original,surface,40,[bad])).toThrow('Invalid retained surface support');
});
