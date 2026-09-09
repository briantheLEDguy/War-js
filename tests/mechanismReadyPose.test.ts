import * as THREE from 'three';
import { describe, expect, it } from 'vitest';
import { applyMechanismReadyPose } from '../src/game/animation/MechanismReadyPose';

describe('static mechanism ready pose for game and GM placements', () => {
  it('keeps a fixed axle parent while sampling the arm and rope, without changing cached clones or clips', () => {
    const cached = new THREE.Group(), pivot = new THREE.Group(), arm = new THREE.Group(), rope = new THREE.Group();
    pivot.position.set(2, 3, 4); arm.name = 'arm'; rope.name = 'rope'; pivot.add(arm, rope); cached.add(pivot);
    const clip = new THREE.AnimationClip('catapult_fire', 1, [
      new THREE.NumberKeyframeTrack('arm.rotation[x]', [0, 1], [-1.1, .37]),
      new THREE.NumberKeyframeTrack('rope.scale[y]', [0, 1], [.5, 1.2]),
    ]);
    const loaded = cached.clone(true);
    applyMechanismReadyPose(loaded, [clip]);
    expect(loaded.getObjectByName('arm')!.rotation.x).toBeCloseTo(-1.1);
    expect(loaded.getObjectByName('rope')!.scale.y).toBeCloseTo(.5);
    expect(loaded.children[0].position.toArray()).toEqual([2, 3, 4]);
    expect(arm.rotation.x).toBe(0);
    expect(rope.scale.y).toBe(1);
    const mixer = new THREE.AnimationMixer(loaded);
    mixer.clipAction(clip).play(); mixer.update(.5);
    expect(loaded.getObjectByName('arm')!.rotation.x).toBeCloseTo(-.365);
    mixer.stopAllAction(); mixer.uncacheRoot(loaded);
    expect(loaded.getObjectByName('arm')!.rotation.x).toBeCloseTo(-1.1);
  });
  it('leaves unrelated props and character clips in their existing pose', () => {
    const object = new THREE.Group(); object.position.set(1, 2, 3);
    applyMechanismReadyPose(object, [new THREE.AnimationClip('idle', 2, [])]);
    expect(object.position.toArray()).toEqual([1, 2, 3]);
  });
});
