import { createHash } from 'node:crypto';
import { expect, test } from 'vitest';
import { validateNativeCampaignCharacter } from '../shared/siege/character';
import type { ScenarioCharacter } from '../shared/scenarios/types';
import { nativeDefinitionSha256, nativeCombatantKey } from '../shared/siege/runtime';
import { createCampaign, restoreCampaign } from '../shared/orvr';
import { nativeSiegeRequest } from '../server/nativeSiege';

function appliedPayload() {
  const effect = { id: 'burn', recipient: 'target', kind: 'status', school: 'fire', statusId: 'burn', statusKind: 'burn',
    modifier: '', stackGroup: 'fire', direction: '', label: 'Burn', minimum: 0, maximum: 0, statScale: 0, levelScale: 0,
    resourceScale: 0, duration: 30, magnitude: .2, distance: 0, periodicDuration: 0, interval: 1, hasAmount: false, cleanse: [] };
  return { schemaVersion: 1, units: 'native_cm_seconds', id: 'ember_arcanist.burn', career: 'ember_arcanist', version: 'applied-old-version',
    shape: 'single', school: 'fire', assignmentId: '', targetKind: 'enemy', timingMode: 'instant', name: 'Burn', summary: '', unavailableReason: '',
    resourceLabel: 'Heat', slot: 0, unlockLevel: 1, enemyTarget: true, spendAll: false, blockedBySilence: true, legacyTargeting: false,
    authoredTiming: true, cancelOnMovement: false, preparationScale: 1, range: 900, radius: 0, projectileSpeed: 0, cooldown: 30, gcd: 1,
    mana: 20, build: 0, cost: 0, minimumResource: 0, resourceMax: 100, resourceInitial: 0, releaseFraction: .4,
    castSeconds: 0, channelSeconds: 0, tickInterval: 1, maxTargets: 1, presentations: {}, effects: [effect], conditions: [] };
}

export function runtimeCharacterFixture(): ScenarioCharacter {
  const capturedAtUnixMs = 1_800_000_000_000, payload = JSON.stringify(appliedPayload());
  const sha256 = createHash('sha256').update(payload).digest('hex');
  return { id: 'stable_hero', realm: 'aegis', name: 'Hero', visual: '/Game/Characters/Hero', returnMap: '/Game/World', returnPosition: [10, 20, 30],
    document: { zone: 'aegis_capital', inventory: { revision: 1 }, runtime: { version: 2, capturedAtUnixMs, health: 1200, mana: 300,
      rewards: ['12345678-1234-1234-1234-123456789abc'], questKills: [], dead: false,
      abilities: { resource: 20, globalCooldown: 1, globalCooldownExpiresAtUnixMs: capturedAtUnixMs + 1000,
        cooldowns: [{ id: 'ember_arcanist.burn', remaining: 30, expiresAtUnixMs: capturedAtUnixMs + 30000 }] },
      combat: { version: 1, definitions: [{ id: 'ember_arcanist.burn', career: 'ember_arcanist', version: 'applied-old-version', payload, sha256 }],
        statuses: [{ id: 'ember_arcanist.burn:burn:human:stable_caster', kind: 'burn', group: 'fire', modifier: '', label: 'Burn',
          magnitude: .2, shield: 0, tickDamage: 15, tickHealing: 0, interval: 1, expiresAtUnixMs: capturedAtUnixMs + 30000,
          nextTickAtUnixMs: capturedAtUnixMs + 1000, sourceKey: 'human:stable_caster', sourceRealm: 'aegis', abilityId: 'ember_arcanist.burn',
          effectId: 'burn', category: 'dot', appliedVersion: 'applied-old-version', definitionSha256: sha256 }],
        ascEffects: [{ id: 'DevelopmentStrikeCooldown', expiresAtUnixMs: capturedAtUnixMs + 1000, level: 1, stacks: 1 }] } } } };
}

