import * as THREE from 'three';
import fs from 'node:fs';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { describe, expect, it } from 'vitest';
import { assembleCampaignSiege, campaignSiegeFacing, SIEGE_WHEEL_CIRCUMFERENCE } from '../src/game/network/CampaignSiegePresentation';

function fixture() {
  const object = new THREE.Group();
  const arm = new THREE.Group(); arm.name = 'arm';
  const wheel = new THREE.Group(); wheel.name = 'wheel'; object.add(arm, wheel);
  const clip = (name: string, duration: number, values: number[], node = 'arm') => new THREE.AnimationClip(name, duration,
    [new THREE.NumberKeyframeTrack(`${node}.position[x]`, [0, duration], values)]);
  const clips = [clip('catapult_fire', .8, [-1.1, .37]), clip('catapult_reload', 3.6, [.37, -1.1]),
    clip('siege_roll', 1.6, [0, 2 * Math.PI], 'wheel'), clip('ram_strike', 1.5, [0, 1]), clip('oil_pour', 3.5, [0, 1])];
  return { object, arm, wheel, clips };
}
const operation = { at: 10, target: { x: 15, y: 0, z: 0 } };

/** Retain literal exported transforms and animation accessors; omit GPU-only payload references. */
async function exportedMechanism(key: string, level: number) {
  const bytes = fs.readFileSync(`public/assets/models/${key}_lod${level}.glb`);
  const jsonLength = bytes.readUInt32LE(12), document = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString());
  for (const node of document.nodes) { delete node.mesh; delete node.skin; }
  for (const key of ['meshes', 'skins', 'materials', 'textures', 'images', 'samplers']) delete document[key];
  const json = Buffer.from(JSON.stringify(document)), length = Math.ceil(json.length / 4) * 4;
  const binaryChunk = bytes.subarray(20 + jsonLength), result = Buffer.alloc(20 + length + binaryChunk.length, 32);
  bytes.copy(result, 0, 0, 20); result.writeUInt32LE(result.length, 8); result.writeUInt32LE(length, 12);
  json.copy(result, 20); binaryChunk.copy(result, 20 + length);
  return new GLTFLoader().parseAsync(result.buffer.slice(result.byteOffset, result.byteOffset + result.byteLength), '');
}

describe('confirmed siege mechanism playback', () => {
  it.each([
    ['ram', 'frontier_battering_ram', 'ram_striker', .7],
    ['oil', 'frontier_oil_cauldron', 'tipping_cauldron', 1.5],
    ['catapult', 'frontier_field_catapult', 'throwing_assembly', .4],
  ] as const)('drives the literal %s export at every LOD and keeps its fixed pivot', async (kind, key, nodeName, phase) => {
    const poses: number[][] = [];
    for (const level of [0, 1, 2]) {
      const loaded = await exportedMechanism(key, level), part = loaded.scene.getObjectByName(nodeName)!;
      expect(part).toBeDefined();
      const pivot = part.parent!, fixed = pivot.matrix.clone();
      const visual = assembleCampaignSiege(loaded.scene, loaded.animations, kind);
      loaded.scene.updateMatrixWorld(true);
      const ready = part.matrix.toArray();
      visual.update(10 + phase, operation, SIEGE_WHEEL_CIRCUMFERENCE / 3);
      loaded.scene.updateMatrixWorld(true);
      expect(part.matrix.toArray()).not.toEqual(ready);
      expect(pivot.matrix.toArray()).toEqual(fixed.toArray());
      poses.push(part.matrix.toArray());
      visual.update(20, operation, SIEGE_WHEEL_CIRCUMFERENCE / 3);
      loaded.scene.updateMatrixWorld(true);
      expect(part.matrix.equals(new THREE.Matrix4().fromArray(ready))).toBe(true);
      visual.mixer.stopAllAction(); visual.mixer.uncacheRoot(loaded.scene);
    }
    for (const pose of poses.slice(1)) pose.forEach((value, index) => expect(value).toBeCloseTo(poses[0][index], 5));
  });
  it('cocks a freshly loaded catapult, fires once, reloads continuously, then holds ready', () => {
    const f = fixture(), visual = assembleCampaignSiege(f.object, f.clips, 'catapult');
    expect(f.arm.position.x).toBeCloseTo(-1.1);
    visual.update(10.4, operation, 0);
    expect(f.arm.position.x).toBeCloseTo((-.73) / 2);
    visual.update(10.8, operation, 0);
    expect(f.arm.position.x).toBeCloseTo(.37);
    visual.update(12.6, operation, 0);
    expect(f.arm.position.x).toBeCloseTo((-.73) / 2);
    visual.update(15, operation, 0);
    expect(f.arm.position.x).toBeCloseTo(-1.1);
    visual.update(20, operation, 0);
    expect(f.arm.position.x).toBeCloseTo(-1.1);
  });

  it('repeated snapshots and a late LOD load show the same current phase', () => {
    const f = fixture(), visual = assembleCampaignSiege(f.object, f.clips, 'catapult');
    visual.update(12, operation, 0);
    const x = f.arm.position.x;
    visual.update(12, structuredClone(operation), 0);
    expect(f.arm.position.x).toBe(x);
    const distant = fixture();
    assembleCampaignSiege(distant.object, distant.clips, 'catapult').update(12, operation, 0);
    expect(distant.arm.position.x).toBe(x);
    visual.update(16.4, { ...operation, at: 16 }, 0);
    expect(f.arm.position.x).toBeCloseTo(-.365);
  });

  it.each(['ram', 'oil'] as const)('%s only moves on confirmed actions, while wheel motion follows distance', kind => {
    const f = fixture(), visual = assembleCampaignSiege(f.object, f.clips, kind);
    visual.update(20, undefined, SIEGE_WHEEL_CIRCUMFERENCE / 4);
    expect(f.arm.position.x).toBe(0);
    expect(f.wheel.position.x).toBeCloseTo(Math.PI / 2);
    const duration = kind === 'ram' ? 1.5 : 3.5;
    visual.update(10 + duration / 2, operation, SIEGE_WHEEL_CIRCUMFERENCE / 4);
    expect(f.arm.position.x).toBeCloseTo(.5);
    visual.update(30, operation, SIEGE_WHEEL_CIRCUMFERENCE / 4);
    expect(f.arm.position.x).toBe(0);
    expect(f.wheel.position.x).toBeCloseTo(Math.PI / 2);
  });

  it('retains an available model when optional clips are unavailable', () => {
    const f = fixture();
    expect(() => assembleCampaignSiege(f.object, [], 'catapult').update(15, operation, 5)).not.toThrow();
    expect(f.object.children).toHaveLength(2);
  });

  it('aims mobile equipment at the confirmed target without turning a wall-mounted cauldron', () => {
    const keep = { position: { x: 0, y: 0, z: 0 }, outerGate: { x: 0, y: 0, z: -10 } };
    const machine = { kind: 'catapult' as const, position: { x: 0, y: 0, z: 0 }, lastOperation: operation };
    expect(campaignSiegeFacing(machine)).toBeCloseTo(Math.PI / 2);
    expect(campaignSiegeFacing({ ...machine, kind: 'oil' }, keep)).toBeCloseTo(Math.PI);
  });
});
