import {
  CLASSES_BY_RACE,
  DESTRUCTION_RACES,
  ORDER_RACES,
  RACE_DISPLAY,
  type PlayableRace,
} from '../data/careers';
import {
  CRAFTING_PROFESSIONS,
  CRAFTING_RECIPES,
  CULTIVATION_SEEDS,
  type CraftingItemStack,
  type CraftingRecipe,
  type CraftingRewardItem,
} from '../data/crafting';
import { getItemDefinition, ITEM_CATALOG, type ItemDefinition } from '../data/items';
import { QUESTS } from '../data/quests';
import type { QuestDefinition, QuestRewardItem } from '../services/types';
import { CAREER_ABILITY_KITS } from '../game/abilities/abilityData';
import type {
  AbilityAmount,
  AbilityDefinition,
  AbilityEffect,
  CareerAbilityKit,
  CareerResourceDefinition,
} from '../game/abilities/types';
import {
  CLASS_FAMILY_LABELS,
  OVERVIEW_PAGES,
  RACE_GUIDE_COPY,
  ROADMAP_PAGES,
  WIKI_SECTIONS,
} from './wikiMetadata';
import type {
  WikiDetailRow,
  WikiIndex,
  WikiPage,
  WikiTable,
  WikiTableRow,
} from './wikiTypes';

const REALM_BY_RACE: Record<PlayableRace, 'Aegis Accord' | 'Riftbound Host'> = {
  empire: 'Aegis Accord',
  dwarf: 'Aegis Accord',
  high_elf: 'Aegis Accord',
  chaos: 'Riftbound Host',
  greenskin: 'Riftbound Host',
  dark_elf: 'Riftbound Host',
};

const CAPITAL_BY_REALM: Record<'Aegis Accord' | 'Riftbound Host', string> = {
  'Aegis Accord': 'Bastion of Aegis',
  'Riftbound Host': 'Riftspire Citadel',
};

const STATION_LABELS: Record<string, string> = {
  apothecary: 'Apothecary Station',
  talisman_making: 'Talisman Making Station',
  cultivation: 'Cultivation Plot',
  salvage: 'Salvage Station',
  general: 'General Crafting Hub',
};

const RACES: PlayableRace[] = [...ORDER_RACES, ...DESTRUCTION_RACES];

let cachedIndex: WikiIndex | null = null;

export function buildWikiIndex(): WikiIndex {
  if (cachedIndex) return cachedIndex;

  const pages: WikiPage[] = [
    ...OVERVIEW_PAGES,
    ...buildRaceAndClassPages(),
    ...buildAbilityPages(),
    ...buildCraftingPages(),
    ...buildQuestPages(),
    ...buildWorldPages(),
    ...ROADMAP_PAGES,
  ];

  cachedIndex = {
    sections: [...WIKI_SECTIONS].sort((a, b) => a.order - b.order),
    pages,
    pagesById: Object.fromEntries(pages.map((page) => [page.id, page])),
  };

  return cachedIndex;
}

