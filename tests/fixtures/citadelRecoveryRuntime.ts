import { createHash } from 'node:crypto';
/** Synthetic portable codec rows, never an actual native catalog or process witness. */
export const RECOVERY_EPOCH=1_800_000_000_000;
export function recoveryRuntimeFixture(characterId:string,realm:string,now=RECOVERY_EPOCH,castAt?:number):any {
  const effect={id:'self_haste',recipient:'caster',kind:'player_status',school:'',statusId:'haste',statusKind:'haste',
    modifier:'',stackGroup:'self_haste',direction:'',label:'Portable haste',minimum:0,maximum:0,statScale:0,levelScale:0,
    resourceScale:0,duration:30,magnitude:.2,distance:0,periodicDuration:0,interval:1,hasAmount:false,cleanse:[]};
  const payload=JSON.stringify({schemaVersion:1,units:'native_cm_seconds',id:'battle_prelate.self_haste',career:'battle_prelate',version:'portable-v1',
    shape:'single',school:'',assignmentId:'',targetKind:'self',timingMode:'instant',name:'Portable haste',summary:'',unavailableReason:'',
    resourceLabel:'',slot:0,unlockLevel:1,enemyTarget:false,spendAll:false,blockedBySilence:true,legacyTargeting:false,
    authoredTiming:true,cancelOnMovement:false,preparationScale:1,range:0,radius:0,projectileSpeed:0,cooldown:30,gcd:1,
    mana:0,build:0,cost:0,minimumResource:0,resourceMax:100,resourceInitial:0,releaseFraction:.4,castSeconds:0,
    channelSeconds:0,tickInterval:1,maxTargets:1,presentations:{},effects:[effect],conditions:[]});
  const definition={id:'battle_prelate.self_haste',career:'battle_prelate',version:'portable-v1',payload,
    sha256:createHash('sha256').update(payload).digest('hex')};
  const expiry=(castAt ?? 0)+30_000,active=castAt!==undefined && expiry>now;
  const status={id:`battle_prelate.self_haste:self_haste:human:${characterId}`,kind:'haste',group:'self_haste',modifier:'',label:'Portable haste',
    magnitude:.2,shield:0,tickDamage:0,tickHealing:0,interval:1,expiresAtUnixMs:expiry,nextTickAtUnixMs:0,
    sourceKey:`human:${characterId}`,sourceRealm:realm,abilityId:definition.id,effectId:'self_haste',category:'status',
    appliedVersion:definition.version,definitionSha256:definition.sha256};
  return {version:2,capturedAtUnixMs:now,health:2000,mana:300,dead:false,rewards:[],questKills:['0123456789abcdef0123456789abcdef'],
    abilities:{resource:20,globalCooldown:Math.max(0,((castAt ?? 0)+1000-now)/1000),
      globalCooldownExpiresAtUnixMs:castAt===undefined ? 0 : castAt+1000,
      cooldowns:active ? [{id:definition.id,remaining:(expiry-now)/1000,expiresAtUnixMs:expiry}] : []},
    combat:{version:1,definitions:active ? [definition] : [],statuses:active ? [status] : [],ascEffects:[]}};
}
export function recoveryCastFixture(runtime:any,castAt:number):any {
  const d=runtime.combat.definitions[0];return {abilityId:d.id,career:d.career,version:d.version,definitionSha256:d.sha256,
    startedAtUnixMs:castAt,succeeded:true,observedAtUnixMs:runtime.capturedAtUnixMs,
    statusIds:runtime.combat.statuses.map((s:any)=>s.id),cooldownExpiresAtUnixMs:runtime.abilities.cooldowns[0].expiresAtUnixMs};
}
