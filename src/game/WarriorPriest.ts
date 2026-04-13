/**
 * Detailed procedural mesh for the Empire Warrior Priest.
 *
 * Design goals (carbon-copy of WAR's Warrior Priest silhouette):
 *   — High-segment smooth curves via LatheGeometry / TorusGeometry.
 *   — Proper armor layering: chainmail under, plate over, cloth robe beneath.
 *   — Tapered torso (broad chest → narrow waist → flared tabard).
 *   — Correct metallic gold materials for trim, greater roughness on cloth.
 *   — Solar halo crown, Sigmar war hammer.
 *
 * This module is intentionally isolated from CharacterMeshes.ts so it can be
 * iterated without destabilising the other five races. The entry point is
 * buildWarriorPriest() which returns an Object3D whose feet sit at y = 0 and
 * head tops out ≈ 1.95 units — matching the empireBase() character scale.
 */
import * as THREE from 'three';

// ─── Shared materials ────────────────────────────────────────────────────────
// Created per-build (not cached) so independent characters can be recolored
// without polluting siblings.

export interface WarriorPriestPalette {
  /** Polished gold for trim, pauldron caps, halo crown, chest sigil. */
  gold: number;
  /** Darker "antiqued" gold for recessed relief. */
  goldDark: number;
  /** Dark blue-steel plate (breastplate, greaves, gauntlets). */
  steel: number;
  /** Chainmail rings (underlayer). */
  mail: number;
  /** Deep royal-blue robe / tabard fabric. */
  robe: number;
  /** Robe shadow tone for inner panels. */
  robeDark: number;
  /** Leather straps, belt. */
  leather: number;
  /** Bare skin (face, shaved scalp). */
  skin: number;
}

export const DEFAULT_PALETTE: WarriorPriestPalette = {
  gold:     0xd9a842,
  goldDark: 0x8a6018,
  steel:    0x3d3f48,
  mail:     0x555a64,
  robe:     0x1e2a5a,
  robeDark: 0x0f1636,
  leather:  0x3a2410,
  skin:     0xd4a478,
};

/** Polished gold — high metalness, low roughness, slight emissive sheen. */
function goldMat(hex: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: hex,
    metalness: 0.95,
    roughness: 0.28,
  });
}

/** Dark blue-steel — plate armor base. */
function steelMat(hex: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: hex,
    metalness: 0.85,
    roughness: 0.38,
  });
}

/** Chainmail — moderate metalness, high roughness for woven look. */
function mailMat(hex: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: hex,
    metalness: 0.6,
    roughness: 0.75,
  });
}

/** Fabric robe — non-metallic, high roughness. */
function clothMat(hex: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: hex,
    metalness: 0.0,
    roughness: 0.92,
  });
}

/** Leather strap / belt material. */
function leatherMat(hex: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: hex,
    metalness: 0.05,
    roughness: 0.88,
  });
}

/** Skin — subsurface-style warm tone. */
function skinMat(hex: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: hex,
    metalness: 0.0,
    roughness: 0.68,
  });
}

/** Bundle of all materials the Warrior Priest uses. */
export interface WarriorPriestMaterials {
  gold: THREE.MeshStandardMaterial;
  goldDark: THREE.MeshStandardMaterial;
  steel: THREE.MeshStandardMaterial;
  mail: THREE.MeshStandardMaterial;
  robe: THREE.MeshStandardMaterial;
  robeDark: THREE.MeshStandardMaterial;
  leather: THREE.MeshStandardMaterial;
  skin: THREE.MeshStandardMaterial;
}

function buildMaterials(p: WarriorPriestPalette): WarriorPriestMaterials {
  return {
    gold:     goldMat(p.gold),
    goldDark: goldMat(p.goldDark),
    steel:    steelMat(p.steel),
    mail:     mailMat(p.mail),
    robe:     clothMat(p.robe),
    robeDark: clothMat(p.robeDark),
    leather:  leatherMat(p.leather),
    skin:     skinMat(p.skin),
  };
}

// ─── Geometry helpers ────────────────────────────────────────────────────────

/** Wraps a mesh with castShadow/receiveShadow for every build call. */
function shadowed(m: THREE.Mesh): THREE.Mesh {
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

/**
 * Lathe a silhouette around the Y axis — produces a smooth revolved surface
 * with configurable radial segment count. Used for gorgets, halos, hammer
 * heads, etc.
 */
function lathe(
  profile: THREE.Vector2[],
  segments: number,
  mat: THREE.Material,
): THREE.Mesh {
  const g = new THREE.LatheGeometry(profile, segments);
  g.computeVertexNormals();
  return shadowed(new THREE.Mesh(g, mat));
}

/** Smooth high-segment cylinder. */
function smoothCyl(
  rt: number, rb: number, h: number, mat: THREE.Material,
  seg = 20,
): THREE.Mesh {
  return shadowed(new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat));
}

/** Smooth high-segment sphere. */
function smoothSph(r: number, mat: THREE.Material, seg = 24): THREE.Mesh {
  return shadowed(new THREE.Mesh(new THREE.SphereGeometry(r, seg, seg), mat));
}

