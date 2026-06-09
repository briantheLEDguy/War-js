export type AbilitySchool =
  | 'physical'
  | 'fire'
  | 'holy'
  | 'shadow'
  | 'nature'
  | 'arcane'
  | 'chaos'
  | 'rune'
  | 'engineer'
  | 'poison';

export type AbilityFamily =
  | 'risk_caster'
  | 'verdict_assassin'
  | 'commander_tank'
  | 'melee_healer'
  | 'reactive_oath_tank'
  | 'berserker'
  | 'rune_mark_support'
  | 'deployable_artillery'
  | 'stance_chain_tank'
  | 'bonded_beast_hunter'
  | 'balance_caster'
  | 'mobile_skirmisher'
  | 'dark_gift_tank'
  | 'mutation_disruptor'
  | 'occult_artillery'
  | 'ritual_support'
  | 'plan_bruiser'
  | 'pet_skirmisher'
  | 'hybrid_hexer'
  | 'frenzy_bruiser'
  | 'blood_assassin'
  | 'hatred_tank'
  | 'dark_power_caster'
  | 'siphon_healer';

export type AbilityShape =
  | 'melee'
  | 'projectile'
  | 'beam'
  | 'cone'
  | 'area'
  | 'self'
  | 'dash'
  | 'deployable'
  | 'pet';

export type AbilityTargetKind = 'enemy' | 'self';

export type AbilityEffectKind = 'damage' | 'heal' | 'status';

export interface AbilityAmount {
  min: number;
  max: number;
  statScale?: number;
  resourceScale?: number;
  levelScale?: number;
}

export type CombatStatusKind = 'burn' | 'bleed' | 'slow' | 'root' | 'silence' | 'stagger' | 'mark' | 'debuff';

export interface AbilityStatusPayload {
  id: string;
  label: string;
  kind: CombatStatusKind;
  durationSec: number;
  magnitude?: number;
}

export interface AbilityEffect {
  kind: AbilityEffectKind;
  school?: AbilitySchool;
  amount?: AbilityAmount;
  status?: AbilityStatusPayload;
}

export interface AbilityResourceDelta {
  manaCost?: number;
  careerBuild?: number;
  careerCost?: number;
  spendAllCareer?: boolean;
  minCareer?: number;
}

export interface AbilityAnimationWindow {
  name: 'release' | 'active' | 'impact';
  start: number;
  end: number;
}

export interface AbilityAnimation {
  actionId: string;
  clip: string;
  durationSec: number;
  upperBodyOnly?: boolean;
  notifyWindows: AbilityAnimationWindow[];
}

export interface AbilityTargeting {
  target: AbilityTargetKind;
  shape: AbilityShape;
  range: number;
  radius?: number;
  projectileSpeed?: number;
  tracePolicy: 'client_preview' | 'server_auth';
}

export interface AbilityCancelRules {
  blockedBy: string[];
  appliesOwnerTags: string[];
}

export interface AbilityDefinition {
  id: string;
  career: string;
  classFamily: AbilityFamily;
  slot: number;
  key: string;
  icon: string;
  name: string;
  summary: string;
  cooldownSec: number;
  gcdSec: number;
  tags: string[];
  resource: AbilityResourceDelta;
  animation: AbilityAnimation;
  targeting: AbilityTargeting;
  effects: AbilityEffect[];
  vfxSockets: string[];
  cancelRules: AbilityCancelRules;
}

export interface CareerResourceDefinition {
  key: string;
  label: string;
  max: number;
  initial: number;
  highRisk?: boolean;
}

export interface CareerAbilityKit {
  career: string;
  classFamily: AbilityFamily;
  resource: CareerResourceDefinition;
  abilities: AbilityDefinition[];
}