function buildRaceAndClassPages(): WikiPage[] {
  const classRows = RACES.flatMap((race) =>
    CLASSES_BY_RACE[race].map((className) => {
      const kit = CAREER_ABILITY_KITS[className];
      return {
        id: `${race}-${slug(className)}`,
        cells: [
          REALM_BY_RACE[race],
          RACE_DISPLAY[race],
          className,
          familyLabel(kit.classFamily),
          kit.resource.label,
        ],
      };
    }),
  );

  const pages: WikiPage[] = [
    {
      id: 'races-classes-roster',
      sectionId: 'races_classes',
      title: 'Playable Roster',
      subtitle: 'Realms, races, classes, and class resources',
      status: 'implemented',
      tags: ['roster', 'races', 'classes', 'aegis', 'riftbound'],
      body: [
        'The current roster uses the player-facing renamed class list from ability-system.md. Legacy class names are compatibility aliases only.',
      ],
      tables: [
        {
          title: 'Classes by race',
          columns: ['Realm', 'Race', 'Class', 'Role Family', 'Resource'],
          rows: classRows,
        },
      ],
    },
  ];

  for (const race of RACES) {
    const realm = REALM_BY_RACE[race];
    pages.push({
      id: `race-${race}`,
      sectionId: 'races_classes',
      title: RACE_DISPLAY[race],
      subtitle: `${realm} race`,
      status: 'implemented',
      tags: ['race', race, realm, ...CLASSES_BY_RACE[race]],
      body: [RACE_GUIDE_COPY[race]],
      details: [
        { label: 'Realm', value: realm },
        { label: 'Capital', value: CAPITAL_BY_REALM[realm] },
        { label: 'Classes', value: CLASSES_BY_RACE[race].join(', ') },
      ],
      tables: [
        {
          title: 'Class kit summary',
          columns: ['Class', 'Role Family', 'Resource', 'Ability Count'],
          rows: CLASSES_BY_RACE[race].map((className) => {
            const kit = CAREER_ABILITY_KITS[className];
            return {
              id: slug(className),
              cells: [
                className,
                familyLabel(kit.classFamily),
                resourceSummary(kit.resource),
                String(kit.abilities.length),
              ],
            };
          }),
        },
      ],
    });
  }

  for (const kit of orderedKits()) {
    const race = raceForClass(kit.career);
    const realm = race ? REALM_BY_RACE[race] : 'Aegis Accord';
    pages.push({
      id: `class-${slug(kit.career)}`,
      sectionId: 'races_classes',
      title: kit.career,
      subtitle: `${race ? RACE_DISPLAY[race] : 'Playable'} class`,
      status: 'implemented',
      tags: [
        'class',
        kit.career,
        kit.classFamily,
        kit.resource.label,
        race ? RACE_DISPLAY[race] : '',
        realm,
      ],
      body: [
        `${kit.career} is a ${familyLabel(kit.classFamily).toLowerCase()} class using ${resourceSummary(kit.resource)}.`,
      ],
      details: [
        { label: 'Realm', value: realm },
        { label: 'Race', value: race ? RACE_DISPLAY[race] : 'Unknown' },
        { label: 'Role Family', value: familyLabel(kit.classFamily) },
        { label: 'Class Resource', value: resourceSummary(kit.resource) },
      ],
      tables: [
        {
          title: 'Ability kit',
          columns: ['Slot', 'Ability', 'School', 'Targeting', 'Resource'],
          rows: kit.abilities.map((ability) => ({
            id: ability.id,
            cells: [
              ability.key,
              ability.name,
              ability.visual.school,
              formatTargeting(ability),
              formatResourceCost(ability, kit.resource),
            ],
          })),
        },
      ],
    });
  }

  return pages;
}

function buildAbilityPages(): WikiPage[] {
  const pages: WikiPage[] = [
    {
      id: 'abilities-index',
      sectionId: 'abilities',
      title: 'Ability Index',
      subtitle: 'All current class abilities',
      status: 'implemented',
      tags: ['abilities', 'combat', 'hotbar'],
      body: [
        'Every playable class currently has a ten-ability hotbar mapped to keys 1 through 0. Ability pages are generated from the runtime ability catalog.',
      ],
      tables: [
        {
          title: 'Classes',
          columns: ['Class', 'Role Family', 'Resource', 'Abilities'],
          rows: orderedKits().map((kit) => ({
            id: slug(kit.career),
            cells: [
              kit.career,
              familyLabel(kit.classFamily),
              resourceSummary(kit.resource),
              String(kit.abilities.length),
            ],
          })),
        },
      ],
    },
  ];

  for (const kit of orderedKits()) {
    for (const ability of kit.abilities) {
      pages.push({
        id: `ability-${ability.id}`,
        sectionId: 'abilities',
        title: ability.name,
        subtitle: `${ability.key}. ${ability.career}`,
        status: 'implemented',
        tags: [
          'ability',
          ability.name,
          ability.career,
          ability.visual.school,
          ability.targeting.shape,
          ability.targeting.target,
          ...ability.tags,
        ],
        body: [ability.summary],
        details: abilityDetails(ability, kit.resource),
        tables: [
          {
            title: 'Effects',
            columns: ['Type', 'School', 'Details'],
            rows: ability.effects.length > 0
              ? ability.effects.map((effect, index) => abilityEffectRow(effect, index))
              : [{ id: 'no-effect', cells: ['None', '-', 'No immediate effect payload.'] }],
          },
          {
            title: 'Runtime metadata',
            columns: ['Field', 'Value'],
            rows: [
              { id: 'animation', cells: ['Animation', `${ability.animation.actionId} (${ability.animation.durationSec}s)`] },
              { id: 'windows', cells: ['Notify Windows', ability.animation.notifyWindows.map((w) => `${w.name} ${w.start}-${w.end}`).join(', ') || 'None'] },
              { id: 'sockets', cells: ['VFX Sockets', ability.vfxSockets.join(', ') || 'None'] },
              { id: 'tags', cells: ['Tags', ability.tags.join(', ') || 'None'] },
            ],
          },
        ],
        source: {
          kind: 'ability',
          ability,
          resource: kit.resource,
        },
      });
    }
  }

  return pages;
}

