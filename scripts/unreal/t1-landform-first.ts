/** Terrain-first authoring changes elevations together; gameplay rules and horizontal military anchors remain retained. */
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {validateTerrainSurface,terrainSurfaceHeight,type TerrainSurface} from '../../shared/terrainSurface';
import {createOrvrGridHeightSampler} from '../../shared/orvrTerrain';
import {containsSpatialPoint,spatialSegmentInside} from '../../shared/worldSpatial';
import {gradeTerrainNetwork} from './t1-grade-network';
import {reconcilePocketGrounding} from './t1-pocket-grounding';
import type {LandscapePocket} from './t1-landscape-pockets';
import {battlefieldGrades,type GradeRoute} from './t1-battlefield-grades';
import {tacticalSpurRecipes} from './t1-tactical-spurs';
import {contourRoutes} from './t1-contour-routes';
import {detourRoundReserve} from './t1-route-reserves';
import {validateT1} from './t1-layouts';

/** Apply one translation to every world position in a complete keep assembly, retaining relative fitted offsets. */
export function translateAssemblyElevation<T>(original:T,delta:number):T {
 if(!Number.isFinite(delta))throw new Error('Invalid assembly elevation');
 const value=structuredClone(original);
 const visit=(item:unknown)=>{
  if(!item||typeof item!=='object')return;
  const row=item as Record<string,unknown>;
  if(typeof row.x==='number'&&typeof row.z==='number'&&typeof row.y==='number')row.y+=delta;
  for(const child of Object.values(item))if(child&&typeof child==='object')visit(child);
 };
 visit(value);return value;
}

export interface KeepPropFrame {id:string;x:number;z:number;y:number}

export interface LandformFirstOptions {pockets?:LandscapePocket[];support?:GradeRoute[];keepFrames?:KeepPropFrame[];links?:GradeRoute[]}

