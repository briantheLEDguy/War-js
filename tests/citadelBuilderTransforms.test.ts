import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { generateBuilderCatalog } from '../scripts/generate-builder-catalog.mjs';
import { spawnProps, type WorldCollider } from '../src/world/Props';
import { cityPositionBlocked } from '../src/world/CityNavigation';
import { createEmptyWorldEditDocument } from '../src/world/WorldEditValidation';
import { WorldEditorRuntime, propCollidersFromObject, propWalkablesFromObject } from '../src/world/editor/WorldEditorRuntime';
import { prefabDefinitionForKind } from '../src/world/editor/PrefabCatalog';
import { WorldEditLocal } from '../src/services/local/worldEditLocal';
import type { WorldPropObject } from '../src/services/types';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Terrain } from '../src/world/Terrain';

const zone = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8')) as ZoneDefinition;
const loader = {
  resolveStaticModel: async (_key: string, model: string) => model,
  loadModel: async (_model: string, fallback: () => THREE.Object3D) => fallback(),
} as unknown as AssetLoader;
const terrain = { heightAt: () => 7 } as Terrain;
const samples = {
  aegis_room: { doors: [[0, 6]], walls: [[0, -6], [-6, 0], [6, 0], [3.7, 6]] },
  aegis_mountain_vault: { doors: [[23.5, 18], [23.5, -24]], walls: [[23.5, 0], [-23.5, 18], [0, 41.5], [0, -41.5]] },
};
const cases = Object.keys(samples).flatMap(kind => [0, Math.PI / 2, Math.PI, -Math.PI / 2].map(yaw => ({ kind, yaw })));

function checkDoorways(object: WorldPropObject, colliders: WorldCollider[]) {
  const mesh = new THREE.Object3D();
  mesh.position.copy(object.transform.position);
  mesh.rotation.set(object.transform.rotation.x, object.transform.rotation.y, object.transform.rotation.z);
  mesh.scale.copy(object.transform.scale);
  mesh.updateMatrixWorld(true);
  const { doors, walls } = samples[object.kind as keyof typeof samples];
  for (const [x, z] of doors) {
    expect(cityPositionBlocked(mesh.localToWorld(new THREE.Vector3(x, .1, z)), colliders, .3), `${object.kind}: doorway ${x}/${z}`).toBe(false);
  }
  for (const [x, z] of walls) {
    expect(cityPositionBlocked(mesh.localToWorld(new THREE.Vector3(x, .1, z)), colliders, .3), `${object.kind}: wall ${x}/${z}`).toBe(true);
  }
}

