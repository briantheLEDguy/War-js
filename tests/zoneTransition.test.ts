import { describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { Player } from '../src/game/Player';
import { defaultZoneSpawnPoint } from '../src/data/zoneRouting';
import type { Terrain } from '../src/world/Terrain';
import type { FollowCamera } from '../src/game/Camera';
import type { Input } from '../src/game/Input';
import {
  resolveZoneEntryPoint,
  zoneTransitionCanArm,
} from '../src/game/ZoneTransition';
import { makeCharacter } from './testUtils';

describe('zone transition helpers', () => {
  test('uses the character position before the zone default spawn', () => {
    expect(resolveZoneEntryPoint(
      { x: 105, y: 7, z: -12 },
      { x: 0, y: 0, z: -40 },
    )).toEqual({ x: 105, y: 7, z: -12 });
  });

  test('falls back to the zone spawn when the character position is invalid', () => {
    expect(resolveZoneEntryPoint(
      { x: Number.NaN, y: 4, z: 8 },
      { x: 0, y: 0, z: -40 },
    )).toEqual({ x: 0, y: 0, z: -40 });
  });

  test('falls back to world origin when no finite spawn exists', () => {
    expect(resolveZoneEntryPoint(undefined, undefined)).toEqual({ x: 0, y: 0, z: 0 });
  });

  test('uses safe generated spawn fallbacks for fortress and lair zones', () => {
    expect(defaultZoneSpawnPoint('aegis_gate_fortress')).toEqual({ x: 0, y: 0, z: -118 });
    expect(defaultZoneSpawnPoint('rift_gate_fortress')).toEqual({ x: 0, y: 0, z: -118 });
    expect(defaultZoneSpawnPoint('wardens_hollow')).toEqual({ x: 0, y: 0, z: -58 });
    expect(defaultZoneSpawnPoint('aegis_capital')).toEqual({ x: 0, y: 0, z: -40 });
  });

  test('does not arm portal triggers until the player is clear after grace', () => {
    expect(zoneTransitionCanArm(999, 1000, false)).toBe(false);
    expect(zoneTransitionCanArm(1000, 1000, true)).toBe(false);
    expect(zoneTransitionCanArm(1000, 1000, false)).toBe(true);
  });

  test('moves the active player object for same-zone GM teleports', () => {
    const player = new Player(
      makeCharacter(),
      { heightAt: () => 0 } as unknown as Terrain,
    );
    player.object = new THREE.Object3D();

    player.teleportTo({ x: 12, y: 3, z: -8 }, Math.PI / 2);

    expect(player.position.toArray()).toEqual([12, 3, -8]);
    expect(player.object.position.toArray()).toEqual([12, 3, -8]);
    expect(player.rotationY).toBeCloseTo(Math.PI / 2);
    expect(player.object.rotation.y).toBeCloseTo(Math.PI / 2);
  });

  test('GM flying mode uses Q and E for vertical movement without collision snap', () => {
    const player = new Player(
      makeCharacter(),
      { heightAt: () => 0 } as unknown as Terrain,
    );
    player.object = new THREE.Object3D();
    player.teleportTo({ x: 0, y: 10, z: 0 }, 0);
    const resolveCollision = vi.fn();

    player.update(
      1,
      makeInput(['KeyE']),
      makeCamera(),
      resolveCollision,
      2,
      { flying: true },
    );

    expect(player.position.y).toBeCloseTo(22);
    expect(player.object.position.y).toBeCloseTo(22);
    expect(resolveCollision).not.toHaveBeenCalled();

    player.update(
      1,
      makeInput(['KeyQ']),
      makeCamera(),
      resolveCollision,
      2,
      { flying: true },
    );

    expect(player.position.y).toBeCloseTo(10);
  });
});

function makeInput(down: string[]): Input {
  const keys = new Set(down);
  return {
    touchMoveX: 0,
    touchMoveZ: 0,
    mouseLeftDown: false,
    mouseRightDown: false,
    touchJumpThisFrame: false,
    isDown: (code: string) => keys.has(code),
    wasPressed: () => false,
  } as unknown as Input;
}

function makeCamera(): FollowCamera {
  return {
    yawAngle: 0,
    forwardYaw: 0,
  } as unknown as FollowCamera;
}
