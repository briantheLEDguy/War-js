import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { Vector3 } from 'three';
// @ts-expect-error Authoring inspection tools are executable ESM modules.
import { readGlb } from '../authoring/blender/orvr-frontier/tools/inspect_mechanical_glb.mjs';
// @ts-expect-error Authoring inspection tools are executable ESM modules.
import { accessorValues, animatedWorldMatrices } from '../authoring/blender/orvr-frontier/tools/inspect_skinned_glb.mjs';

const root = path.resolve('authoring/blender/orvr-frontier');

describe('actual draft-horse runtime export', () => {
  it('retains the complete skinned coat and harness, normalized influences and three named actions in every LOD', () => {
    const report = JSON.parse(fs.readFileSync(path.join(root, 'review/frontier_draft_horse_build.json'), 'utf8'));
    expect(report.lods.map((lod: { level: number }) => lod.level)).toEqual([0, 1, 2]);
    const counts = [];
    for (const level of [0, 1, 2]) {
      const { document, binary } = readGlb(fs.readFileSync(path.join(root, `runtime/frontier_draft_horse_lod${level}.glb`)));
      expect(document.nodes.filter((node: { mesh?: number }) => node.mesh !== undefined).map((node: { name: string }) => node.name).sort())
        .toEqual(['frontier_draft_horse_coat', 'frontier_draft_horse_tack']);
      expect(document.animations.map((clip: { name: string }) => clip.name).sort()).toEqual(['draft_trot', 'idle', 'walk']);
      expect(document.skins).toHaveLength(1);
      const skeleton = document.skins[0];
      for (const mesh of document.meshes) for (const primitive of mesh.primitives) {
        const weights: number[][] = accessorValues(document, binary, primitive.attributes.WEIGHTS_0);
        const joints: number[][] = accessorValues(document, binary, primitive.attributes.JOINTS_0);
        expect(weights.length).toBe(joints.length);
        expect(primitive.attributes.WEIGHTS_1).toBeUndefined();
        let normalizationError = 0; let invalidWeights = 0; let invalidJoints = 0;
        for (let i = 0; i < weights.length; i++) {
          normalizationError = Math.max(normalizationError, Math.abs(weights[i].reduce((a, b) => a + b, 0) - 1));
          if (!weights[i].every(weight => weight >= 0 && weight <= 1)) invalidWeights++;
          if (!joints[i].every(joint => joint >= 0 && joint < skeleton.joints.length)) invalidJoints++;
        }
        expect(normalizationError).toBeLessThan(1e-5); expect(invalidWeights).toBe(0); expect(invalidJoints).toBe(0);
      }
      counts.push(report.lods[level].triangles);
    }
    expect(counts[0]).toBeGreaterThan(counts[1]); expect(counts[1]).toBeGreaterThan(counts[2]);
  });

  it('plants the exported forefoot against 3.5 m/s authoritative forward motion without moving the root', () => {
    const { document, binary } = readGlb(fs.readFileSync(path.join(root, 'runtime/frontier_draft_horse_lod0.glb')));
    const foot = document.nodes.findIndex((node: { name: string }) => node.name === 'hoof_front_L');
    const rootNode = document.nodes.findIndex((node: { name: string }) => node.name === 'root');
    expect(foot).toBeGreaterThanOrEqual(0); expect(rootNode).toBeGreaterThanOrEqual(0);
    const positions = [0, 1/30, 2/30, 3/30, 4/30, 5/30, 6/30].map(seconds => {
      const matrices = animatedWorldMatrices(document, binary, 'draft_trot', seconds);
      expect(new Vector3().setFromMatrixPosition(matrices.get(rootNode)).length()).toBeLessThan(1e-5);
      const position = new Vector3().setFromMatrixPosition(matrices.get(foot));
      position.z += 3.5 * seconds;
      return position;
    });
    for (const position of positions.slice(1)) expect(position.distanceTo(positions[0])).toBeLessThan(.001);
    // Quaternion interpolation adds a measured 6.12 mm peak at the first
    // midpoint; the contact budget is 1 cm, including between authored keys.
    for (const seconds of [.5/30, 1.5/30, 2.5/30, 3.5/30, 4.5/30, 5.5/30]) {
      const matrix = animatedWorldMatrices(document, binary, 'draft_trot', seconds).get(foot);
      const point = new Vector3().setFromMatrixPosition(matrix); point.z += 3.5 * seconds;
      expect(point.distanceTo(positions[0])).toBeLessThan(.01);
    }
  });
});
