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

export type AbilityIconSymbol =
  | 'arrow'
  | 'axe'
  | 'banner'
  | 'blade'
  | 'bolt'
  | 'bomb'
  | 'chain'
  | 'chalice'
  | 'claw'
  | 'cross'
  | 'crown'
  | 'dagger'
  | 'eye'
  | 'fang'
  | 'flame'
  | 'hammer'
  | 'leaf'
  | 'paw'
  | 'rune'
  | 'shield'
  | 'skull'
  | 'spear'
  | 'star'
  | 'turret'
  | 'vortex';

export type AbilityIconFrame = 'round' | 'diamond' | 'shield' | 'rune' | 'burst';
export type AbilityIconAccent = 'none' | 'chevron' | 'cross' | 'dot' | 'spark' | 'tear';
export type AbilityCastVfxKind = 'flare' | 'chant' | 'guard' | 'ritual' | 'surge' | 'venom';
export type AbilityProjectileVfxKind =
  | 'none'
  | 'arrow'
  | 'bolt'
  | 'bomb'
  | 'chain'
  | 'ember'
  | 'hammer'
  | 'knife'
  | 'rune'
  | 'shard'
  | 'spirit'
  | 'venom';
export type AbilityImpactVfxKind =
  | 'burst'
  | 'cross'
  | 'flare'
  | 'quake'
  | 'rune'
  | 'shatter'
  | 'splash'
  | 'venom';
export type AbilityTrailVfxKind = 'none' | 'embers' | 'runes' | 'smoke' | 'sparks' | 'spiral' | 'venom';
export type AbilityMotionKind = 'cleave' | 'jab' | 'leap' | 'ritual' | 'shot' | 'slam' | 'ward' | 'weave';
export type AbilityClassFlair =
  | 'neutral'
  | 'ember'
  | 'inquisition'
  | 'sun_banner'
  | 'prelate_hymn'
  | 'stone_oath'
  | 'doom_axes'
  | 'glyph_script'
  | 'siege_engine'
  | 'blade_kata'
  | 'pride_beast'
  | 'aether_stars'
  | 'veil_arrows'
  | 'dread_aura'
  | 'mutation'
  | 'void_artillery'
  | 'ruin_rite'
  | 'warbrute_plan'
  | 'fang_pack'
  | 'bog_hex'
  | 'cleaver_frenzy'
  | 'blood_dance'
  | 'dread_guard'
  | 'dusk_weave'
  | 'crimson_siphon';

export interface AbilityColorProfile {
  primary: string;
  secondary: string;
  accent: string;
  shadow: string;
  glow: string;
}

export interface AbilityIconProfile {
  symbol: AbilityIconSymbol;
  frame: AbilityIconFrame;
  accent: AbilityIconAccent;
  seed: number;
}

export interface AbilityVfxProfile {
  cast: AbilityCastVfxKind;
  projectile: AbilityProjectileVfxKind;
  impact: AbilityImpactVfxKind;
  trail: AbilityTrailVfxKind;
  motion: AbilityMotionKind;
  flair: AbilityClassFlair;
  colors: AbilityColorProfile;
  seed: number;
}

export interface AbilityVisualProfile {
  school: AbilitySchool;
  icon: AbilityIconProfile;
  vfx: AbilityVfxProfile;
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
  visual: AbilityVisualProfile;
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
