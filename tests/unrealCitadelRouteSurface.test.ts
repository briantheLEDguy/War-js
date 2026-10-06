import {citadelCapsuleCollisionPolicy,citadelCapsuleKinematicsPolicy} from './fixtures/citadelCapsulePolicy';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';
import { citadelProofConfig, validateCitadelRouteWidth, type CitadelLedger } from '../scripts/unreal/citadel-proof';
import { citadelRouteWidthSeed, citadelSurfaceHeight, requireCitadelRouteSurfaceBindings,
  validateCitadelRouteSurfaceProfiles, validateCitadelSurfaceProfile, validateCitadelSurfaceReport,
  type CitadelRouteSurfaceProfile, type CitadelSurfaceProofRoute } from '../scripts/unreal/citadel-route-surface';

// Portable mathematical fixtures do not represent native clearance or acceptance.
const profile:CitadelRouteSurfaceProfile={schemaVersion:1,routeId:'west_approach',kind:'world_x_piecewise_linear',
  meshId:'stairs_and_balconies',knotsCm:[[-200,0],[400,300],[1000,450]],
  boundaryPolicy:'closed_profile_domain_shared_boundaries_same_height',construction:'continuous_paved_fan_ramp'};
const route={id:'west_approach',points:[[400,100,300],[400,900,300]] as [number,number,number][],width:1200};
const proof:CitadelSurfaceProofRoute={id:route.id+':forward',points:route.points,clearWidthCm:route.width,surfaceProfile:profile};
const method='signed_world_x_piecewise_linear_per_lane_and_movement_step';
function sourceFixture() {
  const positions:[number,number,number][]=[];const indices:number[]=[];
  for (const [a,b] of [[-200,400],[400,1000]]) {
    const start=positions.length;
    positions.push([a,0,citadelSurfaceHeight(profile,a)],[b,0,citadelSurfaceHeight(profile,b)],
      [b,1000,citadelSurfaceHeight(profile,b)],[a,1000,citadelSurfaceHeight(profile,a)]);
    indices.push(start,start+1,start+2,start,start+2,start+3);
  }
  const payload=JSON.stringify(profile),source={assets:[{id:'stairs_and_balconies',sha256:'a'.repeat(64)}],
    surfaceBindings:[{routeId:route.id,profilePayload:payload,profileSha256:createHash('sha256').update(payload).digest('hex'),
      meshId:'stairs_and_balconies',sourceMeshSha256:'a'.repeat(64),topTriangleIndices:[0,1,2,3]}]};
  return {source,blueprint:{routes:[route],routeSurfaceProfiles:[profile]},meshes:new Map([['stairs_and_balconies',{positions,indices}]])};
}
function widthEvidence(routes:CitadelSurfaceProofRoute[]) {
  const setup={version:4,placementOverlapPolicy:'fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1',
    gateOverlapAdmissionRemainsRaw:true,
    capsulePolicyCheckedEveryTick:true,capsulePolicyCheckedEveryPlacementQuery:true,capsuleCollisionPolicy:citadelCapsuleCollisionPolicy(),capsuleKinematicsPolicy:citadelCapsuleKinematicsPolicy(),laneFractions:[-1,-.5,0,.5,1],maxSpacingCm:100,movementSpacingCm:10,
    edgeInsetCm:0,maxFloorDeviationCm:120,groundClearanceCm:2.4,minFloorDistanceCm:1.9,maxFloorDistanceCm:2.4,
    capsuleRadiusCm:42,capsuleHalfHeightCm:96,maxStepHeightCm:45,walkableFloorZ:0.7100000381469727,collisionChannel:'ECC_Pawn',
    collisionProfile:'Custom',simpleCollision:true,movementMethod:'ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight',
    surfaceSamplingMethod:method,surfaceProfiles:routes.map(r => ({id:r.id,surfaceProfile:r.surfaceProfile}))};
  const rows:any[]=[];
  for (const r of routes) {
    const previous=new Map<number,number[]>();
    for (let segment=0;segment<r.points.length-1;segment++) {
      const a=r.points[segment],b=r.points[segment+1],count=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/100);
      for (let sample=0;sample<=count;sample++) for (const lane of setup.laneFractions) {
        const seed=citadelRouteWidthSeed(r,segment,sample/count,lane,42),before=previous.get(lane);previous.set(lane,seed);
        const movementSteps=before ? Math.ceil(Math.hypot(seed[0]-before[0],seed[1]-before[1])/10) : 0;
        const rawEvidence=(queries:number)=>({queries,rawClear:queries,separated:0,blocked:0,unresolved:0,
          rawBlockingHits:0,lastDisposition:queries ? 'raw_clear' : 'unused',contacts:[]});
        rows.push({id:r.id,segment,sample,lane,alpha:sample/count,clearWidthCm:r.clearWidthCm,
          lateralOffsetCm:lane*(r.clearWidthCm/2-42),seed,center:[seed[0],seed[1],seed[2]+98.4],
          floorImpact:[...seed],floorZCm:seed[2],floorNormalZ:.8,floorDistanceCm:2.4,floor:true,
          placementClear:true,transitionClear:true,passed:true,stepAttempted:false,stepSucceeded:false,
          movementSteps,placementOverlapEvidence:rawEvidence(2),
          movementOverlapEvidence:rawEvidence(movementSteps ? 2+3*movementSteps : 0)});
      }
    }
  }
  return {capsuleRadiusCm:42,capsuleHeightCm:192,routeWidthConfig:setup,routeWidthSamples:rows,
    routeWidthComplete:true,routeWidthPassed:true};
}

