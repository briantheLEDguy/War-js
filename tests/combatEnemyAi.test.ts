import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { Combat } from '../src/game/Combat';
import { Enemy } from '../src/game/Enemy';
import type { EnemySpawn } from '../src/world/ZoneLoader';
import type { Terrain } from '../src/world/Terrain';
import { useGameStore, type CombatStatusEffect } from '../src/state/gameStore';
import { makeCharacter, makePlayer, resetGameStore } from './testUtils';

describe('enemy archetype AI', () => {
  test.each([
    { label: 'hostile enemies', aggroRange: 12, expectedAggro: true },
    { label: 'passive training targets', aggroRange: 0, expectedAggro: false },
    { label: 'targets without aggression settings', aggroRange: undefined, expectedAggro: false },
  ])('ranged damage gives $label the correct aggression state', ({ aggroRange, expectedAggro }) => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter({ className: 'Ember Arcanist' }));
    const combat = new Combat();
    const enemy = runtimeEnemy({ id: 'ranged-target', x: 0, z: 22, aggroRange });
    combat.registerEnemy(enemy);
    useGameStore.getState().setEnemies([enemyState(enemy)]);
    useGameStore.getState().setTarget(enemy.spawn.id);
    const player = makePlayer();
    expect(combat.tryAbility(0, player, 1000)).toBe(true);
    combat.tickAbilityImpacts(3000);
    expect(useGameStore.getState().enemies[0].health).toBeGreaterThan(0);
    expect(useGameStore.getState().enemies[0].health).toBeLessThan(enemy.spawn.maxHealth);
    expect(enemy.aggroed).toBe(expectedAggro);
    combat.tickEnemies(0.1, 3100, player);
    expect(enemy.aggroed).toBe(expectedAggro);
  });

  test('melee enemies chase and damage the player in range', () => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter({ health: 100, maxHealth: 100 }));
    const combat = new Combat();
    const enemy = runtimeEnemy({
      id: 'raider',
      archetype: 'raider',
      x: 0,
      z: 5,
      aggroRange: 10,
      attackRange: 2,
      attackDamage: 10,
      moveSpeed: 5,
    });
    enemy.abilityCooldown = 999;
    combat.registerEnemy(enemy);
    useGameStore.getState().setEnemies([enemyState(enemy)]);

    combat.tickEnemies(0.5, 1_000, makePlayer());
    expect(enemy.position.z).toBeLessThan(5);
    expect(useGameStore.getState().enemies[0].position.z).toBeLessThan(5);

    combat.tickEnemies(1, 2_000, makePlayer());
    expect(useGameStore.getState().character?.health).toBeLessThan(100);
  });

  test('caster enemies hold preferred range and resolve a cast ability', () => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter({ health: 120, maxHealth: 120 }));
    const combat = new Combat();
    const enemy = runtimeEnemy({
      id: 'caster',
      archetype: 'caster',
      x: 0,
      z: 5,
      aggroRange: 20,
      attackRange: 16,
      preferredRange: 12,
      moveSpeed: 4,
    });
    combat.registerEnemy(enemy);
    useGameStore.getState().setEnemies([enemyState(enemy)]);

    combat.tickEnemies(1, 1_000, makePlayer());
    expect(enemy.position.z).toBeGreaterThan(5);
    expect(enemy.pendingAbility?.abilityId).toBe('caster_rift_bolt');

    combat.tickEnemies(1.1, 2_100, makePlayer());
    expect(useGameStore.getState().character?.health).toBeLessThan(120);
    expect(useGameStore.getState().playerStatusEffects.some((effect) => effect.kind === 'debuff')).toBe(true);
  });

  test('root, stagger, and silence statuses block enemy movement or casts', () => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter({ health: 120, maxHealth: 120 }));
    const combat = new Combat();
    const rooted = runtimeEnemy({
      id: 'rooted',
      archetype: 'raider',
      x: 0,
      z: 8,
      aggroRange: 20,
      moveSpeed: 4,
    });
    rooted.abilityCooldown = 999;
    combat.registerEnemy(rooted);
    useGameStore.getState().setEnemies([
      enemyState(rooted, [status('root', 3_000)]),
    ]);

    combat.tickEnemies(1, 1_000, makePlayer());
    expect(rooted.position.z).toBe(8);

    const silenced = runtimeEnemy({
      id: 'silenced',
      archetype: 'caster',
      x: 0,
      z: 10,
      aggroRange: 20,
      attackRange: 16,
      preferredRange: 12,
    });
    combat.registerEnemy(silenced);
    useGameStore.getState().setEnemies([
      enemyState(silenced, [status('silence', 3_000)]),
    ]);

    combat.tickEnemies(0.5, 1_000, makePlayer());
    expect(silenced.pendingAbility).toBeNull();

    useGameStore.getState().setEnemies([enemyState(silenced)]);
    combat.tickEnemies(0.1, 1_100, makePlayer());
    expect(silenced.pendingAbility).not.toBeNull();
    useGameStore.getState().setEnemies([
      enemyState(silenced, [status('stagger', 3_000)]),
    ]);
    combat.tickEnemies(0.6, 1_600, makePlayer());
    expect(silenced.pendingAbility).toBeNull();
    expect(useGameStore.getState().character?.health).toBe(120);
  });

  test('leashing resets position, health, cooldowns, and pending casts', () => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter());
    const combat = new Combat();
    const enemy = runtimeEnemy({
      id: 'leashed',
      archetype: 'guard',
      x: 0,
      z: 0,
      maxHealth: 160,
      aggroRange: 50,
      moveSpeed: 4,
    });
    combat.registerEnemy(enemy);
    useGameStore.getState().setEnemies([enemyState(enemy)]);
    combat.tickEnemies(0.1, 900, makePlayer({ position: { x: 0, y: 0, z: 1 } }));
    expect(enemy.pendingAbility).not.toBeNull();
    enemy.position.set(0, 0, 30);
    enemy.object.position.copy(enemy.position);
    enemy.aggroed = true;
    enemy.attackCooldown = 3;
    enemy.abilityCooldown = 4;
    useGameStore.getState().setEnemies([{
      ...enemyState(enemy),
      health: 20,
      position: { x: 0, y: 0, z: 30 },
    }]);

    combat.tickEnemies(0.1, 1_000, makePlayer({ position: { x: 0, y: 0, z: 0 } }));

    expect(enemy.position.z).toBe(0);
    expect(enemy.aggroed).toBe(false);
    expect(enemy.attackCooldown).toBe(0);
    expect(enemy.abilityCooldown).toBe(0);
    expect(enemy.pendingAbility).toBeNull();
    expect(useGameStore.getState().enemies[0]).toMatchObject({
      health: 160,
      position: { x: 0, y: 0, z: 0 },
      activeCast: null,
    });
  });
});

