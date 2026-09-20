import fs from 'node:fs';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { describe, expect, it } from 'vitest';
import { assembleCampaignSiegeCrew, compatibleRamCrew, createCampaignSiegeCrew } from '../src/game/network/CampaignSiegeCrewPresentation';
import { campaignSiegeFacing, SIEGE_WHEEL_CIRCUMFERENCE } from '../src/game/network/CampaignSiegePresentation';

const compatible = { model: 'body.glb', bodyFamily: 'civic_battle_prelate_m', bodyVariant: 'm', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2' };
function fixture() {
  const root = new THREE.Group(), hand = new THREE.Bone(); hand.name = 'hand_L'; root.add(hand);
  const weapon = new THREE.Group(); weapon.userData.equipmentSlot = 'mainHand'; hand.add(weapon);
  const clips = (side: number) => ['ram_crew_idle', 'ram_crew_drive', 'ram_crew_strike'].map((name, index) => new THREE.AnimationClip(name, [4, 1.6, 1.5][index], [
    new THREE.NumberKeyframeTrack('hand_L.position[x]', [0, [4, 1.6, 1.5][index]], [side * 10, side * 10 + index + 1]),
    new THREE.VectorKeyframeTrack('root.position', [0, 1], [0, 0, 0, 50, 50, 50]),
  ]));
  return { root, hand, weapon, visual: createCampaignSiegeCrew(root, [clips(0), clips(1)])! };
}

describe('real player ram crew presentation', () => {
  it('uses the confirmed phase, switches seat packs, and restores held gear on dismount', () => {
    const f = fixture(), origin = f.root.position.clone();
    f.visual.setSeat(0); expect(f.weapon.visible).toBe(false);
    f.visual.update(10.75, { at: 10, target: { x: 0, y: 0, z: 0 } }, 0, 0);
    expect(f.hand.position.x).toBeCloseTo(1.5); expect(f.root.position).toEqual(origin);
    f.visual.update(10.75, { at: 10, target: { x: 1, y: 0, z: 0 } }, 0, 0);
    expect(f.hand.position.x).toBeCloseTo(1.5);
    f.visual.setSeat(1); f.visual.update(10.75, { at: 10, target: { x: 0, y: 0, z: 0 } }, 0, 0);
    expect(f.hand.position.x).toBeCloseTo(11.5);
    f.visual.setSeat(undefined); expect(f.weapon.visible).toBe(true);
    f.visual.update(11, undefined, 0, 0); expect(f.root.position).toEqual(origin);
    f.visual.dispose();
  });

  it('rolls with the engine distance and keeps previously hidden off-hand gear hidden', () => {
    const f = fixture(); f.weapon.visible = false; f.visual.setSeat(0);
    f.visual.update(3, undefined, SIEGE_WHEEL_CIRCUMFERENCE / 2, 2);
    expect(f.hand.position.x).toBeCloseTo(1);
    f.visual.setSeat(undefined); expect(f.weapon.visible).toBe(false);
    f.visual.dispose();
  });

  it('never swaps another player body to obtain a compatible skeleton', async () => {
    expect(compatibleRamCrew(compatible)).toBe(true);
    expect(compatibleRamCrew({ ...compatible, bodyFamily: 'dwarf' })).toBe(false);
    const object = new THREE.Group(), original = new THREE.Mesh(); object.add(original);
    const loader = { resolveStaticOperatorAnimationPacks: async () => { throw Error('must not load'); }, loadCharacterAnimations: async () => [] };
    expect(await assembleCampaignSiegeCrew(object, { ...compatible, bodyVariant: 'f' }, loader)).toBeNull();
    expect(object.children).toEqual([original]);
  });

  it('loads both literal published packs with their unchanged canonical skeleton and clip durations', async () => {
    for (const seat of ['left', 'right']) {
      const bytes = fs.readFileSync(`public/assets/models/frontier_ram_crew_${seat}_animations.glb`);
      const loaded = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
      expect(loaded.animations.map(clip => [clip.name, clip.duration])).toEqual([
        ['ram_crew_idle', 4], ['ram_crew_drive', expect.closeTo(1.6, 5)], ['ram_crew_strike', 1.5],
      ]);
      let meshes = 0; loaded.scene.traverse(node => { if ((node as THREE.Mesh).isMesh) meshes++; }); expect(meshes).toBe(0);
      const root = loaded.scene.getObjectByName('root')!;
      const original = root.matrix.clone();
      const visual = createCampaignSiegeCrew(loaded.scene, [loaded.animations, loaded.animations])!;
      visual.setSeat(0); visual.update(10.7, { at: 10, target: { x: 0, y: 0, z: 1 } }, 0, 0);
      root.updateMatrix(); expect(root.matrix.equals(original)).toBe(true); visual.dispose();
    }
  });

  it('uses the authority ram heading while oil and legacy machines retain their facing policy', () => {
    expect(campaignSiegeFacing({ kind: 'ram', facing: 1.2, position: { x: 0, y: 0, z: 0 }, lastOperation: { at: 0, target: { x: -5, y: 0, z: 0 } } })).toBe(1.2);
  });
});
