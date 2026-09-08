import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
import type { WorldWalkableSurface } from '../src/world/Props';
import { craterGround } from '../src/world/CraterCity';
import { cityPositionBlocked } from '../src/world/CityNavigation';
import type { WorldCollider } from '../src/world/Props';
const city = JSON.parse(readFileSync('public/assets/maps/riftspire_capital.json','utf8')) as ZoneDefinition;
const surfaces: WorldWalkableSurface[] = city.props.flatMap(p => (p.walkableSurfaces??[]).map((s,i) => {
  const yaw=p.rotY??0,scale=p.scale??1,sx=scale*(p.scaleX??1),sy=scale*(p.scaleY??1),sz=scale*(p.scaleZ??1);
  const x=(s.x??0)*sx,z=(s.z??0)*sz;
  return {id:`${p.id}_${i}`,sourceObjectId:p.id,x:p.x+x*Math.cos(yaw)+z*Math.sin(yaw),z:p.z-x*Math.sin(yaw)+z*Math.cos(yaw),rotY:-yaw,
    width:s.width*sx,depth:s.depth*sz,fromY:(p.y??0)+(s.fromY??0)*sy,toY:(p.y??0)+(s.toY??0)*sy,axis:s.axis??'z'};
}));
const colliders: WorldCollider[] = city.props.flatMap(p => (p.colliders??[]).map((c,i) => {
  const yaw=p.rotY??0,s=p.scale??1,sx=s*(p.scaleX??1),sy=s*(p.scaleY??1),sz=s*(p.scaleZ??1);
  const x=(c.x??0)*sx,z=(c.z??0)*sz;
  return {id:`${p.id}_${i}`,x:p.x+x*Math.cos(yaw)+z*Math.sin(yaw),z:p.z-x*Math.sin(yaw)+z*Math.cos(yaw),
    width:c.width*sx,depth:c.depth*sz,rotY:-yaw-(c.rotY??0),minY:(p.y??0)+(c.minY??0)*sy,maxY:(p.y??0)+(c.maxY??20)*sy,blocksWhen:'always'};
}));
describe('Riftspire authored layout',()=>{
  it('retains the zone, graph, six districts and population targets',()=>{
    expect(city.size).toBe(1024);expect(city.zoneTriggers).toHaveLength(3);expect(city.cityDistricts).toHaveLength(6);
    expect(city.props.filter(p=>p.id?.includes('residence_')).length).toBeGreaterThanOrEqual(140);
    expect(new Set(city.props.filter(p=>p.id?.includes('residence_')).map(p=>p.model)).size).toBe(8);
    expect(city.props.filter(p=>p.id?.includes('suspended_hut_'))).toHaveLength(24);
    expect(city.craterCity?.lifts).toHaveLength(5);expect(city.craterCity?.interiors).toHaveLength(11);
  });
  it('breaks regular residential rings into different densities, widths and heights',()=>{
    const homes=city.props.filter(p=>p.id?.includes('residence_'));
    const counts=[0,-50,-105,-175,-245].map(y=>homes.filter(p=>p.y===y).length);
    expect(new Set(counts).size).toBeGreaterThanOrEqual(4);
    expect(Math.max(...counts)-Math.min(...counts)).toBeGreaterThan(20);
    expect(homes.some(p=>p.id?.endsWith('_annex'))).toBe(true);
    expect(city.props.some(p=>p.kind==='riftspire_rock_infill')).toBe(true);
    expect(new Set(homes.map(p=>p.scaleX)).size).toBeGreaterThan(30);
    expect(new Set(homes.map(p=>p.scaleY)).size).toBeGreaterThan(30);
    const gaps=[0,-50,-105,-175,-245].flatMap(y=>{
      const angles=homes.filter(p=>p.y===y).map(p=>Math.atan2(p.x,p.z)).sort((a,b)=>a-b);
      return angles.map((a,i)=>(angles[(i+1)%angles.length]-a+Math.PI*2)%(Math.PI*2));
    });
    expect(Math.max(...gaps)/Math.min(...gaps)).toBeGreaterThan(5);
  });
  it('keeps every varied residential threshold supported and clear',()=>{
    const failures:string[]=[];
    for(const p of city.props.filter(p=>p.id?.includes('residence_'))) {
      const balcony=p.walkableSurfaces![1],yaw=p.rotY??0;
      const z=(balcony.z??0)*(p.scaleZ??1);
      const entry={x:p.x+Math.sin(yaw)*z,y:p.y??0,z:p.z+Math.cos(yaw)*z};
      if(Math.abs(craterGround(entry.x,entry.z,entry.y,surfaces)-entry.y)>.85 || cityPositionBlocked(entry,colliders))failures.push(p.id!);
    }
    expect(failures).toEqual([]);
  });
  it('uses explicit heights, reviewed filenames and no primitive scenery',()=>{
    for(const p of city.props){expect(p.model,p.id).toMatch(/^prop_riftspire_/);expect(p.lodModels,p.id).toHaveLength(2);expect(p.heightMode,p.id).toBe('absolute');}
    for(const npc of city.npcs??[])expect(npc.approvedOnly,npc.id).toBe(true);
  });
  it('gives districts distinct activities and a substantial reviewed population',()=>{
    const dressing=city.props.filter(p=>p.id?.startsWith('riftspire_district_'));
    expect(dressing.length).toBeGreaterThanOrEqual(600);
    for(const [district,kinds] of Object.entries({ashgate:['arms_rack','hanging_cage'],market:['market_stall','apothecary','provision_stall'],warrens:['laundry_rig','communal_hearth'],works:['water_pump','ore_cart','chain_winch'],commons:['supply_cart','communal_hearth'],crown:['oath_monument','ritual_obelisk','war_table']})) {
      for(const kind of kinds)expect(dressing.some(p=>p.id?.startsWith(`riftspire_district_${district}_`)&&p.kind===`riftspire_${kind}`),`${district}: ${kind}`).toBe(true);
    }
    expect(city.ambientLife!.actors.length).toBeGreaterThanOrEqual(120);
    for(const actor of city.ambientLife!.actors)expect(actor.approvedOnly).toBe(true);
  });
  it('supports the whole footprint of every district assembly',()=>{
    const failures:string[]=[];
    for(const p of city.props.filter(p=>p.id?.startsWith('riftspire_district_'))) {
      const c=p.colliders![0],yaw=p.rotY??0,s=p.scale??1;
      for(const a of [-1,1])for(const b of [-1,1]) {
        const x=a*c.width*s/2,z=b*c.depth*s/2;
        const px=p.x+x*Math.cos(yaw)+z*Math.sin(yaw),pz=p.z-x*Math.sin(yaw)+z*Math.cos(yaw);
        if(Math.abs(craterGround(px,pz,p.y??0,surfaces)-(p.y??0))>.3)failures.push(p.id!);
      }
    }
    expect(failures).toEqual([]);
  });
  it('keeps broad street lanes and permanent bridge approaches free of dressing',()=>{
    const dressing=colliders.filter(c=>c.id?.startsWith('riftspire_district_'));
    const failures:string[]=[];
    for(const route of city.craterCity!.routes)for(let i=1;i<route.points.length;i++) {
      const a=route.points[i-1],b=route.points[i],length=Math.hypot(b.x-a.x,b.z-a.z),count=Math.ceil(length/3);
      const side=route.id.startsWith('terrace_')?3.1:Math.max(0,route.width/2-1.1);
      for(let j=0;j<=count;j++)for(const sign of [-1,0,1]) {
        const p={x:a.x+(b.x-a.x)*j/count+sign*side*(b.z-a.z)/length,y:a.y+(b.y-a.y)*j/count,z:a.z+(b.z-a.z)*j/count-sign*side*(b.x-a.x)/length};
        if(cityPositionBlocked(p,dressing)) {failures.push(route.id);break;}
      }
    }
    expect([...new Set(failures)]).toEqual([]);
  });
  it('keeps entrances, services, lift landings and capture positions supported',()=>{
    const points=[city.spawnPoint!,...city.craterCity!.interiors.map(i=>i.entry),...city.npcs!.map(n=>({...n,y:n.y??0})),...city.rvrObjectives!.map(o=>({...o,y:o.y??0})),...city.craterCity!.recovery];
    const failures=points.filter(p=>Math.abs(craterGround(p.x,p.z,p.y,surfaces)-p.y)>.85);
    expect(failures).toEqual([]);
  });
  it('has continuous terrace, bridge and redundant stair routes',()=>{
    const failures:string[]=[];
    for(const route of city.craterCity!.routes)for(let i=1;i<route.points.length;i++){
      const a=route.points[i-1],b=route.points[i],n=Math.ceil(Math.hypot(b.x-a.x,b.z-a.z)/2);
      for(let j=0;j<=n;j++){
        const t=j/n,x=a.x+(b.x-a.x)*t,z=a.z+(b.z-a.z)*t,y=a.y+(b.y-a.y)*t;
        if(Math.abs(craterGround(x,z,y,surfaces)-y)>1) {failures.push(`${route.id} @ ${x.toFixed(1)},${y.toFixed(1)},${z.toFixed(1)}`);break;}
      }
    }
    expect(failures).toEqual([]);
  });
  it('orders bridgehead, vault and throne and separates 18-person formations',()=>{
    const o=city.rvrObjectives!;expect(o.map(o=>o.label)).toEqual(['Chainwake Bridgehead','Blackvein Vault','Riftspire Throne']);
    expect(o[1].requiresObjectiveIds).toEqual([o[0].id]);expect(o[2].requiresObjectiveIds).toEqual([o[0].id,o[1].id]);
    for(const formation of city.craterCity!.formations){expect(formation.teams.map(t=>t.length)).toEqual([18,18]);for(const p of formation.teams.flat())expect(craterGround(p.x,p.z,p.y,surfaces)).toBe(p.y);}
  });
  it('keeps stair mouths, public doors and battle formations clear of railings',()=>{
    const points=[...city.craterCity!.interiors.map(i=>i.entry),...city.craterCity!.formations.flatMap(f=>f.teams.flat())];
    for(const route of city.craterCity!.routes.filter(r=>r.id.startsWith('stairs_'))) {
      for(let i=1;i<route.points.length;i++) {
        const a=route.points[i-1],b=route.points[i],n=Math.ceil(Math.hypot(b.x-a.x,b.z-a.z));
        for(let j=0;j<=n;j++)points.push({x:a.x+(b.x-a.x)*j/n,y:a.y+(b.y-a.y)*j/n,z:a.z+(b.z-a.z)*j/n});
      }
    }
    expect(points.filter(p=>cityPositionBlocked(p,colliders))).toEqual([]);
  });
});
