import fs from 'node:fs';
import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { cityHeightAt } from '../src/world/CityElevation';
import { cityPositionBlocked } from '../src/world/CityNavigation';
import { cityFallback } from '../src/world/CityArchitecture';
import { propCollidersFromObject } from '../src/world/editor/WorldEditorRuntime';
import { spawnProps } from '../src/world/Props';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { WorldPropObject } from '../src/services/types';
import type { PropSpawn, ZoneDefinition } from '../src/world/ZoneLoader';
import type { Terrain } from '../src/world/Terrain';

const zone: ZoneDefinition = JSON.parse(fs.readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
const mountain = zone.cityCitadel!.mountainExtension!;
const ground = (x: number, z: number) => cityHeightAt(zone.cityElevation!, zone.size, x, z);
const definition = (p: PropSpawn): WorldPropObject => ({ ...p, id: p.id!, type: 'prop', createdAt: 0, updatedAt: 0,
  transform: { position: { x: p.x, y: ground(p.x, p.z) + (p.y ?? 0), z: p.z },
    rotation: { x: 0, y: p.rotY ?? 0, z: 0 }, scale: { x: (p.scale ?? 1) * (p.scaleX ?? 1),
      y: (p.scale ?? 1) * (p.scaleY ?? 1), z: (p.scale ?? 1) * (p.scaleZ ?? 1) } } });
const colliders = zone.props.flatMap(p => propCollidersFromObject(definition(p)));

// Raycast exported triangles, including node transforms, independently of authored collision boxes.
function shippedMesh(kind: string, suffix: string): THREE.Group {
  const bytes = fs.readFileSync(`public/assets/models/prop_aegis_${kind}${suffix}.glb`);
  const jsonLength = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  const binary = bytes.subarray(20 + jsonLength + 8);
  const attribute = (index: number, positions: boolean) => {
    const accessor = gltf.accessors[index], view = gltf.bufferViews[accessor.bufferView];
    const size = positions ? 3 : 1, unit = accessor.componentType === 5121 ? 1 : accessor.componentType === 5123 ? 2 : 4;
    const values: number[] = [];
    for (let i = 0; i < accessor.count; i++) for (let j = 0; j < size; j++) {
      const offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0) + i * (view.byteStride ?? size * unit) + j * unit;
      values.push(positions ? binary.readFloatLE(offset) : unit === 1 ? binary.readUInt8(offset)
        : unit === 2 ? binary.readUInt16LE(offset) : binary.readUInt32LE(offset));
    }
    return values;
  };
  const scene = new THREE.Group(), material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide });
  const visit = (index: number, parent: THREE.Object3D) => {
    const node = gltf.nodes[index], group = new THREE.Group();
    if (node.matrix) group.applyMatrix4(new THREE.Matrix4().fromArray(node.matrix));
    else {
      group.position.fromArray(node.translation ?? [0, 0, 0]);
      group.quaternion.fromArray(node.rotation ?? [0, 0, 0, 1]);
      group.scale.fromArray(node.scale ?? [1, 1, 1]);
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
  return scene;
}

function disposeMesh(scene: THREE.Object3D) {
  const materials = new Set<THREE.Material>();
  scene.traverse(node => {
    if (!(node instanceof THREE.Mesh)) return;
    node.geometry.dispose();
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) materials.add(material);
  });
  for (const material of materials) material.dispose();
}

function clearRoute(a: { x: number; z: number }, b: { x: number; z: number }, label: string, radius = .65) {
  const steps = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) * 4);
  for (let i = 0; i <= steps; i++) {
    const x = a.x + (b.x - a.x) * i / steps, z = a.z + (b.z - a.z) * i / steps;
    expect(ground(x, z), `${label} height ${x}/${z}`).toBeCloseTo(42);
    expect(cityPositionBlocked({ x, y: 42, z }, colliders, radius), `${label} ${x}/${z}`).toBe(false);
  }
}

