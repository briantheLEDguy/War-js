import {expect,it} from 'vitest';
import {terrainSurfaceHeight,validateTerrainSurface,type TerrainSurface} from '../shared/terrainSurface';
import {terrainFieldHeight,validateTerrainField,type TerrainField} from '../shared/terrainField';
import {createOrvrGridHeightSampler,orvrHeightAt} from '../shared/orvrTerrain';
const surface=():TerrainSurface=>({bounds:{minX:-30,maxX:30,minZ:-20,maxZ:20},segmentsX:3,segmentsZ:2,edgeFade:2,
 samples:[10,30,50,70,20,40,60,80,30,50,70,90]});
const field:TerrainField={version:1,baseHeight:7,seed:1,rolls:[],ridges:[],channels:[]};
it('samples rectangular absolute elevations and survives serialization without mutating the raster',()=>{
 const s=surface(),copy=structuredClone(s);validateTerrainSurface(s);
 expect(terrainSurfaceHeight(s,-20,-10,7)).toBe(25);expect(terrainSurfaceHeight(s,20,10,7)).toBe(75);
 expect(terrainSurfaceHeight(JSON.parse(JSON.stringify(s)),20,10,7)).toBe(75);expect(s).toEqual(copy);
});
it('joins the original field continuously at every raster edge with compact smooth fading',()=>{
 const s=surface();for(const [x,z] of [[-30,0],[30,0],[0,-20],[0,20],[50,50],[NaN,0]])expect(terrainSurfaceHeight(s,x,z,7)).toBe(7);
 for(const [x,z] of [[-30+.00001,0],[30-.00001,0],[0,-20+.00001],[0,20-.00001]])expect(terrainSurfaceHeight(s,x,z,7)).toBeCloseTo(7,7);
 expect(terrainSurfaceHeight(s,-29,0,7)).toBeCloseTo(14,12);
});
it('preserves the legacy field and keeps route and footing controls above the absolute source',()=>{
 expect(terrainFieldHeight(field,0,0)).toBe(7);
 const f={...field,surface:surface()};validateTerrainField(f);expect(terrainFieldHeight(f,0,0)).toBe(50);
 const t={sourceVersion:'surface-test',naturalField:f,landforms:[],flattenAreas:[],clearCorridors:[{id:'road',height:12,radius:5,feather:10,points:[{x:-20,z:0,y:12},{x:20,z:0,y:12}]}]};
 expect(orvrHeightAt(t,0,0)).toBe(12);
 expect(orvrHeightAt({...t,flattenAreas:[{id:'home',x:0,z:0,height:5,radius:2,feather:3,preserveFooting:true}]},0,0)).toBe(5);
});
it('uses native Float32 triangle grounding on the admitted rectangular surface',()=>{
 const t={sourceVersion:'surface-test',naturalField:{...field,surface:surface()},landforms:[],flattenAreas:[],clearCorridors:[]};
 const spatial={bounds:surface().bounds,terrainGrid:{segmentsX:3,segmentsZ:2},playableOutline:[{x:-30,z:-20},{x:30,z:-20},{x:30,z:20},{x:-30,z:20}]};
 const h=createOrvrGridHeightSampler(t,60,3,spatial),v=(x:number,z:number)=>Math.fround(orvrHeightAt(t,x,z));
 expect(h(-25,-16)).toBeCloseTo(v(-30,-20)+.25*(v(-10,-20)-v(-30,-20))+.2*(v(-30,0)-v(-30,-20)),7);
 expect(h(-15,-4)).toBeCloseTo(v(-10,0)+.25*(v(-30,0)-v(-10,0))+.2*(v(-10,-20)-v(-10,0)),7);
});
it('rejects missing, sparse, nonfinite and unbounded samples or raster controls at admission',()=>{
 const sparse=surface();delete sparse.samples[2];
 const invalid=[sparse,{...surface(),samples:[1]}, {...surface(),samples:surface().samples.map((v,i)=>i===1?NaN:v)},
 {...surface(),samples:surface().samples.map((v,i)=>i===1?351:v)}, {...surface(),samples:surface().samples.map((v,i)=>i===1?-101:v)},
 {...surface(),segmentsX:513},{...surface(),segmentsZ:0},{...surface(),edgeFade:21},{...surface(),edgeFade:0},
 {...surface(),bounds:{...surface().bounds,minX:-10001}},{...surface(),bounds:{...surface().bounds,maxX:-30}}];
 for(const s of invalid){expect(()=>validateTerrainSurface(s)).toThrow();expect(()=>validateTerrainField({...field,surface:s})).toThrow();
 expect(()=>createOrvrGridHeightSampler({sourceVersion:'bad',naturalField:{...field,surface:s},landforms:[],flattenAreas:[],clearCorridors:[]},60,3)).toThrow();}
});
