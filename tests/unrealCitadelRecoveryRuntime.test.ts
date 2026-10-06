import { createHash } from 'node:crypto';
import { expect, test } from 'vitest';
import { validateCitadelRecoveryCast, validateCitadelRuntimeEvolution } from '../scripts/unreal/citadel-recovery-runtime';
import { RECOVERY_EPOCH as epoch, recoveryCastFixture, recoveryRuntimeFixture } from './fixtures/citadelRecoveryRuntime';

const characterId='portable_recovery',realm='aegis';
function state(now=epoch+100,castAt=epoch):any { return recoveryRuntimeFixture(characterId,realm,now,castAt); }
function capture(before:any,now:number):any {
  const next=structuredClone(before);next.capturedAtUnixMs=now;
  next.abilities.globalCooldown=Math.max(0,(next.abilities.globalCooldownExpiresAtUnixMs-now)/1000);
  for (const row of next.abilities.cooldowns) row.remaining=Math.max(0,(row.expiresAtUnixMs-now)/1000);
  return next;
}
function periodic():any {
  const r=state(),d=r.combat.definitions[0],pure=JSON.parse(d.payload);
  Object.assign(pure.effects[0],{kind:'heal',statusId:'',statusKind:'',stackGroup:'',duration:0,
    magnitude:0,periodicDuration:30,minimum:10,maximum:10,hasAmount:true});
  d.payload=JSON.stringify(pure);d.sha256=createHash('sha256').update(d.payload).digest('hex');
  Object.assign(r.combat.statuses[0],{kind:'hot',category:'hot',group:'',magnitude:0,tickHealing:10,
    definitionSha256:d.sha256,nextTickAtUnixMs:epoch+1000,
    periodic:{base:10,strength:1,level:1,bonus:false,targetKey:`human:${characterId}`}});
  return r;
}

test('keeps exact epochs through capture work, supports natural expiry and retained expired stored rows', () => {
  const before=state(),after=capture(before,epoch+150);
  expect(() => validateCitadelRuntimeEvolution(before,after)).not.toThrow();
  const stalled=capture(before,epoch+31_000);
  expect(() => validateCitadelRuntimeEvolution(before,stalled)).not.toThrow();
  expect(() => validateCitadelRuntimeEvolution(before,recoveryRuntimeFixture(characterId,realm,epoch+31_000,epoch))).not.toThrow();
  const reset=structuredClone(after);reset.combat.statuses[0].expiresAtUnixMs+=30;
  expect(() => validateCitadelRuntimeEvolution(before,reset)).toThrow(/deadline changed/);
});

test('skips elapsed periodic cadence without changing immutable execution or replaying offline ticks', () => {
  const before=periodic(),after=capture(before,epoch+5100);after.combat.statuses[0].nextTickAtUnixMs=epoch+6000;
  expect(() => validateCitadelRuntimeEvolution(before,after)).not.toThrow();
  for (const next of [epoch+5000,epoch+6100,epoch+7000,epoch]) {
    const bad=structuredClone(after);bad.combat.statuses[0].nextTickAtUnixMs=next;
    expect(() => validateCitadelRuntimeEvolution(before,bad)).toThrow(/cadence/);
  }
  const changed=structuredClone(after);changed.combat.statuses[0].periodic.base=11;
  expect(() => validateCitadelRuntimeEvolution(before,changed)).toThrow(/values/);
});

test('derives fractional cadence quantization from the two integer-ms wire endpoints only',()=>{
  const before=periodic(),interval=Math.fround(.3333),d=before.combat.definitions[0],pure=JSON.parse(d.payload);
  pure.effects[0].interval=interval;d.payload=JSON.stringify(pure);d.sha256=createHash('sha256').update(d.payload).digest('hex');
  Object.assign(before.combat.statuses[0],{interval,nextTickAtUnixMs:epoch+333,definitionSha256:d.sha256});
  const after=capture(before,epoch+1500);after.combat.statuses[0].nextTickAtUnixMs=epoch+1666;
  expect(()=>validateCitadelRuntimeEvolution(before,after)).not.toThrow();
  after.combat.statuses[0].nextTickAtUnixMs=epoch+1668;
  expect(()=>validateCitadelRuntimeEvolution(before,after)).toThrow(/cadence/);
});

test.each([
  ['source', (r:any)=>{r.combat.statuses[0].sourceKey='human:somebody_else';}],
  ['shield', (r:any)=>{r.combat.statuses[0].shield=1;}],
  ['effect identity', (r:any)=>{r.combat.statuses[0].effectId='not_applied';}],
  ['lost status', (r:any)=>{r.combat.statuses=[];r.combat.definitions=[];}],
  ['class cooldown reset', (r:any)=>{r.abilities.cooldowns[0].expiresAtUnixMs+=30;r.abilities.cooldowns[0].remaining+=.03;}],
  ['global cooldown reset', (r:any)=>{r.abilities.globalCooldownExpiresAtUnixMs+=30;r.abilities.globalCooldown+=.03;}],
  ['class resource lost', (r:any)=>{r.abilities.resource=0;}],
  ['new opaque ASC', (r:any)=>{r.combat.ascEffects.push({id:'Unknown',expiresAtUnixMs:epoch+1000,level:1,stacks:1});}],
  ['historical runtime', (r:any)=>{r.version=1;}],
] as const)('rejects %s instead of ignoring combat',(_label,change)=>{
  const before=state(),after=capture(before,epoch+150);change(after);
  expect(() => validateCitadelRuntimeEvolution(before,after)).toThrow();
});

