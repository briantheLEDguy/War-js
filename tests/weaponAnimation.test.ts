import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import {
  inferWeaponKindFromText,
  markWeaponAttachment,
  WeaponAnimationController,
} from '../src/game/WeaponAnimation';

describe('weapon animation controller', () => {
  test('swings a sword and restores the rest pose after the action', () => {
    const root = new THREE.Group();
    const sword = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'sword',
    });
    root.add(sword);

    const controller = new WeaponAnimationController(root);
    controller.play({
      actionId: 'heavy_attack',
      durationSec: 0.6,
      shape: 'melee',
      school: 'physical',
      motion: 'cleave',
    });

    controller.update(0.24);
    expect(Math.abs(sword.rotation.z)).toBeGreaterThan(0.1);

    controller.update(0.8);
    expect(sword.rotation.x).toBeCloseTo(0);
    expect(sword.rotation.y).toBeCloseTo(0);
    expect(sword.rotation.z).toBeCloseTo(0);
  });

  test('points a staff toward a ranged target during projectile attacks', () => {
    const root = new THREE.Group();
    const staff = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'staff',
    });
    root.add(staff);

    const controller = new WeaponAnimationController(root);
    controller.play({
      actionId: 'cast_short',
      durationSec: 0.8,
      shape: 'projectile',
      school: 'fire',
      motion: 'shot',
      targetPosition: { x: 4, y: 0, z: 4 },
    });

    controller.update(0.32);
    expect(staff.rotation.x).toBeGreaterThan(1);
    expect(staff.rotation.y).toBeGreaterThan(0.1);
    expect(staff.position.z).toBeGreaterThan(0.05);
  });

  test('raises an off-hand shield for ward motions', () => {
    const root = new THREE.Group();
    const shield = markWeaponAttachment(new THREE.Group(), {
      slot: 'offHand',
      kind: 'shield',
    });
    root.add(shield);

    const controller = new WeaponAnimationController(root);
    controller.play({
      actionId: 'cast_short',
      durationSec: 0.7,
      shape: 'self',
      school: 'holy',
      motion: 'ward',
      abilityName: 'Shield of Noon',
    });

    controller.update(0.24);
    expect(shield.position.z).toBeGreaterThan(0.05);
    expect(shield.rotation.y).toBeLessThan(-0.1);
  });

  test('infers supported weapon families from item-like text', () => {
    expect(inferWeaponKindFromText('Veteran Greatsword')).toBe('sword');
    expect(inferWeaponKindFromText('Runed staff')).toBe('staff');
    expect(inferWeaponKindFromText('Dusk glaive')).toBe('spear');
    expect(inferWeaponKindFromText('Hand pistol')).toBe('gun');
  });
});
