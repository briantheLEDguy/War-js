import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { Game } from '../src/game/Game';
import { WorldEditorRuntime } from '../src/world/editor/WorldEditorRuntime';
import { spawnProps, type WorldCollider } from '../src/world/Props';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Terrain } from '../src/world/Terrain';
import type { WorldPropObject } from '../src/services/types';

describe('camera world integration', () => {
  test('keeps obstacles above the player but excludes open gates and replaced static colliders', () => {
    const elevated: WorldCollider = { id: 'roof', x: 0, z: 0, width: 4, depth: 4, rotY: 0, minY: 4, maxY: 5, blocksWhen: 'always' };
    const gate = { ...elevated, id: 'gate', blocksWhen: 'closed' as const, interactionId: 'gate' };
    const replaced = { ...elevated, id: 'old', sourceObjectId: 'edited' };
    const game = Object.assign(Object.create(Game.prototype), {
      player: { position: new THREE.Vector3() },
      cameraColliders: [elevated, gate, replaced],
      isStaticSourceSuppressed: (id?: string) => id === 'edited',
      findGateById: () => ({ isOpen: true }),
    }) as { getActiveCameraColliders(): WorldCollider[]; isColliderActive(c: WorldCollider): boolean };
    expect(game.getActiveCameraColliders()).toEqual([elevated]);
    expect(game.isColliderActive(elevated)).toBe(false);
  });

  test('includes hidden instancing sources, visible editor props and voxel terrain, excluding helpers/deleted objects', () => {
    const source = new THREE.Group();
    source.visible = false;
    const prop = new THREE.Group();
    const voxel = new THREE.Group();
    const editor = Object.assign(Object.create(WorldEditorRuntime.prototype), {
      staticObjects: new Map([
        ['source', { object: source, definition: { type: 'prop' } }],
        ['hidden', { object: new THREE.Group(), definition: { type: 'prop', hidden: true } }],
      ]),
      spawned: new Map([
        ['prop', { object: prop, definition: { type: 'prop' } }],
        ['helper', { object: new THREE.Group(), definition: { type: 'collider' } }],
      ]),
      voxelRuntime: { object: voxel },
    }) as WorldEditorRuntime;
    expect(editor.getCameraObjects()).toEqual([source, prop, voxel]);
  });

  test('derives missing camera height bounds from a transformed prop without changing movement bounds', async () => {
    const model = new THREE.Mesh(new THREE.BoxGeometry(2, 4, 2), new THREE.MeshBasicMaterial());
    const loader = { loadModel: async () => model } as unknown as AssetLoader;
    const terrain = { heightAt: () => 10 } as unknown as Terrain;
    const result = await spawnProps(new THREE.Scene(), loader, terrain, [{
      kind: 'building', model: 'fixture.glb', x: 0, z: 0, y: 3, scaleY: 2,
      colliders: [{ width: 2, depth: 2 }],
    }]);
    expect(result.cameraColliders[0].minY).toBe(9);
    expect(result.cameraColliders[0].maxY).toBe(17);
    expect(result.colliders[0].minY).toBeUndefined();
    expect(result.colliders[0].maxY).toBeUndefined();
  });

  test('preserves finite camera heights after GM transforms rebuild collision', () => {
    const object = new THREE.Mesh(new THREE.BoxGeometry(2, 4, 2), new THREE.MeshBasicMaterial());
    object.position.y = 6;
    const definition: WorldPropObject = {
      id: 'edited-prop', type: 'prop', kind: 'building', createdAt: 0, updatedAt: 0,
      transform: {
        position: { x: 0, y: 6, z: 0 }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 },
      },
      colliders: [{ width: 2, depth: 2 }],
    };
    const editor = Object.assign(Object.create(WorldEditorRuntime.prototype), {
      document: { objects: [definition] },
      spawned: new Map([['edited-prop', { object, definition }]]),
      staticObjects: new Map(),
    }) as { rebuildStandaloneCollision(): void; getCameraColliders(): WorldCollider[]; getColliders(): WorldCollider[] };
    editor.rebuildStandaloneCollision();
    expect(editor.getCameraColliders()[0]).toMatchObject({ minY: 4, maxY: 8 });
    expect(editor.getColliders()[0].minY).toBeUndefined();
  });
});
