/**
 * Reusable procedural face geometry for any humanoid head sphere.
 *
 * All internal offsets are expressed in "WP-baseline" coordinates: a sphere
 * of radius 0.18 centred at the origin.  To apply to any other head, every
 * offset is multiplied by  s = radius / 0.18  and then shifted to the actual
 * world-space centre (cx, cy, cz).  This preserves the z-clearance maths
 * that keep features outside the sphere surface regardless of head size.
 *
 * Usage
 * -----
 *   buildHumanoidFace(group, cx, cy, cz, radius, skinHex, options);
 *
 * The Warrior Priest keeps its own bespoke buildHead() for full art-direction
 * control (halo, headband, WP-specific beard layers, etc.).  This module
 * targets all other careers that show a bare humanoid face.
 */

import * as THREE from 'three';

// ─── Internal helpers ────────────────────────────────────────────────────────

function fm(geo: THREE.BufferGeometry, mat: THREE.Material): THREE.Mesh {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function fsph(r: number, mat: THREE.Material, seg = 14): THREE.Mesh {
  return fm(new THREE.SphereGeometry(r, seg, seg), mat);
}

function fcaps(r: number, len: number, mat: THREE.Material, seg = 4): THREE.Mesh {
  return fm(new THREE.CapsuleGeometry(r, len, seg, 10), mat);
}

function fcyl(rt: number, rb: number, h: number, mat: THREE.Material, seg = 12): THREE.Mesh {
  return fm(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
}

// ─── Public API ──────────────────────────────────────────────────────────────

export interface FaceOptions {
  /** Iris colour — default dark forest green. */
  irisColor?: number;
  /** Eyebrow + beard hair colour — default very dark brown. */
  hairColor?: number;
  /** Brow-ridge darker skin tone — default warm shadow. */
  browColor?: number;
  /** Lip colour — default muted brick red. */
  lipColor?: number;
  /** When true, add a two-layer partial-arc beard. */
  beard?: boolean;
  /** Override beard colour independently of hairColor. */
  beardColor?: number;
  /** Add pointed elf ears instead of round human ears. Default false. */
  elfEars?: boolean;
}

/**
 * Attach procedural facial features to any humanoid head sphere.
 *
 * @param parent   THREE.Group the geometry is added to.
 * @param cx/cy/cz World-space centre of the head sphere.
 * @param r        Sphere radius.
 * @param skinColor Skin hex colour (used for most flesh-tone geometry).
 * @param opts     Optional colour and feature overrides.
 */
export function buildHumanoidFace(
  parent: THREE.Group,
  cx: number,
  cy: number,
  cz: number,
  r: number,
  skinColor: number,
  opts: FaceOptions = {},
): void {
  const {
    irisColor  = 0x243820,
    hairColor  = 0x2a1c0a,
    browColor  = 0xa07550,
    lipColor   = 0x8a3428,
    beard      = false,
    elfEars    = false,
  } = opts;
  const beardColor = opts.beardColor ?? hairColor;

  // Scale relative to the WP-baseline radius.
  const s = r / 0.18;

  // Position helper: dx/dy/dz in WP-local space → world space.
  const wp = (dx: number, dy: number, dz: number): THREE.Vector3 =>
    new THREE.Vector3(cx + dx * s, cy + dy * s, cz + dz * s);

  // ── Materials ──────────────────────────────────────────────────────────────

  const skinMat = new THREE.MeshStandardMaterial({
    color: skinColor, metalness: 0.0, roughness: 0.68,
  });
  const browMat = new THREE.MeshStandardMaterial({
    color: browColor, metalness: 0.0, roughness: 0.85,
  });
  const hairMat = new THREE.MeshStandardMaterial({
    color: hairColor, metalness: 0.0, roughness: 0.95,
  });
  const scleraMat = new THREE.MeshStandardMaterial({
    color: 0xece6d8, metalness: 0.0, roughness: 0.42,
  });
  const irisMat = new THREE.MeshStandardMaterial({
    color: irisColor, metalness: 0.0, roughness: 0.50,
  });
  const pupilMat = new THREE.MeshStandardMaterial({
    color: 0x060404, metalness: 0.0, roughness: 0.60,
  });
  const eyelidMat = new THREE.MeshStandardMaterial({
    // eyelid is slightly darker than face skin
    color: new THREE.Color(skinColor).multiplyScalar(0.80).getHex(),
    metalness: 0.0, roughness: 0.78,
  });
  const lowerLidMat = new THREE.MeshStandardMaterial({
    color: 0x8a5c38, metalness: 0.0, roughness: 0.82,
  });
  const lipMat = new THREE.MeshStandardMaterial({
    color: lipColor, metalness: 0.0, roughness: 0.80,
  });
  const mouthLineMat = new THREE.MeshStandardMaterial({
    color: 0x200a08, metalness: 0.0, roughness: 0.92,
  });
  const nostrilMat = new THREE.MeshStandardMaterial({
    color: 0x6e3422, metalness: 0.0, roughness: 0.88,
  });
  const earInnerMat = new THREE.MeshStandardMaterial({
    color: 0x7a4228, metalness: 0.0, roughness: 0.88,
  });

  // ── Brow ridge ─────────────────────────────────────────────────────────────
  // Two capsule halves, each with a slight inward tilt.
  // dy = +0.082 → above the head equator; dz = 0.174 clears the sphere surface.
  for (const [dx, tiltY] of [[-0.045, 0.12], [0.045, -0.12]] as [number, number][]) {
    const brow = fcaps(0.015 * s, 0.074 * s, browMat);
    brow.rotation.z = Math.PI / 2;
    brow.rotation.y = tiltY;
    brow.position.copy(wp(dx, 0.082, 0.174));
    parent.add(brow);
  }

  // ── Eyebrows ────────────────────────────────────────────────────────────────
  for (const [dx, tiltY] of [[-0.060, 0.18], [0.060, -0.18]] as [number, number][]) {
    const eyebrow = fcaps(0.014 * s, 0.060 * s, hairMat);
    eyebrow.rotation.z = Math.PI / 2;
    eyebrow.rotation.y = tiltY;
    eyebrow.position.copy(wp(dx, 0.088, 0.178));
    parent.add(eyebrow);
  }

  // ── Eyes ────────────────────────────────────────────────────────────────────
  // dy = +0.052, sphere surface at that offset: z ≈ 0.173.
  // Sclera centre at dz = 0.190 → 0.017 proud of the sphere.
  for (const dx of [-0.055, 0.055]) {
    // Sclera
    const sclera = fsph(0.028 * s, scleraMat, 18);
    sclera.scale.set(1.20, 0.86, 0.60);
    sclera.position.copy(wp(dx, 0.052, 0.190));
    parent.add(sclera);

    // Iris disc
    const irisDisc = fcyl(0.016 * s, 0.016 * s, 0.003 * s, irisMat, 16);
    irisDisc.rotation.x = Math.PI / 2;
    irisDisc.position.copy(wp(dx, 0.052, 0.207));
    parent.add(irisDisc);

    // Pupil disc
    const pupilDisc = fcyl(0.009 * s, 0.009 * s, 0.003 * s, pupilMat, 12);
    pupilDisc.rotation.x = Math.PI / 2;
    pupilDisc.position.copy(wp(dx, 0.052, 0.210));
    parent.add(pupilDisc);

    // Upper eyelid fold
    const eyelid = fsph(0.030 * s, eyelidMat, 14);
    eyelid.scale.set(1.14, 0.34, 0.48);
    eyelid.position.copy(wp(dx, 0.064, 0.194));
    parent.add(eyelid);

    // Lower eyelid shadow crescent
    const lowerLid = fsph(0.028 * s, lowerLidMat, 14);
    lowerLid.scale.set(1.12, 0.22, 0.42);
    lowerLid.position.copy(wp(dx, 0.040, 0.193));
    parent.add(lowerLid);
  }

  // ── Nose ────────────────────────────────────────────────────────────────────
  const nose = fcaps(0.022 * s, 0.060 * s, skinMat);
  nose.rotation.x = -0.15;
  nose.position.copy(wp(0, 0.020, 0.185));
  parent.add(nose);

  const noseTip = fsph(0.024 * s, skinMat, 14);
  noseTip.position.copy(wp(0, -0.010, 0.195));
  parent.add(noseTip);

  // Nostrils — at dy = -0.015 the sphere surface is ≈ 0.179; dz 0.193 clears it.
  for (const dx of [-0.027, 0.027]) {
    const nostril = fsph(0.013 * s, nostrilMat, 10);
    nostril.scale.set(0.78, 0.55, 0.55);
    nostril.position.copy(wp(dx, -0.015, 0.193));
    parent.add(nostril);
  }

  // ── Mouth ───────────────────────────────────────────────────────────────────
  // Seam between the lips.
  const mouthLine = fcaps(0.007 * s, 0.052 * s, mouthLineMat);
  mouthLine.rotation.z = Math.PI / 2;
  mouthLine.position.copy(wp(0, -0.059, 0.185));
  parent.add(mouthLine);

  // Upper lip — two lobes (cupid's bow).
  for (const dx of [-0.018, 0.018]) {
    const lobe = fcaps(0.010 * s, 0.022 * s, lipMat);
    lobe.rotation.z = Math.PI / 2;
    lobe.position.copy(wp(dx, -0.052, 0.184));
    parent.add(lobe);
  }

  // Lower lip — fuller single dome.
  const lowerLip = fcaps(0.013 * s, 0.050 * s, lipMat);
  lowerLip.rotation.z = Math.PI / 2;
  lowerLip.position.copy(wp(0, -0.067, 0.187));
  parent.add(lowerLip);

  // ── Chin ────────────────────────────────────────────────────────────────────
  // dy = -0.088 → sphere surface ≈ 0.158; dz 0.172 clears it.
  const chin = fsph(0.036 * s, skinMat, 14);
  chin.scale.set(0.72, 0.46, 0.38);
  chin.position.copy(wp(0, -0.088, 0.172));
  parent.add(chin);

  // Jaw-corner wideners — placed at the sides, not the front, to broaden
  // the lower-face silhouette without creating visible blobs.
  for (const dx of [-0.150, 0.150]) {
    const jaw = fsph(0.030 * s, skinMat, 12);
    jaw.scale.set(0.42, 0.62, 0.38);
    jaw.position.copy(wp(dx, -0.078, 0.052));
    parent.add(jaw);
  }

  // ── Ears ─────────────────────────────────────────────────────────────────────
  if (elfEars) {
    // Pointed high-elf ear: elongated cone tipped upward and outward.
    for (const dx of [-0.168, 0.168]) {
      const earBase = fsph(0.036 * s, skinMat, 14);
      earBase.scale.set(0.30, 0.62, 0.40);
      earBase.position.copy(wp(dx, 0.040, 0.018));
      parent.add(earBase);

      const earTip = fm(new THREE.ConeGeometry(0.012 * s, 0.060 * s, 8), skinMat);
      earTip.rotation.z = dx < 0 ? 1.0 : -1.0; // splay outward
      earTip.rotation.x = -0.30;
      earTip.position.copy(wp(dx * 1.04, 0.090, 0.008));
      parent.add(earTip);
    }
  } else {
    // Round human ear lobe.
    for (const dx of [-0.168, 0.168]) {
      const ear = fsph(0.038 * s, skinMat, 14);
      ear.scale.set(0.30, 0.60, 0.40);
      ear.position.copy(wp(dx, 0.040, 0.018));
      parent.add(ear);

      const earInner = fsph(0.022 * s, earInnerMat, 12);
      earInner.scale.set(0.40, 0.55, 0.35);
      earInner.position.copy(wp(dx * 0.98, 0.038, 0.008));
      parent.add(earInner);
    }
  }

  // ── Optional beard ──────────────────────────────────────────────────────────
  if (beard) {
    const beardMat = new THREE.MeshStandardMaterial({
      color: beardColor, metalness: 0, roughness: 0.95,
    });
    // Inner layer — close-cropped partial arc.
    const innerProfile = [
      new THREE.Vector2(0.000,         0.000        ),
      new THREE.Vector2(0.125 * s,     0.022 * s    ),
      new THREE.Vector2(0.148 * s,     0.090 * s    ),
      new THREE.Vector2(0.140 * s,     0.155 * s    ),
      new THREE.Vector2(0.112 * s,     0.210 * s    ),
      new THREE.Vector2(0.000,         0.210 * s    ),
    ];
    const innerGeo = new THREE.LatheGeometry(
      innerProfile, 24, -Math.PI * 0.56, Math.PI * 1.12,
    );
    const innerBeard = new THREE.Mesh(innerGeo, beardMat);
    innerBeard.castShadow = true;
    innerBeard.position.copy(wp(0, -0.130, 0.020));
    parent.add(innerBeard);

    // Outer layer — slightly darker, puffier, narrower arc.
    const beardMatOuter = new THREE.MeshStandardMaterial({
      color: new THREE.Color(beardColor).multiplyScalar(0.75).getHex(),
      metalness: 0, roughness: 0.97,
    });
    const outerProfile = [
      new THREE.Vector2(0.000,         0.000        ),
      new THREE.Vector2(0.110 * s,     0.020 * s    ),
      new THREE.Vector2(0.135 * s,     0.080 * s    ),
      new THREE.Vector2(0.128 * s,     0.148 * s    ),
      new THREE.Vector2(0.098 * s,     0.195 * s    ),
      new THREE.Vector2(0.000,         0.195 * s    ),
    ];
    const outerGeo = new THREE.LatheGeometry(
      outerProfile, 24, -Math.PI * 0.50, Math.PI * 1.00,
    );
    const outerBeard = new THREE.Mesh(outerGeo, beardMatOuter);
    outerBeard.castShadow = true;
    outerBeard.scale.set(1.06, 1.0, 1.08);
    outerBeard.position.copy(wp(0, -0.130, 0.040));
    parent.add(outerBeard);
  }
}
