import {it,expect} from 'vitest';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';
import {extendTerrainOwnership,distantMountainBounds,validateDistantMountains} from '../scripts/unreal/t1-distant-scenery';
const source=()=>({id:'sunmeadow_march',size:100,segments:4,spatial:{bounds:{minX:-50,maxX:50,minZ:-40,maxZ:40},terrainGrid:{segmentsX:4,segmentsZ:3},playableOutline:[{x:-40,z:-30},{x:40,z:-30},{x:40,z:30},{x:-40,z:30}]},orvrLayout:{keeps:[{objectiveId:'retained',x:0,z:0,y:8}],terrain:{sourceVersion:'retained'}}} as ZoneDefinition);
const bounds={minX:-1000,maxX:1000,minZ:-1000,maxZ:1000};
const mountain=()=>({location:[40000,1000,5000],scale:[1,1,1],source:{boundsOrigin:[0,0,1000],boundsExtent:[10000,10000,1000]}});
it('expands content immutably while retaining military coordinates, outline and exact sampling metadata',()=>{
 const s=source(),before=structuredClone(s),z=extendTerrainOwnership(s,bounds);
 expect(s).toEqual(before);expect(z.spatial!.terrainBounds).toEqual(s.spatial!.bounds);
 expect(z.orvrLayout!.keeps).toEqual(s.orvrLayout!.keeps);expect(z.spatial!.playableOutline).toEqual(s.spatial!.playableOutline);
 expect(z.orvrLayout!.spatial).toBe(z.spatial);
 expect(()=>extendTerrainOwnership(s,{...bounds,minX:0})).toThrow(/retained/);
});
it('converts translated original mesh bounds into source axes and reserves distant separation',()=>{
 expect(distantMountainBounds(mountain())).toEqual({minX:-90,maxX:110,minZ:300,maxZ:500});
 const z=extendTerrainOwnership(source(),bounds);expect(validateDistantMountains(z,[mountain()])).toHaveLength(1);
 const close=mountain();close.location[0]=10000;expect(()=>validateDistantMountains(z,[close])).toThrow(/playable/);
 const escaped=mountain();escaped.location[0]=110000;expect(()=>validateDistantMountains(z,[escaped])).toThrow(/ownership/);
 const invalid=mountain();invalid.scale[2]=0;expect(()=>distantMountainBounds(invalid)).toThrow(/transform/);
 expect(()=>validateDistantMountains(z,[])).toThrow(/bounded/);
});
