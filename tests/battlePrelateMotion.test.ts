import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { beforeAll, describe, expect, test, vi } from 'vitest';
import contract from '../src/game/animation/battlePrelateMotions.json';
import { getCareerAbilityKit } from '../src/game/abilities/abilityData';
import { AssetLoader } from '../src/game/AssetLoader';

const path = 'public/assets/models/';
const bytes = readFileSync(path + 'anim_battle_prelate_combat.glb');
const json = (b: Buffer) => JSON.parse(b.subarray(20, 20 + b.readUInt32LE(12)).toString());
let clips: THREE.AnimationClip[];
beforeAll(async () => { clips = (await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer, '')).animations; });

function skeleton(variant: string) {
  const data = json(readFileSync(path + `chr_civic_battle_prelate_t1_${variant}.glb`));
  const nodes = data.nodes.map((n: any) => {
    const object = new THREE.Bone(); object.name = n.name;
    if (n.translation) object.position.fromArray(n.translation);
    if (n.rotation) object.quaternion.fromArray(n.rotation);
    if (n.scale) object.scale.fromArray(n.scale);
    if (n.matrix) { object.matrix.fromArray(n.matrix); object.matrix.decompose(object.position, object.quaternion, object.scale); }
    return object;
  });
  data.nodes.forEach((n: any, i: number) => n.children?.forEach((child: number) => nodes[i].add(nodes[child])));
  const root = new THREE.Group();
  data.scenes[data.scene ?? 0].nodes.forEach((id: number) => root.add(nodes[id]));
  return root;
}

