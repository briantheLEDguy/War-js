/** Qualify absolute landforms while retaining complete military and route grounding. */
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {terrainFieldHeight} from '../../shared/terrainField';
import {validateTerrainSurface,type TerrainSurface} from '../../shared/terrainSurface';
import {createOrvrGridHeightSampler,type TerrainPoint} from '../../shared/orvrTerrain';
import {battlefieldGrades,type GradeRoute} from './t1-battlefield-grades';
import {spatialSegmentInside} from '../../shared/worldSpatial';
import {validateT1} from './t1-layouts';

/** Bake the original field beneath retained lanes, pads and counters before native triangulation. */
export function protectSurfaceGrounding(original:ZoneDefinition,surface:TerrainSurface,apron=90,support:GradeRoute[]=[]):TerrainSurface {
 if(!original.spatial||!original.paths||!original.orvrLayout?.terrain.naturalField||!Number.isFinite(apron)||apron<25||apron>200)
  throw new Error('Absolute surface protection requires bounded explicit grounding');
 validateTerrainSurface(surface);
 if(!Array.isArray(support)||support.length>128||support.some(route=>!route.id||!Number.isFinite(route.width)||route.width<2||route.width>12
  ||!Array.isArray(route.points)||route.points.length<2||route.points.length>2048
  ||route.points.some((p,i)=>!Number.isFinite(p.x)||!Number.isFinite(p.z)||i>0&&!spatialSegmentInside(original.spatial!,route.points[i-1],p,route.width/2))))
  throw new Error('Invalid retained surface support approach');
 const b=surface.bounds,s=original.spatial,t=original.orvrLayout.terrain,f=t.naturalField!;
 if(f.surface)throw new Error('Preserve existing absolute terrain surface');
 const buffer=2*Math.max((b.maxX-b.minX)/surface.segmentsX,(b.maxZ-b.minZ)/surface.segmentsZ,
  (s.bounds.maxX-s.bounds.minX)/s.terrainGrid.segmentsX,(s.bounds.maxZ-s.bounds.minZ)/s.terrainGrid.segmentsZ);
 const routes=[...original.paths,...original.orvrLayout.caravanRoutes,...support].map(p=>({points:p.points,radius:p.width/2}));
 routes.push(...t.clearCorridors.map(c=>({points:c.points,radius:c.radius})));
 const segments=routes.flatMap(r=>r.points.slice(1).map((p,i)=>({a:r.points[i],b:p,radius:r.radius})));
 const distance=(x:number,z:number,a:TerrainPoint,c:TerrainPoint)=>{const dx=c.x-a.x,dz=c.z-a.z,d=dx*dx+dz*dz;
  const u=d?Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/d)):0;return Math.hypot(x-a.x-u*dx,z-a.z-u*dz);};
 const result=structuredClone(surface);
 result.samples=result.samples.map((value,i)=>{
  const x=b.minX+i%(surface.segmentsX+1)/surface.segmentsX*(b.maxX-b.minX),z=b.minZ+Math.floor(i/(surface.segmentsX+1))/surface.segmentsZ*(b.maxZ-b.minZ);
  let nearest=Infinity;
  for(const r of segments)nearest=Math.min(nearest,distance(x,z,r.a,r.b)-r.radius-buffer);
  for(const a of t.flattenAreas)nearest=Math.min(nearest,Math.hypot(x-a.x,z-a.z)-a.radius-buffer);
  const u=Math.max(0,Math.min(1,nearest/apron)),old=terrainFieldHeight(f,x,z);
  return old+(value-old)*u*u*(3-2*u);
 });
 validateTerrainSurface(result);return result;
}

export function sourceTerrainSurface(original:ZoneDefinition,surface:TerrainSurface,apron=90,support:GradeRoute[]=[]) {
 if(!['sunmeadow_march','cinderfen_outskirts'].includes(original.id)||!original.spatial||!original.paths||!original.orvrLayout?.terrain.naturalField)
  throw new Error('Absolute terrain surface requires an explicit first-pair zone');
 if(original.orvrLayout.terrain.naturalField.surface)throw new Error('Preserve existing absolute terrain surface');
 const zone=structuredClone(original),terrain=zone.orvrLayout!.terrain;
 const before=createOrvrGridHeightSampler(original.orvrLayout.terrain,original.size,original.segments,original.spatial);
 terrain.naturalField!.surface=protectSurfaceGrounding(original,surface,apron,support);
 const height=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
 const anchors=[...zone.orvrLayout!.keeps,...zone.orvrLayout!.battlefieldObjectives,...zone.orvrLayout!.stagingCamps,
 ...(zone.spawnPoint?[zone.spawnPoint]:[]),...(zone.zoneTriggers??[]).flatMap(t=>t.arrivalPoint?[t,t.arrivalPoint]:[t])];
 if(anchors.some(p=>Math.abs(height(p.x,p.z)-before(p.x,p.z))>.01))throw new Error('Absolute terrain surface moves a retained gameplay footing');
 for(const route of support)for(const p of route.points)if(Math.abs(height(p.x,p.z)-before(p.x,p.z))>.01)throw new Error('Absolute terrain surface moves a retained population approach');
 const supportGrades=battlefieldGrades(support,height);
 const ids=new Set(zone.paths!.map(p=>p.id));
 const grades=battlefieldGrades([...zone.paths!,...zone.orvrLayout!.caravanRoutes,...terrain.clearCorridors.filter(c=>!ids.has(c.id)).map(c=>({id:c.id,points:c.points,width:c.id.includes('_pocket_')?6:12}))],height);
 if(grades.some(g=>g.maximumGrade>.22))throw new Error('Absolute terrain surface exceeds full-width route grades');
 for(const prop of zone.props??[])if(prop.heightMode==='absolute')prop.y=(prop.y??0)+height(prop.x,prop.z)-before(prop.x,prop.z);
 terrain.sourceVersion='t1-source-surface-v1';zone.orvrLayout!.version=terrain.sourceVersion;validateT1(zone);
 return {zone,grades,supportGrades,nativeBuilt:false,appearanceApproved:false,drivingAccepted:false};
}
