import { afterEach, describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { WorldLife, WORLD_LIFE_LIMITS } from '../src/world/WorldLife';
import { buildWorldLifeProp } from '../src/world/WorldLifeAssets';
import type { WorldLifeActorSpawn, WorldLifeDefinition } from '../src/world/worldLifeTypes';

const instances: WorldLife[] = [];

function createLife(
  definition: WorldLifeDefinition | undefined,
  groundHeight: (x: number, z: number) => number = () => 0,
  scenery: THREE.Object3D[] = [],
) {
  const scene = new THREE.Scene();
  scene.add(...scenery);
  const life = new WorldLife(scene, definition, 'aegis', groundHeight, scenery);
  instances.push(life);
  return { life, scene };
}

function objectNamed(root: THREE.Object3D, name: string): THREE.Object3D {
  const object = root.getObjectByName(name);
  expect(object, `Expected scene object ${name}`).toBeDefined();
  return object!;
}

function emitterNamed(root: THREE.Object3D, name: string): THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial> {
  const object = objectNamed(root, name);
  expect(object).toBeInstanceOf(THREE.Points);
  return object as THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial>;
}

function poseOf(root: THREE.Object3D) {
  const poses: number[][] = [];
  root.traverse((object) => {
    poses.push([...object.position.toArray(), ...object.quaternion.toArray(), ...object.scale.toArray()]);
  });
  return poses;
}

afterEach(() => {
  for (const life of instances.splice(0)) life.dispose();
  vi.restoreAllMocks();
});

describe('ambient world life runtime', () => {
  test('supports zones with no ambient definition', () => {
    const { life, scene } = createLife(undefined);
    expect(scene.children).toContain(life.group);
    expect(life.group.children).toHaveLength(0);
    expect(() => life.update(1, { x: 0, z: 0 }, 50)).not.toThrow();
  });

  test('culls actors and emitters by planar distance, including the boundary', () => {
    const { life } = createLife({
      actors: [{ id: 'citizen', kind: 'citizen', x: 30, z: 40 }],
      emitters: [{ id: 'smoke', kind: 'smoke', x: 30, z: 40, y: 50 }],
    });
    const actor = objectNamed(life.group, 'citizen');
    const emitter = emitterNamed(life.group, 'smoke');

    life.update(0, { x: 0, z: 0 }, 49);
    expect(actor.visible).toBe(false);
    expect(emitter.visible).toBe(false);
    life.update(0, { x: 0, z: 0 }, 50);
    expect(actor.visible).toBe(true);
    expect(emitter.visible).toBe(true);
    life.update(0, { x: -100, z: 40 }, 10_000);
    expect(actor.visible).toBe(false);
    expect(emitter.visible).toBe(false);
    life.update(0, { x: 30, z: 40 }, 15);
    expect(actor.visible).toBe(true);
    expect(emitter.visible).toBe(true);
  });

  test('skips distant rig, terrain, and particle work but catches up on re-entry', () => {
    const definition: WorldLifeDefinition = {
      actors: [{ id: 'traveler', kind: 'citizen', x: 120, z: 0, route: [{ x: 140, z: 0 }], speed: 2, pauseSeconds: 0 }],
      emitters: [{ id: 'embers', kind: 'embers', x: 120, z: 0 }],
    };
    const groundHeight = vi.fn((x: number) => x / 10);
    const { life } = createLife(definition, groundHeight);
    const { life: visibleLife } = createLife(definition, groundHeight);
    const actor = objectNamed(life.group, 'traveler');
    const initialPosition = actor.position.x;
    const initialRig = objectNamed(actor, 'leg-left').rotation.x;
    const particles = emitterNamed(life.group, 'embers').geometry.getAttribute('position') as THREE.BufferAttribute;
    const initialVersion = particles.version;
    groundHeight.mockClear();

    life.update(2, { x: 0, z: 0 }, 100);
    expect(actor.visible).toBe(false);
    expect(actor.position.x).not.toBe(initialPosition);
    expect(objectNamed(actor, 'leg-left').rotation.x).toBe(initialRig);
    expect(groundHeight).not.toHaveBeenCalled();
    expect(particles.version).toBe(initialVersion);

    life.update(0, { x: 130, z: 0 }, 100);
    visibleLife.update(2, { x: 130, z: 0 }, 100);
    expect(actor.visible).toBe(true);
    expect(poseOf(actor)).toEqual(poseOf(objectNamed(visibleLife.group, 'traveler')));
    expect(particles.array).toEqual(emitterNamed(visibleLife.group, 'embers').geometry.getAttribute('position').array);
    expect(particles.version).toBe(initialVersion + 1);
  });

  test('grounds moving actors at their sampled location and offsets birds and emitters above terrain', () => {
    const heightAt = (x: number, z: number) => 2 + x / 10 + z / 4;
    const { life } = createLife({
      actors: [
        { id: 'walker', kind: 'citizen', x: 0, z: 0, route: [{ x: 20, z: 12 }], speed: 2, pauseSeconds: 0, scale: 2 },
        { id: 'deer', kind: 'deer', x: 5, z: 3, route: [{ x: 15, z: 8 }], speed: 2, pauseSeconds: 0 },
        { id: 'bird', kind: 'bird', x: 4, z: 3 },
      ],
      emitters: [
        { id: 'smoke', kind: 'smoke', x: 12, z: 8, y: 2.5 },
        { id: 'motes', kind: 'motes', x: 2, z: 4 },
      ],
    }, heightAt);

    for (const dt of [0, 0.5, 3]) {
      life.update(dt, { x: 0, z: 0 }, 100);
      for (const id of ['walker', 'deer']) {
        const { position } = objectNamed(life.group, id);
        expect(position.y).toBeCloseTo(heightAt(position.x, position.z));
      }
      const bird = objectNamed(life.group, 'bird');
      const altitude = bird.position.y - heightAt(bird.position.x, bird.position.z);
      expect(altitude).toBeGreaterThan(6);
      expect(altitude).toBeLessThan(12);
    }
    expect(objectNamed(life.group, 'smoke').position.y).toBeCloseTo(heightAt(12, 8) + 2.5);
    expect(objectNamed(life.group, 'motes').position.y).toBeCloseTo(heightAt(2, 4) + 0.5);
  });

  test('keeps stationary residents grounded while deer graze and birds flap', () => {
    const actors: WorldLifeActorSpawn[] = [
      { id: 'resident', kind: 'citizen', x: 3, z: 4 },
      { id: 'guard', kind: 'guard', x: 7, z: 4, speed: 0, route: [{ x: 14, z: 5 }] },
      { id: 'deer', kind: 'deer', x: 8, z: 9 },
      { id: 'bird', kind: 'bird', x: 4, z: 3 },
    ];
    const { life } = createLife({ actors, emitters: [] }, () => 3);
    const resident = objectNamed(life.group, 'resident');
    const deerHead = objectNamed(objectNamed(life.group, 'deer'), 'head');
    const birdWing = objectNamed(objectNamed(life.group, 'bird'), 'wing-left');
    const before = [resident.rotation.y, deerHead.rotation.x, birdWing.rotation.z];

    life.update(0.5, { x: 0, z: 0 }, 100);

    expect(resident.rotation.y).not.toBe(before[0]);
    expect(deerHead.rotation.x).not.toBe(before[1]);
    expect(birdWing.rotation.z).not.toBe(before[2]);
    for (const spawn of actors) {
      const object = objectNamed(life.group, spawn.id);
      expect(object.position.x).toBe(spawn.x);
      expect(object.position.z).toBe(spawn.z);
      if (spawn.kind !== 'bird') {
        expect(object.position.y).toBe(3);
        expect(objectNamed(object, 'leg-left').rotation.x).toBe(0);
      }
    }
  });

  test('produces the same rigs and particle positions across frame partitions and invalid deltas', () => {
    const definition: WorldLifeDefinition = {
      actors: [
        { id: 'walker', kind: 'guard', x: 0, z: 0, route: [{ x: 12, z: 16 }, { x: 20, z: 0 }], speed: 1.4 },
        { id: 'bird', kind: 'bird', x: 6, z: 3, route: [{ x: 18, z: 6 }] },
      ],
      emitters: [
        { id: 'smoke', kind: 'smoke', x: 3, z: 4 },
        { id: 'embers', kind: 'embers', x: 4, z: 4 },
        { id: 'motes', kind: 'motes', x: 5, z: 4 },
      ],
    };
    const { life: partitioned } = createLife(definition);
    const { life: singleFrame } = createLife(definition);
    for (let frame = 0; frame < 44; frame++) partitioned.update(0.125, { x: 0, z: 0 }, 100);
    singleFrame.update(5.5, { x: 0, z: 0 }, 100);
    for (const dt of [-1, Number.NaN, Number.POSITIVE_INFINITY]) partitioned.update(dt, { x: 0, z: 0 }, 100);

    expect(poseOf(partitioned.group)).toEqual(poseOf(singleFrame.group));
    for (const { id } of definition.emitters) {
      expect(emitterNamed(partitioned.group, id).geometry.getAttribute('position').array)
        .toEqual(emitterNamed(singleFrame.group, id).geometry.getAttribute('position').array);
    }
  });

  test('enforces independent actor, emitter, and particle budgets', () => {
    const actors: WorldLifeActorSpawn[] = Array.from({ length: 60 }, (_, index) => ({ id: `bird-${index}`, kind: 'bird', x: 0, z: 0 }));
    const { life: emitterLimited } = createLife({
      actors,
      emitters: Array.from({ length: 40 }, (_, index) => ({ id: `mote-${index}`, kind: 'motes', x: 0, z: 0, count: 1 })),
    });
    expect(emitterLimited.group.children.filter((object) => object instanceof THREE.Group)).toHaveLength(WORLD_LIFE_LIMITS.actors);
    expect(emitterLimited.group.children.filter((object) => object instanceof THREE.Points)).toHaveLength(WORLD_LIFE_LIMITS.emitters);

    const { life: particleLimited } = createLife({
      actors: [],
      emitters: Array.from({ length: 40 }, (_, index) => ({ id: `smoke-${index}`, kind: 'smoke', x: 0, z: 0, count: 100_000 })),
    });
    const points = particleLimited.group.children as THREE.Points[];
    expect(points.length).toBeLessThanOrEqual(WORLD_LIFE_LIMITS.emitters);
    expect(points.reduce((sum, point) => sum + point.geometry.getAttribute('position').count, 0)).toBe(WORLD_LIFE_LIMITS.particles);
    for (const point of points) expect(point.geometry.getAttribute('position').count).toBeLessThanOrEqual(48);
  });

  test('keeps all animated particle positions inside their authored culling bounds', () => {
    const { life } = createLife({
      actors: [],
      emitters: [
        { id: 'smoke', kind: 'smoke', x: 0, z: 0, radius: 20, count: 48 },
        { id: 'embers', kind: 'embers', x: 0, z: 0, radius: 20, count: 48 },
        { id: 'motes', kind: 'motes', x: 0, z: 0, radius: 20, count: 48 },
      ],
    });
    const point = new THREE.Vector3();
    for (let frame = 0; frame < 30; frame++) {
      life.update(0.7, { x: 0, z: 0 }, 100);
      for (const object of life.group.children as THREE.Points[]) {
        const positions = object.geometry.getAttribute('position');
        const bounds = object.geometry.boundingSphere!;
        expect(bounds).toBeInstanceOf(THREE.Sphere);
        for (let index = 0; index < positions.count; index++) {
          point.fromBufferAttribute(positions, index);
          expect(point.toArray().every(Number.isFinite)).toBe(true);
          expect(bounds.containsPoint(point)).toBe(true);
        }
      }
    }
  });

  test('animates cloth and flame metadata from their original authored transforms', () => {
    const campfire = buildWorldLifeProp('life_campfire')!;
    const clothesline = buildWorldLifeProp('life_clothesline')!;
    const flame = objectNamed(campfire, 'flame');
    const cloth = objectNamed(clothesline, 'cloth-0');
    flame.scale.y = 2;
    cloth.rotation.z = 0.3;
    const { life } = createLife(undefined, () => 0, [campfire, clothesline]);
    const flameBefore = flame.scale.y;
    const clothBefore = cloth.rotation.z;

    life.update(0.5, { x: 0, z: 0 }, 100);
    expect(flame.scale.y).not.toBe(flameBefore);
    expect(cloth.rotation.z).not.toBe(clothBefore);
    expect(flame.scale.y).toBeGreaterThanOrEqual(2 * 0.88);
    expect(flame.scale.y).toBeLessThanOrEqual(2 * 1.12);
    expect(Math.abs(cloth.rotation.z - 0.3)).toBeLessThanOrEqual(0.045);
    const pose = poseOf(campfire).concat(poseOf(clothesline));
    life.update(0, { x: 0, z: 0 }, 100);
    expect(poseOf(campfire).concat(poseOf(clothesline))).toEqual(pose);
  });

  test('detaches owned objects and disposes every unique resource once, including animated scenery', () => {
    const campfire = buildWorldLifeProp('life_campfire')!;
    const { life, scene } = createLife({
      actors: [{ id: 'guard', kind: 'guard', x: 0, z: 0 }],
      emitters: [{ id: 'smoke', kind: 'smoke', x: 0, z: 0 }],
    }, () => 0, [campfire]);
    const unrelated = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial());
    scene.add(unrelated);
    const unrelatedGeometry = vi.spyOn(unrelated.geometry, 'dispose');
    const unrelatedMaterial = vi.spyOn(unrelated.material, 'dispose');
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    const collect = (object: THREE.Object3D) => {
      if (!(object instanceof THREE.Mesh || object instanceof THREE.Points)) return;
      geometries.add(object.geometry);
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material);
    };
    life.group.traverse(collect);
    campfire.traverse(collect);
    expect(geometries.size).toBeGreaterThan(2);
    expect(materials.size).toBeGreaterThan(2);
    const disposeSpies = [...geometries, ...materials].map((resource) => vi.spyOn(resource, 'dispose'));
    const flame = objectNamed(campfire, 'flame');
    const flameBefore = flame.scale.y;

    life.dispose();
    life.dispose();
    life.update(10, { x: 0, z: 0 }, 100);

    expect(life.group.parent).toBeNull();
    expect(life.group.children).toHaveLength(0);
    expect(campfire.parent).toBeNull();
    expect(scene.children).toEqual([unrelated]);
    expect(flame.scale.y).toBe(flameBefore);
    for (const dispose of disposeSpies) expect(dispose).toHaveBeenCalledTimes(1);
    expect(unrelatedGeometry).not.toHaveBeenCalled();
    expect(unrelatedMaterial).not.toHaveBeenCalled();
    unrelated.geometry.dispose();
    unrelated.material.dispose();
  });
});
