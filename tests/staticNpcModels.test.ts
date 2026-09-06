import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { aegisNpcCivilianVariantFor } from '../src/data/modelOverrides';
import { spawnNpcs } from '../src/world/NpcSpawner';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Terrain } from '../src/world/Terrain';
import type { NpcSpawn } from '../src/world/ZoneLoader';

describe('reviewed stationary Aegis people', () => {
  test('assigns service-appropriate reviewed models and preserves explicit civic or other-realm profiles', () => {
    expect(aegisNpcCivilianVariantFor('banker', 'npc_aegis_vault_keeper')?.profileKey).toBe('npc_aegis_people_attendant');
    expect(aegisNpcCivilianVariantFor('questgiver', 'npc_aegis_marshal')?.profileKey).toBe('npc_aegis_people_courtier');
    expect(aegisNpcCivilianVariantFor('trainer', 'npc_aegis_trainer')?.profileKey).toBe('npc_aegis_people_attendant');
    expect(aegisNpcCivilianVariantFor('vendor', 'npc_aegis_vendor', 'merchant_1')).toEqual(
      aegisNpcCivilianVariantFor('vendor', 'npc_aegis_vendor', 'merchant_1'));
    expect(aegisNpcCivilianVariantFor('ambient', 'npc_aegis_people_lady')).toBeNull();
    expect(aegisNpcCivilianVariantFor('guard', 'npc_aegis_gate_guard')).toBeNull();
    expect(aegisNpcCivilianVariantFor('vendor', 'npc_riftbound_vendor')).toBeNull();
    expect(aegisNpcCivilianVariantFor('ambient')).toBeNull();
  });

  test('uses direct reviewed fallback files when legacy profiles are absent while retaining NPC interaction state', async () => {
    const scene = new THREE.Scene();
    const requested: string[] = [];
    const loader = {
      resolveCharacterModel: async () => null,
      loadModelFull: async (model: string) => {
        requested.push(model);
        return { object: new THREE.Group(), animations: [new THREE.AnimationClip('idle', 2, [])] };
      },
    } as unknown as AssetLoader;
    const spawn: NpcSpawn = {
      id: 'vault_keeper', name: 'Mira Stonewake', title: 'Vault Keeper', role: 'banker',
      characterProfileKey: 'npc_aegis_mira_stonewake_vault_keeper', x: 12, y: 6, z: 18, rotY: .5,
    };
    const result = await spawnNpcs(scene, loader, { heightAt: () => 42 } as Terrain, [spawn], (_x, _z, height) => height!);
    expect(requested).toEqual(['chr_aegis_people_attendant_lod1.glb']);
    expect(result.states).toEqual([{
      id: spawn.id, name: spawn.name, title: spawn.title, role: spawn.role,
      position: { x: 12, y: 48, z: 18 },
    }]);
    expect(result.mixers).toHaveLength(1);
    expect(scene.children[0].rotation.y).toBe(.5);
  });
});
