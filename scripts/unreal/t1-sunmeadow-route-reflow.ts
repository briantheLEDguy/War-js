/** Terrain-qualified Sunmeadow route revision; no active/native content is written here. */
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {createOrvrGridHeightSampler,type TerrainPoint} from '../../shared/orvrTerrain';
import {spatialSegmentInside} from '../../shared/worldSpatial';
import {battlefieldGrades} from './t1-battlefield-grades';
import {contourRoutes} from './t1-contour-routes';
import {tacticalSpurRecipes} from './t1-tactical-spurs';
import {containsSpatialPoint} from '../../shared/worldSpatial';
import {validateT1} from './t1-layouts';
import {curveRouteNetwork,mapRouteEdges,projectRouteJoin,routeEdgeKey,type RouteMove} from './t1-route-network';

const moves:RouteMove[]=[
 {from:{x:75,z:190},to:{x:130,z:210}},
 {from:{x:-60,z:-190},to:{x:-130,z:-215}},
 {from:{x:75,z:-170},to:{x:120,z:-250}},
 {from:{x:-310,z:-205},to:{x:-300,z:-260}},
 {from:{x:300,z:-180},to:{x:310,z:-300}},
 {from:{x:290,z:150},to:{x:325,z:95}},
];

export function sunmeadowRouteReflow(original:ZoneDefinition) {
 if(original.id!=='sunmeadow_march'||!original.paths||original.paths.length<5||!original.spatial||!original.orvrLayout?.terrain.naturalField
   ||original.paths.slice(0,5).some((p,i)=>!p.id.endsWith(['_advance','_ridge_flank','_outer_flank','_rotation_1','_rotation_2'][i])))throw new Error('Route reflow requires explicit Sunmeadow battlefield controls');
 if(original.orvrLayout.terrain.balancedCorridors)throw new Error('Preserve existing balanced route revision');
 const zone=structuredClone(original),paths=zone.paths!,terrain=zone.orvrLayout!.terrain;
 const before=createOrvrGridHeightSampler(original.orvrLayout.terrain,original.size,original.segments,original.spatial);
 const frozen=paths[0].points.slice(1).map((p,i)=>routeEdgeKey(p,paths[0].points[i]));
 // Preserve the western overlook approaches and complete military entrance geometry.
 frozen.push(routeEdgeKey({x:-285,z:-70},{x:-310,z:130}),routeEdgeKey({x:-310,z:130},{x:-60,z:180}),routeEdgeKey({x:-60,z:180},{x:-60,z:-15}));
 const network=curveRouteNetwork(paths.slice(0,5),moves,frozen);
 const primary=new Set(paths.slice(0,5).map(p=>p.id));
 const branch=(points:TerrainPoint[],limit=12)=>{
  const first=projectRouteJoin(points[0],network.curves,limit),last=projectRouteJoin(points.at(-1)!,network.curves,limit),lengths=[0];
  for(let i=1;i<points.length;i++)lengths.push(lengths.at(-1)!+Math.hypot(points[i].x-points[i-1].x,points[i].z-points[i-1].z));
  if(!lengths.at(-1))throw new Error('Route branch has no length');
  return points.map((p,i)=>{const t=lengths[i]/lengths.at(-1)!;return {...p,
   x:p.x+(first.x-points[0].x)*(1-t)+(last.x-points.at(-1)!.x)*t,
   z:p.z+(first.z-points[0].z)*(1-t)+(last.z-points.at(-1)!.z)*t};});
 };
 for(const p of paths)p.points=primary.has(p.id)?mapRouteEdges(p.points,network.curves):branch(p.points);
 for(const c of terrain.clearCorridors)c.points=primary.has(c.id)?mapRouteEdges(c.points,network.curves):branch(c.points,c.id==='east_shoulder_counter'?40:12);
 for(const route of zone.orvrLayout!.caravanRoutes) {
  route.points=mapRouteEdges(route.points,network.curves);
  route.lengthMetres=route.points.slice(1).reduce((s,p,i)=>s+Math.hypot(p.x-route.points[i].x,p.z-route.points[i].z),0);
  if(route.lengthMetres<350||route.lengthMetres>750)throw new Error('Reflow supply itinerary leaves pacing band');
 }
 terrain.balancedCorridors=true;
 terrain.clearCorridors.find(c=>c.id.endsWith('_rotation_2'))!.feather=64;
 const height=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
 for(const recipe of tacticalSpurRecipes(zone.id).searches)for(const counter of contourRoutes(recipe,height,(p,r)=>containsSpatialPoint(zone.spatial!,p,r)).routes) {
  const path=paths.find(p=>p.id===counter.id);if(!path)throw new Error('Retained counter identity is absent');path.points=counter.points;
 }
 const anchors=[...zone.orvrLayout!.keeps,...zone.orvrLayout!.stagingCamps,...(zone.spawnPoint?[zone.spawnPoint]:[]),
  ...(zone.zoneTriggers??[]).flatMap(t=>t.arrivalPoint?[t,t.arrivalPoint]:[t])];
 if(anchors.some(p=>Math.abs(height(p.x,p.z)-before(p.x,p.z))>.01))throw new Error('Route reflow moves a retained military or arrival footing');
 for(const objective of zone.orvrLayout!.battlefieldObjectives)objective.y=height(objective.x,objective.z);
 for(const prop of zone.props??[])if(prop.heightMode==='absolute')prop.y=(prop.y??0)+height(prop.x,prop.z)-before(prop.x,prop.z);
 const ids=new Set(paths.map(p=>p.id));
 const graded=[...paths,...zone.orvrLayout!.caravanRoutes,...terrain.clearCorridors.filter(c=>!ids.has(c.id)).map(c=>({id:c.id,points:c.points,width:c.id.includes('_pocket_')?6:12}))];
 if(graded.some(p=>p.points.slice(1).some((b,i)=>!spatialSegmentInside(zone.spatial!,p.points[i],b,p.width/2))))throw new Error('Route reflow leaves admitted playable ground');
 const grades=battlefieldGrades(graded,height);if(grades.some(g=>g.maximumGrade>.22))throw new Error('Route reflow exceeds full-width grade limits');
 terrain.sourceVersion='t1-sunmeadow-route-reflow-v1';zone.orvrLayout!.version=terrain.sourceVersion;validateT1(zone);
 return {zone,grades,curves:network.curves,movedNodes:structuredClone(moves),nativeBuilt:false,appearanceApproved:false,drivingAccepted:false};
}
