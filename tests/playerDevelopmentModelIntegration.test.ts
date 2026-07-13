import { describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import {
  BATTLE_PRELATE_DEVELOPMENT_MODEL,
  developmentCharacterAssetFor,
} from '../src/config/developmentModelCandidates';
import type { AssetLoader } from '../src/game/AssetLoader';
import { Player } from '../src/game/Player';
import type { Terrain } from '../src/world/Terrain';
import { makeCharacter } from './testUtils';

describe('Player development candidate integration', () => {
  test('loads the exact assembled visual and does not stack modular equipment over it', async () => {
    const candidate = developmentCharacterAssetFor('civic_battle_prelate_m', 'm', true);
    expect(candidate).not.toBeNull();

    const resolveCharacterAsset = vi.fn(async (profileKey: string) => (
      profileKey === 'civic_battle_prelate_m' ? candidate : null
    ));
    const loadModelFull = vi.fn(async () => ({
      object: new THREE.Group(),
      animations: [],
    }));
    const resolveEquipmentBaseBodyModel = vi.fn(async () => null);
    const resolveEquipmentModel = vi.fn();
    const loader = {
      resolveCharacterAsset,
      loadModelFull,
      resolveEquipmentBaseBodyModel,
      resolveEquipmentModel,
    } as unknown as AssetLoader;
    const scene = new THREE.Scene();
    const player = new Player(
      makeCharacter({ equipment: { mainHand: 'weapon_hammer_reliquary_2h' } }),
      { heightAt: () => 0 } as unknown as Terrain,
    );

    await player.build(loader, scene);
    await player.applyEquipmentVisuals(player.character.equipment, loader);

    expect(loadModelFull).toHaveBeenCalledWith(
      BATTLE_PRELATE_DEVELOPMENT_MODEL,
      expect.any(Function),
    );
    expect(resolveEquipmentBaseBodyModel).not.toHaveBeenCalled();
    expect(resolveEquipmentModel).not.toHaveBeenCalled();
    expect(scene.children).toContain(player.object);
  });
});