describe('Crownwatch mountain siege extension', () => {
  test('keeps the expanded playable area on the same floor and seals its internal threshold with a working gate', async () => {
    expect(zone.size / zone.cityElevation!.segments).toBeLessThanOrEqual(1);
    expect(mountain.bounds.maxZ).toBeLessThan(zone.size / 2);
    expect(mountain.bounds.minX).toBeGreaterThan(-zone.size / 2);
    expect(mountain.bounds.maxX).toBeLessThan(zone.size / 2);
    expect(zone.cityCitadel!.entranceGateIds).toHaveLength(3);
    expect(zone.cityCitadel!.entranceGateIds).not.toContain(mountain.internalGateId);
    const gates = zone.props.filter(p => p.interaction?.id === mountain.internalGateId);
    expect(gates).toHaveLength(1);
    const gate = gates[0];
    const loader = { resolveStaticModel: async (_key: string, model: string) => model,
      loadModelWithAnimations: async (_model: string, fallback: () => THREE.Object3D) => ({ object: fallback(), animations: [] }) };
    const spawned = await spawnProps(new THREE.Scene(), loader as unknown as AssetLoader, { heightAt: () => 42 } as Terrain, gates);
    expect(spawned.gates).toHaveLength(1);
    expect(spawned.gates[0].isOpen).toBe(false);
    expect(spawned.gates[0].fallbackVisual).not.toBeNull();
    const closed = colliders.map(c => c.interactionId === mountain.internalGateId ? { ...c, blocksWhen: 'always' as const } : c);
    for (let x = -8.5; x <= 8.5; x += .5) {
      expect(cityPositionBlocked({ x, y: 42, z: gate.z }, closed), `closed threshold ${x}`).toBe(true);
      expect(cityPositionBlocked({ x, y: 42, z: gate.z }, colliders, .3), `open threshold ${x}`).toBe(false);
    }
  });

  test('connects the keep to the forehall, throne hall, working vault and reserved crypt branch', () => {
    clearRoute({ x: 0, z: 220 }, { x: 0, z: 358 }, 'keep to throne approach');
    clearRoute({ x: -83.5, z: 314 }, { x: 83.5, z: 314 }, 'crypts to vault approach');
    for (const x of [-34, 34]) clearRoute({ x, z: 342 }, { x, z: 360 }, 'command flanking passage');
    for (const route of mountain.routes) for (let i = 1; i < route.points.length; i++)
      clearRoute(route.points[i - 1], route.points[i], route.id);
  });

  test('fits two teams of eighteen with every staging slot connected through the siege hall', () => {
    const { battleHall: bounds, staging } = mountain;
    expect((bounds.maxX - bounds.minX) * (bounds.maxZ - bounds.minZ)).toBeGreaterThan(7500);
    expect(staging.south).toHaveLength(18);
    expect(staging.north).toHaveLength(18);
    const slots = [...staging.south, ...staging.north];
    for (const [i, p] of slots.entries()) {
      expect(p.x).toBeGreaterThan(bounds.minX);
      expect(p.x).toBeLessThan(bounds.maxX);
      expect(p.z).toBeGreaterThan(bounds.minZ);
      expect(p.z).toBeLessThan(bounds.maxZ);
      expect(cityPositionBlocked({ ...p, y: 42 }, colliders, 1), `staging slot ${i}`).toBe(false);
      for (const q of slots.slice(i + 1)) expect(Math.hypot(p.x - q.x, p.z - q.z)).toBeGreaterThanOrEqual(5);
    }
    const local = colliders.filter(c => c.z > 270 && Math.abs(c.x) < 100);
    const width = 115, minZ = 280, maxZ = 372, seen = new Set<number>(), queue = [{ x: 0, z: 314 }];
    const key = (x: number, z: number) => (z - minZ) * width + x + 57;
    seen.add(key(0, 314));
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i];
      for (const [x, z] of [[p.x - 1, p.z], [p.x + 1, p.z], [p.x, p.z - 1], [p.x, p.z + 1]]) {
        const k = key(x, z);
        if (Math.abs(x) > 57 || z < minZ || z > maxZ || seen.has(k) || cityPositionBlocked({ x, y: 42, z }, local, 1)) continue;
        seen.add(k); queue.push({ x, z });
      }
    }
    for (const p of [...slots, { x: -34, z: 360 }, { x: 0, z: 360 }, { x: 34, z: 360 }])
      expect(seen.has(key(p.x, p.z)), `connected battle position ${p.x}/${p.z}`).toBe(true);
  });

  test('retains the sealed future crypt while the vault is connected inside this zone', () => {
    expect(mountain.futureConnections.map(c => c.id)).toEqual(['crypts']);
    expect(mountain.vault?.gateIds).toHaveLength(2);
    expect(zone.props.some(p => p.id === 'aegis_mountain_vault_seal')).toBe(false);
    for (const connection of mountain.futureConnections) {
      expect(connection.status).toBe('sealed');
      const portal = zone.props.find(p => p.id === connection.portalPropId)!;
      expect(portal.kind).toBe('aegis_mountain_seal');
      expect(portal.interaction).toBeUndefined();
      expect(cityPositionBlocked(connection.approach, colliders)).toBe(false);
      for (let z = portal.z - 4.5; z <= portal.z + 4.5; z += .25)
        expect(cityPositionBlocked({ x: portal.x, y: 42, z }, colliders), `${connection.id} sealed ${z}`).toBe(true);
      expect(zone.zoneTriggers?.some(t => Math.hypot(t.x - portal.x, t.z - portal.z) < 10)).toBe(false);
      const reserved = connection.reservedBounds;
      expect(reserved.maxX - reserved.minX).toBeGreaterThan(40);
      expect(reserved.maxZ - reserved.minZ).toBeGreaterThan(80);
      expect(reserved.minX).toBeGreaterThan(-zone.size / 2);
      expect(reserved.maxX).toBeLessThan(zone.size / 2);
    }
    for (let x = -59; x <= 59; x += .5)
      expect(cityPositionBlocked({ x, y: 42, z: 373.5 }, colliders), `rear enclosure ${x}`).toBe(true);
  });

  test('ships genuinely hollow passages and a connected redoubt at every detail level', () => {
    for (const suffix of ['', '_lod1', '_lod2']) {
      const passage = shippedMesh('mountain_passage', suffix);
      const ray = new THREE.Raycaster(new THREE.Vector3(0, 2, 20), new THREE.Vector3(0, 0, -1), 0, 40);
      expect(ray.intersectObject(passage, true), `passage ${suffix} open ends`).toHaveLength(0);
      ray.set(new THREE.Vector3(0, 2, 0), new THREE.Vector3(1, 0, 0));
      expect(ray.intersectObject(passage, true).length, `passage ${suffix} side wall`).toBeGreaterThan(0);
      ray.set(new THREE.Vector3(0, 2, 0), new THREE.Vector3(0, -1, 0));
      expect(ray.intersectObject(passage, true).length, `passage ${suffix} floor`).toBeGreaterThan(0);
      disposeMesh(passage);

      const redoubt = shippedMesh('mountain_redoubt', suffix);
      ray.set(new THREE.Vector3(0, 2, 60), new THREE.Vector3(0, 0, -1)); ray.far = 106;
      expect(ray.intersectObject(redoubt, true), `redoubt ${suffix} entry and command doorway`).toHaveLength(0);
      ray.far = 120;
      expect(ray.intersectObject(redoubt, true).length, `redoubt ${suffix} rear wall`).toBeGreaterThan(0);
      ray.set(new THREE.Vector3(-70, 2, 12), new THREE.Vector3(1, 0, 0)); ray.far = 140;
      expect(ray.intersectObject(redoubt, true), `redoubt ${suffix} side portals`).toHaveLength(0);
      for (const x of [-34, 34]) {
        ray.set(new THREE.Vector3(x, 2, 15), new THREE.Vector3(0, 0, -1)); ray.far = 30;
        expect(ray.intersectObject(redoubt, true), `redoubt ${suffix} flank ${x}`).toHaveLength(0);
      }
      ray.set(new THREE.Vector3(-70, 2, -30), new THREE.Vector3(1, 0, 0)); ray.far = 20;
      expect(ray.intersectObject(redoubt, true), `redoubt ${suffix} royal treasury return`).toHaveLength(0);
      ray.set(new THREE.Vector3(18, 2, 15), new THREE.Vector3(0, 0, -1)); ray.far = 20;
      expect(ray.intersectObject(redoubt, true).length, `redoubt ${suffix} forehall partition`).toBeGreaterThan(0);
      ray.set(new THREE.Vector3(0, 2, 0), new THREE.Vector3(0, -1, 0));
      expect(ray.intersectObject(redoubt, true).length, `redoubt ${suffix} floor`).toBeGreaterThan(0);
      disposeMesh(redoubt);

      const vault = shippedMesh('mountain_vault', suffix);
      for (const z of [18, -24]) {
        ray.set(new THREE.Vector3(35, 2, z), new THREE.Vector3(-1, 0, 0)); ray.far = 35;
        expect(ray.intersectObject(vault, true), `vault ${suffix} side portal ${z}`).toHaveLength(0);
      }
      ray.set(new THREE.Vector3(0, 2, 36), new THREE.Vector3(0, 0, -1)); ray.far = 72;
      expect(ray.intersectObject(vault, true), `vault ${suffix} full-length center aisle`).toHaveLength(0);
      ray.set(new THREE.Vector3(0, 2, 0), new THREE.Vector3(0, -1, 0)); ray.far = 10;
      expect(ray.intersectObject(vault, true)[0]?.point.y, `vault ${suffix} floor`).toBeCloseTo(0, 2);
      ray.set(new THREE.Vector3(0, 2, 10), new THREE.Vector3(0, 1, 0)); ray.far = 30;
      const ceiling = ray.intersectObject(vault, true)[0];
      expect(ceiling, `vault ${suffix} roof`).toBeDefined();
      expect(ceiling.point.y).toBeGreaterThanOrEqual(19.9);
      expect(ceiling.point.y).toBeLessThanOrEqual(20.1);
      ray.set(new THREE.Vector3(0, 2, 0), new THREE.Vector3(-1, 0, 0)); ray.far = 40;
      expect(ray.intersectObject(vault, true).length, `vault ${suffix} closed east wall`).toBeGreaterThan(0);
      disposeMesh(vault);

      const seal = shippedMesh('mountain_seal', suffix);
      ray.set(new THREE.Vector3(0, 2, 10), new THREE.Vector3(0, 0, -1)); ray.far = 20;
      expect(ray.intersectObject(seal, true).length, `seal ${suffix} solid door`).toBeGreaterThan(0);
      disposeMesh(seal);
    }
  });

  test('missing models still leave the keep and mountain rooms traversable while future doors stay sealed', () => {
    for (const [kind, startZ, distance] of [
      ['citadel', 20, 40], ['mountain_passage', 20, 40], ['mountain_redoubt', 60, 106], ['mountain_vault', 36, 72],
    ] as const) {
      const fallback = cityFallback(`aegis_${kind}`);
      fallback.updateMatrixWorld(true);
      const ray = new THREE.Raycaster(new THREE.Vector3(0, 2, startZ), new THREE.Vector3(0, 0, -1), 0, distance);
      expect(ray.intersectObject(fallback, true), `${kind} fallback entry`).toHaveLength(0);
      ray.set(new THREE.Vector3(0, 2, 0), new THREE.Vector3(0, -1, 0));
      expect(ray.intersectObject(fallback, true).length, `${kind} fallback floor`).toBeGreaterThan(0);
      disposeMesh(fallback);
    }
    const seal = cityFallback('aegis_mountain_seal');
    seal.updateMatrixWorld(true);
    const ray = new THREE.Raycaster(new THREE.Vector3(0, 2, 10), new THREE.Vector3(0, 0, -1), 0, 20);
    expect(ray.intersectObject(seal, true).length).toBeGreaterThan(0);
    disposeMesh(seal);
  });

  test('the four service-room GLB doorways face their authored central-aisle entrances at every LOD', () => {
    const rooms = zone.cityCitadel!.siege!.rooms.filter(room => ['barracks', 'mess', 'stores', 'counting'].includes(room.id));
    expect(rooms).toHaveLength(4);
    for (const suffix of ['', '_lod1', '_lod2']) {
      const shell = shippedMesh('room', suffix);
      for (const room of rooms) {
        const prop = zone.props.find(p => p.id === `aegis_interior_${room.id}_room`)!, transform = definition(prop).transform;
        shell.position.set(transform.position.x, transform.position.y, transform.position.z);
        shell.rotation.set(transform.rotation.x, transform.rotation.y, transform.rotation.z);
        shell.scale.set(transform.scale.x, transform.scale.y, transform.scale.z);
        shell.updateMatrixWorld(true);
        const outward = Math.sign(room.entry.x - prop.x);
        for (const lateral of [-.65, 0, .65]) {
          const ray = new THREE.Raycaster(new THREE.Vector3(room.entry.x + outward * 4, room.floorY + 2, room.entry.z + lateral),
            new THREE.Vector3(-outward, 0, 0), 0, 7);
          expect(ray.intersectObject(shell, true), `${room.id}${suffix} open aisle-facing door ${lateral}`).toHaveLength(0);
        }
        const floor = new THREE.Raycaster(new THREE.Vector3(prop.x, room.floorY + 2, prop.z), new THREE.Vector3(0, -1, 0), 0, 3);
        expect(floor.intersectObject(shell, true)[0]?.point.y, `${room.id}${suffix} floor`).toBeCloseTo(room.floorY, 2);
      }
      disposeMesh(shell);
    }
  });

  test('keeps the actual mountain surface above the buried rooms and passage roofs at every LOD', () => {
    const prop = zone.props.find(p => p.id === 'aegis_mountain_massif')!;
    for (const suffix of ['', '_lod1', '_lod2']) {
      const massif = shippedMesh('mountain_massif', suffix), transform = definition(prop).transform;
      massif.position.set(transform.position.x, transform.position.y, transform.position.z);
      massif.rotation.set(transform.rotation.x, transform.rotation.y, transform.rotation.z);
      massif.scale.set(transform.scale.x, transform.scale.y, transform.scale.z);
      massif.updateMatrixWorld(true);
      const samples = [
        ...[-50, 0, 50].flatMap(x => [280, 314, 350, 372].map(z => ({ x, z, roof: 34 }))),
        { x: 0, z: 258, roof: 20 }, ...[-80, 80].map(x => ({ x, z: 314, roof: 20 })),
        ...[91, 114, 137].flatMap(x => [291, 314, 356, 373].map(z => ({ x, z, roof: 22 }))),
        { x: 74.5, z: 356, roof: 20 },
      ];
      for (const { x, z, roof } of samples) {
        const ray = new THREE.Raycaster(new THREE.Vector3(x, 1000, z), new THREE.Vector3(0, -1, 0));
        const hit = ray.intersectObject(massif, true)[0];
        expect(hit, `mountain ${suffix} covers ${x}/${z}`).toBeDefined();
        expect(hit.point.y, `mountain ${suffix} roof clearance ${x}/${z}`).toBeGreaterThan(42 + roof);
      }
      disposeMesh(massif);
    }
  });
});