function runtimeEnemy(overrides: Partial<EnemySpawn>): Enemy {
  const spawn: EnemySpawn = {
    id: 'enemy',
    name: 'Enemy',
    level: 3,
    x: 0,
    z: 0,
    maxHealth: 100,
    aggroRange: 12,
    attackRange: 2.5,
    attackDamage: 8,
    moveSpeed: 3,
    ...overrides,
  };
  const enemy = new Enemy(spawn, { heightAt: () => 0 } as unknown as Terrain);
  enemy.object = new THREE.Object3D();
  enemy.position.set(spawn.x, 0, spawn.z);
  enemy.homePosition.copy(enemy.position);
  enemy.object.position.copy(enemy.position);
  return enemy;
}

function enemyState(enemy: Enemy, statusEffects: CombatStatusEffect[] = []) {
  return {
    id: enemy.spawn.id,
    name: enemy.spawn.name,
    level: enemy.spawn.level,
    health: enemy.spawn.maxHealth,
    maxHealth: enemy.spawn.maxHealth,
    position: { x: enemy.position.x, y: enemy.position.y, z: enemy.position.z },
    alive: true,
    statusEffects,
  };
}

function status(kind: CombatStatusEffect['kind'], expiresAt: number): CombatStatusEffect {
  return {
    id: `${kind}-test`,
    label: kind,
    kind,
    expiresAt,
    sourceAbilityId: 'test',
  };
}