function buildCraftingPages(): WikiPage[] {
  const usedItemKeys = new Set<string>();
  for (const recipe of CRAFTING_RECIPES) {
    recipe.inputs.forEach((item) => usedItemKeys.add(item.key));
    recipe.outputs.forEach((item) => usedItemKeys.add(item.key));
  }
  for (const seed of CULTIVATION_SEEDS) {
    usedItemKeys.add(seed.seedKey);
    seed.outputs.forEach((item) => usedItemKeys.add(item.key));
    seed.bonusOutputs?.forEach((item) => usedItemKeys.add(item.key));
    if (seed.bonusAdditiveKey) usedItemKeys.add(seed.bonusAdditiveKey);
  }
  for (const quest of QUESTS) {
    quest.reward.items?.forEach((item) => usedItemKeys.add(item.key));
  }

  const pages: WikiPage[] = [
    {
      id: 'crafting-overview',
      sectionId: 'crafting',
      title: 'Crafting Overview',
      subtitle: 'Implemented professions and stations',
      status: 'implemented',
      tags: ['crafting', 'professions', 'recipes', 'stations'],
      body: [
        'Gathering and crafting are data-driven and persisted through services.crafting. Local storage is active by default.',
      ],
      tables: [
        {
          title: 'Professions',
          columns: ['Profession', 'Description'],
          rows: CRAFTING_PROFESSIONS.map((profession) => ({
            id: profession.id,
            cells: [profession.label, profession.description],
          })),
        },
        {
          title: 'Stations',
          columns: ['Station Kind', 'Use'],
          rows: Object.entries(STATION_LABELS).map(([kind, label]) => ({
            id: kind,
            cells: [kind, label],
          })),
        },
      ],
    },
    {
      id: 'crafting-items',
      sectionId: 'crafting',
      title: 'Crafting Materials and Rewards',
      subtitle: 'Items referenced by current recipes, seeds, and quests',
      status: 'implemented',
      tags: ['crafting', 'items', 'materials', 'rewards'],
      body: [
        'This page lists item definitions used by current crafting recipes, cultivation seeds, and quest rewards.',
      ],
      tables: [
        {
          title: 'Referenced items',
          columns: ['Item', 'Key', 'Kind', 'Equip Slot'],
          rows: [...usedItemKeys]
            .sort((a, b) => itemName(a).localeCompare(itemName(b)))
            .map((key) => {
              const item = getItemDefinition(key);
              return {
                id: key,
                cells: [
                  item?.name ?? key,
                  key,
                  item?.kind ?? 'unknown',
                  item?.equipSlot ?? '-',
                ],
              };
            }),
        },
      ],
    },
  ];

  for (const profession of CRAFTING_PROFESSIONS) {
    const recipes = CRAFTING_RECIPES.filter((recipe) => recipe.professionId === profession.id);
    pages.push({
      id: `crafting-profession-${profession.id}`,
      sectionId: 'crafting',
      title: profession.label,
      subtitle: 'Crafting profession',
      status: 'implemented',
      tags: ['crafting', 'profession', profession.id, profession.label],
      body: [profession.description],
      details: [
        { label: 'Profession ID', value: profession.id },
        { label: 'Recipe Count', value: String(recipes.length) },
      ],
      tables: recipes.length > 0
        ? [
            {
              title: 'Recipes',
              columns: ['Recipe', 'Rank', 'Station', 'Output'],
              rows: recipes.map((recipe) => ({
                id: recipe.id,
                cells: [
                  recipe.name,
                  String(recipe.minRank),
                  recipe.station,
                  formatRewardList(recipe.outputs),
                ],
              })),
            },
          ]
        : undefined,
    });
  }

  for (const recipe of CRAFTING_RECIPES) {
    pages.push({
      id: `crafting-recipe-${recipe.id}`,
      sectionId: 'crafting',
      title: recipe.name,
      subtitle: `${professionLabel(recipe.professionId)} recipe`,
      status: 'implemented',
      tags: ['crafting', 'recipe', recipe.professionId, recipe.station, recipe.name],
      body: [recipe.summary],
      details: recipeDetails(recipe),
      tables: [
        {
          title: 'Ingredients',
          columns: ['Item', 'Quantity'],
          rows: itemStackRows(recipe.inputs),
        },
        {
          title: 'Outputs',
          columns: ['Item', 'Quantity', 'Details'],
          rows: rewardRows(recipe.outputs),
        },
      ],
      source: {
        kind: 'craftingRecipe',
        recipe,
      },
    });
  }

  for (const seed of CULTIVATION_SEEDS) {
    pages.push({
      id: `cultivation-seed-${seed.seedKey}`,
      sectionId: 'crafting',
      title: seed.name,
      subtitle: 'Cultivation seed',
      status: 'implemented',
      tags: ['crafting', 'cultivation', 'seed', seed.seedKey, seed.name],
      body: [
        `${seed.name} grows through cultivation and grants profession XP when harvested.`,
      ],
      details: [
        { label: 'Seed Key', value: seed.seedKey },
        { label: 'Growth Time', value: formatDuration(seed.durationMs) },
        { label: 'XP', value: String(seed.xp) },
        { label: 'Bonus Additive', value: seed.bonusAdditiveKey ? itemName(seed.bonusAdditiveKey) : 'None' },
      ],
      tables: [
        {
          title: 'Harvest Outputs',
          columns: ['Item', 'Quantity', 'Details'],
          rows: rewardRows([...seed.outputs, ...(seed.bonusOutputs ?? [])]),
        },
      ],
      source: {
        kind: 'cultivationSeed',
        seed,
      },
    });
  }

  return pages;
}

