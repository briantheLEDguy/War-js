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
  type ActionVfxContext,
  sampleKeys,
} from './CharacterAnimator';
import * as THREE from 'three';
import { staticTarget, type Vfx } from './VfxLayer';
import { DivineBoltVfx, HealGlowVfx, MeleeImpactVfx } from './WarriorPriestVfx';

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

/**
 * Fraction of each action's duration at which the hammer's striking face
 * reaches the target. Kept next to the key-framed pose curves in
 * `applyAction` so the VFX impact frame stays in lockstep with the visible
 * contact moment.
 */
const WP_IMPACT_FRACTION: Partial<Record<WpActionId, number>> = {
  autoattack:   0.50,
  heavy_strike: 0.48,
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

  /**
   * Class-specific VFX hook.
   *
   *   autoattack   — gold impact burst at the target, delayed so it fires
   *                   on the visible contact frame of the chop.
   *   heavy_strike — larger gold impact burst, same impact-frame alignment.
   *   ranged_shot  — golden divine bolt flying from the off-hand to the
   *                   target (snapshotted at cast time).
   *   bandage      — emerald heal glow anchored to the priest.
   */
  getActionVfx(actionId: string, ctx: ActionVfxContext): Vfx | null {
    const id = actionId as WpActionId;
    switch (id) {
      case 'bandage':
        return new HealGlowVfx(ctx.self, WP_ACTION_DURATION.bandage);

      case 'ranged_shot': {
        if (!ctx.target) return null;
        const targetPos = ctx.target.getWorldPosition(new THREE.Vector3());
        // Nudge the impact point up to the dummy's chest so the ring sits
        // where the silhouette is, not on the ground.
        targetPos.y += 1.1;
        return new DivineBoltVfx(ctx.self, targetPos, WP_ACTION_DURATION.ranged_shot);
      }

      case 'autoattack':
      case 'heavy_strike': {
        if (!ctx.target) return null;
        const impactFrac = WP_IMPACT_FRACTION[id] ?? 0.5;
        const delay = impactFrac * WP_ACTION_DURATION[id];
        // Freeze the target's world position at spawn — the burst should
        // fire where the enemy stood when the ability was committed, not
        // where they are mid-dodge.
        const snapshot = ctx.target.getWorldPosition(new THREE.Vector3());
        return new MeleeImpactVfx(staticTarget(snapshot), delay);
      }

      default:
        return null;
    }
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
   * Autoattack — a committed two-handed diagonal chop.
   *
   * The Hammer of Sigmar is a two-handed weapon, so both arms drive the
   * swing together. The priest cocks the hammer over his right shoulder,
   * snaps it down and across the body, holds briefly at the low point so
   * the weight reads, then returns to rest.
   *
   * Timing (t in 0..1 over ~0.45 s):
   *   0.00 → 0.25  windup — hammer cocks up and back, weight shifts to back foot
   *   0.25 → 0.50  downswing — explosive chop down across the body
   *   0.50 → 0.65  impact hold — heavy hammer lingers for a beat
   *   0.65 → 1.00  recovery to rest
   */
  private applyAutoattack(t: number): void {
    const { rightArm, leftArm, leftLeg, rightLeg, hammer, hammerRestEuler, root } =
      this.rig;

    // Both shoulders share the same pitch curve so the grip reads as a
    // coordinated two-handed chop. Right arm drives the full range; the
    // off-hand's amplitude is scaled so it stays anchored near the haft.
    const shoulderPitch = sampleKeys(
      [
        { t: 0.00, v:  0.0  },
        { t: 0.25, v: -0.9  },   // cocked up and back
        { t: 0.50, v:  1.35 },   // snap-forward through impact
        { t: 0.65, v:  1.20 },   // brief heavy-weapon hold
        { t: 1.00, v:  0.0  },
      ],
      t,
    );

    // Inward shoulder roll — the swing arc crosses the body diagonally
    // rather than staying in the sagittal plane, so there's a Z component.
    const shoulderRoll = sampleKeys(
      [
        { t: 0.00, v:  0.0  },
        { t: 0.25, v:  0.20 },   // right hand pulled in toward centerline
        { t: 0.50, v: -0.35 },   // arc swings across to the left side
        { t: 0.65, v: -0.25 },
        { t: 1.00, v:  0.0  },
      ],
      t,
    );

    rightArm.rotation.x = shoulderPitch;
    rightArm.rotation.z = shoulderRoll;

    // Off-hand tracks the right arm at reduced amplitude so the hands stay
    // plausibly together on the haft. Sign matches (not opposed) — a
    // counter-swing would read as a one-handed swing with a loose off-hand.
    leftArm.rotation.x =  shoulderPitch * 0.75;
    leftArm.rotation.z = -shoulderRoll * 0.6;

    // Stance: right leg plants slightly back during windup, front leg takes
    // the load during impact. Small amplitudes so it reads as a step-step
    // rather than a full lunge.
    const stance = sampleKeys(
      [
        { t: 0.00, v: 0.0 },
        { t: 0.25, v: 1.0 },
        { t: 0.65, v: 1.0 },
        { t: 1.00, v: 0.0 },
      ],
      t,
    );
    rightLeg.rotation.x = -0.18 * stance;   // back leg braces
    leftLeg.rotation.x  =  0.10 * stance;   // front leg forward

    // Weight drop — subtle knee bend at impact sells the weapon weight.
    const impactDrop = sampleKeys(
      [
        { t: 0.00, v: 0.00 },
        { t: 0.45, v: 0.00 },
        { t: 0.50, v: 0.05 },
        { t: 0.65, v: 0.05 },
        { t: 1.00, v: 0.00 },
      ],
      t,
    );
    root.position.y = -impactDrop;

    // Hammer twist: striking face leads the arc, peaks exactly on impact.
    const hammerTwist = sampleKeys(
      [
        { t: 0.00, v: 0.0 },
        { t: 0.25, v: 0.35 },
        { t: 0.50, v: 1.10 },
        { t: 0.65, v: 1.00 },
        { t: 1.00, v: 0.0 },
      ],
      t,
    );
    hammer.rotation.z = hammerRestEuler.z + hammerTwist;
  }

  /**
   * Heavy Strike — the Warrior Priest's signature two-handed overhead smash.
   *
   * A full four-phase swing per classical combat animation:
   *   Anticipation  (0.00 → 0.32): deep coil, hammer lifts behind the head,
   *                                 back leg braces and front leg plants.
   *   Acceleration  (0.32 → 0.48): explosive release — the stored coil snaps
   *                                 the hammer down through the centreline.
   *   Impact        (0.48 → 0.60): hard stop with a knee-drop to sell the
   *                                 transferred weight; hammer frozen a beat.
   *   Follow-through(0.60 → 1.00): smooth recovery, arms unwind to rest, the
   *                                 stance relaxes, weight re-centres.
   *
   * The grip reads two-handed because both shoulders share a matched pitch
   * curve and the shoulder rolls sweep inward so the hands stay plausibly
   * together on the haft through the whole arc.
   */
  private applyHeavyStrike(t: number): void {
    const {
      rightArm, leftArm, leftLeg, rightLeg,
      hammer, hammerRestEuler, root,
    } = this.rig;

    // Right shoulder pitch — coils up behind the head (negative), snaps
    // hard through vertical to a low chest-forward strike (positive).
    // A small overshoot past the impact target reads as committed force
    // before the recovery curve pulls back.
    const shoulderPitch = sampleKeys(
      [
        { t: 0.00, v:  0.0  },
        { t: 0.15, v: -0.8  },   // initial lift
        { t: 0.32, v: -2.3  },   // maximum coil — hammer directly overhead
        { t: 0.48, v:  1.7  },   // strike with slight overshoot
        { t: 0.60, v:  1.45 },   // settle on impact line
        { t: 0.75, v:  1.35 },   // brief hold
        { t: 1.00, v:  0.0  },   // recover to rest
      ],
      t,
    );

    // Off-hand shadows the right arm — same direction, scaled down so the
    // hands stay approximately together on the haft. The slight timing
    // offset at the peak of the coil (a few hundredths of a second later)
    // avoids the "locked-together" uncanny look of a perfectly mirrored rig.
    const offHandPitch = sampleKeys(
      [
        { t: 0.00, v:  0.0  },
        { t: 0.18, v: -0.7  },
        { t: 0.34, v: -1.95 },
        { t: 0.50, v:  1.30 },
        { t: 0.62, v:  1.15 },
        { t: 0.75, v:  1.10 },
        { t: 1.00, v:  0.0  },
      ],
      t,
    );

    // Shoulder rolls pull both hands toward the centreline — the canonical
    // two-handed stance. They relax back out during the recovery.
    const gripRoll = sampleKeys(
      [
        { t: 0.00, v: 0.0 },
        { t: 0.32, v: 1.0 },   // both hands centred at full coil
        { t: 0.60, v: 0.9 },   // still centred through impact
        { t: 1.00, v: 0.0 },
      ],
      t,
    );

    // Hammer twist — striking face rotates to lead the arc. Peaks exactly
    // on impact for a clean "head down" silhouette frame.
    const hammerTwist = sampleKeys(
      [
        { t: 0.00, v: 0.0 },
        { t: 0.32, v: 0.6 },
        { t: 0.48, v: 1.3 },   // fully face-down at impact
        { t: 0.60, v: 1.2 },
        { t: 0.75, v: 1.1 },
        { t: 1.00, v: 0.0 },
      ],
      t,
    );

    // Stance: back leg braces during coil (hip extends), front leg plants
    // forward for the power line. Mirror sign chosen so the whole body
    // silhouette reads as "loading toward a strike" at the coil peak.
    const stanceWidth = sampleKeys(
      [
        { t: 0.00, v: 0.00 },
        { t: 0.32, v: 1.00 },   // fully planted on the coil
        { t: 0.60, v: 1.00 },   // stays planted through impact
        { t: 1.00, v: 0.00 },
      ],
      t,
    );
    rightLeg.rotation.x = -0.30 * stanceWidth;   // right leg back, hip extended
    leftLeg.rotation.x  =  0.18 * stanceWidth;   // left leg forward, knee drives

    // Weight drop — the body dips at impact as the hammer's mass transfers
    // into the target. A 10 cm drop, then a slow rise during recovery.
    const weightDrop = sampleKeys(
      [
        { t: 0.00, v: 0.00 },
        { t: 0.30, v: 0.04 },   // small rise during coil (rising onto toes)
        { t: 0.48, v: 0.00 },
        { t: 0.55, v: -0.10 },  // knees bend hard on impact
        { t: 0.65, v: -0.10 },
        { t: 1.00, v: 0.00 },
      ],
      t,
    );

    rightArm.rotation.x = shoulderPitch;
    leftArm.rotation.x  = offHandPitch;
    rightArm.rotation.z = -0.22 * gripRoll;   // right hand swings inward
    leftArm.rotation.z  =  0.22 * gripRoll;   // left hand swings inward

    hammer.rotation.z = hammerRestEuler.z + hammerTwist;

    root.position.y = weightDrop;
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

  /**
   * Bandage — a self-heal devotional pose. The priest dips into a shallow
   * kneel (root drops, legs bend), plants the hammer vertically in front
   * of the body, and raises the off-hand to his chest in supplication.
   *
   * Timing (t in 0..1 over ~1.20 s):
   *   0.00 → 0.25  ease down into kneel + plant hammer
   *   0.25 → 0.75  hold the pose — this is when the heal ticks
   *   0.75 → 1.00  rise back to standing rest
   */
  private applyBandage(t: number): void {
    const { leftArm, rightArm, leftLeg, rightLeg, hammer, hammerRestEuler, root } =
      this.rig;

    // 0→1 "in-kneel" blend (rises to 1 during the hold, falls back to 0).
    const kneel = sampleKeys(
      [
        { t: 0.00, v: 0.0 },
        { t: 0.25, v: 1.0 },
        { t: 0.75, v: 1.0 },
        { t: 1.00, v: 0.0 },
      ],
      t,
    );

    // Body drops slightly (negative y) during the kneel.
    root.position.y = -0.15 * kneel;

    // Legs bend — front leg bends more than back, like a supplicant's posture.
    leftLeg.rotation.x  =  0.45 * kneel;
    rightLeg.rotation.x = -0.20 * kneel;

    // Off-hand rises to the chest, palm turned inward (devotional gesture).
    leftArm.rotation.x = -1.0  * kneel;
    leftArm.rotation.z =  0.55 * kneel;

    // Weapon arm drops so the hammer rests vertically head-up in front of the body.
    rightArm.rotation.x =  0.25 * kneel;
    rightArm.rotation.z = -0.30 * kneel;

    // Hammer rotates from its diagonal rest to vertical (head pointing up).
    // The rest Z is -PI*0.35; add ~+PI*0.45 so it aligns with the arm axis.
    const verticalize = Math.PI * 0.45 * kneel;
    hammer.rotation.z = hammerRestEuler.z + verticalize;
  }
}