describe('mesh-aligned citadel builder collision', () => {
  beforeEach(() => vi.stubGlobal('window', new EventTarget()));
  afterEach(() => vi.unstubAllGlobals());

  test('generated and runtime prefabs preserve the opt-in collision space for rooms, vault and decorations', () => {
    const generated = generateBuilderCatalog();
    const kinds = ['aegis_room', 'aegis_mountain_vault', ...zone.cityCitadel!.siege!.decorationKinds];
    for (const kind of kinds) {
      expect(generated.find(entry => entry.kind === kind)?.colliderSpace, kind).toBe('model');
      expect(prefabDefinitionForKind(kind)?.colliderSpace, kind).toBe('model');
    }
    expect(prefabDefinitionForKind('aegis_citadel')?.colliderSpace).toBeUndefined();
  });

  test.each(cases)('$kind doorways follow visible geometry at yaw $yaw in map spawning and GM stamps', async ({ kind, yaw }) => {
    const source = zone.props.find(prop => prop.kind === kind)!;
    const scene = new THREE.Scene();
    const spawned = await spawnProps(scene, loader, terrain, [{ ...source, x: 12, y: 0, z: -18,
      rotY: yaw, scale: 1, scaleX: 1, scaleY: 1, scaleZ: 1 }]);
    const mapObject = spawned.objects[0].definition;
    expect(mapObject.colliderSpace).toBe('model');
    checkDoorways(mapObject, spawned.colliders);
    checkDoorways(mapObject, propCollidersFromObject(mapObject));
    expect(propWalkablesFromObject(mapObject)[0]).toMatchObject({ x: 12, z: -18, fromY: 7, toY: 7 });

    const element = Object.assign(new EventTarget(), { style: {}, ownerDocument: new EventTarget() });
    const runtime = new WorldEditorRuntime({ scene: new THREE.Scene(), camera: new THREE.PerspectiveCamera(),
      domElement: element as unknown as HTMLElement, loader, terrain, groundHeightAt: () => 7 });
    try {
      await runtime.loadDocument(createEmptyWorldEditDocument('aegis_capital', 'draft'), true);
      runtime.setSettings({ prefabKind: kind });
      runtime.setPlayerPose({ x: 12, y: 7, z: -18 }, yaw);
      runtime.setTool('stamp_prefab');
      await runtime.stampPrefabAtPlayer({ x: 12, y: 7, z: -18 });
      let stamped = runtime.currentDocument!.objects[0] as WorldPropObject;
      expect(stamped.colliderSpace).toBe('model');
      expect(stamped.transform.rotation.y).toBeCloseTo(yaw);
      checkDoorways(stamped, runtime.getColliders());

      const service = new WorldEditLocal();
      await service.saveDraft('aegis_capital', { replaceDocument: runtime.currentDocument! });
      const saved = await service.getDraft('aegis_capital');
      await runtime.loadDocument(saved, true);
      stamped = runtime.currentDocument!.objects[0] as WorldPropObject;
      expect(stamped.colliderSpace).toBe('model');
      checkDoorways(stamped, runtime.getColliders());
      runtime.selectObject(stamped.id);
      expect(runtime.deleteSelectedObject()).toBe(true);
      expect(runtime.getColliders()).toHaveLength(0);
    } finally {
      runtime.dispose();
    }
  });

  test.each([undefined, 'model'] as const)('collision space %s keeps scaled offsets, local yaw and walkable ramps consistent', async (colliderSpace) => {
    const source = { id: 'offset-room', kind: 'aegis_room', visible: false, colliderSpace,
      x: 10, y: -3, z: 20, rotY: Math.PI / 2, scaleX: 2, scaleY: 3, scaleZ: 4,
      colliders: [{ x: 2, z: 3, width: 1, depth: 2, rotY: Math.PI / 4, minY: 1, maxY: 2 }],
      walkableSurfaces: [{ x: 2, z: 3, width: 1, depth: 2, rotY: Math.PI / 4, fromY: 1, toY: 6 }],
    };
    const spawned = await spawnProps(new THREE.Scene(), loader, terrain, [source]);
    const object = spawned.objects[0].definition;
    const expectedX = colliderSpace === 'model' ? 22 : -2;
    const expectedZ = colliderSpace === 'model' ? 16 : 24;
    const expectedYaw = (colliderSpace === 'model' ? -1 : 1) * Math.PI * .75;
    for (const collider of [spawned.colliders[0], propCollidersFromObject(object)[0]]) {
      expect(collider.x).toBeCloseTo(expectedX);
      expect(collider.z).toBeCloseTo(expectedZ);
      expect(collider.rotY).toBeCloseTo(expectedYaw);
      expect(collider).toMatchObject({ width: 2, depth: 8, minY: 7, maxY: 10 });
    }
    for (const surface of [spawned.walkableSurfaces[0], propWalkablesFromObject(object)[0]]) {
      expect(surface.x).toBeCloseTo(expectedX);
      expect(surface.z).toBeCloseTo(expectedZ);
      expect(surface.rotY).toBeCloseTo(expectedYaw);
      expect(surface).toMatchObject({ width: 2, depth: 8, fromY: 7, toY: 22 });
    }
  });
});
