import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { BODY_VARIANTS, BODY_VARIANT_DISPLAY, CLASS_RENAMES, CLASSES_BY_RACE, DEFAULT_CLASS_NAME, DESTRUCTION_RACES, ORDER_RACES, RACE_DISPLAY, playerRealmForRace } from '../../src/data/careers';
import { PLAYABLE_CHARACTER_PROFILES } from '../../src/data/playableAssets.generated';
import { CAREER_ABILITY_KITS, HOTBAR_KEYS, HOTBAR_SLOT_COUNT } from '../../src/game/abilities/abilityData';
import { abilityUnlockLevel, FULL_KIT_LEVEL } from '../../src/game/abilities/abilityProgression';
import { ITEM_CATALOG, INVENTORY_CAPACITY, EQUIP_SLOT_ORDER, EQUIP_SLOT_LABELS } from '../../src/data/items';
import { CRAFTING_PROFESSIONS, CRAFTING_RECIPES, CULTIVATION_SEEDS, CRAFTING_XP_PER_RANK, CULTIVATION_SLOT_COUNT, createDefaultCraftingState, getEnemyGatheringDefinition, getSalvageOutputs } from '../../src/data/crafting';
import { QUESTS } from '../../src/data/quests';
import * as campaign from '../../src/data/campaign';
import * as campaignSource from '../../src/data/campaign.generated';
import { WORLD_EDITOR_PREFABS, WORLD_EDITOR_PREFAB_GROUPS } from '../../src/world/editor/PrefabCatalog';
import { buildWikiIndex } from '../../src/wiki/wikiContent';
import { DEFAULT_KEYBINDINGS, KEYBIND_CATEGORIES, KEYBIND_DEFINITIONS } from '../../src/data/keybindings';
import { DEFAULT_GAMEPLAY_SETTINGS } from '../../src/state/gameStore';
import { VIEW_DISTANCE_MIN, VIEW_DISTANCE_MAX, VIEW_DISTANCE_STEP } from '../../src/config/viewDistance';
import { GUIDED_TASKS } from '../../src/ui/hud/guidedTasks';
import { ORVR_RULES, ORVR_TRACKS, defaultZoneConfigs } from '../../src/shared/orvr/config';
import type { ZoneDefinition } from '../../src/world/ZoneLoader';
import { assertJsonSerializable, canonicalJson, CONTENT_SCHEMA_VERSION, COORDINATE_CONTRACT, requireUniqueIds, sha256 } from './content-contract';

export { canonicalJson, sourcePointToUnreal, sourceYawToUnrealDegrees } from './content-contract';
export const REPOSITORY_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const DEFAULT_CONTENT_OUTPUT = path.join(REPOSITORY_ROOT, 'artifacts/unreal/content.json');

export interface ExportedMap { id: string; sourcePath: string; definition: ZoneDefinition }

/** Whole map JSON is retained: importer support must not determine what enters this archive. */
async function readMaps(): Promise<{ maps: ExportedMap[]; developmentMaps: ExportedMap[] }> {
  const directory = path.join(REPOSITORY_ROOT, 'public/assets/maps');
  const files = (await readdir(directory)).filter(file => file.endsWith('.json')).sort();
  const all = await Promise.all(files.map(async file => {
    const sourcePath = `public/assets/maps/${file}`;
    const definition = JSON.parse(await readFile(path.join(directory, file), 'utf8')) as ZoneDefinition;
    if (definition.id !== file.slice(0, -5)) throw new Error(`Map filename does not match definition.id: ${sourcePath}`);
    return { id: definition.id, sourcePath, definition };
  }));
  const canonicalIds = new Set(campaign.CAMPAIGN_ZONES.map(zone => zone.id));
  const found = new Set(all.map(map => map.id));
  for (const id of canonicalIds) if (!found.has(id)) throw new Error(`Missing canonical map: ${id}`);
  return { maps: all.filter(map => canonicalIds.has(map.id)), developmentMaps: all.filter(map => !canonicalIds.has(map.id)) };
}

function slug(value: string): string { return value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, ''); }

