import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { Matrix4, Vector3 } from 'three';
// @ts-expect-error Authoring tools are executable ESM inspection modules.
import { readGlb, worldMatrices } from '../authoring/blender/orvr-frontier/tools/inspect_mechanical_glb.mjs';
// @ts-expect-error Authoring tools are executable ESM inspection modules.
import { accessorValues, animatedWorldMatrices } from '../authoring/blender/orvr-frontier/tools/inspect_skinned_glb.mjs';

const root = path.resolve('authoring/blender/orvr-frontier');
const load = (file: string) => readGlb(fs.readFileSync(file));
const staged = (key: string, lod = 0) => load(path.join(root, `runtime/${key}_lod${lod}.glb`));
const driver = () => load(path.join(root, 'runtime/frontier_teamster_animations.glb'));
const poseRecord = () => JSON.parse(fs.readFileSync(path.join(root, 'review/frontier_teamster_animations_build.json'), 'utf8'));
const indexOf = (document: { nodes: Array<{ name: string }> }, name: string) => {
  const index = document.nodes.findIndex(node => node.name === name);
  if (index < 0) throw new Error(`Missing literal exported node ${name}`);
  return index;
};

describe('literal caravan attachment and seated-operator exports', () => {
  it('preserves the published humanoid rest skeleton and keeps the seated action in place', () => {
    const { document, binary } = driver();
    const body = load('public/assets/models/chr_civic_battle_prelate_t1_m.glb');
    const rest = worldMatrices(document); const bodyRest = worldMatrices(body.document);
    expect(document.meshes ?? []).toHaveLength(0);
    expect(document.animations.map((clip: { name: string }) => clip.name)).toEqual(['driver_seated']);
    const animatedNodes = new Set<number>(document.animations[0].channels.map((channel: { target: { node: number } }) => channel.target.node));
    expect(animatedNodes.size).toBeGreaterThan(50);
    for (const index of animatedNodes) {
      const match = indexOf(body.document, document.nodes[index].name);
      expect(rest.get(index).elements.every((value: number, axis: number) => Math.abs(value - bodyRest.get(match).elements[axis]) < 1e-5)).toBe(true);
    }
    for (const seconds of [0, .5, 2, 4]) {
      const matrices = animatedWorldMatrices(document, binary, 'driver_seated', seconds);
      expect(new Vector3().setFromMatrixPosition(matrices.get(indexOf(document, 'root')))
        .distanceTo(new Vector3().setFromMatrixPosition(rest.get(indexOf(document, 'root'))))).toBeLessThan(1e-5);
      expect(new Vector3().setFromMatrixPosition(matrices.get(indexOf(document, 'hips')))
        .distanceTo(new Vector3().setFromMatrixPosition(rest.get(indexOf(document, 'hips'))))).toBeLessThan(1e-5);
    }
  });

  it('fits literal published boot soles to the authored footboard after applying the exported pose', () => {
    const { document, binary } = driver();
    const boots = load('public/assets/models/arm_civic_battle_prelate_feet_novitiate_m.glb');
    const pose = animatedWorldMatrices(document, binary, 'driver_seated', 0);
    const origin = new Vector3().fromArray(poseRecord().avatar_origin_wagon_local_gltf);
    const points: Vector3[] = [];
    for (const node of boots.document.nodes) {
      if (node.mesh === undefined || node.skin === undefined) continue;
      const skin = boots.document.skins[node.skin];
      const inverseBind: number[][] = accessorValues(boots.document, boots.binary, skin.inverseBindMatrices);
      const joints: Matrix4[] = skin.joints.map((joint: number, index: number) => new Matrix4().multiplyMatrices(
        pose.get(indexOf(document, boots.document.nodes[joint].name)), new Matrix4().fromArray(inverseBind[index]),
      ));
      for (const primitive of boots.document.meshes[node.mesh].primitives) {
        const positions: number[][] = accessorValues(boots.document, boots.binary, primitive.attributes.POSITION);
        const weights: number[][] = accessorValues(boots.document, boots.binary, primitive.attributes.WEIGHTS_0);
        const indices: number[][] = accessorValues(boots.document, boots.binary, primitive.attributes.JOINTS_0);
        for (let i = 0; i < positions.length; i++) {
          const point = new Vector3();
          for (let j = 0; j < 4; j++) point.addScaledVector(new Vector3().fromArray(positions[i]).applyMatrix4(joints[indices[i][j]]), weights[i][j]);
          points.push(point.add(origin));
        }
      }
    }
    expect(points.length).toBeGreaterThan(1000);
    for (const sign of [-1, 1]) {
      const sole = points.filter(point => point.x * sign > 0).sort((a, b) => a.y - b.y)[0];
      expect(Math.abs(sole.y - 1.16)).toBeLessThan(.012);
      expect(sole.z).toBeGreaterThan(1.65); expect(sole.z).toBeLessThan(2.2);
      expect(Math.abs(sole.x)).toBeLessThan(.38);
    }
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
