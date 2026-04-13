/**
 * Warrior Priest animation driver.
 *
 * Drives the pivot groups on a `WarriorPriestRig` to produce:
 *   - Locomotion: alternating leg swing + counter arm swing, sinusoidal torso bob.
 *   - Autoattack: short horizontal hammer swing from rest through a forward arc.
 *   - Heavy Strike: big overhead two-handed smash (added in a follow-up).
 *   - Ranged Shot:  off-hand thrust + divine bolt pose.
 *   - Bandage:      self-heal pose (arms raised, halo-facing).
 *
 * The priest's right arm holds the Hammer of Sigmar. Because the hammer is
 * parented under the right-arm pivot, rotating the shoulder automatically
 * carries the weapon. We bias the right arm's run-cycle amplitude lower so
 * the heavy hammer doesn't flail unrealistically.
 */
import type { WarriorPriestRig } from '../WarriorPriest';
import {
  CharacterAnimator,
  type ActionState,
  easeInOut,
  easeOut,
  sampleKeys,
} from './CharacterAnimator';

// ─── Tunable pose constants ──────────────────────────────────────────────────

/** Peak leg-swing amplitude during full-run locomotion (radians). */
const RUN_LEG_AMP = 0.55;
/** Peak off-hand arm counter-swing amplitude (radians). */
const RUN_LEFT_ARM_AMP = 0.45;
/** Peak hammer-hand bob amplitude — small since the weapon is heavy. */
const RUN_RIGHT_ARM_AMP = 0.12;
/** Vertical bob on the root group (metres). */
const RUN_BODY_BOB = 0.035;

/** Warrior Priest ability ids. Consumed by `applyAction`. */
export type WpActionId =
  | 'autoattack'    // Slot 0 — horizontal hammer swing
  | 'heavy_strike'  // Slot 1 — overhead two-handed smash
  | 'ranged_shot'   // Slot 2 — off-hand Sigmarite bolt
  | 'bandage';      // Slot 3 — self-heal pose

/** Canonical durations (seconds) for each WP action. */
export const WP_ACTION_DURATION: Record<WpActionId, number> = {
  autoattack:   0.45,
  heavy_strike: 0.85,
  ranged_shot:  0.55,
  bandage:      1.20,
};

export class WarriorPriestAnimator extends CharacterAnimator {
  constructor(private rig: WarriorPriestRig) {
    super();
    // Warrior Priest cadence — around 1.6 strides/sec at walk, scales with speed.
    this.cadenceHz = 1.6;
  }

  /** Convenience: play a WP action by id using its canonical duration. */
  playWpAction(id: WpActionId): void {
    this.playAction(id, WP_ACTION_DURATION[id]);
  }

  // ─── Rest pose ─────────────────────────────────────────────────────────────

  protected resetPose(): void {
    const { leftArm, rightArm, leftLeg, rightLeg, hammer, root, hammerRestEuler } = this.rig;

    // All four limb pivots return to neutral (zero) rotation.
    leftArm.rotation.set(0, 0, 0);
    rightArm.rotation.set(0, 0, 0);
    leftLeg.rotation.set(0, 0, 0);
    rightLeg.rotation.set(0, 0, 0);

    // Hammer returns to its held-across-body rest orientation.
    hammer.rotation.copy(hammerRestEuler);

    // Reset root y bob (locomotion layer re-applies as needed).
    root.position.y = 0;
  }

  // ─── Locomotion ────────────────────────────────────────────────────────────

  protected applyLocomotion(phase: number, speed: number, blend: number): void {
    if (blend <= 0.001) return;

    const { leftArm, rightArm, leftLeg, rightLeg, root } = this.rig;

    // Amplitude scales with speed up to ~6 m/s (match MOVE_SPEED in Player).
    const speedScale = Math.min(1, speed / 6) * blend;

    const swing = Math.sin(phase);
    // Legs: opposite-phase swing around X axis.
    leftLeg.rotation.x  =  swing * RUN_LEG_AMP * speedScale;
    rightLeg.rotation.x = -swing * RUN_LEG_AMP * speedScale;

    // Arms: counter to the legs. Left arm swings big; right arm (hammer)
    // bobs only slightly — the priest keeps his weapon hand steady.
    leftArm.rotation.x  = -swing * RUN_LEFT_ARM_AMP  * speedScale;
    rightArm.rotation.x =  swing * RUN_RIGHT_ARM_AMP * speedScale;

    // Subtle body bob at twice the stride frequency (both feet push off).
    root.position.y = Math.abs(Math.sin(phase)) * RUN_BODY_BOB * speedScale;
  }

