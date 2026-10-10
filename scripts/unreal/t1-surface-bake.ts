/** Admit an immutable private landform recipe; no licensed samples are checked into source. */
import {validateTerrainSurface,type TerrainSurface} from '../../shared/terrainSurface';
import {sha256} from './content-contract';

export function qualifySurfaceBake(parent:string,file:string,read:(file:string)=>Buffer) {
 const privatePath=(p:unknown):p is string=>typeof p==='string'&&!p.includes('\\')&&!p.includes(':')&&!p.includes('\0')
  &&p.split('/').every(part=>part!==''&&part!=='.'&&part!=='..')
  &&(p.startsWith('artifacts/unreal/')||p.startsWith('unreal/AegisWar/Content/'));
 if(!privatePath(file)||!file.startsWith('artifacts/unreal/t1-redesign/')||!file.endsWith('/surface-bake-receipt.json'))throw new Error('Invalid private surface bake path');
 const bytes=read(file),bake=JSON.parse(Buffer.from(bytes).toString('utf8'));
 const directory=file.slice(0,file.lastIndexOf('/'));
 if(bake.parentSignature!==parent||bake.licensedDerivative!==true||bake.distributionApproved!==false||bake.nativeIntegrated!==false
  ||bake.file!==directory+'/sunmeadow-surface.json'||!bake.inputs||typeof bake.inputs!=='object'||Array.isArray(bake.inputs))throw new Error('Unqualified absolute landform bake');
 const inputs:Record<string,string>={};
 for(const [binding,digest] of Object.entries(bake.inputs)) {
  if(!privatePath(binding)||typeof digest!=='string'||! /^[a-f0-9]{64}$/.test(digest)||sha256(read(binding))!==digest)throw new Error('Changed or invalid private landform binding: '+binding);
  inputs[binding]=digest;
 }
 if(!inputs[bake.file])throw new Error('Absolute surface bake lacks its sample fingerprint');
 const data=JSON.parse(Buffer.from(read(bake.file)).toString('utf8'));
 if(data.licensedDerivative!==true||data.distributionApproved!==false||data.nativeIntegrated!==false)throw new Error('Absolute surface lacks private derivative flags');
 const surface:TerrainSurface={bounds:data.bounds,segmentsX:data.segmentsX,segmentsZ:data.segmentsZ,edgeFade:data.edgeFade,samples:data.samples};validateTerrainSurface(surface);
 const apron=bake.groundingApronMetres??90;
 if(!Number.isFinite(apron)||apron<25||apron>200)throw new Error('Invalid surface grounding apron');
 inputs[file]=sha256(bytes);return {surface,inputs,apron};
}
