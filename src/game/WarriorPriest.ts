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
 * Boots, greaves (shin plates), thigh chainmail, and the flowing tabard skirt.
 *
 * Layering (outer → inner):
 *   1. Blue cloth tabard — front & back panels, split at the sides
 *   2. Chainmail skirt — conical drape visible through the tabard split
 *   3. Steel greaves + gold knee poleyns from knee to ankle
 *   4. Gold-trimmed leather boots
 *
 * All meshes are added to `parent` at world-space coordinates (feet at y=0).
 */
function buildLowerBody(parent: THREE.Group, mats: WarriorPriestMaterials): void {
  // ── Boots (y ≈ 0 → 0.35) ────────────────────────────────────────────────
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
  for (const sx of [-0.16, 0.16]) {
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
  }

  // ── Greaves (shin plate, y ≈ 0.35 → 0.85) ───────────────────────────────
  // Slight taper: narrower at ankle, wider at knee — smooth cylinder.
  for (const sx of [-0.16, 0.16]) {
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
  }

  // ── Thigh chainmail (y ≈ 0.82 → 1.10) ───────────────────────────────────
  // A short cylinder of mail peeking out between the tabard and greaves.
  for (const sx of [-0.14, 0.14]) {
    const mail = smoothCyl(0.15, 0.16, 0.28, mats.mail, 20);
    mail.position.set(sx, 0.98, 0);
    parent.add(mail);
  }

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

  // ── Tabard front panel (blue cloth hanging over chainmail) ──────────────
  // Uses a plane slightly bent forward so the silhouette reads as fabric
  // rather than a flat slab. Built from a ShapeGeometry for crisp edges.
  const tabardShape = new THREE.Shape();
  tabardShape.moveTo(-0.19, 0.00);
  tabardShape.lineTo( 0.19, 0.00);   // waist
  tabardShape.lineTo( 0.24, -0.55);
  tabardShape.lineTo( 0.10, -0.72);  // bottom fringe bevel
  tabardShape.lineTo(-0.10, -0.72);
  tabardShape.lineTo(-0.24, -0.55);
  tabardShape.closePath();
  const tabardGeo = new THREE.ShapeGeometry(tabardShape, 12);
  const tabardFront = shadowed(new THREE.Mesh(tabardGeo, mats.robe));
  tabardFront.position.set(0, 1.08, 0.24);
  parent.add(tabardFront);
  // Matching back panel (same shape, flipped normal — slightly darker tone).
  const tabardBack = shadowed(new THREE.Mesh(tabardGeo.clone(), mats.robeDark));
  tabardBack.position.set(0, 1.08, -0.24);
  tabardBack.rotation.y = Math.PI;
  parent.add(tabardBack);

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
  // ── Chainmail hauberk (under the breastplate) ───────────────────────────
  // A subtle hourglass taper from chest → waist using a lathe silhouette.
  const mailProfile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.28, 0.00),   // waist
    new THREE.Vector2(0.32, 0.12),
    new THREE.Vector2(0.36, 0.26),   // chest widest
    new THREE.Vector2(0.34, 0.38),
    new THREE.Vector2(0.22, 0.48),   // shoulder
    new THREE.Vector2(0.00, 0.48),
  ];
  const mailTorso = lathe(mailProfile, 28, mats.mail);
  mailTorso.position.set(0, 1.12, 0);
  parent.add(mailTorso);

  // ── Breastplate — two half-shells (front + back) ────────────────────────
  // Carved from a sphere, scaled and clipped to produce a curved plate.
  // The WAR Warrior Priest silhouette has a distinctive bevelled chest
  // with a raised central boss; we approximate that with nested lathes.
  const frontShellProfile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.26, 0.02),
    new THREE.Vector2(0.32, 0.14),
    new THREE.Vector2(0.36, 0.26),
    new THREE.Vector2(0.34, 0.40),
    new THREE.Vector2(0.22, 0.48),
    new THREE.Vector2(0.00, 0.48),
  ];
  // Front half — render only the forward 180° of the revolution.
  const frontShell = shadowed(new THREE.Mesh(
    new THREE.LatheGeometry(frontShellProfile, 24, -Math.PI / 2, Math.PI),
    mats.steel,
  ));
  frontShell.scale.set(1.02, 1.0, 1.02);
  frontShell.position.set(0, 1.14, 0);
  parent.add(frontShell);
  // Back half — slightly flatter for the backplate.
  const backShell = shadowed(new THREE.Mesh(
    new THREE.LatheGeometry(frontShellProfile, 24, Math.PI / 2, Math.PI),
    mats.steel,
  ));
  backShell.scale.set(1.02, 1.0, 0.88);
  backShell.position.set(0, 1.14, 0);
  parent.add(backShell);

  // ── Gold breastplate trim (top edge + lower hem) ────────────────────────
  // Two thin tori hug the chest ridge and the waist seam.
  const topTrim = smoothTorus(0.30, 0.025, mats.gold, 10, 36);
  topTrim.rotation.x = Math.PI / 2;
  topTrim.position.set(0, 1.53, 0);
  parent.add(topTrim);
  const waistTrim = smoothTorus(0.28, 0.03, mats.gold, 10, 36);
  waistTrim.rotation.x = Math.PI / 2;
  waistTrim.position.set(0, 1.14, 0);
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

// ─── Entry point ─────────────────────────────────────────────────────────────

/** Build a detailed Warrior Priest. Feet at y=0, head ≈ y=1.95. */
export function buildWarriorPriest(
  palette: WarriorPriestPalette = DEFAULT_PALETTE,
): THREE.Group {
  const group = new THREE.Group();
  group.name = 'WarriorPriest';
  const mats = buildMaterials(palette);
  buildLowerBody(group, mats);
  buildTorso(group, mats);
  // Arms / head / weapon built in subsequent commits.
  return group;
}
