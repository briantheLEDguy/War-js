/** Immutable first-pair scenery admission; playable terrain, roads and military coordinates remain retained. */
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {extendTerrainOwnership,validateDistantMountains} from './t1-distant-scenery';
import {outdoorTerrain,portalPlan} from './world-portals';
import {canonicalJson,sha256} from './content-contract';
import {isMain,repoRoot} from './toolchain';

const COMPATIBLE_READERS=['scripts/unreal/t1-road-conformance.ts','scripts/unreal/t1-source-relief.ts',
 'scripts/unreal/t1-source-surface.ts','scripts/unreal/world-portals.ts','shared/orvrTerrain.ts'];
const portable=(p:string)=>typeof p==='string'&&!path.isAbsolute(p)&&!p.includes('\\')&&!p.split('/').some(v=>!v||v==='.'||v==='..');

export function prepareDistantScenery(parentRevision:string,bakeFile:string):void {
 if(!/^[a-f0-9]{12}$/.test(parentRevision)||!portable(bakeFile)||!bakeFile.startsWith('artifacts/unreal/t1-redesign/distant-native-mountain-bakes/'))throw new Error('Invalid qualified distant scenery input');
 const base=path.join(repoRoot,'artifacts/unreal/t1-redesign'),read=(file:string)=>readFileSync(path.join(repoRoot,file)),json=(file:string)=>JSON.parse(read(file).toString());
 const parentFile='artifacts/unreal/t1-redesign/battlefield/'+parentRevision+'/source.json',parent=json(parentFile),bake=json(bakeFile);
 if(!parent.signature?.startsWith(parentRevision)||parent.directory!=='artifacts/unreal/t1-redesign/battlefield/'+parentRevision||parent.study!=='terrain-conformed-roads'||parent.distantScenery)
  throw new Error('Distant scenery requires a retained conformed-road source');
 if(parent.zones?.length!==2||parent.zones[0].zone!=='sunmeadow_march'||parent.zones[1].zone!=='cinderfen_outskirts')throw new Error('Distant scenery admits the first pair only');
 const inputs:Record<string,string>={...parent.inputs,...parent.files,[parentFile]:sha256(read(parentFile))},previousCompatibleBindings:Record<string,string>={};
 for(const [file,digest] of Object.entries(inputs)){
  const current=sha256(read(file));if(current===digest)continue;
  if(!COMPATIBLE_READERS.includes(file))throw new Error('Preserve changed scenery parent binding: '+file);
  previousCompatibleBindings[file]=digest;inputs[file]=current;
 }
 if(bake.parentSignature!==parent.signature||bake.licensedDerivative!==true||bake.distributionApproved!==false||bake.playable!==false||bake.collisionEnabled!==false
  ||bake.innerBoundaryHeightErrorMetres!==0||bake.mountains?.length!==4||!portable(bake.file)||!bake.file.startsWith(path.posix.dirname(bakeFile)+'/')||sha256(read(bake.file))!==bake.sha256)
  throw new Error('Distant bake identity, isolation or fingerprint differs');
 const original=json(parent.directory+'/sunmeadow_march.json') as ZoneDefinition,zone=extendTerrainOwnership(original,bake.proposedContentBounds);
 const mountainFootprints=validateDistantMountains(zone,bake.mountains);
 const skirt=json(bake.file);
 if(skirt.positions?.length!==bake.vertices||skirt.indices?.length!==bake.triangles*3||bake.vertices>50000||bake.triangles>100000
  ||skirt.normals?.length!==bake.vertices||skirt.uvs?.length!==bake.vertices||skirt.positions.some((p:number[])=>p.length!==3||!p.every(Number.isFinite))
  ||skirt.indices.some((i:number)=>!Number.isInteger(i)||i<0||i>=bake.vertices))throw new Error('Invalid bounded distant skirt geometry');
 for(const [file,digest] of Object.entries(bake.inputs) as [string,string][]){if(!portable(file)||sha256(read(file))!==digest)throw new Error('Distant source package changed: '+file);inputs[file]=digest;}
 inputs[bakeFile]=sha256(read(bakeFile));
 // An enlarged content box must not change any playable native triangle byte.
 if(sha256(JSON.stringify(outdoorTerrain(zone)))!==parent.files[parent.directory+'/sunmeadow_march_terrain.json'])throw new Error('Distant ownership changes playable terrain');
 const maps:ZoneDefinition[]=json('artifacts/unreal/t1-redesign/plan.json').zones.map((r:{id:string})=>json(parent.directory+'/maps/'+r.id+'.json'));
 maps[maps.findIndex(m=>m.id===zone.id)]=zone;
 const portals=portalPlan(maps);
 if(portals.zones.length!==32||portals.routes.length!==70)throw new Error('Distant ownership changes the campaign graph');
 for(const file of ['scripts/unreal/prepare-t1-distant-scenery.ts','scripts/unreal/t1-distant-scenery.ts','shared/worldSpatial.ts',...COMPATIBLE_READERS])inputs[file]=sha256(read(file));
 const distantScenery={sunmeadow_march:bakeFile},signature=sha256(canonicalJson({parent:parent.signature,inputs,zone,distantScenery,portals}));
 const directory=path.join(base,'battlefield',signature.slice(0,12));if(existsSync(directory))throw new Error('Preserve existing distant scenery revision');
 mkdirSync(path.join(directory,'maps'),{recursive:true});const files:Record<string,string>={};
 const save=(relative:string,bytes:Buffer|string)=>{const target=path.join(directory,relative);writeFileSync(target,bytes);files[path.relative(repoRoot,target).replaceAll('\\','/')]=sha256(bytes);};
 for(const file of Object.keys(parent.files)){
  const relative=path.relative(path.join(repoRoot,parent.directory),path.join(repoRoot,file)).replaceAll('\\','/');
  if(!portable(relative))throw new Error('Scenery parent file escapes qualified source');
  save(relative,relative==='sunmeadow_march.json'||relative==='maps/sunmeadow_march.json'?JSON.stringify(zone):read(file));
 }
 save('campaign-portals.json',JSON.stringify(portals));
 const receipt={...parent,signature,directory:path.relative(repoRoot,directory).replaceAll('\\','/'),parentTerrain:parent.signature,study:'distant-native-scenery',
  inputs,files,distantScenery,previousCompatibleBindings,mountainFootprints,terrainChanged:false,roadMeshesBytePreserved:true,routeCoordinatesChanged:false,
  capitalOriginsRetained:true,nativeBuilt:false,appearanceApproved:false,activeMapsChanged:false,distributionApproved:false};
 writeFileSync(path.join(directory,'source.json'),canonicalJson(receipt));writeFileSync(path.join(base,'battlefield-source-latest.json'),canonicalJson(receipt));
 console.log(JSON.stringify({signature:signature.slice(0,12),terrainBytePreserved:true,campaignZones:32,reciprocalRoutes:70,nativeBuilt:false}));
}
if(isMain(import.meta.url)){
 const parent=process.argv.find(a=>a.startsWith('--parent='))?.slice(9),bake=process.argv.find(a=>a.startsWith('--bake='))?.slice(7);
 if(!parent||!bake)throw new Error('Distant scenery requires explicit --parent and --bake');prepareDistantScenery(parent,bake);
}
