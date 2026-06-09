import type {
  AbilityDefinition,
  AbilityAnimation,
  AbilityEffect,
  AbilityFamily,
  AbilitySchool,
  AbilityShape,
  AbilityStatusPayload,
  AbilityTargetKind,
  CareerAbilityKit,
  CareerResourceDefinition,
} from './types';
import { DEFAULT_CLASS_NAME, normalizeClassName } from '../../data/careers';

export const HOTBAR_SLOT_COUNT = 10;
export const HOTBAR_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'] as const;

export interface AbilityResourceState {
  key: string;
  label: string;
  current: number;
  max: number;
}

type AbilityKind =
  | 'builder'
  | 'strike'
  | 'spender'
  | 'control'
  | 'mobility'
  | 'defense'
  | 'heal'
  | 'buff'
  | 'area'
  | 'summon'
  | 'stance'
  | 'ultimate';

interface AbilitySeed {
  name: string;
  summary: string;
  kind: AbilityKind;
  school: AbilitySchool;
  shape: AbilityShape;
  target?: AbilityTargetKind;
  range?: number;
  radius?: number;
  cooldownSec?: number;
  manaCost?: number;
  careerBuild?: number;
  careerCost?: number;
  spendAllCareer?: boolean;
  minCareer?: number;
  status?: AbilityStatusPayload;
  effects?: AbilityEffect[];
}

interface KitSeed {
  career: string;
  classFamily: AbilityFamily;
  resource: CareerResourceDefinition;
  abilities: AbilitySeed[];
}

