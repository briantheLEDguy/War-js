/** Tangent detours retain full-width route reserves around exploration structures. */
import type {TerrainPoint} from '../../shared/orvrTerrain';
import {distanceToSpatialSegment,type SpatialPoint} from '../../shared/worldSpatial';

export function detourRoundReserve(points:TerrainPoint[],centre:SpatialPoint,radius:number,admitted:(a:SpatialPoint,b:SpatialPoint)=>boolean=()=>true) {
 if(!Array.isArray(points)||points.length<2||points.length>4096||![centre.x,centre.z,radius].every(Number.isFinite)||radius<4||radius>80
  ||points.some((p,i)=>![p.x,p.z].every(v=>Number.isFinite(v)&&Math.abs(v)<=10000)||i>0&&Math.hypot(p.x-points[i-1].x,p.z-points[i-1].z)<.001))throw new Error('Invalid bounded route reserve');
 // Circumscribe the sampled arc so its straight chords also remain outside the reserve.
 const r=radius/Math.cos(Math.PI/36),tau=Math.PI*2,result:TerrainPoint[]=[{...points[0]}];let detouredSegments=0;
 for(let i=1;i<points.length;i++){
  const a=points[i-1],b=points[i];
  if(distanceToSpatialSegment(centre,a,b)>=radius){result.push({...b});continue;}
  const da=Math.hypot(a.x-centre.x,a.z-centre.z),db=Math.hypot(b.x-centre.x,b.z-centre.z);
  if(da<=r||db<=r)throw new Error('Route endpoint lies inside an exploration reserve');
  const aa=Math.atan2(a.z-centre.z,a.x-centre.x),ab=Math.atan2(b.z-centre.z,b.x-centre.x),candidates=[];
  for(const direction of [1,-1]){
   const start=aa+direction*Math.acos(r/da),end=ab-direction*Math.acos(r/db),sweep=((direction*(end-start))%tau+tau)%tau,steps=Math.max(1,Math.ceil(sweep/(Math.PI/18)));
   const arc=Array.from({length:steps+1},(_,j)=>({x:centre.x+r*Math.cos(start+direction*sweep*j/steps),z:centre.z+r*Math.sin(start+direction*sweep*j/steps)}));
   const chain=[a,...arc,b];if(!chain.slice(1).every((p,j)=>admitted(chain[j],p)))continue;
   const length=chain.slice(1).reduce((sum,p,j)=>sum+Math.hypot(p.x-chain[j].x,p.z-chain[j].z),0);candidates.push({chain,length,direction});
  }
  candidates.sort((a,b)=>a.length-b.length||b.direction-a.direction);if(!candidates.length)throw new Error('No contained exploration counterroute');
  result.push(...candidates[0].chain.slice(1).map(p=>({...p})));detouredSegments++;
  if(result.length>4096)throw new Error('Exploration detour inventory exceeded');
 }
 return {points:result,detouredSegments};
}
