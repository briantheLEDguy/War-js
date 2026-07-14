import { describe, expect, test } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const generator = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/blender/generate_mpfb_body.py',
), 'utf8');
const roundtripAudit = readFileSync(path.join(
  root,
  'scripts/blender-character-pipeline/blender/glb_roundtrip_audit.py',
), 'utf8');

describe('MPFB body authoring/runtime boundary', () => {
  test('saves stable authoring topology before runtime-only helper stripping', () => {
    const save = generator.indexOf('bpy.ops.wm.save_as_mainfile');
    const strip = generator.indexOf('helper_stripping = bake_targets_and_strip_helpers');
    expect(save).toBeGreaterThan(-1);
    expect(strip).toBeGreaterThan(save);
    expect(generator).toContain('helperVerticesRemoved');
    expect(generator).toContain('shapeKeysBaked');
    expect(generator).toContain('MPFB_AUTHORING_BODY_VERTICES = 19_158');
    expect(generator).toContain('"authoringTopologyStable"');
  });

  test('makes imported bind geometry and opaque materials part of QC', () => {
    expect(generator).toContain('"roundTripBindPose": roundtrip_audit["passed"]');
    expect(generator).toContain('"runtimeBodyMaterialsOpaque"');
    expect(generator).toContain('"groomingFixturesPresent"');
    for (const invariant of [
      'meshCountMatches',
      'allMeshesRemainSkinned',
      'triangleCountMatches',
      'boneCountMatches',
      'bindBoundsMatch',
    ]) {
      expect(roundtripAudit).toContain(`"${invariant}"`);
    }
  });

  test('creates sockets from the canonical skeleton contract, including rotations', () => {
    expect(generator).toContain('SKELETON_CONTRACT_PATH');
    expect(generator).toContain('definition["rotationDegrees"]');
    expect(generator).toContain('empty.rotation_euler');
  });
});
