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
