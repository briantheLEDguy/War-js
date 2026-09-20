import * as THREE from 'three';
import { expect, test } from 'vitest';
import { Game } from '../src/game/Game';
import { Player } from '../src/game/Player';
import type { FollowCamera } from '../src/game/Camera';
import type { Input } from '../src/game/Input';
import type { Terrain } from '../src/world/Terrain';
import type { WorldCollider } from '../src/world/Props';
import { makeCharacter } from './testUtils';

test.each([
  ['thin elevated railing', .1, -.52, 1],
  ['closed gate', .45, -.7, 2],
  ['keep wall during accelerated movement', 2, -1.5, 4],
] as const)('local movement cannot cross %s during a 100 ms frame', (_, thickness, startX, multiplier) => {
  const character = makeCharacter(), terrain = { heightAt: () => 0 } as Terrain;
  const player = new Player(character, terrain, () => 0); player.object = new THREE.Group();
  player.teleportTo({ x: startX, y: 0, z: 0 });
  const collider: WorldCollider = { id: 'wall', x: 0, z: 0, width: thickness, depth: 12,
    rotY: 0, minY: .8, maxY: 2, blocksWhen: 'always' };
  const game = Object.assign(new Game({} as HTMLElement, character), { player, propColliders: [collider] }) as unknown as {
    resolvePlayerCollisions(position: THREE.Vector3, radius: number): void;
  };
  const input = { touchMoveX: 1, touchMoveZ: 0, isBindingDown: () => false, wasBindingPressed: () => false } as unknown as Input;
  const camera = { yawAngle: 0 } as FollowCamera;
  for (let frame = 0; frame < 12; frame++) player.update(.1, input, camera, game.resolvePlayerCollisions, multiplier);
  expect(player.position.x).toBeLessThanOrEqual(-thickness/2-.45+1e-8);
});
