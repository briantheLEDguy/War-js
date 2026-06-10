import { beforeEach, describe, expect, test, vi } from 'vitest';
import { createAbilityResourceState, getAbilityForCareer } from '../src/game/abilities/abilityData';
import { tryActivateAbility } from '../src/game/abilities/AbilityRuntime';
import { spawnAbilityVfx } from '../src/game/abilities/AbilityVfx';
import { useGameStore } from '../src/state/gameStore';
import {
  getEnemyObject,
  makeCharacter,
  makeEnemy,
  makePlayer,
  makeVfxLayer,
  resetGameStore,
} from './testUtils';

vi.mock('../src/game/abilities/AbilityVfx', () => ({
  spawnAbilityVfx: vi.fn(),
}));

const NOW = 10_000;

describe('ability runtime activation', () => {
  beforeEach(() => {
    resetGameStore();
    vi.mocked(spawnAbilityVfx).mockClear();
  });

  test('returns null without a character or with an invalid slot', () => {
    expect(activate(0)).toBeNull();

    useGameStore.getState().setCharacter(makeCharacter());
    expect(activate(99)).toBeNull();
    expect(vi.mocked(spawnAbilityVfx)).not.toHaveBeenCalled();
  });

  test('returns null for cooldowns, missing targets, dead targets, out-of-range targets, and insufficient resources', () => {
    useGameStore.getState().setCharacter(makeCharacter());
    useGameStore.getState().setHotbarCooldown(6, 3);
    setTargetedEnemy(makeEnemy());
    expect(activate(6)).toBeNull();

    resetForCharacter();
    expect(activate(6)).toBeNull();

    resetForCharacter();
    setTargetedEnemy(makeEnemy({ alive: false }));
    expect(activate(6)).toBeNull();

    resetForCharacter();
    setTargetedEnemy(makeEnemy({ position: { x: 0, y: 0, z: 100 } }));
    expect(activate(6)).toBeNull();

    resetForCharacter();
    useGameStore.getState().setAbilityResource({
      ...createAbilityResourceState('Battle Prelate'),
      current: 0,
    });
    expect(activate(7)).toBeNull();
    expect(vi.mocked(spawnAbilityVfx)).not.toHaveBeenCalled();
  });

  test('activates an enemy ability and schedules its impact', () => {
    const player = makePlayer();
    const vfx = makeVfxLayer();
    const enemy = makeEnemy({ id: 'dummy-a', position: { x: 0, y: 0, z: 8 } });
    resetForCharacter();
    setTargetedEnemy(enemy);

    const result = activate(6, player, vfx);
    const ability = getAbilityForCareer('Battle Prelate', 6);

    expect(result?.ability).toBe(ability);
    expect(result?.impacts).toHaveLength(1);
    expect(result?.impacts[0]).toMatchObject({
      ability,
      targetId: enemy.id,
      sourcePosition: { x: 0, y: 0, z: 0 },
      sourceRotationY: 0,
      sourceStrength: 14,
      sourceLevel: 5,
      resourceSpent: 0,
    });
    expect(result?.impacts[0].dueAt).toBeGreaterThan(NOW);
    expect(useGameStore.getState().character?.mana).toBe(52);
    expect(useGameStore.getState().abilityResource?.current).toBe(20);
    expect(useGameStore.getState().hotbarCooldowns[6]).toBe(ability?.cooldownSec);
    expect(player.animator?.playAction).toHaveBeenCalledWith(ability?.animation.actionId, ability?.animation.durationSec);
    expect(player.playGlbAction).not.toHaveBeenCalled();
    expect(vi.mocked(spawnAbilityVfx)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(spawnAbilityVfx).mock.calls[0][1]).toBe(ability);
  });

  test('updates builder, spender, spend-all, and self-target resources correctly', () => {
    resetForCharacter();
    setTargetedEnemy(makeEnemy());
    expect(activate(0)?.ability.name).toBe('Litany of Strikes');
    expect(useGameStore.getState().character?.mana).toBe(60);
    expect(useGameStore.getState().abilityResource?.current).toBe(32);

    resetForCharacter({ mana: 60 });
    useGameStore.getState().setAbilityResource({
      ...createAbilityResourceState('Battle Prelate'),
      current: 50,
    });
    expect(activate(5)?.ability.name).toBe('Reliquary Smash');
    expect(useGameStore.getState().character?.mana).toBe(48);
    expect(useGameStore.getState().abilityResource?.current).toBe(30);

    resetForCharacter({ mana: 60 });
    useGameStore.getState().setAbilityResource({
      ...createAbilityResourceState('Battle Prelate'),
      current: 72,
    });
    expect(activate(9)?.ability.name).toBe('Last Homily');
    expect(useGameStore.getState().character?.mana).toBe(35);
    expect(useGameStore.getState().abilityResource?.current).toBe(0);
  });

  test('allows self abilities without a selected target', () => {
    resetForCharacter({ mana: 60 });
    useGameStore.getState().setTarget(null);

    const result = activate(2);

    expect(result?.ability.name).toBe("Martyr's Ward");
    expect(result?.impacts).toEqual([]);
    expect(useGameStore.getState().character?.mana).toBe(46);
    expect(vi.mocked(spawnAbilityVfx)).toHaveBeenCalledTimes(1);
  });

  test('ticks cooldowns without going below zero', () => {
    resetForCharacter();
    useGameStore.getState().setHotbarCooldown(1, 5);

    useGameStore.getState().tickCooldowns(1.5);
    expect(useGameStore.getState().hotbarCooldowns[1]).toBeCloseTo(3.5);

    useGameStore.getState().tickCooldowns(10);
    expect(useGameStore.getState().hotbarCooldowns[1]).toBe(0);
  });
});

function activate(slot: number, player = makePlayer(), vfx = makeVfxLayer()) {
  return tryActivateAbility({
    slot,
    player,
    now: NOW,
    vfx,
    getEnemyObject,
  });
}

function resetForCharacter(overrides: Parameters<typeof makeCharacter>[0] = {}): void {
  resetGameStore();
  useGameStore.getState().setCharacter(makeCharacter(overrides));
}

function setTargetedEnemy(enemy = makeEnemy()): void {
  useGameStore.getState().setEnemies([enemy]);
  useGameStore.getState().setTarget(enemy.id);
}
