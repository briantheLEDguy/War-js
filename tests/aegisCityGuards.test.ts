import { describe, expect, test } from 'vitest';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { aegisEnemyGuardVariantFor, aegisNpcGuardVariantFor } from '../src/data/modelOverrides';

describe('Aegis civic guard loadouts', () => {
  test('distributes four stable guard variants without changing other NPCs', () => {
    const variants = new Set<string>();
    for (let i = 0; i < 32; i++) {
      const result = aegisNpcGuardVariantFor('guard', 'npc_aegis_gate_guard', `guard_${i}`);
      expect(result).toEqual(aegisNpcGuardVariantFor('guard', 'npc_aegis_gate_guard', `guard_${i}`));
      expect(result?.fallbackModel).toMatch(/^chr_aegis_city_guard_.*\.glb$/);
      variants.add(result!.profileKey);
    }
    expect(variants.size).toBe(4);
    expect(aegisNpcGuardVariantFor('vendor', 'npc_aegis_vendor')).toBeNull();
    expect(aegisNpcGuardVariantFor('guard', 'npc_riftbound_guard')).toBeNull();
  });

  test('respects named specialist roles and preserves enemy allegiance', () => {
    expect(aegisNpcGuardVariantFor('guard', 'npc_aegis_guard', 'gate_captain')?.profileKey).toBe('npc_aegis_city_guard_captain');
    expect(aegisNpcGuardVariantFor('guard', 'npc_aegis_guard', 'wall_crossbow')?.profileKey).toBe('npc_aegis_city_guard_crossbow');
    expect(aegisEnemyGuardVariantFor('guard', 'enemy_aegis_guard', 'Guard', 'halberd_post')?.profileKey).toBe('npc_aegis_city_guard_halberd');
    expect(aegisEnemyGuardVariantFor('guard', 'enemy_riftbound_guard', 'Rift Guard')).toBeNull();
  });

  test('installed guards match the exports used for weapon contact review', () => {
    const root = 'public/assets/models/';
    const index = JSON.parse(readFileSync(root + 'asset-index.json', 'utf8'));
    const audit = JSON.parse(readFileSync(root + 'reviews/aegis-city-guards/exported-grip-audit.json', 'utf8'));
    expect(audit.max_gap_m).toBeLessThanOrEqual(0.015);
    for (const variant of ['standard', 'halberd', 'crossbow', 'captain']) {
      const entry = index.characterProfiles[`npc_aegis_city_guard_${variant}`];
      const hash = createHash('sha256').update(readFileSync(root + entry.model)).digest('hex');
      expect(hash).toBe(entry.modelSha256);
      expect(hash).toBe(audit.models[variant]);
    }
    for (const variant of ['halberd', 'crossbow']) {
      const samples = audit.samples.filter((s: { variant: string }) => s.variant === variant);
      expect(new Set(samples.map((s: { hand: string }) => s.hand))).toEqual(new Set(['L', 'R']));
      expect(samples).toHaveLength(90);
      expect(new Set(samples.map((s: { clip: string }) => s.clip)).size).toBe(9);
    }
  });
});
