import { describe, expect, it } from 'vitest';
import { parityFeatures, validateParityLedger } from '../scripts/unreal/feature-parity';

describe('Unreal parity contract', () => {
  it('binds every contract to existing source and regression tests', () => {
    expect(validateParityLedger()).toEqual([]);
    expect(new Set(parityFeatures.map(feature => feature.id)).size).toBe(parityFeatures.length);
  });
  it('does not label inventory or a C++ scaffold as completed gameplay', () => {
    expect(parityFeatures.every(feature => feature.unrealStatus === 'pending')).toBe(true);
  });
  it('carries both local-only and shared-only systems, including runtime GM editing', () => {
    const ids = new Set(parityFeatures.map(feature => feature.id));
    for (const id of ['quests', 'crafting', 'inventory', 'reward-settlement', 'gm-terrain', 'gm-publication', 'supplies', 'siege', 'campaign-rounds', 'admission-reconnect', 'persistence', 'interiors', 'world-life']) expect(ids.has(id), id).toBe(true);
  });
});
