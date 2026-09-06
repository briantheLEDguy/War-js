import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { CombatAnimationController } from '../src/game/animation/CombatAnimationController';
import { AbilityMotionSequence } from '../src/game/animation/battlePrelateProfile';
import { getAbilityForCareer } from '../src/game/abilities/abilityData';
import type { AbilityAnimation } from '../src/game/abilities/types';

function fixture() {
  const root = new THREE.Group();
  const hand = new THREE.Bone(); hand.name = 'hand_R'; root.add(hand);
  const leg = new THREE.Bone(); leg.name = 'thigh_R'; root.add(leg);
  const clip = (name: string, handEnd: number, legEnd: number) => new THREE.AnimationClip(name, 2, [
    new THREE.NumberKeyframeTrack('hand_R.position[x]', [0, 2], [0, handEnd]),
    new THREE.NumberKeyframeTrack('thigh_R.position[x]', [0, 2], [0, legEnd]),
  ]);
  const clips = [clip('idle', 0, 0), clip('combat_idle', .1, 0), clip('walk', 0, 4), clip('run', 0, 6), clip('jump', 0, 2), clip('death', -1, -1), clip('attack_melee', 2, -2), clip('specific', 4, -4)];
  return { hand, leg, controller: new CombatAnimationController(root, clips) };
}
const motion: AbilityAnimation = { actionId: 'light_attack_a', clip: 'specific', durationSec: 1, notifyWindows: [], blendInSec: .05, blendOutSec: .1 };

describe('combat animation playback', () => {
  test('selects explicit clips, falls back to generic actions, and reports absent motion', () => {
    const { controller } = fixture();
    expect(controller.resolveClip(motion)).toBe('specific');
    expect(controller.resolveClip({ ...motion, clip: 'missing' })).toBe('attack_melee');
    expect(controller.resolveClip({ clip: 'missing', actionId: 'unknown' })).toBeNull();
  });
  test('fits source duration to the requested action timeline', () => {
    const { controller, hand } = fixture(); controller.play(motion);
    controller.update(.5, 0, false);
    expect(hand.position.x).toBeCloseTo(2);
  });
  test('repeated actions restart and crossfade without stopping the new action', () => {
    const { controller, hand } = fixture(); controller.play(motion); controller.update(.6, 0, false);
    expect(hand.position.x).toBeCloseTo(2.4);
    controller.play(motion); controller.update(.1, 0, false);
    expect(hand.position.x).toBeCloseTo(.4);
    controller.update(.1, 0, false);
    expect(hand.position.x).toBeCloseTo(.8);
  });
  test('moving legs retain locomotion while the upper body attacks', () => {
    const { controller, hand, leg } = fixture(); controller.play(motion);
    for (let i = 0; i < 30; i++) controller.update(1 / 60, 3, false);
    expect(hand.position.x).toBeCloseTo(2);
    expect(leg.position.x).toBeGreaterThan(0);
  });
  test('stationary actions use their authored lower-body pose', () => {
    const { controller, leg } = fixture(); controller.play(motion); controller.update(.5, 0, false);
    expect(leg.position.x).toBeCloseTo(-2);
  });
  test('interruptions retire and release old tracks and return to idle', () => {
    const { controller, hand } = fixture();
    for (let i = 0; i < 40; i++) { controller.play(motion); controller.update(.05, 0, false); }
    for (let i = 0; i < 360; i++) controller.update(1 / 60, 0, false);
    expect(hand.position.x).toBeCloseTo(0, 4);
    controller.dispose();
  });
  test('combat guard lasts four seconds after a combat notification', () => {
    const { controller, hand } = fixture(); controller.markCombat();
    controller.update(1, 0, false); expect(hand.position.x).toBeGreaterThan(0);
    for (let i = 0; i < 300; i++) controller.update(1 / 60, 0, false);
    expect(hand.position.x).toBeCloseTo(0, 4);
  });
  test('airborne legs are animated while an ability continues', () => {
    const { controller, leg } = fixture(); controller.play(motion); controller.update(.4, 0, true);
    expect(leg.position.x).toBeGreaterThan(0);
    controller.update(.1, 0, false);
    expect(Number.isFinite(leg.position.x)).toBe(true);
  });
});

describe('Litany sequence', () => {
  test('cycles once per activation, resets after three seconds, and does not mutate catalog data', () => {
    const sequence = new AbilityMotionSequence();
    const ability = getAbilityForCareer('Battle Prelate', 0)!;
    const original = structuredClone(ability);
    expect(sequence.resolve(ability, 1000).animation.clip).toBe('prelate_litany_a');
    expect(sequence.resolve(ability, 2300).animation.clip).toBe('prelate_litany_b');
    expect(sequence.resolve(ability, 3600).animation.clip).toBe('prelate_litany_c');
    expect(sequence.resolve(ability, 4900).animation.clip).toBe('prelate_litany_a');
    expect(sequence.resolve(ability, 7900).animation.clip).toBe('prelate_litany_a');
    expect(ability).toEqual(original);
  });
  test('other abilities leave the sequence intact', () => {
    const sequence = new AbilityMotionSequence();
    const litany = getAbilityForCareer('Battle Prelate', 0)!;
    sequence.resolve(litany, 1000);
    sequence.resolve(getAbilityForCareer('Battle Prelate', 1)!, 1500);
    expect(sequence.resolve(litany, 2300).animation.clip).toBe('prelate_litany_b');
  });
});
