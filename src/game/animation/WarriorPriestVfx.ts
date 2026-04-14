/**
 * Warrior Priest visual effects.
 *
 * All effects subclass `Vfx` so they plug straight into the generic
 * `VfxLayer`. Sigmar's favour is rendered as warm-gold motes for offensive
 * channels and emerald-green motes for restorative channels — the two
 * colour keys that readers of the Warhammer fiction associate with the
 * god's dual nature (wrath and mercy).
 */
import * as THREE from 'three';
import { Vfx, type TargetProvider } from './VfxLayer';

// Shared palette — tuned warm gold + emerald green so the motes read
// against both dark-stone indoor zones and bright sky outdoor zones.
const HEAL_COLOR = 0x48e07a;         // emerald green — Sigmar's mercy
const HEAL_CORE_COLOR = 0xb8ffc8;    // almost-white core for the central orb
const BOLT_COLOR = 0xffd560;         // warm gold — Sigmar's wrath (ranged bolt)
const BOLT_CORE_COLOR = 0xfff4c8;    // pale yellow core for the bolt head

/**
 * Heal glow — an emerald halo under the caster's feet plus several rising
 * sparkle motes that orbit and fade. Reads clearly from third-person camera
 * without obscuring the character.
 *
 * Lifetime should match the bandage action's duration (~1.2 s). The glow
 * ramps in over the first 25 %, holds full intensity during the channel,
 * then fades out smoothly.
 */
export class HealGlowVfx extends Vfx {
  private disc!: THREE.Mesh;
  private discMat!: THREE.MeshBasicMaterial;
  private core!: THREE.Mesh;
  private coreMat!: THREE.MeshBasicMaterial;
  private motes: Array<{
    mesh: THREE.Mesh;
    mat: THREE.MeshBasicMaterial;
    angle: number;
    radius: number;
    phase: number;
    rise: number;
  }> = [];

  /** @param target  usually the caster (self-heal). */
  constructor(target: TargetProvider, duration = 1.2) {
    super(target, duration);
  }

