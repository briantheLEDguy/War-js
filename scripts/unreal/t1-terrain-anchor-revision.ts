/** Explicit revision of an already authored landform; only elevations and terrain controls change. */
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {createOrvrGridHeightSampler} from '../../shared/orvrTerrain';
import {validateTerrainSurface} from '../../shared/terrainSurface';
import {containsSpatialPoint} from '../../shared/worldSpatial';
import {translateAssemblyElevation,type KeepPropFrame} from './t1-landform-first';
import {validateT1} from './t1-layouts';

const FIRST_PAIR=['sunmeadow_march','cinderfen_outskirts'];

export function relocateTerrainAnchors(original:ZoneDefinition,revisedTerrain:NonNullable<ZoneDefinition['orvrLayout']>['terrain'],keepFrames:KeepPropFrame[]=[]) {
 const old=original.orvrLayout?.terrain,previous=old?.naturalField?.surface,next=revisedTerrain?.naturalField?.surface;
 if(!FIRST_PAIR.includes(original.id)||!original.spatial||!old||!previous||!next)throw new Error('Anchor revision requires an explicit absolute first-pair landform');
 validateTerrainSurface(next);
 if(['minX','maxX','minZ','maxZ'].some(k=>next.bounds[k as keyof typeof next.bounds]!==previous.bounds[k as keyof typeof previous.bounds])||next.segmentsX!==previous.segmentsX||next.segmentsZ!==previous.segmentsZ)throw new Error('Preserve the retained terrain sampling grid');
 if(!Array.isArray(revisedTerrain.flattenAreas)||revisedTerrain.flattenAreas.length>128||new Set(revisedTerrain.flattenAreas.map(p=>p.id)).size!==revisedTerrain.flattenAreas.length||revisedTerrain.flattenAreas.some(p=>![p.x,p.z,p.height,p.radius,p.feather].every(Number.isFinite)||p.radius<=0||p.feather<0))throw new Error('Invalid revised foundations');
 for(const pad of old.flattenAreas){const revised=revisedTerrain.flattenAreas.find(p=>p.id===pad.id);if(!revised||revised.x!==pad.x||revised.z!==pad.z||revised.preserveFooting!==pad.preserveFooting)throw new Error('Preserve retained foundation identities and positions');}
 if(!Array.isArray(revisedTerrain.clearCorridors)||revisedTerrain.clearCorridors.length>128||new Set(revisedTerrain.clearCorridors.map(c=>c.id)).size!==revisedTerrain.clearCorridors.length||revisedTerrain.clearCorridors.some(c=>!c.id||![c.radius,c.feather,c.height].every(Number.isFinite)||c.radius<=0||c.feather<0||!Array.isArray(c.points)||c.points.length<2||c.points.length>4096||c.points.some(p=>![p.x,p.z,p.y??c.height].every(Number.isFinite))))throw new Error('Invalid revised ground corridors');
 if(old.clearCorridors.some(c=>!revisedTerrain.clearCorridors.some(n=>n.id===c.id)))throw new Error('Preserve retained ground corridors');
 const frames=new Map(keepFrames.map(p=>[p.id,p]));
 if(keepFrames.length>512||frames.size!==keepFrames.length||keepFrames.some(p=>{const prop=original.props.find(o=>o.id===p.id);return !prop||![p.x,p.z,p.y].every(Number.isFinite)||Math.abs(p.y)>350||Math.hypot(p.x-prop.x,p.z-prop.z)>.001||!original.orvrLayout!.keeps.some(k=>p.id.startsWith(k.objectiveId+'_'));}))throw new Error('Invalid retained native keep prop frame');
 const zone=structuredClone(original);zone.orvrLayout!.terrain=structuredClone(revisedTerrain);
 const before=createOrvrGridHeightSampler(old,original.size,original.segments,original.spatial),sample=createOrvrGridHeightSampler(zone.orvrLayout!.terrain,zone.size,zone.segments,zone.spatial);
 const height=(x:number,z:number)=>{const y=sample(x,z);if(!Number.isFinite(y)||y< -100||y>350)throw new Error('Invalid revised terrain height');return y;};
 let boundaryError=0;
 for(let i=0;i<=next.segmentsX;i++)for(const z of [next.bounds.minZ,next.bounds.maxZ]){const x=next.bounds.minX+i/next.segmentsX*(next.bounds.maxX-next.bounds.minX);boundaryError=Math.max(boundaryError,Math.abs(height(x,z)-before(x,z)));}
 for(let i=0;i<=next.segmentsZ;i++)for(const x of [next.bounds.minX,next.bounds.maxX]){const z=next.bounds.minZ+i/next.segmentsZ*(next.bounds.maxZ-next.bounds.minZ);boundaryError=Math.max(boundaryError,Math.abs(height(x,z)-before(x,z)));}
 if(boundaryError>.001)throw new Error('Preserve retained distant-terrain seams');
 const deltas=new Map<string,number>();
 zone.orvrLayout!.keeps=zone.orvrLayout!.keeps.map(keep=>{const pad=zone.orvrLayout!.terrain.flattenAreas.find(p=>p.id===keep.objectiveId);if(!pad||!Number.isFinite(keep.y))throw new Error('Missing retained keep foundation');const delta=pad.height-keep.y!;deltas.set(keep.objectiveId,delta);return translateAssemblyElevation(keep,delta);});
 for(const camp of zone.orvrLayout!.stagingCamps){const pad=zone.orvrLayout!.terrain.flattenAreas.find(p=>p.id===camp.id);if(!pad)throw new Error('Missing retained staging foundation');camp.y=pad.height;}
 for(const bo of zone.orvrLayout!.battlefieldObjectives)bo.y=height(bo.x,bo.z);
 for(const objective of zone.rvrObjectives??[]){const anchor=zone.orvrLayout!.keeps.find(k=>k.objectiveId===objective.id)??zone.orvrLayout!.battlefieldObjectives.find(k=>k.objectiveId===objective.id);if(!anchor||anchor.x!==objective.x||anchor.z!==objective.z)throw new Error('Preserve runtime objective identity and position');objective.y=anchor.y;}
 const move=(p:{x:number;z:number;y?:number},delta?:number)=>{if(p.y!==undefined)p.y+=delta??height(p.x,p.z)-before(p.x,p.z);};
 if(zone.spawnPoint)move(zone.spawnPoint);
 for(const trigger of zone.zoneTriggers??[]){move(trigger);if(trigger.arrivalPoint)move(trigger.arrivalPoint);}
 for(const prop of zone.props){
  const keep=original.orvrLayout!.keeps.find(k=>prop.id===k.objectiveId||prop.id?.startsWith(k.objectiveId+'_'));
  if(keep){const frame=frames.get(prop.id??'');if(!frame&&prop.heightMode!=='absolute')throw new Error('Keep revision requires retained absolute prop frames');prop.y=(frame?.y??prop.y??0)+deltas.get(keep.objectiveId)!;prop.heightMode='absolute';}
  else if(prop.heightMode==='absolute')move(prop);
 }
 for(const actor of [...zone.npcs??[],...zone.enemies])if(actor.heightMode==='absolute'){
  const keep=original.orvrLayout!.keeps.find(k=>actor.id.startsWith(k.objectiveId+'_')||'encounter' in actor&&actor.encounter?.objectiveId===k.objectiveId);move(actor,keep?deltas.get(keep.objectiveId):undefined);
 }
 for(const route of [...zone.paths??[],...zone.orvrLayout!.caravanRoutes])for(const point of route.points)point.y=height(point.x,point.z);
 validateT1(zone);
 return {zone,keepDeltas:Object.fromEntries(deltas),maximumBoundaryErrorMetres:boundaryError,requiresReciprocalArrivals:true,nativeIntegrated:false,routeGradesAccepted:false,fullAssemblyRelocationAccepted:false,appearanceApproved:false};
}