test('v2 normal character runtime keeps exact applied definitions, timers and partially consumed state', () => {
  const character = runtimeCharacterFixture(), before = JSON.stringify(character);
  expect(() => validateNativeCampaignCharacter(character)).not.toThrow();
  expect(JSON.stringify(character)).toBe(before);
  const expired: any = structuredClone(character);
  expired.document.runtime.capturedAtUnixMs += 60_000;
  expired.document.runtime.abilities.globalCooldown = 0;
  expired.document.runtime.abilities.cooldowns[0].remaining = 0;
  // Storage validation does not invent offline ticks or replace old definitions.
  expect(() => validateNativeCampaignCharacter(expired)).not.toThrow();
});

test('v2 runtime rejects unsupported versions, malformed epochs and silent legacy fallback', () => {
  for (const change of [
    (r: any) => { r.version = 3; }, (r: any) => { delete r.capturedAtUnixMs; },
    (r: any) => { r.capturedAtUnixMs = NaN; }, (r: any) => { r.abilities.globalCooldownExpiresAtUnixMs = -1; },
    (r: any) => { delete r.combat; }, (r: any) => { r.abilities.cooldowns[0].remaining = 1; },
    (r: any) => { delete r.version; },
  ]) { const character: any = runtimeCharacterFixture(); change(character.document.runtime);
    expect(() => validateNativeCampaignCharacter(character)).toThrow(); }
  const old: any = runtimeCharacterFixture();
  delete old.document.runtime.version; delete old.document.runtime.capturedAtUnixMs; delete old.document.runtime.combat;
  delete old.document.runtime.abilities.globalCooldownExpiresAtUnixMs; delete old.document.runtime.abilities.cooldowns[0].expiresAtUnixMs;
  expect(() => validateNativeCampaignCharacter(old)).not.toThrow();
});

test('v2 runtime requires exact hash-bound applied effect references and stable source identities', () => {
  for (const change of [
    (r: any) => { r.combat.definitions[0].payload += ' '; }, (r: any) => { r.combat.statuses[0].definitionSha256 = 'f'.repeat(64); },
    (r: any) => { r.combat.statuses[0].appliedVersion = 'current-catalog'; },
    (r: any) => { r.combat.statuses[0].effectId = 'not-in-applied-definition'; },
    (r: any) => { r.combat.statuses[0].sourceKey = '/Game/World:PersistentLevel.Player_123'; },
    (r: any) => { r.combat.statuses[0].sourceKey = 'encounter:activation:2:riftbound:guard:0'; },
    (r: any) => { r.combat.statuses.push(structuredClone(r.combat.statuses[0])); },
    (r: any) => { r.combat.ascEffects[0].id = '/Script/UnknownEffect'; },
    (r: any) => { r.combat.ascEffects[0].stacks = 2; },
  ]) { const character: any = runtimeCharacterFixture(); change(character.document.runtime);
    expect(() => validateNativeCampaignCharacter(character)).toThrow(); }
});

test('pure payload hashing agrees with exact UTF8 bytes and retained multiline authored text', () => {
  for (const text of ['', 'abc', 'é盾 😀', '\ud800', 'a'.repeat(1000)])
    expect(nativeDefinitionSha256(text)).toBe(createHash('sha256').update(text).digest('hex'));
  const character: any = runtimeCharacterFixture(), row = character.document.runtime.combat.definitions[0];
  const value = JSON.parse(row.payload); value.summary = 'A crafted\nmultiline é description';
  row.payload = JSON.stringify(value); row.sha256 = nativeDefinitionSha256(row.payload);
  character.document.runtime.combat.statuses[0].definitionSha256 = row.sha256;
  expect(() => validateNativeCampaignCharacter(character)).not.toThrow();
});

