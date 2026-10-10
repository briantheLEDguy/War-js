import {terrainSamplingBounds} from '../../shared/worldSpatial';
/** Admit private source-derived relief without moving gameplay controls or retaining hidden fallbacks. */
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { validateTerrainRelief,type TerrainRelief } from '../../shared/terrainRelief';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { battlefieldGrades } from './t1-battlefield-grades';
import { validateT1 } from './t1-layouts';
import type { TerrainPoint } from '../../shared/orvrTerrain';

/** Bake a continuous exclusion apron into private detail, including ungraded pedestrian counters. */
export function protectReliefGrounding(original: ZoneDefinition, relief: TerrainRelief): TerrainRelief {
  if (!original.spatial || !original.orvrLayout || !original.paths) throw new Error('Relief protection requires explicit grounding');
  validateTerrainRelief(relief);
  const b=relief.bounds,spatial=original.spatial,terrain=original.orvrLayout.terrain;
  const buffer=2*Math.max((b.maxX-b.minX)/relief.segmentsX,(b.maxZ-b.minZ)/relief.segmentsZ,
    (terrainSamplingBounds(spatial).maxX-terrainSamplingBounds(spatial).minX)/spatial.terrainGrid.segmentsX,(terrainSamplingBounds(spatial).maxZ-terrainSamplingBounds(spatial).minZ)/spatial.terrainGrid.segmentsZ);
  const routes=[...original.paths,...original.orvrLayout.caravanRoutes].map(p=>({points:p.points,radius:p.width/2}));
  routes.push(...terrain.clearCorridors.map(c=>({points:c.points,radius:c.radius})));
  const segments=routes.flatMap(r=>r.points.slice(1).map((p,i)=>({a:r.points[i],b:p,radius:r.radius})));
  const distance=(x:number,z:number,a:TerrainPoint,c:TerrainPoint)=>{
    const dx=c.x-a.x,dz=c.z-a.z,d=dx*dx+dz*dz;
    const t=d?Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/d)):0;
    return Math.hypot(x-a.x-t*dx,z-a.z-t*dz);
  };
  const result=structuredClone(relief);
  result.samples=result.samples.map((value,i)=>{
    if(!value)return 0;
    const x=b.minX+(i%(relief.segmentsX+1))/relief.segmentsX*(b.maxX-b.minX);
    const z=b.minZ+Math.floor(i/(relief.segmentsX+1))/relief.segmentsZ*(b.maxZ-b.minZ);
    let nearest=Infinity;
    for(const s of segments)nearest=Math.min(nearest,distance(x,z,s.a,s.b)-s.radius-buffer);
    for(const area of terrain.flattenAreas)nearest=Math.min(nearest,Math.hypot(x-area.x,z-area.z)-area.radius-buffer);
    const t=Math.max(0,Math.min(1,nearest/25));
    return value*t*t*(3-2*t);
  });
  return result;
}

export function sourceTerrainRelief(original: ZoneDefinition, relief: TerrainRelief) {
  if (!['sunmeadow_march','cinderfen_outskirts'].includes(original.id) || !original.spatial || !original.paths || !original.orvrLayout?.terrain.naturalField)
    throw new Error('Source terrain relief requires an explicit first-pair region');
  if (original.orvrLayout.terrain.naturalField.relief) throw new Error('Preserve existing source terrain relief');
  validateTerrainRelief(relief);
  const zone=structuredClone(original),terrain=zone.orvrLayout!.terrain;
  const before=createOrvrGridHeightSampler(original.orvrLayout.terrain,original.size,original.segments,original.spatial);
  terrain.naturalField!.relief=protectReliefGrounding(original,relief);
  const height=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
  const anchors=[...zone.orvrLayout!.keeps,...zone.orvrLayout!.battlefieldObjectives,...zone.orvrLayout!.stagingCamps,
    ...(zone.spawnPoint?[zone.spawnPoint]:[]),...(zone.zoneTriggers??[]).flatMap(t=>t.arrivalPoint?[t,t.arrivalPoint]:[t])];
  if(anchors.some(p=>Math.abs(height(p.x,p.z)-before(p.x,p.z))>.01))throw new Error('Source relief moves a retained gameplay anchor');
  const ids=new Set(zone.paths!.map(p=>p.id));
  const grades=battlefieldGrades([...zone.paths!,...zone.orvrLayout!.caravanRoutes,
    ...terrain.clearCorridors.filter(c=>!ids.has(c.id)).map(c=>({id:c.id,points:c.points,width:c.id.includes('_pocket_')?6:12}))],height);
  if(grades.some(g=>g.maximumGrade>.22))throw new Error('Source relief exceeds retained full-width route grades');
  for(const prop of zone.props??[])if(prop.heightMode==='absolute')prop.y=(prop.y??0)+height(prop.x,prop.z)-before(prop.x,prop.z);
  terrain.sourceVersion='t1-source-relief-v1';zone.orvrLayout!.version=terrain.sourceVersion;validateT1(zone);
  return {zone,grades,nativeBuilt:false,appearanceApproved:false,drivingAccepted:false};
}