/** Smooth torus — used for halo ring, belt loops, shoulder trim. */
function smoothTorus(
  radius: number, tube: number, mat: THREE.Material,
  radialSeg = 8, tubularSeg = 32,
): THREE.Mesh {
  return shadowed(
    new THREE.Mesh(new THREE.TorusGeometry(radius, tube, radialSeg, tubularSeg), mat),
  );
}

// ─── Lower body ──────────────────────────────────────────────────────────────

/**
 * Build a single leg (boot, greave, knee poleyn, thigh chainmail) at the given
 * horizontal sign (+1 = right side, -1 = left side). All meshes are added to
 * `parent` at absolute world-space coordinates (feet at y=0). The caller is
 * expected to re-parent these under a hip pivot so the leg can swing during
 * walk/run animations (see `buildWarriorPriestRigged`).
 */
function buildLeg(
  parent: THREE.Group,
  mats: WarriorPriestMaterials,
  side: 1 | -1,
): void {
  const sx = 0.16 * side;
  const tx = 0.14 * side;

  // ── Boot (y ≈ 0 → 0.35) ────────────────────────────────────────────────
  // Tapered profile: toe narrows, ankle widens — revolved via lathe.
  const bootProfile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.14, 0.00),
    new THREE.Vector2(0.16, 0.04),
    new THREE.Vector2(0.15, 0.14),
    new THREE.Vector2(0.13, 0.28),
    new THREE.Vector2(0.14, 0.34),
    new THREE.Vector2(0.00, 0.35),
  ];
  const boot = lathe(bootProfile, 20, mats.leather);
  boot.position.set(sx, 0, 0);
  parent.add(boot);
  // Gold ankle trim — thin torus sitting on top of the boot cuff.
  const cuff = smoothTorus(0.15, 0.022, mats.gold, 10, 24);
  cuff.rotation.x = Math.PI / 2;
  cuff.position.set(sx, 0.34, 0);
  parent.add(cuff);
  // Gold toe cap — small bevelled wedge for that ornate WAR silhouette.
  const toeCap = smoothSph(0.08, mats.gold, 16);
  toeCap.scale.set(1.0, 0.45, 1.4);
  toeCap.position.set(sx, 0.05, 0.10);
  parent.add(toeCap);

  // ── Greave (shin plate, y ≈ 0.35 → 0.85) ───────────────────────────────
  const greave = smoothCyl(0.14, 0.12, 0.48, mats.steel, 20);
  greave.position.set(sx, 0.60, 0);
  parent.add(greave);
  // Vertical gold ridge running up the shin (a thin raised band).
  const ridge = smoothCyl(0.015, 0.015, 0.46, mats.gold, 12);
  ridge.position.set(sx, 0.60, 0.125);
  parent.add(ridge);
  // Knee poleyn — domed gold cap with a gold edge torus.
  const poleyn = smoothSph(0.11, mats.gold, 20);
  poleyn.scale.set(1.0, 0.6, 1.1);
  poleyn.position.set(sx, 0.86, 0.05);
  parent.add(poleyn);

  // ── Thigh chainmail (y ≈ 0.82 → 1.10) ───────────────────────────────────
  // A short cylinder of mail peeking out between the tabard and greaves.
  const mail = smoothCyl(0.15, 0.16, 0.28, mats.mail, 20);
  mail.position.set(tx, 0.98, 0);
  parent.add(mail);
}

/**
 * Centered waist region — mail skirt, tabard panels, belt, and buckle.
 * These pieces stay attached to the root (they don't swing with the legs).
 */