async function buildContentData() {
  const { maps, developmentMaps } = await readMaps();
  const races = [...ORDER_RACES, ...DESTRUCTION_RACES];
  const classes = races.flatMap(race => CLASSES_BY_RACE[race].map(name => ({ id: slug(name), name, race, realm: playerRealmForRace(race) })));
  const kits = Object.values(CAREER_ABILITY_KITS);
  const definitions = kits.flatMap(kit => kit.abilities);
  const itemDefinitions = Object.values(ITEM_CATALOG);
  const enemyNames = [...new Set([...maps, ...developmentMaps].flatMap(map => (map.definition.enemies ?? []).map(enemy => enemy.name)))].sort();
  return {
    schemaVersion: CONTENT_SCHEMA_VERSION,
    coordinateContract: COORDINATE_CONTRACT,
    careers: {
      races: races.map(id => ({ id, label: RACE_DISPLAY[id], realm: playerRealmForRace(id), classes: CLASSES_BY_RACE[id] })),
      classes, playableProfiles: PLAYABLE_CHARACTER_PROFILES, legacyAliases: CLASS_RENAMES, defaultClass: DEFAULT_CLASS_NAME,
      bodyVariants: BODY_VARIANTS.map(id => ({ id, label: BODY_VARIANT_DISPLAY[id] })),
    },
    abilities: {
      kits, definitions, hotbarKeys: HOTBAR_KEYS, slotCount: HOTBAR_SLOT_COUNT, fullKitLevel: FULL_KIT_LEVEL,
      progression: definitions.map(ability => ({ abilityId: ability.id, unlockLevel: abilityUnlockLevel(ability), activatable: !ability.unavailableReason, unavailableReason: ability.unavailableReason })),
    },
    items: { definitions: itemDefinitions, capacity: INVENTORY_CAPACITY, equipmentSlots: EQUIP_SLOT_ORDER, equipmentSlotLabels: EQUIP_SLOT_LABELS },
    crafting: {
      professions: CRAFTING_PROFESSIONS, recipes: CRAFTING_RECIPES, seeds: CULTIVATION_SEEDS,
      xpPerRank: CRAFTING_XP_PER_RANK, cultivationSlotCount: CULTIVATION_SLOT_COUNT, defaultState: createDefaultCraftingState(),
      gatheringByEnemy: enemyNames.map(enemyName => ({ enemyName, definition: getEnemyGatheringDefinition(enemyName) })),
      salvageByItem: itemDefinitions.map(item => ({ itemKey: item.key, outputs: getSalvageOutputs({ ...item, slot: 0, qty: 1 }) })),
    },
    quests: QUESTS,
    campaign: {
      zones: campaign.CAMPAIGN_ZONES, edges: campaign.CAMPAIGN_GRAPH_EDGES, objectivesByZone: campaign.CAMPAIGN_OBJECTIVES_BY_ZONE,
      sourceDefinition: { ...campaignSource },
      defaults: campaign.buildCampaignSnapshot(null),
      rules: Object.fromEntries(Object.entries(campaign).filter(([key, value]) => key.startsWith('CAMPAIGN_') && (typeof value === 'number' || typeof value === 'string'))),
    },
    maps, developmentMaps,
    sharedCampaign: { rules: ORVR_RULES, tracks: ORVR_TRACKS, defaultZoneConfigs: defaultZoneConfigs(), note: 'Defaults only; authoritative server map configuration also consumes the complete exported maps.' },
    builder: { prefabs: WORLD_EDITOR_PREFABS, groups: WORLD_EDITOR_PREFAB_GROUPS },
    wiki: buildWikiIndex(),
    controls: { definitions: KEYBIND_DEFINITIONS, defaults: DEFAULT_KEYBINDINGS, categories: KEYBIND_CATEGORIES, guidedTasks: GUIDED_TASKS },
    settings: { defaults: DEFAULT_GAMEPLAY_SETTINGS, viewDistance: { min: VIEW_DISTANCE_MIN, max: VIEW_DISTANCE_MAX, step: VIEW_DISTANCE_STEP }, frameRateChoices: [30, 60], renderResolutionChoices: ['auto', 'quality', 'native'] },
  };
}