test('pure applied schemas reject weakened timing and hidden default-action state while retaining legacy recipients', () => {
  const emptyEffect = { id:'',recipient:'',kind:'',school:'',statusId:'',statusKind:'',modifier:'',stackGroup:'',direction:'',label:'',
    minimum:0,maximum:0,statScale:0,levelScale:0,resourceScale:0,duration:0,magnitude:0,distance:0,periodicDuration:0,interval:1,
    hasAmount:false,cleanse:[] };
  const payload = appliedPayload();
  payload.effects.push({ ...payload.effects[0],id:'damage',kind:'damage',statusKind:'',hasAmount:true,minimum:5,maximum:10 });
  (payload.conditions as any[]).push({ id:'conditional',event:'application',name:'Recorded',
    condition:{kind:'all',subject:'',source:'',abilityId:'',effectId:'',not:false,
      children:[{kind:'hot',subject:'target',source:'any',abilityId:'',effectId:'',not:false,children:[]}]},
    actions:[{kind:'flat',effectId:'damage',value:1,effect:emptyEffect}] });
  const validate = (change: (v: any) => void) => {
    const character:any = runtimeCharacterFixture(), value=structuredClone(payload); change(value);
    const row=character.document.runtime.combat.definitions[0]; row.payload=JSON.stringify(value); row.sha256=nativeDefinitionSha256(row.payload);
    character.document.runtime.combat.statuses[0].definitionSha256=row.sha256;
    return () => validateNativeCampaignCharacter(character);
  };
  expect(validate(() => {})).not.toThrow();
  expect(validate(v => { v.legacyTargeting=true;v.effects[0].recipient=''; })).not.toThrow();
  for (const change of [
    (v:any) => { v.resourceMax=0; }, (v:any) => { v.resourceInitial=101; }, (v:any) => { v.preparationScale=.01; },
    (v:any) => { v.cooldown=3601; }, (v:any) => { v.gcd=61; }, (v:any) => { v.releaseFraction=.99; },
    (v:any) => { v.timingMode='opaque_mode'; }, (v:any) => { v.effects[0].recipient=''; },
    (v:any) => { v.effects[0].duration=.001; }, (v:any) => { v.effects[1].hasAmount=false; },
    (v:any) => { v.conditions[0].actions[0].effect.label='hidden status'; },
    (v:any) => { v.conditions[0].actions[0].effect.interval=0; },
    (v:any) => { v.conditions[0].actions[0].effectId='missing'; },
    (v:any) => { v.conditions[0].actions[0].kind='percent';v.conditions[0].actions[0].value=101; },
    (v:any) => { v.conditions[0].event='tick'; },
    (v:any) => { v.conditions[0].condition=v.conditions[0].condition.children[0]; },
  ]) expect(validate(change)).toThrow();
});

test('bounded codec rejects missing native fields, opaque payloads, excess rows and forged stable keys', () => {
  for (const change of [
    (r: any) => { r.combat.statuses = Array(129).fill(r.combat.statuses[0]); },
    (r: any) => { r.combat.definitions = Array(129).fill(r.combat.definitions[0]); },
    (r: any) => { r.combat.ascEffects = Array(17).fill(r.combat.ascEffects[0]); },
    (r: any) => { r.abilities.cooldowns = Array(257).fill(r.abilities.cooldowns[0]); },
    (r: any) => { const row = r.combat.definitions[0], value = JSON.parse(row.payload); delete value.units;
      row.payload = JSON.stringify(value); row.sha256 = nativeDefinitionSha256(row.payload); },
    (r: any) => { r.combat.statuses[0].periodic = { base: 15, strength: 90, level: 12, bonus: false, targetKey: '/Game/TransientPawn' }; },
    (r: any) => { r.combat.statuses[0].expiresAtUnixMs = Infinity; },
    (r: any) => { r.combat.statuses[0].nextTickAtUnixMs = 1.5; },
    (r: any) => { r.combat.statuses[0].expiresAtUnixMs = r.capturedAtUnixMs+60_002; },
    (r: any) => { r.combat.ascEffects[0].expiresAtUnixMs = r.capturedAtUnixMs+3_600_002; },
    (r: any) => { r.health = 1e99; },
    (r: any) => { r.rewards = ['same', 'same']; },
    (r: any) => { r.rewards = ['not-a-native-receipt']; },
    (r: any) => { r.rewards.push('12345678123412341234123456789ABC'); },
    (r: any) => { r.arbitraryAscObject = '/Script/UnsafeObject'; },
  ]) { const character: any = runtimeCharacterFixture(); change(character.document.runtime);
    expect(() => validateNativeCampaignCharacter(character)).toThrow(); }
  for (const value of ['human:stable_caster', 'authored:/Game/WorldRebuild/Layer#WarZoneObject_aegis_capital_Guard',
    'encounter:campaign:1:aegis_capital:1:2:riftbound:guard:0:12345678-1234-1234-1234-123456789abc'])
    expect(nativeCombatantKey(value)).toBe(true);
  for (const value of ['human:__proto__','authored:/Game/../Other#WarWorldObject_guard','authored:/Game//Other#WarWorldObject_guard',
    'encounter:a:2:riftbound:guard:128:12345678123412341234123456789abc']) expect(nativeCombatantKey(value)).toBe(false);
});

