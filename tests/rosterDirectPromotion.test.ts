import { describe, expect, it } from 'vitest';
import {
  canonicalCreatureRuntimeIds,
  canonicalNpcRuntimeIds,
  canonicalPlayableRuntimeIds,
} from '../scripts/blender-character-pipeline/tools/promote-roster-revision.mjs';

describe('direct roster promotion contract', () => {
  it('preserves the established playable runtime keys and neutral filenames', () => {
    expect(canonicalPlayableRuntimeIds({
      family: 'civic',
      key: 'battle_prelate',
      variant: 'm',
      slot: 'head',
    })).toEqual({
      profileKey: 'civic_battle_prelate_m',
      characterAssetId: 'chr.civic.battle_prelate.t1.m',
      characterModel: 'chr_civic_battle_prelate_t1_m.glb',
      armorAssetId: 'arm.civic.battle_prelate.head.t1.m',
      armorModel: 'arm_civic_battle_prelate_head_t1_m.glb',
      bodyFamily: 'civic_battle_prelate_m',
    });
  });

  it('supports a body-only runtime identity when no armor slot is supplied', () => {
    const ids = canonicalPlayableRuntimeIds({ family: 'mire', key: 'warbrute', variant: 'f' });
    expect(ids.profileKey).toBe('mire_warbrute_f');
    expect(ids.armorAssetId).toBeNull();
    expect(ids.armorModel).toBeNull();
  });

  it('maps NPC roles to neutral equipped runtime models', () => {
    expect(canonicalNpcRuntimeIds({ key: 'empire_m', role: 'guard', variant: 'm' })).toEqual({
      profileKey: 'empire_m',
      characterAssetId: 'chr.npc.empire.m',
      characterModel: 'chr_npc_empire_m_guard_m.glb',
    });
  });

  it('maps creature revisions to static runtime keys', () => {
    expect(canonicalCreatureRuntimeIds({ key: 'barrow_wolf' })).toEqual({
      staticKey: 'creature_barrow_wolf',
      assetId: 'creature.barrow_wolf.t1',
      model: 'prop_creature_barrow_wolf.glb',
    });
  });
});
