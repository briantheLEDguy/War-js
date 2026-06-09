/**
 * Reusable VFX (visual-effect) layer.
 *
 * Scope: short-lived spatial effects that accompany combat abilities — heal
 * glows, weapon trails, divine bolts, impact bursts. Generic so any class
 * can register its own effects without touching the base layer.
 *
 * Why a dedicated layer and not "just spawn meshes in Combat.ts":
 *   - Effects need per-frame update (rise, fade, pulse) — a central `update(dt)`
 *     drives all of them so nothing gets orphaned on a paused loop.
 *   - Effects auto-expire and dispose their GPU resources when done.
 *   - Effects can follow a moving target (self-heal on the player) by
 *     accepting a `TargetProvider` rather than a fixed position.
 *
 * Concrete effect subclasses should live alongside the systems that emit them
 * so action-specific art stays out of the combat loop.
 */
import * as THREE from 'three';

/**
 * Anything that can report a world-space anchor point each frame. The game
 * loop re-queries this every update so the effect tracks a moving entity.
 * Use `staticTarget(vec)` to pin to a fixed point.
 */
export interface TargetProvider {
  getWorldPosition(out: THREE.Vector3): THREE.Vector3;
}

/** Pin an effect to a fixed world position. */
export function staticTarget(pos: THREE.Vector3): TargetProvider {
  const frozen = pos.clone();
  return {
    getWorldPosition(out) {
      out.copy(frozen);
      return out;
    },
  };
}

/** Follow a Three.js Object3D (e.g. the player mesh) in world space. */
export function followObject(obj: THREE.Object3D): TargetProvider {
  return {
    getWorldPosition(out) {
      obj.getWorldPosition(out);
      return out;
    },
  };
}

/**
 * Base class for a spatial effect. Subclasses create a root group in
 * `build()`, then animate it per-frame in `updateEffect(t, dt)` where
 * `t` is the normalized 0..1 progress through the effect's lifetime.
 */
export abstract class Vfx {
  /** Active lifetime in seconds, measured from after any start delay. */
  readonly duration: number;
  /**
   * Seconds to wait before the effect becomes visible. Useful for syncing
   * an impact burst to the contact frame of a multi-second swing
   * animation. While delayed, the root group is hidden and `updateEffect`
   * is not called.
   */
  readonly startDelay: number;
  /** Where the effect anchors each frame. */
  readonly target: TargetProvider;
  /** Seconds elapsed since spawn (mutated by VfxLayer). */
  elapsed = 0;
  /** Three.js group containing all mesh(es) for this effect. */
  root: THREE.Group | null = null;

  constructor(target: TargetProvider, duration: number, startDelay = 0) {
    this.target = target;
    this.duration = duration;
    this.startDelay = Math.max(0, startDelay);
  }

  /**
   * Build the mesh(es). Called once at spawn. Must return a group that the
   * VfxLayer will add to the scene; do NOT attach it to the scene here.
   */
  abstract build(): THREE.Group;

  /**
   * Per-frame animation. `t` is progress in 0..1; `dt` is seconds since
   * last frame. The base layer has already updated this.root.position to
   * the current target anchor — subclasses can overwrite it if they want
   * world-static motion (e.g. a projectile that leaves the target).
   */
  abstract updateEffect(t: number, dt: number): void;

  /**
   * Free GPU resources held by any meshes in the root group. Called once
   * when the VfxLayer retires the effect. Default walks children and
   * disposes geometry / materials — override only for custom resources.
   */
  dispose(): void {
    if (!this.root) return;
    this.root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.geometry) m.geometry.dispose();
      if (m.material) {
        const mats = Array.isArray(m.material) ? m.material : [m.material];
        for (const mat of mats) mat.dispose();
      }
    });
  }
}

/**
 * Owns all live effects for a scene. Create one at Game.start(), tick it
 * in the main loop, dispose on teardown.
 */
export class VfxLayer {
  private effects: Vfx[] = [];
  private tmpVec = new THREE.Vector3();

  constructor(private scene: THREE.Scene) {}

  /** Spawn an effect; it will auto-despawn when its duration elapses. */
  spawn(vfx: Vfx): void {
    const root = vfx.build();
    vfx.root = root;
    this.scene.add(root);
    // If the effect has a start delay, hide it until we cross the threshold.
    if (vfx.startDelay > 0) root.visible = false;
    // Anchor to the current target position immediately so the first frame
    // doesn't flash at the origin before update() runs.
    vfx.target.getWorldPosition(this.tmpVec);
    root.position.copy(this.tmpVec);
    this.effects.push(vfx);
  }

  /** Advance all effects; retire expired ones. */
  update(dt: number): void {
    for (let i = this.effects.length - 1; i >= 0; i--) {
      const v = this.effects[i];
      // Isolate each effect: a throw inside updateEffect should retire that
      // effect, not take down the whole layer (which would freeze combat).
      try {
        v.elapsed += dt;

        const activeElapsed = v.elapsed - v.startDelay;
        if (activeElapsed < 0) {
          // Still in the start-delay window — keep the effect hidden and skip
          // its per-frame work. We still advance the target anchor in case
          // the parent moved, so the first visible frame snaps cleanly.
          if (v.root) {
            v.target.getWorldPosition(this.tmpVec);
            v.root.position.copy(this.tmpVec);
          }
          continue;
        }

        // Reveal the effect on the frame the delay expires.
        if (v.root && !v.root.visible) v.root.visible = true;

        // Track the moving target each frame.
        if (v.root) {
          v.target.getWorldPosition(this.tmpVec);
          v.root.position.copy(this.tmpVec);
        }
        const t = Math.min(1, activeElapsed / v.duration);
        v.updateEffect(t, dt);
        if (activeElapsed >= v.duration) {
          if (v.root) this.scene.remove(v.root);
          v.dispose();
          this.effects.splice(i, 1);
        }
      } catch (err) {
        console.error('VFX update failed — retiring effect', err);
        if (v.root) this.scene.remove(v.root);
        try { v.dispose(); } catch { /* already broken */ }
        this.effects.splice(i, 1);
      }
    }
  }

  /** Retire and dispose all live effects (e.g. on zone change). */
  clear(): void {
    for (const v of this.effects) {
      if (v.root) this.scene.remove(v.root);
      v.dispose();
    }
    this.effects = [];
  }

  /** Dispose all effects and release layer state. */
  dispose(): void {
    this.clear();
  }
}