export const CAREER_ABILITY_KITS: Record<string, CareerAbilityKit> = Object.fromEntries(
  [
    kit('Ember Arcanist', 'risk_caster', resource('heat', 'Heat', 100, 0, true), [
      a('Spark Lash', 'Quick fire bolt that builds Heat.', 'builder', 'fire', 'projectile'),
      a('Cinder Lance', 'Heavier single-target fire nuke.', 'strike', 'fire', 'projectile', { cooldownSec: 5 }),
      a('Kindle Hex', 'Burning mark that primes the next hit.', 'control', 'fire', 'projectile', { status: burn('Kindle Hex', 5) }),
      a('Soot Veil', 'Smoke cone that hinders nearby enemies.', 'control', 'fire', 'cone', { range: 8, status: slow('Soot Veil', 3, 0.35) }),
      a('Flashstep', 'Short evasive blink that scorches the arrival line.', 'mobility', 'fire', 'dash', { target: 'self', cooldownSec: 10 }),
      a('Pyre Circle', 'Ground fire ring for zone denial.', 'area', 'fire', 'area', { range: 22, radius: 4, status: burn('Pyre Circle', 4) }),
      a('White Cautery', 'Risky cauterize heal on self.', 'heal', 'holy', 'self', { manaCost: 18 }),
      a('Furnace Heart', 'Self-buff that surges Heat generation.', 'buff', 'fire', 'self', { cooldownSec: 18 }),
      a('Ashen Cataclysm', 'Channeled beam that spends Heat for burst.', 'spender', 'fire', 'beam', { range: 26, careerCost: 35 }),
      a('Phoenix Collapse', 'Ultimate meteor strike that empties Heat.', 'ultimate', 'fire', 'area', { range: 28, radius: 6, spendAllCareer: true }),
    ]),
    kit('Hex Inquisitor', 'verdict_assassin', resource('verdicts', 'Verdicts', 5, 0), [
      a('Brand Shot', 'Pistol shot that applies a Verdict.', 'builder', 'physical', 'projectile', { careerBuild: 1 }),
      a('Interrogate', 'Rapier stab that weakens armor.', 'builder', 'physical', 'melee', { careerBuild: 1, status: mark('Interrogated', 5) }),
      a('Silver Snare', 'Thrown chain root for isolating prey.', 'control', 'physical', 'projectile', { status: root('Silver Snare', 2.2) }),
      a('Relic Oil', 'Weapon anoint for marked targets.', 'buff', 'holy', 'self'),
      a('Purging Slash', 'Fast melee combo that spends Verdicts.', 'spender', 'physical', 'melee', { careerCost: 2 }),
      a('Black-Powder Step', 'Evasive backstep with a return shot.', 'mobility', 'physical', 'projectile', { range: 14 }),
      a('Stake the Guilty', 'Execution strike against wounded enemies.', 'spender', 'holy', 'melee', { careerCost: 3, cooldownSec: 9 }),
      a('Ash Ward', 'Self-cleanse and brief anti-magic ward.', 'defense', 'holy', 'self'),
      a('Torch of Scorn', 'Cone burn that panics weak enemies.', 'area', 'fire', 'cone', { range: 8, status: burn('Torch of Scorn', 4) }),
      a('Final Sentence', 'Ultimate execution shot at full Verdict.', 'ultimate', 'physical', 'projectile', { spendAllCareer: true, minCareer: 5, range: 24 }),
    ]),
    kit('Sunfire Templar', 'commander_tank', resource('valor', 'Valor', 100, 0), [
      a('Solar Edict', 'Aura stance that improves allied offense.', 'stance', 'holy', 'self', { cooldownSec: 1 }),
      a('Bastion Edict', 'Aura stance that improves allied defense.', 'stance', 'holy', 'self', { cooldownSec: 1 }),
      a('Pursuit Edict', 'Aura stance for speed and action tempo.', 'stance', 'holy', 'self', { cooldownSec: 1 }),
      a('Sunbrand Strike', 'Melee hit that marks a target for follow-up.', 'builder', 'holy', 'melee', { status: mark('Sunbranded', 6) }),
      a('Shield of Noon', 'Frontal block stance against pressure.', 'defense', 'holy', 'self'),
      a('Rallying Rebuke', 'Taunt that lowers enemy damage output.', 'control', 'holy', 'melee', { status: debuff('Rebuked', 5) }),
      a('Banner Rush', 'Shield-led engage and charge.', 'mobility', 'physical', 'dash', { range: 12 }),
      a('Radiant Counter', 'Riposte that briefly blinds.', 'strike', 'holy', 'melee', { status: slow('Blinded', 2, 0.25) }),
      a('Heavenrend Sweep', 'Wide cleave that spends Valor.', 'spender', 'holy', 'cone', { careerCost: 35, range: 6 }),
      a('Daybreak Standard', 'Ultimate banner zone with radiant pulses.', 'ultimate', 'holy', 'area', { target: 'self', radius: 7, spendAllCareer: true }),
    ]),
    kit('Battle Prelate', 'melee_healer', resource('zeal', 'Zeal', 100, 20), [
      a('Litany of Strikes', 'Hammer combo that builds Zeal.', 'builder', 'holy', 'melee'),
      a('Sanctified Blow', 'Empowered hit that splashes healing.', 'strike', 'holy', 'melee', { effects: mixedDamageHeal('holy', 15, 28, 12, 22) }),
      a("Martyr's Ward", 'Targeted ward for self or ally.', 'defense', 'holy', 'self', { manaCost: 14 }),
      a('Penance Step', 'Short gap-close with a slowing strike.', 'mobility', 'holy', 'dash', { status: slow('Penance', 2.5, 0.4) }),
      a('Hymn of Resolve', 'Chant aura that rewards allies for striking.', 'buff', 'holy', 'self'),
      a('Reliquary Smash', 'Overhead area stagger.', 'area', 'holy', 'area', { target: 'self', radius: 3.5, status: stagger('Reliquary Smash', 1.2) }),
      a('Judgment of Ash', 'Line-based holy shock at mid range.', 'strike', 'holy', 'beam', { range: 16 }),
      a('Redemption Surge', 'Spend Zeal for a burst self heal.', 'heal', 'holy', 'self', { careerCost: 35, manaCost: 12 }),
      a('Icon of Wrath', 'Placed relic that grants lifesteal pressure.', 'summon', 'holy', 'deployable', { target: 'self', radius: 5 }),
      a('Last Homily', 'Ultimate sermon that converts damage into healing.', 'ultimate', 'holy', 'area', { target: 'self', radius: 7, spendAllCareer: true, effects: mixedDamageHeal('holy', 28, 44, 28, 46) }),
    ]),
    kit('Stoneguard', 'reactive_oath_tank', resource('grudge', 'Grudge', 100, 20), [
      a('Oath Bind', 'Designate an oathmate and prepare protection.', 'stance', 'rune', 'self'),
      a('Grudge Axes', 'Ranged axe toss taunt.', 'builder', 'physical', 'projectile', { status: mark('Grudged', 6) }),
      a('Clanwall', 'Shield slam with a short stagger.', 'control', 'physical', 'melee', { status: stagger('Clanwall', 1) }),
      a('Bitter Reprisal', 'Punishing retaliatory strike.', 'spender', 'physical', 'melee', { careerCost: 30 }),
      a('Runebound Mail', 'Heavy armor buff.', 'defense', 'rune', 'self'),
      a('Stone March', 'Slow unstoppable advance.', 'buff', 'rune', 'self'),
      a('Holdfast', 'Planted defensive stance.', 'defense', 'rune', 'self'),
      a('Vengeful Hook', 'Chain-pull punishment.', 'control', 'physical', 'projectile', { status: root('Vengeful Hook', 1.4) }),
      a('Hearthguard Vow', 'Cleanse and shield transfer.', 'heal', 'rune', 'self', { careerCost: 25 }),
      a('Book of Wrongs', 'Ultimate taunt field with shockwaves.', 'ultimate', 'rune', 'area', { target: 'self', radius: 6, spendAllCareer: true }),
    ]),
    kit('Doomseeker', 'berserker', resource('rage', 'Rage', 100, 10, true), [
      a('Death Oath', 'Enter berserk state.', 'stance', 'physical', 'self'),
      a('Twin Hew', 'Dual-axe builder.', 'builder', 'physical', 'melee'),
      a('Skullsplit Leap', 'Leap in and inflict bleeding.', 'mobility', 'physical', 'dash', { status: bleed('Skullsplit', 5) }),
      a('Exhausting Swing', 'Brutal strike that dumps Rage.', 'spender', 'physical', 'melee', { spendAllCareer: true }),
      a('Bloodhowl', 'Self-buff for speed and attack tempo.', 'buff', 'physical', 'self'),
      a('Grim Pursuit', 'Shrug off slows and chase harder.', 'defense', 'physical', 'self'),
      a('Reckless Arc', 'Spin attack that scales with Rage.', 'area', 'physical', 'area', { target: 'self', radius: 3.5, careerCost: 20 }),
      a('No Respite', 'Finisher against bleeding targets.', 'spender', 'physical', 'melee', { careerCost: 30 }),
      a('Doom Roar', 'Anti-peel shout.', 'control', 'physical', 'cone', { range: 7, status: slow('Doom Roar', 2.5, 0.3) }),
      a('Final Reckoning', 'Ultimate frenzy with a vulnerability crash.', 'ultimate', 'physical', 'area', { target: 'self', radius: 5, spendAllCareer: true }),
    ]),
    kit('Glyphbinder', 'rune_mark_support', resource('runic_focus', 'Runic Focus', 100, 30), [
      a('Rune of Mending', 'Direct heal that leaves a mending rune.', 'heal', 'rune', 'self'),
      a('Rune of Warding', 'Shield rune on self.', 'defense', 'rune', 'self'),
      a('Rune of Cleaving', 'Enemy mark that lowers armor.', 'builder', 'rune', 'projectile', { status: debuff('Cleaving Rune', 5) }),
      a('Anchor Sigil', 'Rune circle that roots entrants.', 'control', 'rune', 'area', { range: 18, radius: 3, status: root('Anchor Sigil', 1.8) }),
      a('Oath Script', 'Buff rune granting damage or resistance.', 'buff', 'rune', 'self'),
      a('Master Rune of Hearth', 'Persistent healing rune stone.', 'summon', 'rune', 'deployable', { target: 'self', effects: [{ kind: 'heal', school: 'rune', amount: { min: 22, max: 38, statScale: 0.4 } }] }),
      a('Master Rune of Ruin', 'Delayed explosive rune zone.', 'area', 'rune', 'area', { range: 20, radius: 4 }),
      a('Stoneword', 'Knockback line of erupting sigils.', 'control', 'rune', 'beam', { range: 14, status: stagger('Stoneword', 1) }),
      a("Ancestor's Favor", 'Refresh and cleanse through ancestral rune work.', 'heal', 'rune', 'self', { careerCost: 25 }),
      a('Ancestor Lexicon', 'Ultimate that pulses all active runes again.', 'ultimate', 'rune', 'area', { target: 'self', radius: 7, spendAllCareer: true, effects: mixedDamageHeal('rune', 24, 38, 32, 48) }),
    ]),
    kit('Siegewright', 'deployable_artillery', resource('pressure', 'Pressure', 100, 0), [
      a('Deploy Gunlet', 'Place a turret mode.', 'summon', 'engineer', 'deployable', { target: 'self' }),
      a('Crank Charge', 'Overclock current deployable.', 'builder', 'engineer', 'self'),
      a('Buckshot Salvo', 'Close cone blast for self-defense.', 'control', 'engineer', 'cone', { range: 7, status: slow('Buckshot', 2, 0.3) }),
      a('Fragment Bomb', 'Thrown area explosive.', 'area', 'engineer', 'area', { range: 18, radius: 4 }),
      a('Harpoon Line', 'Pull or tether tool.', 'control', 'engineer', 'projectile', { range: 18, status: root('Harpoon Line', 1.4) }),
      a('Landmine Satchel', 'Trap with knock-up pressure.', 'control', 'engineer', 'area', { target: 'self', radius: 4, status: stagger('Landmine', 1) }),
      a('Grapnel Traverse', 'Zip reposition.', 'mobility', 'engineer', 'dash', { target: 'self' }),
      a('Armor Piercer', 'Charged rifle shot through lines.', 'spender', 'engineer', 'projectile', { range: 28, careerCost: 25 }),
      a('Ironstorm Battery', 'Turret-assisted barrage.', 'area', 'engineer', 'area', { range: 24, radius: 5, careerCost: 30 }),
      a('Fortified Redoubt', 'Ultimate upgraded emplacement and cover.', 'ultimate', 'engineer', 'deployable', { target: 'self', radius: 7, spendAllCareer: true }),
    ]),
    kit('Blade Savant', 'stance_chain_tank', resource('balance', 'Balance', 3, 0), [
      a('Opening Form', 'Entry strike that starts the stance chain.', 'builder', 'arcane', 'melee', { careerBuild: 1 }),
      a('Rising Form', 'Advancing cut that improves the chain.', 'builder', 'arcane', 'dash', { careerBuild: 1 }),
      a('Perfect Form', 'Finisher slash after proper sequencing.', 'spender', 'arcane', 'melee', { careerCost: 2 }),
      a('Warding Arc', 'Parry cone versus frontal attacks.', 'defense', 'arcane', 'cone', { range: 5 }),
      a('Moonstep', 'Elegant sidestep that improves the next form.', 'mobility', 'arcane', 'self', { careerBuild: 1 }),
      a('Enchanted Edge', 'Magic-imbued blade stance.', 'buff', 'arcane', 'self'),
      a('Spiral Guard', 'Circular peel attack.', 'area', 'arcane', 'area', { target: 'self', radius: 3.5 }),
      a('Mindward', 'Party anti-magic buffer.', 'defense', 'arcane', 'self'),
      a('Aether Crossing', 'Dash-through slash to reposition.', 'mobility', 'arcane', 'dash', { range: 12 }),
      a('Sevenfold Kata', 'Ultimate rapid Perfect Form recital.', 'ultimate', 'arcane', 'area', { target: 'self', radius: 5, spendAllCareer: true }),
    ]),
    kit('Pride Warden', 'bonded_beast_hunter', resource('pack_fury', 'Pack Fury', 100, 20), [
      a("Hunter's Mark", 'Identify prey for companion pressure.', 'builder', 'physical', 'projectile', { status: mark("Hunter's Mark", 7) }),
      a('Pounce', 'Self-and-companion engage.', 'mobility', 'physical', 'dash', { range: 14 }),
      a('Pack Rend', 'Synchronized bleed combo.', 'strike', 'physical', 'melee', { status: bleed('Pack Rend', 5) }),
      a('Guardian Roar', 'Companion peel and taunt.', 'control', 'physical', 'cone', { range: 7, status: slow('Guardian Roar', 2.5, 0.3) }),
      a("Flanker's Path", 'Command the beast to circle behind prey.', 'buff', 'physical', 'self'),
      a('Trophy Axe', 'High-commitment cleave.', 'spender', 'physical', 'cone', { careerCost: 30, range: 6 }),
      a('Wild Bond', 'Heal and speed boost for hunter and beast.', 'heal', 'nature', 'self'),
      a('Snare Net', 'Ranged root setup.', 'control', 'physical', 'projectile', { range: 16, status: root('Snare Net', 2) }),
      a("King's Leap", 'Companion knockdown into your finisher.', 'spender', 'physical', 'dash', { careerCost: 35, status: stagger("King's Leap", 1.2) }),
      a('Pride Unleashed', 'Ultimate empowered companion hunt phase.', 'ultimate', 'nature', 'pet', { spendAllCareer: true, range: 18 }),
    ]),
    kit('Aether Sage', 'balance_caster', resource('high_magic', 'High Magic', 100, 25), [
      a('Starshard', 'Damage bolt that builds healing echo.', 'builder', 'arcane', 'projectile'),
      a('Verdant Current', 'Heal that builds arcane echo.', 'heal', 'nature', 'self', { careerBuild: 10 }),
      a('Energy Weave', 'Convert stored echo into efficiency.', 'buff', 'arcane', 'self'),
      a('Moonwell', 'Field that heals allies and harms foes.', 'area', 'nature', 'area', { target: 'self', radius: 5, effects: mixedDamageHeal('nature', 16, 28, 18, 32) }),
      a('Sunpierce', 'Beam damage that echoes healing.', 'strike', 'arcane', 'beam', { range: 24, effects: mixedDamageHeal('arcane', 18, 34, 10, 18) }),
      a('Merciful Veil', 'Shield and cleanse spell.', 'defense', 'nature', 'self'),
      a('Comet Snare', 'Delayed root burst.', 'control', 'arcane', 'area', { range: 20, radius: 3, status: root('Comet Snare', 1.8) }),
      a('Tranquil Drift', 'Blink with a trailing ward.', 'mobility', 'nature', 'self'),
      a('High Concord', 'Next spell double-casts opposite polarity.', 'buff', 'arcane', 'self', { careerCost: 25 }),
      a('Celestial Equinox', 'Ultimate equilibrium echo state.', 'ultimate', 'arcane', 'area', { target: 'self', radius: 7, spendAllCareer: true, effects: mixedDamageHeal('arcane', 24, 42, 30, 48) }),
    ]),
    kit('Veil Ranger', 'mobile_skirmisher', resource('focus', 'Focus', 100, 0), [
      a('Longdraw', 'Stand-and-fire precision shot.', 'builder', 'physical', 'projectile', { range: 28 }),
      a('Running Shot', 'Mobile bow attack while moving.', 'strike', 'physical', 'projectile', { range: 22, cooldownSec: 3 }),
      a('Shadow Rush', 'Sudden close-range dash slash.', 'mobility', 'physical', 'dash', { range: 12 }),
      a('Barbed Volley', 'Bleed-inflicting arrow fan.', 'area', 'physical', 'cone', { range: 14, status: bleed('Barbed Volley', 5) }),
      a('Mist Walk', 'Camouflage reposition tool.', 'defense', 'shadow', 'self'),
      a('Eye Pierce', 'Interrupting silence shot.', 'control', 'physical', 'projectile', { range: 24, status: silence('Eye Pierce', 2) }),
      a('Waylay Trap', 'Ground snare trap.', 'control', 'physical', 'area', { target: 'self', radius: 4, status: root('Waylay Trap', 1.8) }),
      a('Moonshot', 'Arcing reveal arrow.', 'strike', 'arcane', 'projectile', { range: 30 }),
      a('Vengeance Mark', 'Target takes bonus pressure after stance changes.', 'builder', 'shadow', 'projectile', { status: mark('Vengeance Mark', 7) }),
      a('Eclipse Hunt', 'Ultimate aimed shot, dash, and finisher chain.', 'ultimate', 'shadow', 'projectile', { spendAllCareer: true, range: 28 }),
    ]),
    kit('Dreadsworn', 'dark_gift_tank', resource('dark_gifts', 'Dark Gifts', 100, 20), [
      a('Aura of Dread', 'Passive enemy offense reduction nearby.', 'stance', 'chaos', 'self'),
      a('Aura of Ruin', 'Nearby armor and resistance debuff field.', 'stance', 'chaos', 'self'),
      a('Aura of Dominion', 'Team control-resistance aura.', 'stance', 'chaos', 'self'),
      a('Hexbrand Cleave', 'Melee cleave that spreads curse tags.', 'builder', 'chaos', 'cone', { range: 5, status: debuff('Hexbrand', 6) }),
      a('Black Bastion', 'Heavy defensive shield stance.', 'defense', 'chaos', 'self'),
      a("Tyrant's Advance", 'Unstoppable march forward.', 'mobility', 'chaos', 'dash', { target: 'self' }),
      a('Sunder Faith', 'Anti-caster taunt and silence.', 'control', 'chaos', 'melee', { status: silence('Sunder Faith', 2) }),
      a('Warp Riposte', 'Counter hit after a block.', 'strike', 'chaos', 'melee'),
      a('Harrowing Roar', 'Fear pulse that detonates curses.', 'area', 'chaos', 'area', { target: 'self', radius: 5, status: slow('Harrowed', 2.5, 0.35) }),
      a('Crown of Ruin', 'Ultimate with all three auras active.', 'ultimate', 'chaos', 'area', { target: 'self', radius: 7, spendAllCareer: true }),
    ]),
    kit('Warped Reaver', 'mutation_disruptor', resource('mutation', 'Mutation', 100, 0), [
      a('Mutate Claw', 'Enter high-speed shredding form.', 'stance', 'chaos', 'self'),
      a('Mutate Crusher', 'Enter armor-breaking bruiser form.', 'stance', 'chaos', 'self'),
      a('Mutate Tendril', 'Enter reach-and-pull form.', 'stance', 'chaos', 'self'),
      a('Flesh Hook', 'Drag prey inward.', 'control', 'chaos', 'projectile', { range: 16, status: root('Flesh Hook', 1.4) }),
      a('Ravage Burst', 'Mutation-specific spender attack.', 'spender', 'physical', 'melee', { careerCost: 30 }),
      a('Hideous Regrowth', 'Regenerative self-heal.', 'heal', 'chaos', 'self'),
      a('Warpsprint', 'Burst chase movement.', 'mobility', 'chaos', 'dash', { target: 'self' }),
      a('Bone Splinter', 'Cone rupture that bleeds and lowers armor.', 'area', 'physical', 'cone', { range: 7, status: bleed('Bone Splinter', 5) }),
      a('Mutation Shift', 'Fast form swap that empowers the next cast.', 'buff', 'chaos', 'self'),
      a('Apotheosis of Change', 'Ultimate fused mutation state.', 'ultimate', 'chaos', 'area', { target: 'self', radius: 5, spendAllCareer: true }),
    ]),
    kit('Void Magister', 'occult_artillery', resource('warp_charge', 'Warp Charge', 100, 0), [
      a('Summon Idol', 'Deploy the current idol form.', 'summon', 'chaos', 'deployable', { target: 'self' }),
      a('Warp Bolt', 'Basic ranged nuke.', 'builder', 'chaos', 'projectile'),
      a('Entropic Field', 'Slow and damage field centered on the idol.', 'area', 'chaos', 'area', { range: 20, radius: 4, status: slow('Entropic Field', 3, 0.35) }),
      a('Rift Pull', 'Draw enemies toward the idol.', 'control', 'chaos', 'area', { range: 20, radius: 4, status: root('Rift Pull', 1.2) }),
      a('Daemonfire Orb', 'Projectile that bursts near the idol.', 'strike', 'fire', 'projectile', { range: 24, status: burn('Daemonfire', 4) }),
      a('Hover Disc', 'Strafe mobility and kiting tool.', 'mobility', 'chaos', 'self'),
      a('Unmake Armor', 'Dark debuff on a key target.', 'control', 'chaos', 'projectile', { status: debuff('Unmade Armor', 6) }),
      a('Feed the Idol', 'Overcharge summon with personal cost.', 'buff', 'chaos', 'self', { careerBuild: 18, manaCost: 12 }),
      a('Warp Storm', 'Sustained area channel from idol location.', 'area', 'chaos', 'area', { range: 22, radius: 5, careerCost: 30 }),
      a('Grand Conjunction', 'Ultimate tri-layer zone of pull, burn, and debuff.', 'ultimate', 'chaos', 'area', { range: 24, radius: 7, spendAllCareer: true, status: slow('Grand Conjunction', 3, 0.45) }),
    ]),
    kit('Ruin Oracle', 'ritual_support', resource('harbingers', 'Harbingers', 100, 30), [
      a('Mark of Vigor', 'Ally buff mark.', 'heal', 'chaos', 'self'),
      a('Harbinger of Frailty', 'Enemy damage and debuff mark.', 'builder', 'chaos', 'projectile', { status: debuff('Frailty', 6) }),
      a('Soul Drain Rite', 'Siphon from a harbinger target.', 'strike', 'chaos', 'beam', { range: 22, effects: mixedDamageHeal('chaos', 16, 28, 14, 24) }),
      a('Fetish Ward', 'Totem pulse for resistance or cleanse.', 'defense', 'chaos', 'self'),
      a('Madness Cant', 'Cone disorientation chant.', 'control', 'chaos', 'cone', { range: 8, status: slow('Madness Cant', 3, 0.35) }),
      a('Blessing of Ruin', 'Lifesaving ward.', 'heal', 'chaos', 'self', { manaCost: 16 }),
      a('Scourging Sigil', 'Cursed ground zone.', 'area', 'chaos', 'area', { range: 20, radius: 4 }),
      a('Tether of Agony', 'Pain link between combatants.', 'control', 'chaos', 'projectile', { status: mark('Tethered', 6) }),
      a('Prophecy of Ash', 'Delayed detonation on afflicted foes.', 'spender', 'fire', 'projectile', { careerCost: 30, status: burn('Prophecy of Ash', 4) }),
      a('Altar of the Raven', 'Ultimate ritual upgrading marks and harbingers.', 'ultimate', 'chaos', 'deployable', { target: 'self', radius: 7, spendAllCareer: true, effects: mixedDamageHeal('chaos', 22, 38, 30, 48) }),
    ]),
    kit('Warbrute', 'plan_bruiser', resource('plan', 'Plan', 3, 0), [
      a('Sneaky Start', 'Opener that enters Good Plan.', 'builder', 'physical', 'melee', { careerBuild: 1 }),
      a('Proper Wallop', 'Chain attack that advances the Plan.', 'builder', 'physical', 'melee', { careerBuild: 1 }),
      a('Biggest Finish', 'Finisher from the top Plan tier.', 'spender', 'physical', 'melee', { careerCost: 2 }),
      a('Shut It!', 'Shield bash silence.', 'control', 'physical', 'melee', { status: silence('Shut It!', 2) }),
      a('Get Stuck In', 'Charge into melee.', 'mobility', 'physical', 'dash', { range: 12 }),
      a("Wot's Yours Is Mine", 'Steal armor and block from target.', 'control', 'physical', 'melee', { status: debuff("Wot's Yours", 5) }),
      a('Keep Smashin', 'Sustain buff on hit.', 'buff', 'physical', 'self'),
      a('Boss Stomp', 'Area knockdown.', 'area', 'physical', 'area', { target: 'self', radius: 4, status: stagger('Boss Stomp', 1.2) }),
      a('You Watch Me!', 'Bodyguard-style protection shout.', 'defense', 'physical', 'self'),
      a("Boss's Big Idea", 'Ultimate top Plan brawl window.', 'ultimate', 'physical', 'area', { target: 'self', radius: 5, spendAllCareer: true }),
    ]),
    kit('Fang Herder', 'pet_skirmisher', resource('pet_fury', 'Pet Fury', 100, 20), [
      a('Loose Fang', 'Send companion to harry a target.', 'builder', 'physical', 'pet', { range: 18 }),
      a('Skewa Shot', 'Armor-piercing arrow.', 'strike', 'physical', 'projectile', { range: 24 }),
      a("Bouncin' Escape", 'Hop backward while firing.', 'mobility', 'physical', 'projectile', { range: 16 }),
      a('Bait Bag', 'Lure trap that erupts into bites.', 'control', 'physical', 'area', { target: 'self', radius: 4, status: slow('Bait Bag', 3, 0.35) }),
      a('Spit Fang', 'Acid-spitting pet stance.', 'stance', 'poison', 'self'),
      a('Hound Fang', 'Fast chaser pet stance.', 'stance', 'physical', 'self'),
      a('Big Chompa', 'Heavy companion leap and knockdown.', 'spender', 'physical', 'pet', { careerCost: 30, status: stagger('Big Chompa', 1.2) }),
      a('Needle Rain', 'Moving arrow volley.', 'area', 'physical', 'cone', { range: 16 }),
      a('Gobbo Prod', 'Force the pet into a frenzy.', 'buff', 'physical', 'self'),
      a('Fang Stampede', 'Ultimate multi-beast rush across a lane.', 'ultimate', 'physical', 'beam', { range: 24, spendAllCareer: true }),
    ]),
    kit('Bog Hexer', 'hybrid_hexer', resource('waaagh', 'Waaagh!', 100, 25), [
      a('Green Zap', 'Damage builder for support power.', 'builder', 'nature', 'projectile'),
      a('Patch-Up', 'Heal builder for hex power.', 'heal', 'nature', 'self', { careerBuild: 10 }),
      a('Crooked Beam', 'Lifetap beam.', 'strike', 'nature', 'beam', { range: 20, effects: mixedDamageHeal('nature', 14, 26, 12, 22) }),
      a('Bog Hop', 'Bouncing reposition.', 'mobility', 'nature', 'self'),
      a('Sticky Curse', 'Slow and anti-heal curse.', 'control', 'nature', 'projectile', { status: slow('Sticky Curse', 4, 0.4) }),
      a('Lucky Idol', 'Supportive idol field.', 'summon', 'nature', 'deployable', { target: 'self', effects: [{ kind: 'heal', school: 'nature', amount: { min: 18, max: 32, statScale: 0.3 } }] }),
      a('Brain Banga', 'Interrupt projectile.', 'control', 'nature', 'projectile', { status: silence('Brain Banga', 2) }),
      a('Foul Brew', 'Bouncing heal-or-harm concoction.', 'area', 'nature', 'area', { range: 18, radius: 4, effects: mixedDamageHeal('nature', 16, 28, 16, 28) }),
      a('Mixed Medicine', 'Next cast echoes the opposite type.', 'buff', 'nature', 'self', { careerCost: 25 }),
      a('Big Green Turnabout', 'Ultimate offensive and healing echo window.', 'ultimate', 'nature', 'area', { target: 'self', radius: 7, spendAllCareer: true, effects: mixedDamageHeal('nature', 24, 40, 28, 46) }),
    ]),
    kit('Cleaver', 'frenzy_bruiser', resource('rage', 'Rage', 100, 10, true), [
      a('Whirly Chop', 'Spinning builder attack.', 'builder', 'physical', 'area', { target: 'self', radius: 3 }),
      a("Get Over 'Ere", 'Hook pull.', 'control', 'physical', 'projectile', { range: 14, status: root("Get Over 'Ere", 1.4) }),
      a('Mad Dash', 'Reckless forward rush.', 'mobility', 'physical', 'dash', { range: 12 }),
      a('Heavy Chop', 'Big Rage-dump strike.', 'spender', 'physical', 'melee', { spendAllCareer: true }),
      a("Can't Stop Me", 'Anti-control rage button.', 'defense', 'physical', 'self'),
      a('Deep Cutz', 'Bleed cleave.', 'area', 'physical', 'cone', { range: 6, status: bleed('Deep Cutz', 5) }),
      a('Facebreaker', 'Stun uppercut hit.', 'control', 'physical', 'melee', { status: stagger('Facebreaker', 1.1) }),
      a('Keep Swingin', 'Temporary on-hit sustain.', 'buff', 'physical', 'self'),
      a('Smash Pile', 'Leap slam into clustered enemies.', 'area', 'physical', 'area', { range: 12, radius: 4 }),
      a('Red Mist', 'Ultimate cleaving frenzy.', 'ultimate', 'physical', 'area', { target: 'self', radius: 6, spendAllCareer: true }),
    ]),
    kit('Blood Dancer', 'blood_assassin', resource('bloodlust', 'Bloodlust', 5, 0), [
      a('Vein Slice', 'Stealth opener that builds Bloodlust.', 'builder', 'poison', 'melee', { careerBuild: 1, status: bleed('Vein Slice', 5) }),
      a('Poison Kiss', 'Venom application attack.', 'builder', 'poison', 'melee', { careerBuild: 1, status: debuff('Poison Kiss', 5) }),
      a('Shadow Prowl', 'Vanish and reposition.', 'defense', 'shadow', 'self'),
      a('Razor Waltz', 'Rapid multi-dagger flurry.', 'strike', 'physical', 'melee'),
      a('Crippling Cut', 'Slow plus healing reduction.', 'control', 'physical', 'melee', { status: slow('Crippling Cut', 4, 0.45) }),
      a('Heartseeker', 'Lunge toward marked prey.', 'mobility', 'physical', 'dash', { range: 12 }),
      a('Red Caress', 'Bloodlust-spending execute.', 'spender', 'poison', 'melee', { careerCost: 3 }),
      a('Mirror Veil', 'Brief evasive untargetable step.', 'defense', 'shadow', 'self'),
      a('Suffering Bloom', 'Detonate active poisons around the victim.', 'area', 'poison', 'area', { range: 3, radius: 4, careerCost: 2 }),
      a('Crimson Ecstasy', 'Ultimate blood-frenzy and flank pressure.', 'ultimate', 'poison', 'area', { target: 'self', radius: 5, spendAllCareer: true }),
    ]),
    kit('Dread Guard', 'hatred_tank', resource('hatred', 'Hatred', 100, 20), [
      a('Spite Lash', 'Spear lash that builds Hatred.', 'builder', 'physical', 'melee'),
      a('Malice Guard', 'Designate prey for elevated Hatred gain.', 'builder', 'shadow', 'projectile', { status: mark('Malice Guard', 7) }),
      a('Void Buckler', 'Spell block and reflect defense.', 'defense', 'shadow', 'self'),
      a('Glaive Hook', 'Pull and disrupt positioning.', 'control', 'physical', 'projectile', { range: 15, status: root('Glaive Hook', 1.3) }),
      a('Cruel Intercept', 'Leap to intercept and strike back.', 'mobility', 'physical', 'dash', { range: 12 }),
      a('Sunder Grace', 'Lower enemy parry and disrupt.', 'control', 'shadow', 'melee', { status: debuff('Sunder Grace', 5) }),
      a('Torment Cage', 'Taunt plus anti-escape field.', 'area', 'shadow', 'area', { target: 'self', radius: 4, status: slow('Torment Cage', 3, 0.4) }),
      a('Bitter Harvest', 'Hatred-spending sustain strike.', 'spender', 'shadow', 'melee', { careerCost: 30, effects: mixedDamageHeal('shadow', 18, 32, 12, 24) }),
      a('Harrow Pike', 'Long thrust line attack.', 'strike', 'physical', 'beam', { range: 12 }),
      a("Throne's Contempt", 'Ultimate prey hunt and anti-magic pressure.', 'ultimate', 'shadow', 'dash', { range: 14, spendAllCareer: true }),
    ]),
    kit('Dusk Weaver', 'dark_power_caster', resource('dark_power', 'Dark Power', 100, 0, true), [
      a('Umbral Bolt', 'Safe ranged builder.', 'builder', 'shadow', 'projectile'),
      a('Chill of Dusk', 'Snare and lingering pain spell.', 'control', 'shadow', 'projectile', { status: slow('Chill of Dusk', 4, 0.4) }),
      a('Black Shard', 'Heavy nuke that adds Dark Power quickly.', 'strike', 'shadow', 'projectile', { careerBuild: 18, cooldownSec: 5 }),
      a('Gloom Step', 'Blink that leaves a curse pool.', 'mobility', 'shadow', 'self'),
      a('Agony Thread', 'Debuff increasing incoming critical harm.', 'control', 'shadow', 'projectile', { status: debuff('Agony Thread', 6) }),
      a('Soul Freeze', 'Root with shatter follow-up.', 'control', 'shadow', 'projectile', { status: root('Soul Freeze', 2) }),
      a('Void Rain', 'Cursed ground AoE.', 'area', 'shadow', 'area', { range: 22, radius: 5 }),
      a('Cruel Harvest', 'Vent Dark Power for a safer next cast.', 'heal', 'shadow', 'self', { careerCost: 25 }),
      a('Backlash Surge', 'Weaponize accumulated instability.', 'spender', 'shadow', 'area', { target: 'self', radius: 4, careerCost: 35 }),
      a('Midnight Cataclysm', 'Ultimate storm with backlash risk.', 'ultimate', 'shadow', 'area', { range: 26, radius: 7, spendAllCareer: true }),
    ]),
    kit('Crimson Acolyte', 'siphon_healer', resource('essence', 'Essence', 100, 30), [
      a('Siphon Cut', 'Melee builder for Essence.', 'builder', 'poison', 'melee'),
      a('Blood Rite', 'Targeted heal that spends Essence.', 'heal', 'poison', 'self', { careerCost: 25 }),
      a('Pain Mirror', 'Mark causing suffering to feed you.', 'builder', 'shadow', 'projectile', { status: mark('Pain Mirror', 6), effects: mixedDamageHeal('shadow', 10, 18, 8, 14) }),
      a('Razor Prayer', 'Aura granting lifesteal nearby.', 'buff', 'poison', 'self'),
      a('Cruel Embrace', 'Pull target inward.', 'control', 'shadow', 'projectile', { range: 14, status: root('Cruel Embrace', 1.3) }),
      a('Scarlet Step', 'Rush slash and reposition.', 'mobility', 'poison', 'dash', { range: 12 }),
      a('Borrowed Vigor', 'Steal stats from foe for team gain.', 'control', 'shadow', 'melee', { status: debuff('Borrowed Vigor', 5) }),
      a('Covenant of Knives', 'Spinning AoE lifetap.', 'area', 'poison', 'area', { target: 'self', radius: 4, effects: mixedDamageHeal('poison', 16, 28, 14, 26) }),
      a('Dark Communion', 'Group heal over time at Essence cost.', 'heal', 'shadow', 'self', { careerCost: 30 }),
      a('Feast of the Shrine', 'Ultimate altar state converting damage into healing.', 'ultimate', 'poison', 'deployable', { target: 'self', radius: 7, spendAllCareer: true, effects: mixedDamageHeal('poison', 22, 38, 32, 52) }),
    ]),
  ].map((entry) => [entry.career, entry]),
);

