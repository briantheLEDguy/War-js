/** Pure trusted-host codec contracts. No UObject, client effect or live catalog can replace an applied definition. */
export interface NativeAppliedDefinition {
  id: string; career: string; version: string; payload: string; sha256: string;
}
export interface NativeCombatStatus {
  id: string; kind: string; group: string; modifier: string; label: string;
  magnitude: number; shield: number; tickDamage: number; tickHealing: number; interval: number;
  expiresAtUnixMs: number; nextTickAtUnixMs: number;
  sourceKey: string; sourceRealm: '' | 'aegis' | 'riftbound'; abilityId: string; effectId: string;
  category: 'status' | 'shield' | 'dot' | 'hot'; appliedVersion: string; definitionSha256: string;
  periodic?: { base: number; strength: number; level: number; bonus: boolean; targetKey: string };
}
export interface NativeNormalRuntimeV2 {
  version: 2; capturedAtUnixMs: number; health: number; mana: number; dead: boolean;
  rewards: string[]; questKills: string[];
  abilities: { resource: number; globalCooldown: number; globalCooldownExpiresAtUnixMs: number;
    cooldowns: { id: string; remaining: number; expiresAtUnixMs: number }[] };
  combat: { version: 1; definitions: NativeAppliedDefinition[]; statuses: NativeCombatStatus[];
    ascEffects: { id: 'DevelopmentStrikeCooldown'; expiresAtUnixMs: number; level: number; stacks: 1 }[] };
}
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const forbidden = new Set(['__proto__', 'prototype', 'constructor']);
const keys = (value: Record<string, unknown>, required: readonly string[], optional: readonly string[] = []) =>
  required.every(k => Object.hasOwn(value, k)) && Object.keys(value).every(k => required.includes(k) || optional.includes(k));
const numeric = (v: unknown, min = 0, max = 1_000_000) => typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max;
const epoch = (v: unknown) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const text = (v: unknown, max: number, empty = false): v is string => typeof v === 'string' && v.length <= max
  && (empty || v.length > 0) && !/[\x00-\x1f\x7f]/.test(v);
const prose = (v: unknown, max: number): v is string => typeof v === 'string' && v.length <= max
  && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(v);
const name = (v: unknown, empty = false): v is string => text(v, 160, empty) && (empty && v === ''
  || /^[a-zA-Z0-9_.:-]+$/.test(v)) && !forbidden.has(v);
const hash = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const receipt = (v: unknown): v is string => typeof v === 'string'
  && /^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$/.test(v);
function fail(reason: string): never { throw new Error('Invalid native runtime v2: ' + reason); }

function utf8(value: string): number[] {
  const bytes: number[] = [];
  for (const char of value) {
    let cp = char.codePointAt(0)!;
    if (cp >= 0xd800 && cp <= 0xdfff) cp = 0xfffd;
    if (cp < 0x80) bytes.push(cp);
    else if (cp < 0x800) bytes.push(0xc0 | cp >>> 6, 0x80 | cp & 63);
    else if (cp < 0x10000) bytes.push(0xe0 | cp >>> 12, 0x80 | cp >>> 6 & 63, 0x80 | cp & 63);
    else bytes.push(0xf0 | cp >>> 18, 0x80 | cp >>> 12 & 63, 0x80 | cp >>> 6 & 63, 0x80 | cp & 63);
  }
  return bytes;
}
export function nativeUtf8ByteLength(value: string): number {
  let length=0;
  for (const char of value) {
    const cp=char.codePointAt(0)!;
    length+=cp<0x80 ? 1 : cp<0x800 ? 2 : cp<0x10000 ? 3 : 4;
  }
  return length;
}

