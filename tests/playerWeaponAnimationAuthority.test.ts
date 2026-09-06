import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { getAbilityForCareer } from '../src/game/abilities/abilityData';
import type { AssetLoader } from '../src/game/AssetLoader';
import { Player } from '../src/game/Player';
import { markWeaponAttachment } from '../src/game/WeaponAnimation';
import type { Terrain } from '../src/world/Terrain';
import { makeCharacter } from './testUtils';

function importedHammerVisual(): { visual: THREE.Group; hammerRoot: THREE.Group } {
  const visual = new THREE.Group();
  const hammerRoot = new THREE.Group();
  hammerRoot.name = 'battle_prelate_hammer_root';
  hammerRoot.userData.assetCategory = 'weapon';
  hammerRoot.userData.assetSlot = 'mainHand';
  const hammerMesh = new THREE.Group();
  hammerMesh.name = 'battle_prelate_hammer_mesh';
  hammerMesh.userData.assetCategory = 'weapon';
  hammerMesh.userData.assetSlot = 'mainHand';
  hammerRoot.add(hammerMesh);
  visual.add(hammerRoot);
  return { visual, hammerRoot };
}

function loaderFor(
  visual: THREE.Object3D,
  animations: THREE.AnimationClip[],
): AssetLoader {
  return {
    resolveCharacterAsset: vi.fn(async () => ({
      assetId: 'chr.test.authored',
      model: 'authored-character.glb',
      bodyFamily: 'civic_humanoid_v2',
      bodyVariant: 'm',
      skeletonId: 'humanoid_game_v2',
      bindPoseId: 'a_pose_v2',
    })),
    loadModelFull: vi.fn(async () => ({ object: visual, animations })),
  } as unknown as AssetLoader;
}

function equipmentLoaderFor(
  visual: THREE.Object3D,
  animations: THREE.AnimationClip[],
): AssetLoader {
  return {
    ...loaderFor(visual, animations),
    resolveEquipmentBaseBodyModel: vi.fn(async () => null),
    resolveEquipmentModel: vi.fn(async () => ({
      model: 'blocked-hammer.glb',
      bodyModel: null,
      disabled: true,
    })),
  } as unknown as AssetLoader;
}

async function buildPlayer(
  visual: THREE.Object3D,
  animations: THREE.AnimationClip[],
): Promise<Player> {
  const player = new Player(
    makeCharacter(),
    { heightAt: () => 0 } as unknown as Terrain,
  );
  await player.build(loaderFor(visual, animations), new THREE.Scene());
  return player;
}

async function buildSocketEquipmentPlayer(options: {
  authoredClip?: boolean;
  fallback?: boolean;
  sourceRecords?: boolean;
  declaredSocket?: string;
} = {}): Promise<{ player: Player; socket: THREE.Object3D; hand: THREE.Bone; overlay: THREE.Object3D }> {
  const visual = new THREE.Group();
  const hand = new THREE.Bone();
  hand.name = 'hand_R';
  const socket = new THREE.Object3D();
  socket.name = 'socket_hand_R';
  socket.position.y = .12;
  hand.add(socket);
  visual.add(hand);
  const animations = [new THREE.AnimationClip('idle', 1, []), new THREE.AnimationClip('walk', 1, [])];
  if (options.authoredClip !== false) {
    const turn = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), .8);
    animations.push(new THREE.AnimationClip('attack_melee', 1, [
      new THREE.QuaternionKeyframeTrack('hand_R.quaternion', [0, 1], [0, 0, 0, 1, ...turn.toArray()]),
    ]));
  }
  const imported = new THREE.Group();
  const mesh = new THREE.Group();
  mesh.userData = {
    socket: options.declaredSocket ?? 'socket_hand_R',
    primary_grip_local: [0, 0, 0],
    geometry_provenance: 'Explicit authored source records evaluated with permitted finishing',
    ...(options.sourceRecords === false ? {} : {
      source_records: JSON.stringify([{ file: 'source/warhammer.json', part: 'warhammer_head', sha256: 'a'.repeat(64) }]),
    }),
  };
  imported.add(mesh);
  const loader = {
    ...loaderFor(visual, animations),
    resolveEquipmentBaseBodyModel: vi.fn(async () => null),
    resolveEquipmentModel: vi.fn(async () => ({
      model: 'authored-socket-hammer.glb', bodyModel: null, skinned: false, disabled: options.fallback === true,
    })),
    loadModel: vi.fn(async () => imported),
  } as unknown as AssetLoader;
  const player = new Player(makeCharacter(), { heightAt: () => 0 } as unknown as Terrain);
  await player.build(loader, new THREE.Scene());
  await player.applyEquipmentVisuals({ mainHand: 'weapon_hammer_reliquary_2h' }, loader);
  const overlay = player.object.getObjectByName('EquipmentOverlay_mainHand_weapon_hammer_reliquary_2h');
  expect(overlay).toBeDefined();
  return { player, socket, hand, overlay: overlay! };
}

