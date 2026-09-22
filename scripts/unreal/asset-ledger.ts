import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import ts from 'typescript';
import { readBrowserReference } from './browser-reference';
import { PLAYABLE_CHARACTER_PROFILES } from '../../shared/data/playableAssets.generated';
import { ITEM_CATALOG } from '../../shared/data/items';
import { aegisEnemyGuardVariantFor, aegisHouseResidentVariantFor, aegisNpcCivilianVariantFor,
  aegisNpcGuardVariantFor, playerModelOverrideForRace } from '../../shared/data/modelOverrides';
import { worldLifeCharacterProfile } from '../../shared/world/worldLifeModels';
import { applyBiomeKits } from '../../shared/world/BiomeKit';
import { applyZonePaths } from '../../shared/world/PathKit';
import { WORLD_EDITOR_PREFABS } from '../../shared/world/editor/PrefabCatalog';
import { campaignNpcProfile } from '../../shared/assets/campaignModels';
import { CARAVAN_DRIVER_PROFILE } from '../../shared/assets/caravanModels';
import { SIEGE_ASSET_KEYS } from '../../shared/assets/siegeModels';
import { recruitCombatProfile } from '../../server/abilityCatalog';
import { loadCampaignMapConfigs } from '../../server/mapConfig';
import type { ZoneDefinition, NpcSpawn, EnemySpawn } from '../../shared/world/ZoneDefinition';
import { containedPath, fileHash, inspectGlb, readJson, type GlbEvidence } from './asset-evidence';
import { auditPrimitives } from './primitive-audit';

type Category = 'characterProfiles' | 'staticProps' | 'equipment';
interface AnimationPack { model: string; sha256?: string; skeletonId?: string; bindPoseId?: string }
interface IndexedAsset {
  model?: string; modelSha256?: string; assetId?: string; bodyFamily?: string; bodyVariant?: string;
  skeletonId?: string; bindPoseId?: string; qc?: string; qcSha256?: string; runtimeReady?: boolean;
  approvalState?: string; lifecycleStatus?: string; reviewStatus?: string; animationPack?: AnimationPack;
  operatorAnimationPacks?: Record<string, AnimationPack>; variants?: Record<string, IndexedAsset>;
}
type AssetIndex = Record<Category, Record<string, IndexedAsset>> & { assetVersion?: string };
interface Qc { model?: string; modelSha256?: string; qcPassed?: boolean; reviewStatus?: string; lifecycleStatus?: string;
  provenance?: unknown; lods?: Lod[]; builtLods?: Lod[]; validationErrors?: number }
interface Lod { model?: string; sha256?: string; name?: string; level?: number }
interface SourceRecord { path: string; provenance: unknown; licenses: string[]; approvalState?: string }
interface Identity { race: string | null; species: string | null; bodyVariant: string | null; role: string; identitySource?: string }
interface Request { profileKey?: string; assetKey?: string; model?: string; category?: Category }
interface Resolution { category?: Category; key?: string; model?: string; entry?: IndexedAsset; method: string }
export interface AssetAssignment extends Identity {
  id: string; surface: string; source: string; entityId: string; zoneId?: string; className?: string;
  instanceIds?: string[];
  requested: Request; resolved: { key: string | null; category: Category | null; modelPath: string | null; method: string };
  modelEvidence: string | null; rig: { skeletonId: string | null; bindPoseId: string | null; bodyFamily: string | null; joints: number[] };
  clips: string[]; requiredClips: string[]; lods: Array<{ path: string; expectedHash: string | null; matchesHash: boolean | null }>;
  animationPacks: Array<{ path: string; target: 'model' | 'operator'; expectedHash: string | null; matchesHash: boolean | null; compatibleRig: boolean | null }>;
  provenance: Array<Pick<SourceRecord, 'path' | 'licenses' | 'approvalState'>>; status: 'blocked' | 'candidate'; blockers: string[]; reviewRequirements: string[];
  candidates: Array<{ profileKey: string; modelPath: string; status: 'adaptation_candidate_not_approved'; work: string[] }>;
  notes: string[];
}
interface AssignmentInput extends Partial<Identity> {
  id: string; surface: string; source: string; entityId: string; zoneId?: string; className?: string;
  requested: Request; resolution: Resolution; requiredClips?: string[]; requiresSkin?: boolean;
  instanceIds?: string[]; requiresModel?: boolean;
  blockers?: string[]; notes?: string[]; packs?: AnimationPack[]; explicitLods?: string[];
}
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const MODEL_ROOT = 'public/assets/models/';
const COMBAT_CLIPS = ['idle', 'walk', 'run', 'jump', 'death', 'combat_idle', 'attack_melee', 'attack_ranged', 'cast'];
const REVIEW_REQUIREMENTS = ['unreal_import_and_cook_unverified', 'visual_identity_and_nonprimitive_art_unverified',
  'rig_animation_equipment_collision_lod_budget_unverified', 'commercial_source_rights_unverified'];
const sortedUnique = (values: string[]) => [...new Set(values)].sort();

function approved(entry: IndexedAsset | undefined): entry is IndexedAsset {
  const lifecycle = entry?.lifecycleStatus?.trim().toLowerCase(), review = entry?.reviewStatus?.trim().toLowerCase();
  return Boolean(entry?.model && entry.runtimeReady !== false && (!lifecycle || lifecycle === 'approved') && (!review || review === 'approved'));
}

