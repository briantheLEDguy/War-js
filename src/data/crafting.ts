import type {
  CraftingProfessionId,
  CraftingState,
  CraftingStationKind,
  EquipSlot,
  InventoryItem,
  ItemKind,
  ProfessionProgress,
} from '../services/types';

export interface CraftingItemStack {
  key: string;
  qty: number;
}

export interface CraftingRewardItem extends CraftingItemStack {
  name?: string;
  kind?: ItemKind;
  equipSlot?: EquipSlot;
  strengthRoll?: { min: number; max: number };
}

export interface CraftingRecipe {
  id: string;
  name: string;
  professionId: CraftingProfessionId;
  station: CraftingStationKind;
  minRank: number;
  inputs: CraftingItemStack[];
  outputs: CraftingRewardItem[];
  xp: number;
  summary: string;
}

export interface CultivationSeedDefinition {
  seedKey: string;
  name: string;
  durationMs: number;
  outputs: CraftingRewardItem[];
  bonusAdditiveKey?: string;
  bonusOutputs?: CraftingRewardItem[];
  xp: number;
}

export interface EnemyGatheringDefinition {
  professionId: Extract<CraftingProfessionId, 'scavenging' | 'butchering'>;
  actionLabel: string;
  corpseLabel: string;
  xp: number;
  loot: Array<CraftingRewardItem & { chance: number; minQty?: number; maxQty?: number }>;
}

export type GatheringLootEntry = CraftingRewardItem & {
  chance: number;
  minQty?: number;
  maxQty?: number;
};

export interface EnemyGatheringState {
  professionId: EnemyGatheringDefinition['professionId'];
  actionLabel: string;
  corpseLabel: string;
  harvested: boolean;
}

export const CRAFTING_XP_PER_RANK = 100;
export const CULTIVATION_SLOT_COUNT = 3;

export const CRAFTING_PROFESSIONS: Array<{
  id: CraftingProfessionId;
  label: string;
  description: string;
}> = [
  { id: 'scavenging', label: 'Scavenging', description: 'Recover useful supplies from humanoid corpses.' },
  { id: 'butchering', label: 'Butchering', description: 'Harvest hides, bone, and reagents from beasts.' },
  { id: 'salvaging', label: 'Salvaging', description: 'Break equipment into fragments and essences.' },
  { id: 'cultivation', label: 'Cultivation', description: 'Grow apothecary reagents from seeds.' },
  { id: 'apothecary', label: 'Apothecary', description: 'Brew restorative draughts from grown reagents.' },
  { id: 'talisman_making', label: 'Talisman Making', description: 'Bind fragments into stat-bearing charms.' },
];

