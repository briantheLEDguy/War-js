import { validateNativeRuntime, type NativeNormalRuntimeV2 } from '../../shared/siege/runtime';

export interface CitadelRecoveryCast {
  abilityId:string; career:string; version:string; definitionSha256:string; startedAtUnixMs:number;
  succeeded:true; observedAtUnixMs:number; statusIds:string[]; cooldownExpiresAtUnixMs:number;
}
const canonical=(v:any):string => JSON.stringify(Array.isArray(v) ? v.map(sort) : sort(v));
function sort(v:any):any { return Array.isArray(v) ? v.map(sort) : v && typeof v==='object'
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k,sort(v[k])])) : v; }
const same=(a:any,b:any) => canonical(a)===canonical(b);
function fail(message:string):never { throw new Error('Invalid recovery runtime progression: '+message); }
function runtime(value:any):NativeNormalRuntimeV2 {
  validateNativeRuntime(value);
  if (value.version!==2) fail('fresh process evidence requires the complete epoch codec');
  return value;
}

/** This witness binds a genuine native self-buff; it does not authorize arbitrary status creation. */
export function validateCitadelRecoveryCast(value:any, state:any, characterId:string, realm:string):CitadelRecoveryCast {
  const r=runtime(state), definition=r.combat.definitions.find(d => d.sha256===value?.definitionSha256);
  if (!value || Object.keys(value).sort().join(',')!=='abilityId,career,cooldownExpiresAtUnixMs,definitionSha256,observedAtUnixMs,startedAtUnixMs,statusIds,succeeded,version'
    || value.succeeded!==true || !definition || definition.id!==value.abilityId || definition.career!==value.career || definition.version!==value.version
    || !Number.isSafeInteger(value.startedAtUnixMs) || value.startedAtUnixMs<=0 || value.startedAtUnixMs>r.capturedAtUnixMs
    || value.observedAtUnixMs!==r.capturedAtUnixMs || !Array.isArray(value.statusIds) || !value.statusIds.length
    || value.statusIds.some((id:any) => typeof id!=='string') || new Set(value.statusIds).size!==value.statusIds.length) fail('actual catalog cast identity or times');
  const applied=JSON.parse(definition.payload), statuses=r.combat.statuses.filter(s => s.abilityId===value.abilityId
    && s.appliedVersion===value.version && s.definitionSha256===value.definitionSha256);
  const effects=[...applied.effects,...applied.conditions.flatMap((rule:any)=>rule.actions
    .filter((action:any)=>action.kind==='add_effect').map((action:any)=>action.effect))];
  const statusMatches=(s:any):boolean=>{
    const effect=effects.find((e:any)=>e.id===s.effectId);
    return !!effect && effect.kind==='player_status' && (effect.recipient==='caster' || applied.legacyTargeting && effect.recipient==='')
      && s.id===(effect.recipient!=='' ? `${definition.id}:${effect.id}:${s.sourceKey}` : `${definition.id}:${effect.statusId}:${effect.statusKind}`)
      && s.kind===effect.statusKind && s.group===effect.stackGroup && s.modifier===effect.modifier
      && s.label===(effect.label || effect.statusKind) && s.category===(s.kind==='shield' ? 'shield' : 'status')
      && s.magnitude===Math.min(effect.magnitude,s.kind==='guard' ? .75 : Math.fround(.6))
      && s.interval===1 && s.tickDamage===0 && s.tickHealing===0 && s.periodic===undefined
      && s.expiresAtUnixMs-r.capturedAtUnixMs<=effect.duration*1000+1;
  };
  if (applied.enemyTarget!==false || !['self','ally'].includes(applied.targetKind) || !applied.effects.length
    || applied.effects.some((e:any) => e.kind!=='player_status' || (e.recipient!=='caster' && !(applied.legacyTargeting && e.recipient==='')))
    || !same(statuses.map(s=>s.id).sort(),[...value.statusIds].sort())
    || statuses.some(s => !statusMatches(s) || s.sourceKey!==`human:${characterId}` || s.sourceRealm!==realm || s.expiresAtUnixMs<=r.capturedAtUnixMs)
    || !r.abilities.cooldowns.some(c => c.id===value.abilityId && c.expiresAtUnixMs===value.cooldownExpiresAtUnixMs
      && c.expiresAtUnixMs>r.capturedAtUnixMs && c.expiresAtUnixMs-r.capturedAtUnixMs<=applied.cooldown*1000+1)) fail('actual self-cast status or cooldown');
  return value;
}

