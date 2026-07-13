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

describe('Player authored weapon animation authority', () => {
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
});