export const CRAFTING_RECIPES: CraftingRecipe[] = [
  {
    id: 'apothecary_minor_health',
    name: 'Minor Healing Draught',
    professionId: 'apothecary',
    station: 'apothecary',
    minRank: 1,
    inputs: [
      { key: 'craft_vial_cloudy', qty: 1 },
      { key: 'craft_mandrake_root', qty: 2 },
      { key: 'craft_clear_water', qty: 1 },
    ],
    outputs: [{ key: 'potion_health', qty: 2 }],
    xp: 10,
    summary: 'Brew two health potions.',
  },
  {
    id: 'apothecary_minor_mana',
    name: 'Minor Restorative Draught',
    professionId: 'apothecary',
    station: 'apothecary',
    minRank: 1,
    inputs: [
      { key: 'craft_vial_cloudy', qty: 1 },
      { key: 'craft_goldweed', qty: 2 },
      { key: 'craft_clear_water', qty: 1 },
    ],
    outputs: [{ key: 'potion_mana', qty: 2 }],
    xp: 10,
    summary: 'Brew two mana potions.',
  },
  {
    id: 'apothecary_rejuvenation',
    name: 'Rejuvenating Draught',
    professionId: 'apothecary',
    station: 'apothecary',
    minRank: 2,
    inputs: [
      { key: 'craft_vial_cloudy', qty: 1 },
      { key: 'craft_mandrake_root', qty: 1 },
      { key: 'craft_goldweed', qty: 1 },
      { key: 'craft_stabilizing_salt', qty: 1 },
    ],
    outputs: [{ key: 'potion_rejuvenation', qty: 1 }],
    xp: 16,
    summary: 'Brew a draught that restores health and mana.',
  },
  {
    id: 'talisman_minor_might',
    name: 'Minor Might Talisman',
    professionId: 'talisman_making',
    station: 'talisman_making',
    minRank: 1,
    inputs: [
      { key: 'craft_talisman_fragment', qty: 2 },
      { key: 'craft_arcane_dust', qty: 1 },
      { key: 'craft_scrap_iron', qty: 2 },
    ],
    outputs: [
      {
        key: 'crafted_minor_strength_talisman',
        qty: 1,
        kind: 'armor',
        equipSlot: 'neck',
        strengthRoll: { min: 1, max: 2 },
      },
    ],
    xp: 14,
    summary: 'Bind a neck talisman with a small Strength roll.',
  },
  {
    id: 'talisman_soldiers_seal',
    name: "Soldier's Seal",
    professionId: 'talisman_making',
    station: 'talisman_making',
    minRank: 2,
    inputs: [
      { key: 'craft_talisman_fragment', qty: 3 },
      { key: 'craft_essence_minor', qty: 1 },
      { key: 'craft_goblin_trinket', qty: 1 },
      { key: 'craft_stabilizing_salt', qty: 1 },
    ],
    outputs: [
      {
        key: 'crafted_soldiers_seal',
        qty: 1,
        kind: 'armor',
        equipSlot: 'neck',
        strengthRoll: { min: 2, max: 4 },
      },
    ],
    xp: 20,
    summary: 'Create a stronger neck talisman from scavenged trinkets.',
  },
];

export const CULTIVATION_SEEDS: CultivationSeedDefinition[] = [
  {
    seedKey: 'seed_mandrake',
    name: 'Mandrake Seed',
    durationMs: 30_000,
    outputs: [{ key: 'craft_mandrake_root', qty: 2 }],
    bonusAdditiveKey: 'craft_fertile_soil',
    bonusOutputs: [{ key: 'craft_mandrake_root', qty: 1 }],
    xp: 8,
  },
  {
    seedKey: 'seed_goldweed',
    name: 'Goldweed Seed',
    durationMs: 45_000,
    outputs: [{ key: 'craft_goldweed', qty: 2 }],
    bonusAdditiveKey: 'craft_fertile_soil',
    bonusOutputs: [{ key: 'craft_goldweed', qty: 1 }],
    xp: 10,
  },
];

const DEFAULT_PROFESSIONS: ProfessionProgress[] = CRAFTING_PROFESSIONS.map((profession) => ({
  professionId: profession.id,
  rank: 1,
  xp: 0,
}));

const HUMANOID_SCAVENGE: EnemyGatheringDefinition = {
  professionId: 'scavenging',
  actionLabel: 'Scavenge',
  corpseLabel: 'Humanoid remains',
  xp: 6,
  loot: [
    { key: 'craft_scrap_iron', qty: 1, chance: 0.8, minQty: 1, maxQty: 2 },
    { key: 'craft_torn_cloth', qty: 1, chance: 0.7, minQty: 1, maxQty: 2 },
    { key: 'craft_goblin_trinket', qty: 1, chance: 0.25 },
    { key: 'seed_mandrake', qty: 1, chance: 0.18 },
  ],
};

const BEAST_BUTCHER: EnemyGatheringDefinition = {
  professionId: 'butchering',
  actionLabel: 'Butcher',
  corpseLabel: 'Beast carcass',
  xp: 6,
  loot: [
    { key: 'craft_ragged_leather', qty: 1, chance: 0.85, minQty: 1, maxQty: 2 },
    { key: 'craft_bone_chips', qty: 1, chance: 0.7, minQty: 1, maxQty: 2 },
    { key: 'seed_goldweed', qty: 1, chance: 0.16 },
  ],
};