/** Exact UTF-8 bytes; synchronous shared validation also runs when restoring a journal. */
export function nativeDefinitionSha256(payload: string): string {
  const bytes = utf8(payload), bits = bytes.length * 8;
  bytes.push(0x80); while (bytes.length % 64 !== 56) bytes.push(0);
  bytes.push(0, 0, 0, 0, bits >>> 24 & 255, bits >>> 16 & 255, bits >>> 8 & 255, bits & 255);
  const constants = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  const state = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const rotate = (v: number, amount: number) => v >>> amount | v << 32 - amount;
  for (let offset = 0; offset < bytes.length; offset += 64) {
    const words = new Array<number>(64);
    for (let i = 0; i < 16; i++) { const p = offset + i * 4; words[i] = bytes[p] << 24 | bytes[p + 1] << 16 | bytes[p + 2] << 8 | bytes[p + 3]; }
    for (let i = 16; i < 64; i++) {
      const a = words[i - 15], b = words[i - 2];
      words[i] = (words[i - 16] + (rotate(a,7) ^ rotate(a,18) ^ a >>> 3) + words[i - 7] + (rotate(b,17) ^ rotate(b,19) ^ b >>> 10)) >>> 0;
    }
    let [a,b,c,d,e,f,g,h] = state;
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rotate(e,6) ^ rotate(e,11) ^ rotate(e,25)) + (e & f ^ ~e & g) + constants[i] + words[i]) >>> 0;
      const t2 = ((rotate(a,2) ^ rotate(a,13) ^ rotate(a,22)) + (a & b ^ a & c ^ b & c)) >>> 0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
    }
    [a,b,c,d,e,f,g,h].forEach((v,i) => { state[i]=(state[i]+v)>>>0; });
  }
  return state.map(v => v.toString(16).padStart(8,'0')).join('');
}