export function getCareerAbilityKit(career: string | null | undefined): CareerAbilityKit {
  return CAREER_ABILITY_KITS[normalizeClassName(career)] ?? CAREER_ABILITY_KITS[DEFAULT_CLASS_NAME];
}

export function getAbilityForCareer(
  career: string | null | undefined,
  slot: number,
): AbilityDefinition | null {
  return getCareerAbilityKit(career).abilities[slot] ?? null;
}

export function createAbilityResourceState(career: string | null | undefined): AbilityResourceState {
  const res = getCareerAbilityKit(career).resource;
  return {
    key: res.key,
    label: res.label,
    current: res.initial,
    max: res.max,
  };
}

export function abilityHasEnoughResources(
  ability: AbilityDefinition,
  mana: number,
  resource: AbilityResourceState | null,
): boolean {
  const career = resource?.current ?? 0;
  return (
    mana >= (ability.resource.manaCost ?? 0) &&
    career >= (ability.resource.minCareer ?? 0) &&
    career >= (ability.resource.careerCost ?? 0)
  );
}

function kit(
  career: string,
  classFamily: AbilityFamily,
  resourceDefinition: CareerResourceDefinition,
  seeds: AbilitySeed[],
): CareerAbilityKit {
  return {
    career,
    classFamily,
    resource: resourceDefinition,
    abilities: seeds.map((seed, index) =>
      defineAbility(career, classFamily, resourceDefinition, seed, index),
    ),
  };
}

