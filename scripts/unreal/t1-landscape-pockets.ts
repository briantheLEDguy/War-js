import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { containsSpatialPoint, distanceToSpatialSegment } from '../../shared/worldSpatial';
import { battlefieldGrades } from './t1-battlefield-grades';

export interface LandscapePocket {
  id: string; label: string; purpose: string; x: number; z: number; radius: number; waterY: number; bedY: number;
  approach: Array<{ x: number; z: number; y: number }>;
  cosmeticWater: boolean; gameplayAccepted: false;
}
/** Fresh shallow terrain pockets: no hazards, rewards, quest changes or lair completion are implied. */
export function landscapePockets(original: ZoneDefinition): { zone: ZoneDefinition; pockets: LandscapePocket[] } {
  const zone = structuredClone(original), terrain = zone.orvrLayout!.terrain;
  if (!zone.spatial || !terrain.naturalField || !zone.paths) throw new Error('Pockets require a connected battlefield candidate');
  const specifications = zone.id === 'sunmeadow_march' ? [
    ['brook_meadow', 'Brookmeadow Pool', 'A shallow meadow pool beside the field counterapproach', -240, -105, 9],
    ['eastern_hollow', 'Hearthroot Hollow', 'Water collects below the eastern pasture; a quiet exploration pocket', 330, -225, 10],
  ] : zone.id === 'cinderfen_outskirts' ? [
    ['amber_runoff', 'Amber Runoff', 'Reflective amber runoff between the advance and peat flank', -230, -245, 10],
    ['rust_sedge', 'Rustsedge Pools', 'Sedge collects around shallow peat water behind the lower flank', -65, -400, 11],
    ['mineral_margin', 'Embervein Seep', 'A pale mineral bank gives way to a quiet geothermal seep', 190, -390, 10],
    ['western_peat', 'Cinderreed Hollow', 'A small reed-framed pool beside the outer basin margin', -390, -340, 9],
  ] : [];
  if (!specifications.length) throw new Error('Pocket authoring admits the first native pair');
  const nearestRoad=(p:{x:number;z:number})=>zone.paths!.slice(0,3).flatMap(road=>road.points.slice(1).map((b,i)=>{
    const a=road.points[i],dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.z-a.z)*dz)/(dx*dx+dz*dz)));
    const x=a.x+dx*t,z=a.z+dz*t;return {x,z,distance:Math.hypot(p.x-x,p.z-z)};
  })).sort((a,b)=>a.distance-b.distance)[0];
  const pockets: LandscapePocket[] = [];
  for (const [key, label, purpose, cx, cz, radiusValue] of specifications) {
    const radius = radiusValue as number, h = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
    const candidates: Array<{ x: number; z: number; score: number }> = [];
    for (let dx = -80; dx <= 80; dx += 8) for (let dz = -80; dz <= 80; dz += 8) {
      const x = (cx as number) + dx, z = (cz as number) + dz, p = { x, z };
      if (!containsSpatialPoint(zone.spatial, p, radius + 24)
        || terrain.clearCorridors.some(c => c.points.slice(1).some((b, j) => distanceToSpatialSegment(p, c.points[j], b) < radius + c.radius + 23))
        || terrain.flattenAreas.some(a => Math.hypot(x-a.x,z-a.z) < radius + a.radius + 24)
        || [...(zone.npcs ?? []), ...zone.enemies, ...(zone.resourceNodes ?? []), ...(zone.craftingStations ?? []), ...(zone.zoneTriggers ?? [])].some(a => Math.hypot(x-a.x,z-a.z) < radius+18)
        || pockets.some(a => Math.hypot(x-a.x,z-a.z) < radius+a.radius+35)) continue;
      const samples = Array.from({ length: 16 }, (_, i) => h(x+Math.cos(i*Math.PI/8)*radius,z+Math.sin(i*Math.PI/8)*radius));
      const range = Math.max(...samples)-Math.min(...samples);
      const road=nearestRoad(p),grade=Math.abs(h(x,z)-h(road.x,road.z))/road.distance;
      if (range > 2.5 || grade > .12 || road.distance > 200) continue;
      candidates.push({ x, z, score: range*16 + Math.hypot(dx,dz)*.5 + grade*150 });
    }
    const baseAreas = structuredClone(terrain.flattenAreas), baseCorridors = structuredClone(terrain.clearCorridors);
    let admitted: LandscapePocket | undefined;
    for (const requireWater of [true,false]) {
    for (const site of candidates.sort((a,b) => a.score-b.score).slice(0,80)) {
      terrain.flattenAreas = structuredClone(baseAreas); terrain.clearCorridors = structuredClone(baseCorridors);
      const waterY = h(site.x,site.z)-1, bedY = waterY-.45, id = zone.id+'_pocket_'+key;
      terrain.flattenAreas.push({ id, x: site.x, z: site.z, radius, feather: 52, height: bedY, preserveFooting: true });
      const start=nearestRoad(site), startY=h(start.x,start.z);
      const approach=Array.from({length:5},(_,i)=>({x:start.x+(site.x-start.x)*i/4,z:start.z+(site.z-start.z)*i/4,y:startY+(bedY-startY)*i/4}));
      terrain.clearCorridors.push({id:id+'_approach',points:approach,radius:12,height:0,feather:64});
      const grounded=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
      const closedBasin = !Array.from({length:64},(_,i)=>grounded(site.x+Math.cos(i*Math.PI/32)*(radius+60),site.z+Math.sin(i*Math.PI/32)*(radius+60))).some(y=>y<waterY+.08);
      if(requireWater && !closedBasin) continue;
      const existing=new Set(zone.paths.map(p=>p.id));
      const routes=[...zone.paths,...terrain.clearCorridors.filter(c=>!existing.has(c.id)).map(c=>({id:c.id,width:c.id.includes('_pocket_')?6:12,points:c.points}))];
      if (battlefieldGrades(routes,grounded).some(g=>g.maximumGrade>.22)) continue;
      admitted={id,label:label as string,purpose:purpose as string,x:site.x,z:site.z,radius,waterY,bedY,approach,cosmeticWater:closedBasin,gameplayAccepted:false};
      break;
    }
    if (admitted) break;
    }
    if (!admitted) throw new Error('No pocket preserves connected route grades: '+key);
    pockets.push(admitted);
  }
  return {zone,pockets};
}