export function landformFirst(original:ZoneDefinition,surface:TerrainSurface,options:LandformFirstOptions={}) {
 const {pockets:retainedPockets=[],support=[],keepFrames=[],links=[]}=options;
 if(!['sunmeadow_march','cinderfen_outskirts'].includes(original.id)||!original.spatial||!original.paths||!original.orvrLayout?.terrain.naturalField)
  throw new Error('Terrain-first authoring requires an explicit first-pair zone');
 if(original.orvrLayout.terrain.naturalField.surface)throw new Error('Preserve existing absolute terrain surface');
 validateTerrainSurface(surface);
 if(!Array.isArray(support)||support.length>128||support.some(r=>!r.id||!Number.isFinite(r.width)||r.width<2||r.width>12||!Array.isArray(r.points)||r.points.length<2||r.points.length>2048
  ||r.points.some((p,i)=>!Number.isFinite(p.x)||!Number.isFinite(p.z)||i>0&&!spatialSegmentInside(original.spatial!,r.points[i-1],p,r.width/2))))throw new Error('Invalid terrain-first population approach');
 let zone=structuredClone(original),terrain=zone.orvrLayout!.terrain;
 terrain.naturalField!.surface=structuredClone(surface);terrain.landforms=[];
 const promotedLinks=structuredClone(links);
 if(promotedLinks.length>16||promotedLinks.some(r=>!r.id||!Number.isFinite(r.width)||r.width<2||r.width>12||zone.paths!.some(p=>p.id===r.id)))throw new Error('Invalid retained exploration links');
 for(const link of promotedLinks){
  for(const pocket of retainedPockets.filter(p=>!p.cosmeticWater))link.points=detourRoundReserve(link.points,pocket,pocket.radius+18,(a,b)=>spatialSegmentInside(zone.spatial!,a,b,link.width/2+3)).points;
  const corridor=terrain.clearCorridors.find(c=>c.id===link.id);if(!corridor)throw new Error('Exploration link lacks its retained ground corridor');corridor.points=structuredClone(link.points);
  zone.paths!.push({id:link.id!,points:structuredClone(link.points),width:link.width,style:'dirt_trail'});
 }
 const counterPrefix=zone.id+'_western_spur_counter_',routes=[...zone.paths!.filter(p=>!p.id.startsWith(counterPrefix)),...zone.orvrLayout!.caravanRoutes,...terrain.clearCorridors];
 const network=gradeTerrainNetwork(routes,terrain.flattenAreas,(x,z)=>terrainSurfaceHeight(surface,x,z,7));
 routes.forEach((r,i)=>r.points=network.routes[i].points);terrain.flattenAreas=network.pads;
 const village=terrain.flattenAreas.find(a=>a.id==='village');if(!village)throw new Error('Terrain-first village foundation is missing');
 for(const area of terrain.flattenAreas)if(area.id==='village'||area.id==='arrival_court'||area.id.startsWith(zone.id+'_village_')){area.height=village.height;if(area.y!==undefined)area.y=village.height;}
 const grounded=reconcilePocketGrounding(zone,retainedPockets);zone=grounded.zone;terrain=zone.orvrLayout!.terrain;
 const height=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial),before=createOrvrGridHeightSampler(original.orvrLayout.terrain,original.size,original.segments,original.spatial);
 zone.orvrLayout!.keeps=zone.orvrLayout!.keeps.map(keep=>{
  const pad=terrain.flattenAreas.find(a=>a.id===keep.objectiveId);if(!pad)throw new Error('Terrain-first keep foundation is missing');
  return translateAssemblyElevation(keep,pad.height-(keep.y??0));
 });
 for(const camp of zone.orvrLayout!.stagingCamps){const pad=terrain.flattenAreas.find(a=>a.id===camp.id);if(!pad)throw new Error('Terrain-first staging foundation is missing');camp.y=pad.height;}
 for(const bo of zone.orvrLayout!.battlefieldObjectives)bo.y=height(bo.x,bo.z);
 const move=(p:{x:number;z:number;y?:number})=>{if(p.y!==undefined)p.y+=height(p.x,p.z)-before(p.x,p.z);};
 if(zone.spawnPoint)move(zone.spawnPoint);
 for(const t of zone.zoneTriggers??[]){move(t);if(t.arrivalPoint)move(t.arrivalPoint);}
 const frames=new Map(keepFrames.map(p=>[p.id,p]));
 if(keepFrames.length>512||frames.size!==keepFrames.length||keepFrames.some(p=>{const old=original.props?.find(o=>o.id===p.id);return !old||![p.x,p.z,p.y].every(Number.isFinite)||Math.abs(p.y)>350||Math.hypot(p.x-old.x,p.z-old.z)>.001||!original.orvrLayout!.keeps.some(k=>p.id.startsWith(k.objectiveId+'_'));}))throw new Error('Invalid retained native keep prop frame');
 // Source collision and fitted props follow the same rigid keep translation as native assemblies.
 for(const p of zone.props??[]){
  const keep=original.orvrLayout.keeps.find(k=>p.id===k.objectiveId||p.id?.startsWith(k.objectiveId+'_'));
  if(keep){
   const moved=zone.orvrLayout!.keeps.find(k=>k.objectiveId===keep.objectiveId)!;
   const frame=frames.get(p.id??''),gate=keep.gates.find(g=>g.propId===p.id);
   const postern=keep.postern&&[keep.postern.propId,keep.postern.propId.replace(/_outside$/,'_inside')].includes(p.id??'')?keep.postern:undefined;
   const oldY=frame?.y??(postern?postern.outside.y+(p.y??0):gate?(gate.y??keep.y??0)+(p.y??0):(p.heightMode==='absolute'?0:before(p.x,p.z))+(p.y??0));
   p.y=oldY+(moved.y??0)-(keep.y??0);p.heightMode='absolute';
  }else if(p.heightMode==='absolute')p.y=(p.y??0)+height(p.x,p.z)-before(p.x,p.z);
 }
 if(zone.paths!.some(p=>p.id.startsWith(counterPrefix)))for(const recipe of tacticalSpurRecipes(zone.id).searches)
  for(const counter of contourRoutes(recipe,height,(p,r)=>containsSpatialPoint(zone.spatial!,p,r)).routes){const path=zone.paths!.find(p=>p.id===counter.id);if(!path)throw new Error('Terrain-first counter identity is missing');path.points=counter.points;}
 const ids=new Set(zone.paths!.map(p=>p.id));
 const grades=battlefieldGrades([...zone.paths!,...zone.orvrLayout!.caravanRoutes,...terrain.clearCorridors.filter(c=>!ids.has(c.id)).map(c=>({id:c.id,points:c.points,width:c.id.includes('_pocket_')?6:12}))],height),supportGrades=battlefieldGrades(support,height);
 if([...grades,...supportGrades].some(g=>g.maximumGrade>.22))throw new Error('Terrain-first surface exceeds full-width route grades');
 terrain.sourceVersion='t1-landform-first-v1';zone.orvrLayout!.version=terrain.sourceVersion;validateT1(zone);
 return {zone,links:promotedLinks.map(link=>({...link,points:structuredClone(zone.paths!.find(p=>p.id===link.id)!.points)})),pockets:grounded.pockets,basins:grounded.basins,grades,supportGrades,network:{nodeCount:network.nodeCount,edgeCount:network.edgeCount,maximumCutMetres:network.maximumCutMetres,maximumCentreGrade:network.maximumCentreGrade},
  nativeBuilt:false,appearanceApproved:false,drivingAccepted:false,fullAssemblyRelocationAccepted:false};
}