test('profile height follows actual lateral world X in both walking directions', () => {
  validateCitadelRouteSurfaceProfiles([profile],[route]);
  const left=citadelRouteWidthSeed(proof,0,.5,1,42),right=citadelRouteWidthSeed(proof,0,.5,-1,42);
  expect(left).toEqual([-158,500,21]);expect(right).toEqual([958,500,439.5]);
  expect(Math.abs(left[2]-300)).toBeGreaterThan(120);
  const reverse={...proof,id:route.id+':reverse',points:[...proof.points].reverse()};
  expect(citadelRouteWidthSeed(reverse,0,.5,-1,42)).toEqual(left);
  expect(citadelRouteWidthSeed(reverse,0,.5,1,42)).toEqual(right);
  expect(citadelSurfaceHeight(profile,400)).toBe(300);
  expect(() => citadelSurfaceHeight(profile,-201)).toThrow(/domain/);
  expect(() => citadelSurfaceHeight(profile,-200-1e-9)).toThrow(/domain/);
  expect(() => citadelSurfaceHeight(profile,1000+1e-9)).toThrow(/domain/);
});

test('schema, slope, full footprint domain and center waypoint heights are immutable', () => {
  for (const alter of [(p:any) => {p.knotsCm.reverse();},(p:any) => {p.knotsCm[1][0]=p.knotsCm[0][0];},
    (p:any) => {p.knotsCm[1][1]=10000;},(p:any) => {p.knotsCm[1][1]=NaN;},(p:any) => {p.kind='flat';},
    (p:any) => {p.allowHeightGuess=true;},(p:any) => {p.schemaVersion=true;}]) {
    const bad=structuredClone(profile);alter(bad);expect(() => validateCitadelSurfaceProfile(bad)).toThrow();
  }
  const short=structuredClone(profile);short.knotsCm[0][0]=-190;
  expect(() => validateCitadelRouteSurfaceProfiles([short],[route])).toThrow(/domain/);
  expect(() => validateCitadelRouteSurfaceProfiles([profile],[{...route,points:[[400,100,301],[400,900,300]]}])).toThrow(/height/);
  expect(() => validateCitadelRouteSurfaceProfiles([profile,profile],[route])).toThrow();
  expect(() => validateCitadelRouteSurfaceProfiles(null,[route])).toThrow();
  expect(() => validateCitadelSurfaceProfile({...profile,knotsCm:[[-1_000_001,0],[1_000_001,0]]})).toThrow();
});

test('config binds the identical signed profile forward and reverse without changing route width', () => {
  const ledger:CitadelLedger={schemaVersion:1,signature:'a'.repeat(64),routes:[{...route,start:'entry',end:'court',bidirectional:true}],
    routeSurfaceProfiles:[profile],objectives:Array.from({length:8},()=>[0,0,0]),optionalObjectives:Array.from({length:3},()=>[0,0,0]),
    gates:[0,1].map(index => ({id:'gate_'+index,index,leaves:Array.from({length:index ? 5 : 3},()=>({point:[0,0,0],width:600,height:1000}))}))};
  const config=citadelProofConfig(ledger,'/Game/WorldRebuild/AegisCitadel_abcdef123456/SiegeCandidate','b'.repeat(64),'c'.repeat(64),'routes');
  expect(config.routes.map(r=>r.surfaceProfile)).toEqual([profile,profile]);
  expect(config.routes.map(r=>r.clearWidthCm)).toEqual([1200,1200]);
  expect(config.routes[1].points).toEqual([...route.points].reverse());
});