export function nativeCombatantKey(value: unknown, empty = false): value is string {
  if (!text(value, 512, empty)) return false;
  if (value === '') return empty;
  const human = /^human:([a-zA-Z0-9_-]{1,80})$/.exec(value);
  if (human) return !forbidden.has(human[1]);
  if (/^authored:\/Game\/[a-zA-Z0-9_/-]+#War(?:World|Zone)Object_[a-zA-Z0-9_]+$/.test(value))
    return !value.includes('//') && !value.includes('..');
  const encounter = /^encounter:[a-zA-Z0-9_:-]{1,160}:[012]:(?:aegis|riftbound):[a-zA-Z0-9_-]{1,80}:([0-9]{1,3}):(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$/.exec(value);
  return !!encounter && Number(encounter[1]) <= 127;
}

const effectNames = ['id','recipient','kind','school','statusId','statusKind','modifier','stackGroup','direction'];
const effectNumbers = ['minimum','maximum','statScale','levelScale','resourceScale','duration','magnitude','distance','periodicDuration','interval'];
function effect(value: unknown, allowDefault = false, legacy = false): Record<string, unknown> {
  if (!object(value) || !keys(value, [...effectNames,...effectNumbers,'label','hasAmount','cleanse'])
    || effectNames.some(k => !name(value[k], true)) || effectNumbers.some(k => !numeric(value[k]))
    || !prose(value.label, 512) || typeof value.hasAmount !== 'boolean' || !Array.isArray(value.cleanse)
    || value.cleanse.length > 32 || value.cleanse.some(k => !name(k))) fail('applied effect fields');
  if (allowDefault) {
    if (effectNames.some(k => value[k] !== '') || effectNumbers.some(k => value[k] !== (k === 'interval' ? 1 : 0))
      || value.label !== '' || value.hasAmount !== false || value.cleanse.length) fail('nondefault conditional modifier effect');
    return value;
  }
  if (!name(value.id) || !['damage','heal','status','player_status','movement','cleanse','wrath_relic','warp_idol'].includes(value.kind as string)
    || !(legacy && value.recipient === '' || ['caster','target','allies','enemies'].includes(value.recipient as string))
    || (value.minimum as number) > (value.maximum as number) || (value.duration as number) > 60
    || (value.periodicDuration as number) > 60 || (value.interval as number) < .1
    || (value.distance as number) > 1200 || ['statScale','levelScale','resourceScale'].some(k => (value[k] as number) > 1000)
    || ['damage','heal','warp_idol'].includes(value.kind as string) && !value.hasAmount
    || value.kind === 'warp_idol' && (value.minimum as number) <= 0
    || (value.periodicDuration as number) > 0 && (!['damage','heal'].includes(value.kind as string)
      || (value.periodicDuration as number) < .1 || (value.interval as number) > (value.periodicDuration as number))) fail('applied effect semantics');
  if (value.kind === 'status' || value.kind === 'player_status') {
    const permitted = value.kind === 'status' ? ['burn','bleed','slow','root','silence','stagger','mark','debuff'] : ['shield','guard','empower','haste'];
    const limit = ['root','silence','stagger'].includes(value.statusKind as string) ? 1 : value.statusKind === 'guard' ? .75 : Math.fround(.6);
    if (!permitted.includes(value.statusKind as string) || (value.duration as number) < Math.fround(.01) || (value.magnitude as number) > limit)
      fail('applied status semantics');
  }
  if (value.kind === 'movement' && (value.recipient !== 'caster' && !(legacy && value.recipient === '')
      || !['forward','backward','toward_target'].includes(value.direction as string))
    || value.kind === 'cleanse' && value.cleanse.some(v => !['slow','root','stagger','debuff'].includes(v as string))) fail('applied movement or cleanse');
  return value;
}
function condition(value: unknown, depth = 1, budget = { leaves: 0 }): void {
  if (!object(value) || !keys(value,['kind','subject','source','abilityId','effectId','not','children'])
    || ['kind','subject','source','abilityId','effectId'].some(k => !name(value[k], true))
    || typeof value.not !== 'boolean' || !Array.isArray(value.children)) fail('pure condition fields');
  if (value.kind === 'all' || value.kind === 'any') {
    if (depth > 2 || !value.children.length || value.children.length > 16) fail('condition depth or children');
    value.children.forEach(child => condition(child, depth + 1, budget));
  } else if (++budget.leaves > 16 || value.children.length || !['ability_effect','effect','hot','dot','casting'].includes(value.kind as string)
    || !['caster','target','recipient'].includes(value.subject as string) || !['self','allied','any'].includes(value.source as string))
    fail('condition predicate');
}
const definitionNames = ['id','career','version','shape','school','assignmentId','targetKind','timingMode'];
const definitionNumbers = ['preparationScale','range','radius','projectileSpeed','cooldown','gcd','mana','build','cost','minimumResource',
  'resourceMax','resourceInitial','releaseFraction','castSeconds','channelSeconds','tickInterval'];
const definitionBooleans = ['enemyTarget','spendAll','blockedBySilence','legacyTargeting','authoredTiming','cancelOnMovement'];
function appliedDefinition(row: unknown): { row: NativeAppliedDefinition; effects: Map<string, Record<string, unknown>> } {
  if (!object(row) || !keys(row,['id','career','version','payload','sha256']) || !name(row.id) || !name(row.career)
    || !name(row.version) || typeof row.payload !== 'string' || nativeUtf8ByteLength(row.payload) > 65_536
    || !hash(row.sha256) || nativeDefinitionSha256(row.payload) !== row.sha256) fail('applied definition hash or identity');
  let value: unknown;
  try { value = JSON.parse(row.payload); } catch { fail('pure applied definition JSON'); }
  if (!object(value) || !keys(value,['schemaVersion','units',...definitionNames,...definitionNumbers,...definitionBooleans,
      'name','summary','unavailableReason','resourceLabel','slot','unlockLevel','maxTargets','presentations','effects','conditions'])
    || value.schemaVersion !== 1 || value.units !== 'native_cm_seconds'
    || value.id !== row.id || value.career !== row.career || value.version !== row.version
    || definitionNames.some(k => !name(value[k], true)) || definitionNumbers.some(k => !numeric(value[k]))
    || definitionBooleans.some(k => typeof value[k] !== 'boolean')
    || ['name','resourceLabel'].some(k => !prose(value[k], 512))
    || ['summary','unavailableReason'].some(k => !prose(value[k], 4096))
    || !Number.isSafeInteger(value.slot) || (value.slot as number) < 0 || (value.slot as number) > 1024
    || !Number.isSafeInteger(value.unlockLevel) || (value.unlockLevel as number) < 1 || (value.unlockLevel as number) > 1000
    || !Number.isSafeInteger(value.maxTargets) || (value.maxTargets as number) < 1 || (value.maxTargets as number) > 128
    || !object(value.presentations) || Object.keys(value.presentations).length > 128
    || Object.entries(value.presentations).some(([profile,motion]) => !name(profile) || !name(motion))
    || !Array.isArray(value.effects) || value.effects.length > 128 || !Array.isArray(value.conditions) || value.conditions.length > 16)
    fail('full pure applied definition fields');
  if ((value.preparationScale as number) < .1 || (value.preparationScale as number) > 1 || (value.resourceMax as number) <= 0
    || (value.resourceInitial as number) > (value.resourceMax as number) || (value.cooldown as number) > 3600 || (value.gcd as number) > 60
    || (value.releaseFraction as number) < .05 || (value.releaseFraction as number) > .95 || (value.tickInterval as number) < .1
    || !['','instant','cast','channel'].includes(value.timingMode as string)) fail('applied timing or resource bounds');
  const effects = new Map<string, Record<string, unknown>>();
  const add = (v: Record<string, unknown>) => { if (effects.has(v.id as string)) fail('duplicate applied effect'); effects.set(v.id as string,v); };
  value.effects.forEach(v => add(effect(v,false,value.legacyTargeting as boolean)));
  const ruleIds = new Set();
  for (const rule of value.conditions) {
    if (!object(rule) || !keys(rule,['id','event','name','condition','actions']) || !name(rule.id) || ruleIds.has(rule.id)
      || !['cast_start','application','tick'].includes(rule.event as string) || !prose(rule.name,512)
      || !Array.isArray(rule.actions) || !rule.actions.length || rule.actions.length > 32) fail('pure conditional rule');
    ruleIds.add(rule.id); condition(rule.condition);
    if (!object(rule.condition) || !['all','any'].includes(rule.condition.kind as string)) fail('root conditional group');
    const modifiers = new Set();
    for (const action of rule.actions) {
      if (!object(action) || !keys(action,['kind','effectId','value','effect']) || !['add_effect','flat','percent'].includes(action.kind as string)
        || !name(action.effectId,true) || !numeric(action.value,-1_000_000)) fail('pure conditional action');
      const applied = effect(action.effect, action.kind !== 'add_effect',value.legacyTargeting as boolean);
      if (action.kind === 'add_effect') {
        if (!['damage','heal','status','player_status'].includes(applied.kind as string)
          || rule.event === 'tick' && ((applied.periodicDuration as number) > 0 || ['burn','bleed'].includes(applied.statusKind as string)))
          fail('recursive conditional bonus');
        add(applied);
      } else {
        const base = value.effects.find(v => object(v) && v.id === action.effectId) as Record<string,unknown> | undefined;
        const identity=action.kind+':'+action.effectId;
        if (!base || !['damage','heal'].includes(base.kind as string) || modifiers.has(identity)
          || action.kind === 'percent' && ((action.value as number) < -1 || (action.value as number) > 100)
          || rule.event === 'tick' && (base.periodicDuration as number) <= 0 && value.timingMode !== 'channel') fail('conditional amount modifier');
        modifiers.add(identity);
      }
    }
    if (rule.event === 'tick' && value.timingMode !== 'channel' && !value.effects.some(v => object(v) && (v.periodicDuration as number) > 0))
      fail('conditional tick without periodic definition');
  }
  return { row: row as unknown as NativeAppliedDefinition, effects };
}

/** Old documents retain recorded relative timing; partial/unknown new versions fail closed. */
export function validateNativeRuntime(value: Record<string, unknown>): void {
  if (value.version === undefined || value.version === 1) {
    if (value.capturedAtUnixMs !== undefined || value.combat !== undefined
      || object(value.abilities) && (value.abilities.globalCooldownExpiresAtUnixMs !== undefined
        || Array.isArray(value.abilities.cooldowns) && value.abilities.cooldowns.some(c => object(c) && c.expiresAtUnixMs !== undefined)))
      fail('partial v2 cannot fall back to historical timing');
    return;
  }
  if (value.version !== 2 || !epoch(value.capturedAtUnixMs) || value.capturedAtUnixMs === 0
    || !keys(value,['version','capturedAtUnixMs','health','mana','dead','rewards','questKills','abilities','combat'])
    || !numeric(value.health,0,3.4028234663852886e38) || !numeric(value.mana,0,3.4028234663852886e38)
    || typeof value.dead !== 'boolean' || !object(value.abilities) || !object(value.combat)
    || ['rewards','questKills'].some(key => !Array.isArray(value[key]) || (value[key] as unknown[]).length > 65_536
      || (value[key] as unknown[]).some(v => !receipt(v)) || new Set((value[key] as string[]).map(v => v.replaceAll('-','').toLowerCase())).size !== (value[key] as unknown[]).length))
    fail('version, capture epoch or state');
  const captured = value.capturedAtUnixMs as number, abilities = value.abilities, combat = value.combat;
  const deadline = (remaining: unknown, expires: unknown, maximum: number) => numeric(remaining,0,maximum) && epoch(expires)
    && Math.abs(Math.max(0,(expires as number)-captured)/1000-(remaining as number)) <= .01;
  if (!keys(abilities,['resource','globalCooldown','globalCooldownExpiresAtUnixMs','cooldowns']) || !numeric(abilities.resource)
    || !deadline(abilities.globalCooldown,abilities.globalCooldownExpiresAtUnixMs,60) || !Array.isArray(abilities.cooldowns)
    || abilities.cooldowns.length > 256) fail('ability epochs or bounded cooldowns');
  const cooldownIds = new Set();
  for (const row of abilities.cooldowns) {
    if (!object(row) || !keys(row,['id','remaining','expiresAtUnixMs']) || !name(row.id) || cooldownIds.has(row.id)
      || !deadline(row.remaining,row.expiresAtUnixMs,3600)) fail('cooldown identity or epoch');
    cooldownIds.add(row.id);
  }
  if (!keys(combat,['version','definitions','statuses','ascEffects']) || combat.version !== 1
    || !Array.isArray(combat.definitions) || combat.definitions.length > 128
    || !Array.isArray(combat.statuses) || combat.statuses.length > 128
    || !Array.isArray(combat.ascEffects) || combat.ascEffects.length > 16) fail('bounded combat codec');
  const definitions = new Map<string, ReturnType<typeof appliedDefinition>>(), appliedIds = new Set();
  for (const value of combat.definitions) {
    const parsed = appliedDefinition(value), row = parsed.row, identity = row.career + ':' + row.id + ':' + row.version;
    if (definitions.has(row.sha256) || appliedIds.has(identity)) fail('duplicate applied definition');
    definitions.set(row.sha256,parsed); appliedIds.add(identity);
  }
  const statusIds = new Set();
  for (const status of combat.statuses) {
    if (!object(status) || !keys(status,['id','kind','group','modifier','label','magnitude','shield','tickDamage','tickHealing','interval',
        'expiresAtUnixMs','nextTickAtUnixMs','sourceKey','sourceRealm','abilityId','effectId','category','appliedVersion','definitionSha256'],['periodic'])
      || !text(status.id,1024) || statusIds.has(status.id)
      || !['burn','bleed','slow','root','silence','stagger','mark','debuff','shield','guard','empower','haste','dot','hot'].includes(status.kind as string)
      || !name(status.group,true) || !name(status.modifier,true) || !prose(status.label,512)
      || !numeric(status.magnitude,0,1) || ['shield','tickDamage','tickHealing'].some(k => !numeric(status[k],0,3.4028234663852886e38))
      || !numeric(status.interval,.1,60) || !epoch(status.expiresAtUnixMs) || !epoch(status.nextTickAtUnixMs)
      || (status.expiresAtUnixMs as number)-captured > 60_001
      || !nativeCombatantKey(status.sourceKey) || !['','aegis','riftbound'].includes(status.sourceRealm as string)
      || !name(status.abilityId) || !name(status.effectId) || !['status','shield','dot','hot'].includes(status.category as string)
      || !name(status.appliedVersion) || !hash(status.definitionSha256)) fail('status fields, source or immutable identity');
    const definition = definitions.get(status.definitionSha256 as string);
    if (!definition || definition.row.id !== status.abilityId || definition.row.version !== status.appliedVersion
      || !definition.effects.has(status.effectId as string)) fail('status has no exact applied definition/effect');
    if (status.periodic !== undefined) {
      const p = status.periodic;
      if (!object(p) || !keys(p,['base','strength','level','bonus','targetKey']) || !numeric(p.base,0,3.4028234663852886e38)
        || !numeric(p.strength) || !Number.isSafeInteger(p.level) || (p.level as number) < 1 || (p.level as number) > 1000
        || typeof p.bonus !== 'boolean' || !nativeCombatantKey(p.targetKey,true)) fail('periodic immutable execution');
    }
    statusIds.add(status.id);
  }
  const ascIds = new Set();
  for (const entry of combat.ascEffects) {
    if (!object(entry) || !keys(entry,['id','expiresAtUnixMs','level','stacks']) || entry.id !== 'DevelopmentStrikeCooldown'
      || ascIds.has(entry.id) || !epoch(entry.expiresAtUnixMs) || !numeric(entry.level,.00001,1000) || entry.stacks !== 1)
      fail('unsupported opaque ASC effect or stacks');
    if ((entry.expiresAtUnixMs as number)-captured > 3_600_001) fail('supported ASC effect exceeds native duration');
    ascIds.add(entry.id);
  }
}