/** Fixed epochs cannot reset after a crash. Only natural expiry and skipped tick cadence may change. */
export function validateCitadelRuntimeEvolution(before:any, after:any, cast?:CitadelRecoveryCast):void {
  const a=runtime(before),b=runtime(after),now=b.capturedAtUnixMs;
  if (now<a.capturedAtUnixMs) fail('capture epoch moved backwards');
  let resource=a.abilities.resource;
  if (cast) {
    const definition=b.combat.definitions.find(d=>d.sha256===cast.definitionSha256);
    if (!definition) fail('cast has no recorded resource definition');
    const applied=JSON.parse(definition.payload);
    resource=Math.min(applied.resourceMax,Math.max(0,Math.fround(Math.fround(applied.spendAll ? 0 : resource-applied.cost)+applied.build)));
    if (b.abilities.globalCooldownExpiresAtUnixMs-now>applied.gcd*1000+1) fail('actual cast cannot extend its recorded global cooldown');
  }
  if (b.abilities.resource!==resource) fail('class resource lost or changed without its actual cast');
  const recast=(s:any) => !!cast && cast.statusIds.includes(s.id) && s.abilityId===cast.abilityId
    && s.appliedVersion===cast.version && s.definitionSha256===cast.definitionSha256;
  const oldStatuses=new Map(a.combat.statuses.map(s=>[s.id,s]));
  const nextStatuses=new Map(b.combat.statuses.map(s=>[s.id,s]));
  const replaced=(s:any)=>!!cast && b.combat.statuses.some(next=>recast(next)
    && (s.group!=='' && s.group===next.group || s.kind==='shield' && next.kind==='shield'));
  for (const old of a.combat.statuses) {
    const next=nextStatuses.get(old.id);
    if (next && recast(next)) continue;
    if (!next) { if (old.expiresAtUnixMs>now && !replaced(old)) fail('unexpired status disappeared');continue; }
    const oldValues={...old},newValues={...next};delete (oldValues as any).nextTickAtUnixMs;delete (newValues as any).nextTickAtUnixMs;
    if (!same(oldValues,newValues)) fail('surviving status values, source, definition or deadline changed');
    const difference=next.nextTickAtUnixMs-old.nextTickAtUnixMs,interval=old.interval*1000;
    // Two independently rounded integer-ms endpoints contribute at most 1 ms;
    // expiry epochs remain exact and never share this cadence quantization.
    const steps=Math.round(difference/interval);
    if (difference<0 || difference && (steps<1 || Math.abs(difference-steps*interval)>1
      || next.nextTickAtUnixMs<=now || next.nextTickAtUnixMs>now+interval+1)) fail('tick cadence reset instead of skipping overdue ticks');
  }
  for (const next of b.combat.statuses) if (!oldStatuses.has(next.id) && !recast(next)) fail('unsupported new combat status');
  const definitions=new Map(a.combat.definitions.map(d=>[d.sha256,d]));
  const used=new Set(b.combat.statuses.map(s=>s.definitionSha256));
  if (used.size!==b.combat.definitions.length) fail('unreferenced or missing applied definition');
  for (const d of b.combat.definitions) if (!used.has(d.sha256) || (definitions.has(d.sha256)
    ? !same(definitions.get(d.sha256),d) : d.sha256!==cast?.definitionSha256)) fail('immutable applied definition replaced');
  const oldAsc=new Map(a.combat.ascEffects.map(s=>[s.id,s])),newAsc=new Map(b.combat.ascEffects.map(s=>[s.id,s]));
  for (const old of a.combat.ascEffects) {
    const next=newAsc.get(old.id);
    if (next ? !same(old,next) : old.expiresAtUnixMs>now) fail('supported ASC values or deadline changed');
  }
  if (b.combat.ascEffects.some(s=>!oldAsc.has(s.id))) fail('new ASC entry has no actual cast witness');
  const oldCooldowns=new Map(a.abilities.cooldowns.map(c=>[c.id,c]));
  const newCooldowns=new Map(b.abilities.cooldowns.map(c=>[c.id,c]));
  for (const old of a.abilities.cooldowns) {
    const next=newCooldowns.get(old.id);
    if (cast?.abilityId===old.id && next?.expiresAtUnixMs===cast.cooldownExpiresAtUnixMs) continue;
    if (old.expiresAtUnixMs>now && (!next || next.expiresAtUnixMs!==old.expiresAtUnixMs)) fail('unexpired class cooldown lost or reset');
    if (old.expiresAtUnixMs<=now && next && next.expiresAtUnixMs>now) fail('expired class cooldown restarted');
  }
  for (const next of b.abilities.cooldowns) if (!oldCooldowns.has(next.id)
    && !(next.id===cast?.abilityId && next.expiresAtUnixMs===cast.cooldownExpiresAtUnixMs)) fail('new class cooldown lacks its actual cast');
  if (!cast && (a.abilities.globalCooldownExpiresAtUnixMs>now
    ? b.abilities.globalCooldownExpiresAtUnixMs!==a.abilities.globalCooldownExpiresAtUnixMs
    : b.abilities.globalCooldownExpiresAtUnixMs>now)) fail('global cooldown reset');
}
