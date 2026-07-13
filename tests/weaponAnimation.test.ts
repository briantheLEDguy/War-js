import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import {
  inferWeaponKindFromText,
  markImportedWeaponAttachments,
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

  test('marks only the highest imported weapon attachment root', () => {
    const character = new THREE.Group();
    const hammerRoot = new THREE.Group();
    hammerRoot.name = 'battle_prelate_hammer_root';
    hammerRoot.userData.assetCategory = 'weapon';
    hammerRoot.userData.assetSlot = 'mainHand';
    const hammerMesh = new THREE.Group();
    hammerMesh.name = 'battle_prelate_hammer_mesh';
    hammerMesh.userData.assetCategory = 'weapon';
    hammerMesh.userData.assetSlot = 'mainHand';
    hammerRoot.add(hammerMesh);
    character.add(hammerRoot);

    markImportedWeaponAttachments(character);

    expect(hammerRoot.userData).toMatchObject({
      weaponAttachment: true,
      weaponSlot: 'mainHand',
      weaponKind: 'hammer',
      weaponSource: 'baked',
    });
    expect(hammerMesh.userData.weaponAttachment).not.toBe(true);
    expect(hammerMesh.userData.weaponSlot).toBeUndefined();
  });

  test('restricts authored-clip procedural motion to equipment overlays', () => {
    const root = new THREE.Group();
    const bakedHammer = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'hammer',
      source: 'baked',
    });
    const equipmentHammer = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'hammer',
      source: 'equipment',
    });
    root.add(bakedHammer, equipmentHammer);

    const controller = new WeaponAnimationController(root);
    controller.refreshTargets();
    // Simulate an authored GLB track updating the embedded attachment after
    // the procedural controller captured its bind/rest transform.
    bakedHammer.rotation.x = 0.35;
    controller.play({
      actionId: 'light_attack_a',
      durationSec: 0.58,
      shape: 'melee',
      school: 'holy',
      motion: 'jab',
      targetSources: ['equipment'],
    });
    controller.update(0.24);

    expect(bakedHammer.rotation.x).toBeCloseTo(0.35);
    expect(bakedHammer.rotation.y).toBeCloseTo(0);
    expect(bakedHammer.rotation.z).toBeCloseTo(0);
    expect(Math.abs(equipmentHammer.rotation.x)).toBeGreaterThan(0.1);
  });

  test('releases a previously controlled baked target before authored motion takes over', () => {
    const root = new THREE.Group();
    const bakedHammer = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'hammer',
      source: 'baked',
    });
    const equipmentHammer = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'hammer',
      source: 'equipment',
    });
    root.add(bakedHammer, equipmentHammer);

    const controller = new WeaponAnimationController(root);
    controller.play({
      actionId: 'fallback_attack',
      durationSec: 0.58,
      shape: 'melee',
      motion: 'jab',
      targetSources: ['baked'],
    });
    controller.update(0.18);
    expect(Math.abs(bakedHammer.rotation.x)).toBeGreaterThan(0.1);

    controller.play({
      actionId: 'light_attack_a',
      durationSec: 0.58,
      shape: 'melee',
      motion: 'jab',
      targetSources: ['equipment'],
    });
    expect(bakedHammer.rotation.x).toBeCloseTo(0);

    // The mixer evaluates after the source hand-off. Procedural updates must
    // leave that newly authored local transform intact.
    bakedHammer.rotation.x = 0.42;
    controller.update(0.18);
    expect(bakedHammer.rotation.x).toBeCloseTo(0.42);
    expect(Math.abs(equipmentHammer.rotation.x)).toBeGreaterThan(0.1);
  });

  test('keeps procedural baked-weapon motion when no authored clip owns it', () => {
    const root = new THREE.Group();
    const bakedHammer = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'hammer',
      source: 'baked',
    });
    root.add(bakedHammer);

    const controller = new WeaponAnimationController(root);
    controller.play({
      actionId: 'light_attack_a',
      durationSec: 0.58,
      shape: 'melee',
      school: 'holy',
      motion: 'jab',
    });
    controller.update(0.24);

    expect(Math.abs(bakedHammer.rotation.x)).toBeGreaterThan(0.1);
  });

  test('infers supported weapon families from item-like text', () => {
    expect(inferWeaponKindFromText('Veteran Greatsword')).toBe('sword');
    expect(inferWeaponKindFromText('Runed staff')).toBe('staff');
    expect(inferWeaponKindFromText('Dusk glaive')).toBe('spear');
    expect(inferWeaponKindFromText('Hand pistol')).toBe('gun');
  });
});