function resource(
  key: string,
  label: string,
  max: number,
  initial: number,
  highRisk = false,
): CareerResourceDefinition {
  return { key, label, max, initial, highRisk };
}

function a(
  name: string,
  summary: string,
  kind: AbilityKind,
  school: AbilitySchool,
  shape: AbilityShape,
  options: Partial<AbilitySeed> = {},
): AbilitySeed {
  return { name, summary, kind, school, shape, ...options };
}

function defineAbility(
  career: string,
  classFamily: AbilityFamily,
  res: CareerResourceDefinition,
  seed: AbilitySeed,
  slot: number,
): AbilityDefinition {
  const target = seed.target ?? defaultTarget(seed.kind, seed.shape);
  const cooldownSec = seed.cooldownSec ?? defaultCooldown(seed.kind);
  const animation = animationFor(seed.kind, seed.shape, seed.school);
  const resourceDelta = {
    manaCost: seed.manaCost ?? defaultManaCost(seed.kind),
    careerBuild: seed.careerBuild ?? defaultCareerBuild(seed.kind, res),
    careerCost: seed.careerCost ?? defaultCareerCost(seed.kind, res),
    spendAllCareer: seed.spendAllCareer,
    minCareer: seed.minCareer,
  };

  return {
    id: `${slug(career)}.${slug(seed.name)}`,
    career,
    classFamily,
    slot,
    key: HOTBAR_KEYS[slot] ?? String(slot + 1),
    icon: iconFor(seed.kind, seed.school, seed.shape),
    name: seed.name,
    summary: seed.summary,
    cooldownSec,
    gcdSec: seed.kind === 'stance' ? 0.5 : 1.2,
    tags: tagsFor(seed, target),
    resource: resourceDelta,
    animation,
    targeting: {
      target,
      shape: seed.shape,
      range: seed.range ?? defaultRange(seed.shape, target),
      radius: seed.radius ?? defaultRadius(seed.shape),
      projectileSpeed: defaultProjectileSpeed(seed.shape, seed.school),
      tracePolicy: 'server_auth',
    },
    effects: seed.effects ?? defaultEffects(seed, resourceDelta.spendAllCareer === true),
    vfxSockets: socketsFor(seed.shape, seed.school),
    cancelRules: {
      blockedBy: ['State.Stunned', 'State.Silenced'],
      appliesOwnerTags: animation.clip.startsWith('cast') ? ['State.Casting'] : ['State.Acting'],
    },
  };
}