  // ─── Actions ──────────────────────────────────────────────────────────────

  protected applyAction(action: ActionState, t: number): void {
    switch (action.id as WpActionId) {
      case 'autoattack':   this.applyAutoattack(t); break;
      case 'heavy_strike': this.applyHeavyStrike(t); break;
      case 'ranged_shot':  this.applyRangedShot(t); break;
      case 'bandage':      this.applyBandage(t); break;
    }
  }

  /**
   * Autoattack — a short horizontal hammer swing.
   *
   * The right arm raises slightly (windup), then swings forward through
   * a ~90° arc and returns to rest. The hammer's local rotation twists
   * so the striking face leads the arc.
   */
  private applyAutoattack(t: number): void {
    const { rightArm, leftArm, hammer, hammerRestEuler } = this.rig;

    // Shoulder pitch keyframes: windup (-0.6 rad) → forward strike (+1.2) → rest.
    const shoulderPitch = sampleKeys(
      [
        { t: 0.0,  v: 0.0 },
        { t: 0.25, v: -0.6 },   // windup
        { t: 0.55, v: 1.2 },    // peak forward
        { t: 1.0,  v: 0.0 },    // return
      ],
      t,
    );

    // Small inward shoulder roll so the swing arc crosses the body.
    const shoulderRoll = sampleKeys(
      [
        { t: 0.0,  v: 0.0 },
        { t: 0.25, v: 0.15 },
        { t: 0.55, v: -0.25 },
        { t: 1.0,  v: 0.0 },
      ],
      t,
    );

    rightArm.rotation.x = shoulderPitch;
    rightArm.rotation.z = shoulderRoll;

    // Off-hand follows the motion with a smaller counter-swing.
    leftArm.rotation.x = -shoulderPitch * 0.3;

    // Hammer twists in the hand so the striking face leads the arc — rotate
    // around Z (local to right arm) from rest toward vertical during contact.
    const hammerTwist = sampleKeys(
      [
        { t: 0.0,  v: 0.0 },
        { t: 0.55, v: 0.8 },
        { t: 1.0,  v: 0.0 },
      ],
      t,
    );
    hammer.rotation.z = hammerRestEuler.z + hammerTwist;
  }

  /**
   * Heavy Strike — the Warrior Priest's signature two-handed overhead smash.
   *
   * Timing breakdown (t in 0..1 over ~0.85 s):
   *   0.00 → 0.35  deep windup: both hands raise overhead, torso leans back
   *   0.35 → 0.55  explosive downswing through the vertical plane
   *   0.55 → 0.75  impact hold — hammer frozen at full extension
   *   0.75 → 1.00  recovery to rest pose
   *
   * Both arms drive the swing because this is a two-handed hammer. The off
   * hand mirrors the right arm's pitch so the grip reads as coordinated.
   */
  private applyHeavyStrike(t: number): void {
    const { rightArm, leftArm, hammer, hammerRestEuler, root } = this.rig;

    // Right shoulder pitch: up high for windup, then forward-down for strike.
    // Negative = backward/up in our rig; positive = forward/down.
    const shoulderPitch = sampleKeys(
      [
        { t: 0.00, v:  0.0  },
        { t: 0.35, v: -2.0  },   // hammer fully overhead
        { t: 0.55, v:  1.4  },   // smash through to chest-height-forward
        { t: 0.75, v:  1.4  },   // impact hold
        { t: 1.00, v:  0.0  },   // recover
      ],
      t,
    );

    // Off-hand mirrors the right arm, slightly less amplitude.
    const offHandPitch = sampleKeys(
      [
        { t: 0.00, v:  0.0  },
        { t: 0.35, v: -1.7  },
        { t: 0.55, v:  1.1  },
        { t: 0.75, v:  1.1  },
        { t: 1.00, v:  0.0  },
      ],
      t,
    );

    // Torso lean-back during windup, forward through impact (body y offset fakes it).
    const bodyLean = sampleKeys(
      [
        { t: 0.00, v:  0.00 },
        { t: 0.35, v: -0.08 },   // rock back
        { t: 0.55, v:  0.06 },   // pitch forward
        { t: 0.75, v:  0.06 },
        { t: 1.00, v:  0.00 },
      ],
      t,
    );

    // Hammer twists in the hand so the striking face leads the arc.
    const hammerTwist = sampleKeys(
      [
        { t: 0.00, v:  0.0 },
        { t: 0.35, v:  0.5 },   // ready above the head
        { t: 0.55, v:  1.2 },   // face-down at impact
        { t: 0.75, v:  1.2 },
        { t: 1.00, v:  0.0 },
      ],
      t,
    );

    rightArm.rotation.x = shoulderPitch;
    leftArm.rotation.x  = offHandPitch;
    // Subtle inward roll so the swing arc reads as a centered overhead strike.
    rightArm.rotation.z = easeInOut(t) * -0.15 + 0.15;
    leftArm.rotation.z  = easeInOut(t) *  0.15 - 0.15;

    hammer.rotation.z = hammerRestEuler.z + hammerTwist;

    // Vertical bob — sign matches torso lean so the silhouette bobs with the swing.
    root.position.y = Math.max(0, bodyLean);
  }

