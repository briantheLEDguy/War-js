import * as THREE from 'three';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { WorldEditorRuntime, propCollidersFromObject, propWalkablesFromObject } from '../src/world/editor/WorldEditorRuntime';
import type { WorldEditDocument, WorldPropObject } from '../src/services/types';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Terrain } from '../src/world/Terrain';

const prop = (): WorldPropObject => ({ id: 'map-stairs', type: 'prop', kind: 'aegis_stairs', createdAt: 0, updatedAt: 0,
  transform: { position: { x: 10, y: 4, z: 20 }, rotation: { x: 0, y: Math.PI / 2, z: 0 }, scale: { x: 2, y: 3, z: 4 } },
  colliders: [{ x: 2, z: 3, width: 1, depth: 2, minY: 1, maxY: 2 }],
  walkableSurfaces: [{ x: 2, z: 3, width: 1, depth: 2, fromY: 1, toY: 6 }] });
const document = (): WorldEditDocument => ({ schemaVersion: 1, versionId: 'draft', zoneId: 'aegis_capital', status: 'draft',
  createdAt: 0, updatedAt: 0, palette: { materials: [] }, objects: [], voxelChunks: [] } as WorldEditDocument);

afterEach(() => vi.unstubAllGlobals());
describe('GM object editing', () => {
  test('rotated and scaled collision offsets match map spawning, including height bounds', () => {
    const collider = propCollidersFromObject(prop())[0];
    const walkable = propWalkablesFromObject(prop())[0];
    expect(collider.x).toBeCloseTo(-2);
    expect(collider.z).toBeCloseTo(24);
    expect(collider.minY).toBe(7);
    expect(collider.maxY).toBe(10);
    expect(walkable.x).toBeCloseTo(collider.x);
    expect(walkable.z).toBeCloseTo(collider.z);
    expect(walkable.toY).toBe(22);
  });
  test('map objects can be removed, reloaded, restored and undone through the object list', async () => {
    vi.stubGlobal('window', new EventTarget());
    const element = Object.assign(new EventTarget(), { style: {}, ownerDocument: new EventTarget() });
    const runtime = new WorldEditorRuntime({ scene: new THREE.Scene(), camera: new THREE.PerspectiveCamera(),
      domElement: element as unknown as HTMLElement, loader: {} as AssetLoader,
      terrain: { heightAt: () => 0 } as Terrain, groundHeightAt: () => 0 });
    const object = new THREE.Group(); // Even invisible collision-only map objects must be selectable by ID.
    runtime.registerStaticObject(prop(), object);
    await runtime.loadDocument(document(), true);
    runtime.selectObject('map-stairs');
    expect(runtime.deleteSelectedObject()).toBe(true);
    expect(object.visible).toBe(false);
    expect(runtime.isStaticObjectSuppressed('map-stairs')).toBe(true);
    const saved = runtime.currentDocument!;
    await runtime.loadDocument(saved, true);
    expect(runtime.objectList[0].hidden).toBe(true);
    runtime.selectObject('map-stairs');
    expect(runtime.restoreSelectedObject()).toBe(true);
    expect(object.visible).toBe(true);
    expect(runtime.getColliders()).toHaveLength(1);
    runtime.undo();
    await vi.waitFor(() => expect(object.visible).toBe(false));
    runtime.redo();
    await vi.waitFor(() => expect(object.visible).toBe(true));
    const heightfield = new THREE.Group(), importedTerrain = new THREE.Group();
    runtime.registerStaticObject({ ...prop(), id: 'heightfield', kind: 'terrain' }, heightfield);
    runtime.registerStaticObject({ ...prop(), id: 'imported-terrain', kind: 'terrain', model: 'cave.glb' }, importedTerrain);
    expect(runtime.getCameraObjects()).not.toContain(heightfield);
    expect(runtime.getCameraObjects()).toContain(importedTerrain);
    runtime.dispose();
  });
  test('new gate stamps preserve independent interaction IDs, lift visuals, deletion and reload', async () => {
    vi.stubGlobal('window', new EventTarget());
    const element = Object.assign(new EventTarget(), { style: {}, ownerDocument: new EventTarget() });
    const loader = { resolveStaticModel: async (_key: string, model: string) => model,
      loadModel: async (_model: string, fallback: () => THREE.Object3D) => fallback(),
      loadModelWithAnimations: async (_model: string, fallback: () => THREE.Object3D) => ({ object: fallback(), animations: [] }) };
    const runtime = new WorldEditorRuntime({ scene: new THREE.Scene(), camera: new THREE.PerspectiveCamera(),
      domElement: element as unknown as HTMLElement, loader: loader as unknown as AssetLoader,
      terrain: { heightAt: () => 0 } as Terrain, groundHeightAt: () => 0 });
    await runtime.loadDocument(document(), true);
    runtime.setSettings({ prefabKind: 'aegis_portcullis' });
    await runtime.stampPrefabAtPlayer({ x: 0, y: 0, z: 0 });
    await runtime.stampPrefabAtPlayer({ x: 20, y: 0, z: 0 });
    const objects = runtime.currentDocument!.objects as WorldPropObject[];
    expect(objects).toHaveLength(2);
    expect(objects[0].interaction!.id).not.toBe(objects[1].interaction!.id);
    expect(runtime.getGates()).toHaveLength(2);
    for (const gate of runtime.getGates()) {
      expect(gate.isOpen).toBe(false);
      expect(gate.fallbackVisual).not.toBeNull();
      expect(gate.object.children.some(child => child.userData.gateLift && child.position.y === child.userData.gateLiftBaseY)).toBe(true);
    }
    runtime.selectObject(objects[0].id);
    expect(runtime.deleteSelectedObject()).toBe(true);
    expect(runtime.getGates()).toHaveLength(1);
    await runtime.loadDocument(runtime.currentDocument, true);
    expect(runtime.getGates()).toHaveLength(1);
    expect(runtime.currentDocument!.objects[0].id).toBe(objects[1].id);
    runtime.dispose();
  });
});
