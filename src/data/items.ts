import type {
  EquipmentEntry,
  EquipSlot,
  InventoryItem,
  ItemKind,
} from '../services/types';
import { PLAYABLE_ARMOR_ITEM_CATALOG } from './playableAssets.generated';

export interface ConsumableEffect {
  hp?: number;
  mp?: number;
  label: string;
}

export type EquipmentVisualFallback = 'chest' | 'head' | 'mainHand' | 'neck' | 'offHand' | 'overlay';
export type WeaponVisualKind =
  | 'sword'
  | 'staff'
  | 'hammer'
  | 'cleaver'
  | 'axe'
  | 'dagger'
  | 'spear'
  | 'bow'
  | 'gun'
  | 'shield'
  | 'focus'
  | 'generic';

export interface EquipmentVisualDefinition {
  /** Fallback model. Asset-index entries override this when available. */
  model: string;
  fallback: EquipmentVisualFallback;
}

export interface ItemDefinition {
  key: string;
  name: string;
  icon: string;
  kind: ItemKind;
  equipSlot?: EquipSlot;
  consumable?: ConsumableEffect;
  visual?: EquipmentVisualDefinition;
  weaponKind?: WeaponVisualKind;
}

const equipmentModel = (key: string) => `equipment_${key}.glb`;

export const INVENTORY_CAPACITY = 24;

export const EQUIP_SLOT_ORDER: EquipSlot[] = [
  'head',
  'neck',
  'shoulders',
  'chest',
  'hands',
  'waist',
  'legs',
  'feet',
  'back',
  'tabard',
  'mainHand',
  'offHand',
];

export const EQUIP_SLOT_LABELS: Record<EquipSlot, string> = {
  head: 'Head',
  neck: 'Neck',
  shoulders: 'Shoulders',
  chest: 'Chest',
  hands: 'Hands',
  waist: 'Waist',
  legs: 'Legs',
  feet: 'Feet',
  back: 'Back',
  tabard: 'Tabard',
  mainHand: 'Main Hand',
  offHand: 'Off Hand',
};