function buildWaist(parent: THREE.Group, mats: WarriorPriestMaterials): void {
  // ── Chainmail skirt (conical drape under tabard, y ≈ 0.75 → 1.15) ──────
  // A single bell-shaped lathe — wider at hem, narrower at waist.
  const skirtProfile = [
    new THREE.Vector2(0.22, 0.00),   // waist top
    new THREE.Vector2(0.24, 0.10),
    new THREE.Vector2(0.28, 0.25),
    new THREE.Vector2(0.33, 0.38),   // hem
    new THREE.Vector2(0.00, 0.40),
  ];
  const mailSkirt = lathe(skirtProfile, 28, mats.mail);
  mailSkirt.position.set(0, 0.75, 0);
  parent.add(mailSkirt);

  // ── Long flowing robe (full-length skirt panels) ────────────────────────
  // Replaces a short kilt-style tabard — the WAR Warrior Priest reference
  // shows a long blue robe falling almost to the boots. Built as a bell-
  // shaped lathe so the fabric drapes evenly all the way around, plus a
  // decorated front fringe panel for the layered silhouette.
  const robeProfile = [
    new THREE.Vector2(0.26, 0.00),   // waist top
    new THREE.Vector2(0.28, 0.10),
    new THREE.Vector2(0.30, 0.30),
    new THREE.Vector2(0.34, 0.50),
    new THREE.Vector2(0.40, 0.70),
    new THREE.Vector2(0.46, 0.80),   // hem just above the boot cuff
    new THREE.Vector2(0.00, 0.80),
  ];
  const robe = lathe(robeProfile, 32, mats.robe);
  // Lathe Y grows upward; we want it draping downward from the waist.
  robe.scale.y = -1;
  robe.position.set(0, 1.10, 0);
  parent.add(robe);

  // Inner darker liner — peeks at the hem when the camera is low.
  const liner = lathe(robeProfile, 32, mats.robeDark);
  liner.scale.set(0.96, -1, 0.96);
  liner.position.set(0, 1.10, 0);
  parent.add(liner);

  // Front fringe panel — a narrow vertical strip sits proud of the robe
  // front, edged in gold. This is the decorated tabard-style panel visible
  // between the breastplate and the robe's hem.
  const frontPanelShape = new THREE.Shape();
  frontPanelShape.moveTo(-0.13, 0.00);
  frontPanelShape.lineTo( 0.13, 0.00);
  frontPanelShape.lineTo( 0.16, -0.40);
  frontPanelShape.lineTo( 0.18, -0.78);
  frontPanelShape.lineTo( 0.06, -0.92);   // pointed hem bevel
  frontPanelShape.lineTo(-0.06, -0.92);
  frontPanelShape.lineTo(-0.18, -0.78);
  frontPanelShape.lineTo(-0.16, -0.40);
  frontPanelShape.closePath();
  const frontPanelGeo = new THREE.ShapeGeometry(frontPanelShape, 16);
  const frontPanel = shadowed(new THREE.Mesh(frontPanelGeo, mats.robeDark));
  frontPanel.position.set(0, 1.08, 0.32);
  parent.add(frontPanel);

  // Gold edging along the front panel's hem — two short angled bands.
  for (const sx of [-0.12, 0.12]) {
    const trim = shadowed(new THREE.Mesh(
      new THREE.BoxGeometry(0.014, 0.28, 0.01), mats.gold,
    ));
    trim.rotation.z = sx > 0 ? -0.18 : 0.18;
    trim.position.set(sx, 0.85, 0.325);
    parent.add(trim);
  }
  // Small gold roundel at the centre of the front panel (decorative seal).
  const roundel = smoothTorus(0.04, 0.012, mats.gold, 8, 24);
  roundel.position.set(0, 0.66, 0.33);
  parent.add(roundel);
  const roundelInner = smoothSph(0.022, mats.goldDark, 14);
  roundelInner.position.set(0, 0.66, 0.34);
  parent.add(roundelInner);

  // Matching narrow back panel (darker, no gold trim).
  const backPanelGeo = new THREE.ShapeGeometry(frontPanelShape, 16);
  const backPanel = shadowed(new THREE.Mesh(backPanelGeo, mats.robeDark));
  backPanel.position.set(0, 1.08, -0.32);
  backPanel.rotation.y = Math.PI;
  parent.add(backPanel);

  // ── Belt (wraps waist, separates tabard from torso) ─────────────────────
  const belt = smoothTorus(0.28, 0.05, mats.leather, 10, 28);
  belt.rotation.x = Math.PI / 2;
  belt.position.set(0, 1.12, 0);
  parent.add(belt);
  // Gold belt buckle — square front plate with engraved Hammer-of-Sigmar.
  const buckle = shadowed(
    new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.10, 0.04), mats.gold),
  );
  buckle.position.set(0, 1.12, 0.27);
  parent.add(buckle);
  const buckleInset = shadowed(
    new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.06, 0.02), mats.goldDark),
  );
  buckleInset.position.set(0, 1.12, 0.29);
  parent.add(buckleInset);
}

// ─── Torso ───────────────────────────────────────────────────────────────────

/**
 * Tapered upper body — broad at the chest, pinched at the waist.
 * Layering (outer → inner):
 *   1. Gold-trimmed steel breastplate (front + back half-shells)
 *   2. Central chest sigil (Hammer of Sigmar cross) in polished gold
 *   3. Chainmail hauberk (short-sleeved) beneath the plate
 *   4. Gorget — high gold collar protecting the neck
 */