function buildQuestPages(): WikiPage[] {
  const pages: WikiPage[] = [
    {
      id: 'quests-overview',
      sectionId: 'quests',
      title: 'Quest Overview',
      subtitle: 'Current quest chain',
      status: 'implemented',
      tags: ['quests', 'quest chain', 'objectives', 'rewards'],
      body: [
        'The current quest catalog is a linear chain. Quest pages are generated from src/data/quests.ts.',
      ],
      tables: [
        {
          title: 'Quest chain',
          columns: ['Step', 'Quest', 'Level', 'Prerequisite', 'Reward'],
          rows: QUESTS.map((quest, index) => ({
            id: quest.id,
            cells: [
              String(index + 1),
              quest.title,
              String(quest.minLevel),
              quest.prereqQuestId ? questTitle(quest.prereqQuestId) : 'None',
              questRewardSummary(quest),
            ],
          })),
        },
      ],
    },
  ];

  for (const quest of QUESTS) {
    pages.push({
      id: `quest-${quest.id}`,
      sectionId: 'quests',
      title: quest.title,
      subtitle: `Level ${quest.minLevel} quest`,
      status: 'implemented',
      tags: [
        'quest',
        quest.id,
        quest.title,
        quest.giverNpcId,
        quest.turninNpcId ?? quest.giverNpcId,
        ...quest.objectives.map((objective) => objective.killTarget ?? objective.talkTarget ?? objective.description),
      ],
      body: [quest.description],
      details: [
        { label: 'Quest ID', value: quest.id },
        { label: 'Minimum Level', value: String(quest.minLevel) },
        { label: 'Giver NPC ID', value: quest.giverNpcId },
        { label: 'Turn-in NPC ID', value: quest.turninNpcId ?? quest.giverNpcId },
        { label: 'Prerequisite', value: quest.prereqQuestId ? questTitle(quest.prereqQuestId) : 'None' },
        { label: 'Reward', value: questRewardSummary(quest) },
      ],
      tables: [
        {
          title: 'Objectives',
          columns: ['Objective', 'Target', 'Required'],
          rows: quest.objectives.map((objective) => ({
            id: objective.id,
            cells: [
              objective.description,
              objective.killTarget ?? objective.talkTarget ?? '-',
              String(objective.required),
            ],
          })),
        },
      ],
    });
  }

  return pages;
}

