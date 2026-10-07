import { expect,test } from 'vitest';
import { privateMountainStudyExpectation } from '../scripts/unreal/citadel-mountain-study-binding';
import { validatePrivateMaterialReadiness } from '../scripts/unreal/citadel-material-readiness';

const root='/Game/WorldRebuild/AegisCitadel_abcdef123456';
const material=`${root}/Materials/MI_PrivateSurface_mountain.MI_PrivateSurface_mountain`;
const baseMaterial=`${root}/Materials/M_PrivateSurface_mountain.M_PrivateSurface_mountain`;
const sourceInstance='/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/MI_Mountain_365df6bd.MI_Mountain_365df6bd';
const sourceParent='/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/M_Mountain.M_Mountain';
const keys=['material_domain','blend_mode','shading_model','two_sided','tangent_space_normal','use_material_attributes'];
const context={map:`${root}/LightingStudy`,mapSha256:'a'.repeat(64),cityRevision:'b'.repeat(64),blueprintSha256:'c'.repeat(64)};
const receipt=()=>({schemaVersion:1,diagnosticOnly:true,signature:'abcdef123456'+'d'.repeat(52),...context,
  historicalGeometryRevision:'aaaaaaaaaaaa',
  sourceAndCandidateHashesUnchanged:true,visualApproved:false,lightingApproved:false,physicalTraversalApproved:false,gameplayApproved:false,releaseAcceptance:false,
  privateSurfaceStudy:{spec:{sourceRevision:'aaaaaaaaaaaa',mountainMode:'existing_alpine_color_v2_preserve_uv',retainedMountainInspection:{
    map:'/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Layers/RetainedCity_0',
    actorReadback:{level:'/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Layers/RetainedCity_0'},
    inspectionKind:'fresh_native_retained_mountain_v1',readOnly:true,sourceBytesPreserved:true,candidateSha256:'e'.repeat(64),candidateCityRevision:'f'.repeat(64)}},
    mountain:{material,graphMaterial:baseMaterial,sourceMaterial:sourceInstance,sourcePbrGraph:sourceParent,
      expectedResourceOwner:baseMaterial,hasStaticPermutationResource:false,editorContractChecksPassed:true,textureRepeatApplied:false,
      candidateSha256:'e'.repeat(64),candidateCityRevision:'f'.repeat(64),freshInspectionSha256:'1'.repeat(64),
      beforeInstance:{material:sourceInstance,parent:sourceParent},afterInstance:{material,parent:baseMaterial,hasStaticPermutationResource:false},
      materialProfile:{name:'retained_mountain_material_properties_v1',complete:true,keys},afterGraph:{
        materialProfile:{name:'retained_mountain_material_properties_v1',complete:true,keys},
        materialProperties:Object.fromEntries(keys.map(k=>[k,false]))},
      nativeRenderNormalConvention:{source:'actual_saved_native_rendered_faces',slopeMaskNormalZSign:-1},
      coldProcessVerified:false,rendererStateVerified:false,submittedMeshBatchVerified:false,screenshotPixelBindingVerified:false,visualApproved:false,releaseAcceptance:false}}});

test('derives the required MI/base pair from the exact signed study audit',()=>{
  expect(privateMountainStudyExpectation(receipt(),context)).toEqual([{material,baseMaterial}]);
  expect(privateMountainStudyExpectation({privateSurfaceStudy:{spec:{mountainMode:null},mountain:null}},context)).toBeUndefined();
});
test('rejects stale candidate, archival inspection, wrong namespace/parent and incomplete six-property profiles',()=>{
  const actions=[(s:any)=>s.privateSurfaceStudy.mountain.material=material.replace('abcdef123456','111111111111'),
    (s:any)=>s.privateSurfaceStudy.mountain.graphMaterial=sourceParent,(s:any)=>s.privateSurfaceStudy.mountain.sourcePbrGraph='/Wrong',
    (s:any)=>s.privateSurfaceStudy.mountain.candidateSha256='0'.repeat(64),
    (s:any)=>s.privateSurfaceStudy.spec.retainedMountainInspection.inspectionKind='archival',
    (s:any)=>s.historicalGeometryRevision='bbbbbbbbbbbb',
    (s:any)=>s.privateSurfaceStudy.spec.retainedMountainInspection.actorReadback.level='/Wrong',
    (s:any)=>delete s.privateSurfaceStudy.mountain.afterGraph.materialProfile,
    (s:any)=>s.privateSurfaceStudy.mountain.materialProfile.complete=false,
    (s:any)=>delete s.privateSurfaceStudy.mountain.afterGraph.materialProperties.blend_mode,
    (s:any)=>s.privateSurfaceStudy.mountain.nativeRenderNormalConvention.slopeMaskNormalZSign=1,
    (s:any)=>s.privateSurfaceStudy.mountain.afterInstance.hasStaticPermutationResource=true,
    (s:any)=>s.mapSha256='0'.repeat(64),(s:any)=>s.privateSurfaceStudy.mountain=null,
    (s:any)=>s.privateSurfaceStudy.spec.mountainMode=null];
  for(const action of actions){const s=receipt();action(s);expect(()=>privateMountainStudyExpectation(s,context)).toThrow();}
});
test('source-bound expectation prevents self-consistent zero or substituted discovered inventory',()=>{
  const expected=privateMountainStudyExpectation(receipt(),context);
  const ready={schemaVersion:1,readOnly:true,available:true,ready:true,renderBuffersReady:true,
    materialCount:0,readyMaterialCount:0,submittedMeshBatchVerified:false,screenshotPixelBindingVerified:false};
  expect(()=>validatePrivateMaterialReadiness(ready,[])).not.toThrow();
  expect(()=>validatePrivateMaterialReadiness(ready,[],expected)).toThrow(/omitted/);
});
test('rejects premature renderer/visual claims',()=>{
  for(const key of ['rendererStateVerified','visualApproved','coldProcessVerified','submittedMeshBatchVerified']){
    const s=receipt();(s.privateSurfaceStudy.mountain as any)[key]=true;
    expect(()=>privateMountainStudyExpectation(s,context)).toThrow();
  }
});
