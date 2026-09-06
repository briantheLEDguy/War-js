import { beforeEach, describe, expect, test, vi } from 'vitest';
import { CAREER_ABILITY_KITS, createAbilityResourceState, getAbilityForCareer } from '../src/game/abilities/abilityData';
import { getAbilityActivationFailure, tryActivateAbility } from '../src/game/abilities/AbilityRuntime';
import { spawnAbilityVfx } from '../src/game/abilities/AbilityVfx';
import { useGameStore } from '../src/state/gameStore';
import { getEnemyObject, makeCharacter, makeEnemy, makePlayer, resetGameStore } from './testUtils';

vi.mock('../src/game/abilities/AbilityVfx', () => ({ spawnAbilityVfx: vi.fn() }));
const NOW = 1000;
const context = (slot: number, now = NOW) => ({ slot, now, player: makePlayer(), vfx: null, getEnemyObject });
function setup(career = 'Battle Prelate') {
  resetGameStore();
  useGameStore.getState().setCharacter(makeCharacter({ className: career, level: 8, mana: 100 }));
  const resource = createAbilityResourceState(career);
  useGameStore.getState().setAbilityResource({ ...resource, current: resource.max });
  const enemy = makeEnemy({ position: { x: 0, y: 0, z: 2 } });
  useGameStore.getState().setEnemies([enemy]);
  useGameStore.getState().setTarget(enemy.id);
}

describe('utility activation and shared recovery', () => {
  beforeEach(() => { setup(); vi.mocked(spawnAbilityVfx).mockClear(); });

  test('the only effectless actions are explicitly unavailable persistent summons', () => {
    const all = Object.values(CAREER_ABILITY_KITS).flatMap((kit) => kit.abilities);
    expect(all.filter((ability) => ability.unavailableReason).map((ability) => ability.name)).toEqual(['Icon of Wrath', 'Deploy Gunlet', 'Summon Idol']);
    expect(all.filter((ability) => !ability.effects.length).every((ability) => ability.unavailableReason)).toBe(true);
    for (const ability of all.filter((entry) => entry.unavailableReason)) {
      setup(ability.career);
      const before = useGameStore.getState();
      expect(getAbilityActivationFailure(context(ability.slot))?.code).toBe('unavailable_ability');
      expect(tryActivateAbility(context(ability.slot))).toBeNull();
      expect(useGameStore.getState().character).toBe(before.character);
      expect(useGameStore.getState().abilityResource).toBe(before.abilityResource);
      expect(useGameStore.getState().hotbarCooldowns).toBe(before.hotbarCooldowns);
      expect(useGameStore.getState().globalCooldownUntil).toBe(0);
    }
    expect(spawnAbilityVfx).not.toHaveBeenCalled();
  });

  test('a clear movement request happens before costs and only combat effects are delayed', () => {
    const ctx = context(3);
    useGameStore.getState().updateEnemy('enemy-test', { position: { x: 0, y: 0, z: 10 } });
    const movePlayer = vi.fn((request) => {
      expect(useGameStore.getState().character?.mana).toBe(100);
      Object.assign(ctx.player.position, request.destination);
      return true;
    });
    const result = tryActivateAbility({ ...ctx, movePlayer });
    expect(movePlayer).toHaveBeenCalledOnce();
    expect(ctx.player.position.z).toBeCloseTo(8.4);
    expect(result?.impacts[0].sourcePosition.z).toBeCloseTo(8.4);
    expect(result?.impacts[0].effects.map((effect) => effect.kind)).toEqual(['damage', 'status']);
    expect(useGameStore.getState().character?.mana).toBe(92);
  });

  test('blocked movement and failed prerequisites spend nothing and never start recovery', () => {
    setup('Ember Arcanist');
    const ctx = context(4);
    expect(getAbilityActivationFailure(ctx)?.code).toBe('movement_blocked');
    const movePlayer = vi.fn(() => false);
    const before = useGameStore.getState();
    expect(tryActivateAbility({ ...ctx, movePlayer })).toBeNull();
    expect(useGameStore.getState().character).toBe(before.character);
    expect(useGameStore.getState().hotbarCooldowns).toBe(before.hotbarCooldowns);
    expect(useGameStore.getState().globalCooldownUntil).toBe(0);
    expect(useGameStore.getState().abilityFeedback?.message).toContain('path is blocked');
    expect(spawnAbilityVfx).not.toHaveBeenCalled();
    useGameStore.getState().updateCharacter({ mana: 0 });
    movePlayer.mockClear();
    expect(tryActivateAbility({ ...ctx, movePlayer })).toBeNull();
    expect(movePlayer).not.toHaveBeenCalled();
  });

  test('cleanse can rescue a rooted and staggered player immediately', () => {
    setup('Hex Inquisitor');
    useGameStore.setState({ playerStatusEffects: [
      { id: 'root', label: 'Root', kind: 'root', expiresAt: NOW + 3000 },
      { id: 'stagger', label: 'Stagger', kind: 'stagger', expiresAt: NOW + 3000 },
    ] });
    expect(getAbilityActivationFailure(context(0))?.code).toBe('controlled_player');
    expect(tryActivateAbility(context(7))?.impacts).toEqual([]);
    expect(useGameStore.getState().playerStatusEffects.map((effect) => effect.kind)).toEqual(['guard']);
  });

  test('root prevents movement until it expires without disabling stationary attacks', () => {
    useGameStore.setState({ playerStatusEffects: [{ id: 'root', label: 'Root', kind: 'root', expiresAt: NOW + 2000 }] });
    const moving = { ...context(3), movePlayer: vi.fn(() => true) };
    expect(getAbilityActivationFailure(moving)?.code).toBe('controlled_player');
    expect(getAbilityActivationFailure(context(0))).toBeNull();
    expect(getAbilityActivationFailure({ ...moving, now: NOW + 2000 })).toBeNull();
  });

  test('success starts shared recovery, failed attempts preserve costs, and exact expiry allows a new action', () => {
    expect(tryActivateAbility(context(0))).not.toBeNull();
    expect(useGameStore.getState().globalCooldownUntil).toBe(2200);
    const before = useGameStore.getState();
    expect(getAbilityActivationFailure(context(2, 2199))?.code).toBe('global_cooldown');
    expect(tryActivateAbility(context(2, 2199))).toBeNull();
    expect(useGameStore.getState().character).toBe(before.character);
    expect(useGameStore.getState().hotbarCooldowns).toBe(before.hotbarCooldowns);
    expect(tryActivateAbility(context(2, 2200))).not.toBeNull();
    expect(useGameStore.getState().globalCooldownUntil).toBe(3400);
  });

  test('zero-GCD actions neither wait for nor replace shared recovery', () => {
    const ability = getAbilityForCareer('Battle Prelate', 2)!;
    const oldGcd = ability.gcdSec;
    try {
      ability.gcdSec = 0;
      useGameStore.getState().setGlobalCooldownUntil(5000);
      expect(tryActivateAbility(context(2))).not.toBeNull();
      expect(useGameStore.getState().globalCooldownUntil).toBe(5000);
    } finally { ability.gcdSec = oldGcd; }
  });

  test('a character refresh preserves recovery while an identity change resets it', () => {
    useGameStore.getState().setGlobalCooldownUntil(5000);
    useGameStore.getState().setCharacter(makeCharacter());
    expect(useGameStore.getState().globalCooldownUntil).toBe(5000);
    useGameStore.getState().setCharacter(makeCharacter({ id: 'different-character' }));
    expect(useGameStore.getState().globalCooldownUntil).toBe(0);
  });
});
