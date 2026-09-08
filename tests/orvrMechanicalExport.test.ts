import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
// @ts-expect-error The authoring inspection tool is an executable ESM module.
import { inspectMechanics, readGlb } from '../authoring/blender/orvr-frontier/tools/inspect_mechanical_glb.mjs';

const root = path.resolve('authoring/blender/orvr-frontier');

describe('exported frontier mechanical transforms', () => {
  it('retains four distinct axle pivots and a zero-start wheel action in every wagon LOD', () => {
    const report = JSON.parse(fs.readFileSync(path.join(root, 'review/frontier_supply_wagon_build.json'), 'utf8'));
    for (const level of [0, 1, 2]) {
      const { document } = readGlb(fs.readFileSync(path.join(root, `runtime/frontier_supply_wagon_lod${level}.glb`)));
      const measured = report.lods.find((lod: { level: number }) => lod.level === level);
      expect(inspectMechanics(document, measured)).toEqual([]);
      const pivotTranslations = document.nodes.filter((node: { name: string }) => node.name.startsWith('pivot.wheel_')).map((node: { translation: number[] }) => node.translation);
      expect(pivotTranslations).toHaveLength(4);
      expect(new Set(pivotTranslations.map((translation: number[]) => JSON.stringify(translation))).size).toBe(4);
      for (const translation of pivotTranslations) {
        expect(Math.abs(translation[0])).toBeCloseTo(1.47, 5);
        expect(translation[1]).toBeCloseTo(.79, 5);
        expect(Math.abs(translation[2])).toBeCloseTo(1.15, 5);
      }
      const seat = document.nodes.find((node: { name: string }) => node.name === 'socket.driver_seat');
      expect(seat.translation[1]).toBeCloseTo(1.54, 5);
      expect(seat.translation[2]).toBeCloseTo(1.38, 5);
    }
  });

  it('rejects the wheel-collapse and delayed-NLA regressions found in actual reimport review', () => {
    const report = JSON.parse(fs.readFileSync(path.join(root, 'review/frontier_supply_wagon_build.json'), 'utf8')).lods[0];
    const { document } = readGlb(fs.readFileSync(path.join(root, 'runtime/frontier_supply_wagon_lod0.glb')));
    const collapsed = structuredClone(document);
    for (const node of collapsed.nodes) if (node.name.startsWith('pivot.wheel_')) node.translation = [0, 0, 0];
    expect(inspectMechanics(collapsed, report).filter((issue: string) => issue.includes('world pivot'))).toHaveLength(4);
    const delayed = structuredClone(document);
    for (const sampler of delayed.animations[0].samplers) {
      delayed.accessors[sampler.input].min = [2]; delayed.accessors[sampler.input].max = [3.6];
    }
    expect(inspectMechanics(delayed, report)).toContain('caravan_roll: runtime action must start at zero');
  });
});