function buildTorso(parent: THREE.Group, mats: WarriorPriestMaterials): void {
  // The torso is built from lathes (radially symmetric) and then scaled
  // non-uniformly in X and Z so a real human body shape emerges: wider
  // across the shoulders than front-to-back, with a pinched waist and a
  // flared chest.
  const TORSO_WIDTH_SCALE = 1.20;  // X — broaden across shoulders
  const TORSO_DEPTH_SCALE = 0.70;  // Z — flatten front-to-back

  // ── Chainmail hauberk (under the breastplate) ───────────────────────────
  // Stronger hourglass taper — narrow waist, broad chest, with a
  // "trapezius shelf" at the top so the shoulders read as muscled rather
  // than a flat shelf cut.
  const mailProfile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.22, 0.00),   // waist (pinched in)
    new THREE.Vector2(0.26, 0.10),
    new THREE.Vector2(0.34, 0.22),
    new THREE.Vector2(0.40, 0.32),   // chest widest
    new THREE.Vector2(0.42, 0.40),   // upper chest / shoulder shelf
    new THREE.Vector2(0.34, 0.48),   // shoulder slope inward toward neck
    new THREE.Vector2(0.18, 0.54),   // trapezius rise toward neck
    new THREE.Vector2(0.00, 0.54),
  ];
  const mailTorso = lathe(mailProfile, 32, mats.mail);
  mailTorso.scale.set(TORSO_WIDTH_SCALE, 1.0, TORSO_DEPTH_SCALE);
  mailTorso.position.set(0, 1.08, 0);
  parent.add(mailTorso);

  // ── Breastplate — two half-shells (front + back) ────────────────────────
  // Same hourglass profile, same non-uniform scaling, sitting just outside
  // the mail. Pec relief + sternum groove + abdominal plate go on top for
  // anatomical structure.
  const shellProfile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.21, 0.02),   // waist
    new THREE.Vector2(0.26, 0.12),
    new THREE.Vector2(0.34, 0.24),
    new THREE.Vector2(0.39, 0.34),   // chest widest
    new THREE.Vector2(0.40, 0.40),
    new THREE.Vector2(0.32, 0.48),   // shoulder slope
    new THREE.Vector2(0.16, 0.52),
  ];
  // Front half — forward 180° of revolution.
  const frontShell = shadowed(new THREE.Mesh(
    new THREE.LatheGeometry(shellProfile, 28, -Math.PI / 2, Math.PI),
    mats.steel,
  ));
  frontShell.scale.set(TORSO_WIDTH_SCALE * 1.02, 1.0, TORSO_DEPTH_SCALE * 1.05);
  frontShell.position.set(0, 1.10, 0);
  parent.add(frontShell);
  // Back half — flatter (smaller Z scale) backplate.
  const backShell = shadowed(new THREE.Mesh(
    new THREE.LatheGeometry(shellProfile, 28, Math.PI / 2, Math.PI),
    mats.steel,
  ));
  backShell.scale.set(TORSO_WIDTH_SCALE * 1.02, 1.0, TORSO_DEPTH_SCALE * 0.85);
  backShell.position.set(0, 1.10, 0);
  parent.add(backShell);

  // Pectoral relief — two flattened domes giving the chest anatomical
  // structure rather than a smooth bowl. Sit just proud of the front shell.
  for (const sx of [-0.13, 0.13]) {
    const pec = smoothSph(0.13, mats.steel, 18);
    pec.scale.set(1.05, 0.85, 0.55);
    pec.position.set(sx, 1.42, 0.30);
    parent.add(pec);
  }
  // Sternum groove — a thin dark recessed band running between the pecs,
  // simulating the seam where the two halves of the breastplate meet.
  const sternum = shadowed(new THREE.Mesh(
    new THREE.BoxGeometry(0.012, 0.30, 0.02),
    new THREE.MeshStandardMaterial({
      color: 0x1a1c20, metalness: 0.6, roughness: 0.6,
    }),
  ));
  sternum.position.set(0, 1.34, 0.36);
  parent.add(sternum);

  // Abdominal plate — a smaller curved plate below the breastplate hem,
  // emphasising the waist pinch.
  const abdomenProfile = [
    new THREE.Vector2(0.20, 0.00),
    new THREE.Vector2(0.23, 0.04),
    new THREE.Vector2(0.22, 0.10),
    new THREE.Vector2(0.20, 0.14),
  ];
  const abdomen = shadowed(new THREE.Mesh(
    new THREE.LatheGeometry(abdomenProfile, 24, -Math.PI / 2, Math.PI),
    mats.steel,
  ));
  abdomen.scale.set(TORSO_WIDTH_SCALE * 0.95, 1.0, TORSO_DEPTH_SCALE * 1.0);
  abdomen.position.set(0, 1.04, 0);
  parent.add(abdomen);

  // ── Gold breastplate trim (top edge + lower hem) ────────────────────────
  // Scaled to match the wider/flatter torso silhouette established above.
  const topTrim = smoothTorus(0.30, 0.022, mats.gold, 10, 36);
  topTrim.rotation.x = Math.PI / 2;
  topTrim.scale.set(TORSO_WIDTH_SCALE * 1.05, TORSO_DEPTH_SCALE * 1.05, 1);
  topTrim.position.set(0, 1.50, 0);
  parent.add(topTrim);
  const waistTrim = smoothTorus(0.24, 0.028, mats.gold, 10, 36);
  waistTrim.rotation.x = Math.PI / 2;
  waistTrim.scale.set(TORSO_WIDTH_SCALE, TORSO_DEPTH_SCALE, 1);
  waistTrim.position.set(0, 1.11, 0);
  parent.add(waistTrim);

  // ── Central gold sigil: stylised Hammer of Sigmar (cross) ───────────────
  // Vertical bar.
  const sigilBar = shadowed(
    new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.26, 0.04), mats.gold),
  );
  sigilBar.position.set(0, 1.32, 0.36);
  parent.add(sigilBar);
  // Hammer head (horizontal crossbar).
  const sigilCross = shadowed(
    new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.07, 0.04), mats.gold),
  );
  sigilCross.position.set(0, 1.40, 0.36);
  parent.add(sigilCross);
  // Central boss — small domed gold stud.
  const sigilBoss = smoothSph(0.045, mats.goldDark, 16);
  sigilBoss.position.set(0, 1.36, 0.39);
  parent.add(sigilBoss);

  // ── Gorget (tall gold collar) ───────────────────────────────────────────
  // A short flared lathe sitting above the breastplate, covering the neck.
  const gorgetProfile = [
    new THREE.Vector2(0.15, 0.00),
    new THREE.Vector2(0.19, 0.04),
    new THREE.Vector2(0.18, 0.11),
    new THREE.Vector2(0.13, 0.16),
    new THREE.Vector2(0.11, 0.20),
  ];
  const gorget = lathe(gorgetProfile, 24, mats.gold);
  gorget.position.set(0, 1.55, 0);
  parent.add(gorget);
  // Gorget inner rim (darker gold) — adds depth to the collar lip.
  const gorgetRim = smoothTorus(0.12, 0.02, mats.goldDark, 10, 28);
  gorgetRim.rotation.x = Math.PI / 2;
  gorgetRim.position.set(0, 1.72, 0);
  parent.add(gorgetRim);
}