function licenses(value: unknown): string[] {
  if (!value || typeof value !== 'object') return [];
  return Object.entries(value).flatMap(([key, child]) => /license/i.test(key) && typeof child === 'string'
    ? [child] : licenses(child));
}

function sourceRecords(root: string): Map<string, SourceRecord[]> {
  const records = new Map<string, SourceRecord[]>();
  for (const directory of ['scripts/blender-character-pipeline/data/approved-assets', 'scripts/blender-character-pipeline/data/asset-blueprints']) {
    for (const filename of readdirSync(path.join(root, directory)).filter(file => file.endsWith('.json')).sort()) {
      const sourcePath = `${directory}/${filename}`;
      const value = readJson<{ model?: string; output?: { model?: string }; provenance?: unknown; approvalState?: string }>(root, sourcePath);
      const model = value.model ?? value.output?.model;
      if (!model) continue;
      const rows = records.get(model) ?? [];
      rows.push({ path: sourcePath, provenance: value.provenance ?? null, licenses: sortedUnique(licenses(value)), approvalState: value.approvalState });
      records.set(model, rows);
    }
  }
  return records;
}

function inferRace(key: string): string | null {
  const families: Record<string, string> = { civic: 'empire', stone: 'dwarf', aether: 'high_elf', riven: 'chaos', mire: 'greenskin', umbra: 'dark_elf' };
  const family = families[key.split('_')[0]];
  if (family) return family;
  for (const race of ['high_elf', 'dark_elf', 'greenskin', 'dwarf', 'chaos', 'empire']) if (key.includes(race)) return race;
  if (key.startsWith('npc_aegis_city_guard_') || key.startsWith('npc_aegis_people_')) return 'empire';
  return null;
}

function speciesFor(key: string): string | null {
  const match = key.match(/(?:creature_|frontier_sunmeadow_)(.+?)(?:_lod\d)?(?:\.glb)?$/);
  if (match && /wolf|spider|fox|hare|deer|boar|ram|hound|bear|snapper|toad|stag|drake/.test(match[1])) return match[1];
  return /draft_horse/.test(key) ? 'draft_horse' : null;
}