  /**
   * Ranged Shot — invoke Sigmar's wrath. The off-hand thrusts forward with
   * an open palm as the divine bolt is released; the hammer-hand stays
   * half-raised in a defensive ready pose.
   *
   * Timing (t in 0..1 over ~0.55 s):
   *   0.00 → 0.25  gather: off-hand pulls back to the hip
   *   0.25 → 0.50  release: off-hand thrusts forward into extension
   *   0.50 → 0.75  hold at full extension (the bolt is airborne)
   *   0.75 → 1.00  recover
   */
  private applyRangedShot(t: number): void {
    const { leftArm, rightArm, hammer, hammerRestEuler } = this.rig;

    // Off-hand pitch: small pullback (positive = forward-down in our rig, so
    // negative = up-forward for the thrust extension).
    const offHandPitch = sampleKeys(
      [
        { t: 0.00, v:  0.00 },
        { t: 0.25, v:  0.30 },   // gathered at the hip
        { t: 0.50, v: -1.45 },   // thrust forward (arm near-horizontal)
        { t: 0.75, v: -1.45 },   // hold
        { t: 1.00, v:  0.00 },
      ],
      t,
    );

    // Off-hand roll: palm opens outward as the bolt releases.
    const offHandRoll = sampleKeys(
      [
        { t: 0.00, v:  0.00 },
        { t: 0.25, v: -0.20 },
        { t: 0.50, v:  0.35 },
        { t: 0.75, v:  0.35 },
        { t: 1.00, v:  0.00 },
      ],
      t,
    );

    // Weapon hand pulls into a defensive ready (hammer slightly raised toward chest).
    const weaponPitch = sampleKeys(
      [
        { t: 0.00, v:  0.00 },
        { t: 0.25, v: -0.35 },
        { t: 0.50, v: -0.50 },
        { t: 0.75, v: -0.50 },
        { t: 1.00, v:  0.00 },
      ],
      t,
    );

    leftArm.rotation.x = offHandPitch;
    leftArm.rotation.z = offHandRoll;
    rightArm.rotation.x = weaponPitch;

    // Hammer tilts to a near-vertical ready guard during the thrust.
    const hammerGuard = sampleKeys(
      [
        { t: 0.00, v:  0.0 },
        { t: 0.50, v:  0.6 },
        { t: 0.75, v:  0.6 },
        { t: 1.00, v:  0.0 },
      ],
      t,
    );
    hammer.rotation.z = hammerRestEuler.z + hammerGuard;
  }

  private applyBandage(t: number): void {
    // Temporary: raise both arms slightly until the full pose is authored.
    const { leftArm, rightArm } = this.rig;
    const raise = Math.sin(Math.PI * t) * 0.4;
    leftArm.rotation.x  = -raise;
    rightArm.rotation.x = -raise;
  }
}