test('retains supported ASC identity and expiry, including an unchanged expired stored row',()=>{
  const before=state();before.combat.ascEffects=[{id:'DevelopmentStrikeCooldown',expiresAtUnixMs:epoch+2000,level:2,stacks:1}];
  expect(()=>validateCitadelRuntimeEvolution(before,capture(before,epoch+2100))).not.toThrow();
  const removed=capture(before,epoch+2100);removed.combat.ascEffects=[];
  expect(()=>validateCitadelRuntimeEvolution(before,removed)).not.toThrow();
  const bad=capture(before,epoch+150);bad.combat.ascEffects[0].expiresAtUnixMs+=30;
  expect(()=>validateCitadelRuntimeEvolution(before,bad)).toThrow(/ASC/);
});

test('requires a separately verified catalog self-cast to explain new or genuinely recast effects',()=>{
  const baseline=recoveryRuntimeFixture(characterId,realm,epoch),after=state(),cast=recoveryCastFixture(after,epoch);
  expect(()=>validateCitadelRecoveryCast(cast,after,characterId,realm)).not.toThrow();
  expect(()=>validateCitadelRuntimeEvolution(baseline,after,cast)).not.toThrow();
  expect(()=>validateCitadelRuntimeEvolution(baseline,after)).toThrow(/new combat status/);
  const recast=state(epoch+5100,epoch+5000),witness=recoveryCastFixture(recast,epoch+5000);
  expect(()=>validateCitadelRecoveryCast(witness,recast,characterId,realm)).not.toThrow();
  expect(()=>validateCitadelRuntimeEvolution(after,recast,witness)).not.toThrow();
  for (const update of [{succeeded:false},{statusIds:[]},{career:'another_career'},
    {observedAtUnixMs:epoch+200},{cooldownExpiresAtUnixMs:epoch+99_000}])
    expect(()=>validateCitadelRecoveryCast({...cast,...update},after,characterId,realm)).toThrow();
});

test('only an actual named self-cast may replace a previous native stack group',()=>{
  const before=state(),after=state(epoch+5100,epoch+5000),d=after.combat.definitions[0],pure=JSON.parse(d.payload);
  pure.id='battle_prelate.second_haste';pure.effects[0].id='second_haste';
  d.id=pure.id;d.payload=JSON.stringify(pure);d.sha256=createHash('sha256').update(d.payload).digest('hex');
  Object.assign(after.combat.statuses[0],{id:`${d.id}:second_haste:human:${characterId}`,abilityId:d.id,effectId:'second_haste',definitionSha256:d.sha256});
  after.abilities.cooldowns[0].id=d.id;
  after.abilities.cooldowns.push({...before.abilities.cooldowns[0],remaining:(before.abilities.cooldowns[0].expiresAtUnixMs-after.capturedAtUnixMs)/1000});
  const cast=recoveryCastFixture(after,epoch+5000);validateCitadelRecoveryCast(cast,after,characterId,realm);
  expect(()=>validateCitadelRuntimeEvolution(before,after,cast)).not.toThrow();
  const unrelated=structuredClone(before);unrelated.combat.statuses[0].group='other_group';
  expect(()=>validateCitadelRuntimeEvolution(unrelated,after,cast)).toThrow(/unexpired status disappeared/);
  const mismatched=structuredClone(after);mismatched.combat.statuses[0].group='other_group';
  expect(()=>validateCitadelRecoveryCast(cast,mismatched,characterId,realm)).toThrow(/self-cast/);
});

test('a genuine cast may change only its recorded native float resource cost and build',()=>{
  const baseline=recoveryRuntimeFixture(characterId,realm,epoch),after=state(),d=after.combat.definitions[0],pure=JSON.parse(d.payload);
  pure.cost=7;pure.build=2;d.payload=JSON.stringify(pure);d.sha256=createHash('sha256').update(d.payload).digest('hex');
  after.combat.statuses[0].definitionSha256=d.sha256;after.abilities.resource=15;
  const cast=recoveryCastFixture(after,epoch);validateCitadelRecoveryCast(cast,after,characterId,realm);
  expect(()=>validateCitadelRuntimeEvolution(baseline,after,cast)).not.toThrow();
  after.abilities.resource=14;
  expect(()=>validateCitadelRuntimeEvolution(baseline,after,cast)).toThrow(/class resource/);
});