function defaultTarget(kind: AbilityKind, shape: AbilityShape): AbilityTargetKind {
  if (shape === 'self' || shape === 'deployable') return 'self';
  if (kind === 'heal' || kind === 'buff' || kind === 'defense' || kind === 'stance') return 'self';
  return 'enemy';
}

function defaultCooldown(kind: AbilityKind): number {
  switch (kind) {
    case 'builder':
    case 'stance':
      return 1.5;
    case 'strike':
      return 4;
    case 'spender':
      return 6;
    case 'control':
      return 8;
    case 'mobility':
      return 10;
    case 'defense':
    case 'buff':
      return 12;
    case 'heal':
      return 8;
    case 'area':
      return 9;
    case 'summon':
      return 14;
    case 'ultimate':
      return 45;
    default:
      return 5;
  }
}

function defaultManaCost(kind: AbilityKind): number {
  switch (kind) {
    case 'builder':
    case 'stance':
      return 0;
    case 'strike':
      return 8;
    case 'spender':
    case 'control':
      return 10;
    case 'mobility':
      return 8;
    case 'defense':
    case 'buff':
    case 'area':
      return 12;
    case 'heal':
    case 'summon':
      return 15;
    case 'ultimate':
      return 25;
    default:
      return 0;
  }
}

function defaultCareerBuild(kind: AbilityKind, res: CareerResourceDefinition): number {
  if (kind !== 'builder') return 0;
  if (res.max <= 5) return 1;
  return 12;
}