export function createDefaultCraftingState(): CraftingState {
  return {
    professions: DEFAULT_PROFESSIONS.map((profession) => ({ ...profession })),
    cultivationSlots: [],
    resourceNodeCooldowns: {},
  };
}

export function normalizeCraftingState(value: unknown): CraftingState {
  const fallback = createDefaultCraftingState();
  if (!value || typeof value !== 'object') return fallback;
  const partial = value as Partial<CraftingState>;
  const byId = new Map(
    (Array.isArray(partial.professions) ? partial.professions : [])
      .filter((entry): entry is ProfessionProgress =>
        !!entry &&
        typeof entry.professionId === 'string' &&
        typeof entry.xp === 'number',
      )
      .map((entry) => [
        entry.professionId,
        {
          professionId: entry.professionId,
          xp: Math.max(0, Math.floor(entry.xp)),
          rank: rankForXp(entry.xp),
        },
      ]),
  );

  return {
    professions: DEFAULT_PROFESSIONS.map((profession) => byId.get(profession.professionId) ?? { ...profession }),
    cultivationSlots: Array.isArray(partial.cultivationSlots)
      ? partial.cultivationSlots
          .filter((slot) =>
            !!slot &&
            typeof slot.id === 'string' &&
            typeof slot.seedKey === 'string' &&
            typeof slot.plantedAt === 'number' &&
            typeof slot.readyAt === 'number',
          )
          .slice(0, CULTIVATION_SLOT_COUNT)
          .map((slot) => ({
            id: slot.id,
            seedKey: slot.seedKey,
            plantedAt: slot.plantedAt,
            readyAt: slot.readyAt,
            additives: Array.isArray(slot.additives) ? slot.additives.filter((key) => typeof key === 'string') : [],
          }))
      : [],
    resourceNodeCooldowns: normalizeResourceNodeCooldowns(partial.resourceNodeCooldowns),
  };
}

export function resourceNodeCooldownKey(zoneId: string, nodeId: string): string {
  return `${zoneId}:${nodeId}`;
}

export function isResourceNodeAvailable(
  state: CraftingState,
  zoneId: string,
  nodeId: string,
  now = Date.now(),
): boolean {
  const cooldowns = normalizeCraftingState(state).resourceNodeCooldowns;
  return (cooldowns[resourceNodeCooldownKey(zoneId, nodeId)] ?? 0) <= now;
}

export function withResourceNodeCooldown(
  state: CraftingState,
  zoneId: string,
  nodeId: string,
  availableAt: number,
  now = Date.now(),
): CraftingState {
  const normalized = normalizeCraftingState(state);
  const nextCooldowns = Object.fromEntries(
    Object.entries(normalized.resourceNodeCooldowns)
      .filter(([, expiresAt]) => expiresAt > now),
  );
  nextCooldowns[resourceNodeCooldownKey(zoneId, nodeId)] = Math.max(now, availableAt);
  return {
    ...normalized,
    resourceNodeCooldowns: nextCooldowns,
  };
}

export function rollGatheringLootTable(loot: GatheringLootEntry[]): CraftingRewardItem[] {
  const results: CraftingRewardItem[] = [];
  for (const entry of loot) {
    if (Math.random() > entry.chance) continue;
    const min = entry.minQty ?? entry.qty;
    const max = entry.maxQty ?? entry.qty;
    results.push({
      key: entry.key,
      qty: randomInt(min, max),
      name: entry.name,
      kind: entry.kind,
      equipSlot: entry.equipSlot,
      strengthRoll: entry.strengthRoll,
    });
  }
  if (results.length === 0 && loot.length > 0) {
    const fallback = loot[0];
    results.push({ key: fallback.key, qty: fallback.qty, name: fallback.name });
  }
  return results;
}

export function rankForXp(xp: number): number {
  return Math.max(1, Math.floor(Math.max(0, xp) / CRAFTING_XP_PER_RANK) + 1);
}

export function professionLabel(id: CraftingProfessionId): string {
  return CRAFTING_PROFESSIONS.find((profession) => profession.id === id)?.label ?? id;
}

