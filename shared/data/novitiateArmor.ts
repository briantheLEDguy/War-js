import type { ItemDefinition } from './items';
import type { EquipmentState } from '../services/types';

export const NOVITIATE_ARMOR_PARTS = [
  ['head', 'Novitiate Gorget', '♙'],
  ['shoulders', 'Novitiate Shoulder Plates', '◆'],
  ['chest', 'Novitiate Cuirass', '♜'],
  ['hands', 'Novitiate Handguards', '✋'],
  ['waist', 'Novitiate Field Belt', '▰'],
  ['legs', 'Novitiate Legguards', '♜'],
  ['feet', 'Novitiate Boots', '♟'],
  ['back', 'Novitiate Backplate', '◇'],
  ['tabard', 'Novitiate Tabard', '⚑'],
] as const;

export const NOVITIATE_ARMOR_ITEM_CATALOG: Record<string, ItemDefinition> = Object.fromEntries(
  NOVITIATE_ARMOR_PARTS.map(([slot, name, icon]) => {
    const key = `novitiate_civic_battle_prelate_${slot}_m`;
    return [key, {
      key, name, icon, kind: 'armor', equipSlot: slot,
      visual: { model: `arm_civic_battle_prelate_${slot}_novitiate_m.glb`, fallback: 'overlay' },
    }];
  }),
);

/** Fresh snapshots for preview; this does not grant or equip inventory items. */
export function novitiateArmorEquipment(): EquipmentState {
  return Object.fromEntries(Object.values(NOVITIATE_ARMOR_ITEM_CATALOG).map((item) => [
    item.equipSlot!,
    { key: item.key, name: item.name, icon: item.icon, kind: item.kind, equipSlot: item.equipSlot! },
  ]));
}
