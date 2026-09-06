import { describe, expect, test } from 'vitest';
import { ITEM_CATALOG, INVENTORY_CAPACITY } from '../src/data/items';
import { NOVITIATE_ARMOR_ITEM_CATALOG, NOVITIATE_ARMOR_PARTS, novitiateArmorEquipment } from '../src/data/novitiateArmor';
import { starterArmorEquipmentFor } from '../src/data/playableAssets.generated';
import { characterForArmorPreview, supportsNovitiatePreview } from '../src/ui/screens/armorPreview';
import type { CharacterState } from '../src/services/types';

function character(overrides: Partial<CharacterState> = {}): CharacterState {
  return {
    id: 'preview-fixture', name: 'Test', race: 'empire', className: 'Battle Prelate', bodyVariant: 'm',
    level: 1, xp: 0, zoneId: 'aegis_capital', health: 100, maxHealth: 100, mana: 60, maxMana: 60,
    strength: 10, gold: 25, position: { x: 2, y: 0, z: 3 }, rotationY: 0,
    equipment: { ...starterArmorEquipmentFor('empire', 'Battle Prelate', 'm'), mainHand: 'weapon_hammer_reliquary_2h',
      neck: { key: 'crafted_soldiers_seal', name: 'Seal', equipSlot: 'neck', affix: { strengthBonus: 3 } } },
    ...overrides,
  };
}

describe('Novitiate armor catalog and isolated preview', () => {
  test('adds exactly nine named armor items with the matching distinct model paths', () => {
    expect(Object.keys(NOVITIATE_ARMOR_ITEM_CATALOG)).toHaveLength(9);
    expect(new Set(NOVITIATE_ARMOR_PARTS.map(([slot]) => slot)).size).toBe(9);
    for (const [slot] of NOVITIATE_ARMOR_PARTS) {
      const key = `novitiate_civic_battle_prelate_${slot}_m`;
      expect(ITEM_CATALOG[key]).toMatchObject({ key, kind: 'armor', equipSlot: slot,
        visual: { model: `arm_civic_battle_prelate_${slot}_novitiate_m.glb`, fallback: 'overlay' } });
      expect(ITEM_CATALOG[key].name.startsWith('Novitiate ')).toBe(true);
      const starter = starterArmorEquipmentFor('empire', 'Battle Prelate', 'm')[slot];
      expect(ITEM_CATALOG[typeof starter === 'string' ? starter : starter!.key]).toBeDefined();
    }
  });

  test('keeps starter equipment and inventory capacity unchanged', () => {
    expect(INVENTORY_CAPACITY).toBe(24);
    const starter = starterArmorEquipmentFor('empire', 'Battle Prelate', 'm');
    expect(Object.values(starter).every((entry) => (typeof entry === 'string' ? entry : entry?.key)?.startsWith('starter_'))).toBe(true);
  });

  test('preview replaces only nine armor slots and leaves the original character and inventory untouched', () => {
    const source = character();
    const inventory = [{ key: 'potion_health', qty: 5, slot: 0 }];
    const before = structuredClone({ source, inventory });
    const preview = characterForArmorPreview(source, 'novitiate');
    expect(preview.equipment?.mainHand).toBe(source.equipment?.mainHand);
    expect(preview.equipment?.neck).toEqual(source.equipment?.neck);
    for (const [slot] of NOVITIATE_ARMOR_PARTS) {
      expect(preview.equipment?.[slot]).toMatchObject({ key: `novitiate_civic_battle_prelate_${slot}_m` });
    }
    preview.position.x = 999;
    const neck = preview.equipment?.neck;
    if (neck && typeof neck !== 'string') neck.affix!.strengthBonus = 999;
    expect({ source, inventory }).toEqual(before);
    expect(source.gold).toBe(25);
  });

  test('current preview is also a deep copy and switching back restores the actual loadout', () => {
    const source = character();
    characterForArmorPreview(source, 'novitiate');
    const current = characterForArmorPreview(source, 'current');
    expect(current).toEqual(source);
    expect(current).not.toBe(source);
    expect(current.equipment).not.toBe(source.equipment);
  });

  test.each([
    { bodyVariant: 'f' as const }, { race: 'dwarf' as const }, { className: 'Sunfire Templar' },
  ])('does not apply the male Battle Prelate set to incompatible character %j', (overrides) => {
    const source = character(overrides);
    expect(supportsNovitiatePreview(source)).toBe(false);
    expect(characterForArmorPreview(source, 'novitiate')).toEqual(source);
  });

  test('equipment snapshots do not share mutable entries', () => {
    const first = novitiateArmorEquipment();
    const second = novitiateArmorEquipment();
    expect(first).toEqual(second);
    expect(first.chest).not.toBe(second.chest);
    expect(supportsNovitiatePreview(null)).toBe(false);
  });
});
