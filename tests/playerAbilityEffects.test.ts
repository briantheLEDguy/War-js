import { describe, expect, test } from 'vitest';
import { applyPlayerUtilityEffects, createAbilityMovementRequest, playerAbilityMoveMultiplier, playerOutgoingDamageMultiplier, resolvePlayerIncomingDamage } from '../src/game/abilities/playerAbilityEffects';
import type { PlayerStatusEffect } from '../src/state/gameStore';
import type { AbilityEffect } from '../src/game/abilities/types';

const NOW = 1000;
const context = { now: NOW, maxHealth: 200, sourceAbilityId: 'test.ward', label: 'Ward' };
const status = (kind: PlayerStatusEffect['kind'], extra: Partial<PlayerStatusEffect> = {}): PlayerStatusEffect => ({ id: kind, label: kind, kind, expiresAt: NOW + 5000, ...extra });

describe('player utility effects', () => {
  test('strongest guard reduces damage before a finite shield is consumed', () => {
    const statuses = [status('guard', { magnitude: 0.3 }), status('guard', { id: 'weak', magnitude: 0.1 }), status('shield', { remainingAbsorb: 50 })];
    const first = resolvePlayerIncomingDamage(100, statuses, NOW);
    expect(first.damage).toBe(20);
    expect(first.statusEffects.filter((effect) => effect.kind === 'shield')).toEqual([]);
    expect(resolvePlayerIncomingDamage(100, first.statusEffects, NOW).damage).toBe(70);
    expect(statuses[2].remainingAbsorb).toBe(50);
  });

  test('shield retains the remainder and expired defenses cannot protect', () => {
    const first = resolvePlayerIncomingDamage(20, [status('shield', { remainingAbsorb: 50 })], NOW);
    expect(first.damage).toBe(0);
    expect(first.statusEffects[0].remainingAbsorb).toBe(30);
    expect(resolvePlayerIncomingDamage(100, first.statusEffects, NOW + 5000)).toEqual({ damage: 100, statusEffects: [] });
  });

  test('repeated and different shields do not add unbounded pools', () => {
    const effect: AbilityEffect = { kind: 'player_status', playerStatus: { kind: 'shield', magnitude: 0.25, durationSec: 5 } };
    const once = applyPlayerUtilityEffects([effect], [], context);
    const twice = applyPlayerUtilityEffects([effect], once, { ...context, sourceAbilityId: 'test.other' });
    expect(twice).toHaveLength(1);
    expect(twice[0].remainingAbsorb).toBe(50);
    expect(resolvePlayerIncomingDamage(80, twice, NOW).damage).toBe(30);
  });

  test('same stance family replaces its previous effect while preserving other buffs', () => {
    const before = [status('guard', { stackGroup: 'stance:templar' }), status('shield', { remainingAbsorb: 20 })];
    const after = applyPlayerUtilityEffects([{ kind: 'player_status', playerStatus: { kind: 'empower', magnitude: 0.2, durationSec: 12, stackGroup: 'stance:templar' } }], before, context);
    expect(after.map((effect) => effect.kind)).toEqual(['shield', 'empower']);
    expect(playerOutgoingDamageMultiplier(after, NOW)).toBe(1.2);
  });

  test('cleanse removes harmful conditions and preserves active defenses', () => {
    const before = [status('root'), status('slow'), status('stagger'), status('debuff'), status('guard', { magnitude: 0.3 })];
    const after = applyPlayerUtilityEffects([{ kind: 'cleanse', cleanse: { kinds: ['root', 'slow', 'stagger', 'debuff'] } }], before, context);
    expect(after.map((effect) => effect.kind)).toEqual(['guard']);
  });

  test('bonuses use the strongest finite active value and expire exactly on time', () => {
    const statuses = [status('empower', { magnitude: 0.2 }), status('empower', { id: 'extra', magnitude: 0.4 }), status('haste', { magnitude: 0.3 })];
    expect(playerOutgoingDamageMultiplier(statuses, NOW)).toBe(1.4);
    expect(playerAbilityMoveMultiplier(statuses, NOW)).toBe(1.3);
    expect(playerOutgoingDamageMultiplier(statuses, NOW + 5000)).toBe(1);
    expect(playerAbilityMoveMultiplier(statuses, NOW + 5000)).toBe(1);
    expect(resolvePlayerIncomingDamage(100, [status('guard', { magnitude: 500 })], NOW).damage).toBe(25);
    expect(playerOutgoingDamageMultiplier([status('empower', { magnitude: Infinity })], NOW)).toBe(1);
    expect(playerAbilityMoveMultiplier([status('haste', { magnitude: NaN })], NOW)).toBe(1);
  });

  test('movement follows facing or target direction with a capped gap close and melee stopping distance', () => {
    const origin = { x: 0, y: 3, z: 0 };
    const forward = createAbilityMovementRequest({ mode: 'forward', distance: 6 }, origin, Math.PI / 2);
    expect(forward.destination.x).toBeCloseTo(6);
    expect(forward.destination.y).toBe(3);
    const back = createAbilityMovementRequest({ mode: 'backward', distance: 6 }, origin, 0, { x: 10, y: 0, z: 0 });
    expect(back.destination.x).toBe(-6);
    const close = createAbilityMovementRequest({ mode: 'toward_target', distance: 100 }, origin, 0, { x: 0, y: 0, z: 10 });
    expect(close.destination.z).toBe(8.4);
    expect(createAbilityMovementRequest({ mode: 'toward_target', distance: 100 }, origin, 0, { x: 0, y: 0, z: 100 }).distance).toBe(12);
    expect(createAbilityMovementRequest({ mode: 'toward_target', distance: 12 }, origin, 0, { x: 0, y: 0, z: 1 }).distance).toBe(0);
    expect(origin).toEqual({ x: 0, y: 3, z: 0 });
  });
});