test('new v2 custody bounds actual UTF8 storage bytes while historical documents keep recorded compatibility', () => {
  const character:any=runtimeCharacterFixture();character.document.inventory.unicode='\u76fe'.repeat(90_000);
  expect(JSON.stringify(character).length).toBeLessThan(262_144);
  expect(Buffer.byteLength(JSON.stringify(character),'utf8')).toBeGreaterThan(262_144);
  expect(() => validateNativeCampaignCharacter(character)).toThrow(/oversized/);
  delete character.document.runtime.version;delete character.document.runtime.capturedAtUnixMs;delete character.document.runtime.combat;
  delete character.document.runtime.abilities.globalCooldownExpiresAtUnixMs;delete character.document.runtime.abilities.cooldowns[0].expiresAtUnixMs;
  expect(() => validateNativeCampaignCharacter(character)).not.toThrow();
});

test('owning journal retains full v2 snapshots and prevents a later relative-timer downgrade or capture rewind', () => {
  const state = createCampaign({ id: 'runtime-v2-fixture' }); state.phase = 'city';
  for (const key of ['dawnline_expanse','aegis_crownworks','aegis_gate_fortress']) state.zones[key].victor = 'riftbound';
  const city = state.zones.aegis_capital;
  Object.assign(city,{cityAttacker:'riftbound',status:'staging',stagingRemaining:180,activationId:'runtime-v2:1:aegis_capital:1',activation:1,cityRemaining:1800});
  const options = { bootstrapKey:'b'.repeat(64),verifyContent:()=>'reviewed',now:()=>1000 }, hostId='codec-host';
  const registration = nativeSiegeRequest(state,'register',{hostId},options.bootstrapKey,options).response as {token:string};
  nativeSiegeRequest(state,'activate',{hostId,requestId:'activate',rulesVersion:2,contentRevision:'reviewed'},registration.token,options);
  const activationId=city.activationId, character=runtimeCharacterFixture();
  nativeSiegeRequest(state,'membership',{hostId,activationId,requestId:'join',action:'join',characterId:character.id,realm:character.realm,character},registration.token,options);
  const restored=restoreCampaign(JSON.parse(JSON.stringify(state)));
  expect(restored.nativeSiegeJournal!.characters!['codec-host:stable_hero'].character).toEqual(character);
  for (const rewind of [false,true]) {
    const changed: any = structuredClone(character); changed.document.inventory.revision++;
    if (rewind) changed.document.runtime.capturedAtUnixMs--;
    else { delete changed.document.runtime.version;delete changed.document.runtime.capturedAtUnixMs;delete changed.document.runtime.combat;
      delete changed.document.runtime.abilities.globalCooldownExpiresAtUnixMs;delete changed.document.runtime.abilities.cooldowns[0].expiresAtUnixMs; }
    expect(() => nativeSiegeRequest(state,'checkpoint',{hostId,activationId,requestId:'bad-'+rewind,scope:'participant',character:changed},registration.token,options)).toThrow();
    expect(state.nativeSiegeJournal!.characters!['codec-host:stable_hero'].character).toEqual(character);
  }
});
