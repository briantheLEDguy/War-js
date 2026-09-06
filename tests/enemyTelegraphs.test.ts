import * as THREE from 'three';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Combat } from '../src/game/Combat';
import { Enemy } from '../src/game/Enemy';
import { VfxLayer } from '../src/game/animation/VfxLayer';
import { enemyAttackContains, type EnemyCastState } from '../src/game/enemyAttackTelegraph';
import { EnemyAttackTelegraphVfx } from '../src/game/EnemyAttackTelegraphVfx';
import type { EnemySpawn } from '../src/world/ZoneLoader';
import type { Terrain } from '../src/world/Terrain';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, makePlayer, resetGameStore } from './testUtils';

describe('readable enemy special attacks', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ playerDead: false, quests: [] });
    useGameStore.getState().setCharacter(makeCharacter({ level: 8, health: 100, maxHealth: 100 }));
  });

  test('captain commits to a visible cone and lets a player sidestep without taking an ordinary hit', () => {
    const { combat, enemy, scene, vfx } = encounter('captain');
    const player = makePlayer({ position: { x: 0, y: 0, z: 3 } });
    combat.tickEnemies(0.1, 1000, player);
    const cast = useGameStore.getState().enemies[0].activeCast!;
    const origin = enemy.position.clone();
    const rotation = enemy.object.rotation.y;
    expect(cast).toMatchObject({ label: 'Line Breaker', startedAt: 1000, dueAt: 2200, progress: 0 });
    expect(scene.children).toHaveLength(1);
    expect(cast.responseCue).toContain('cone');
    expect(useGameStore.getState().character?.health).toBe(100);

    player.position.x = 3;
    player.position.z = 1;
    expect(enemyAttackContains(cast.footprint, player.position)).toBe(false);
    combat.tickEnemies(0.6, 1600, player);
    expect(enemy.position.equals(origin)).toBe(true);
    expect(enemy.object.rotation.y).toBe(rotation);
    expect(useGameStore.getState().enemies[0].activeCast?.progress).toBeCloseTo(0.5);
    expect(useGameStore.getState().character?.health).toBe(100);

    combat.tickEnemies(0.6, 2200, player);
    expect(useGameStore.getState().character?.health).toBe(100);
    expect(enemy.pendingAbility).toBeNull();
    expect(useGameStore.getState().enemies[0].activeCast).toBeNull();
    vfx.update(0.016);
    expect(scene.children).toHaveLength(0);
  });

  test('remaining in the captain cone takes exactly one special hit after its windup', () => {
    const { combat } = encounter('captain');
    const player = makePlayer({ position: { x: 0, y: 0, z: 2 } });
    combat.tickEnemies(0.1, 1000, player);
    combat.tickEnemies(1, 2000, player);
    expect(useGameStore.getState().character?.health).toBe(100);
    combat.tickEnemies(0.2, 2200, player);
    const state = useGameStore.getState();
    expect(state.character!.health).toBeLessThan(100);
    expect(state.floatingDamage).toHaveLength(1);
    expect(state.playerStatusEffects.some((effect) => effect.label === 'Pressed')).toBe(true);
    expect(state.enemies[0].activeCast).toBeNull();
  });

  test('caster circle stays at the initial target position and can be dodged', () => {
    const { combat } = encounter('caster');
    const player = makePlayer({ position: { x: 0, y: 0, z: 10 } });
    combat.tickEnemies(0.1, 1000, player);
    const cast = useGameStore.getState().enemies[0].activeCast!;
    expect(cast.footprint).toMatchObject({ shape: 'circle', origin: { x: 0, y: 0, z: 10 }, radius: 2.4 });
    player.position.x = 3;
    combat.tickEnemies(1.1, 2100, player);
    expect(useGameStore.getState().character?.health).toBe(100);
    expect(useGameStore.getState().enemies[0].activeCast).toBeNull();
  });

  test('combat projects its marker through the enemy ground resolver', () => {
    const terrainHeight = (x: number, z: number) => 2 + x * 0.2 + z * 0.4;
    const { combat, scene } = encounter('captain', {}, terrainHeight);
    combat.tickEnemies(0.1, 1000, makePlayer({ position: { x: 0, y: 2.8, z: 2 } }));
    const root = scene.children[0];
    const mesh = root.children[0] as THREE.Mesh;
    const positions = mesh.geometry.getAttribute('position');
    for (let i = 0; i < positions.count; i++) {
      expect(positions.getY(i) + root.position.y).toBeCloseTo(
        terrainHeight(positions.getX(i) + root.position.x, positions.getZ(i) + root.position.z) + 0.08, 5,
      );
    }
  });

  test.each(['silence', 'stagger'] as const)('%s interrupts the cast and removes its ground marker', (kind) => {
    const { combat, enemy, scene, vfx } = encounter('guard');
    const player = makePlayer({ position: { x: 0, y: 0, z: 2 } });
    combat.tickEnemies(0.1, 1000, player);
    useGameStore.getState().updateEnemy(enemy.spawn.id, {
      statusEffects: [{ id: 'interrupt', label: 'Interrupt', kind, expiresAt: 4000, sourceAbilityId: 'test' }],
    });
    combat.tickEnemies(0.5, 1500, player);
    expect(enemy.pendingAbility).toBeNull();
    expect(useGameStore.getState().enemies[0].activeCast).toBeNull();
    expect(scene.children[0].visible).toBe(false);
    vfx.update(0.016);
    expect(scene.children).toHaveLength(0);
    enemy.attackCooldown = 999;
    combat.tickEnemies(0.5, 2000, player);
    expect(useGameStore.getState().character?.health).toBe(100);
  });

  test.each(['player death', 'enemy death', 'leash', 'aggro drop'] as const)('%s clears pending casts and telegraphs', (cause) => {
    const { combat, enemy, scene, vfx } = encounter('guard');
    const player = makePlayer({ position: { x: 0, y: 0, z: 2 } });
    combat.tickEnemies(0.1, 1000, player);
    if (cause === 'player death') useGameStore.getState().setPlayerDead(true);
    if (cause === 'enemy death') useGameStore.getState().updateEnemy(enemy.spawn.id, { alive: false, health: 0 });
    if (cause === 'leash') enemy.position.z = 30;
    if (cause === 'aggro drop') player.position.z = 30;
    combat.tickEnemies(0.1, 1100, player);
    expect(enemy.pendingAbility).toBeNull();
    expect(useGameStore.getState().enemies[0].activeCast).toBeNull();
    vfx.update(0.016);
    expect(scene.children).toHaveLength(0);
  });

  test.each([
    ['raider', 15_000], ['beast', 15_000], ['guard', 30_000], ['caster', 30_000], ['captain', 30_000],
    ['dummy', 5000],
  ] as const)('%s stays defeated for its recovery window before respawning', (archetype, delay) => {
    const { combat, enemy } = encounter(archetype === 'dummy' ? 'raider' : archetype,
      archetype === 'dummy' ? { name: 'Training Dummy', aggroRange: 0 } : {});
    useGameStore.getState().updateEnemy(enemy.spawn.id, { health: 1 });
    useGameStore.getState().setTarget(enemy.spawn.id);
    expect(combat.tryAbility(0, makePlayer(), 1000)).toBe(true);
    combat.tickAbilityImpacts(2000);
    expect(useGameStore.getState().enemies[0].alive).toBe(false);
    expect(enemy.respawnAt).toBe(2000 + delay);
    combat.tickRespawns(2000 + delay - 1);
    expect(useGameStore.getState().enemies[0].alive).toBe(false);
    combat.tickRespawns(2000 + delay);
    expect(useGameStore.getState().enemies[0]).toMatchObject({ alive: true, health: 100, activeCast: null });
    expect(enemy.pendingAbility).toBeNull();
  });

  test('an objective-bound raider stays defeated for thirty seconds so its partner can be cleared', () => {
    const { combat, enemy } = encounter('raider');
    enemy.objectiveDefender = true;
    useGameStore.getState().updateEnemy(enemy.spawn.id, { health: 1 });
    useGameStore.getState().setTarget(enemy.spawn.id);
    expect(combat.tryAbility(0, makePlayer(), 1000)).toBe(true);
    combat.tickAbilityImpacts(2000);
    expect(enemy.respawnAt).toBe(32_000);
    combat.tickRespawns(17_000);
    expect(useGameStore.getState().enemies[0].alive).toBe(false);
    combat.tickRespawns(32_000);
    expect(useGameStore.getState().enemies[0].alive).toBe(true);
  });
});

