import {describe,it,expect} from 'vitest';
import {qualifySurfaceBake} from '../scripts/unreal/t1-surface-bake';
import {sha256} from '../scripts/unreal/content-contract';

const file='artifacts/unreal/t1-redesign/landform-bakes/study-test/surface-bake-receipt.json';
function fixture() {
 const sample=file.replace('surface-bake-receipt.json','sunmeadow-surface.json');
 const data={bounds:{minX:-10,maxX:10,minZ:-5,maxZ:5},segmentsX:2,segmentsZ:1,edgeFade:2,samples:[0,1,2,3,4,5],licensedDerivative:true,distributionApproved:false,nativeIntegrated:false};
 const files:Record<string,Buffer>={[sample]:Buffer.from(JSON.stringify(data))};
 const bake={parentSignature:'parent',file:sample,licensedDerivative:true,distributionApproved:false,nativeIntegrated:false,groundingApronMetres:40,inputs:{[sample]:sha256(files[sample])}};
 const write=()=>files[file]=Buffer.from(JSON.stringify(bake));write();
 return {data,bake,files,write,read:(p:string)=>{if(!files[p])throw new Error('Missing private binding');return files[p];}};
}
describe('private immutable surface bake admission',()=>{
 it('verifies exact hashes, flags, rectangular samples and apron without mutating input',()=>{
  const f=fixture(),before=JSON.stringify(f.bake),r=qualifySurfaceBake('parent',file,f.read);
  expect(r.surface.samples).toEqual(f.data.samples);expect(r.apron).toBe(40);expect(r.inputs[file]).toBe(sha256(f.files[file]));expect(JSON.stringify(f.bake)).toBe(before);
 });
 it('rejects changed source bytes, missing fingerprints and mismatched parents',()=>{
  const f=fixture();expect(()=>qualifySurfaceBake('different',file,f.read)).toThrow();f.files[f.bake.file]=Buffer.from('changed');expect(()=>qualifySurfaceBake('parent',file,f.read)).toThrow();
  const g=fixture();g.bake.inputs={};g.write();expect(()=>qualifySurfaceBake('parent',file,g.read)).toThrow();
 });
 it('refuses traversal through either Windows or portable path syntax',()=>{
  for(const p of ['artifacts/unreal/../secret','artifacts/unreal/..\\secret','artifacts/unreal/C:/secret','public/assets/map.json']) {
   const f=fixture();f.bake.inputs[p]='a'.repeat(64);f.write();expect(()=>qualifySurfaceBake('parent',file,f.read)).toThrow();
  }
 });
 it('rejects distribution claims, integration claims, malformed grids and unsupported aprons',()=>{
  for(const mutate of [(f:ReturnType<typeof fixture>)=>f.bake.distributionApproved=true,(f:ReturnType<typeof fixture>)=>f.bake.nativeIntegrated=true,(f:ReturnType<typeof fixture>)=>f.bake.groundingApronMetres=24]) {
   const f=fixture();mutate(f);f.write();expect(()=>qualifySurfaceBake('parent',file,f.read)).toThrow();
  }
  const f=fixture();f.data.samples.pop();f.files[f.bake.file]=Buffer.from(JSON.stringify(f.data));f.bake.inputs[f.bake.file]=sha256(f.files[f.bake.file]);f.write();expect(()=>qualifySurfaceBake('parent',file,f.read)).toThrow();
 });
});
