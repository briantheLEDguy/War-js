/** Reconcile retained shallow pockets after landform changes; never represents a completed lair. */
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {createOrvrGridHeightSampler} from '../../shared/orvrTerrain';
import {containsSpatialPoint} from '../../shared/worldSpatial';
import type {LandscapePocket} from './t1-landscape-pockets';

export function reconcilePocketGrounding(original:ZoneDefinition,retained:LandscapePocket[]) {
 if(!original.spatial||!original.orvrLayout||!Array.isArray(retained)||retained.length>12)
  throw new Error('Pocket grounding requires bounded explicit terrain');
 const zone=structuredClone(original),pockets=structuredClone(retained),terrain=zone.orvrLayout!.terrain,basins=[];
 const sampler=()=>createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
 for(const p of pockets){
  const area=terrain.flattenAreas.find(a=>a.id===p.id),corridor=terrain.clearCorridors.find(c=>c.id===p.id+'_approach');
  const depth=p.waterY-p.bedY;
  if(!p.id||!area||!corridor||corridor.points.length<2||![p.x,p.z,p.radius,depth,area.feather].every(Number.isFinite)
   ||p.radius<2||p.radius>20||depth<=0||depth>2||area.feather<0||area.feather>60
   ||!containsSpatialPoint(zone.spatial!,p,p.radius+60))throw new Error('Invalid retained pocket grounding');
  const lengths=[0];for(let i=1;i<corridor.points.length;i++)lengths.push(lengths[i-1]+Math.hypot(corridor.points[i].x-corridor.points[i-1].x,corridor.points[i].z-corridor.points[i-1].z));
  const length=lengths[lengths.length-1];if(!Number.isFinite(length)||length<1)throw new Error('Invalid retained pocket approach');
  const rim=(height:(x:number,z:number)=>number)=>Math.min(...Array.from({length:96},(_,i)=>height(p.x+Math.cos(i*Math.PI/48)*(p.radius+60),p.z+Math.sin(i*Math.PI/48)*(p.radius+60))));
  let iterations=0;
  if(p.cosmeticWater)for(;iterations<8;iterations++){
   const height=sampler(),bed=height(p.x,p.z),edge=rim(height);
   if(!Number.isFinite(bed)||!Number.isFinite(edge))throw new Error('Nonfinite pocket grounding');
   if(edge>=bed+depth+.15)break;
   const target=edge-depth-.5,start=height(corridor.points[0].x,corridor.points[0].z);
   if(target< -100||target>350)throw new Error('Pocket basin exceeds terrain height bounds');
   area.height=target;if(area.y!==undefined)area.y=target;
   corridor.points.forEach((point,i)=>point.y=start+(target-start)*lengths[i]/length);
  }
  const height=sampler();p.bedY=height(p.x,p.z);p.waterY=p.bedY+depth;p.approach=structuredClone(corridor.points).map(point=>({...point,y:point.y??height(point.x,point.z)}));
  const minimumRimAboveWater=rim(height)-p.waterY;
  if(p.cosmeticWater&&minimumRimAboveWater<.1)throw new Error('Pocket basin did not converge to an enclosed surface');
  basins.push({id:p.id,bed:p.bedY,water:p.waterY,cosmeticWater:p.cosmeticWater,minimumRimAboveWater,iterations});
 }
 return {zone,pockets,basins,nativeVerified:false,appearanceApproved:false};
}
