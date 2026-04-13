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

// ─── Entry point (scaffold — body parts added in subsequent commits) ────────

/** Build a detailed Warrior Priest. Feet at y=0, head ≈ y=1.95. */
export function buildWarriorPriest(
  palette: WarriorPriestPalette = DEFAULT_PALETTE,
): THREE.Group {
  const group = new THREE.Group();
  group.name = 'WarriorPriest';
  const mats = buildMaterials(palette);
  // Body parts are assembled by helpers introduced in subsequent commits.
  void mats;
  void lathe; void smoothCyl; void smoothSph; void smoothTorus;
  return group;
}
