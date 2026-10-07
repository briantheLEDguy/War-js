import { expect, test } from 'vitest';
import { validatePrivateMaterialReadiness } from '../scripts/unreal/citadel-material-readiness';

const root='/Game/WorldRebuild/AegisCitadel_abcdef123456';
const material=`${root}/Materials/MI_PrivateSurface_mountain.MI_PrivateSurface_mountain`;
const baseMaterial=`${root}/Materials/M_PrivateSurface_mountain.M_PrivateSurface_mountain`;
const ready=()=>({schemaVersion:1,readOnly:true,available:true,ready:true,renderBuffersReady:true,
  materialCount:1,readyMaterialCount:1,submittedMeshBatchVerified:false,screenshotPixelBindingVerified:false});
const binding=()=>({registered:true,visible:true,hiddenInGame:false,actorHidden:false,material,baseMaterial,
  component:`${root}/Scenery.Sceneries:PersistentLevel.StaticMeshActor_306.StaticMeshComponent0`,materialSlot:0,
  proxyInterface:material,hasStaticPermutationResource:false,renderBuffersAvailable:true,rendererAvailable:true,
  renderSections:[{lod:0,triangles:128}],submittedMeshBatchVerified:false,screenshotPixelBindingVerified:false,visualApproved:false,
  renderMaterial:{available:true,usedFallback:false,effectiveInterface:baseMaterial,materialDomain:0,shaderMapPresent:true,shaderMapValidForRendering:true}});

test('admits the owned non-static mountain MI proxy and its copied parent resource',()=>{
  expect(()=>validatePrivateMaterialReadiness(ready(),[binding()])).not.toThrow();
});
test('rejects proxy/parent substitutions, static permutations, unowned paths and missing component coverage',()=>{
  for(const change of [{proxyInterface:baseMaterial},{proxyInterface:undefined},{baseMaterial:material},
    {baseMaterial:baseMaterial.replace('abcdef123456','111111111111')},{hasStaticPermutationResource:true},
    {hasStaticPermutationResource:undefined},{component:'/Game/Unowned.Map:Actor.Component'},{materialSlot:1},
    {material:material+'_extra'},{material:material.replace('abcdef123456','ABCDEF123456')},
    {renderSections:[]},{actorHidden:true}])
    expect(()=>validatePrivateMaterialReadiness(ready(),[{...binding(),...change}])).toThrow();
  expect(()=>validatePrivateMaterialReadiness(ready(),[])).toThrow();
});
test('rejects fallback, wrong resource owner/domain, unfinished shaders and premature pixel acceptance',()=>{
  for(const change of [{usedFallback:true},{effectiveInterface:material},{effectiveInterface:'/Engine/WorldGrid'},
    {materialDomain:1},{materialDomain:undefined},{available:false},{shaderMapPresent:false},{shaderMapValidForRendering:false}]){
    const row=binding();Object.assign(row.renderMaterial,change);
    expect(()=>validatePrivateMaterialReadiness(ready(),[row])).toThrow();
  }
  expect(()=>validatePrivateMaterialReadiness(ready(),[{...binding(),visualApproved:true}])).toThrow();
});
test('null backend diagnostics remain unavailable and cannot supply renderer evidence',()=>{
  expect(()=>validatePrivateMaterialReadiness({...ready(),available:false,ready:false},[binding()])).toThrow();
});
const expected=()=>[{material,baseMaterial}];
test('requires signed interfaces when supplied and keeps untreated two-argument studies compatible',()=>{
  expect(()=>validatePrivateMaterialReadiness(ready(),[binding()],expected())).not.toThrow();
  expect(()=>validatePrivateMaterialReadiness({...ready(),materialCount:0,readyMaterialCount:0},[])).not.toThrow();
});
test('rejects zero, hidden or omitted required mountain and a discovered pair in the wrong namespace',()=>{
  const empty={...ready(),materialCount:0,readyMaterialCount:0};
  expect(()=>validatePrivateMaterialReadiness(empty,[],expected())).toThrow();
  expect(()=>validatePrivateMaterialReadiness(empty,[{...binding(),actorHidden:true}],expected())).toThrow();
  const foreignRoot='/Game/WorldRebuild/AegisCitadel_111111111111';
  const foreign=binding();foreign.material=material.replace(root,foreignRoot);foreign.proxyInterface=foreign.material;
  foreign.baseMaterial=baseMaterial.replace(root,foreignRoot);foreign.component=foreign.component.replace(root,foreignRoot);
  foreign.renderMaterial.effectiveInterface=foreign.baseMaterial;
  // A complete discovered inventory alone cannot establish the requested signed identity.
  expect(()=>validatePrivateMaterialReadiness(ready(),[foreign])).not.toThrow();
  expect(()=>validatePrivateMaterialReadiness(ready(),[foreign],expected())).toThrow();
});
test('rejects duplicate expectations/actual component slots and an unsigned expected parent',()=>{
  expect(()=>validatePrivateMaterialReadiness(ready(),[binding()],[...expected(),...expected()])).toThrow();
  expect(()=>validatePrivateMaterialReadiness(ready(),[binding(),binding()],expected())).toThrow();
  expect(()=>validatePrivateMaterialReadiness(ready(),[binding()],[{material,baseMaterial:material}])).toThrow();
});
