import type { PrivateMaterialExpectation } from './citadel-material-readiness';

const sourceInstance='/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/MI_Mountain_365df6bd.MI_Mountain_365df6bd';
const sourceParent='/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/M_Mountain.M_Mountain';
const profileKeys=['material_domain','blend_mode','shading_model','two_sided','tangent_space_normal','use_material_attributes'];

/** Bind the required interface from the source-bound study receipt, never from discovered render rows. */
export function privateMountainStudyExpectation(study: any, expected: {
  map: string; mapSha256: string; cityRevision: string; blueprintSha256: string;
}): readonly PrivateMaterialExpectation[] | undefined {
  const treatment=study?.privateSurfaceStudy;
  if (!treatment?.spec?.mountainMode && !treatment?.mountain) return undefined;
  const root=/^(\/Game\/WorldRebuild\/AegisCitadel_[a-f0-9]{12})\/[A-Za-z0-9_/]+$/.exec(expected.map)?.[1];
  const material=`${root}/Materials/MI_PrivateSurface_mountain.MI_PrivateSurface_mountain`;
  const baseMaterial=`${root}/Materials/M_PrivateSurface_mountain.M_PrivateSurface_mountain`;
  const audit=treatment?.mountain;
  const inspection=treatment?.spec?.retainedMountainInspection;
  const profile=audit?.materialProfile;
  const afterProfile=audit?.afterGraph?.materialProfile;
  if (!root || study.schemaVersion!==1 || study.diagnosticOnly!==true
    || typeof study.signature!=='string' || !/^[a-f0-9]{64}$/.test(study.signature)
    || !root.endsWith(study.signature.slice(0,12))
    || Object.entries(expected).some(([key,value])=>study[key]!==value)
    || study.sourceAndCandidateHashesUnchanged!==true
    || ['visualApproved','lightingApproved','physicalTraversalApproved','gameplayApproved','releaseAcceptance'].some(key=>study[key]!==false)
    || treatment.spec.mountainMode!=='existing_alpine_color_v2_preserve_uv'
    || inspection?.inspectionKind!=='fresh_native_retained_mountain_v1'
    || inspection.readOnly!==true || inspection.sourceBytesPreserved!==true
    || !/^[a-f0-9]{64}$/.test(inspection.candidateSha256 ?? '')
    || !/^[a-f0-9]{64}$/.test(inspection.candidateCityRevision ?? '')
    || !/^[a-f0-9]{12}$/.test(treatment.spec.sourceRevision ?? '')
    || treatment.spec.sourceRevision!==study.historicalGeometryRevision
    || !inspection.map?.startsWith(`/Game/WorldRebuild/AegisCitadel_${treatment.spec.sourceRevision}/`)
    || inspection.actorReadback?.level!==inspection.map
    || audit?.material!==material || audit.graphMaterial!==baseMaterial
    || audit.sourceMaterial!==sourceInstance || audit.sourcePbrGraph!==sourceParent
    || audit.expectedResourceOwner!==baseMaterial || audit.hasStaticPermutationResource!==false
    || audit.editorContractChecksPassed!==true || audit.textureRepeatApplied!==false
    || audit.candidateSha256!==inspection.candidateSha256 || audit.candidateCityRevision!==inspection.candidateCityRevision
    || !/^[a-f0-9]{64}$/.test(audit.freshInspectionSha256 ?? '')
    || audit.beforeInstance?.material!==sourceInstance || audit.beforeInstance?.parent!==sourceParent
    || audit.afterInstance?.material!==material || audit.afterInstance?.parent!==baseMaterial
    || audit.afterInstance?.hasStaticPermutationResource!==false
    || profile?.name!=='retained_mountain_material_properties_v1' || profile.complete!==true
    || Object.keys(profile).sort().join(',')!=='complete,keys,name'
    || !Array.isArray(profile.keys) || JSON.stringify(profile.keys)!==JSON.stringify(profileKeys)
    || afterProfile?.name!==profile.name || afterProfile.complete!==true
    || Object.keys(afterProfile).sort().join(',')!=='complete,keys,name'
    || JSON.stringify(afterProfile.keys)!==JSON.stringify(profileKeys)
    || Object.keys(audit.afterGraph?.materialProperties ?? {}).sort().join(',')!==[...profileKeys].sort().join(',')
    || audit.nativeRenderNormalConvention?.source!=='actual_saved_native_rendered_faces'
    || audit.nativeRenderNormalConvention?.slopeMaskNormalZSign!==-1
    || ['coldProcessVerified','rendererStateVerified','submittedMeshBatchVerified','screenshotPixelBindingVerified','visualApproved','releaseAcceptance'].some(key=>audit[key]!==false))
    throw new Error('Mountain capture requires the exact signed native MI/base study audit and six-property profile.');
  return [{material,baseMaterial}];
}
