import { spawnSync } from 'node:child_process';
import { expect,test } from 'vitest';
import { validateCitadelCapsulePolicy,validateCitadelCapsuleKinematics } from '../scripts/unreal/citadel-collision-policy';
import {citadelCapsuleKinematicsPolicy} from './fixtures/citadelCapsulePolicy';

const policy=()=>({version:1,source:'native_AWarCharacter_class_default_capsule_v1',
  characterClass:'/Script/AegisWar.WarCharacter',classDefaultClass:'/Script/AegisWar.WarCharacter',
  profile:'Custom',classDefaultProfile:'Custom',collisionEnabled:3,classDefaultCollisionEnabled:3,
  objectChannel:2,classDefaultObjectChannel:2,responses:Array.from({length:64},(_,i):number=>i===8 ? 0 : 2),
  classDefaultResponses:Array.from({length:64},(_,i):number=>i===8 ? 0 : 2),matchesClassDefault:true,simulatingPhysics:false,classDefaultSimulatingPhysics:false});

test('collision admission audits all 64 channels rather than the display profile label',()=>{
  expect(()=>validateCitadelCapsulePolicy(policy())).not.toThrow();
  for (let channel=0;channel<64;channel++) for(const field of ['responses','classDefaultResponses'] as const){
    const p=policy();p[field][channel]=1;expect(()=>validateCitadelCapsulePolicy(p)).toThrow();
  }
  const p=policy();p.responses[0]=p.classDefaultResponses[0]=0;
  expect(()=>validateCitadelCapsulePolicy(p)).toThrow();
});

test('disabled capsules and alternate native classes cannot claim default collision',()=>{
  for(const change of [(p:any)=>{p.collisionEnabled=1;},(p:any)=>{p.objectChannel=0;},
    (p:any)=>{p.profile='Pawn';},(p:any)=>{p.characterClass='Other';},(p:any)=>{p.responses=[2];},
    (p:any)=>{p.simulatingPhysics=true;},(p:any)=>{p.matchesClassDefault=false;}]){
    const p=policy();change(p);expect(()=>validateCitadelCapsulePolicy(p)).toThrow();
  }
});

test('publisher independently enforces native capsule collision policy',()=>{
  const run=spawnSync('python',['-B','tests/unrealCitadelCollisionPolicy.test.py'],{encoding:'utf8',windowsHide:true});
  expect(run.error).toBeUndefined();expect(run.status,run.stdout+run.stderr).toBe(0);
});

test('changed dimensions, slope, gravity and movement body cannot use a captured native policy',()=>{
  expect(()=>validateCitadelCapsuleKinematics(citadelCapsuleKinematicsPolicy())).not.toThrow();
  for (const edit of [
    (p:any)=>{p.scaledRadiusCm=21;},(p:any)=>{p.scaledHalfHeightCm=48;},
    (p:any)=>{p.capsuleRadiusCm=p.classDefaultRadiusCm=21;},
    (p:any)=>{p.maxStepHeightCm=p.classDefaultMaxStepHeightCm=90;},
    (p:any)=>{p.walkableFloorZ=p.classDefaultWalkableFloorZ=.2;},
    (p:any)=>{p.gravityScale=p.classDefaultGravityScale=0;},
    (p:any)=>{p.componentScale=[.5,.5,.5];},(p:any)=>{p.capsuleAxis=[0,1,0];},
    (p:any)=>{p.gravityDirection=[0,0,1];},(p:any)=>{p.updatedComponentIsCapsule=false;},
    (p:any)=>{p.matchesClassDefault=false;},(p:any)=>{p.gravityScale=true;},
  ]) {const p=citadelCapsuleKinematicsPolicy();edit(p);expect(()=>validateCitadelCapsuleKinematics(p)).toThrow();}
});
