import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { Combat } from '../src/game/Combat';
import { Enemy } from '../src/game/Enemy';
import { dueStatusTicks, enemyDamageTakenMultiplier, enemyDamageDealtMultiplier } from '../src/game/EnemyStatusEffects';
import { useGameStore, type CombatStatusEffect } from '../src/state/gameStore';
import type { Terrain } from '../src/world/Terrain';
import { makeCharacter, makeEnemy, makePlayer, resetGameStore } from './testUtils';

describe('functional combat statuses', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ playerDead: false, inventory: [], quests: [] });
    useGameStore.getState().setCharacter(makeCharacter({ className: 'Ember Arcanist', level: 8, health: 100, maxHealth: 100, xp: 0 }));
    vi.spyOn(Math, 'random').mockReturnValue(0);
  });
  afterEach(() => vi.restoreAllMocks());

  test('burn applies real periodic damage once per second, including its final tick', () => {
    const combat = new Combat();
    useGameStore.getState().setEnemies([makeEnemy({ health: 1000, maxHealth: 1000 })]);
    useGameStore.getState().setTarget('enemy-test');
    expect(combat.tryAbility(2, makePlayer(), 0)).toBe(true);
    combat.tickAbilityImpacts(1000);
    const affected = useGameStore.getState().enemies[0];
    const burn = affected.statusEffects!.find((effect) => effect.kind === 'burn')!;
    expect(burn.tickDamage).toBeGreaterThan(0);
    combat.tickStatusEffects(1999);
    expect(useGameStore.getState().enemies[0].health).toBe(affected.health);
    combat.tickStatusEffects(2000);
    expect(useGameStore.getState().enemies[0].health).toBe(affected.health - burn.tickDamage!);
    combat.tickStatusEffects(2000);
    expect(useGameStore.getState().enemies[0].health).toBe(affected.health - burn.tickDamage!);
    combat.tickStatusEffects(burn.expiresAt + 1000);
    expect(useGameStore.getState().enemies[0].health).toBe(affected.health - burn.tickDamage! * 5);
    expect(useGameStore.getState().enemies[0].statusEffects).toEqual([]);
  });

  test('periodic damage kills once and clears the dead target status', () => {
    const combat = new Combat();
    const effect: CombatStatusEffect = { id: 'bleed', label: 'Bleed', kind: 'bleed', sourceAbilityId: 'test',
      expiresAt: 5000, nextTickAt: 1000, tickDamage: 10 };
    useGameStore.getState().setEnemies([makeEnemy({ health: 5, statusEffects: [effect] })]);
    combat.tickStatusEffects(4000);
    expect(useGameStore.getState().enemies[0]).toMatchObject({ alive: false, health: 0, statusEffects: [] });
    const xp = useGameStore.getState().character!.xp;
    combat.tickStatusEffects(6000);
    expect(useGameStore.getState().character!.xp).toBe(xp);
    expect(xp).toBeGreaterThan(0);
  });

  test('strongest modifiers apply once and expire at the boundary', () => {
    const effects: CombatStatusEffect[] = [
      { id: 'mark1', label: 'Mark', kind: 'mark', sourceAbilityId: 'a', damageModifier: 'damage_taken', magnitude: 0.1, expiresAt: 5000 },
      { id: 'mark2', label: 'Mark', kind: 'mark', sourceAbilityId: 'b', damageModifier: 'damage_taken', magnitude: 0.2, expiresAt: 5000 },
      { id: 'weak', label: 'Weakened', kind: 'debuff', sourceAbilityId: 'c', damageModifier: 'damage_dealt', magnitude: 0.2, expiresAt: 5000 },
    ];
    expect(enemyDamageTakenMultiplier(effects, 4000)).toBe(1.2);
    expect(enemyDamageDealtMultiplier(effects, 4000)).toBe(0.8);
    expect(enemyDamageTakenMultiplier(effects, 5000)).toBe(1);
    expect(enemyDamageDealtMultiplier(effects, 5000)).toBe(1);
    expect(dueStatusTicks({ ...effects[0], nextTickAt: 1000, tickDamage: 2 }, 6000)).toBe(5);
  });

  test('ordinary attacks consume a finite shield after guard mitigation', () => {
    const combat = new Combat();
    const enemy = new Enemy({ id: 'guard', name: 'Guard', level: 1, x: 0, z: 2, maxHealth: 100,
      archetype: 'guard', aggroRange: 10, attackRange: 3, attackDamage: 20, moveSpeed: 0 }, { heightAt: () => 0 } as Terrain);
    enemy.object = new THREE.Group();
    enemy.position.set(0, 0, 2); enemy.homePosition.copy(enemy.position);
    enemy.abilityCooldown = 100;
    combat.registerEnemy(enemy);
    useGameStore.getState().setEnemies([makeEnemy({ id: 'guard', position: { x: 0, y: 0, z: 2 } })]);
    useGameStore.setState({ playerStatusEffects: [
      { id: 'guard', label: 'Guard', kind: 'guard', magnitude: 0.5, expiresAt: 10000 },
      { id: 'shield', label: 'Shield', kind: 'shield', remainingAbsorb: 10, expiresAt: 10000 },
    ] });
    expect(combat.playerInCombat).toBe(false);
    combat.tickEnemies(0.1, 1000, makePlayer());
    expect(combat.playerInCombat).toBe(true);
    expect(useGameStore.getState().character!.health).toBe(100);
    expect(useGameStore.getState().playerStatusEffects.some((effect) => effect.kind === 'shield')).toBe(false);
    enemy.attackCooldown = 0;
    combat.tickEnemies(0.1, 2000, makePlayer());
    expect(useGameStore.getState().character!.health).toBe(90);
    combat.resetEnemy('guard', false);
    expect(combat.playerInCombat).toBe(false);
  });
});
