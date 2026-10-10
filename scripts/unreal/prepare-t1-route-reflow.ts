/** Immutable source revision; native candidates and active/owner maps are never edited here. */
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {createOrvrGridHeightSampler} from '../../shared/orvrTerrain';
import {sunmeadowRouteReflow} from './t1-sunmeadow-route-reflow';
import {outdoorTerrain,outdoorRoads} from './world-portals';
import {canonicalJson,sha256} from './content-contract';
import {repoRoot,isMain} from './toolchain';

export function prepareRouteReflow(parentRevision?:string):void {
 const base=path.join(repoRoot,'artifacts/unreal/t1-redesign');
 if(parentRevision&&!/^[a-f0-9]{12}$/.test(parentRevision))throw new Error('Invalid qualified reflow parent');
 const bytes=readFileSync(parentRevision?path.join(base,'battlefield',parentRevision,'source.json'):path.join(base,'battlefield-source-latest.json'));
 const parent=JSON.parse(bytes.toString()),qualified=parent.directory+'/source.json';
 if(sha256(readFileSync(path.join(repoRoot,qualified)))!==sha256(bytes))throw new Error('Qualified reflow parent differs');
 if(parent.study==='sunmeadow-route-reflow')throw new Error('Preserve existing route reflow source');
 if(parent.zones.length!==2||parent.zones[0].zone!=='sunmeadow_march'||parent.zones[1].zone!=='cinderfen_outskirts')throw new Error('Route reflow admits the retained first pair only');
 const inputs:Record<string,string>={...parent.inputs,...parent.files,[qualified]:sha256(bytes)};
 // One deliberate compatible sampler revision: its new corridor mode defaults absent on legacy terrain.
 const previousSamplerSha256=inputs['shared/orvrTerrain.ts'];
 if(!previousSamplerSha256)throw new Error('Reflow parent lacks a pinned shared sampler');
 inputs['shared/orvrTerrain.ts']=sha256(readFileSync(path.join(repoRoot,'shared/orvrTerrain.ts')));
 for(const [file,digest] of Object.entries(inputs))if(sha256(readFileSync(path.join(repoRoot,file)))!==digest)throw new Error('Preserve changed reflow parent binding: '+file);
 const read=(file:string)=>JSON.parse(readFileSync(path.join(repoRoot,file),'utf8'));
 const study=sunmeadowRouteReflow(read(parent.directory+'/sunmeadow_march.json'));
 const zones:ZoneDefinition[]=[study.zone,read(parent.directory+'/cinderfen_outskirts.json')];
 const pockets=Object.fromEntries(zones.map(z=>{
  const rows=read(parent.directory+'/'+z.id+'_pockets.json');
  const height=createOrvrGridHeightSampler(z.orvrLayout!.terrain,z.size,z.segments,z.spatial);
  for(const p of rows) {
   const corridor=z.orvrLayout!.terrain.clearCorridors.find(c=>c.id===p.id+'_approach');
   if(!corridor)throw new Error('Reflow pocket lacks its retained approach');if(z.id===study.zone.id)p.approach=structuredClone(corridor.points);
   if(Math.abs(height(p.x,p.z)-p.bedY)>.01)throw new Error('Reflow moves a retained pocket bed');
   if(p.cosmeticWater)for(let i=0;i<96;i++)if(height(p.x+Math.cos(i*Math.PI/48)*(p.radius+60),p.z+Math.sin(i*Math.PI/48)*(p.radius+60))<p.waterY+.03)throw new Error('Reflow opens a retained water basin');
  }
  return [z.id,rows];
 }));
 const links=Object.fromEntries(zones.map(z=>[z.id,read(parent.directory+'/'+z.id+'_links.json').map((link:{id:string;points:unknown[]})=>{
  if(z.id!==study.zone.id)return link;
  const corridor=z.orvrLayout!.terrain.clearCorridors.find(c=>c.id===link.id);
  if(!corridor)throw new Error('Reflow link lacks its retained ground corridor');return {...link,points:structuredClone(corridor.points)};
 })]));
 const maps:ZoneDefinition[]=read('artifacts/unreal/t1-redesign/plan.json').zones.map((z:{id:string})=>read(parent.directory+'/maps/'+z.id+'.json'));
 for(const z of zones)maps[maps.findIndex(m=>m.id===z.id)]=z;
 for(const z of maps)for(const trigger of z.zoneTriggers??[]) {
  if(!zones.some(s=>s.id===trigger.targetZoneId))continue;
  const reciprocal=maps.find(m=>m.id===trigger.targetZoneId)!.zoneTriggers!.find(t=>t.targetZoneId===z.id);
  if(!reciprocal?.arrivalPoint)throw new Error('Reflow lacks a reciprocal arrival');trigger.targetSpawn={...reciprocal.arrivalPoint};
 }
 for(const file of ['shared/orvrTerrain.ts','scripts/unreal/t1-route-network.ts','scripts/unreal/t1-sunmeadow-route-reflow.ts','scripts/unreal/prepare-t1-route-reflow.ts'])inputs[file]=sha256(readFileSync(path.join(repoRoot,file)));
 const signature=sha256(canonicalJson({parent:parent.signature,inputs,zones,pockets,links,curves:study.curves}));
 const directory=path.join(base,'battlefield',signature.slice(0,12));
 if(existsSync(directory))throw new Error('Preserve existing reflow revision');mkdirSync(path.join(directory,'maps'),{recursive:true});
 const files:Record<string,string>={};
 const save=(name:string,data:unknown)=>{const output=JSON.stringify(data),file=path.join(directory,name);writeFileSync(file,output);files[path.relative(repoRoot,file).replaceAll('\\','/')]=sha256(output);};
 for(const z of zones) {
  save(z.id+'.json',z);save(z.id+'_terrain.json',outdoorTerrain(z));save(z.id+'_roads.json',outdoorRoads(z));save(z.id+'_pockets.json',pockets[z.id]);save(z.id+'_links.json',links[z.id]);
 }
 for(const z of maps)save('maps/'+z.id+'.json',z);
 const rows=parent.zones.map((row:{zone:string})=>row.zone===study.zone.id?{zone:row.zone,maximumGrade:Math.max(...study.grades.map(g=>g.maximumGrade)),routeGrades:study.grades,movedNodes:study.movedNodes,sharedEdges:study.curves.length,appearanceApproved:false,drivingAccepted:false}:row);
 const receipt={...parent,signature,directory:path.relative(repoRoot,directory).replaceAll('\\','/'),parentTerrain:parent.signature,study:'sunmeadow-route-reflow',previousSamplerSha256,inputs,files,zones:rows,routeCoordinatesChanged:true,terrainChanged:true,nativeBuilt:false,activeMapsChanged:false,appearanceApproved:false};
 writeFileSync(path.join(directory,'source.json'),canonicalJson(receipt));writeFileSync(path.join(base,'battlefield-source-latest.json'),canonicalJson(receipt));
 console.log(JSON.stringify({signature:signature.slice(0,12),maximumGrade:rows[0].maximumGrade,nativeBuilt:false}));
}
if(isMain(import.meta.url))prepareRouteReflow(process.argv.find(a=>a.startsWith('--parent='))?.slice(9));
