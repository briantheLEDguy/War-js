import { expect,test } from 'vitest';
import { spawnSync } from 'node:child_process';
import { validateRoutePlacementOverlaps } from '../scripts/unreal/citadel-placement-evidence';

test('publication independently rejects incomplete and tampered live overlap receipts',()=>{
  const run=spawnSync('python',['-B','tests/unrealCitadelPlacementEvidence.test.py'],{encoding:'utf8',windowsHide:true});
  expect(run.error,run.error?.message).toBeUndefined();
  expect(run.status,run.stdout+run.stderr).toBe(0);
});

// Artificial receipt fields exercise validation; they are never native acceptance evidence.
const evidence=()=> {
  const triangle={internalTriangle:0,finite:true,certificateVersion:1,guardPolicyVersion:1,projectionAxisRecorded:true,
    fullCapsuleSeparationCertified:true,worldVertices:[[-100,-100,0],[100,-100,0],[0,100,0]],
    separatingUnitAxis:[0,0,1],projectionOriginCm:[0,0,98.4],separatingAxisSquaredLength:1,
    capsuleProjectionCm:[-96,96],triangleProjectionCm:[-98.4,-98.4],numericalGuardCm:.01,
    separatingPlaneGapCm:2.4,gapTriangleAfterCapsuleCm:-194.4,gapCapsuleAfterTriangleCm:2.4,projectionGapDirection:'capsule_above_triangle'};
  const shape={shapeIndex:0,selected:true,boundToQueriedBody:true,queryShape:true,rigidUnitSeparationPolicySupported:true,
    collisionMarginCm:0,affineQueryBoundsVerified:true,triangleWitnessComplete:true,truncated:false,
    finiteTriangles:true,candidateTriangleCount:1,liveCookedTriangleCount:1,triangles:[triangle]};
  const witness={schemaVersion:2,source:'live_physics_shape_geometry_under_execute_read',readLockEntered:true,
    complete:true,staticSingleBodyPolicySupported:true,sameReadLockMtdBlocking:false,separatedContactDiagnostic:true,
    admissionGranted:false,capsuleAxisStart:[0,0,44.4],capsuleAxisEnd:[0,0,152.4],capsuleRadiusCm:42,
    liveShapeCount:1,selectedShapeCount:1,shapes:[shape]};
  const resolution={diagnosticOnly:true,admissionGranted:false,capsuleInputValid:true,rawBlockingHitCount:1,
    uniqueBlockingBodyCount:1,resolvedSeparatedBodyCount:1,blockedBodyCount:0,unresolvedBodyCount:0,
    inconsistentDuplicateCount:0,proposalDecision:'all_raw_contacts_proven_separated',
    perBodyDecisions:[{originalBodyBindingVerified:true,decision:'separated',liveWitness:witness}]};
  return {queries:2,rawClear:1,separated:1,blocked:0,unresolved:0,rawBlockingHits:1,lastDisposition:'raw_clear',
    contacts:[{query:{center:[0,0,98.4],quaternion:[0,0,0,1],radiusCm:42,halfHeightCm:96,role:'floor_adjusted'},resolution}]};
};

test('route placement receipts independently audit the whole capsule and account for every raw body',()=>{
  expect(()=>validateRoutePlacementOverlaps(evidence(),null,42,96)).not.toThrow();
  const changes:Array<(e:ReturnType<typeof evidence>)=>void>=[
    e=>{e.contacts=[];},e=>{e.rawBlockingHits=0;},e=>{e.lastDisposition='unresolved';},
    e=>{e.contacts[0].resolution.unresolvedBodyCount=1;},e=>{e.contacts[0].resolution.inconsistentDuplicateCount=1;},
    e=>{e.contacts[0].resolution.perBodyDecisions[0].originalBodyBindingVerified=false;},
    e=>{e.contacts[0].resolution.perBodyDecisions[0].liveWitness.sameReadLockMtdBlocking=true;},
    e=>{e.contacts[0].query.radiusCm=43;},
    e=>{e.contacts[0].resolution.perBodyDecisions[0].liveWitness.shapes[0].triangles[0].capsuleProjectionCm=[-54,54];},
    e=>{e.contacts[0].resolution.perBodyDecisions[0].liveWitness.shapes[0].triangles[0].numericalGuardCm=0;},
    e=>{e.contacts[0].resolution.perBodyDecisions[0].liveWitness.shapes[0].triangles[0].separatingPlaneGapCm=NaN;},
    e=>{e.contacts[0].resolution.perBodyDecisions[0].liveWitness.shapes[0].triangles[0].worldVertices[2]=[0,0,30];},
  ];
  for (const change of changes) {const value=evidence();change(value);expect(()=>validateRoutePlacementOverlaps(value,null,42,96)).toThrow(/overlap evidence/);}
});

test('a rejected seed can precede a valid swept floor but never override the final pose or movement query',()=>{
  const value:any=evidence();value.blocked=1;value.separated=0;
  value.contacts[0].query.role='seed_probe';value.contacts[0].resolution.proposalDecision='blocked';
  value.contacts[0].resolution.blockedBodyCount=1;value.contacts[0].resolution.resolvedSeparatedBodyCount=0;
  value.contacts[0].resolution.perBodyDecisions[0].decision='blocked';
  expect(()=>validateRoutePlacementOverlaps(value,null,42,96)).not.toThrow();
  value.contacts[0].query.role='native_movement_pose';
  expect(()=>validateRoutePlacementOverlaps(value,null,42,96)).toThrow();
  expect(()=>validateRoutePlacementOverlaps(evidence(),1,42,96)).toThrow();
});

test('every selected shape and rejected seed retains complete typed identity accounting',()=>{
  for (const count of [undefined,NaN,Infinity,-1,.5,true,0]) {
    const value:any=evidence();value.contacts[0].resolution.perBodyDecisions[0].liveWitness.shapes[0].liveCookedTriangleCount=count;
    expect(()=>validateRoutePlacementOverlaps(value,null,42,96)).toThrow();
  }
  const value:any=evidence(),w=value.contacts[0].resolution.perBodyDecisions[0].liveWitness;
  w.shapes.push(structuredClone(w.shapes[0]));w.liveShapeCount=2;w.selectedShapeCount=2;
  expect(()=>validateRoutePlacementOverlaps(value,null,42,96)).toThrow();
  const rejected:any=evidence();rejected.blocked=1;rejected.separated=0;
  rejected.contacts[0].query.role='seed_probe';rejected.contacts[0].resolution.proposalDecision='blocked';
  expect(()=>validateRoutePlacementOverlaps(rejected,null,42,96)).toThrow();
});
