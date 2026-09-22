import { getCareerAbilityKit } from './abilityData';
import type { AbilityDefinition } from './types';

export const FULL_KIT_LEVEL = 8;

// Keep established keys stable while giving every class a usable opening kit.
// Starter choices avoid abilities whose advertised utility is not yet simulated.
const STARTER_SLOTS: Record<string, readonly number[]> = {
  'Ember Arcanist': [0, 1, 6],
  'Hex Inquisitor': [0, 2, 4],
  'Sunfire Templar': [3, 7, 8],
  'Battle Prelate': [0, 1, 7],
  Stoneguard: [1, 2, 8],
  Doomseeker: [1, 3, 8],
  Glyphbinder: [0, 2, 3],
  Siegewright: [1, 2, 4],
  'Blade Savant': [0, 1, 2],
  'Pride Warden': [0, 2, 6],
  'Aether Sage': [0, 1, 4],
  'Veil Ranger': [0, 1, 5],
  Dreadsworn: [3, 6, 7],
  'Warped Reaver': [3, 5, 7],
  'Void Magister': [1, 3, 4],
  'Ruin Oracle': [0, 1, 2],
  Warbrute: [0, 1, 2],
  'Fang Herder': [0, 1, 6],
  'Bog Hexer': [0, 1, 2],
  Cleaver: [0, 1, 3],
  'Blood Dancer': [0, 4, 6],
  'Dread Guard': [0, 3, 7],
  'Dusk Weaver': [0, 1, 2],
  'Crimson Acolyte': [0, 1, 2],
};

export function abilityUnlockLevel(ability: AbilityDefinition): number {
  const starters = STARTER_SLOTS[ability.career] ?? [];
  if (starters.includes(ability.slot)) return 1;
  // Reward early levels with simulated effects before unlocking utility placeholders.
  // Sort within each group by the original slot; hotbar keys never move.
  const remaining = getCareerAbilityKit(ability.career).abilities
    .filter((entry) => !starters.includes(entry.slot))
    .sort((a, b) => Number(hasSimulatedEffect(b)) - Number(hasSimulatedEffect(a)) || a.slot - b.slot);
  return 2 + remaining.findIndex((entry) => entry.slot === ability.slot);
}

function hasSimulatedEffect(ability: AbilityDefinition): boolean {
  const buildsResource = !ability.resource.spendAllCareer &&
    (ability.resource.careerBuild ?? 0) > (ability.resource.careerCost ?? 0);
  return buildsResource || ability.effects.some((effect) => {
    if (effect.kind === 'damage' || effect.kind === 'heal') return (effect.amount?.max ?? 0) > 0;
    return effect.kind === 'status' && effect.status !== undefined &&
      ['slow', 'root', 'stagger', 'silence'].includes(effect.status.kind);
  });
}

export function isAbilityUnlocked(ability: AbilityDefinition, level: number): boolean {
  return Number.isFinite(level) && level >= abilityUnlockLevel(ability);
}

export function newlyUnlockedAbilities(
  career: string | null | undefined,
  previousLevel: number,
  nextLevel: number,
): AbilityDefinition[] {
  return getCareerAbilityKit(career).abilities
    .filter((ability) => {
      const unlockLevel = abilityUnlockLevel(ability);
      return unlockLevel > previousLevel && unlockLevel <= nextLevel;
    })
    .sort((a, b) => abilityUnlockLevel(a) - abilityUnlockLevel(b) || a.slot - b.slot);
}
