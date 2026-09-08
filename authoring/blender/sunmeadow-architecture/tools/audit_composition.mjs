/** Read-only comparison of the composed map with delivered model contracts. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { composeSunmeadowEnvironment } from '../../../../scripts/campaign/sunmeadow-environment.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),root=path.resolve(work,'../../..');
const read=async file=>JSON.parse(await fs.readFile(file,'utf8'));
const report=await read(path.join(work,'build-report.json'));
const assets=new Map(report.map(asset=>[asset.asset_id,asset]));
const zone=composeSunmeadowEnvironment(await read(path.join(root,'public/assets/maps/sunmeadow_march.json')),{architecture:true,nature:true,terrain:true});
const world=(prop,x,z)=>({x:prop.x+Math.cos(prop.rotY??0)*x*(prop.scaleX??prop.scale??1)+Math.sin(prop.rotY??0)*z*(prop.scaleZ??prop.scale??1),z:prop.z-Math.sin(prop.rotY??0)*x*(prop.scaleX??prop.scale??1)+Math.cos(prop.rotY??0)*z*(prop.scaleZ??prop.scale??1)});
const local=(prop,point)=>{const x=point.x-prop.x,z=point.z-prop.z;return{x:(Math.cos(prop.rotY??0)*x-Math.sin(prop.rotY??0)*z)/(prop.scaleX??prop.scale??1),z:(Math.sin(prop.rotY??0)*x+Math.cos(prop.rotY??0)*z)/(prop.scaleZ??prop.scale??1)};};
const architecture=zone.props.filter(prop=>assets.has(prop.assetKey));
const services=[...(zone.npcs??[]),...(zone.craftingStations??[])];
const servicePoints=[...services,...zone.orvrLayout.keeps.flatMap(keep=>[
  {id:keep.objectiveId+'_commander',x:keep.x,z:keep.z+4},
  {id:keep.objectiveId+'_quartermaster',...keep.quartermaster},
  {id:keep.objectiveId+'_postern_inside',...keep.postern.inside},
  {id:keep.objectiveId+'_postern_outside',...keep.postern.outside},
  ...keep.siegeSlots.map(slot=>({id:slot.id+'_operator',...(slot.operatorPosition??slot)})),
])];
const overlap=[];
for(const prop of architecture){
  if(/curtain_wall|gatehouse|gate_leaves/.test(prop.assetKey))continue;
  const contract=assets.get(prop.assetKey).contract;
  for(const service of services){
    const p=local(prop,service),[width,depth]=contract.footprint;
    if(Math.abs(p.x)<=width/2+.35&&Math.abs(p.z)<=depth/2+.35)overlap.push({prop:prop.id,service:service.id,position:service,local:p});
  }
}
const gates=architecture.filter(prop=>prop.assetKey.endsWith('gatehouse')).map(prop=>({id:prop.id,centre:{x:prop.x,z:prop.z},wingLineEnds:[world(prop,-14,4.6),world(prop,14,4.6)],entrance:world(prop,0,6),exit:world(prop,0,-6)}));
const entries=architecture.filter(prop=>/farmhouse|workshop|supply_post/.test(prop.assetKey)).map(prop=>({id:prop.id,key:prop.assetKey,x:prop.x,z:prop.z,rotation:prop.rotY,entrance:world(prop,0,assets.get(prop.assetKey).contract.footprint[1]/2),colliders:prop.colliders??[],nearServices:services.filter(point=>Math.hypot(point.x-prop.x,point.z-prop.z)<12).map(point=>({id:point.id,x:point.x,z:point.z}))}));
const result={sourceSha256:crypto.createHash('sha256').update(await fs.readFile(path.join(root,'scripts/campaign/sunmeadow-environment.mjs'))).digest('hex'),architectureInstances:architecture.length,architecture,servicePoints,gatehouses:gates,serviceBuildingOverlap:overlap,entrances:entries,keeps:zone.orvrLayout.keeps.map(keep=>({id:keep.objectiveId,x:keep.x,z:keep.z,quartermaster:keep.quartermaster,postern:keep.postern,commander:keep.commanderPosition,siegeSlots:keep.siegeSlots}))};
await fs.writeFile(path.join(work,'review/composition_audit.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({instances:architecture.length,gatehouses:gates,serviceBuildingOverlap:overlap,missingColliders:entries.filter(entry=>!entry.colliders.length).map(entry=>entry.id)},null,2));
