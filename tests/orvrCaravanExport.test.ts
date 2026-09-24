import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { Matrix4, Vector3 } from 'three';
// @ts-expect-error Authoring tools are executable ESM inspection modules.
import { readGlb, worldMatrices } from '../authoring/blender/orvr-frontier/tools/inspect_mechanical_glb.mjs';
const root = path.resolve('authoring/blender/orvr-frontier');
const load = (file: string) => readGlb(fs.readFileSync(file));
const staged = (key: string, lod = 0) => load(path.join(root, `runtime/${key}_lod${lod}.glb`));
const poseRecord = () => JSON.parse(fs.readFileSync(path.join(root, 'review/frontier_teamster_animations_build.json'), 'utf8'));
const indexOf = (document: { nodes: Array<{ name: string }> }, name: string) => {
  const index = document.nodes.findIndex(node => node.name === name);
  if (index < 0) throw new Error(`Missing literal exported node ${name}`);
  return index;
};

describe('literal caravan attachment and seated-operator exports', () => {
  it('removes superseded operator animation packs while preserving the body rig', () => {
    expect(fs.existsSync(path.join(root, 'runtime/frontier_teamster_animations.glb'))).toBe(false);
    const body = load('public/assets/models/chr_civic_battle_prelate_t1_m.glb');
    expect(body.document.animations ?? []).toEqual([]);
    expect(body.document.skins).toHaveLength(1);
    expect(body.document.skins[0].joints.length).toBeGreaterThan(50);
  });

  it('aligns both horse tugs with actual wagon shaft sockets and both rein grips across all three LODs', () => {
    const grips = poseRecord().rein_grip_wagon_local_gltf.map((point: number[]) => new Vector3().fromArray(point));
    for (const level of [0, 1, 2]) {
      const wagon = staged('frontier_supply_wagon', level); const horse = staged('frontier_draft_horse', level);
      const reins = staged('frontier_caravan_reins', level);
      const wagonWorld = worldMatrices(wagon.document); const horseWorld = worldMatrices(horse.document); const reinWorld = worldMatrices(reins.document);
      for (const side of ['left', 'right']) {
        const shaft = new Vector3().setFromMatrixPosition(wagonWorld.get(indexOf(wagon.document, `socket.shaft_${side}`)));
        const tug = new Vector3().setFromMatrixPosition(horseWorld.get(indexOf(horse.document, `hitch_shaft_${side}`))).add(new Vector3(0, 0, 3.75));
        expect(shaft.distanceTo(tug)).toBeLessThan(1e-5);
        const hand = new Vector3().setFromMatrixPosition(reinWorld.get(indexOf(reins.document, `socket.driver_hand_${side}`)));
        expect(Math.min(...grips.map((grip: Vector3) => grip.distanceTo(hand)))).toBeLessThan(1e-5);
      }
    }
  });

  it('places the officer belt mount correctly through the actual published hips transform', () => {
    const body = load('public/assets/models/chr_civic_battle_prelate_t1_m.glb');
    const fit = JSON.parse(fs.readFileSync(path.join(root, 'review/frontier_supply_officer_fit.json'), 'utf8'));
    const hips = worldMatrices(body.document).get(indexOf(body.document, fit.bone));
    for (const level of [0, 1, 2]) {
      const kit = staged('frontier_supply_officer_kit', level);
      const socket = worldMatrices(kit.document).get(indexOf(kit.document, 'socket.belt_mount'));
      const mounted = new Matrix4().multiplyMatrices(hips, new Matrix4().fromArray(fit.attachment_matrix_gltf_column_major)).multiply(socket);
      expect(new Vector3().setFromMatrixPosition(mounted).distanceTo(new Vector3().fromArray(fit.rest_mount_avatar_gltf))).toBeLessThan(1e-5);
    }
  });
});