describe('Player authored weapon animation authority', () => {
  test('keeps the calibrated imported grip on the moving authored hand without a second weapon offset', async () => {
    const { player, socket, hand, overlay } = await buildSocketEquipmentPlayer();
    const ability = getAbilityForCareer('Battle Prelate', 0)!;
    const slam = { ...ability, visual: { ...ability.visual, vfx: { ...ability.visual.vfx, motion: 'slam' as const } } };
    player.playGlbAction(slam.animation.actionId, slam.animation.durationSec);
    player.playAbilityWeaponAction(slam);
    player.updateVisuals(.24);

    expect(Math.abs(hand.rotation.z)).toBeGreaterThan(.1);
    expect(overlay.parent).toBe(socket);
    expect(overlay.position.toArray()).toEqual([0, 0, 0]);
    expect(overlay.quaternion.angleTo(new THREE.Quaternion())).toBeCloseTo(0);
    player.object.updateMatrixWorld(true);
    expect(overlay.getWorldPosition(new THREE.Vector3()).distanceTo(socket.getWorldPosition(new THREE.Vector3()))).toBeLessThan(1e-6);
    expect(overlay.getWorldQuaternion(new THREE.Quaternion()).angleTo(socket.getWorldQuaternion(new THREE.Quaternion()))).toBeLessThan(1e-6);
  });

  test.each([
    ['procedural fallback', { fallback: true }],
    ['missing authored action', { authoredClip: false }],
    ['missing source provenance', { sourceRecords: false }],
    ['different declared socket', { declaredSocket: 'socket_hand_L' }],
  ] as const)('preserves procedural ability motion for %s', async (_label, options) => {
    const { player, overlay } = await buildSocketEquipmentPlayer(options);
    player.playAbilityWeaponAction(getAbilityForCareer('Battle Prelate', 0)!);
    player.updateVisuals(.24);
    expect(Math.abs(overlay.rotation.x)).toBeGreaterThan(.1);
  });

  test('restores a prior procedural action before authored socket motion takes over', async () => {
    const { player, overlay } = await buildSocketEquipmentPlayer();
    player.playWeaponAction({ actionId: 'unmapped_action', durationSec: .6, motion: 'slam' });
    player.updateVisuals(.18);
    expect(Math.abs(overlay.rotation.x)).toBeGreaterThan(.1);
    expect(overlay.position.y).toBeGreaterThan(.05);

    const ability = getAbilityForCareer('Battle Prelate', 0)!;
    player.playGlbAction(ability.animation.actionId, ability.animation.durationSec);
    player.playAbilityWeaponAction(ability);
    expect(overlay.position.toArray()).toEqual([0, 0, 0]);
    expect(overlay.quaternion.angleTo(new THREE.Quaternion())).toBeCloseTo(0);
    player.updateVisuals(.18);
    expect(overlay.position.toArray()).toEqual([0, 0, 0]);
    expect(overlay.quaternion.angleTo(new THREE.Quaternion())).toBeCloseTo(0);
  });

  test('keeps the embedded weapon authored while an equipment overlay receives procedural motion', async () => {
    const { visual, hammerRoot } = importedHammerVisual();
    const player = await buildPlayer(
      visual,
      [new THREE.AnimationClip('attack_melee', 1, [])],
    );
    const equipmentHammer = markWeaponAttachment(new THREE.Group(), {
      slot: 'mainHand',
      kind: 'hammer',
      source: 'equipment',
    });
    player.object.add(equipmentHammer);
    const ability = getAbilityForCareer('Battle Prelate', 0);
    expect(ability).not.toBeNull();

    player.playAbilityWeaponAction(ability!);
    player.updateVisuals(0.24);

    expect(hammerRoot.userData.weaponAttachment).toBe(true);
    expect(hammerRoot.rotation.x).toBeCloseTo(0);
    expect(hammerRoot.rotation.y).toBeCloseTo(0);
    expect(hammerRoot.rotation.z).toBeCloseTo(0);
    expect(Math.abs(equipmentHammer.rotation.x)).toBeGreaterThan(0.1);
  });

  test('falls back to procedural motion for an embedded weapon when the mapped clip is absent', async () => {
    const { visual, hammerRoot } = importedHammerVisual();
    const player = await buildPlayer(
      visual,
      [new THREE.AnimationClip('idle', 1, [])],
    );
    const ability = getAbilityForCareer('Battle Prelate', 0);
    expect(ability).not.toBeNull();

    player.playAbilityWeaponAction(ability!);
    player.updateVisuals(0.24);

    expect(Math.abs(hammerRoot.rotation.x)).toBeGreaterThan(0.1);
  });

  test('keeps a procedural weapon visible when the authored weapon is blocked', async () => {
    const player = await buildPlayer(new THREE.Group(), []);
    await player.applyEquipmentVisuals(
      { mainHand: 'weapon_hammer_reliquary_2h' },
      equipmentLoaderFor(new THREE.Group(), []),
    );

    const overlay = player.object.getObjectByName(
      'EquipmentOverlay_mainHand_weapon_hammer_reliquary_2h',
    );
    expect(overlay).toBeDefined();
    expect(overlay?.userData.weaponSource).toBe('equipment');
    expect(overlay?.getObjectByName('FallbackHammerHead')).toBeDefined();
  });

  test('parents rigid equipment to the canonical hand socket', async () => {
    const visual = new THREE.Group();
    const rightSocket = new THREE.Object3D();
    rightSocket.name = 'socket_hand_R';
    visual.add(rightSocket);
    const player = await buildPlayer(visual, []);

    await player.applyEquipmentVisuals(
      { mainHand: 'weapon_hammer_reliquary_2h' },
      equipmentLoaderFor(new THREE.Group(), []),
    );

    const overlay = player.object.getObjectByName(
      'EquipmentOverlay_mainHand_weapon_hammer_reliquary_2h',
    );
    expect(overlay?.parent).toBe(rightSocket);
    expect(overlay?.position.toArray()).toEqual([0, 0, 0]);
    expect(overlay?.rotation.toArray()).toEqual([0, 0, 0, 'XYZ']);
  });

  test('calibrates procedural sword geometry into a guarded carry pose', async () => {
    const visual = new THREE.Group();
    const rightSocket = new THREE.Object3D();
    rightSocket.name = 'socket_hand_R';
    visual.add(rightSocket);
    const player = await buildPlayer(visual, []);

    await player.applyEquipmentVisuals(
      { mainHand: 'sword_iron' },
      equipmentLoaderFor(new THREE.Group(), []),
    );

    const overlay = player.object.getObjectByName('EquipmentOverlay_mainHand_sword_iron');
    expect(overlay?.parent).toBe(rightSocket);
    expect(overlay?.userData.equipmentFallback).toBe(true);
    const carryDirection = new THREE.Vector3(0, 1, 0)
      .applyQuaternion(overlay!.quaternion);
    expect(carryDirection.y).toBeLessThan(-0.8);
  });

  test('lowers a procedural shield from the wrist socket onto the forearm', async () => {
    const visual = new THREE.Group();
    const leftSocket = new THREE.Object3D();
    leftSocket.name = 'socket_hand_L';
    visual.add(leftSocket);
    const player = await buildPlayer(visual, []);

    await player.applyEquipmentVisuals(
      { offHand: 'shield_steel' },
      equipmentLoaderFor(new THREE.Group(), []),
    );

    const overlay = player.object.getObjectByName('EquipmentOverlay_offHand_shield_steel');
    expect(overlay?.parent).toBe(leftSocket);
    expect(overlay?.userData.equipmentFallback).toBe(true);
    expect(overlay?.position.toArray()).toEqual([0, -0.045, 0.12]);
  });
});
