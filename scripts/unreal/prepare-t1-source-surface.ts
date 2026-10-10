/** Immutable source revision; native candidates and active/owner maps are never edited here. */
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {createOrvrGridHeightSampler} from '../../shared/orvrTerrain';
import {sourceTerrainSurface} from './t1-source-surface';
import {qualifySurfaceBake} from './t1-surface-bake';
import {outdoorTerrain,outdoorRoads} from './world-portals';
import {canonicalJson,sha256} from './content-contract';
import {repoRoot,isMain} from './toolchain';

export function prepareSourceSurface(parentRevision?:string,bakeRevision?:string,supportParent?:string):void {
 const base=path.join(repoRoot,'artifacts/unreal/t1-redesign');
 if(parentRevision&&!/^[a-f0-9]{12}$/.test(parentRevision))throw new Error('Invalid qualified surface parent');
 const bytes=readFileSync(parentRevision?path.join(base,'battlefield',parentRevision,'source.json'):path.join(base,'battlefield-source-latest.json'));
 const parent=JSON.parse(bytes.toString()),qualified=parent.directory+'/source.json';
 if(sha256(readFileSync(path.join(repoRoot,qualified)))!==sha256(bytes))throw new Error('Qualified surface parent differs');
 if(parent.study==='absolute-landform-surface')throw new Error('Preserve existing absolute surface source');
 if(parent.zones.length!==2||parent.zones[0].zone!=='sunmeadow_march'||parent.zones[1].zone!=='cinderfen_outskirts')throw new Error('Absolute surface admits the retained first pair only');
 const inputs:Record<string,string>={...parent.inputs,...parent.files,[qualified]:sha256(bytes)};
 // One explicit compatible field revision; absolute surfaces are absent on legacy terrain.
 const previousFieldSha256=inputs['shared/terrainField.ts'];
 if(!previousFieldSha256)throw new Error('Surface parent lacks a pinned shared sampler');
 inputs['shared/terrainField.ts']=sha256(readFileSync(path.join(repoRoot,'shared/terrainField.ts')));
 for(const [file,digest] of Object.entries(inputs))if(sha256(readFileSync(path.join(repoRoot,file)))!==digest)throw new Error('Preserve changed surface parent binding: '+file);
 const read=(file:string)=>JSON.parse(readFileSync(path.join(repoRoot,file),'utf8'));
 const bakeFile=bakeRevision??'artifacts/unreal/t1-redesign/eroded-surface-samples/full-height-study/surface-bake-receipt.json';
 const {surface,inputs:bakeInputs,apron}=qualifySurfaceBake(parent.signature,bakeFile,file=>readFileSync(path.join(repoRoot,file)));
 Object.assign(inputs,bakeInputs);
 if(!supportParent||!/^[a-f0-9]{12}$/.test(supportParent))throw new Error('Absolute surfaces require a qualified retained native approach parent');
 const supportFile='artifacts/unreal/t1-redesign/battlefield-'+supportParent+'.json',native=read(supportFile);
 if(!native.signature?.startsWith(supportParent)||native.inputs?.sourceSignature!==parent.signature
  ||native.zones?.length!==2||native.zones[0].id!=='sunmeadow_march'||native.zones[1].id!=='cinderfen_outskirts')throw new Error('Population approach parent differs from the qualified source');
 inputs[supportFile]=sha256(readFileSync(path.join(repoRoot,supportFile)));
 for(const row of native.zones) {
  const file=row.sourceDirectory+'/'+row.id+'.json';
  if(native.inputs.sourceHashes[file]!==parent.files[file]||sha256(readFileSync(path.join(repoRoot,file)))!==parent.files[file])throw new Error('Retained native approach source differs');
 }
 for(const [packageName,digest] of Object.entries(native.packageHashes) as [string,string][]) {
  if(!packageName.startsWith('/Game/WorldRebuild/')||packageName.includes('..')||packageName.includes('\\'))throw new Error('Invalid retained native approach package');
  const file='unreal/AegisWar/Content/'+packageName.slice(6)+'.umap';
  if(sha256(readFileSync(path.join(repoRoot,file)))!==digest)throw new Error('Retained native approach package changed');inputs[file]=digest;
 }
 const support=native.zones[0].population.map((p:{id:string;approach:number[][]})=>({id:p.id+'_retained_support',width:4,points:p.approach.map(a=>({x:a[1]/100,z:a[0]/100}))}));
 const study=sourceTerrainSurface(read(parent.directory+'/sunmeadow_march.json'),surface,apron,support);
 const zones:ZoneDefinition[]=[study.zone,read(parent.directory+'/cinderfen_outskirts.json')];
 const pockets=Object.fromEntries(zones.map(z=>{
  const rows=read(parent.directory+'/'+z.id+'_pockets.json');
  const height=createOrvrGridHeightSampler(z.orvrLayout!.terrain,z.size,z.segments,z.spatial);
  for(const p of rows) {
   const corridor=z.orvrLayout!.terrain.clearCorridors.find(c=>c.id===p.id+'_approach');
   if(!corridor)throw new Error('Surface pocket lacks its retained approach');
   if(Math.abs(height(p.x,p.z)-p.bedY)>.01)throw new Error('Surface moves a retained pocket bed');
   if(p.cosmeticWater)for(let i=0;i<96;i++)if(height(p.x+Math.cos(i*Math.PI/48)*(p.radius+60),p.z+Math.sin(i*Math.PI/48)*(p.radius+60))<p.waterY+.03)throw new Error('Surface opens a retained water basin');
  }
  return [z.id,rows];
 }));
 const links=Object.fromEntries(zones.map(z=>[z.id,read(parent.directory+'/'+z.id+'_links.json')]));
 const maps:ZoneDefinition[]=read('artifacts/unreal/t1-redesign/plan.json').zones.map((z:{id:string})=>read(parent.directory+'/maps/'+z.id+'.json'));
 for(const z of zones)maps[maps.findIndex(m=>m.id===z.id)]=z;
 for(const z of maps)for(const trigger of z.zoneTriggers??[]) {
  if(!zones.some(s=>s.id===trigger.targetZoneId))continue;
  const reciprocal=maps.find(m=>m.id===trigger.targetZoneId)!.zoneTriggers!.find(t=>t.targetZoneId===z.id);
  if(!reciprocal?.arrivalPoint)throw new Error('Surface lacks a reciprocal arrival');trigger.targetSpawn={...reciprocal.arrivalPoint};
 }
 for(const file of ['shared/terrainField.ts','shared/terrainSurface.ts','scripts/unreal/t1-source-surface.ts','scripts/unreal/t1-surface-bake.ts','scripts/unreal/prepare-t1-source-surface.ts'])inputs[file]=sha256(readFileSync(path.join(repoRoot,file)));
 const signature=sha256(canonicalJson({parent:parent.signature,inputs,zones,pockets,links,surface:study.zone.orvrLayout!.terrain.naturalField!.surface}));
 const directory=path.join(base,'battlefield',signature.slice(0,12));
 if(existsSync(directory))throw new Error('Preserve existing surface revision');mkdirSync(path.join(directory,'maps'),{recursive:true});
 const files:Record<string,string>={};
 const save=(name:string,data:unknown)=>{const output=JSON.stringify(data),file=path.join(directory,name);writeFileSync(file,output);files[path.relative(repoRoot,file).replaceAll('\\','/')]=sha256(output);};
 for(const z of zones) {
  save(z.id+'.json',z);save(z.id+'_terrain.json',outdoorTerrain(z));save(z.id+'_roads.json',outdoorRoads(z));save(z.id+'_pockets.json',pockets[z.id]);save(z.id+'_links.json',links[z.id]);
 }
 for(const z of maps)save('maps/'+z.id+'.json',z);
 const rows=parent.zones.map((row:{zone:string})=>row.zone===study.zone.id?{zone:row.zone,maximumGrade:Math.max(...study.grades.map(g=>g.maximumGrade)),routeGrades:study.grades,absoluteSurfaceSamples:surface.samples.length,supportRoutes:support.length,supportGrades:study.supportGrades,appearanceApproved:false,drivingAccepted:false}:row);
 const receipt={...parent,signature,directory:path.relative(repoRoot,directory).replaceAll('\\','/'),parentTerrain:parent.signature,study:'absolute-landform-surface',previousFieldSha256,inputs,files,zones:rows,bakeFile,groundingApronMetres:apron,retainedNativeApproachParent:native.signature,routeCoordinatesChanged:false,terrainChanged:true,nativeBuilt:false,activeMapsChanged:false,appearanceApproved:false};
 writeFileSync(path.join(directory,'source.json'),canonicalJson(receipt));writeFileSync(path.join(base,'battlefield-source-latest.json'),canonicalJson(receipt));
 console.log(JSON.stringify({signature:signature.slice(0,12),maximumGrade:rows[0].maximumGrade,nativeBuilt:false}));
}
if(isMain(import.meta.url))prepareSourceSurface(process.argv.find(a=>a.startsWith('--parent='))?.slice(9),process.argv.find(a=>a.startsWith('--bake='))?.slice(7),process.argv.find(a=>a.startsWith('--support-parent='))?.slice(17));