function defaultCareerCost(kind: AbilityKind, res: CareerResourceDefinition): number {
  if (kind !== 'spender' && kind !== 'area') return 0;
  if (res.max <= 3) return kind === 'spender' ? 2 : 1;
  if (res.max <= 5) return kind === 'spender' ? 2 : 1;
  return kind === 'spender' ? 30 : 20;
}

function defaultRange(shape: AbilityShape, target: AbilityTargetKind): number {
  if (target === 'self') return 0;
  switch (shape) {
    case 'melee':
      return 3.2;
    case 'cone':
      return 7;
    case 'dash':
      return 12;
    case 'beam':
      return 18;
    case 'area':
      return 18;
    case 'pet':
      return 18;
    case 'projectile':
      return 24;
    default:
      return 12;
  }
}

function defaultRadius(shape: AbilityShape): number | undefined {
  switch (shape) {
    case 'area':
    case 'deployable':
      return 4;
    case 'cone':
      return 3;
    default:
      return undefined;
  }
}

function defaultProjectileSpeed(shape: AbilityShape, school: AbilitySchool): number | undefined {
  if (shape !== 'projectile' && shape !== 'pet') return undefined;
  if (school === 'physical' || school === 'engineer' || school === 'poison') return 32;
  return 24;
}

function animationFor(kind: AbilityKind, shape: AbilityShape, school: AbilitySchool): AbilityAnimation {
  const isWeaponProjectile = shape === 'projectile' && ['physical', 'engineer', 'poison'].includes(school);
  const isMelee = shape === 'melee' || shape === 'cone' || shape === 'dash';
  const actionId =
    kind === 'ultimate' ? 'ultimate_cast' :
    kind === 'heal' ? 'cast_heal' :
    kind === 'buff' || kind === 'defense' || kind === 'stance' || kind === 'summon' ? 'cast_short' :
    isWeaponProjectile ? 'shoot_standing' :
    isMelee ? (kind === 'spender' || kind === 'area' ? 'heavy_attack' : 'light_attack_a') :
    shape === 'beam' ? 'cast_long' :
    'cast_short';
  const durationSec =
    kind === 'ultimate' ? 1.45 :
    kind === 'spender' || kind === 'area' ? 0.9 :
    kind === 'control' || kind === 'heal' || kind === 'summon' ? 0.8 :
    kind === 'buff' || kind === 'defense' || kind === 'stance' ? 0.7 :
    0.58;
  const windowName: 'active' | 'release' = isMelee ? 'active' : 'release';
  return {
    actionId,
    clip: actionId,
    durationSec,
    upperBodyOnly: !isMelee,
    notifyWindows: [{ name: windowName, start: 0.34, end: 0.42 }],
  };
}