test('full-width floor evidence uses signed seeds and retains every physical threshold', () => {
  const routes=[proof,{...proof,id:route.id+':reverse',points:[...proof.points].reverse()}];
  expect(() => validateCitadelRouteWidth(widthEvidence(routes),routes)).not.toThrow();
  for (const alter of [(e:any)=>{delete e.routeWidthConfig.surfaceProfiles;},(e:any)=>{e.routeWidthConfig.surfaceSamplingMethod='centerline';},
    (e:any)=>{e.routeWidthConfig.surfaceProfiles[0].surfaceProfile.knotsCm[0][1]=10;},
    (e:any)=>{e.routeWidthSamples[0].seed[2]=300;},
    (e:any)=>{const r=e.routeWidthSamples[0];r.floorZCm+=120.01;r.floorImpact[2]=r.floorZCm;r.center[2]+=120.01;},
    (e:any)=>{e.routeWidthConfig.maxFloorDeviationCm=300;},(e:any)=>{e.routeWidthConfig.maxStepHeightCm=46;},
    (e:any)=>{e.routeWidthConfig.capsuleRadiusCm=20;},(e:any)=>{e.routeWidthSamples[0].transitionClear=false;}]) {
    const bad=structuredClone(widthEvidence(routes));alter(bad);expect(() => validateCitadelRouteWidth(bad,routes)).toThrow();
  }
});

test('normal historical reports accept no profiles but reject an unexplained profile witness', () => {
  const ordinary={...proof};delete ordinary.surfaceProfile;
  expect(() => validateCitadelSurfaceReport({},[ordinary])).not.toThrow();
  expect(() => validateCitadelSurfaceReport({surfaceProfiles:[],surfaceSamplingMethod:method},[ordinary])).not.toThrow();
  expect(() => validateCitadelSurfaceReport({surfaceProfiles:[{id:proof.id,surfaceProfile:profile}]},[ordinary])).toThrow();
});

test('actual source triangle ordinals and partitioned top surfaces cover all five lanes and floor edges', () => {
  const f=sourceFixture();expect(() => requireCitadelRouteSurfaceBindings(f.source,f.blueprint,f.meshes)).not.toThrow();
  for (const alter of [(s:any)=>{s.surfaceBindings[0].profilePayload+=' ';},(s:any)=>{s.surfaceBindings[0].sourceMeshSha256='b'.repeat(64);},
    (s:any)=>{s.surfaceBindings[0].topTriangleIndices=[0,1,2];},(s:any)=>{s.surfaceBindings[0].topTriangleIndices=[0,1,2,2];},
    (s:any)=>{s.surfaceBindings[0].topTriangleIndices=[0,1,2,99];},(s:any)=>{s.surfaceBindings=[];}]) {
    const source=structuredClone(f.source);alter(source);expect(() => requireCitadelRouteSurfaceBindings(source,f.blueprint,f.meshes)).toThrow();
  }
  const wrong=sourceFixture();wrong.meshes.get('stairs_and_balconies')!.positions[0][2]=1;
  expect(() => requireCitadelRouteSurfaceBindings(wrong.source,wrong.blueprint,wrong.meshes)).toThrow(/h\(worldX\)/);
  const crossing=sourceFixture(),mesh=crossing.meshes.get('stairs_and_balconies')!;
  mesh.indices=[0,5,6];crossing.source.surfaceBindings[0].topTriangleIndices=[0];
  expect(() => requireCitadelRouteSurfaceBindings(crossing.source,crossing.blueprint,crossing.meshes)).toThrow(/knot seam/);
});

test('portable publisher mirrors signed profile and source guards', () => {
  const r=spawnSync('python',['-B','tests/unrealCitadelRouteSurface.test.py'],{encoding:'utf8',windowsHide:true});
  expect(r.error).toBeUndefined();expect(r.status,r.stdout+r.stderr).toBe(0);
},30_000);
