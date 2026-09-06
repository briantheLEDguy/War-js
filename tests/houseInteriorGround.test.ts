import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { Game } from '../src/game/Game';
import { FollowCamera } from '../src/game/Camera';
import { HouseInteriorRuntime } from '../src/game/HouseInteriorRuntime';
import { Player } from '../src/game/Player';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Input } from '../src/game/Input';
import type { Terrain } from '../src/world/Terrain';
import { makeCharacter } from './testUtils';

describe('off-map house floors in an elevated capital', () => {
  test('keeps the player and camera inside the room after entry without flattening outdoor terrain', async () => {
    const scene = new THREE.Scene(), runtime = new HouseInteriorRuntime(scene);
    const loader = {
      loadModel: async () => new THREE.Group(),
      resolveCharacterModel: async () => null,
      loadModelFull: async () => ({ object: new THREE.Group(), animations: [] }),
    } as unknown as AssetLoader;
    await runtime.loadCityRooms(loader);
    const terrain = { heightAt: () => 42 } as Terrain;
    const character = makeCharacter();
    // Construct field-bound resolvers without starting a renderer or game loop.
    const game = Object.assign(new Game({} as HTMLElement, character), { terrain, houseInteriors: runtime }) as unknown as {
      groundHeightAt(x: number, z: number, y?: number): number;
      cameraGroundHeightAt(x: number, z: number): number;
    };
    const camera = new FollowCamera(new EventTarget() as HTMLElement, 16 / 9);
    camera.setIndoorMode(true);
    const player = new Player(character, terrain, game.groundHeightAt);
    player.object = new THREE.Group();
    const input = { touchMoveX: 0, touchMoveZ: 0, isBindingDown: () => false,
      wasBindingPressed: () => false } as unknown as Input;

    for (const variant of ['small', 'large', 'tavern', 'shop', 'chapel', 'civic'] as const) {
      const room = runtime.enter(variant);
      player.teleportTo(room.spawn, room.spawn.rotationY);
      player.update(1 / 30, input, camera);
      expect(player.position.y, variant).toBe(room.anchor.y);
      camera.update(player.position, input, runtime.getCameraColliders(), game.cameraGroundHeightAt);
      const focus = player.position.clone().add(new THREE.Vector3(0, .9, 0));
      expect(camera.camera.position.distanceTo(focus), variant).toBeGreaterThan(1);
      expect(camera.camera.position.y, variant).toBeLessThan(room.anchor.y + room.height);
      expect(game.groundHeightAt(0, 0), 'outdoor actors keep their terrain').toBe(42);
      expect(game.cameraGroundHeightAt(0, 0)).toBe(42);
    }
    runtime.deactivate();
    expect(game.groundHeightAt(player.position.x, player.position.z)).toBe(42);
    expect(game.cameraGroundHeightAt(player.position.x, player.position.z)).toBe(42);
    camera.dispose(); runtime.dispose(scene);
  });

  test('only supplies a floor for the active room and its wall thickness', () => {
    const runtime = new HouseInteriorRuntime(new THREE.Scene());
    expect(runtime.getFloorHeightAt(960, 960)).toBeNull();
    const room = runtime.enter('small');
    expect(runtime.getFloorHeightAt(room.spawn.x, room.spawn.z)).toBe(0);
    expect(runtime.getFloorHeightAt(room.anchor.x + room.width / 2 + 1, room.anchor.z)).toBeNull();
    expect(runtime.getFloorHeightAt(1010, 960)).toBeNull();
    runtime.deactivate();
    expect(runtime.getFloorHeightAt(room.spawn.x, room.spawn.z)).toBeNull();
  });
});