  build(): THREE.Group {
    const group = new THREE.Group();
    group.name = 'HealGlow';

    // Ground disc — sits just above the feet plane so z-fighting doesn't
    // show on flat city cobbles. Additive blending sells the "divine light"
    // feel without a real light source (which would be expensive).
    const discGeo = new THREE.CircleGeometry(1.2, 32);
    discGeo.rotateX(-Math.PI / 2);
    this.discMat = new THREE.MeshBasicMaterial({
      color: HEAL_COLOR,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    this.disc = new THREE.Mesh(discGeo, this.discMat);
    this.disc.position.y = 0.02;
    group.add(this.disc);

    // Central core orb — floats at the caster's chest, pulses through the hold.
    this.coreMat = new THREE.MeshBasicMaterial({
      color: HEAL_CORE_COLOR,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    this.core = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 16, 12),
      this.coreMat,
    );
    this.core.position.y = 1.25;
    group.add(this.core);

    // Orbiting motes — six small tetrahedra on random orbit starting angles.
    // Tetrahedra read as sparkles without needing a sprite texture.
    for (let i = 0; i < 6; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: HEAL_COLOR,
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const geo = new THREE.TetrahedronGeometry(0.08, 0);
      const mesh = new THREE.Mesh(geo, mat);
      const angle = (i / 6) * Math.PI * 2 + Math.random() * 0.4;
      const radius = 0.6 + Math.random() * 0.25;
      const phase = Math.random() * Math.PI * 2;
      const rise = 0.6 + Math.random() * 0.7;  // metres over the effect lifetime
      mesh.position.set(Math.cos(angle) * radius, 0.3, Math.sin(angle) * radius);
      group.add(mesh);
      this.motes.push({ mesh, mat, angle, radius, phase, rise });
    }

    return group;
  }

  updateEffect(t: number, _dt: number): void {
    // Overall intensity envelope: ramp 0-0.25, hold 0.25-0.75, fade 0.75-1.
    const env =
      t < 0.25 ? t / 0.25 :
      t > 0.75 ? 1 - (t - 0.75) / 0.25 :
      1;

    // Ground disc: pulse at ~3 Hz within the envelope.
    const pulse = 0.7 + 0.3 * Math.sin(t * Math.PI * 6);
    this.discMat.opacity = 0.55 * env * pulse;
    const discScale = 0.85 + 0.15 * pulse;
    this.disc.scale.setScalar(discScale);

    // Core orb: rises slightly as the heal completes, fades with envelope.
    this.coreMat.opacity = 0.9 * env;
    this.core.position.y = 1.25 + 0.08 * Math.sin(t * Math.PI * 4);
    this.core.rotation.y += 0.04;

    // Motes: orbit, rise, and fade — gives a "prayer answered" ascension read.
    for (const m of this.motes) {
      const a = m.angle + t * Math.PI * 2;  // one revolution per lifetime
      const r = m.radius * (1 - 0.35 * t);  // tighten inward
      m.mesh.position.x = Math.cos(a) * r;
      m.mesh.position.z = Math.sin(a) * r;
      m.mesh.position.y = 0.3 + m.rise * t;
      m.mesh.rotation.x += 0.08;
      m.mesh.rotation.y += 0.05;
      // Each mote flickers on a small phase offset so they don't pulse in lockstep.
      const flicker = 0.6 + 0.4 * Math.sin(t * Math.PI * 8 + m.phase);
      m.mat.opacity = env * flicker;
    }
  }
}

/**
 * Divine Bolt — a gold comet launched from the caster's off-hand toward the
 * enemy. Travels along a straight line over the action's second half
 * (matching the `ranged_shot` animation's release phase), leaves a tapered
 * trail of motes, and finishes with a small radial burst at the target.
 *
 * The bolt does NOT anchor to the caster's moving position each frame — it
 * snapshots the caster's release point and the enemy target point at spawn
 * and lerps between them, so the projectile reads as a launched object
 * rather than something tethered to the priest.
 */
export class DivineBoltVfx extends Vfx {
  private caster: TargetProvider;
  private targetPos: THREE.Vector3;
  private start = new THREE.Vector3();
  private bolt!: THREE.Mesh;
  private boltMat!: THREE.MeshBasicMaterial;
  private trail: Array<{
    mesh: THREE.Mesh;
    mat: THREE.MeshBasicMaterial;
    offset: number;  // 0..1 — fraction of the flight path behind the head
  }> = [];
  private burst!: THREE.Mesh;
  private burstMat!: THREE.MeshBasicMaterial;
  /** Fraction of total duration before launch (windup portion of the cast). */
  private readonly launchT = 0.35;

  /**
   * @param caster     follows the priest so the launch point tracks his
   *                    off-hand if he turns or moves during windup.
   * @param targetPos  world-space anchor for the enemy (snapshotted at spawn
   *                    — a moving enemy will not be tracked mid-flight, which
   *                    matches WAR's instant-hit bolt mechanics).
   */
  constructor(caster: TargetProvider, targetPos: THREE.Vector3, duration = 0.55) {
    // Anchor target is the caster — we override position ourselves in
    // updateEffect so the base layer's auto-anchor is just a safe default
    // before the first frame runs.
    super(caster, duration);
    this.caster = caster;
    this.targetPos = targetPos.clone();
  }

  build(): THREE.Group {
    const group = new THREE.Group();
    group.name = 'DivineBolt';

    // Bolt head — bright core plus a surrounding halo disc so it reads from
    // any camera angle without a real light source.
    this.boltMat = new THREE.MeshBasicMaterial({
      color: BOLT_CORE_COLOR,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    this.bolt = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 10), this.boltMat);
    group.add(this.bolt);

    // Trail motes — each one renders at a small distance "behind" the bolt
    // head along the flight direction. Offsets fan out across 0..0.25 so the
    // trail reads as a comet tail rather than a uniform blob.
    for (let i = 0; i < 7; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: BOLT_COLOR,
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const scale = 0.12 - i * 0.012;
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(Math.max(0.04, scale), 8, 6),
        mat,
      );
      group.add(mesh);
      this.trail.push({ mesh, mat, offset: 0.04 + i * 0.035 });
    }

    // Impact burst — hidden until the bolt lands, then ring expands.
    this.burstMat = new THREE.MeshBasicMaterial({
      color: BOLT_COLOR,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const burstGeo = new THREE.RingGeometry(0.1, 0.3, 24);
    burstGeo.rotateX(-Math.PI / 2);
    this.burst = new THREE.Mesh(burstGeo, this.burstMat);
    this.burst.visible = false;
    group.add(this.burst);

    // Snapshot the launch point (caster's off-hand / chest height) at spawn.
    // The base layer has already populated root.position with the caster's
    // current world position, so that's a good starting point — plus a
    // chest-height offset.
    this.caster.getWorldPosition(this.start);
    this.start.y += 1.35;

    return group;
  }

  updateEffect(t: number, _dt: number): void {
    if (!this.root) return;

    // Override the base layer's auto-anchor — we drive position along the
    // caster→target line ourselves.
    this.root.position.set(0, 0, 0);

    // During windup the bolt hangs at the caster's off-hand; afterwards it
    // flies to the target. Remap t so 0 at launch → 1 at impact.
    const launch = this.launchT;
    const flightT = t < launch ? 0 : (t - launch) / (1 - launch);

    // Caster position (refreshed each frame so the bolt's origin tracks a
    // moving priest). Target is the snapshotted enemy point.
    const origin = new THREE.Vector3();
    this.caster.getWorldPosition(origin);
    origin.y += 1.35;

    const headPos = origin.clone().lerp(this.targetPos, flightT);
    this.bolt.position.copy(headPos);

    // Fade the bolt head in over the windup, full brightness during flight,
    // dim sharply past impact.
    const preLaunchFade = Math.min(1, t / launch);
    const postImpactFade = flightT >= 1 ? Math.max(0, 1 - (t - launch - (1 - launch)) / 0.18) : 1;
    this.boltMat.opacity = Math.min(preLaunchFade, postImpactFade);

    // Trail: each mote sits at a fraction behind the head along the flight
    // direction, so the tail grows out of the launch point as the head moves.
    const dir = new THREE.Vector3().subVectors(this.targetPos, origin);
    const flightLen = dir.length();
    if (flightLen > 1e-4) dir.multiplyScalar(1 / flightLen);
    for (const m of this.trail) {
      const tailT = Math.max(0, flightT - m.offset);
      const tailPos = origin.clone().lerp(this.targetPos, tailT);
      m.mesh.position.copy(tailPos);
      // Fade trail motes in/out with the bolt and with distance from head.
      m.mat.opacity =
        0.8 * this.boltMat.opacity * (1 - m.offset / 0.3) * (flightT > 0 ? 1 : 0);
    }

    // Impact ring: visible once the bolt arrives, expands and fades.
    if (flightT >= 1) {
      const impactT = Math.min(1, (t - launch - (1 - launch)) / 0.18);
      this.burst.visible = true;
      this.burst.position.copy(this.targetPos);
      this.burst.scale.setScalar(0.8 + 2.2 * impactT);
      this.burstMat.opacity = 0.9 * (1 - impactT);
    } else {
      this.burst.visible = false;
    }
  }
}