// ─── Arms ────────────────────────────────────────────────────────────────────

/**
 * Build a single arm (pauldron → upper arm → elbow → vambrace → gauntlet).
 * `sx` is the shoulder x-offset (±); the arm hangs straight down.
 *
 * The pauldron is a compound: a domed steel shell + a gold crested ridge
 * + a gold scalloped hem — all high-segment so the shoulder silhouette
 * reads smooth from any camera angle.
 */
function buildArm(
  parent: THREE.Group,
  mats: WarriorPriestMaterials,
  sx: number,
): void {
  const side = Math.sign(sx);

  // ── Pauldron (shoulder armor) ───────────────────────────────────────────
  // Dome — half-sphere with extra squash for the rounded WAR look.
  const pauldronDome = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.20, 24, 18, 0, Math.PI * 2, 0, Math.PI * 0.6),
    mats.steel,
  ));
  pauldronDome.scale.set(1.2, 0.95, 1.15);
  pauldronDome.position.set(sx, 1.48, 0);
  parent.add(pauldronDome);

  // Gold crest ridge running front-to-back along the pauldron top.
  const crest = smoothCyl(0.02, 0.02, 0.36, mats.gold, 12);
  crest.rotation.x = Math.PI / 2;
  crest.position.set(sx, 1.63, 0);
  parent.add(crest);

  // Gold scalloped hem — a thin torus along the pauldron's bottom edge.
  const hem = smoothTorus(0.22, 0.022, mats.gold, 10, 32);
  hem.rotation.x = Math.PI / 2;
  hem.position.set(sx, 1.42, 0);
  parent.add(hem);

  // Gold stud at the pauldron's apex (the characteristic WAR rivet boss).
  const stud = smoothSph(0.045, mats.gold, 16);
  stud.position.set(sx, 1.66, 0);
  parent.add(stud);

  // ── Upper arm (chainmail sleeve) ────────────────────────────────────────
  // Smooth cylinder, tapered slightly from shoulder to elbow.
  const upperArm = smoothCyl(0.095, 0.085, 0.38, mats.mail, 20);
  upperArm.position.set(sx, 1.24, 0);
  parent.add(upperArm);

  // ── Elbow couter (steel cap) ────────────────────────────────────────────
  const elbow = smoothSph(0.09, mats.steel, 18);
  elbow.scale.set(1.0, 0.75, 1.0);
  elbow.position.set(sx, 1.05, 0);
  parent.add(elbow);
  // Gold elbow spike — small conical accent pointing outward.
  const elbowSpike = shadowed(new THREE.Mesh(
    new THREE.ConeGeometry(0.04, 0.10, 12), mats.gold,
  ));
  elbowSpike.rotation.z = -side * (Math.PI / 2);
  elbowSpike.position.set(sx + side * 0.09, 1.05, 0);
  parent.add(elbowSpike);

  // ── Vambrace (forearm plate) ────────────────────────────────────────────
  // Lathed profile: fluted wrist cuff, tapering toward elbow.
  const vambraceProfile = [
    new THREE.Vector2(0.08, 0.00),   // wrist bottom
    new THREE.Vector2(0.10, 0.03),
    new THREE.Vector2(0.09, 0.10),
    new THREE.Vector2(0.085, 0.22),
    new THREE.Vector2(0.095, 0.32),  // elbow end
  ];
  const vambrace = lathe(vambraceProfile, 20, mats.steel);
  vambrace.position.set(sx, 0.72, 0);
  parent.add(vambrace);

  // Two gold bands (upper + lower) wrapping the vambrace.
  for (const dy of [0.05, 0.28]) {
    const band = smoothTorus(0.10, 0.015, mats.gold, 8, 24);
    band.rotation.x = Math.PI / 2;
    band.position.set(sx, 0.72 + dy, 0);
    parent.add(band);
  }

  // ── Gauntlet (hand) ─────────────────────────────────────────────────────
  // Steel knuckle dome + gold cuff + leather grip underneath.
  const gauntlet = smoothSph(0.09, mats.steel, 18);
  gauntlet.scale.set(1.0, 0.85, 1.15);
  gauntlet.position.set(sx, 0.66, 0);
  parent.add(gauntlet);
  // Gold knuckle ridges — three tiny spheres across the back of the hand.
  for (const dz of [-0.05, 0.0, 0.05]) {
    const knuckle = smoothSph(0.022, mats.gold, 12);
    knuckle.position.set(sx, 0.69, dz);
    parent.add(knuckle);
  }
  // Leather finger group — tapered cylinder for fingers held together.
  const fingers = smoothCyl(0.06, 0.05, 0.12, mats.leather, 14);
  fingers.position.set(sx, 0.58, 0.02);
  parent.add(fingers);
}

