import { mkdirSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import path from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import {
  compileRosterSpec,
  validateRosterSpec,
} from '../scripts/blender-character-pipeline/tools/roster-spec.mjs';
import {
  createRevisionManifest,
} from '../scripts/blender-character-pipeline/tools/roster-runs.mjs';
import {
  animationProfileForGroup,
  technicalQcPassed,
} from '../scripts/blender-character-pipeline/tools/roster-generation.mjs';
import {
  buildPlayableArmorRecipe,
  FIXTURE_PACK_CONTRACT,
  playableFixtureSignature,
} from '../scripts/blender-character-pipeline/tools/roster-recipes.mjs';

const scratch = path.resolve('artifacts', 'model-jobs', `vitest-roster-spec-${randomUUID()}`);

afterAll(() => rmSync(scratch, { recursive: true, force: true }));

describe('full playable, NPC, and creature roster contract', () => {
  const spec = compileRosterSpec();

  it('declares the exact 48 resumable generation groups', () => {
    expect(validateRosterSpec(spec)).toEqual([]);
    expect(spec.counts).toEqual({
      generationGroups: 48,
      playableGroups: 24,
      playableAppearances: 48,
      armorModules: 432,
      npcFoundations: 12,
      liveNpcProfiles: 106,
      creatureSpecies: 12,
    });
  });

  it('gives every class/body appearance nine unique modules and all weapon modes', () => {
    const playable = spec.groups.filter((group) => group.kind === 'playable');
    const moduleIds = playable.flatMap((group) => group.variants.flatMap((variant) => (
      variant.armorModules.map((module) => module.assetId)
    )));
    expect(new Set(moduleIds).size).toBe(432);
    for (const group of playable) {
      expect(group.variants.map((variant) => variant.variant)).toEqual(['m', 'f']);
      expect(group.variants.every((variant) => variant.armorModules.length === 9)).toBe(true);
      expect(group.weaponHandlingModes).toEqual(['one_handed', 'two_handed', 'dual_wield']);
    }
    const physiques = playable.flatMap((group) => group.variants.map((variant) => (
      JSON.stringify(variant.physique.propertyValues)
    )));
    expect(new Set(physiques).size).toBe(48);
    expect(new Set(playable.map((group) => group.futureAnimationPackId)).size).toBe(24);
    expect(playable.every((group) => group.futureAnimationClips.length === 9)).toBe(true);
  });

  it('uses distinct open-face authored fixture recipes for all 24 classes', () => {
    const playable = spec.groups.filter((group) => group.kind === 'playable');
    const signatures = playable.map((group) => playableFixtureSignature(group));
    expect(new Set(signatures).size).toBe(24);
    for (const group of playable) {
      const recipe = buildPlayableArmorRecipe(group, 1).sets[group.key];
      const modules = Object.values(recipe.modules) as any[];
      expect(modules).toHaveLength(9);
      expect(modules.filter((module) => ['mpfbAsset', 'mpfbSegment'].includes(module.kind)).length)
        .toBeGreaterThanOrEqual(5);
      expect(recipe.modules.head.faceCoverage).toBe('open');
      expect(recipe.modules.head.faceOcclusionAllowed).toBe(false);
      expect(modules.map((module) => module.asset).filter(Boolean)).not.toContain('culturalibre_skull_helmet');
    }
    expect(FIXTURE_PACK_CONTRACT).toEqual([
      'makehuman_system_assets', 'skins03', 'ears01', 'hands01', 'nose01',
      'cheek01', 'faceunits01', 'suits02', 'hats02', 'gloves01', 'equipment01',
    ]);
  });

  it('requires every race body to exercise all anatomical packs and real grooming geometry', () => {
    const policy = JSON.parse(readFileSync(
      path.resolve('scripts', 'blender-character-pipeline', 'data', 'full-roster-policy.json'),
      'utf8',
    ));
    const required = new Set(['ears01', 'hands01', 'nose01', 'cheek01', 'faceunits01']);
    for (const identity of Object.values(policy.raceIdentity) as any[]) {
      expect(new Set(identity.fixtureTargets.map((target: any) => target.pack))).toEqual(required);
      expect(identity.grooming.m).toEqual(expect.objectContaining({
        hair: expect.any(String), eyebrows: expect.any(String), eyelashes: expect.any(String),
      }));
      expect(identity.grooming.f).toEqual(expect.objectContaining({
        hair: expect.any(String), eyebrows: expect.any(String), eyelashes: expect.any(String),
      }));
    }
    const bodyGenerator = readFileSync(
      path.resolve('scripts', 'blender-character-pipeline', 'blender', 'generate_mpfb_body.py'),
      'utf8',
    );
    expect(bodyGenerator).toContain('def add_grooming(');
    expect(bodyGenerator).toContain('obj["bodyAccessory"] = True');
  });

  it('builds weapons and creatures without Blender primitive operators', () => {
    const weaponGenerator = readFileSync(
      path.resolve('scripts', 'blender-character-pipeline', 'blender', 'generate_mpfb_weapon_suite.py'),
      'utf8',
    );
    const creatureGenerator = readFileSync(
      path.resolve('scripts', 'blender-character-pipeline', 'blender', 'generate_roster_creature.py'),
      'utf8',
    );
    expect(weaponGenerator).toContain('equipment01');
    expect(weaponGenerator).toContain('authoredEquipmentFixtures');
    expect(weaponGenerator).not.toMatch(/bpy\.ops\.mesh\.primitive_/u);
    expect(creatureGenerator).not.toMatch(/bpy\.ops\.mesh\.primitive_/u);
    expect(creatureGenerator).toContain('primitiveOperatorsUsed');
  });

  it('maps all 106 humanoid profiles through 12 race/body foundations and 17 realm roles', () => {
    const foundations = spec.groups.filter((group) => group.kind === 'npc');
    const profiles = foundations.flatMap((group) => group.liveProfiles);
    expect(new Set(foundations.map((group) => `${group.race}:${group.bodyVariant}`)).size).toBe(12);
    expect(profiles.filter((profile) => profile.source === 'static_npc')).toHaveLength(74);
    expect(profiles.filter((profile) => profile.source === 'enemy')).toHaveLength(32);
    expect(new Set(profiles.map((profile) => `${profile.realm}:${profile.role}`)).size).toBe(17);
  });

  it('declares rig/contact contracts for all twelve realm-aligned species', () => {
    const creatures = spec.groups.filter((group) => group.kind === 'creature');
    expect(creatures.filter((group) => group.realm === 'aegis')).toHaveLength(6);
    expect(creatures.filter((group) => group.realm === 'riftbound')).toHaveLength(6);
    expect(new Set(creatures.map((group) => group.futureAnimationPackId)).size).toBe(12);
    for (const creature of creatures) {
      expect(creature.skeletonId).toMatch(/^creature_[a-z_]+_v1$/u);
      expect(creature.requiredMarkers).toEqual(['root', 'ground_contact', 'attack_origin', 'hit_center']);
      expect(creature).not.toHaveProperty('weaponHandlingModes');
    }
  });

  it('uses deterministic, revision-varying seeds', () => {
    mkdirSync(scratch, { recursive: true });
    const group = spec.groups.find((candidate) => candidate.kind === 'creature');
    expect(group).toBeTruthy();
    const first = createRevisionManifest({ runId: 'seed-test', group, revision: 1, root: path.join(scratch, 'a') });
    const repeated = createRevisionManifest({ runId: 'seed-test', group, revision: 1, root: path.join(scratch, 'b') });
    const next = createRevisionManifest({ runId: 'seed-test', group, revision: 2, root: path.join(scratch, 'b') });
    expect(first.revisionSeed).toBe(repeated.revisionSeed);
    expect(next.revisionSeed).not.toBe(first.revisionSeed);
  });

  it('loads MPFB explicitly for background body and armor generation', () => {
    const source = readFileSync(
      path.resolve('scripts', 'blender-character-pipeline', 'tools', 'roster-generation.mjs'),
      'utf8',
    );
    expect(source).toContain('["--background", "--addons", "bl_ext.blender_org.mpfb"]');
    expect(source).toContain('], { mpfb: true }), { signal, onOutput });');
    expect(source).toContain('includes("Traceback (most recent call last):")');
    expect(source).toContain('"--animation-profile", animationProfileForGroup(group)');
    expect(animationProfileForGroup({ key: 'warbrute' })).toBe('unarmed');
  });

  it('keeps pending human approval separate from completed technical QC', () => {
    expect(technicalQcPassed({ qcPassed: true })).toBe(true);
    expect(technicalQcPassed({ qcPassed: false })).toBe(false);
    expect(technicalQcPassed({
      technicalRoundTripPassed: true,
      visualApprovalPassed: false,
      invalidBounds: [],
      blockingReasons: [
        'human_roundtrip_visual_approval_missing',
        'stress_pose_review_missing',
      ],
    })).toBe(true);
    expect(technicalQcPassed({
      technicalRoundTripPassed: true,
      invalidBounds: ['body'],
    })).toBe(false);
  });
});

describe('canonical creature placement redistribution', () => {
  it('preserves every generated beast coordinate/level while using all twelve realm species', () => {
    const maps = readdirSync(path.resolve('public', 'assets', 'maps'))
      .filter((file) => file.endsWith('.json') && file !== 'zone1.json')
      .map((file) => JSON.parse(readFileSync(path.resolve('public', 'assets', 'maps', file), 'utf8')));
    const placements = maps.flatMap((zone) => (zone.enemies ?? [])
      .filter((enemy: { assetKey?: string }) => enemy.assetKey?.startsWith('creature_'))
      .map((enemy: { id: string; assetKey: string; level: number; x: number; z: number }) => ({
        zone: zone.id,
        realm: zone.campaign.realm,
        id: enemy.id,
        assetKey: enemy.assetKey,
        level: enemy.level,
        x: enemy.x,
        z: enemy.z,
      })));
    const aegis = new Set([
      'creature_barrow_wolf', 'creature_war_boar', 'creature_wild_stag',
      'creature_suncrest_ram', 'creature_briarback_bear', 'creature_glassriver_snapper',
    ]);
    const riftbound = new Set([
      'creature_ash_hound', 'creature_mire_hound', 'creature_rift_hound',
      'creature_lair_spider', 'creature_cinderhide_drake', 'creature_rotmaw_toad',
    ]);
    expect(placements).toHaveLength(60);
    expect(new Set(placements.map((row) => row.assetKey))).toEqual(new Set([...aegis, ...riftbound]));
    expect(placements.every((row) => (row.realm === 'aegis' ? aegis : riftbound).has(row.assetKey))).toBe(true);
    const placementIdentity = placements
      .map(({ zone, id, level, x, z }) => `${zone}:${id}:${level}:${x}:${z}`)
      .sort()
      .join('\n');
    expect(createHash('sha256').update(placementIdentity).digest('hex')).toBe(
      '645e5d32de5e0c6739ab3b969588f2d2fa6243f1ad7c122ec1b9ce4adbb93c85',
    );
  });
});