function buildWorldPages(): WikiPage[] {
  return [
    {
      id: 'world-current-zones',
      sectionId: 'world_roadmap',
      title: 'Current World Data',
      subtitle: 'Implemented zone loading',
      status: 'implemented',
      tags: ['world', 'zones', 'maps', 'aegis', 'riftbound', 'campaign'],
      body: [
        'Zone definitions load from public/assets/maps by zone ID. The generated Aegis/Riftbound campaign maps are static committed assets; missing assets fall back to procedural primitives and must not hard-fail the browser.',
      ],
      details: [
        { label: 'Map Source', value: 'public/assets/maps/<zoneId>.json' },
        { label: 'Implemented examples', value: 'Aegis/Riftbound campaign maps, plus legacy dev maps' },
        { label: 'Asset behavior', value: 'GLB assets when present, primitive fallbacks otherwise' },
      ],
    },
  ];
}

function orderedKits(): CareerAbilityKit[] {
  const classes = RACES.flatMap((race) => CLASSES_BY_RACE[race]);
  return classes.map((className) => CAREER_ABILITY_KITS[className]).filter(Boolean);
}

function raceForClass(className: string): PlayableRace | null {
  for (const race of RACES) {
    if (CLASSES_BY_RACE[race].includes(className)) return race;
  }
  return null;
}

function familyLabel(family: string): string {
  return CLASS_FAMILY_LABELS[family] ?? titleCase(family.replace(/_/g, ' '));
}

function resourceSummary(resource: CareerResourceDefinition): string {
  const risk = resource.highRisk ? ', high risk' : '';
  return `${resource.label} (${resource.initial}/${resource.max}${risk})`;
}

function abilityDetails(
  ability: AbilityDefinition,
  resource: CareerResourceDefinition,
): WikiDetailRow[] {
  return [
    { label: 'Class', value: ability.career },
    { label: 'Slot', value: ability.key },
    { label: 'School', value: ability.visual.school },
    { label: 'Cooldown', value: `${ability.cooldownSec}s` },
    { label: 'GCD', value: `${ability.gcdSec}s` },
    { label: 'Targeting', value: formatTargeting(ability) },
    { label: 'Resource', value: formatResourceCost(ability, resource) },
    { label: 'Cancel Rules', value: ability.cancelRules.blockedBy.join(', ') || 'None' },
  ];
}

function recipeDetails(recipe: CraftingRecipe): WikiDetailRow[] {
  return [
    { label: 'Recipe ID', value: recipe.id },
    { label: 'Profession', value: professionLabel(recipe.professionId) },
    { label: 'Station', value: recipe.station },
    { label: 'Minimum Rank', value: String(recipe.minRank) },
    { label: 'XP', value: String(recipe.xp) },
  ];
}

function formatTargeting(ability: AbilityDefinition): string {
  const targeting = ability.targeting;
  const radius = targeting.radius ? `, radius ${targeting.radius}` : '';
  const speed = targeting.projectileSpeed ? `, projectile ${targeting.projectileSpeed}/s` : '';
  return `${targeting.shape} -> ${targeting.target}, range ${targeting.range}${radius}${speed}`;
}