/** Shoulder anchor for the left arm pivot (world-space when priest is at rest). */
export const LEFT_SHOULDER = new THREE.Vector3(-0.42, 1.50, 0);
/** Shoulder anchor for the right arm pivot (world-space when priest is at rest). */
export const RIGHT_SHOULDER = new THREE.Vector3(0.42, 1.50, 0);
/** Hip anchor shared by both leg pivots (world-space when priest is at rest). */
export const HIP_ANCHOR = new THREE.Vector3(0, 1.10, 0);

// ─── Head + halo crown ──────────────────────────────────────────────────────

/**
 * Head, neck, beard, and the solar halo crown that is the Warrior Priest's
 * signature silhouette feature.
 *
 * The halo is constructed as a ring-plus-rays: a thin gold torus encircling
 * the crown, with twelve tapered spikes radiating outward like a sunburst.
 */
function buildHead(parent: THREE.Group, mats: WarriorPriestMaterials): void {
  // ── Neck (short mail column inside the gorget) ──────────────────────────
  const neck = smoothCyl(0.10, 0.10, 0.12, mats.skin, 16);
  neck.position.set(0, 1.68, 0);
  parent.add(neck);

  // ── Head (slightly elongated sphere) ────────────────────────────────────
  const head = smoothSph(0.18, mats.skin, 28);
  head.scale.set(0.95, 1.05, 1.0);
  head.position.set(0, 1.86, 0);
  parent.add(head);

  // ── Shaved scalp highlight — a darker crown cap for visual separation ───
  const scalp = shadowed(new THREE.Mesh(
    new THREE.SphereGeometry(0.182, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.45),
    new THREE.MeshStandardMaterial({
      color: 0xb8865e, metalness: 0, roughness: 0.85,
    }),
  ));
  scalp.position.set(0, 1.86, 0);
  parent.add(scalp);

  // ── Beard (short cropped) ───────────────────────────────────────────────
  // Dark brown lathed shape hugging the jawline.
  const beardMat = new THREE.MeshStandardMaterial({
    color: 0x3a2612, metalness: 0, roughness: 0.95,
  });
  const beardProfile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.12, 0.02),
    new THREE.Vector2(0.14, 0.08),
    new THREE.Vector2(0.13, 0.14),
    new THREE.Vector2(0.10, 0.18),
    new THREE.Vector2(0.00, 0.18),
  ];
  const beard = lathe(beardProfile, 20, beardMat);
  beard.position.set(0, 1.74, 0.04);
  parent.add(beard);

  // Moustache — a thin horizontal capsule across the upper lip.
  const mustache = shadowed(new THREE.Mesh(
    new THREE.CapsuleGeometry(0.025, 0.14, 4, 8), beardMat,
  ));
  mustache.rotation.z = Math.PI / 2;
  mustache.position.set(0, 1.82, 0.16);
  parent.add(mustache);

  // ── Cloth headband (sits under the halo, covering the brow) ────────────
  const headband = smoothTorus(0.185, 0.022, mats.robe, 10, 28);
  headband.rotation.x = Math.PI / 2;
  headband.position.set(0, 1.92, 0);
  parent.add(headband);

  // ── Solar halo crown ────────────────────────────────────────────────────
  // Main gold ring floating just above the crown of the head.
  const haloRing = smoothTorus(0.21, 0.018, mats.gold, 10, 40);
  haloRing.rotation.x = Math.PI / 2;
  haloRing.position.set(0, 2.00, 0);
  parent.add(haloRing);

  // Twelve radial spikes — thin cones evenly distributed around the ring.
  const spikeCount = 12;
  for (let i = 0; i < spikeCount; i++) {
    const angle = (i / spikeCount) * Math.PI * 2;
    // Alternate tall/short spikes for a sunburst rhythm.
    const len = i % 2 === 0 ? 0.12 : 0.08;
    const baseR = 0.22;
    const tipR  = baseR + len;
    const spike = shadowed(new THREE.Mesh(
      new THREE.ConeGeometry(0.022, len, 8), mats.gold,
    ));
    // Cone apex points along +Y by default. To aim it outward in the XZ
    // plane: rotate -90° around Z (apex now points along +X), then rotate
    // around Y by -angle to sweep the +X axis to the desired direction.
    spike.rotation.order = 'YXZ';
    spike.rotation.z = -Math.PI / 2;
    spike.rotation.y = -angle;
    // Position spike midpoint on the ring at the correct radial offset.
    const midR = (baseR + tipR) / 2;
    spike.position.set(
      Math.cos(angle) * midR,
      2.00,
      Math.sin(angle) * midR,
    );
    parent.add(spike);
  }

  // Halo backplate disc — a very thin cylinder behind the ring, giving the
  // halo a soft metallic "aura" when lit from behind.
  const halodisc = smoothCyl(0.19, 0.19, 0.01, mats.goldDark, 40);
  halodisc.position.set(0, 2.00, -0.005);
  halodisc.rotation.x = Math.PI / 2;
  parent.add(halodisc);
}