/** Refresh only incoming landings; campaign arrows and local trigger geometry remain exact. */
export function reconcileTerrainArrivals(original:ZoneDefinition[],changedIds:string[]) {
 if(!Array.isArray(changedIds)||!changedIds.length||changedIds.length>2||new Set(changedIds).size!==changedIds.length||changedIds.some(id=>!FIRST_PAIR.includes(id))||new Set(original.map(z=>z.id)).size!==original.length)throw new Error('Invalid terrain arrival revision');
 const maps=structuredClone(original),targets=new Map(maps.filter(z=>changedIds.includes(z.id)).map(z=>[z.id,z]));
 if(targets.size!==changedIds.length)throw new Error('Missing changed arrival zone');
 for(const zone of maps)for(const trigger of zone.zoneTriggers??[]){
  const target=targets.get(trigger.targetZoneId);if(!target)continue;
  const reciprocals=target.zoneTriggers?.filter(t=>t.targetZoneId===zone.id)??[],arrival=reciprocals[0]?.arrivalPoint;
  if(reciprocals.length!==1||!arrival||![arrival.x,arrival.y,arrival.z].every(Number.isFinite)||!target.spatial||!containsSpatialPoint(target.spatial,arrival,1))throw new Error('Missing unique connected reciprocal arrival');
  const height=createOrvrGridHeightSampler(target.orvrLayout!.terrain,target.size,target.segments,target.spatial);
  if(Math.abs(height(arrival.x,arrival.z)-arrival.y)>.05)throw new Error('Reciprocal arrival lacks revised terrain support');
  trigger.targetSpawn={...arrival};
 }
 return maps;
}
