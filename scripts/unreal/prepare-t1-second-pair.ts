/** Immutable later-pair source experiment; no active maps or native packages are modified. */
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import type {ZoneDefinition} from '../../shared/world/ZoneDefinition';
import {redesignT1} from './t1-layouts';
import {secondPairLandscape} from './t1-second-pair-landscape';
import {battlefieldGrades} from './t1-battlefield-grades';
import {createOrvrGridHeightSampler} from '../../shared/orvrTerrain';
import {outdoorTerrain,outdoorRoads} from './world-portals';
import {canonicalJson,sha256} from './content-contract';
import {isMain,repoRoot} from './toolchain';

export function prepareSecondPair():void{
 const base=path.join(repoRoot,'artifacts/unreal/t1-redesign'),inputs:Record<string,string>={};
 const load=(file:string)=>{const bytes=readFileSync(path.join(repoRoot,file));inputs[file]=sha256(bytes);return JSON.parse(bytes.toString().replace(/^\uFEFF/,'')) as ZoneDefinition;};
 const zones=['brightfen_approach','ashen_steppe'].map(id=>secondPairLandscape(redesignT1(load('public/assets/maps/'+id+'.json'))));
 for(const p of ['scripts/unreal/prepare-t1-second-pair.ts','scripts/unreal/t1-second-pair-landscape.ts','scripts/unreal/t1-layouts.ts',
   'scripts/unreal/t1-battlefield-grades.ts','scripts/unreal/world-portals.ts','shared/terrainField.ts','shared/orvrTerrain.ts','shared/worldSpatial.ts'])inputs[p]=sha256(readFileSync(path.join(repoRoot,p)));
 const reports=zones.map(z=>{
  const h=createOrvrGridHeightSampler(z.orvrLayout!.terrain,z.size,z.segments,z.spatial),routes=battlefieldGrades([...z.paths!,...z.orvrLayout!.caravanRoutes],h);
  if(routes.some(r=>r.maximumGrade>.22))throw new Error('Second-pair source grade exceeds target: '+JSON.stringify(routes.filter(r=>r.maximumGrade>.22)));
  return {zone:z.id,routeGrades:routes,maximumGrade:Math.max(...routes.map(r=>r.maximumGrade)),fullWidthSamples:routes.reduce((n,r)=>n+r.samples,0),nativeBuilt:false,visualApproved:false};
 });
 const signature=sha256(canonicalJson({inputs,zones})),directory=path.join(base,'second-pair',signature.slice(0,12));
 if(existsSync(directory))throw new Error('Preserve an existing second-pair source study');mkdirSync(directory,{recursive:true});
 const files:Record<string,string>={};
 for(const z of zones)for(const [suffix,data] of [['',z],['_terrain',outdoorTerrain(z)],['_roads',outdoorRoads(z)]] as const){
  const file=path.join(directory,z.id+suffix+'.json'),bytes=JSON.stringify(data);writeFileSync(file,bytes);files[path.relative(repoRoot,file).replaceAll('\\','/')]=sha256(bytes);
 }
 const receipt={signature,directory:path.relative(repoRoot,directory).replaceAll('\\','/'),inputs,files,zones:reports,nativeBuilt:false,activeMapsChanged:false,
  appearanceApproved:false,undergroundEnvironmentsBuilt:false,firstPairLairGateRetained:true,allGameplayAndReleaseGatesRetained:true};
 writeFileSync(path.join(directory,'source.json'),canonicalJson(receipt));writeFileSync(path.join(base,'second-pair-source-latest.json'),canonicalJson(receipt));
 console.log(JSON.stringify({signature:signature.slice(0,12),zones:reports,nativeBuilt:false}));
}
if(isMain(import.meta.url))prepareSecondPair();