// ─── Hammer of Sigmar (the Warrior Priest's two-handed warhammer) ───────────

/**
 * Build the Hammer of Sigmar geometry into the supplied group. The hammer
 * head is a chunky steel rectangle with a gold Sigmarite cross on each
 * striking face. Local origin sits roughly at the right-hand grip — the
 * caller positions and orients the whole weapon (see `buildWarriorPriestRigged`,
 * which attaches the hammer under the right-arm pivot so it can swing).
 */
function buildHammerGeometry(hammer: THREE.Group, mats: WarriorPriestMaterials): void {
  // ── Haft (wrapped handle) ───────────────────────────────────────────────
  // Core wooden shaft.
  const shaftWood = new THREE.MeshStandardMaterial({
    color: 0x5a2a12, metalness: 0.0, roughness: 0.85,
  });
  const haft = smoothCyl(0.028, 0.030, 1.30, shaftWood, 16);
  haft.position.set(0, 0, 0);
  hammer.add(haft);

  // Leather grip wrap — darker strip covering the center 40% of the haft.
  const grip = smoothCyl(0.034, 0.034, 0.52, mats.leather, 16);
  grip.position.set(0, -0.10, 0);
  hammer.add(grip);

  // Gold ferrules (bottom cap + shaft-to-head collar + head bolster).
  for (const y of [-0.66, 0.50, 0.60]) {
    const ferr = smoothTorus(0.032, 0.010, mats.gold, 8, 20);
    ferr.rotation.x = Math.PI / 2;
    ferr.position.set(0, y, 0);
    hammer.add(ferr);
  }
  // Decorative gold pommel cap at the base of the haft.
  const pommel = smoothSph(0.045, mats.gold, 16);
  pommel.scale.set(1.0, 0.6, 1.0);
  pommel.position.set(0, -0.68, 0);
  hammer.add(pommel);

  // ── Hammer head (steel block with gold trim) ────────────────────────────
  const headBlock = shadowed(new THREE.Mesh(
    new THREE.BoxGeometry(0.22, 0.28, 0.18), mats.steel,
  ));
  headBlock.position.set(0, 0.72, 0);
  hammer.add(headBlock);

  // Gold end caps on the two striking faces.
  for (const sx of [-0.115, 0.115]) {
    const cap = shadowed(new THREE.Mesh(
      new THREE.BoxGeometry(0.03, 0.24, 0.16), mats.gold,
    ));
    cap.position.set(sx, 0.72, 0);
    hammer.add(cap);
  }

  // Sigmarite cross inset on each striking face — vertical + horizontal bars.
  for (const sx of [-0.13, 0.13]) {
    const vbar = shadowed(new THREE.Mesh(
      new THREE.BoxGeometry(0.01, 0.18, 0.03), mats.gold,
    ));
    vbar.position.set(sx, 0.72, 0);
    hammer.add(vbar);
    const hbar = shadowed(new THREE.Mesh(
      new THREE.BoxGeometry(0.01, 0.04, 0.11), mats.gold,
    ));
    hbar.position.set(sx, 0.76, 0);
    hammer.add(hbar);
  }

  // Gold top spike (small pyramid rising from the head).
  const topSpike = shadowed(new THREE.Mesh(
    new THREE.ConeGeometry(0.04, 0.12, 4), mats.gold,
  ));
  topSpike.position.set(0, 0.92, 0);
  hammer.add(topSpike);

  // Gold bottom fang — reversed cone pointing down from the hammer head,
  // giving the weapon that distinctive ornate Sigmarite silhouette.
  const bottomFang = shadowed(new THREE.Mesh(
    new THREE.ConeGeometry(0.05, 0.14, 4), mats.gold,
  ));
  bottomFang.rotation.x = Math.PI;
  bottomFang.position.set(0, 0.51, 0);
  hammer.add(bottomFang);
}

