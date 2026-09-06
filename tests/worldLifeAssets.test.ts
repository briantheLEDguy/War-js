import * as THREE from 'three';
import { describe, expect, it } from 'vitest';
import { buildWorldLifeActor, buildWorldLifeProp, WORLD_LIFE_PROP_KINDS } from '../src/world/WorldLifeAssets';

function inspect(object: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  let meshes = 0;
  let vertices = 0;
  object.traverse(node => {
    expect(node).not.toBeInstanceOf(THREE.Light);
    if (!(node instanceof THREE.Mesh)) return;
    meshes++;
    geometries.add(node.geometry);
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) materials.add(material);
    const positions = node.geometry.getAttribute('position');
    vertices += positions.count;
    expect(Array.from(positions.array).every(Number.isFinite)).toBe(true);
    expect(node.geometry.getAttribute('normal').count).toBe(positions.count);
  });
  return { geometries, materials, meshes, vertices, bounds: new THREE.Box3().setFromObject(object) };
}

function dispose(object: THREE.Object3D) {
  const { geometries, materials } = inspect(object);
  geometries.forEach(geometry => geometry.dispose());
  materials.forEach(material => material.dispose());
}

describe('world life scenery assets', () => {
  it.each(WORLD_LIFE_PROP_KINDS)('%s is grounded, compact, and has a bounded rendering cost', kind => {
    const object = buildWorldLifeProp(kind)!;
    const { bounds, meshes, vertices } = inspect(object);
    const size = bounds.getSize(new THREE.Vector3());
    expect(bounds.min.y).toBeGreaterThanOrEqual(-0.015);
    expect(bounds.min.y).toBeLessThan(0.04);
    expect(Math.max(size.x, size.y, size.z)).toBeGreaterThan(0.7);
    expect(Math.max(size.x, size.y, size.z)).toBeLessThan(4);
    expect(meshes).toBeLessThanOrEqual(8);
    expect(vertices).toBeLessThan(16000);
    expect(vertices).toBeGreaterThan(100);
    dispose(object);
  });

  it('lets unknown kinds continue through the existing fallback resolver', () => {
    expect(buildWorldLifeProp('unavailable-scenery')).toBeNull();
  });

  it.each(WORLD_LIFE_PROP_KINDS)('%s owns all geometry and materials independently', kind => {
    const first = buildWorldLifeProp(kind)!;
    const second = buildWorldLifeProp(kind)!;
    const a = inspect(first);
    const b = inspect(second);
    expect([...a.geometries].every(geometry => !b.geometries.has(geometry))).toBe(true);
    expect([...a.materials].every(material => !b.materials.has(material))).toBe(true);
    dispose(first);
    expect(inspect(second).bounds.equals(b.bounds)).toBe(true);
    dispose(second);
  });

  it('provides attachment pivots for cloth and flames without dynamic lights', () => {
    const clothesline = buildWorldLifeProp('life_clothesline')!;
    const fire = buildWorldLifeProp('life_campfire')!;
    const cloth = clothesline.getObjectByName('cloth-0')!;
    expect(cloth.userData.worldLifeAnimation).toBe('cloth');
    expect(cloth.position.y).toBeGreaterThan(2);
    const flame = fire.getObjectByName('flame')!;
    expect(flame.userData.worldLifeAnimation).toBe('flame');
    expect(flame.position.y).toBeGreaterThan(0);
    inspect(fire);
    dispose(clothesline);
    dispose(fire);
  });
});

describe('world life actor assets', () => {
  const kinds = ['citizen', 'guard', 'deer', 'bird'] as const;

  it.each(kinds)('%s is grounded and stays within a modest ambient actor budget', kind => {
    for (const realm of ['aegis', 'riftbound'] as const) {
      for (let variant = 0; variant < 4; variant++) {
        const actor = buildWorldLifeActor(kind, realm, variant);
        const { bounds, meshes, vertices } = inspect(actor);
        expect(bounds.min.y).toBeCloseTo(0, 5);
        expect(bounds.max.y).toBeLessThan(2.1);
        expect(meshes).toBeLessThanOrEqual(20);
        expect(vertices).toBeLessThan(12000);
        if (kind === 'citizen' || kind === 'guard') {
          expect(bounds.max.y).toBeGreaterThan(1.7);
          for (const name of ['leg-left', 'leg-right', 'arm-left', 'arm-right']) {
            expect(actor.getObjectByName(name)).toBeInstanceOf(THREE.Group);
          }
        }
        if (kind === 'deer') expect(actor.getObjectByName('head')).toBeInstanceOf(THREE.Group);
        if (kind === 'bird') {
          expect(actor.getObjectByName('wing-left')).toBeInstanceOf(THREE.Group);
          expect(actor.getObjectByName('wing-right')).toBeInstanceOf(THREE.Group);
        }
        dispose(actor);
      }
    }
  });

  it.each(kinds)('%s shares materials inside an actor, but never with another owned actor', kind => {
    const first = buildWorldLifeActor(kind, 'aegis', 0);
    const second = buildWorldLifeActor(kind, 'aegis', 0);
    const a = inspect(first);
    const b = inspect(second);
    expect(a.materials.size).toBeLessThan(a.meshes);
    expect([...a.materials].every(material => !b.materials.has(material))).toBe(true);
    expect([...a.geometries].every(geometry => !b.geometries.has(geometry))).toBe(true);
    expect(a.bounds.equals(b.bounds)).toBe(true);
    dispose(first);
    dispose(second);
  });

  it('articulates limbs without moving the body or its sibling limbs', () => {
    const actor = buildWorldLifeActor('citizen', 'aegis', 0);
    const leg = actor.getObjectByName('leg-left')!;
    const otherLeg = actor.getObjectByName('leg-right')!;
    const before = new THREE.Box3().setFromObject(leg);
    const otherBefore = new THREE.Box3().setFromObject(otherLeg);
    leg.rotation.x = 0.6;
    actor.updateMatrixWorld(true);
    expect(new THREE.Box3().setFromObject(leg).equals(before)).toBe(false);
    expect(new THREE.Box3().setFromObject(otherLeg).equals(otherBefore)).toBe(true);
    expect(actor.position.toArray()).toEqual([0, 0, 0]);
    dispose(actor);
  });
});