describe('ground-projected attack geometry', () => {
  test.each(['cone', 'circle'] as const)('%s interior and border follow sloped terrain with bounded geometry and dispose cleanly', (shape) => {
    const origin = { x: 10, y: 2, z: 20 };
    const cast: EnemyCastState = {
      abilityId: 'test', label: 'Test', startedAt: 1000, dueAt: 2000, progress: 0, responseCue: 'Move',
      footprint: shape === 'cone'
        ? { shape, origin, rotationY: 0.7, range: 5, halfAngleRad: Math.PI / 3 }
        : { shape, origin, radius: 2.4 },
    };
    const slope = (x: number, z: number) => 3 + x * 0.25 + z * 0.5;
    const sampleHeight = vi.fn(slope);
    const scene = new THREE.Scene();
    const layer = new VfxLayer(scene);
    const telegraph = new EnemyAttackTelegraphVfx(cast, sampleHeight);
    layer.spawn(telegraph);
    const root = scene.children[0];
    const mesh = root.children[0] as THREE.Mesh;
    const border = root.children[1] as THREE.LineLoop;
    expect(sampleHeight.mock.calls.length).toBeLessThanOrEqual(300);
    expect(mesh.geometry.getAttribute('position').count).toBeLessThanOrEqual(300);
    expect(mesh.geometry.getIndex()!.count).toBeLessThanOrEqual(1600);
    expect(border.geometry.getAttribute('position').count).toBeLessThanOrEqual(64);
    for (const part of [mesh, border]) {
      const positions = part.geometry.getAttribute('position');
      for (let i = 0; i < positions.count; i++) {
        const worldX = positions.getX(i) + root.position.x;
        const worldZ = positions.getZ(i) + root.position.z;
        expect(positions.getY(i) + root.position.y).toBeCloseTo(slope(worldX, worldZ) + 0.08, 5);
      }
    }
    const disposeMesh = vi.spyOn(mesh.geometry, 'dispose');
    const disposeBorder = vi.spyOn(border.geometry, 'dispose');
    const disposeFill = vi.spyOn(mesh.material as THREE.Material, 'dispose');
    const disposeOutline = vi.spyOn(border.material as THREE.Material, 'dispose');
    telegraph.cancel();
    layer.update(0.016);
    expect(scene.children).toHaveLength(0);
    expect(disposeMesh).toHaveBeenCalledTimes(1);
    expect(disposeBorder).toHaveBeenCalledTimes(1);
    expect(disposeFill).toHaveBeenCalledTimes(1);
    expect(disposeOutline).toHaveBeenCalledTimes(1);
  });
});

function encounter(archetype: NonNullable<EnemySpawn['archetype']>, overrides: Partial<EnemySpawn> = {}, groundHeight = (_x: number, _z: number) => 0) {
  const spawn: EnemySpawn = {
    id: 'enemy', name: 'Enemy', level: 3, x: 0, z: 0, maxHealth: 100,
    aggroRange: 20, attackRange: 2.5, attackDamage: 8, moveSpeed: 3, archetype, ...overrides,
  };
  const enemy = new Enemy(spawn, { heightAt: groundHeight } as unknown as Terrain);
  enemy.object = new THREE.Object3D();
  const scene = new THREE.Scene();
  const vfx = new VfxLayer(scene);
  const combat = new Combat();
  combat.setVfxLayer(vfx);
  combat.registerEnemy(enemy);
  useGameStore.getState().setEnemies([{
    id: spawn.id, name: spawn.name, level: spawn.level, health: 100, maxHealth: 100,
    position: { x: 0, y: 0, z: 0 }, alive: true,
  }]);
  return { combat, enemy, scene, vfx };
}