/**
 * Held-two-handed rest orientation for the Hammer of Sigmar. The haft lies
 * diagonally across the torso with the head to the upper-left and the pommel
 * to the lower-right — matching the classic Warrior Priest silhouette.
 * Animators interpolate away from this rest pose when swinging.
 */
export const HAMMER_REST_EULER = new THREE.Euler(0, -0.15, -Math.PI * 0.35);
/** World-space anchor for the hammer when the priest is in rest pose. */
export const HAMMER_REST_WORLD = new THREE.Vector3(0.22, 1.10, 0.30);

// ─── Rig & entry point ───────────────────────────────────────────────────────

/**
 * A rigged Warrior Priest — the root group plus named pivot sub-groups that
 * animators can rotate to produce walk/run/attack motion. The rest pose is
 * identical to `buildWarriorPriest()` (all rotations zero).
 *
 * Pivot anchors (world-space when priest is at rest):
 *   leftArm  @ (-0.42, 1.50, 0) — left shoulder
 *   rightArm @ ( 0.42, 1.50, 0) — right shoulder
 *   leftLeg  @ (   0, 1.10, 0) — hip (mirrored in Z/X via pivot contents)
 *   rightLeg @ (   0, 1.10, 0) — hip
 *   hammer   — child of rightArm, oriented diagonally across the body
 */
export interface WarriorPriestRig {
  root: THREE.Group;
  leftArm: THREE.Group;
  rightArm: THREE.Group;
  leftLeg: THREE.Group;
  rightLeg: THREE.Group;
  hammer: THREE.Group;
  /** Rest-pose local position of the hammer inside the right-arm pivot. */
  hammerRestPosition: THREE.Vector3;
  /** Rest-pose local rotation (Euler) of the hammer inside the right-arm pivot. */
  hammerRestEuler: THREE.Euler;
}

/**
 * Wraps an already-filled group so its children become pivot-local: each
 * child's position is shifted by `-worldPivot`, then the group itself is
 * placed at `worldPivot`. This preserves absolute world coords of every
 * child while introducing a single-point rotation axis at `worldPivot`.
 */
function pivotify(g: THREE.Group, worldPivot: THREE.Vector3): THREE.Group {
  for (const c of g.children) c.position.sub(worldPivot);
  g.position.copy(worldPivot);
  return g;
}

/** Build a detailed Warrior Priest and return its animation rig. */
export function buildWarriorPriestRigged(
  palette: WarriorPriestPalette = DEFAULT_PALETTE,
): WarriorPriestRig {
  const root = new THREE.Group();
  root.name = 'WarriorPriest';
  const mats = buildMaterials(palette);

  // Static (non-swinging) regions go straight onto the root.
  buildWaist(root, mats);
  buildTorso(root, mats);
  buildHead(root, mats);

  // Legs: each side built into its own pivot at the hip.
  const leftLeg = new THREE.Group();
  leftLeg.name = 'LeftLeg';
  buildLeg(leftLeg, mats, -1);
  pivotify(leftLeg, HIP_ANCHOR);
  root.add(leftLeg);

  const rightLeg = new THREE.Group();
  rightLeg.name = 'RightLeg';
  buildLeg(rightLeg, mats, 1);
  pivotify(rightLeg, HIP_ANCHOR);
  root.add(rightLeg);

  // Arms: each side built into its own shoulder pivot.
  const leftArm = new THREE.Group();
  leftArm.name = 'LeftArm';
  buildArm(leftArm, mats, LEFT_SHOULDER.x);
  pivotify(leftArm, LEFT_SHOULDER);
  root.add(leftArm);

  const rightArm = new THREE.Group();
  rightArm.name = 'RightArm';
  buildArm(rightArm, mats, RIGHT_SHOULDER.x);
  pivotify(rightArm, RIGHT_SHOULDER);
  root.add(rightArm);

  // Hammer: geometry built into its own group, parented to the right arm so
  // it follows shoulder rotation. Rest position is the classic held-across-body
  // diagonal — we translate world coords into right-arm-local space.
  const hammer = new THREE.Group();
  hammer.name = 'HammerOfSigmar';
  buildHammerGeometry(hammer, mats);
  const hammerRestPosition = HAMMER_REST_WORLD.clone().sub(RIGHT_SHOULDER);
  const hammerRestEuler = HAMMER_REST_EULER.clone();
  hammer.position.copy(hammerRestPosition);
  hammer.rotation.copy(hammerRestEuler);
  rightArm.add(hammer);

  return {
    root,
    leftArm,
    rightArm,
    leftLeg,
    rightLeg,
    hammer,
    hammerRestPosition,
    hammerRestEuler,
  };
}

/**
 * Legacy entry point — returns just the root group. Prefer
 * `buildWarriorPriestRigged()` when you need access to the rig for animation.
 */
export function buildWarriorPriest(
  palette: WarriorPriestPalette = DEFAULT_PALETTE,
): THREE.Group {
  return buildWarriorPriestRigged(palette).root;
}
