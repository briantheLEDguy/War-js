import { createHash } from 'node:crypto';
import { describe, expect, test } from 'vitest';
import { ITEM_CATALOG } from '../src/data/items';
import {
  PLAYABLE_ARMOR_ITEM_CATALOG,
  PLAYABLE_ARMOR_SLOTS,
  PLAYABLE_CHARACTER_PROFILES,
  starterArmorEquipmentFor,
  starterArmorInventoryFor,
} from '../src/data/playableAssets.generated';

describe('playable starter armor catalog', () => {
  test('preserves the complete catalog when deriving entries from profiles', () => {
    // Captured from the literal catalog before removing its duplicate records.
    expect(Object.keys(PLAYABLE_ARMOR_ITEM_CATALOG)).toHaveLength(432);
    expect(createHash('sha256').update(JSON.stringify(PLAYABLE_ARMOR_ITEM_CATALOG)).digest('hex'))
      .toBe('8ba7f4a1915ea2ae83fe2c56b77449735734c223a466f07c2264e4f9da4271e6');
  });

  test('resolves every playable starting loadout through the shared item catalog', () => {
    expect(PLAYABLE_CHARACTER_PROFILES).toHaveLength(48);
    for (const profile of PLAYABLE_CHARACTER_PROFILES) {
      const equipment = starterArmorEquipmentFor(profile.race, profile.className, profile.bodyVariant);
      const inventory = starterArmorInventoryFor(profile.race, profile.className, profile.bodyVariant);
      expect(inventory).toHaveLength(PLAYABLE_ARMOR_SLOTS.length);
      for (const [index, slot] of PLAYABLE_ARMOR_SLOTS.entries()) {
        const equipped = equipment[slot];
        expect(equipped).toBeDefined();
        if (!equipped || typeof equipped === 'string') throw new Error(`Missing armor in ${profile.profileKey}/${slot}`);
        const item = ITEM_CATALOG[equipped.key];
        expect(item).toMatchObject(equipped);
        expect(item.visual).toEqual({ model: profile.armor[slot].model, fallback: 'overlay' });
        expect(inventory[index]).toEqual({ ...equipped, qty: 1, slot: index + 5 });
      }
    }
  });
});