export function getProfessionProgress(
  state: CraftingState,
  professionId: CraftingProfessionId,
): ProfessionProgress {
  return state.professions.find((progress) => progress.professionId === professionId) ?? {
    professionId,
    rank: 1,
    xp: 0,
  };
}

export function addProfessionXp(
  state: CraftingState,
  professionId: CraftingProfessionId,
  xp: number,
): CraftingState {
  const normalized = normalizeCraftingState(state);
  return {
    ...normalized,
    professions: normalized.professions.map((progress) => {
      if (progress.professionId !== professionId) return progress;
      const nextXp = Math.max(0, progress.xp + xp);
      return { ...progress, xp: nextXp, rank: rankForXp(nextXp) };
    }),
  };
}

export function getSeedDefinition(seedKey: string): CultivationSeedDefinition | undefined {
  return CULTIVATION_SEEDS.find((seed) => seed.seedKey === seedKey);
}

export function buildEnemyGatheringState(enemyName: string): EnemyGatheringState | undefined {
  const definition = getEnemyGatheringDefinition(enemyName);
  if (!definition) return undefined;
  return {
    professionId: definition.professionId,
    actionLabel: definition.actionLabel,
    corpseLabel: definition.corpseLabel,
    harvested: false,
  };
}

export function getEnemyGatheringDefinition(enemyName: string): EnemyGatheringDefinition | null {
  const normalized = enemyName.toLowerCase();
  if (
    /goblin|shaman|warboss|raider|cultist|marauder|bandit|thug|soldier|guard/.test(normalized)
  ) {
    return HUMANOID_SCAVENGE;
  }
  if (/wolf|boar|bear|hound|spider|bat|rat|beast|carcass|stag/.test(normalized)) {
    return BEAST_BUTCHER;
  }
  return null;
}

export function rollGatheringLoot(definition: EnemyGatheringDefinition): CraftingRewardItem[] {
  return rollGatheringLootTable(definition.loot);
}

export function getSalvageOutputs(item: InventoryItem): CraftingRewardItem[] {
  if (item.kind !== 'weapon' && item.kind !== 'armor') return [];
  const strength = item.affix?.strengthBonus ?? 0;
  const bonusEssence = strength >= 3 ? 1 : 0;

  if (item.kind === 'weapon') {
    return [
      { key: 'craft_scrap_iron', qty: 2 + Math.min(2, strength) },
      { key: 'craft_talisman_fragment', qty: 1 },
      ...(bonusEssence ? [{ key: 'craft_essence_minor', qty: bonusEssence }] : []),
    ];
  }

  if (item.equipSlot === 'chest' || item.equipSlot === 'shoulders' || item.equipSlot === 'legs') {
    return [
      { key: 'craft_scrap_iron', qty: 2 },
      { key: 'craft_torn_cloth', qty: 1 + Math.min(2, strength) },
      ...(bonusEssence ? [{ key: 'craft_essence_minor', qty: bonusEssence }] : []),
    ];
  }

  return [
    { key: 'craft_ragged_leather', qty: 2 },
    { key: 'craft_torn_cloth', qty: 1 + Math.min(1, strength) },
    ...(bonusEssence ? [{ key: 'craft_essence_minor', qty: bonusEssence }] : []),
  ];
}

export function inventoryQty(items: InventoryItem[], key: string): number {
  return items
    .filter((item) => item.key === key)
    .reduce((sum, item) => sum + item.qty, 0);
}

export function hasIngredients(items: InventoryItem[], ingredients: CraftingItemStack[]): boolean {
  return ingredients.every((ingredient) => inventoryQty(items, ingredient.key) >= ingredient.qty);
}

function randomInt(min: number, max: number): number {
  return Math.floor(min + Math.random() * (max - min + 1));
}

function normalizeResourceNodeCooldowns(value: unknown): Record<string, number> {
  if (!value || typeof value !== 'object') return {};
  const now = Date.now();
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([key, expiresAt]) =>
        typeof key === 'string' &&
        typeof expiresAt === 'number' &&
        Number.isFinite(expiresAt) &&
        expiresAt > now,
      )
      .map(([key, expiresAt]) => [key, Math.floor(expiresAt as number)]),
  );
}