type ContentData = Awaited<ReturnType<typeof buildContentData>>;
export type ContentManifest = ContentData & { source: {
  campaignVersion: string;
  sha256: string;
  contentSha256: string;
  files: Array<{ path: string; sha256: string }>;
} };

async function sourceFiles(): Promise<ContentManifest['source']['files']> {
  const paths = ['package.json'];
  async function walk(relative: string): Promise<void> {
    for (const entry of await readdir(path.join(REPOSITORY_ROOT, relative), { withFileTypes: true })) {
      const child = `${relative}/${entry.name}`;
      if (entry.isDirectory()) await walk(child);
      else if (/\.(?:tsx?|mjs|json)$/.test(entry.name)) paths.push(child);
    }
  }
  // Include behavior sources as provenance, not just the subset of catalogs understood by the first importer.
  for (const directory of ['src', 'scripts/campaign', 'public/assets/maps']) await walk(directory);
  paths.push('scripts/unreal/export-content.ts', 'scripts/unreal/content-contract.ts');
  return Promise.all(paths.sort().map(async relative => ({ path: relative, sha256: sha256(await readFile(path.join(REPOSITORY_ROOT, relative))) })));
}

export async function buildContentManifest(): Promise<ContentManifest> {
  const data = await buildContentData();
  assertJsonSerializable(data);
  const files = await sourceFiles();
  const manifest = JSON.parse(canonicalJson({
    ...data,
    source: { campaignVersion: campaignSource.CAMPAIGN_STATIC_VERSION, files, sha256: sha256(canonicalJson(files)), contentSha256: sha256(canonicalJson(data)) },
  })) as ContentManifest;
  validateContentManifest(manifest);
  return manifest;
}

export function validateContentManifest(manifest: ContentManifest): void {
  assertJsonSerializable(manifest);
  if (manifest.schemaVersion !== CONTENT_SCHEMA_VERSION) throw new Error('Unsupported content schemaVersion');
  requireUniqueIds(manifest.careers.races, value => value.id, 'race');
  requireUniqueIds(manifest.careers.classes, value => value.id, 'class');
  requireUniqueIds(manifest.careers.playableProfiles, value => value.profileKey, 'playable profile');
  requireUniqueIds(manifest.abilities.definitions, value => value.id, 'ability');
  requireUniqueIds(manifest.items.definitions, value => value.key, 'item');
  requireUniqueIds(manifest.crafting.professions, value => value.id, 'profession');
  requireUniqueIds(manifest.crafting.recipes, value => value.id, 'recipe');
  requireUniqueIds(manifest.crafting.seeds, value => value.seedKey, 'seed');
  requireUniqueIds(manifest.quests, value => value.id, 'quest');
  requireUniqueIds(manifest.builder.prefabs, value => value.kind, 'prefab');
  requireUniqueIds(manifest.wiki.pages, value => value.id, 'wiki page');
  const allMaps = [...manifest.maps, ...manifest.developmentMaps];
  const mapIds = requireUniqueIds(allMaps, value => value.id, 'map');
  const campaignIds = requireUniqueIds(manifest.campaign.zones, value => value.id, 'campaign zone');
  if (manifest.maps.length !== campaignIds.size || manifest.maps.some(map => !campaignIds.has(map.id))) throw new Error('Canonical maps do not match campaign zones');
  for (const map of allMaps) {
    if (map.definition.id !== map.id) throw new Error(`Map ID mismatch: ${map.id}`);
    validateNestedEntityIds(map.definition, `map ${map.id}`);
    for (const trigger of map.definition.zoneTriggers ?? []) {
      if (!mapIds.has(trigger.targetZoneId)) throw new Error(`Unknown travel target ${trigger.targetZoneId} in ${map.id}`);
    }
  }
  const edges = requireUniqueIds(manifest.campaign.edges, edge => `${edge.fromZoneId}->${edge.toZoneId}`, 'campaign edge');
  for (const edge of manifest.campaign.edges) {
    if (!campaignIds.has(edge.fromZoneId) || !campaignIds.has(edge.toZoneId)) throw new Error(`Unknown campaign edge endpoint: ${edge.fromZoneId}->${edge.toZoneId}`);
    if (!edges.has(`${edge.toZoneId}->${edge.fromZoneId}`)) throw new Error(`Missing reverse campaign edge: ${edge.fromZoneId}->${edge.toZoneId}`);
    const map = manifest.maps.find(value => value.id === edge.fromZoneId)!;
    if (!(map.definition.zoneTriggers ?? []).some(trigger => trigger.targetZoneId === edge.toZoneId)) throw new Error(`Missing travel trigger for ${edge.fromZoneId}->${edge.toZoneId}`);
  }
  for (const map of manifest.maps) for (const trigger of map.definition.zoneTriggers ?? []) {
    if (!edges.has(`${map.id}->${trigger.targetZoneId}`)) throw new Error(`Travel trigger missing campaign edge: ${map.id}->${trigger.targetZoneId}`);
  }
  for (const [zoneId, objectives] of Object.entries(manifest.campaign.objectivesByZone)) {
    if (!campaignIds.has(zoneId)) throw new Error(`Unknown objective zone: ${zoneId}`);
    const ids = requireUniqueIds(objectives, objective => objective.id, `objective in ${zoneId}`);
    for (const objective of objectives) for (const required of objective.requiresObjectiveIds ?? []) {
      if (!ids.has(required)) throw new Error(`Unknown prerequisite objective ${required} in ${zoneId}`);
    }
  }
  const files = requireUniqueIds(manifest.source.files, entry => entry.path, 'source file');
  if (!files.size || manifest.source.files.some(entry => !/^[a-f0-9]{64}$/.test(entry.sha256))) throw new Error('Invalid source file hashes');
  if (sha256(canonicalJson(manifest.source.files)) !== manifest.source.sha256) throw new Error('Source hash mismatch');
  const { source, ...data } = manifest;
  if (sha256(canonicalJson(data)) !== source.contentSha256) throw new Error('Content hash mismatch');
}

