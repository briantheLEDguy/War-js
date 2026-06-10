import { describe, test } from 'vitest';
import {
  CLASSES_BY_RACE,
  DESTRUCTION_RACES,
  ORDER_RACES,
  RACE_DISPLAY,
  type PlayableRace,
} from '../src/data/careers';
import {
  CRAFTING_PROFESSIONS,
  CRAFTING_RECIPES,
  CULTIVATION_SEEDS,
} from '../src/data/crafting';
import { getItemDefinition } from '../src/data/items';
import { QUESTS } from '../src/data/quests';
import {
  CAREER_ABILITY_KITS,
  HOTBAR_KEYS,
  HOTBAR_SLOT_COUNT,
} from '../src/game/abilities/abilityData';
import { OVERVIEW_PAGES, ROADMAP_PAGES, WIKI_SECTIONS } from '../src/wiki/wikiMetadata';
import { buildWikiIndex } from '../src/wiki/wikiContent';
import type { WikiPage } from '../src/wiki/wikiTypes';

const index = buildWikiIndex();
const allRaces = [...ORDER_RACES, ...DESTRUCTION_RACES];
const allClasses = allRaces.flatMap((race) => CLASSES_BY_RACE[race]);

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

function assertArrayEqual<T>(actual: T[], expected: T[], message: string): void {
  assert(
    actual.length === expected.length && actual.every((value, index) => value === expected[index]),
    `${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
  );
}

function page(id: string): WikiPage {
  const found = index.pagesById[id];
  assert(found, `Missing wiki page: ${id}`);
  return found;
}

function rowCount(pageId: string, tableTitle: string): number {
  const table = page(pageId).tables?.find((candidate) => candidate.title === tableTitle);
  assert(table, `Missing table "${tableTitle}" on ${pageId}`);
  return table.rows.length;
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function referencedItemKeys(): string[] {
  const keys = new Set<string>();
  for (const recipe of CRAFTING_RECIPES) {
    recipe.inputs.forEach((item) => keys.add(item.key));
    recipe.outputs.forEach((item) => keys.add(item.key));
  }
  for (const seed of CULTIVATION_SEEDS) {
    keys.add(seed.seedKey);
    seed.outputs.forEach((item) => keys.add(item.key));
    seed.bonusOutputs?.forEach((item) => keys.add(item.key));
    if (seed.bonusAdditiveKey) keys.add(seed.bonusAdditiveKey);
  }
  for (const quest of QUESTS) {
    quest.reward.items?.forEach((item) => keys.add(item.key));
  }
  return [...keys].sort();
}

function testIndexShape() {
  const expectedSections = [...WIKI_SECTIONS]
    .sort((a, b) => a.order - b.order)
    .map((section) => section.id);
  assertArrayEqual(index.sections.map((section) => section.id), expectedSections, 'Wiki sections must match metadata order');

  const pageIds = index.pages.map((wikiPage) => wikiPage.id);
  assertEqual(new Set(pageIds).size, pageIds.length, 'Wiki page IDs must be unique');
  for (const wikiPage of index.pages) {
    assert(index.pagesById[wikiPage.id] === wikiPage, `pagesById must point at page object for ${wikiPage.id}`);
    assert(index.sections.some((section) => section.id === wikiPage.sectionId), `Page has unknown section: ${wikiPage.id}`);
    assert(wikiPage.tags.length > 0, `Page must have tags: ${wikiPage.id}`);
    assert(wikiPage.body.length > 0, `Page must have body copy: ${wikiPage.id}`);
  }

  for (const section of index.sections) {
    assert(index.pages.some((wikiPage) => wikiPage.sectionId === section.id), `Section has no pages: ${section.id}`);
  }

  for (const overviewPage of OVERVIEW_PAGES) {
    assertEqual(page(overviewPage.id).status, 'implemented', `Overview page should be implemented: ${overviewPage.id}`);
  }
  for (const roadmapPage of ROADMAP_PAGES) {
    assertEqual(page(roadmapPage.id).status, 'planned', `Roadmap page should be planned: ${roadmapPage.id}`);
  }
}

function testRaceAndClassCoverage() {
  assertEqual(allRaces.length, 6, 'Playable race count should remain explicit');
  assertEqual(allClasses.length, 24, 'Playable class count should remain explicit');
  assertEqual(rowCount('races-classes-roster', 'Classes by race'), allClasses.length, 'Roster table must include every class');

  for (const race of allRaces) {
    const racePage = page(`race-${race}`);
    assertEqual(racePage.status, 'implemented', `Race page status for ${race}`);
    assert(racePage.title === RACE_DISPLAY[race], `Race page title must match RACE_DISPLAY for ${race}`);
    for (const className of CLASSES_BY_RACE[race]) {
      assert(racePage.tags.includes(className), `Race page must tag class ${className}`);
    }
  }

  for (const className of allClasses) {
    const kit = CAREER_ABILITY_KITS[className];
    assert(kit, `Missing ability kit for playable class: ${className}`);
    assertEqual(kit.career, className, `Kit career should match class name for ${className}`);
    assertEqual(kit.abilities.length, HOTBAR_SLOT_COUNT, `${className} should have a full hotbar`);

    const classPage = page(`class-${slug(className)}`);
    assertEqual(classPage.status, 'implemented', `Class page status for ${className}`);
    assertEqual(classPage.title, className, `Class page title for ${className}`);
    assertEqual(rowCount(`class-${slug(className)}`, 'Ability kit'), HOTBAR_SLOT_COUNT, `Class page ability rows for ${className}`);

    const seenSlots = new Set<number>();
    const seenKeys = new Set<string>();
    for (const ability of kit.abilities) {
      seenSlots.add(ability.slot);
      seenKeys.add(ability.key);
    }
    assertEqual(seenSlots.size, HOTBAR_SLOT_COUNT, `${className} ability slots must be unique`);
    assertArrayEqual([...seenKeys], [...HOTBAR_KEYS], `${className} hotbar keys must match HOTBAR_KEYS`);
  }
}

function testAbilityPageCoverage() {
  const abilityIds = new Set<string>();
  let abilityCount = 0;

  for (const className of allClasses) {
    const kit = CAREER_ABILITY_KITS[className];
    for (const ability of kit.abilities) {
      abilityCount += 1;
      assert(!abilityIds.has(ability.id), `Ability ID must be unique: ${ability.id}`);
      abilityIds.add(ability.id);

      assertEqual(ability.career, className, `Ability career must match owning class for ${ability.id}`);
      assertEqual(ability.slot >= 0 && ability.slot < HOTBAR_SLOT_COUNT, true, `Ability slot out of range: ${ability.id}`);
      assertEqual(ability.key, HOTBAR_KEYS[ability.slot], `Ability key must match slot for ${ability.id}`);
      assert(ability.cooldownSec >= 0, `Ability cooldown must be non-negative: ${ability.id}`);
      assert(ability.gcdSec >= 0, `Ability GCD must be non-negative: ${ability.id}`);
      assert(ability.targeting.range >= 0, `Ability range must be non-negative: ${ability.id}`);

      const abilityPage = page(`ability-${ability.id}`);
      assertEqual(abilityPage.status, 'implemented', `Ability page status for ${ability.id}`);
      assertEqual(abilityPage.title, ability.name, `Ability page title for ${ability.id}`);
      assertEqual(abilityPage.source?.kind, 'ability', `Ability page source kind for ${ability.id}`);
      assertEqual(abilityPage.source?.ability.id, ability.id, `Ability page source ID for ${ability.id}`);
      assert(abilityPage.tags.includes(ability.career), `Ability page must tag career for ${ability.id}`);
      assert(abilityPage.tags.includes(ability.visual.school), `Ability page must tag school for ${ability.id}`);
      assert(abilityPage.tags.includes(ability.targeting.shape), `Ability page must tag shape for ${ability.id}`);
      assertEqual(
        rowCount(`ability-${ability.id}`, 'Effects'),
        ability.effects.length > 0 ? ability.effects.length : 1,
        `Ability effects table row count for ${ability.id}`,
      );
    }
  }

  assertEqual(rowCount('abilities-index', 'Classes'), allClasses.length, 'Ability index must include every class');
  const abilityPages = index.pages.filter((wikiPage) => wikiPage.sectionId === 'abilities' && wikiPage.source?.kind === 'ability');
  assertEqual(abilityPages.length, abilityCount, 'Ability page count must match ability catalog count');
}

function testCraftingCoverage() {
  assertEqual(rowCount('crafting-overview', 'Professions'), CRAFTING_PROFESSIONS.length, 'Crafting overview profession rows');
  assertEqual(rowCount('crafting-items', 'Referenced items'), referencedItemKeys().length, 'Crafting item reference rows');

  for (const key of referencedItemKeys()) {
    assert(getItemDefinition(key), `Referenced item key must exist in item catalog: ${key}`);
  }

  for (const profession of CRAFTING_PROFESSIONS) {
    const professionPage = page(`crafting-profession-${profession.id}`);
    assertEqual(professionPage.status, 'implemented', `Profession page status for ${profession.id}`);
    const recipes = CRAFTING_RECIPES.filter((recipe) => recipe.professionId === profession.id);
    if (recipes.length > 0) {
      assertEqual(rowCount(`crafting-profession-${profession.id}`, 'Recipes'), recipes.length, `Recipe rows for ${profession.id}`);
    }
  }

  for (const recipe of CRAFTING_RECIPES) {
    assert(recipe.minRank >= 1, `Recipe minRank must be positive: ${recipe.id}`);
    assert(recipe.xp > 0, `Recipe XP must be positive: ${recipe.id}`);
    assert(recipe.inputs.length > 0, `Recipe must have inputs: ${recipe.id}`);
    assert(recipe.outputs.length > 0, `Recipe must have outputs: ${recipe.id}`);
    assert(recipe.inputs.every((item) => getItemDefinition(item.key)), `Recipe input item missing from catalog: ${recipe.id}`);
    assert(recipe.outputs.every((item) => getItemDefinition(item.key)), `Recipe output item missing from catalog: ${recipe.id}`);

    const recipePage = page(`crafting-recipe-${recipe.id}`);
    assertEqual(recipePage.source?.kind, 'craftingRecipe', `Recipe page source kind for ${recipe.id}`);
    assertEqual(recipePage.source?.recipe.id, recipe.id, `Recipe page source ID for ${recipe.id}`);
    assertEqual(rowCount(`crafting-recipe-${recipe.id}`, 'Ingredients'), recipe.inputs.length, `Ingredient rows for ${recipe.id}`);
    assertEqual(rowCount(`crafting-recipe-${recipe.id}`, 'Outputs'), recipe.outputs.length, `Output rows for ${recipe.id}`);
  }

  for (const seed of CULTIVATION_SEEDS) {
    assert(seed.durationMs > 0, `Seed duration must be positive: ${seed.seedKey}`);
    assert(seed.outputs.length > 0, `Seed must have outputs: ${seed.seedKey}`);
    assert(getItemDefinition(seed.seedKey), `Seed item missing from item catalog: ${seed.seedKey}`);
    assert(seed.outputs.every((item) => getItemDefinition(item.key)), `Seed output missing from item catalog: ${seed.seedKey}`);
    if (seed.bonusAdditiveKey) assert(getItemDefinition(seed.bonusAdditiveKey), `Seed additive missing from item catalog: ${seed.seedKey}`);

    const seedPage = page(`cultivation-seed-${seed.seedKey}`);
    assertEqual(seedPage.source?.kind, 'cultivationSeed', `Seed page source kind for ${seed.seedKey}`);
    assertEqual(seedPage.source?.seed.seedKey, seed.seedKey, `Seed page source key for ${seed.seedKey}`);
  }
}

function testQuestCoverage() {
  assertEqual(rowCount('quests-overview', 'Quest chain'), QUESTS.length, 'Quest overview rows');

  const seenQuestIds = new Set<string>();
  for (const quest of QUESTS) {
    assert(!seenQuestIds.has(quest.id), `Quest ID must be unique: ${quest.id}`);
    if (quest.prereqQuestId) {
      assert(seenQuestIds.has(quest.prereqQuestId), `Quest prerequisite must exist earlier in chain: ${quest.id}`);
    }
    seenQuestIds.add(quest.id);

    assert(quest.minLevel >= 1, `Quest minLevel must be positive: ${quest.id}`);
    assert(quest.objectives.length > 0, `Quest must have objectives: ${quest.id}`);
    assert(quest.objectives.every((objective) => objective.required > 0), `Quest objective required count must be positive: ${quest.id}`);
    assert(quest.reward.xp > 0, `Quest reward XP must be positive: ${quest.id}`);
    assert(quest.reward.gold >= 0, `Quest reward gold must be non-negative: ${quest.id}`);
    assert(quest.reward.items?.every((item) => getItemDefinition(item.key)) ?? true, `Quest reward item missing from catalog: ${quest.id}`);

    const questPage = page(`quest-${quest.id}`);
    assertEqual(questPage.status, 'implemented', `Quest page status for ${quest.id}`);
    assertEqual(questPage.title, quest.title, `Quest page title for ${quest.id}`);
    assertEqual(rowCount(`quest-${quest.id}`, 'Objectives'), quest.objectives.length, `Objective rows for ${quest.id}`);
  }
}

describe('wiki content index', () => {
  test('keeps section and page metadata consistent', testIndexShape);
  test('documents every playable race and class', testRaceAndClassCoverage);
  test('documents every generated ability page', testAbilityPageCoverage);
  test('documents crafting data and referenced items', testCraftingCoverage);
  test('documents quest data', testQuestCoverage);
});
