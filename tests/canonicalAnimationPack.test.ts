import { describe, expect, test } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const contract = JSON.parse(readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/data/body-families/canonical-animation-pack.json',
), 'utf8'));
const mpfbSource = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/blender/canonical_mpfb_animation_library.py',
), 'utf8');
const adapterSource = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/blender/canonical_animation_pack.py',
), 'utf8');
const motionAuditSource = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/blender/audit_canonical_animation_motion.py',
), 'utf8');
const geometryAuditSource = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/tools/compare-glb-geometry.mjs',
), 'utf8');
const assemblySource = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/blender/assemble_runtime_equipped_review.py',
), 'utf8');

const requiredClips = [
  'idle',
  'walk',
  'run',
  'combat_idle',
  'attack_melee',
  'attack_ranged',
  'cast',
  'death',
  'jump',
];

describe('free canonical animation pack', () => {
  test('covers the exact runtime clip contract in deterministic order', () => {
    expect(contract.clips.map((clip: { name: string }) => clip.name)).toEqual(requiredClips);
    expect(new Set(contract.clips.map((clip: { name: string }) => clip.name)).size).toBe(requiredClips.length);
    for (const clip of contract.clips) {
      expect(clip.durationFrames).toBeGreaterThan(0);
      expect(typeof clip.loop).toBe('boolean');
    }
  });

  test('is local, original, zero-cost, and remains review-gated', () => {
    expect(contract.skeletonId).toBe('humanoid_game_v2');
    expect(contract.bindPoseId).toBe('a_pose_v2');
    expect(contract.cost).toBe('free_local_only');
    expect(contract.source.kind).toBe('project_authored_keyframes');
    expect(contract.source.externalAsset).toBe(false);
    expect(contract.lifecycle.status).toBe('draft');
    expect(contract.lifecycle.reviewRequired).toBe(true);
  });

  test('uses MPFB rest-axis locomotion and an explicit hammer profile', () => {
    expect(contract.animationPackId).toBe('humanoid_game_v2_local_keyframes_v2');
    expect(contract.coordinateConversion.rotation).toContain('MPFB bone rest basis');
    expect(mpfbSource).toContain('"battle_prelate_hammer"');
    expect(mpfbSource).toContain('"hand_R"');
    expect(mpfbSource).toContain('BATTLE_PRELATE_HAMMER_OVERRIDES');
    expect(adapterSource).toContain('_armature_space_quaternion');
    expect(adapterSource).toContain('rotation_quaternion');
  });

  test('pose-space audit samples centerlines and a real hammer arc', () => {
    expect(motionAuditSource).toContain('SAMPLE_COUNT = 101');
    expect(motionAuditSource).toContain('"leftFootStaysLeftOfCenterline"');
    expect(motionAuditSource).toContain('"rightFootStaysRightOfCenterline"');
    expect(motionAuditSource).toContain('"substantiveHammerArc"');
    expect(motionAuditSource).toContain('"wristDrivesImpact"');
    expect(motionAuditSource).toContain('"socketGripAttached"');
  });

  test('geometry preservation hashes logical position and index payloads', () => {
    expect(geometryAuditSource).toContain("primitive.attributes.POSITION");
    expect(geometryAuditSource).toContain("primitive.indices");
    expect(geometryAuditSource).toContain("createHash('sha256')");
  });

  test('equipment alignment is profile-driven and resolves a semantic strike axis', () => {
    expect(assemblySource).toContain('EQUIPMENT_ANIMATION_PROFILES');
    expect(assemblySource).toContain('resolve_weapon_strike_axis');
    expect(assemblySource).toContain('weapon_strike_head_marker');
    expect(assemblySource).toContain('farthest_geometry_cluster_from_grip');
    expect(assemblySource).toContain('maxWristDegrees');
  });
});