function previewReferences(source: string): Array<{ key?: string; model: string; line: number }> {
  const tree = ts.createSourceFile('CharacterPreviewStage.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const references: Array<{ key?: string; model: string; line: number }> = [];
  const visit = (node: ts.Node) => {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression)) {
      const name = node.expression.text;
      const key = name === 'addStaticProp' && node.arguments[2];
      const model = node.arguments[name === 'addStaticProp' ? 3 : 2];
      if ((name === 'addStaticProp' || name === 'addModel') && model && ts.isStringLiteral(model)) {
        references.push({ ...(key && ts.isStringLiteral(key) ? { key: key.text } : {}), model: model.text,
          line: tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1 });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(tree); return references;
}

/** Reads all current authored content; does not launch a browser/server or approve an Unreal import. */
export async function buildAssetLedger(repoRoot = ROOT) {
  const root = path.resolve(repoRoot);
  const index = readJson<AssetIndex>(root, `${MODEL_ROOT}asset-index.json`);
  const reviews = readJson<{ schemaVersion: number; reviews: Array<{ sourceSha256: string; status: string; reason: string }> }>(root, 'migration/visual-reviews.json');
  if (reviews.schemaVersion !== 1) throw new Error('Unsupported visual review schema.');
  const rejectedSources = new Map(reviews.reviews.filter(row => row.status === 'rejected').map(row => [row.sourceSha256, row.reason]));
  const sources = sourceRecords(root);
  const roster = readJson<{ profiles: Array<{ profileKey: string; raceKey: string; variant: string; role: string }> }>(root,
    'scripts/blender-character-pipeline/data/npc-character-roster.json');
  const identities = new Map(roster.profiles.map(profile => [profile.profileKey, profile]));
  const models: Record<string, GlbEvidence> = {};
  const hashCache = new Map<string, string>();
  const hash = (relative: string) => {
    let value = hashCache.get(relative);
    if (!value) { value = fileHash(containedPath(root, relative)); hashCache.set(relative, value); }
    return value;
  };
  const qcCache = new Map<string, Qc>();
  const assignments: AssetAssignment[] = [];
  const inspect = (model: string) => {
    const relative = `${MODEL_ROOT}${model}`;
    return models[relative] ??= inspectGlb(root, relative);
  };
  const qcFor = (entry?: IndexedAsset): Qc | undefined => {
    if (!entry?.qc) return undefined;
    if (qcCache.has(entry.qc)) return qcCache.get(entry.qc);
    if (!existsSync(containedPath(root, `${MODEL_ROOT}${entry.qc}`))) return undefined;
    const qc = readJson<Qc>(root, `${MODEL_ROOT}${entry.qc}`);
    qcCache.set(entry.qc, qc); return qc;
  };
  const resolve = (category: Category, key: string, direct?: string): Resolution => {
    const entry = index[category]?.[key];
    return { category, key, entry, model: approved(entry) ? entry.model : direct, method: approved(entry) ? 'registry' : direct ? 'direct_file' : 'unresolved' };
  };
  const identity = (profile?: string): Partial<Identity> => {
    const row = profile ? identities.get(profile) : undefined;
    return row ? { race: row.raceKey, bodyVariant: row.variant, role: row.role, identitySource: 'npc_roster' }
      : { race: profile ? inferRace(profile) : null, bodyVariant: profile ? index.characterProfiles[profile]?.bodyVariant ?? null : null,
        identitySource: 'profile_semantics_or_unspecified' };
  };
  const candidatesFor = (race: string | null, variant: string | null, species: string | null, key?: string) => {
    const pool = species ? Object.entries(index.staticProps).filter(([candidate]) => {
      if (/hound|wolf/.test(species)) return /(?:creature_barrow_wolf|frontier_sunmeadow_barrow_wolf)$/.test(candidate);
      if (/stag|deer/.test(species)) return candidate === 'frontier_sunmeadow_roe_deer_buck';
      return speciesFor(candidate) === species;
    }) : Object.entries(index.characterProfiles).filter(([candidate]) => candidate !== key && inferRace(candidate) === race && race !== null);
    const unique = new Set<string>();
    return pool.filter(([, entry]) => approved(entry) && !rejectedSources.has(entry.modelSha256 ?? '') && entry.model && !unique.has(entry.model) && Boolean(unique.add(entry.model)))
      .sort(([a, left], [b, right]) => Number(right.bodyVariant === variant) - Number(left.bodyVariant === variant) || a.localeCompare(b))
      .filter(([, entry]) => {
        const evidence = inspect(entry.model!);
        return evidence.valid && evidence.meshes > 0 && !rejectedSources.has(evidence.sha256 ?? '');
      }).slice(0, 4)
      .map(([profileKey, entry]) => ({ profileKey, modelPath: `${MODEL_ROOT}${entry.model}`, status: 'adaptation_candidate_not_approved' as const,
        work: [variant && entry.bodyVariant !== variant ? 'body_variant_adaptation_required' : 'preserve_authored_body_variant',
          'role_class_or_species_art_review_required', 'rig_equipment_animation_and_unreal_import_required'] }));
  };
  const add = (input: AssignmentInput) => {
    const { entry, model, key, category, method } = input.resolution;
    const evidence = model ? inspect(model) : undefined;
    const qc = qcFor(entry);
    const blockers = [...(input.blockers ?? [])];
    if (evidence?.sha256 && rejectedSources.has(evidence.sha256)) blockers.push(`visual_source_rejected:${rejectedSources.get(evidence.sha256)}`);
    if (!model) { if (input.requiresModel !== false) blockers.push('no_model_assignment'); }
    else if (!evidence?.exists) blockers.push('model_file_missing');
    else if (!evidence.valid) blockers.push('invalid_model_binary_or_dependencies');
    else if (!evidence.meshes || !evidence.triangles) blockers.push('no_renderable_mesh');
    if (evidence?.exists && entry?.modelSha256 && evidence.sha256 !== entry.modelSha256) blockers.push('registry_model_hash_mismatch');
    if (entry?.qc && !qc) blockers.push('qc_file_missing');
    if (qc && entry?.qcSha256 && hash(`${MODEL_ROOT}${entry.qc}`) !== entry.qcSha256) blockers.push('qc_hash_mismatch');
    if (qc?.modelSha256 && evidence?.exists && qc.modelSha256 !== evidence.sha256) blockers.push('qc_model_hash_mismatch');
    if (input.requiresSkin && evidence?.valid && !evidence.skins) blockers.push('character_skin_missing');
    if (input.bodyVariant && entry?.bodyVariant && input.bodyVariant !== entry.bodyVariant) blockers.push('body_variant_mismatch');
    const resolvedRace = key ? inferRace(key) : null;
    if (input.race && resolvedRace && input.race !== resolvedRace) blockers.push('race_mismatch');
    const packs = [...(entry?.animationPack ? [{ pack: entry.animationPack, target: category === 'staticProps' ? 'operator' as const : 'model' as const }] : []),
      ...(input.packs ?? []).map(pack => ({ pack, target: 'model' as const }))];
    const animationPacks = packs.map(({ pack, target }) => {
      const inspected = inspect(pack.model);
      // A wagon advertises its driver's pack; it must not be compared to the wagon mechanism rig.
      const compatibleRig = target === 'operator' ? null : (!entry?.skeletonId || !pack.skeletonId || pack.skeletonId === entry.skeletonId)
        && (!entry?.bindPoseId || !pack.bindPoseId || pack.bindPoseId === entry.bindPoseId);
      const matchesHash = pack.sha256 ? inspected.sha256 === pack.sha256 : null;
      if (!inspected.valid || matchesHash === false || compatibleRig === false) blockers.push('animation_pack_invalid_or_incompatible');
      return { path: inspected.path, target, expectedHash: pack.sha256 ?? null, matchesHash, compatibleRig };
    });
    const clips = sortedUnique([...(evidence?.clips ?? []), ...animationPacks.filter(pack => pack.compatibleRig && pack.matchesHash !== false)
      .flatMap(pack => models[pack.path].clips)]);
    for (const clip of input.requiredClips ?? []) if (!clips.includes(clip)) blockers.push(`animation_missing:${clip}`);
    const rawLods = [...(qc?.builtLods ?? qc?.lods ?? []), ...(input.explicitLods ?? []).map(lod => ({ model: lod }))];
    const lods = rawLods.filter((lod): lod is Lod & { model: string } => typeof lod.model === 'string').map(lod => {
      const inspected = inspect(lod.model);
      const matchesHash = lod.sha256 ? inspected.sha256 === lod.sha256 : null;
      if (!inspected.valid || matchesHash === false) blockers.push('lod_missing_invalid_or_hash_mismatch');
      return { path: inspected.path, expectedHash: lod.sha256 ?? null, matchesHash };
    });
    const provenance = [...(model ? sources.get(model) ?? [] : []), ...(qc?.provenance ? [{ path: `${MODEL_ROOT}${entry!.qc}`,
      provenance: qc.provenance, licenses: sortedUnique(licenses(qc.provenance)) }] : [])];
    const notes = [...(input.notes ?? [])];
    if (qc?.lifecycleStatus === 'draft' || qc?.reviewStatus && qc.reviewStatus !== 'approved') notes.push('source_qc_is_not_final_art_approval');
    if (model && !provenance.length) notes.push('no_direct_provenance_record_found_follow_upstream_sources');
    const race = input.race ?? null, variant = input.bodyVariant ?? null, species = input.species ?? null;
    assignments.push({ id: input.id, surface: input.surface, source: input.source, entityId: input.entityId,
      ...(input.zoneId ? { zoneId: input.zoneId } : {}), ...(input.className ? { className: input.className } : {}),
      ...(input.instanceIds ? { instanceIds: input.instanceIds } : {}),
      race, species, bodyVariant: variant, role: input.role ?? 'unspecified', identitySource: input.identitySource ?? 'authored_definition',
      requested: input.requested, resolved: { key: key ?? null, category: category ?? null, modelPath: evidence?.path ?? null, method },
      modelEvidence: evidence?.path ?? null, rig: { skeletonId: entry?.skeletonId ?? null, bindPoseId: entry?.bindPoseId ?? null,
        bodyFamily: entry?.bodyFamily ?? null, joints: evidence?.joints ?? [] }, clips, requiredClips: input.requiredClips ?? [],
      lods, animationPacks, provenance: provenance.map(({ path, licenses, ...record }) => ({ path, licenses,
        ...('approvalState' in record ? { approvalState: record.approvalState } : {}) })),
      status: blockers.length ? 'blocked' : 'candidate', blockers: sortedUnique(blockers),
      reviewRequirements: [...REVIEW_REQUIREMENTS], candidates: candidatesFor(race, variant, species, key), notes: sortedUnique(notes) });
  };

  for (const profile of PLAYABLE_CHARACTER_PROFILES) {
    const exact = resolve('characterProfiles', profile.profileKey);
    const override = playerModelOverrideForRace(profile.race);
    const resolution = exact.model ? exact : { ...resolve('characterProfiles', override.profileKey, override.fallbackModel), method: 'realm_override_then_primitive_fallback' };
    for (const surface of ['playable', 'character_preview']) add({ id: `${surface}:${profile.profileKey}`, surface,
      source: surface === 'playable' ? 'src/game/Player.ts' : 'src/ui/screens/CharacterPreviewStage.tsx', entityId: profile.profileKey,
      race: profile.race, bodyVariant: profile.bodyVariant, role: 'player', className: profile.className, requiresSkin: true,
      requested: { profileKey: profile.profileKey }, resolution, requiredClips: COMBAT_CLIPS,
      blockers: exact.model ? [] : ['exact_playable_profile_missing'], notes: ['Preview uses the Player assembly path.'] });
    for (const armor of Object.values(profile.armor)) {
      const resolution = resolve('equipment', armor.itemKey, armor.model);
      add({ id: `playable_equipment:${profile.profileKey}:${armor.slot}`, surface: 'playable_equipment', source: 'src/data/playableAssets.generated.ts',
        entityId: armor.itemKey, race: profile.race, bodyVariant: profile.bodyVariant, role: armor.slot, className: profile.className,
        requested: { assetKey: armor.itemKey, model: armor.model, category: 'equipment' }, resolution, requiresSkin: true,
        notes: ['Attachment/body masking compatibility still requires character assembly validation.'] });
    }
  }
  const previewSource = 'src/ui/screens/CharacterPreviewStage.tsx';
  for (const reference of previewReferences(readBrowserReference(previewSource, root))) add({
    id: `preview_environment:${reference.line}`, surface: 'preview_environment', source: `${previewSource}:${reference.line}`,
    entityId: reference.key ?? reference.model, role: 'preview_scenery', requested: { assetKey: reference.key, model: reference.model },
    resolution: reference.key ? resolve('staticProps', reference.key, reference.model) : { model: reference.model, method: 'direct_file' } });
  for (const race of sortedUnique(PLAYABLE_CHARACTER_PROFILES.map(profile => profile.race))) add({
    id: `preview_geometry:${race}`, surface: 'preview_geometry', source: previewSource, entityId: race, race, role: 'preview_stage',
    requested: {}, resolution: { method: 'procedural_preview_environment' }, notes: ['Preview floor, backdrop, scenery and race-specific fixtures also contain procedural geometry; classify and replace visible placeholder scenery while preserving preview behavior.'] });

  const mapFiles = readdirSync(path.join(root, 'public/assets/maps')).filter(file => file.endsWith('.json')).sort();
  const maps = mapFiles.map(file => ({ source: `public/assets/maps/${file}`, zone: readJson<ZoneDefinition>(root, `public/assets/maps/${file}`) }));
  const npcResolution = (npc: NpcSpawn): Resolution => {
    const override = aegisNpcGuardVariantFor(npc.role, npc.characterProfileKey, npc.id)
      ?? aegisNpcCivilianVariantFor(npc.role, npc.characterProfileKey, npc.id);
    if (npc.approvedOnly && !approved(index.characterProfiles[override?.profileKey ?? npc.characterProfileKey ?? ''])) {
      return { key: override?.profileKey ?? npc.characterProfileKey, category: 'characterProfiles', method: 'approved_only_npc_omitted' };
    }
    if (override) return { ...resolve('characterProfiles', override.profileKey, override.fallbackModel), method: 'aegis_role_override' };
    return resolve('characterProfiles', npc.characterProfileKey ?? '', npc.model ?? (npc.role === 'guard' ? 'guard_male.glb' : undefined));
  };
  const enemyResolution = (enemy: EnemySpawn): Resolution => {
    const override = aegisEnemyGuardVariantFor(enemy.archetype, enemy.characterProfileKey, enemy.name, enemy.id);
    if (override) return { ...resolve('characterProfiles', override.profileKey, override.fallbackModel), method: 'aegis_guard_override' };
    if (enemy.characterProfileKey) { const profile = resolve('characterProfiles', enemy.characterProfileKey); if (profile.model) return profile; }
    const fallback = enemy.model ?? 'prop_training_dummy_t1.glb';
    const staticKey = enemy.assetKey ?? (!enemy.model || enemy.model === 'dummy.glb' ? 'dummy' : undefined);
    return staticKey ? resolve('staticProps', staticKey, fallback) : { model: fallback, method: 'direct_file' };
  };
  for (const { source, zone } of maps) {
    const withPaths = applyZonePaths(zone), withBiomes = applyBiomeKits(withPaths);
    const generated = [
      { surface: 'generated_path', props: withPaths.props.slice(zone.props.length), technical: true },
      { surface: 'generated_biome', props: withBiomes.props.slice(withPaths.props.length), technical: false },
    ];
    for (const { surface, props, technical } of generated) {
      const groups = new Map<string, string[]>();
      for (const [position, prop] of props.entries()) { const group = groups.get(prop.kind) ?? []; group.push(prop.id ?? `${surface}_${position}`); groups.set(prop.kind, group); }
      for (const [kind, ids] of groups) add({ id: `${surface}:${zone.id}:${kind}`, surface, source, zoneId: zone.id, entityId: kind,
        instanceIds: ids.sort(), role: kind, requested: {}, resolution: { method: technical ? 'procedural_terrain_path' : 'procedural_scatter_model' },
        requiresModel: !technical, notes: [technical ? 'Terrain-conforming paths are allowed engineering geometry; preserve them with Unreal terrain/material authoring.'
          : 'All deterministic scatter instances are included; replace visible primitive vegetation with authored assets.'] });
    }
    add({ id: `terrain:${zone.id}`, surface: 'terrain', source, zoneId: zone.id, entityId: zone.id, role: 'terrain',
      requested: { model: zone.terrainModel }, resolution: { model: zone.terrainModel, method: zone.terrainModel ? 'direct_file' : 'procedural_heightfield' },
      requiresModel: Boolean(zone.terrainModel), notes: ['Heightfield/landscape is allowed engineering geometry; native Unreal terrain still requires topology, collision, navigation, and visual parity evidence.'] });
    for (const npc of zone.npcs ?? []) {
      const original = identity(npc.characterProfileKey);
      add({ id: `local_npc:${zone.id}:${npc.id}`, surface: 'local_npc', source, zoneId: zone.id, entityId: npc.id,
        ...original, role: npc.role, requested: { profileKey: npc.characterProfileKey, model: npc.model }, resolution: npcResolution(npc),
        requiresSkin: true, requiredClips: ['idle'], notes: npc.approvedOnly ? ['Existing runtime omits unavailable approved-only NPCs.'] : [] });
      const assigned = zone.orvrLayout?.populationAssignments.find(assignment => assignment.entityId === npc.id);
      const profile = campaignNpcProfile({ id: npc.id, role: assigned?.role ?? npc.role, race: assigned?.race, profileKey: npc.characterProfileKey });
      add({ id: `shared_service_npc:${zone.id}:${npc.id}`, surface: 'shared_service_npc', source, zoneId: zone.id, entityId: npc.id,
        ...original, race: assigned?.race ?? original.race, role: assigned?.role ?? npc.role, requested: { profileKey: npc.characterProfileKey },
        resolution: resolve('characterProfiles', profile ?? ''), requiresSkin: true, requiredClips: ['idle'],
        notes: ['Shared renderer service-population path; visibility depends on active map and player range.'] });
    }
    for (const enemy of zone.enemies ?? []) {
      const resolution = enemyResolution(enemy);
      const dummySubstitution = resolution.model === 'prop_training_dummy_t1.glb' && enemy.assetKey !== 'dummy' && enemy.model !== 'dummy.glb';
      add({ id: `local_enemy:${zone.id}:${enemy.id}`, surface: 'local_enemy', source, zoneId: zone.id, entityId: enemy.id,
        ...identity(enemy.characterProfileKey), species: speciesFor(enemy.assetKey ?? ''), role: enemy.archetype ?? enemy.assetKey ?? 'enemy',
        requested: { profileKey: enemy.characterProfileKey, assetKey: enemy.assetKey, model: enemy.model }, resolution,
        requiresSkin: Boolean(enemy.characterProfileKey), requiredClips: enemy.characterProfileKey ? ['idle', 'walk', 'attack_melee', 'death'] : [],
        blockers: dummySubstitution ? ['semantic_training_dummy_substitution'] : [] });
    }
    for (const actor of zone.ambientLife?.actors ?? []) {
      const realm = zone.campaign?.realm === 'riftbound' ? 'riftbound' : 'aegis';
      const profile = zone.cityLayoutVersion ? worldLifeCharacterProfile(actor, realm) : null;
      add({ id: `ambient:${zone.id}:${actor.id}`, surface: 'ambient', source, zoneId: zone.id, entityId: actor.id,
        ...identity(actor.characterProfileKey ?? profile ?? undefined), species: actor.kind === 'deer' || actor.kind === 'bird' ? actor.kind : null,
        role: actor.kind, requested: { profileKey: actor.characterProfileKey }, resolution: profile ? resolve('characterProfiles', profile)
          : { method: actor.approvedOnly ? 'approved_only_actor_omitted' : 'procedural_actor' }, requiresSkin: true,
        requiredClips: ['idle', ...(actor.route?.length ? ['walk'] : [])],
        notes: ['Includes configured actors even when runtime population limits or distance culling hide them.'] });
    }
    for (const [position, prop] of (zone.props ?? []).entries()) {
      if (prop.visible === false) continue;
      const key = prop.assetKey ?? (prop.kind === 'dummy' || prop.model === 'dummy.glb' ? 'dummy' : undefined);
      add({ id: `world_prop:${zone.id}:${prop.id ?? position}`, surface: 'world_prop', source, zoneId: zone.id, entityId: prop.id ?? String(position),
        species: speciesFor(key ?? prop.model ?? ''), role: prop.kind, requested: { assetKey: key, model: prop.model },
        resolution: key ? resolve('staticProps', key, prop.model || 'prop_training_dummy_t1.glb') : { model: prop.model, method: prop.model ? 'direct_file' : 'procedural_world_geometry' },
        explicitLods: prop.lodModels, requiresModel: !/^path_(?:dirt|cobblestone|brick)$/.test(prop.kind),
        notes: ['Procedural terrain/path geometry requires classification; absence of a mesh file never authorizes feature removal.'] });
    }
    for (const assignment of zone.orvrLayout?.populationAssignments ?? []) add({ id: `planned_population:${zone.id}:${assignment.entityId}`,
      surface: 'planned_population', source, zoneId: zone.id, entityId: assignment.entityId, race: assignment.race, role: assignment.role,
      requested: { profileKey: assignment.desiredProfileKey }, resolution: resolve('characterProfiles', assignment.desiredProfileKey),
      requiresSkin: true, requiredClips: ['idle'], notes: [`Authored population assignment status: ${assignment.status}; planned identity is preserved separately from runtime substitutions.`] });
    for (const key of sortedUnique([...(zone.orvrLayout?.assetPolicy.requiredAssetKeys ?? []), ...(zone.orvrLayout?.assetPolicy.optionalAssetKeys ?? []),
      ...(zone.orvrLayout?.biome.creatureProfileKeys ?? [])])) add({ id: `world_contract:${zone.id}:${key}`, surface: 'world_contract', source,
      zoneId: zone.id, entityId: key, species: speciesFor(key), role: 'authored_contract', requested: { assetKey: key }, resolution: resolve('staticProps', key),
      notes: ['Includes optional/planned art keys; gameplay travel optionality does not excuse missing art coverage.'] });
  }

  for (const variant of ['small', 'large', 'tavern', 'shop', 'chapel', 'civic'] as const) for (let person = 0; person < (variant === 'large' ? 3 : 2); person++) {
    const choice = aegisHouseResidentVariantFor(variant, person);
    for (const mode of variant === 'small' || variant === 'large' ? ['default', 'city'] : ['city']) add({
      id: `interior:${mode}:${variant}:${person + 1}`, surface: 'interior', source: 'src/game/HouseInteriorRuntime.ts', entityId: `${variant}-resident-${person + 1}`,
      role: variant === 'chapel' ? 'attendant' : 'resident', race: 'empire', requested: { profileKey: choice.profileKey },
      resolution: mode === 'city' ? resolve('characterProfiles', choice.profileKey, choice.fallbackModel) : { method: 'procedural_resident' },
      requiresSkin: true, requiredClips: ['idle'], notes: ['Generated room template; instances share these residents. Default small/large rooms have procedural occupants until city-room replacement runs.'] });
  }

  for (const realm of ['aegis', 'riftbound'] as const) {
    const recruit = recruitCombatProfile(realm);
    add({ id: `shared_player:${realm}`, surface: 'shared_player', source: 'server/abilityCatalog.ts', entityId: realm,
      ...identity(recruit.avatarProfileKey), role: 'network_recruit', className: recruit.className, requested: { profileKey: recruit.avatarProfileKey },
      resolution: resolve('characterProfiles', recruit.avatarProfileKey!), requiresSkin: true, requiredClips: COMBAT_CLIPS });
    for (const kind of Object.keys(SIEGE_ASSET_KEYS)) for (const seat of kind === 'ram' ? ['left', 'right'] : ['operator']) add({
      id: `siege_crew:${realm}:${kind}:${seat}`, surface: 'siege_crew', source: 'src/game/network/CampaignSiegeCrewPresentation.ts', entityId: `${realm}:${kind}:${seat}`,
      ...identity(recruit.avatarProfileKey), role: `${kind}_${seat}`, requested: { profileKey: recruit.avatarProfileKey },
      resolution: resolve('characterProfiles', recruit.avatarProfileKey!), requiresSkin: true,
      packs: kind === 'ram' ? [index.staticProps.frontier_battering_ram?.operatorAnimationPacks?.[seat]].filter((pack): pack is AnimationPack => Boolean(pack)) : [],
      requiredClips: kind === 'ram' ? ['ram_crew_idle', 'ram_crew_drive', 'ram_crew_strike'] : ['idle'],
      blockers: kind === 'ram' && recruit.avatarProfileKey !== 'civic_battle_prelate_m' ? ['ram_operator_rig_not_supported_by_current_runtime'] : [],
      notes: ['Operator is the actual player avatar, not a separate dummy; every future playable rig must preserve this interaction.'] });
  }
  const configs = await loadCampaignMapConfigs(path.join(root, 'public/assets/maps'));
  for (const config of configs) {
    const map = maps.find(item => item.zone.id === config.id)!;
    const rows = map.zone.orvrLayout?.populationAssignments ?? [];
    for (const objective of config.objectives) for (let guard = 0; guard < (objective.guardCount ?? 2); guard++) {
      const id = `${objective.id}_guard_${guard}`;
      const assigned = rows.find(row => row.entityId === id) ?? rows.find(row => row.entityId.startsWith(objective.id.replace(/_objective$/, '') + '_') && row.role === 'guard');
      for (const realm of [null, 'aegis', 'riftbound'] as const) {
        const profile = campaignNpcProfile({ id, role: 'guard', race: assigned?.race, realm }) ?? campaignNpcProfile({ id, role: 'guard', realm });
        add({ id: `shared_guard:${config.id}:${id}:${realm ?? 'neutral'}`, surface: 'shared_guard', source: 'src/shared/orvr/simulation.ts',
          entityId: id, zoneId: config.id, race: assigned?.race, role: 'guard', requested: { profileKey: assigned?.desiredProfileKey },
          resolution: resolve('characterProfiles', profile ?? ''), requiresSkin: true, requiredClips: ['idle', 'walk', 'attack_melee', 'death'],
          notes: [`Dynamic ownership variant: ${realm ?? 'neutral'}.`] });
      }
    }
    for (const keep of config.keeps) for (const realm of ['aegis', 'riftbound'] as const) {
      const id = `${keep.id}_commander`, assigned = rows.find(row => row.entityId === id);
      const profile = campaignNpcProfile({ id, role: 'commander', race: assigned?.race, realm }) ?? campaignNpcProfile({ id, role: 'commander', realm });
      add({ id: `shared_commander:${config.id}:${id}:${realm}`, surface: 'shared_commander', source: 'src/shared/orvr/simulation.ts',
        entityId: id, zoneId: config.id, race: assigned?.race, role: 'commander', requested: { profileKey: assigned?.desiredProfileKey },
        resolution: resolve('characterProfiles', profile ?? ''), requiresSkin: true, requiredClips: ['idle', 'walk', 'attack_melee', 'death'] });
    }
  }
  for (const [kind, key] of Object.entries(SIEGE_ASSET_KEYS)) add({ id: `siege:${kind}`, surface: 'siege', source: 'src/game/network/CampaignSiegePresentation.ts',
    entityId: kind, role: kind, requested: { assetKey: key }, resolution: resolve('staticProps', key),
    requiredClips: kind === 'ram' ? ['siege_roll', 'ram_strike'] : kind === 'oil' ? ['oil_pour'] : ['catapult_fire', 'catapult_reload'] });
  for (const [key, clips] of Object.entries({ frontier_supply_wagon: ['caravan_roll'], frontier_draft_horse: ['idle', 'walk', 'draft_trot'], frontier_caravan_reins: [] })) add({
    id: `caravan:${key}`, surface: 'caravan', source: 'src/game/network/CampaignCaravanPresentation.ts', entityId: key, role: key,
    species: speciesFor(key), requested: { assetKey: key }, resolution: resolve('staticProps', key), requiredClips: clips });
  add({ id: 'caravan:driver', surface: 'caravan', source: 'src/game/network/CampaignCaravanPresentation.ts', entityId: 'driver',
    race: 'empire', bodyVariant: 'm', role: 'driver', requested: { profileKey: CARAVAN_DRIVER_PROFILE },
    resolution: resolve('characterProfiles', CARAVAN_DRIVER_PROFILE), requiresSkin: true, requiredClips: ['driver_seated'],
    packs: [index.staticProps.frontier_supply_wagon?.animationPack].filter((pack): pack is AnimationPack => Boolean(pack)) });

  for (const prefab of WORLD_EDITOR_PREFABS) add({ id: `builder:${prefab.kind}`, surface: 'builder', source: 'src/world/editor/PrefabCatalog.ts',
    entityId: prefab.kind, ...identity(prefab.assetCategory === 'characterProfiles' ? prefab.assetKey : undefined), role: prefab.group ?? prefab.kind,
    requested: { assetKey: prefab.assetKey, category: prefab.assetCategory, model: prefab.model },
    resolution: prefab.assetKey ? resolve(prefab.assetCategory ?? 'staticProps', prefab.assetKey, prefab.model) : { model: prefab.model, method: prefab.model ? 'direct_file' : 'procedural_builder_preview' },
    requiresSkin: prefab.assetCategory === 'characterProfiles', notes: ['Builder placement and preview paths both need authored geometry; live saved placements are not available in this filesystem audit.'] });
  for (const [key, item] of Object.entries(ITEM_CATALOG)) if (item.visual) add({ id: `item:${key}`, surface: 'item', source: 'src/data/items.ts',
    entityId: key, role: item.equipSlot ?? item.kind, requested: { assetKey: key, category: 'equipment', model: item.visual.model },
    resolution: resolve('equipment', key, item.visual.model), notes: ['Includes catalog equipment beyond class starter armor.'] });
  for (const category of ['characterProfiles', 'staticProps', 'equipment'] as const) for (const [key, parent] of Object.entries(index[category])) {
    for (const [variant, nested] of Object.entries(parent.variants ?? { default: parent })) {
      const entry = { ...parent, ...nested, variants: undefined };
      add({ id: `registry:${category}:${key}:${variant}`, surface: 'registry', source: `${MODEL_ROOT}asset-index.json`, entityId: key,
        ...identity(category === 'characterProfiles' ? key : undefined), bodyVariant: entry.bodyVariant, species: speciesFor(key), role: category,
        requested: { assetKey: key, category }, resolution: { category, key, entry, model: entry.model, method: 'registry_inventory' }, requiresSkin: category === 'characterProfiles' });
    }
  }
  // Unreferenced/legacy exports remain in the audit; an asset not used today can still be packaged accidentally.
  for (const model of readdirSync(path.join(root, MODEL_ROOT)).filter(file => file.endsWith('.glb')).sort()) inspect(model);
  assignments.sort((left, right) => left.id.localeCompare(right.id));
  const duplicateIds = assignments.filter((row, position) => position > 0 && row.id === assignments[position - 1].id).map(row => row.id);
  if (duplicateIds.length) throw new Error(`Duplicate assignment IDs: ${duplicateIds.join(', ')}`);
  const bySurface: Record<string, { total: number; blocked: number; candidate: number }> = {};
  for (const row of assignments) { const count = bySurface[row.surface] ??= { total: 0, blocked: 0, candidate: 0 }; count.total++; count[row.status]++; }
  const primitiveAudit = auditPrimitives(root);
  return { schemaVersion: 1, assetVersion: index.assetVersion ?? null,
    summary: { assignmentCount: assignments.length, blocked: assignments.filter(row => row.status === 'blocked').length,
      candidate: assignments.filter(row => row.status === 'candidate').length, ready: 0, packagingReady: false,
      modelFiles: Object.keys(models).length, mapFiles: maps.length, bySurface },
    coverage: { mapFiles: mapFiles.map(file => `public/assets/maps/${file}`), playableProfiles: PLAYABLE_CHARACTER_PROFILES.length,
      sharedZoneConfigs: configs.map(config => config.id), builderDefinitions: WORLD_EDITOR_PREFABS.length,
      generatedInstanceCounts: Object.fromEntries(['generated_path', 'generated_biome'].map(surface => [surface,
        assignments.filter(row => row.surface === surface).reduce((total, row) => total + (row.instanceIds?.length ?? 0), 0)])),
      authoredContractsIncluded: true, hiddenPopulationIncluded: true, dynamicOwnershipVariantsIncluded: true },
    assignments, models: Object.fromEntries(Object.entries(models).sort(([a], [b]) => a.localeCompare(b))), primitiveAudit,
    limitations: ['No Unreal import, visual approval, animation playback, skin deformation or packaged-build test has been performed by this audit.',
      'GLB structure/triangle counts cannot prove that a model is visually nonprimitive. Candidate never means approved.',
      'Browser-local saved characters/world edits and remote database contents are unavailable; future import must apply the same ledger gate to every saved asset reference.',
      'Procedural scatter/path instance IDs are expanded and grouped by model kind; particles, companions and developer geometry are inventoried through source findings and need final visual classification.',
      'Interior template counts mirror HouseInteriorRuntime and are guarded by a source-contract test; update the adapter when resident generation changes.',
      'Use the current checkout root: imported runtime catalogs and resolver functions are the source of truth for this checkout.',
      'Commercial provenance references are evidence to review, not a legal clearance decision.'] };
}

export function strictAssetLedgerExitCode(ledger: Awaited<ReturnType<typeof buildAssetLedger>>): number {
  // Summary fields cannot override unresolved identity or missing import/art evidence on any assignment.
  if (ledger.assignments.some(row => row.blockers.length || row.reviewRequirements.length || row.status === 'candidate' || row.status === 'blocked')) return 1;
  return ledger.summary.packagingReady && ledger.summary.assignmentCount > 0 && ledger.summary.ready === ledger.summary.assignmentCount ? 0 : 1;
}

export async function runAssetLedgerCli(args = process.argv.slice(2)): Promise<number> {
  let output: string | undefined, strict = false;
  for (let index = 0; index < args.length; index++) {
    const argument = args[index];
    if (argument === '--strict') strict = true;
    else if (argument === '--output' && args[index + 1] && !args[index + 1].startsWith('--')) output = args[++index];
    else throw new Error(`Unknown/incomplete argument: ${argument}. Usage: tsx scripts/unreal/asset-ledger.ts [--output artifacts/unreal/asset-ledger.json] [--strict]`);
  }
  const ledger = await buildAssetLedger();
  if (output) { const target = containedPath(ROOT, output); mkdirSync(path.dirname(target), { recursive: true }); writeFileSync(target, JSON.stringify(ledger, null, 2) + '\n'); }
  process.stdout.write(JSON.stringify({ ...ledger.summary, output: output ?? null }) + '\n');
  return strict ? strictAssetLedgerExitCode(ledger) : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  runAssetLedgerCli().then(code => { process.exitCode = code; }).catch(error => { process.stderr.write(`${error instanceof Error ? error.message : error}\n`); process.exitCode = 2; });
}
