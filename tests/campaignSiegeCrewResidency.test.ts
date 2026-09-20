import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';
import { createCampaignSiegeCrew } from '../src/game/network/CampaignSiegeCrewPresentation';
import { SharedCampaignRenderer } from '../src/game/network/SharedCampaignRenderer';

function level() {
  const object = new THREE.Group(), hand = new THREE.Bone(), weapon = new THREE.Group();
  hand.name = 'hand_L'; object.add(hand); hand.add(weapon); weapon.userData.equipmentSlot = 'mainHand';
  const packs = (side: number) => ['ram_crew_idle', 'ram_crew_drive', 'ram_crew_strike'].map((name, index) => {
    const duration = [4, 1.6, 1.5][index];
    return new THREE.AnimationClip(name, duration, [new THREE.NumberKeyframeTrack('hand_L.position[x]', [0, duration], [side * 10, side * 10 + 3])]);
  });
  const crew = createCampaignSiegeCrew(object, [packs(0), packs(1)])!, mixer = new THREE.AnimationMixer(object);
  const idle = mixer.clipAction(new THREE.AnimationClip('idle', 1, [new THREE.NumberKeyframeTrack('hand_L.position[x]', [0, 1], [2, 2])]));
  return { object, hand, weapon, crew, mixer, idle };
}

describe('shared renderer crew LOD lifecycle', () => {
  it('resamples the same confirmed strike after changing LOD and restores locomotion and gear after dismount', () => {
    // Exercise the actual renderer lifecycle without allocating a WebGL context in the unit runner.
    const renderer = Object.assign(Object.create(SharedCampaignRenderer.prototype), { snapshot: { zone: { seconds: 10.7 } }, snapshotElapsed: 0 });
    const close = level(), distant = level(), object = new THREE.Group(); object.add(close.object, distant.object);
    const actor = {
      object, levels: new Map([[0, close], [2, distant]]), selected: -1, animationAccumulator: 0,
      moving: false, animationTime: 20, travelDistance: 0, speed: 0, valid: true,
      operator: { seat: 1, machine: { lastOperation: { at: 10, target: { x: 0, y: 0, z: 5 } } } } as undefined | object,
    };
    renderer.selectActorLevel(actor, 0);
    expect(close.hand.position.x).toBeCloseTo(11.4); expect(close.weapon.visible).toBe(false);
    renderer.selectActorLevel(actor, 2);
    expect(close.object.visible).toBe(false); expect(distant.object.visible).toBe(true);
    expect(distant.hand.position.x).toBeCloseTo(11.4); expect(distant.weapon.visible).toBe(false);
    renderer.selectActorLevel(actor, 0);
    expect(close.hand.position.x).toBeCloseTo(11.4);
    actor.operator = undefined;
    for (const index of [0, 2]) {
      renderer.selectActorLevel(actor, index);
      const visual = actor.levels.get(index)!;
      visual.mixer.update(.1);
      expect(visual.hand.position.x).toBeCloseTo(2);
      expect(visual.weapon.visible).toBe(true);
    }
    renderer.releaseActor(actor);
  });

  it('disposes crew bindings and restores hidden equipment in every resident LOD', () => {
    const renderer = Object.create(SharedCampaignRenderer.prototype), object = new THREE.Group(), levels = [level(), level(), level()];
    const scene = new THREE.Scene(); scene.add(object);
    const uncache = levels.map(visual => vi.spyOn(visual.crew.mixer, 'uncacheRoot'));
    for (const visual of levels) { object.add(visual.object); visual.crew.setSeat(0); visual.crew.update(0, undefined, 0, 0); }
    const actor = { object, levels: new Map(levels.map((visual, index) => [index, visual])), valid: true };
    renderer.releaseActor(actor);
    expect(actor.valid).toBe(false); expect(actor.levels.size).toBe(0); expect(object.parent).toBeNull();
    for (const [index, visual] of levels.entries()) {
      expect(visual.weapon.visible).toBe(true);
      expect(uncache[index]).toHaveBeenCalledWith(visual.object);
      expect(visual.crew.mixer.stats.actions.inUse).toBe(0);
    }
  });
});
