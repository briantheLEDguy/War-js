import { EQUIP_SLOT_ORDER, getItemDefinition, resolveInventoryItem } from '../data/items';
import { services } from '../services';
import type {
  CharacterState,
  EquipmentEntry,
  EquipmentState,
  EquippedGear,
  EquipSlot,
  InventoryItem,
} from '../services/types';
import { useGameStore } from '../state/gameStore';

export function equippedGearFromInventoryItem(item: InventoryItem): EquippedGear | null {
  const resolved = resolveInventoryItem(item);
  if (!resolved.equipSlot) return null;
  return {
    key: resolved.key,
    name: resolved.name,
    icon: resolved.icon,
    kind: resolved.kind,
    equipSlot: resolved.equipSlot,
    inventorySlot: resolved.slot,
    affix: resolved.affix,
  };
}

export function normalizeEquippedGear(
  entry: EquipmentEntry | undefined,
  slot: EquipSlot,
  inventory: InventoryItem[] = [],
): EquippedGear | null {
  if (!entry) return null;

  const key = typeof entry === 'string' ? entry : entry.key;
  const def = getItemDefinition(key);
  const inventoryMatch =
    typeof entry !== 'string' && entry.inventorySlot !== undefined
      ? inventory.find((item) => item.slot === entry.inventorySlot && item.key === key)
      : inventory.find((item) => {
          const resolved = resolveInventoryItem(item);
          return item.key === key && resolved.equipSlot === slot;
        });
  const resolvedInventory = inventoryMatch ? resolveInventoryItem(inventoryMatch) : null;

  if (typeof entry === 'string') {
    return {
      key,
      name: resolvedInventory?.name ?? def?.name ?? key,
      icon: resolvedInventory?.icon ?? def?.icon,
      kind: resolvedInventory?.kind ?? def?.kind,
      equipSlot: resolvedInventory?.equipSlot ?? def?.equipSlot ?? slot,
      inventorySlot: inventoryMatch?.slot,
      affix: resolvedInventory?.affix,
    };
  }

  return {
    key,
    name: entry.name || resolvedInventory?.name || def?.name || key,
    icon: entry.icon ?? resolvedInventory?.icon ?? def?.icon,
    kind: entry.kind ?? resolvedInventory?.kind ?? def?.kind,
    equipSlot: entry.equipSlot ?? resolvedInventory?.equipSlot ?? def?.equipSlot ?? slot,
    inventorySlot: entry.inventorySlot ?? inventoryMatch?.slot,
    affix: entry.affix ?? resolvedInventory?.affix,
  };
}

export function getEquippedGear(
  character: CharacterState | null,
  slot: EquipSlot,
  inventory: InventoryItem[] = [],
): EquippedGear | null {
  if (!character) return null;
  return normalizeEquippedGear(character.equipment?.[slot], slot, inventory);
}

export function isInventoryItemEquipped(
  item: InventoryItem,
  equipment: EquipmentState | undefined,
): boolean {
  const resolved = resolveInventoryItem(item);
  if (!resolved.equipSlot) return false;
  const gear = normalizeEquippedGear(equipment?.[resolved.equipSlot], resolved.equipSlot, [item]);
  if (!gear || gear.key !== item.key) return false;
  return gear.inventorySlot === undefined || gear.inventorySlot === item.slot;
}

export function equipmentVisualSignature(equipment: EquipmentState | undefined): string {
  if (!equipment) return '';
  return EQUIP_SLOT_ORDER
    .map((slot) => {
      const entry = equipment[slot];
      const key = typeof entry === 'string' ? entry : entry?.key;
      return key ? `${slot}:${key}` : '';
    })
    .filter(Boolean)
    .join('|');
}

export function strengthFromEquipment(
  equipment: EquipmentState | undefined,
  inventory: InventoryItem[] = [],
): number {
  let bonus = 0;
  for (const slot of EQUIP_SLOT_ORDER) {
    const gear = normalizeEquippedGear(equipment?.[slot], slot, inventory);
    bonus += gear?.affix?.strengthBonus ?? 0;
  }
  return bonus;
}

export function baseStrengthForCharacter(
  character: Pick<CharacterState, 'strength' | 'equipment'>,
  inventory: InventoryItem[] = [],
): number {
  return character.strength - strengthFromEquipment(character.equipment, inventory);
}

export function effectiveStrength(
  character: Pick<CharacterState, 'strength' | 'equipment'>,
  equipment: EquipmentState | undefined,
  inventory: InventoryItem[] = [],
): number {
  return baseStrengthForCharacter(character, inventory) + strengthFromEquipment(equipment, inventory);
}

export function equipFromInventory(slot: number): void {
  const store = useGameStore.getState();
  const character = store.character;
  if (!character) return;

  const rawItem = store.inventory.find((item) => item.slot === slot);
  if (!rawItem) return;
  const item = resolveInventoryItem(rawItem);
  if (!item.equipSlot || (item.kind !== 'weapon' && item.kind !== 'armor')) return;

  const equippedGear = equippedGearFromInventoryItem(item);
  if (!equippedGear) return;

  const equipment: EquipmentState = {
    ...(character.equipment ?? {}),
    [item.equipSlot]: equippedGear,
  };
  const strength = effectiveStrength(character, equipment, store.inventory);

  store.updateCharacter({ equipment, strength });
  store.completeGuidedTask('equip');
  store.appendChat({
    id: `equip-${Date.now()}`,
    channel: 'system',
    from: 'System',
    body: `Equipped: ${item.name}${
      item.affix ? ` (+${item.affix.strengthBonus} Strength)` : ''
    }`,
    timestamp: Date.now(),
  });

  void services.characters.save(character.id, { equipment, strength }).catch(() => {});
}
