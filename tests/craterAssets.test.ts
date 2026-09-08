import {afterEach,describe,expect,it,vi} from 'vitest';
import {createHash} from 'node:crypto';
import {Group,Mesh,BoxGeometry,MeshBasicMaterial} from 'three';
import {AssetLoader} from '../src/game/AssetLoader';
import {loadReviewedCityObject} from '../src/world/CityArchitecture';
const hash=(s:string)=>createHash('sha256').update(s).digest('hex');
afterEach(()=>vi.unstubAllGlobals());
describe('crater asset approval and recovery',()=>{
  it('requires matching QC hashes and valid module budgets',async()=>{
    const qc=JSON.stringify({qcPassed:true,validationErrors:0,lods:[{model:'prop_riftspire_house_1.glb',triangles:12000,sha256:'a'.repeat(64)},{model:'prop_riftspire_bad.glb',triangles:30001,sha256:'b'.repeat(64)}]});
    let tampered=false;
    vi.stubGlobal('fetch',vi.fn(async(input:unknown)=>String(input).includes('asset-index')?new Response(JSON.stringify({staticProps:{riftspire_house_1:{model:'prop_riftspire_house_1.glb',runtimeReady:true,lifecycleStatus:'approved',reviewStatus:'approved',qc:'house.qc.json',qcSha256:hash(qc)}}})):new Response(tampered?qc+' ':qc)));
    expect(await new AssetLoader().resolveApprovedCityModels('riftspire_house_1')).toEqual(['prop_riftspire_house_1.glb']);
    tampered=true;expect(await new AssetLoader().resolveApprovedCityModels('riftspire_house_1')).toEqual([]);
  });
  it('uses an approved alternate LOD when the preferred mesh is unavailable',async()=>{
    const visible=new Group();visible.add(new Mesh(new BoxGeometry(),new MeshBasicMaterial()));
    const loader={resolveApprovedCityModels:async()=>['primary.glb','alternate.glb'],loadModel:vi.fn(async(file:string,fallback:()=>Group)=>file==='primary.glb'?fallback():visible)} as unknown as AssetLoader;
    const result=await loadReviewedCityObject('riftspire_house_1',loader);
    expect(result?.levels).toHaveLength(1);expect(result?.levels[0].object).toBe(visible);expect(result?.levels[0].distance).toBe(0);
  });
  it('omits missing architecture instead of returning a primitive',async()=>{
    const loader={resolveApprovedCityModels:async()=>['primary.glb','alternate.glb'],loadModel:async(_file:string,fallback:()=>Group)=>fallback()} as unknown as AssetLoader;
    expect(await loadReviewedCityObject('riftspire_house_1',loader)).toBeNull();
  });
});
