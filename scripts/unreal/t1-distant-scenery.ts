/** Distant scenery expands ownership while preserving the authored playable triangle grid. */
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {resolveZoneSpatial,terrainSamplingBounds,type SpatialBounds} from '../../shared/worldSpatial';

export function extendTerrainOwnership(original:ZoneDefinition,bounds:SpatialBounds):ZoneDefinition {
 if(!original.spatial||!original.orvrLayout)throw new Error('Distant scenery requires explicit regional spatial metadata');
 const prior=resolveZoneSpatial(original),old=prior.bounds;
 if(![bounds.minX,bounds.maxX,bounds.minZ,bounds.maxZ].every(v=>Number.isFinite(v)&&Math.abs(v)<=10000)
  ||bounds.minX>old.minX||bounds.maxX<old.maxX||bounds.minZ>old.minZ||bounds.maxZ<old.maxZ)throw new Error('Distant ownership must contain the retained content envelope');
 const zone=structuredClone(original);
 zone.spatial={...structuredClone(prior),bounds:{...bounds},terrainBounds:{...terrainSamplingBounds(prior)}};
 resolveZoneSpatial(zone);zone.orvrLayout!.spatial=zone.spatial;
 return zone;
}

export interface DistantMountain {
 location:number[];scale:number[];source:{boundsOrigin:number[];boundsExtent:number[]};
}
/** Axis conversion is the same source X/Z to native Y/X mapping as playable geometry. */
export function distantMountainBounds(row:DistantMountain):SpatialBounds {
 const {location:p,scale:s,source:{boundsOrigin:o,boundsExtent:e}}=row;
 if([p,s,o,e].some(a=>!Array.isArray(a)||a.length!==3||!a.every(Number.isFinite))
  ||s.some(v=>v<=0||v>10)||e.some(v=>v<=0)||p.some(v=>Math.abs(v)>1000000))throw new Error('Invalid distant mountain transform');
 return {minX:(p[1]+(o[1]-e[1])*s[1])/100,maxX:(p[1]+(o[1]+e[1])*s[1])/100,
  minZ:(p[0]+(o[0]-e[0])*s[0])/100,maxZ:(p[0]+(o[0]+e[0])*s[0])/100};
}

export function validateDistantMountains(zone:ZoneDefinition,rows:DistantMountain[]):SpatialBounds[] {
 const spatial=resolveZoneSpatial(zone),b=spatial.bounds,t=terrainSamplingBounds(spatial);
 if(!spatial.terrainBounds||!Array.isArray(rows)||rows.length<1||rows.length>8)throw new Error('Distant scenery requires bounded separate ownership');
 return rows.map(row=>{
  const f=distantMountainBounds(row),epsilon=.001;
  if(f.minX<b.minX-epsilon||f.maxX>b.maxX+epsilon||f.minZ<b.minZ-epsilon||f.maxZ>b.maxZ+epsilon)
   throw new Error('Distant mountain escapes regional ownership');
  if(!(f.maxX<=t.minX-199.99||f.minX>=t.maxX+199.99||f.maxZ<=t.minZ-199.99||f.minZ>=t.maxZ+199.99))
   throw new Error('Distant mountain overlaps playable terrain reserve');
  return f;
 });
}