function defaultEffects(seed: AbilitySeed, spendAllCareer: boolean): AbilityEffect[] {
  const effects: AbilityEffect[] = [];
  const target = seed.target ?? defaultTarget(seed.kind, seed.shape);
  if (target === 'enemy' && seed.kind !== 'buff' && seed.kind !== 'defense' && seed.kind !== 'stance') {
    effects.push({
      kind: 'damage',
      school: seed.school,
      amount: damageAmount(seed.kind, spendAllCareer),
    });
  }
  if (seed.kind === 'heal' || (target === 'self' && seed.kind === 'ultimate')) {
    effects.push({
      kind: 'heal',
      school: seed.school,
      amount: healAmount(seed.kind),
    });
  }
  if (seed.status) {
    effects.push({
      kind: 'status',
      school: seed.school,
      status: seed.status,
    });
  }
  return effects;
}

function damageAmount(kind: AbilityKind, spendAllCareer: boolean) {
  const base = (() => {
    switch (kind) {
      case 'builder':
        return { min: 7, max: 12, statScale: 0.35, levelScale: 1.1 };
      case 'strike':
      case 'mobility':
        return { min: 12, max: 22, statScale: 0.45, levelScale: 1.4 };
      case 'spender':
        return { min: 18, max: 34, statScale: 0.55, resourceScale: 0.22, levelScale: 1.8 };
      case 'control':
        return { min: 8, max: 16, statScale: 0.25, levelScale: 1.0 };
      case 'area':
        return { min: 12, max: 24, statScale: 0.35, resourceScale: 0.12, levelScale: 1.2 };
      case 'ultimate':
        return { min: 30, max: 52, statScale: 0.75, resourceScale: 0.3, levelScale: 2.5 };
      default:
        return { min: 10, max: 18, statScale: 0.35, levelScale: 1.0 };
    }
  })();
  return spendAllCareer ? { ...base, resourceScale: Math.max(base.resourceScale ?? 0, 0.35) } : base;
}