const BASE_ITEM_CATALOG: Record<string, ItemDefinition> = {
  sword_iron: {
    key: 'sword_iron',
    name: 'Iron Sword',
    icon: '\u2694',
    kind: 'weapon',
    equipSlot: 'mainHand',
    visual: { model: equipmentModel('sword_iron'), fallback: 'mainHand' },
    weaponKind: 'sword',
  },
  sword_recruit: {
    key: 'sword_recruit',
    name: 'Reikguard Recruit Sword',
    icon: '\u2694',
    kind: 'weapon',
    equipSlot: 'mainHand',
    visual: { model: equipmentModel('sword_recruit'), fallback: 'mainHand' },
    weaponKind: 'sword',
  },
  sword_veteran: {
    key: 'sword_veteran',
    name: "Veteran's Greatsword",
    icon: '\u2694',
    kind: 'weapon',
    equipSlot: 'mainHand',
    visual: { model: equipmentModel('sword_veteran'), fallback: 'mainHand' },
    weaponKind: 'sword',
  },
  shield_wood: {
    key: 'shield_wood',
    name: 'Wooden Shield',
    icon: '\u{1F6E1}',
    kind: 'armor',
    equipSlot: 'offHand',
    visual: { model: equipmentModel('shield_wood'), fallback: 'offHand' },
    weaponKind: 'shield',
  },
  shield_steel: {
    key: 'shield_steel',
    name: 'Steel-Rimmed Shield',
    icon: '\u{1F6E1}',
    kind: 'armor',
    equipSlot: 'offHand',
    visual: { model: equipmentModel('shield_steel'), fallback: 'offHand' },
    weaponKind: 'shield',
  },
  weapon_hammer_reliquary_2h: {
    key: 'weapon_hammer_reliquary_2h',
    name: 'Reliquary Steel Maul',
    icon: '\u2692',
    kind: 'weapon',
    equipSlot: 'mainHand',
    visual: { model: 'wep_civic_battle_prelate_dawn_maul.glb', fallback: 'mainHand' },
    weaponKind: 'hammer',
  },
  weapon_warbrute_cleaver: {
    key: 'weapon_warbrute_cleaver',
    name: 'Mirejaw Cleaver',
    icon: '\u2692',
    kind: 'weapon',
    equipSlot: 'mainHand',
    visual: { model: 'wep_mire_warbrute_mirejaw_cleaver.glb', fallback: 'mainHand' },
    weaponKind: 'cleaver',
  },
  jewel_amulet_bloodglass: {
    key: 'jewel_amulet_bloodglass',
    name: 'Bloodglass Amulet',
    icon: '\u25C8',
    kind: 'armor',
    equipSlot: 'neck',
    visual: { model: 'jwl_amulet_bloodglass_t1.glb', fallback: 'neck' },
  },
  armor_chain: {
    key: 'armor_chain',
    name: 'Reikguard Chain Hauberk',
    icon: '\u{1F9E5}',
    kind: 'armor',
    equipSlot: 'chest',
    visual: { model: equipmentModel('armor_chain'), fallback: 'chest' },
  },
  helm_reikguard: {
    key: 'helm_reikguard',
    name: 'Reikguard Helm',
    icon: '\u{1FA96}',
    kind: 'armor',
    equipSlot: 'head',
    visual: { model: equipmentModel('helm_reikguard'), fallback: 'head' },
  },
  base_male_blackened_chest: {
    key: 'base_male_blackened_chest',
    name: 'Blackened Plate Cuirass',
    icon: '\u{1F9E5}',
    kind: 'armor',
    equipSlot: 'chest',
    visual: { model: 'arm_human_chest_blackened_plate_t1_m.glb', fallback: 'chest' },
  },
  base_male_blackened_shoulders: {
    key: 'base_male_blackened_shoulders',
    name: 'Blackened Plate Pauldrons',
    icon: '\u{1FA96}',
    kind: 'armor',
    equipSlot: 'shoulders',
    visual: { model: 'arm_human_shoulders_blackened_plate_t1_m.glb', fallback: 'overlay' },
  },
  base_male_blackened_bracers: {
    key: 'base_male_blackened_bracers',
    name: 'Blackened Bracers',
    icon: '\u{1F9E4}',
    kind: 'armor',
    equipSlot: 'hands',
    visual: { model: 'arm_human_hands_blackened_bracers_t1_m.glb', fallback: 'overlay' },
  },
  base_male_blackened_belt: {
    key: 'base_male_blackened_belt',
    name: 'Blackened War Belt',
    icon: '\u{1F9F5}',
    kind: 'armor',
    equipSlot: 'waist',
    visual: { model: 'arm_human_waist_blackened_belt_t1_m.glb', fallback: 'overlay' },
  },
  base_male_blackened_legs: {
    key: 'base_male_blackened_legs',
    name: 'Blackened Leg Harness',
    icon: '\u{1F9E6}',
    kind: 'armor',
    equipSlot: 'legs',
    visual: { model: 'arm_human_legs_blackened_plate_t1_m.glb', fallback: 'overlay' },
  },
  base_male_blackened_boots: {
    key: 'base_male_blackened_boots',
    name: 'Blackened Plate Boots',
    icon: '\u{1F462}',
    kind: 'armor',
    equipSlot: 'feet',
    visual: { model: 'arm_human_feet_blackened_boots_t1_m.glb', fallback: 'overlay' },
  },
  base_male_oath_tabard: {
    key: 'base_male_oath_tabard',
    name: 'Oathbound Tabard',
    icon: '\u{1F9E3}',
    kind: 'armor',
    equipSlot: 'tabard',
    visual: { model: 'arm_human_tabard_oathcloth_t1_m.glb', fallback: 'overlay' },
  },
  base_male_crimson_cape: {
    key: 'base_male_crimson_cape',
    name: 'Crimson Campaign Cape',
    icon: '\u{1F9E3}',
    kind: 'armor',
    equipSlot: 'back',
    visual: { model: 'arm_human_back_crimson_cape_t1_m.glb', fallback: 'overlay' },
  },
  potion_health: {
    key: 'potion_health',
    name: 'Health Potion',
    icon: '\u{1F9EA}',
    kind: 'consumable',
    consumable: { hp: 50, label: 'Restores 50 HP' },
  },
  potion_mana: {
    key: 'potion_mana',
    name: 'Mana Potion',
    icon: '\u{1F9EA}',
    kind: 'consumable',
    consumable: { mp: 50, label: 'Restores 50 Mana' },
  },
  bread: {
    key: 'bread',
    name: 'Hunk of Bread',
    icon: '\u{1F35E}',
    kind: 'consumable',
    consumable: { hp: 20, label: 'Restores 20 HP' },
  },
  potion_rejuvenation: {
    key: 'potion_rejuvenation',
    name: 'Rejuvenating Draught',
    icon: '\u{1F9EA}',
    kind: 'consumable',
    consumable: { hp: 35, mp: 35, label: 'Restores 35 HP and 35 Mana' },
  },
  craft_scrap_iron: {
    key: 'craft_scrap_iron',
    name: 'Scrap Iron',
    icon: '\u2699',
    kind: 'material',
  },
  craft_torn_cloth: {
    key: 'craft_torn_cloth',
    name: 'Torn Cloth',
    icon: '\u25A7',
    kind: 'material',
  },
  craft_ragged_leather: {
    key: 'craft_ragged_leather',
    name: 'Ragged Leather',
    icon: '\u25A8',
    kind: 'material',
  },
  craft_bone_chips: {
    key: 'craft_bone_chips',
    name: 'Bone Chips',
    icon: '\u25C7',
    kind: 'material',
  },
  craft_goblin_trinket: {
    key: 'craft_goblin_trinket',
    name: 'Goblin Trinket',
    icon: '\u25C9',
    kind: 'material',
  },
  craft_mandrake_root: {
    key: 'craft_mandrake_root',
    name: 'Mandrake Root',
    icon: '\u2736',
    kind: 'material',
  },
  craft_goldweed: {
    key: 'craft_goldweed',
    name: 'Goldweed',
    icon: '\u2739',
    kind: 'material',
  },
  craft_clear_water: {
    key: 'craft_clear_water',
    name: 'Clear Water',
    icon: '\u25CC',
    kind: 'material',
  },
  craft_fertile_soil: {
    key: 'craft_fertile_soil',
    name: 'Fertile Soil',
    icon: '\u25A6',
    kind: 'material',
  },
  craft_vial_cloudy: {
    key: 'craft_vial_cloudy',
    name: 'Clouded Vial',
    icon: '\u25C7',
    kind: 'material',
  },
  craft_stabilizing_salt: {
    key: 'craft_stabilizing_salt',
    name: 'Stabilizing Salt',
    icon: '\u2219',
    kind: 'material',
  },
  craft_arcane_dust: {
    key: 'craft_arcane_dust',
    name: 'Arcane Dust',
    icon: '\u2726',
    kind: 'material',
  },
  craft_talisman_fragment: {
    key: 'craft_talisman_fragment',
    name: 'Talisman Fragment',
    icon: '\u25C8',
    kind: 'material',
  },
  craft_essence_minor: {
    key: 'craft_essence_minor',
    name: 'Minor Essence',
    icon: '\u25C7',
    kind: 'material',
  },
  seed_mandrake: {
    key: 'seed_mandrake',
    name: 'Mandrake Seed',
    icon: '\u2736',
    kind: 'seed',
  },
  seed_goldweed: {
    key: 'seed_goldweed',
    name: 'Goldweed Seed',
    icon: '\u2739',
    kind: 'seed',
  },
  crafted_minor_strength_talisman: {
    key: 'crafted_minor_strength_talisman',
    name: 'Minor Might Talisman',
    icon: '\u25C8',
    kind: 'armor',
    equipSlot: 'neck',
  },
  crafted_soldiers_seal: {
    key: 'crafted_soldiers_seal',
    name: "Soldier's Seal",
    icon: '\u25C8',
    kind: 'armor',
    equipSlot: 'neck',
  },
};

