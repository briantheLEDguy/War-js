import type { PlayerStatusEffect } from '../../state/gameStore';
import type { AbilityEffect, AbilityMovement, AbilityMovementRequest, PlayerUtilityStatusKind } from './types';

export function applyPlayerUtilityEffects(
  effects: readonly AbilityEffect[],
  currentStatuses: readonly PlayerStatusEffect[],
  context: { now: number; maxHealth: number; sourceAbilityId: string; label: string },
): PlayerStatusEffect[] {
  let statuses = currentStatuses.filter((effect) => effect.expiresAt > context.now);
  for (const effect of effects) {
    if (effect.kind === 'cleanse' && effect.cleanse) {
      const kinds: readonly string[] = effect.cleanse.kinds;
      statuses = statuses.filter((status) => !kinds.includes(status.kind));
    }
    if (effect.kind !== 'player_status' || !effect.playerStatus) continue;
    const payload = effect.playerStatus;
    const duration = finiteClamp(payload.durationSec, 0, 60);
    if (duration === 0) continue;
    const magnitude = finiteClamp(payload.magnitude, 0, payload.kind === 'guard' ? 0.75 : 0.6);
    const id = `${context.sourceAbilityId}:${payload.kind}`;
    const shieldCap = Math.round(finiteClamp(context.maxHealth, 0, 1_000_000) * 0.6);
    const previousShield = statuses.reduce((max, status) => status.kind === 'shield'
      ? Math.max(max, finiteClamp(status.remainingAbsorb ?? 0, 0, shieldCap)) : max, 0);
    statuses = statuses.filter((status) => status.id !== id &&
      (!payload.stackGroup || status.stackGroup !== payload.stackGroup) &&
      (payload.kind !== 'shield' || status.kind !== 'shield'));
    statuses.push({
      id, label: context.label, kind: payload.kind, magnitude,
      expiresAt: context.now + duration * 1000, sourceAbilityId: context.sourceAbilityId,
      stackGroup: payload.stackGroup,
      remainingAbsorb: payload.kind === 'shield'
        ? Math.max(previousShield, Math.round(finiteClamp(context.maxHealth, 0, 1_000_000) * magnitude))
        : undefined,
    });
  }
  return statuses;
}

/** Apply the strongest guard, then consume one finite shield pool without stacking. */
export function resolvePlayerIncomingDamage(
  rawDamage: number, statuses: readonly PlayerStatusEffect[], now: number,
): { damage: number; statusEffects: PlayerStatusEffect[] } {
  const active = statuses.filter((effect) => effect.expiresAt > now);
  let damage = Math.round(finiteClamp(rawDamage, 0, 1_000_000) * (1 - strongest(active, 'guard', 0.75)));
  const shield = active.filter((effect) => effect.kind === 'shield')
    .sort((a, b) => (b.remainingAbsorb ?? 0) - (a.remainingAbsorb ?? 0))[0];
  const remaining = finiteClamp(shield?.remainingAbsorb ?? 0, 0, 1_000_000);
  const absorbed = Math.min(damage, remaining);
  damage -= absorbed;
  const statusEffects = active.flatMap((effect) => {
    if (effect.kind !== 'shield') return [{ ...effect }];
    if (effect !== shield || remaining <= absorbed) return [];
    return [{ ...effect, remainingAbsorb: remaining - absorbed }];
  });
  return { damage, statusEffects };
}

export function playerOutgoingDamageMultiplier(statuses: readonly PlayerStatusEffect[], now: number): number {
  return 1 + strongest(statuses.filter((effect) => effect.expiresAt > now), 'empower', 0.6);
}

export function playerAbilityMoveMultiplier(statuses: readonly PlayerStatusEffect[], now: number): number {
  return 1 + strongest(statuses.filter((effect) => effect.expiresAt > now), 'haste', 0.6);
}

export function createAbilityMovementRequest(
  movement: AbilityMovement, origin: AbilityMovementRequest['origin'], rotationY: number,
  target?: AbilityMovementRequest['origin'] | null,
): AbilityMovementRequest {
  const facing = Number.isFinite(rotationY) ? rotationY : 0;
  let dx = Math.sin(facing);
  let dz = Math.cos(facing);
  let distance = finiteClamp(movement.distance, 0, 12);
  if (target && movement.mode !== 'forward') {
    dx = target.x - origin.x;
    dz = target.z - origin.z;
    const targetDistance = Math.hypot(dx, dz);
    if (targetDistance > 0.001) { dx /= targetDistance; dz /= targetDistance; }
    else { dx = Math.sin(facing); dz = Math.cos(facing); }
    if (movement.mode === 'toward_target') distance = Math.min(distance, Math.max(0, targetDistance - 1.6));
  }
  if (movement.mode === 'backward') { dx *= -1; dz *= -1; }
  return {
    mode: movement.mode, origin: { ...origin }, direction: { x: dx, z: dz }, distance,
    destination: { x: origin.x + dx * distance, y: origin.y, z: origin.z + dz * distance },
  };
}

function strongest(statuses: readonly PlayerStatusEffect[], kind: PlayerUtilityStatusKind, limit: number): number {
  return statuses.filter((effect) => effect.kind === kind)
    .reduce((max, effect) => Math.max(max, finiteClamp(effect.magnitude ?? 0, 0, limit)), 0);
}

function finiteClamp(value: number, min: number, max: number): number {
  return Number.isFinite(value) ? Math.max(min, Math.min(max, value)) : min;
}
