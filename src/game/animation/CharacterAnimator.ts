/**
 * Base class for procedural character animators.
 *
 * Why procedural: generic fallback meshes are built from Three.js primitives.
 * Manifest-backed GLB models use embedded animation clips; subclasses only
 * exist for local rigs that need deterministic pivot animation.
 *
 * Subclasses implement:
 *   - `applyLocomotion(phase, speed)` — continuous locomotion sampled from a
 *     phase angle (0..2π) that the base class advances proportional to speed.
 *   - `applyAction(action)` — snapshot the current action's progress onto the
 *     rig. Called after locomotion so action poses override locomotion on
 *     overlapping joints.
 *
 * The base class handles:
 *   - Action queue / timing / easing helpers.
 *   - Phase advancement for locomotion.
 *   - Idle blend-in so transitions back to rest are smooth.
 */
import * as THREE from 'three';
import type { TargetProvider, Vfx } from './VfxLayer';

/**
 * Describes where class-specific VFX should anchor. The `self` target always
 * follows the caster; `target` follows the current enemy (if any). Subclasses
 * pick whichever is appropriate per action — a heal pins to `self`, a fireball
 * burst pins to `target`.
 */
export interface ActionVfxContext {
  self: TargetProvider;
  target: TargetProvider | null;
}

/** Per-frame input to `update()`. */
export interface AnimatorInput {
  /** Horizontal planar speed in m/s (used to drive locomotion phase + blend). */
  speed: number;
  /** True while the character is airborne — locomotion freezes, action plays. */
  airborne: boolean;
  /** Time delta in seconds (clamped by the caller). */
  dt: number;
}

/**
 * A discrete action (e.g., hammer swing). Actions are timed keyframe poses —
 * the animator samples them via a 0..1 progress value and applies the result
 * on top of the locomotion pose.
 */
export interface ActionState {
  /** Action id — used by subclasses' switch statements. */
  id: string;
  /** Seconds since the action started. */
  elapsed: number;
  /** Total duration (seconds). */
  duration: number;
}

export abstract class CharacterAnimator {
  /** Locomotion phase angle in radians (0..2π). Advances with speed. */
  protected phase = 0;
  /** 0 = idle, 1 = full locomotion blend. Smoothed toward desired. */
  protected locomotionBlend = 0;
  /** Currently-playing action, or null when idle. */
  protected action: ActionState | null = null;

  /** Steps per second at 1 m/s speed (tune per-class in subclass). */
  protected cadenceHz = 1.2;
  /** Threshold below which locomotion blend fades out. */
  protected readonly idleSpeed = 0.05;

  /** Run one frame of animation. Call after the player has moved. */
  update(input: AnimatorInput): void {
    const { dt, speed, airborne } = input;

    // Advance locomotion phase when grounded and moving.
    if (!airborne && speed > this.idleSpeed) {
      this.phase += dt * this.cadenceHz * Math.PI * 2 * Math.max(1, speed);
      if (this.phase > Math.PI * 4) this.phase -= Math.PI * 4;
    }

    // Blend locomotion in/out so transitions don't snap.
    const targetBlend = !airborne && speed > this.idleSpeed ? 1 : 0;
    this.locomotionBlend = approach(this.locomotionBlend, targetBlend, dt * 6);

    // Reset rig to neutral before layering animations. Subclass overrides.
    this.resetPose();

    // Locomotion layer.
    this.applyLocomotion(this.phase, speed, this.locomotionBlend);

    // Action layer (overrides locomotion on shared joints).
    if (this.action) {
      this.action.elapsed += dt;
      const t = Math.min(1, this.action.elapsed / this.action.duration);
      this.applyAction(this.action, t);
      if (this.action.elapsed >= this.action.duration) this.action = null;
    }
  }

  /**
   * Enqueue a timed action. If an action is already playing, the new one
   * interrupts it (common in MMO-style ability spamming). Subclasses define
   * legal ids.
   */
  playAction(id: string, duration: number): void {
    this.action = { id, elapsed: 0, duration };
  }

  /** True when an action is currently animating — useful for gating VFX. */
  isBusy(): boolean {
    return this.action !== null;
  }

  /**
   * Build the class-specific VFX (if any) that should accompany the given
   * action id. The default implementation returns null — override in
   * subclasses to emit heal glows, weapon trails, bolts, etc.
   *
   * Contract: the returned Vfx has NOT been added to the scene yet; the
   * caller is responsible for handing it to a `VfxLayer.spawn()`.
   */
  getActionVfx(
    _actionId: string,
    _ctx: ActionVfxContext,
  ): Vfx | null {
    return null;
  }

  /** Subclass hook: snap the rig back to rest pose (zero rotations). */
  protected abstract resetPose(): void;

  /** Subclass hook: apply walk/run pose for the given phase, speed, and blend. */
  protected abstract applyLocomotion(
    phase: number,
    speed: number,
    blend: number,
  ): void;

  /** Subclass hook: apply a timed action pose at normalized progress `t` (0..1). */
  protected abstract applyAction(action: ActionState, t: number): void;
}

// ─── Shared easing / math helpers ────────────────────────────────────────────

/** Exponential approach — frame-rate independent smoothing. */
export function approach(current: number, target: number, rate: number): number {
  const k = 1 - Math.exp(-rate);
  return current + (target - current) * k;
}

/** Ease-in-out cubic. Useful for windup → release arcs. */
export function easeInOut(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Ease-out cubic — fast start, slow finish (good for impact follow-through). */
export function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * Piecewise key-frame sampler: given sorted keyframes [{t, v}, ...] and
 * query t in 0..1, returns linearly-interpolated v. Clamps outside range.
 * Small helper so action poses can be authored as data.
 */
export function sampleKeys(
  keys: ReadonlyArray<{ t: number; v: number }>,
  t: number,
): number {
  if (keys.length === 0) return 0;
  if (t <= keys[0].t) return keys[0].v;
  if (t >= keys[keys.length - 1].t) return keys[keys.length - 1].v;
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (t >= a.t && t <= b.t) {
      const u = (t - a.t) / Math.max(1e-6, b.t - a.t);
      return a.v + (b.v - a.v) * u;
    }
  }
  return keys[keys.length - 1].v;
}

/** Reusable zero-rotation helper to avoid allocating on every frame. */
export function zeroRotation(obj: THREE.Object3D): void {
  obj.rotation.set(0, 0, 0);
}
