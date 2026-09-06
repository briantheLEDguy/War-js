import fs from 'node:fs';
import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { cityPositionBlocked } from '../src/world/CityNavigation';
import { cityHeightAt } from '../src/world/CityElevation';
import { propCollidersFromObject, propWalkablesFromObject } from '../src/world/editor/WorldEditorRuntime';
import { spawnProps } from '../src/world/Props';
import type { PropSpawn, ZoneDefinition } from '../src/world/ZoneLoader';
import type { WorldPropObject } from '../src/services/types';
import type { Terrain } from '../src/world/Terrain';
import type { AssetLoader } from '../src/game/AssetLoader';

const zone: ZoneDefinition = JSON.parse(fs.readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
const height = (p: PropSpawn) => cityHeightAt(zone.cityElevation!, zone.size, p.x, p.z) + (p.y ?? 0);
const definition = (p: PropSpawn): WorldPropObject => ({ ...p, id: p.id!, type: 'prop', createdAt: 0, updatedAt: 0,
  transform: { position: { x: p.x, y: height(p), z: p.z }, rotation: { x: 0, y: p.rotY ?? 0, z: 0 },
    scale: { x: (p.scale ?? 1) * (p.scaleX ?? 1), y: (p.scale ?? 1) * (p.scaleY ?? 1), z: (p.scale ?? 1) * (p.scaleZ ?? 1) } } });
const colliders = zone.props.flatMap(p => propCollidersFromObject(definition(p)));

describe('Crownwatch gated siege precinct', () => {
  test('the shipped keep mesh has a through hall, floor and rear walls beside the mountain doorway at every LOD', () => {
    for (const suffix of ['', '_lod1', '_lod2']) {
      const bytes = fs.readFileSync(`public/assets/models/prop_aegis_citadel${suffix}.glb`);
      const jsonLength = bytes.readUInt32LE(12);
      const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
      const binary = bytes.subarray(20 + jsonLength + 8);
      const attribute = (index: number, positions: boolean) => {
        const accessor = gltf.accessors[index], view = gltf.bufferViews[accessor.bufferView];
        const size = positions ? 3 : 1, unit = accessor.componentType === 5121 ? 1 : accessor.componentType === 5123 ? 2 : 4;
        const values: number[] = [];
        for (let i = 0; i < accessor.count; i++) for (let j = 0; j < size; j++) {
          const offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0) + i * (view.byteStride ?? size * unit) + j * unit;
          values.push(positions ? binary.readFloatLE(offset) : unit === 1 ? binary.readUInt8(offset) : unit === 2 ? binary.readUInt16LE(offset) : binary.readUInt32LE(offset));
        }
        return values;
      };
      const scene = new THREE.Group();
      const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide });
      const visit = (index: number, parent: THREE.Object3D) => {
        const node = gltf.nodes[index], group = new THREE.Group();
        if (node.matrix) group.applyMatrix4(new THREE.Matrix4().fromArray(node.matrix));
        else {
          group.position.fromArray(node.translation ?? [0,0,0]); group.quaternion.fromArray(node.rotation ?? [0,0,0,1]); group.scale.fromArray(node.scale ?? [1,1,1]);
        }
        parent.add(group);
        for (const primitive of gltf.meshes?.[node.mesh]?.primitives ?? []) {
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(attribute(primitive.attributes.POSITION, true), 3));
          if (primitive.indices !== undefined) geometry.setIndex(attribute(primitive.indices, false));
          group.add(new THREE.Mesh(geometry, material));
        }
        for (const child of node.children ?? []) visit(child, group);
      };
      for (const root of gltf.scenes[gltf.scene ?? 0].nodes) visit(root, scene);
      scene.updateMatrixWorld(true);
      const ray = new THREE.Raycaster(new THREE.Vector3(0,2,60), new THREE.Vector3(0,0,-1), 0, 65);
      expect(ray.intersectObject(scene, true), `${suffix} doorway and hall`).toHaveLength(0);
      ray.far = 80;
      expect(ray.intersectObject(scene, true), `${suffix} mountain doorway`).toHaveLength(0);
      ray.set(new THREE.Vector3(20,2,0), new THREE.Vector3(0,0,-1));
      expect(ray.intersectObject(scene, true).length, `${suffix} rear wall`).toBeGreaterThan(0);
      ray.set(new THREE.Vector3(0,2,0), new THREE.Vector3(0,-1,0));
      expect(ray.intersectObject(scene, true).length, `${suffix} floor`).toBeGreaterThan(0);
      ray.set(new THREE.Vector3(0,2,35), new THREE.Vector3(0,-1,0));
      expect(ray.intersectObject(scene, true).length, `${suffix} extended hall floor`).toBeGreaterThan(0);
      ray.set(new THREE.Vector3(0,2,35), new THREE.Vector3(1,0,0));
      expect(ray.intersectObject(scene, true)[0]?.distance, `${suffix} extended side wall`).toBeCloseTo(34.6, 1);
      scene.traverse(node => { if (node instanceof THREE.Mesh) node.geometry.dispose(); }); material.dispose();
    }
  });
  test('encloses the court with exactly three functional entrances and a separate keep gate', async () => {
    const citadel = zone.cityCitadel!;
    expect(citadel.entranceGateIds).toHaveLength(3);
    const ids = [...citadel.entranceGateIds, citadel.keepGateId];
    expect(new Set(ids).size).toBe(4);
    const gates = zone.props.filter(p => ids.includes(p.interaction?.id ?? ''));
    expect(gates).toHaveLength(4);
    const loader = { resolveStaticModel: async (_key: string, model: string) => model,
      loadModelWithAnimations: async (_model: string, fallback: () => THREE.Object3D) => ({ object: fallback(), animations: [] }) };
    const spawned = await spawnProps(new THREE.Scene(), loader as unknown as AssetLoader, { heightAt: () => 42 } as Terrain, gates);
    expect(spawned.gates).toHaveLength(4);
    for (const gate of spawned.gates) {
      expect(gate.isOpen).toBe(false);
      expect(gate.fallbackVisual).not.toBeNull();
      const bounds = new THREE.Box3().setFromObject(gate.object);
      expect(bounds.min.y).toBeCloseTo(42);
      expect(spawned.colliders.some(c => c.interactionId === gate.id && c.blocksWhen === 'closed')).toBe(true);
    }
  });
  test('closed gates seal the perimeter; opening them clears all three approach centers', () => {
    const closed = colliders.map(c => ({ ...c, blocksWhen: 'always' as const }));
    for (let x = -90; x <= 90; x += .5) {
      expect(cityPositionBlocked({ x, y: 42, z: 132 }, closed, .3), `front ${x}`).toBe(true);
      if (Math.abs(x) >= 9)
        expect(cityPositionBlocked({ x, y: 42, z: 246 }, closed, .3), `rear ${x}`).toBe(true);
    }
    for (let z = 132; z <= 246; z += .5) for (const x of [-90,90]) {
      expect(cityPositionBlocked({ x, y: 42, z }, closed, .3), `side ${x}/${z}`).toBe(true);
    }
    for (const x of [-62,0,62]) expect(cityPositionBlocked({ x, y: 42, z: 132 }, colliders)).toBe(false);
    expect(cityPositionBlocked({ x: 0, y: 42, z: 176.5 }, closed)).toBe(true);
    expect(cityPositionBlocked({ x: 0, y: 42, z: 176.5 }, colliders)).toBe(false);
    expect(cityPositionBlocked({ x: 0, y: 42, z: 246 }, closed)).toBe(false);
    expect(cityPositionBlocked({ x: 0, y: 42, z: 250 }, closed)).toBe(true);
  });
  test('players can walk into the hall, through side chambers and up both gallery stairways', () => {
    for (let z = 172; z <= 230; z += .25) expect(cityPositionBlocked({ x: 0, y: 42, z }, colliders), `entry ${z}`).toBe(false);
    for (let x = -32; x <= 32; x += .25) expect(cityPositionBlocked({ x, y: 42, z: 226 }, colliders), `chamber ${x}`).toBe(false);
    for (const x of [-27,27]) {
      const stairs = zone.props.find(p => p.id === `aegis_battle_hall_stairs_${x}`)!;
      const [ramp] = propWalkablesFromObject(definition(stairs));
      expect(ramp.depth).toBeCloseTo(21);
      for (let i = 0; i <= 40; i++) {
        const z = 215.3 + i / 40 * 21, y = 42 + i / 40 * 6;
        expect(cityPositionBlocked({ x, y, z }, colliders), `stairs ${x}/${z}: ${colliders.filter(c => cityPositionBlocked({ x, y, z }, [c])).map(c => c.id).join(', ')}`).toBe(false);
      }
    }
    for (let x = -27; x <= 27; x += .25) expect(cityPositionBlocked({ x, y: 48, z: 236.8 }, colliders), `gallery ${x}`).toBe(false);
  });
});