function validateNestedEntityIds(value: unknown, label: string): void {
  if (Array.isArray(value)) {
    const entities = value.filter((entry): entry is { id: string } => Boolean(entry && typeof entry === 'object' && 'id' in entry));
    requireUniqueIds(entities, entry => entry.id, label);
    value.forEach((entry, index) => validateNestedEntityIds(entry, `${label}[${index}]`));
  } else if (value && typeof value === 'object') {
    for (const [key, entry] of Object.entries(value)) validateNestedEntityIds(entry, `${label}.${key}`);
  }
}

export async function exportContent({ output = DEFAULT_CONTENT_OUTPUT, check = false }: { output?: string; check?: boolean } = {}): Promise<ContentManifest> {
  const manifest = await buildContentManifest();
  const content = canonicalJson(manifest);
  if (check) {
    const existing = await readFile(output, 'utf8').catch(() => null);
    if (existing !== content) throw new Error(`Content export is missing or stale: ${output}. Run the exporter without --check.`);
  } else {
    await mkdir(path.dirname(output), { recursive: true });
    await writeFile(output, content, 'utf8');
  }
  return manifest;
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  let output = DEFAULT_CONTENT_OUTPUT;
  let check = false;
  for (let index = 0; index < args.length; index++) {
    if (args[index] === '--check') check = true;
    else if (args[index] === '--output' && args[index + 1] && !args[index + 1].startsWith('--')) output = path.resolve(args[++index]);
    else throw new Error(`Unknown or incomplete option: ${args[index]}. Usage: tsx scripts/unreal/export-content.ts [--output path] [--check]`);
  }
  const manifest = await exportContent({ output, check });
  console.log(`${check ? 'Verified' : 'Exported'} Unreal content v${manifest.schemaVersion}: ${manifest.maps.length} campaign maps, ${manifest.abilities.definitions.length} abilities, ${manifest.items.definitions.length} items -> ${output}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
}