function formatResourceCost(
  ability: AbilityDefinition,
  resource: CareerResourceDefinition,
): string {
  const parts: string[] = [];
  if (ability.resource.manaCost) parts.push(`${ability.resource.manaCost} mana`);
  if (ability.resource.careerBuild) parts.push(`builds ${ability.resource.careerBuild} ${resource.label}`);
  if (ability.resource.careerCost) parts.push(`costs ${ability.resource.careerCost} ${resource.label}`);
  if (ability.resource.minCareer) parts.push(`requires ${ability.resource.minCareer} ${resource.label}`);
  if (ability.resource.spendAllCareer) parts.push(`spends all ${resource.label}`);
  return parts.length > 0 ? parts.join(', ') : 'No explicit cost';
}

function abilityEffectRow(effect: AbilityEffect, index: number): WikiTableRow {
  if (effect.kind === 'damage' || effect.kind === 'heal') {
    return {
      id: `${effect.kind}-${index}`,
      cells: [
        titleCase(effect.kind),
        effect.school ?? '-',
        effect.amount ? formatAmount(effect.amount) : 'No amount payload',
      ],
    };
  }

  const status = effect.status;
  return {
    id: `status-${index}`,
    cells: [
      'Status',
      effect.school ?? '-',
      status
        ? `${status.label} (${status.kind}), ${status.durationSec}s${formatMagnitude(status.magnitude)}`
        : 'No status payload',
    ],
  };
}

function formatAmount(amount: AbilityAmount): string {
  const parts = [`${amount.min}-${amount.max}`];
  if (amount.statScale) parts.push(`stat x${amount.statScale}`);
  if (amount.resourceScale) parts.push(`resource x${amount.resourceScale}`);
  if (amount.levelScale) parts.push(`level x${amount.levelScale}`);
  return parts.join(', ');
}

function formatMagnitude(value: number | undefined): string {
  if (value === undefined) return '';
  if (value > 0 && value <= 1) return `, ${Math.round(value * 100)}% magnitude`;
  return `, magnitude ${value}`;
}

function itemStackRows(stacks: CraftingItemStack[]): WikiTableRow[] {
  return stacks.map((stack) => ({
    id: stack.key,
    cells: [itemName(stack.key), String(stack.qty)],
  }));
}

function rewardRows(rewards: CraftingRewardItem[]): WikiTableRow[] {
  return rewards.map((reward) => ({
    id: `${reward.key}-${reward.qty}-${reward.strengthRoll?.min ?? 'none'}`,
    cells: [
      itemName(reward.key),
      String(reward.qty),
      reward.strengthRoll
        ? `Strength +${reward.strengthRoll.min}-${reward.strengthRoll.max}`
        : reward.equipSlot
          ? `Equip slot: ${reward.equipSlot}`
          : '-',
    ],
  }));
}

function formatRewardList(rewards: CraftingRewardItem[]): string {
  return rewards.map((reward) => `${itemName(reward.key)} x${reward.qty}`).join(', ');
}

function itemName(key: string): string {
  return getItemDefinition(key)?.name ?? key;
}

function professionLabel(id: string): string {
  return CRAFTING_PROFESSIONS.find((profession) => profession.id === id)?.label ?? id;
}

function questTitle(id: string): string {
  return QUESTS.find((quest) => quest.id === id)?.title ?? id;
}

function questRewardSummary(quest: QuestDefinition): string {
  const items = quest.reward.items?.map(questRewardItemName).join(', ');
  return `${quest.reward.xp} XP, ${quest.reward.gold} gold${items ? `, ${items}` : ''}`;
}

function questRewardItemName(item: QuestRewardItem): string {
  const itemDef = ITEM_CATALOG[item.key] as ItemDefinition | undefined;
  return item.name ?? itemDef?.name ?? item.key;
}

function formatDuration(ms: number): string {
  const seconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function titleCase(value: string): string {
  return value.replace(/\b\w/g, (char) => char.toUpperCase());
}
