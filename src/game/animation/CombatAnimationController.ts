import * as THREE from 'three';
import type { AbilityAnimation } from '../abilities/types';

const lowerBody = /^(root|hips|thigh_[LR]|shin_[LR]|foot_[LR]|toe.*|socket_root)$/;
type Layers = { upper: THREE.AnimationAction; lower: THREE.AnimationAction };
type Playing = { layers: Layers; elapsed: number; duration: number; weight: number; blendIn: number; blendOut: number; retiring: boolean };

export function genericActionClip(id: string): string | null {
  if (/^(autoattack|heavy_strike|light_attack_[abc]|heavy_attack|shield_bash)$/.test(id)) return 'attack_melee';
  if (/^(ranged_shot|shoot_standing|shoot_moving)$/.test(id)) return 'attack_ranged';
  if (/^(bandage|cast_short|cast_long|cast_heal|ultimate_cast)$/.test(id)) return 'cast';
  return id === 'jump' || id === 'death' ? id : null;
}

/** Disjoint track masks keep locomotion authoritative on moving feet. */
export class CombatAnimationController {
  private mixer: THREE.AnimationMixer;
  private clips = new Map<string, THREE.AnimationClip>();
  private loops = new Map<string, { layers: Layers; weight: number }>();
  private playing: Playing[] = [];
  private moveBlend = 0;
  private combatRemaining = 0;
  private wasAirborne = false;
  private landingRemaining = 0;
  private dead = false;
  private serial = 0;

  constructor(root: THREE.Object3D, clips: THREE.AnimationClip[]) {
    this.mixer = new THREE.AnimationMixer(root);
    for (const clip of clips) this.clips.set(clip.name, clip);
    for (const name of ['idle', 'combat_idle', 'walk', 'run', 'jump', 'death', 'prelate_land']) {
      const clip = this.clips.get(name);
      if (!clip) continue;
      const layers = this.layers(clip);
      for (const action of Object.values(layers)) {
        action.setLoop(['jump', 'death', 'prelate_land'].includes(name) ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
        action.clampWhenFinished = true;
        action.play().setEffectiveWeight(0);
      }
      this.loops.set(name, { layers, weight: name === 'idle' ? 1 : 0 });
    }
  }

  resolveClip(animation: Pick<AbilityAnimation, 'clip' | 'actionId'>): string | null {
    if (this.clips.has(animation.clip)) return animation.clip;
    const fallback = genericActionClip(animation.actionId);
    return fallback && this.clips.has(fallback) ? fallback : null;
  }

  markCombat(): void { this.combatRemaining = 4; }

  play(animation: AbilityAnimation): boolean {
    const name = this.resolveClip(animation);
    if (!name) return false;
    for (const action of this.playing) action.retiring = true;
    const layers = this.layers(this.clips.get(name)!);
    for (const action of Object.values(layers)) {
      action.reset().setLoop(THREE.LoopOnce, 1).setDuration(animation.durationSec).setEffectiveWeight(0).play();
      action.clampWhenFinished = true;
    }
    this.playing.push({ layers, elapsed: 0, duration: animation.durationSec, weight: 0,
      blendIn: animation.blendInSec ?? .1, blendOut: animation.blendOutSec ?? .16, retiring: false });
    this.markCombat();
    return true;
  }

  update(dt: number, speed: number, airborne: boolean, dead = false): void {
    dt = Math.max(0, dt);
    this.combatRemaining = Math.max(0, this.combatRemaining - dt);
    this.moveBlend = THREE.MathUtils.damp(this.moveBlend, airborne ? 1 : THREE.MathUtils.smoothstep(speed, .05, .8), 18, dt);
    if (airborne && !this.wasAirborne) this.restartLoop('jump');
    if (!airborne && this.wasAirborne) { this.restartLoop('prelate_land'); this.landingRemaining = .25; }
    if (dead && !this.dead) { this.restartLoop('death'); for (const action of this.playing) action.retiring = true; }
    this.wasAirborne = airborne;
    this.dead = dead;
    const desired = dead ? 'death' : airborne ? 'jump' : this.landingRemaining > 0 && speed < .15 ? 'prelate_land'
      : speed > 3.6 ? 'run' : speed > .15 ? 'walk' : this.combatRemaining > 0 ? 'combat_idle' : 'idle';
    const loopName = this.loops.has(desired) ? desired : 'idle';
    this.landingRemaining = Math.max(0, this.landingRemaining - dt);
    let total = 0;
    for (const action of this.playing) {
      action.elapsed += dt;
      if (action.elapsed >= action.duration - action.blendOut) action.retiring = true;
      action.weight = action.retiring ? Math.max(0, action.weight - dt / Math.max(.001, action.blendOut))
        : Math.min(1, action.weight + dt / Math.max(.001, action.blendIn));
      total += action.weight;
    }
    const scale = total > 1 ? 1 / total : 1;
    const upperWeight = Math.min(1, total);
    const lowerWeight = upperWeight * (1 - this.moveBlend);
    for (const action of this.playing) {
      action.layers.upper.setEffectiveWeight(action.weight * scale);
      action.layers.lower.setEffectiveWeight(action.weight * scale * (1 - this.moveBlend));
    }
    let loopTotal = 0;
    for (const [name, loop] of this.loops) {
      loop.weight = THREE.MathUtils.damp(loop.weight, name === loopName ? 1 : 0, 18, dt);
      loopTotal += loop.weight;
    }
    for (const [name, loop] of this.loops) {
      const weight = loop.weight / Math.max(1e-6, loopTotal);
      loop.layers.upper.setEffectiveWeight(weight * (1 - upperWeight));
      loop.layers.lower.setEffectiveWeight(weight * (1 - lowerWeight));
      if (name === 'walk' || name === 'run') {
        const rate = THREE.MathUtils.clamp(speed / (name === 'walk' ? 2.4 : 6), .35, 1.6);
        loop.layers.upper.setEffectiveTimeScale(rate);
        loop.layers.lower.setEffectiveTimeScale(rate);
      }
    }
    this.mixer.update(dt);
    this.playing = this.playing.filter((action) => {
      if (!action.retiring || action.weight > 0) return true;
      this.release(action.layers);
      return false;
    });
  }

  dispose(): void {
    this.mixer.stopAllAction();
    this.mixer.uncacheRoot(this.mixer.getRoot());
    this.playing = [];
    this.loops.clear();
  }

  reset(): void {
    for (const action of this.playing) this.release(action.layers);
    this.playing = [];
    this.moveBlend = 0;
    this.wasAirborne = false;
    this.landingRemaining = 0;
    this.combatRemaining = 0;
    for (const [name, loop] of this.loops) {
      loop.weight = name === 'idle' ? 1 : 0;
      for (const action of Object.values(loop.layers)) action.reset().play();
    }
    this.update(0, 0, false);
  }

  private restartLoop(name: string): void {
    const loop = this.loops.get(name);
    if (loop) for (const action of Object.values(loop.layers)) action.reset().play();
  }

  private layers(clip: THREE.AnimationClip): Layers {
    const make = (lower: boolean) => {
      const tracks = clip.tracks.filter((track) => lowerBody.test(track.name.split('.')[0]) === lower);
      return this.mixer.clipAction(new THREE.AnimationClip(`${clip.name}_${lower}_${this.serial++}`, clip.duration, tracks));
    };
    return { upper: make(false), lower: make(true) };
  }

  private release(layers: Layers): void {
    for (const action of Object.values(layers)) { action.stop(); this.mixer.uncacheClip(action.getClip()); }
  }
}