export const ITEM_CATALOG: Record<string, ItemDefinition> = {
  ...BASE_ITEM_CATALOG,
  ...PLAYABLE_ARMOR_ITEM_CATALOG,
};

export function getItemDefinition(key: string): ItemDefinition | undefined {
  return ITEM_CATALOG[key];
}

export function getConsumableEffect(key: string): ConsumableEffect | undefined {
  return ITEM_CATALOG[key]?.consumable;
}

export function getEquipmentVisualForKey(
  key: string,
): EquipmentVisualDefinition | undefined {
  return ITEM_CATALOG[key]?.visual;
}

export function equipmentEntryKey(entry: EquipmentEntry | undefined): string | null {
  if (!entry) return null;
  return typeof entry === 'string' ? entry : entry.key;
}

export function resolveInventoryItem(item: InventoryItem): InventoryItem {
  const def = getItemDefinition(item.key);
  return {
    ...item,
    name: item.name || def?.name || item.key,
    icon: item.icon ?? def?.icon,
    kind: item.kind ?? def?.kind,
    equipSlot: item.equipSlot ?? def?.equipSlot,
  };
}

export function createInventoryItem(
  key: string,
  slot: number,
  overrides: Partial<Omit<InventoryItem, 'key' | 'slot'>> = {},
): InventoryItem {
  const def = getItemDefinition(key);
  return {
    slot,
    key,
    name: overrides.name ?? def?.name ?? key,
    qty: overrides.qty ?? 1,
    icon: overrides.icon ?? def?.icon,
    kind: overrides.kind ?? def?.kind,
    equipSlot: overrides.equipSlot ?? def?.equipSlot,
    affix: overrides.affix,
  };
}
