import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, readdirSync, rmdirSync, unlinkSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { beforeAll, describe, expect, test } from 'vitest';
import { buildAssetLedger, runAssetLedgerCli, strictAssetLedgerExitCode } from '../scripts/unreal/asset-ledger';
import { containedPath, inspectGlb } from '../scripts/unreal/asset-evidence';
import { classifyPrimitive } from '../scripts/unreal/primitive-audit';
import { PLAYABLE_CHARACTER_PROFILES } from '../shared/data/playableAssets.generated';
import { WORLD_EDITOR_PREFABS } from '../shared/world/editor/PrefabCatalog';
import { applyBiomeKits } from '../shared/world/BiomeKit';
import { applyZonePaths } from '../shared/world/PathKit';

const root = process.cwd();
type Ledger = Awaited<ReturnType<typeof buildAssetLedger>>;
let ledger: Ledger;
beforeAll(async () => { ledger = await buildAssetLedger(root); }, 120_000);

describe('Unreal asset assignment coverage', () => {
  test('visual rejection overrides polygon counts and browser registry approval', () => {
    for (const profile of ['civic_battle_prelate_m', 'civic_ember_arcanist_m']) {
      const row = ledger.assignments.find(item => item.id === `playable:${profile}`)!;
      expect(row.status).toBe('blocked');
      expect(row.blockers).toContain('visual_source_rejected:segmented_placeholder_body');
      expect(ledger.assignments.some(item => item.candidates.some(candidate => candidate.profileKey === profile))).toBe(false);
    }
  });
  test('enumerates every map NPC, enemy, ambient actor, and visible prop including the dev map', () => {
    const files = readdirSync(path.join(root, 'public/assets/maps')).filter(file => file.endsWith('.json')).sort();
    expect(ledger.coverage.mapFiles).toEqual(files.map(file => `public/assets/maps/${file}`));
    expect(ledger.coverage.mapFiles).toContain('public/assets/maps/zone1.json');
    const expected = { local_npc: 0, local_enemy: 0, ambient: 0, world_prop: 0 };
    for (const file of files) {
      const zone = JSON.parse(readFileSync(path.join(root, 'public/assets/maps', file), 'utf8'));
      expected.local_npc += zone.npcs?.length ?? 0;
      expected.local_enemy += zone.enemies?.length ?? 0;
      expected.ambient += zone.ambientLife?.actors?.length ?? 0;
      expected.world_prop += (zone.props ?? []).filter((prop: { visible?: boolean }) => prop.visible !== false).length;
    }
    for (const [surface, count] of Object.entries(expected)) expect(ledger.summary.bySurface[surface].total, surface).toBe(count);
    expect(new Set(ledger.assignments.map(row => row.id)).size).toBe(ledger.assignments.length);
  });

  test('preserves all 48 playable variants, their previews, armor slots, and the complete builder catalog', () => {
    expect(PLAYABLE_CHARACTER_PROFILES).toHaveLength(48);
    for (const profile of PLAYABLE_CHARACTER_PROFILES) {
      for (const surface of ['playable', 'character_preview']) {
        const row = ledger.assignments.find(item => item.id === `${surface}:${profile.profileKey}`)!;
        expect(row).toMatchObject({ race: profile.race, bodyVariant: profile.bodyVariant, className: profile.className,
          requested: { profileKey: profile.profileKey } });
      }
      for (const armor of Object.values(profile.armor)) expect(ledger.assignments.some(row => row.id === `playable_equipment:${profile.profileKey}:${armor.slot}`)).toBe(true);
    }
    expect(ledger.summary.bySurface.builder.total).toBe(WORLD_EDITOR_PREFABS.length);
    expect(ledger.assignments.filter(row => row.surface === 'builder').some(row => row.requested.category === 'characterProfiles')).toBe(true);
    expect(ledger.assignments.filter(row => row.surface === 'builder').some(row => row.requested.category === 'staticProps')).toBe(true);
  });

  test('expands procedural scatter and paths without classifying terrain engineering as a missing model', () => {
    let pathInstances = 0, biomeInstances = 0;
    for (const source of ledger.coverage.mapFiles) {
      const zone = JSON.parse(readFileSync(path.join(root, source), 'utf8'));
      const paths = applyZonePaths(zone), biomes = applyBiomeKits(paths);
      pathInstances += paths.props.length - zone.props.length;
      biomeInstances += biomes.props.length - paths.props.length;
    }
    expect(ledger.coverage.generatedInstanceCounts).toEqual({ generated_path: pathInstances, generated_biome: biomeInstances });
    expect(pathInstances).toBeGreaterThan(0);
    expect(biomeInstances).toBeGreaterThan(0);
    for (const row of ledger.assignments.filter(row => row.surface === 'generated_path' || row.surface === 'terrain')) {
      expect(row.blockers).not.toContain('no_model_assignment');
      expect(row.blockers).not.toContain('model_file_missing');
    }
    expect(ledger.assignments.some(row => row.surface === 'preview_environment' && row.requested.model === 'banner_post.glb')).toBe(true);
    expect(ledger.summary.bySurface.preview_geometry.total).toBe(6);
  });

  test('flags semantic dummy substitutions despite the referenced GLB existing', () => {
    const wrong = ledger.assignments.filter(row => row.blockers.includes('semantic_training_dummy_substitution'));
    expect(wrong.length).toBeGreaterThan(0);
    expect(wrong.some(row => row.species === 'war_boar')).toBe(true);
    expect(wrong.some(row => row.requested.profileKey === 'enemy_aegis_battlefield_hexer_caster')).toBe(true);
    for (const row of wrong) {
      expect(row.status).toBe('blocked');
      expect(ledger.models[row.modelEvidence!].exists).toBe(true);
      expect(row.resolved.modelPath).toBe('public/assets/models/prop_training_dummy_t1.glb');
    }
  });

  test('covers network ownership changes, caravan assembly, siege seats, and generated residents', () => {
    expect(ledger.summary.bySurface.shared_player.total).toBe(2);
    expect(ledger.summary.bySurface.shared_guard.total).toBeGreaterThan(0);
    expect(ledger.assignments.some(row => row.surface === 'shared_guard' && row.id.endsWith(':neutral'))).toBe(true);
    for (const id of ['caravan:driver', 'caravan:frontier_draft_horse', 'caravan:frontier_caravan_reins', 'caravan:frontier_supply_wagon',
      'siege:ram', 'siege:oil', 'siege:catapult', 'siege_crew:aegis:ram:left', 'siege_crew:riftbound:ram:right']) {
      expect(ledger.assignments.find(row => row.id === id), id).toBeDefined();
    }
    expect(ledger.assignments.find(row => row.id === 'caravan:driver')?.blockers).toContain('animation_missing:driver_seated');
    expect(ledger.assignments.find(row => row.id === 'caravan:frontier_supply_wagon')?.blockers).not.toContain('animation_pack_invalid_or_incompatible');
    expect(ledger.assignments.find(row => row.id === 'siege_crew:riftbound:ram:right')?.blockers).toContain('ram_operator_rig_not_supported_by_current_runtime');
    const source = readBrowserReference('src/game/HouseInteriorRuntime.ts');
    const residentFunction = source.slice(source.indexOf('function addOccupants('), source.indexOf('function addHearth('));
    expect([...residentFunction.matchAll(/\{ name: '/g)]).toHaveLength(5);
    expect(ledger.summary.bySurface.interior.total).toBe(18);
    expect(ledger.assignments.find(row => row.id === 'interior:default:small:1')?.resolved.method).toBe('procedural_resident');
  });

  test('offers existing adaptations without approving missing identities or allowing a package', () => {
    const dwarf = ledger.assignments.find(row => row.id === 'playable:stone_stoneguard_f')!;
    expect(dwarf.status).toBe('blocked');
    expect(dwarf.candidates.some(candidate => candidate.profileKey === 'npc_frontier_sunmeadow_dwarf_artisan')).toBe(true);
    expect(dwarf.candidates.every(candidate => candidate.status === 'adaptation_candidate_not_approved')).toBe(true);
    expect(dwarf.candidates.some(candidate => candidate.work.includes('body_variant_adaptation_required'))).toBe(true);
    expect(ledger.assignments.find(row => row.id === 'playable:mire_warbrute_m')?.blockers).toContain('animation_missing:idle');
    expect(ledger.assignments.every(row => row.reviewRequirements.includes('unreal_import_and_cook_unverified'))).toBe(true);
    expect(ledger.summary.ready).toBe(0);
    expect(ledger.summary.packagingReady).toBe(false);
    expect(strictAssetLedgerExitCode(ledger)).toBe(1);
    expect(strictAssetLedgerExitCode({ ...ledger, summary: { ...ledger.summary, packagingReady: true, ready: ledger.assignments.length } })).toBe(1);
  });

  test('produces the same report from unchanged inputs without timestamps or absolute roots', async () => {
    const again = await buildAssetLedger(root);
    const digest = (value: Ledger) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
    expect(digest(again)).toBe(digest(ledger));
    expect(JSON.stringify(ledger)).not.toContain(root.replaceAll('\\', '/'));
  }, 120_000);
});

describe('binary evidence and primitive classification', () => {
  test('reads preserved model data and verifies retired embedded clips and packs are absent', () => {
    const body = ledger.models['public/assets/models/chr_civic_battle_prelate_t1_m.glb'];
    expect(body).toMatchObject({ exists: true, valid: true, skins: 1, joints: [56] });
    expect(body.triangles).toBeGreaterThan(30_000);
    expect(body.clips).toEqual([]);
    expect(inspectGlb(root, 'public/assets/models/anim_battle_prelate_combat.glb').exists).toBe(false);
  });

  test('rejects missing, corrupt, truncated, and out-of-root evidence paths', () => {
    const directory = mkdtempSync(path.join(os.tmpdir(), 'war-unreal-glb-audit-'));
    const filename = path.join(directory, 'broken.glb');
    try {
      expect(inspectGlb(directory, 'missing.glb')).toMatchObject({ exists: false, valid: false, errors: ['file_missing'] });
      writeFileSync(filename, Buffer.from('not a GLB'));
      expect(inspectGlb(directory, 'broken.glb').errors).toContain('invalid_glb_header');
      const header = readFileSync(path.join(root, 'public/assets/models/chr_civic_battle_prelate_t1_m.glb')).subarray(0, 20);
      writeFileSync(filename, header);
      expect(inspectGlb(directory, 'broken.glb').valid).toBe(false);
      expect(() => containedPath(directory, '../escape.glb')).toThrow('escapes');
      expect(inspectGlb(directory, '../escape.glb').valid).toBe(false);
    } finally { unlinkSync(filename); rmdirSync(directory); }
  });

  test('distinguishes visible placeholders from effects/collision/editor and authoring geometry', () => {
    expect(classifyPrimitive('src/game/CharacterMeshes.ts', 'new THREE.BoxGeometry(1, 1, 1)')).toBe('visible_model_or_fallback');
    expect(classifyPrimitive('src/world/editor/WorldEditorRuntime.ts', 'AssetLoader.primitives.humanoid()')).toBe('visible_model_or_fallback');
    expect(classifyPrimitive('src/game/abilities/AbilityVfx.ts', 'new THREE.SphereGeometry(1)')).toBe('technical_geometry');
    expect(classifyPrimitive('src/world/editor/WorldEditorRuntime.ts', 'new THREE.BoxGeometry(1, 1, 1)')).toBe('technical_geometry');
    expect(classifyPrimitive('authoring/blender/character/build.py', 'bpy.ops.mesh.primitive_uv_sphere_add()')).toBe('authoring_geometry_review');
    expect(ledger.primitiveAudit.findings.some(row => row.path.startsWith('src/'))).toBe(false);
    expect(ledger.primitiveAudit.findings.every(row => !row.action.includes('delete'))).toBe(true);
  });

  test('rejects incomplete and unknown CLI options before scanning assets', async () => {
    await expect(runAssetLedgerCli(['--output'])).rejects.toThrow('Unknown/incomplete argument');
    await expect(runAssetLedgerCli(['--allow-primitives'])).rejects.toThrow('Unknown/incomplete argument');
  });
});
import { readBrowserReference } from '../scripts/unreal/browser-reference';