function healAmount(kind: AbilityKind) {
  switch (kind) {
    case 'ultimate':
      return { min: 32, max: 54, statScale: 0.55, resourceScale: 0.25, levelScale: 2 };
    case 'defense':
      return { min: 18, max: 30, statScale: 0.35, levelScale: 1.2 };
    default:
      return { min: 24, max: 42, statScale: 0.45, resourceScale: 0.12, levelScale: 1.5 };
  }
}

function mixedDamageHeal(
  school: AbilitySchool,
  damageMin: number,
  damageMax: number,
  healMin: number,
  healMax: number,
): AbilityEffect[] {
  return [
    { kind: 'damage', school, amount: { min: damageMin, max: damageMax, statScale: 0.4, resourceScale: 0.1, levelScale: 1.2 } },
    { kind: 'heal', school, amount: { min: healMin, max: healMax, statScale: 0.35, resourceScale: 0.08, levelScale: 1.2 } },
  ];
}

function tagsFor(seed: AbilitySeed, target: AbilityTargetKind): string[] {
  const tags = [
    `Ability.${capitalize(seed.school)}`,
    `Target.${capitalize(target)}`,
    `Shape.${capitalize(seed.shape)}`,
    'Consumes.GCD',
  ];
  if (seed.status) tags.push(`Status.${capitalize(seed.status.kind)}`);
  if (seed.kind === 'ultimate') tags.push('Ability.Ultimate');
  return tags;
}

function socketsFor(shape: AbilityShape, school: AbilitySchool): string[] {
  if (shape === 'projectile') return school === 'physical' || school === 'engineer' ? ['muzzle', 'weapon_r'] : ['staff_tip', 'hand_r'];
  if (shape === 'melee' || shape === 'cone' || shape === 'dash') return ['weapon_r'];
  if (shape === 'self' || shape === 'deployable') return ['chest_core', 'ground_anchor'];
  return ['hand_r', 'ground_anchor'];
}

function iconFor(kind: AbilityKind, school: AbilitySchool, shape: AbilityShape): string {
  if (kind === 'ultimate') return 'U';
  if (kind === 'heal') return '+';
  if (kind === 'defense') return '#';
  if (kind === 'buff' || kind === 'stance') return '^';
  if (kind === 'control') return '!';
  if (kind === 'mobility') return '>';
  if (shape === 'area' || shape === 'cone') return '*';
  if (shape === 'projectile' || shape === 'beam') return school === 'physical' || school === 'engineer' ? '>' : '~';
  if (kind === 'spender') return 'X';
  return '/';
}

function burn(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'burn', durationSec, magnitude: 0.15 };
}

function bleed(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'bleed', durationSec, magnitude: 0.15 };
}

function slow(label: string, durationSec: number, magnitude: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'slow', durationSec, magnitude };
}

function root(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'root', durationSec, magnitude: 1 };
}

function silence(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'silence', durationSec };
}

function stagger(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'stagger', durationSec, magnitude: 1 };
}

function mark(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'mark', durationSec };
}

function debuff(label: string, durationSec: number): AbilityStatusPayload {
  return { id: slug(label), label, kind: 'debuff', durationSec, magnitude: 0.2 };
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
