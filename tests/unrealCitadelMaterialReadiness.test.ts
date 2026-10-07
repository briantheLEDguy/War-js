import { expect, test } from 'vitest';
import { validatePrivateMaterialReadiness } from '../scripts/unreal/citadel-material-readiness';

const material='/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Materials/M_PrivateSurface_stone.M_PrivateSurface_stone';
const ready=()=>({schemaVersion:1,readOnly:true,available:true,ready:true,renderBuffersReady:true,
  materialCount:1,readyMaterialCount:1,submittedMeshBatchVerified:false,screenshotPixelBindingVerified:false});
const binding=()=>({registered:true,visible:true,hiddenInGame:false,actorHidden:false,material,baseMaterial:material,
  renderBuffersAvailable:true,rendererAvailable:true,renderSections:[{lod:0,triangles:128}],
  submittedMeshBatchVerified:false,screenshotPixelBindingVerified:false,visualApproved:false,
  renderMaterial:{available:true,usedFallback:false,effectiveInterface:material,shaderMapPresent:true,shaderMapValidForRendering:true}});

test('admits intended ready resources and an untreated comparison without granting pixel evidence',()=>{
  expect(()=>validatePrivateMaterialReadiness(ready(),[binding()])).not.toThrow();
  expect(()=>validatePrivateMaterialReadiness({...ready(),materialCount:0,readyMaterialCount:0},[])).not.toThrow();
});
test('rejects the observed valid WorldGrid fallback and later mismatched or unfinished resources',()=>{
  for(const change of [
    {usedFallback:true,effectiveInterface:'/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial'},
    {usedFallback:true},{effectiveInterface:'/another/material'},{available:false},
    {shaderMapPresent:false},{shaderMapValidForRendering:false},
  ]){
    const row=binding();Object.assign(row.renderMaterial,change);
    expect(()=>validatePrivateMaterialReadiness(ready(),[row])).toThrow();
  }
});
test('rejects missing readiness, hidden or missing section coverage, bad counts and premature approvals',()=>{
  for(const change of [{available:false},{ready:false},{readOnly:false},{renderBuffersReady:false},
    {materialCount:2},{readyMaterialCount:0},{materialCount:.5},{submittedMeshBatchVerified:true},
    {screenshotPixelBindingVerified:true}])
    expect(()=>validatePrivateMaterialReadiness({...ready(),...change},[binding()])).toThrow();
  expect(()=>validatePrivateMaterialReadiness(undefined,[binding()])).toThrow();
  expect(()=>validatePrivateMaterialReadiness(ready(),[])).toThrow();
  for(const change of [{actorHidden:true},{renderSections:[]},{renderSections:[{lod:0,triangles:0}]},
    {renderBuffersAvailable:false},{visualApproved:true},{submittedMeshBatchVerified:true}])
    expect(()=>validatePrivateMaterialReadiness(ready(),[{...binding(),...change}])).toThrow();
});

test('requires every declared crag material and its intended ready resource',()=>{
  const rows=['rock','dark_seam','snow'].map(role=>{
    const name='M_DistantCrag_'+role;
    const material=`/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Materials/${name}.${name}`;
    return {...binding(),material,baseMaterial:material,component:'/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Backdrop.Component',
      materialSlot:role==='rock'?0:role==='dark_seam'?1:2,
      renderMaterial:{...binding().renderMaterial,effectiveInterface:material}};
  });
  const expected=rows.map(({material,baseMaterial})=>({material,baseMaterial}));
  const readiness={...ready(),materialCount:3,readyMaterialCount:3};
  expect(()=>validatePrivateMaterialReadiness(readiness,rows,expected)).not.toThrow();
  expect(()=>validatePrivateMaterialReadiness({...ready(),materialCount:2,readyMaterialCount:2},rows.slice(0,2),expected)).toThrow();
  const fallback=structuredClone(rows);fallback[2].renderMaterial.usedFallback=true;
  expect(()=>validatePrivateMaterialReadiness(readiness,fallback,expected)).toThrow();
});

test('rejects crag materials outside a private revision or with mismatched object names',()=>{
  for(const material of [
    '/Game/Materials/M_DistantCrag_rock.M_DistantCrag_rock',
    '/Game/WorldRebuild/AegisCitadel_AAAAAAAAAAAA/Materials/M_DistantCrag_rock.M_DistantCrag_rock',
    '/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Materials/M_DistantCrag_rock.M_DistantCrag_snow',
    '/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Materials/M_DistantCrag_lava.M_DistantCrag_lava',
  ]){
    const row={...binding(),material,baseMaterial:material,renderMaterial:{...binding().renderMaterial,effectiveInterface:material}};
    expect(()=>validatePrivateMaterialReadiness(ready(),[row])).toThrow();
    expect(()=>validatePrivateMaterialReadiness({...ready(),materialCount:0,readyMaterialCount:0},[],[{material,baseMaterial:material}])).toThrow();
  }
});
