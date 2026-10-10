import {describe,it,expect} from 'vitest';
import {resolveZoneSpatial,terrainSamplingBounds,containsSpatialPoint,type ZoneSpatial} from '../shared/worldSpatial';
import {createOrvrGridHeightSampler,type OrvrTerrainControls} from '../shared/orvrTerrain';
import {outdoorTerrain,terrainHeight} from '../scripts/unreal/world-portals';
import {conformRoadSurface,type NativeRoadSurface} from '../scripts/unreal/t1-road-conformance';
import type {ZoneDefinition} from '../shared/world/ZoneDefinition';

const sampling={minX:-12,maxX:20,minZ:-8,maxZ:16};
const local:ZoneSpatial={bounds:sampling,terrainGrid:{segmentsX:4,segmentsZ:3},playableOutline:[{x:-10,z:-6},{x:18,z:-6},{x:18,z:5},{x:3,z:5},{x:3,z:14},{x:-10,z:14}]};
const expanded=():ZoneSpatial=>({...structuredClone(local),bounds:{minX:-3600,maxX:3600,minZ:-3400,maxZ:3400},terrainBounds:{...sampling}});
const controls:OrvrTerrainControls={sourceVersion:'sampling-fixture',landforms:[{id:'ridge',kind:'ridge',x:0,z:0,radiusX:80,radiusZ:60,height:18}],flattenAreas:[],clearCorridors:[]};

describe('independent content and terrain sampling extents',()=>{
 it('preserves legacy square and explicit rectangular behavior when sampling bounds are absent',()=>{
  const legacy=resolveZoneSpatial({size:800,segments:8});expect(terrainSamplingBounds(legacy)).toEqual({minX:-400,maxX:400,minZ:-400,maxZ:400});
  expect(resolveZoneSpatial({size:32,segments:4,spatial:local})).toBe(local);expect(terrainSamplingBounds(local)).toBe(local.bounds);
 });
 it('retains a concave playable outline while admitting separately owned distant content',()=>{
  const s=resolveZoneSpatial({size:32,segments:4,spatial:expanded()});
  expect(containsSpatialPoint(s,{x:2000,z:2000},0,false)).toBe(true);expect(containsSpatialPoint(s,{x:2000,z:2000})).toBe(false);
  expect(containsSpatialPoint(s,{x:10,z:10})).toBe(false);expect(containsSpatialPoint(s,{x:0,z:10})).toBe(true);
 });
 it('keeps native triangles and authoritative ground identical under expanded ownership',()=>{
  const a=createOrvrGridHeightSampler(controls,32,4,local),b=createOrvrGridHeightSampler(controls,32,4,expanded());
  for(let z=-8;z<=16;z+=1.3)for(let x=-12;x<=20;x+=1.7)expect(b(x,z)).toBe(a(x,z));
  expect(b(500,500)).toBe(0);
  const map={id:'sunmeadow_march',size:32,segments:4,orvrLayout:{terrain:controls},spatial:local} as ZoneDefinition;
  const other={...map,spatial:expanded()};expect(outdoorTerrain(other)).toEqual(outdoorTerrain(map));
  for(const p of [[-9,-4],[0,0],[17,4]])expect(terrainHeight(other,p[0],p[1])).toBe(terrainHeight(map,p[0],p[1]));
 });
 it('clips cosmetic road overlays against the retained sampling cells',()=>{
  const mesh:NativeRoadSurface={zoneId:'sunmeadow_march',positions:[[-200,-800,0],[300,1200,0],[1000,0,0]],normals:[[0,0,1],[0,0,1],[0,0,1]],uvs:[[0,0],[1,0],[0,1]],colors:[[1,1,1,0],[1,1,1,1],[1,1,1,.5]],indices:[0,1,2]};
  const height=createOrvrGridHeightSampler(controls,32,4,local);
  expect(conformRoadSurface(mesh,expanded(),height)).toEqual(conformRoadSurface(mesh,local,height));
 });
 it('rejects malformed extents, sampling outside ownership, and playable ground outside sampling',()=>{
  for(const terrainBounds of [null,{}, {...sampling,maxX:NaN},{...sampling,maxZ:-9},{...sampling,minX:-4000},{...sampling,minX:0}])
   expect(()=>resolveZoneSpatial({size:32,segments:4,spatial:{...expanded(),terrainBounds} as ZoneSpatial})).toThrow(/sampling/);
 });
});
