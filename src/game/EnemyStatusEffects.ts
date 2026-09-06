import type { CombatStatusEffect } from '../state/gameStore';

export function enemyDamageTakenMultiplier(effects: readonly CombatStatusEffect[], now: number): number {
  return 1 + strongest(effects, 'damage_taken', now, 0.6);
}

export function enemyDamageDealtMultiplier(effects: readonly CombatStatusEffect[], now: number): number {
  return 1 - strongest(effects, 'damage_dealt', now, 0.75);
}

export function dueStatusTicks(effect: CombatStatusEffect, now: number): number {
  if (!effect.tickDamage || effect.nextTickAt === undefined) return 0;
  return Math.max(0, Math.min(60, Math.floor((Math.min(now, effect.expiresAt) - effect.nextTickAt) / 1000) + 1));
}

function strongest(effects: readonly CombatStatusEffect[], modifier: NonNullable<CombatStatusEffect['damageModifier']>, now: number, cap: number): number {
  return effects.filter((effect) => effect.expiresAt > now && effect.damageModifier === modifier)
    .reduce((max, effect) => Math.max(max, Math.min(cap, Math.max(0, Number.isFinite(effect.magnitude) ? effect.magnitude! : 0))), 0);
}