describe('exported Battle Prelate pack', () => {
  test('covers all choreography with correct duration and valid contact markers', () => {
    expect(clips.map((c) => c.name)).toEqual(expect.arrayContaining(['combat_idle', 'prelate_land', ...contract.motions.map((m) => m.clip)]));
    for (const motion of contract.motions) {
      const clip = clips.find((c) => c.name === motion.clip)!;
      expect(clip.duration).toBeCloseTo(motion.durationSec, 1);
      expect(motion.contact).toBeGreaterThan(.1);
      expect(motion.contact).toBeLessThan(motion.durationSec - .16);
    }
  });
  test.each(['m', 'f'])('binds all tracks to the %s canonical hierarchy and preserves planted feet', (variant) => {
    const root = skeleton(variant);
    for (const clip of clips) {
      expect(clip.tracks.every((track) => !!root.getObjectByName(track.name.split('.')[0]))).toBe(true);
      const mixer = new THREE.AnimationMixer(root);
      const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1); action.clampWhenFinished = true; action.play();
      const positions: THREE.Vector3[][] = [[], []];
      for (let i = 0; i <= 60; i++) {
        mixer.setTime(clip.duration * i / 60); root.updateMatrixWorld(true);
        ['foot_L', 'foot_R'].forEach((name, side) => positions[side].push(root.getObjectByName(name)!.getWorldPosition(new THREE.Vector3())));
      }
      for (const foot of positions) expect(Math.max(...foot.map((p) => p.distanceTo(foot[0])))).toBeLessThan(.002);
      mixer.stopAllAction(); mixer.uncacheRoot(root);
    }
  });
  test('registry and source manifests reference the exact exported bytes', () => {
    const digest = createHash('sha256').update(bytes).digest('hex');
    const index = JSON.parse(readFileSync(path + 'asset-index.json', 'utf8'));
    for (const variant of ['m', 'f']) expect(index.characterProfiles[`civic_battle_prelate_${variant}`].animationPack.sha256).toBe(digest);
  });
  test.each(['m', 'f'])('keeps the %s supporting palm on the shaft during two-hand attacks', (variant) => {
    const root = skeleton(variant);
    const weapon = json(readFileSync(path + 'wep_civic_battle_prelate_dawn_maul.glb'));
    const raw = weapon.nodes.find((n: any) => n.extras?.secondary_grip_local).extras.secondary_grip_local;
    const local = new THREE.Vector3(raw[0], raw[2], -raw[1]);
    for (const motion of contract.motions.filter((m) => ['diagonal', 'return', 'descending', 'empowered', 'drive', 'overhead', 'thrust'].includes(m.style))) {
      const clip = clips.find((c) => c.name === motion.clip)!;
      const mixer = new THREE.AnimationMixer(root);
      const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1); action.clampWhenFinished = true; action.play();
      for (let i = 0; i <= 60; i++) {
        mixer.setTime(clip.duration * i / 60); root.updateMatrixWorld(true);
        const desired = root.getObjectByName('socket_hand_R')!.localToWorld(local.clone());
        const actual = root.getObjectByName('socket_hand_L')!.getWorldPosition(new THREE.Vector3());
        expect(actual.distanceTo(desired), `${variant}/${motion.clip}/${i}`).toBeLessThan(.005);
      }
      mixer.stopAllAction(); mixer.uncacheRoot(root);
    }
  });
  test('only Battle Prelate abilities opt into the new profile', () => {
    expect(getCareerAbilityKit('Battle Prelate').abilities.every((a) => a.animation.contactSec !== undefined)).toBe(true);
    expect(getCareerAbilityKit('Warbrute').abilities.every((a) => a.animation.contactSec === undefined)).toBe(true);
  });
  test('hammer attacks have distinct loaded silhouettes and a readable windup', () => {
    const root = skeleton('m');
    const poses: { name: string; rotation: THREE.Quaternion }[] = [];
    for (const motion of contract.motions.filter((m) => ['return', 'descending', 'empowered', 'drive', 'overhead', 'thrust'].includes(m.style))) {
      const mixer = new THREE.AnimationMixer(root);
      mixer.clipAction(clips.find((c) => c.name === motion.clip)!).play();
      mixer.setTime(0); root.updateMatrixWorld(true);
      const socket = root.getObjectByName('socket_hand_R')!;
      const initial = socket.getWorldQuaternion(new THREE.Quaternion());
      mixer.setTime(motion.contact * .64); root.updateMatrixWorld(true);
      const rotation = socket.getWorldQuaternion(new THREE.Quaternion());
      expect(initial.angleTo(rotation), motion.clip + ' windup').toBeGreaterThan(.35);
      poses.push({ name: motion.clip, rotation });
      mixer.stopAllAction(); mixer.uncacheRoot(root);
    }
    for (let a = 0; a < poses.length; a++) for (let b = a + 1; b < poses.length; b++) {
      expect(poses[a].rotation.angleTo(poses[b].rotation), `${poses[a].name}/${poses[b].name}`).toBeGreaterThan(.20);
    }
  });
  test('swing attacks carry the hammer through a broad arc', () => {
    const root = skeleton('m');
    const weapon = json(readFileSync(path + 'wep_civic_battle_prelate_dawn_maul.glb'));
    const raw = weapon.nodes.find((n: any) => n.extras?.head_center_local).extras.head_center_local;
    const head = new THREE.Vector3(raw[0], raw[2], -raw[1]);
    for (const motion of contract.motions.filter((m) => ['diagonal', 'return', 'descending', 'empowered', 'overhead'].includes(m.style))) {
      const mixer = new THREE.AnimationMixer(root);
      mixer.clipAction(clips.find((c) => c.name === motion.clip)!).play();
      const positions: THREE.Vector3[] = [];
      for (let i = 0; i <= 60; i++) {
        mixer.setTime(motion.durationSec * i / 60); root.updateMatrixWorld(true);
        positions.push(root.getObjectByName('socket_hand_R')!.localToWorld(head.clone()));
      }
      const span = Math.max(...positions.flatMap((a) => positions.map((b) => a.distanceTo(b))));
      expect(span, motion.clip).toBeGreaterThan(.7);
      mixer.stopAllAction(); mixer.uncacheRoot(root);
    }
  });
  test('hammer shaft stays outside the central torso during the heavy strike contacts', () => {
    const root = skeleton('m');
    const weapon = json(readFileSync(path + 'wep_civic_battle_prelate_dawn_maul.glb'));
    const raw = weapon.nodes.find((n: any) => n.extras?.head_center_local).extras.head_center_local;
    const axis = new THREE.Vector3(raw[0], raw[2], -raw[1]).normalize();
    for (const motion of contract.motions.filter((m) => ['descending', 'drive', 'overhead', 'thrust'].includes(m.style))) {
      const mixer = new THREE.AnimationMixer(root);
      mixer.clipAction(clips.find((c) => c.name === motion.clip)!).play();
      mixer.setTime(motion.contact); root.updateMatrixWorld(true);
      const chest = root.getObjectByName('chest')!.getWorldPosition(new THREE.Vector3());
      for (let i = 0; i <= 100; i++) {
        const p = root.getObjectByName('socket_hand_R')!.localToWorld(axis.clone().multiplyScalar(-1.09 + i * 1.51 / 100));
        if (p.y < .85 || p.y > 1.48) continue;
        const radius = Math.hypot(p.x - chest.x, p.z - chest.z);
        expect(radius, motion.clip).toBeGreaterThan(.20);
      }
      mixer.stopAllAction(); mixer.uncacheRoot(root);
    }
  });
  test('absent and incompatible packs retain the embedded fallback', async () => {
    const loader = new AssetLoader();
    expect(await loader.loadCharacterAnimations({ model: 'body.glb' }, new THREE.Group())).toEqual([]);
    expect(await loader.loadCharacterAnimations({ model: 'body.glb', skeletonId: 'other', animationPack: {
      model: 'missing.glb', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2', sha256: '',
    } }, new THREE.Group())).toEqual([]);
    loader.dispose();
  });
  test('loads a verified pack once, rejects bad bindings, and safely falls back on missing or corrupt bytes', async () => {
    const sha256 = createHash('sha256').update(bytes).digest('hex');
    const asset = { model: 'body.glb', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2', animationPack: {
      model: 'anim_battle_prelate_combat.glb', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2', sha256,
    } };
    const fetch = vi.fn(async () => new Response(bytes));
    vi.stubGlobal('fetch', fetch);
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const loader = new AssetLoader();
    try {
      expect((await loader.loadCharacterAnimations(asset, skeleton('m'))).length).toBe(14);
      expect((await loader.loadCharacterAnimations(asset, skeleton('f'))).length).toBe(14);
      expect(fetch).toHaveBeenCalledTimes(1);
      expect(await loader.loadCharacterAnimations(asset, new THREE.Group())).toEqual([]);
      expect(await loader.loadCharacterAnimations({ ...asset, animationPack: { ...asset.animationPack, sha256: '0'.repeat(64) } }, skeleton('m'))).toEqual([]);
      fetch.mockImplementation(async () => new Response(null, { status: 404 }));
      expect(await loader.loadCharacterAnimations({ ...asset, animationPack: { ...asset.animationPack, model: 'missing.glb' } }, skeleton('m'))).toEqual([]);
    } finally { loader.dispose(); warn.mockRestore(); vi.unstubAllGlobals(); }
  });
});
