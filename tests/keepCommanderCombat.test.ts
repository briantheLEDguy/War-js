import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { Combat } from '../src/game/Combat';
import { Enemy } from '../src/game/Enemy';
import { enemyAttackContains } from '../src/game/enemyAttackTelegraph';
import { useGameStore, type PlayerStatusEffect } from '../src/state/gameStore';
import type { Terrain } from '../src/world/Terrain';
import type { EnemySpawn } from '../src/world/ZoneLoader';
import { makeCharacter, makePlayer, resetGameStore } from './testUtils';

function commanderEncounter(health = 320) {
  const spawn: EnemySpawn = {
    id: 'commander', name: 'Keep Commander', level: 4, x: 0, z: 0, maxHealth: 320,
    archetype: 'captain', aggroRange: 20, attackRange: 2.5, attackDamage: 20, moveSpeed: 3,
    encounter: { type: 'keep_commander', objectiveId: 'keep', realm: 'riftbound', enrageHealthFraction: 0.35 },
  };
  const enemy = new Enemy(spawn, { heightAt: () => 0 } as unknown as Terrain);
  enemy.object = new THREE.Object3D();
  const combat = new Combat();
  combat.registerEnemy(enemy);
  useGameStore.getState().setEnemies([{
    id: spawn.id, name: spawn.name, level: spawn.level, health, maxHealth: spawn.maxHealth,
    position: { x: 0, y: 0, z: 0 }, alive: true, keepEncounter: { objectiveId: 'keep', phase: 'engaged' },
  }]);
  const player = makePlayer({ position: { x: 0, y: 0, z: 2 } });
  return { combat, enemy, player };
}

const cast = () => useGameStore.getState().enemies[0].activeCast!;

describe('keep commander attack runtime', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ playerDead: false, quests: [], chat: [], inventory: [] });
    useGameStore.getState().setCharacter(makeCharacter({ level: 8, health: 300, maxHealth: 300 }));
    vi.spyOn(Math, 'random').mockReturnValue(0);
  });
  afterEach(() => vi.restoreAllMocks());

  test('alternates a committed cone and commander-centered circle with distinct dodge opportunities', () => {
    const { combat, enemy, player } = commanderEncounter();
    combat.tickEnemies(0.1, 1000, player);
    const first = cast();
    const position = enemy.position.clone();
    const rotation = enemy.object.rotation.y;
    expect(first).toMatchObject({ label: 'Cleaving Order', startedAt: 1000, dueAt: 2200, footprint: { shape: 'cone', range: 6 } });
    player.position.x = 4;
    player.position.z = 0;
    combat.tickEnemies(0.6, 1600, player);
    expect(enemy.position.equals(position)).toBe(true);
    expect(enemy.object.rotation.y).toBe(rotation);
    expect(cast().progress).toBeCloseTo(0.5);
    expect(enemyAttackContains(first.footprint, player.position)).toBe(false);
    combat.tickEnemies(0.6, 2200, player);
    expect(useGameStore.getState().character!.health).toBe(300);

    enemy.abilityCooldown = 0;
    combat.tickEnemies(0, 2300, player);
    const second = cast();
    expect(second).toMatchObject({ label: 'Siege Pulse', startedAt: 2300, dueAt: 3800,
      footprint: { shape: 'circle', origin: { x: 0, y: 0, z: 0 }, radius: 6 } });
    player.position.x = 7;
    combat.tickEnemies(0.75, 3050, player);
    expect(enemy.position.equals(position)).toBe(true);
    expect(cast().footprint).toEqual(second.footprint);
    expect(enemyAttackContains(second.footprint, player.position)).toBe(false);
    combat.tickEnemies(0.75, 3800, player);
    expect(useGameStore.getState().character!.health).toBe(300);
    player.position.x = 0;
    player.position.z = 2;
    enemy.abilityCooldown = 0;
    combat.tickEnemies(0, 3900, player);
    expect(cast().label).toBe('Cleaving Order');
  });

  test.each([{ health: 320, recovery: 6.5 }, { health: 112, recovery: 4.225 }])(
    '$health health changes recovery while preserving both warning durations', ({ health, recovery }) => {
      const { combat, enemy, player } = commanderEncounter(health);
      combat.tickEnemies(0, 1000, player);
      expect(cast().dueAt - cast().startedAt).toBe(1200);
      expect(enemy.abilityCooldown).toBeCloseTo(recovery);
      combat.tickEnemies(1.2, 2200, player);
      enemy.abilityCooldown = 0;
      combat.tickEnemies(0, 2300, player);
      expect(cast().label).toBe('Siege Pulse');
      expect(cast().dueAt - cast().startedAt).toBe(1500);
      expect(enemy.abilityCooldown).toBeCloseTo(recovery);
    },
  );

  test.each(['silence', 'stagger'] as const)('%s interrupts the commander without adding a hidden ordinary hit', (kind) => {
    const { combat, enemy, player } = commanderEncounter();
    combat.tickEnemies(0.1, 1000, player);
    useGameStore.getState().updateEnemy('commander', {
      statusEffects: [{ id: 'interrupt', label: 'Interrupt', kind, expiresAt: 4000, sourceAbilityId: 'test' }],
    });
    combat.tickEnemies(0.6, 1600, player);
    expect(enemy.pendingAbility).toBeNull();
    expect(useGameStore.getState().enemies[0].activeCast).toBeNull();
    expect(useGameStore.getState().character!.health).toBe(300);
  });

  test('guard mitigates ordinary hits before finite shield absorption, and expires normally', () => {
    const { combat, enemy, player } = commanderEncounter();
    const statuses: PlayerStatusEffect[] = [
      { id: 'guard', label: 'Guard', kind: 'guard', magnitude: 0.5, expiresAt: 2000 },
      { id: 'shield', label: 'Shield', kind: 'shield', magnitude: 0.2, remainingAbsorb: 6, expiresAt: 5000 },
    ];
    useGameStore.setState({ playerStatusEffects: statuses });
    enemy.abilityCooldown = 99;
    combat.tickEnemies(0, 1000, player);
    expect(useGameStore.getState().character!.health).toBe(296);
    expect(useGameStore.getState().playerStatusEffects.map((effect) => effect.kind)).toEqual(['guard']);
    enemy.attackCooldown = 0;
    combat.tickEnemies(0, 2100, player);
    expect(useGameStore.getState().character!.health).toBe(276);
    expect(useGameStore.getState().playerStatusEffects).toEqual([]);
  });

  test('guard and shield also mitigate commander specials without double damage or reusable absorption', () => {
    const { combat, enemy, player } = commanderEncounter();
    useGameStore.setState({ playerStatusEffects: [
      { id: 'guard', label: 'Guard', kind: 'guard', magnitude: 0.5, expiresAt: 10_000 },
      { id: 'shield', label: 'Shield', kind: 'shield', remainingAbsorb: 5, expiresAt: 10_000 },
    ] });
    combat.tickEnemies(0.1, 1000, player);
    combat.tickEnemies(1.2, 2200, player);
    expect(useGameStore.getState().character!.health).toBe(297);
    expect(useGameStore.getState().floatingDamage).toHaveLength(1);
    expect(useGameStore.getState().playerStatusEffects.some((effect) => effect.kind === 'shield')).toBe(false);
    enemy.abilityCooldown = 0;
    combat.tickEnemies(0, 2300, player);
    combat.tickEnemies(1.5, 3800, player);
    expect(useGameStore.getState().character!.health).toBe(288);
    expect(useGameStore.getState().floatingDamage).toHaveLength(2);
  });
});
