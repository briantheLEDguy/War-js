/**
 * Detailed procedural character meshes for each WAR race.
 * Used as fallbacks when .glb models are not present.
 */
import * as THREE from 'three';
import { buildWarriorPriest } from './WarriorPriest';
import { buildHumanoidFace } from './FaceBuilder';

// Shared materials (created once, reused)
const skinMat   = () => new THREE.MeshStandardMaterial({ color: 0xd4a875, roughness: 0.7 });
const darkSkin  = () => new THREE.MeshStandardMaterial({ color: 0x8a6040, roughness: 0.7 });
const greenSkin = () => new THREE.MeshStandardMaterial({ color: 0x3d6a2a, roughness: 0.8 });

function box(w: number, h: number, d: number, mat: THREE.Material): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.castShadow = true;
  return m;
}
function cyl(rt: number, rb: number, h: number, seg: number, mat: THREE.Material): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
  m.castShadow = true;
  return m;
}
function sph(r: number, mat: THREE.Material): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 10, 10), mat);
  m.castShadow = true;
  return m;
}
function cone(r: number, h: number, seg: number, mat: THREE.Material): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.ConeGeometry(r, h, seg), mat);
  m.castShadow = true;
  return m;
}

/** Adds a sword to the group at the right-hand position */
function addSword(group: THREE.Group, gripColor: number, bladeColor: number) {
  const grip = new THREE.MeshStandardMaterial({ color: gripColor, roughness: 0.9 });
  const blade = new THREE.MeshStandardMaterial({ color: bladeColor, metalness: 0.8, roughness: 0.3 });
  const guard = new THREE.MeshStandardMaterial({ color: 0xc8a030, metalness: 0.7, roughness: 0.4 });
  const h = cyl(0.04, 0.04, 0.4, 6, grip);
  h.position.set(0.55, 0.9, 0.1);
  const g = box(0.35, 0.06, 0.06, new THREE.MeshStandardMaterial({ color: 0xc8a030, metalness: 0.7 }));
  g.position.set(0.55, 1.1, 0.1);
  const b = box(0.06, 0.9, 0.04, blade);
  b.position.set(0.55, 1.6, 0.1);
  group.add(h, g, b);
}

/** Adds a staff to the group at the right-hand position */
function addStaff(group: THREE.Group, shaftColor: number, tipColor: number) {
  const shaft = cyl(0.04, 0.05, 2.2, 6, new THREE.MeshStandardMaterial({ color: shaftColor, roughness: 0.8 }));
  shaft.position.set(0.5, 1.1, 0.1);
  const tip = sph(0.12, new THREE.MeshStandardMaterial({ color: tipColor, emissive: tipColor, emissiveIntensity: 0.4, roughness: 0.3 }));
  tip.position.set(0.5, 2.25, 0.1);
  group.add(shaft, tip);
}

/** Adds a war hammer to the group */
function addHammer(group: THREE.Group) {
  const shaft = cyl(0.04, 0.05, 1.8, 6, new THREE.MeshStandardMaterial({ color: 0x4a2e10, roughness: 0.9 }));
  shaft.position.set(0.5, 1.0, 0.1);
  const head = box(0.2, 0.25, 0.18, new THREE.MeshStandardMaterial({ color: 0x8a8880, metalness: 0.5, roughness: 0.5 }));
  head.position.set(0.5, 1.95, 0.1);
  group.add(shaft, head);
}

/** Base armored humanoid — Empire / generic Order. Returns group height ~1.9 units. */
function empireBase(armorColor: number, trimColor: number): THREE.Group {
  const group = new THREE.Group();
  const armor  = new THREE.MeshStandardMaterial({ color: armorColor, metalness: 0.5, roughness: 0.5 });
  const trim   = new THREE.MeshStandardMaterial({ color: trimColor,  metalness: 0.7, roughness: 0.3 });
  const dark   = new THREE.MeshStandardMaterial({ color: 0x1a1a1a,   roughness: 0.9 });
  const skin   = skinMat();

  // Boots
  for (const sx of [-0.15, 0.15]) {
    const boot = cyl(0.11, 0.13, 0.44, 8, dark);
    boot.position.set(sx, 0.22, 0);
    group.add(boot);
  }
  // Greaves (shin armor)
  for (const sx of [-0.15, 0.15]) {
    const greave = box(0.17, 0.35, 0.17, armor);
    greave.position.set(sx, 0.57, 0);
    group.add(greave);
  }
  // Tassets (upper leg plates)
  for (const sx of [-0.15, 0.15]) {
    const tasset = box(0.19, 0.32, 0.19, armor);
    tasset.position.set(sx, 0.88, 0);
    group.add(tasset);
  }
  // Breastplate — wider at chest
  const chest = box(0.52, 0.55, 0.3, armor);
  chest.position.set(0, 1.2, 0);
  group.add(chest);
  // Belly / waist
  const waist = box(0.42, 0.22, 0.26, armor);
  waist.position.set(0, 0.96, 0);
  group.add(waist);
  // Belt trim
  const belt = box(0.48, 0.07, 0.28, trim);
  belt.position.set(0, 0.86, 0);
  group.add(belt);
  // Backplate
  const back = box(0.5, 0.52, 0.08, armor);
  back.position.set(0, 1.2, -0.12);
  group.add(back);
  // Pauldrons (shoulder armor)
  for (const sx of [-0.38, 0.38]) {
    const pauldron = sph(0.18, armor);
    pauldron.scale.set(1, 0.7, 1);
    pauldron.position.set(sx, 1.45, 0);
    group.add(pauldron);
    const pad = box(0.22, 0.08, 0.22, trim);
    pad.position.set(sx, 1.54, 0);
    group.add(pad);
  }
  // Upper arms
  for (const sx of [-0.38, 0.38]) {
    const arm = cyl(0.09, 0.1, 0.38, 8, armor);
    arm.position.set(sx, 1.22, 0);
    group.add(arm);
  }
  // Vambraces (forearm armor)
  for (const sx of [-0.38, 0.38]) {
    const vam = box(0.13, 0.32, 0.13, armor);
    vam.position.set(sx, 0.98, 0);
    group.add(vam);
  }
  // Neck — slightly tapered for realism.
  const neck = cyl(0.092, 0.106, 0.15, 12, skin);
  neck.position.set(0, 1.53, 0);
  group.add(neck);
  // Head sphere.
  const head = sph(0.19, skin);
  head.position.set(0, 1.76, 0);
  group.add(head);
  // Procedural face features (eyes, brows, nose, lips, ears, chin).
  // Warrior Priest uses its own detailed buildHead(); all other Empire careers
  // get the shared face here so face details are visible when the helmet is
  // removed or doesn't cover the full face.
  buildHumanoidFace(group, 0, 1.76, 0, 0.19, 0xd4a875);

  return group;
}

// ─── Public character factories ───────────────────────────────────────────────

/** Empire character — silver/red plate armor, longsword. */
export function empire(career?: string): THREE.Object3D {
  // Warrior Priest has a dedicated high-detail mesh — delegate to its module.
  if (career === 'Warrior Priest') {
    return buildWarriorPriest();
  }
  const g = empireBase(0x8a8a8e, 0xcc1010);
  const helmetMat = new THREE.MeshStandardMaterial({ color: 0x787880, metalness: 0.6, roughness: 0.4 });
  if (career === 'Bright Wizard') {
    // Red robes over armor, fire-tipped staff
    const robe = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.34, 0.7, 8),
      new THREE.MeshStandardMaterial({ color: 0xaa2208, roughness: 0.9 }));
    robe.position.set(0, 1.1, 0);
    robe.castShadow = true;
    g.add(robe);
    addStaff(g, 0x3a1808, 0xff6020);
    // Pointed hood
    const hood = cone(0.22, 0.4, 8, new THREE.MeshStandardMaterial({ color: 0x8a1a06, roughness: 0.9 }));
    hood.position.set(0, 1.97, 0);
    g.add(hood);
  } else if (career === 'Warrior Priest') {
    addHammer(g);
    const helm = new THREE.Mesh(new THREE.SphereGeometry(0.21, 10, 6, 0, Math.PI * 2, 0, Math.PI * 0.6), helmetMat);
    helm.position.set(0, 1.68, 0);
    helm.castShadow = true;
    g.add(helm);
  } else {
    // Knight / Witch Hunter — full helm + sword
    const helm = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 6, 0, Math.PI * 2, 0, Math.PI * 0.65), helmetMat);
    helm.position.set(0, 1.67, 0);
    helm.castShadow = true;
    g.add(helm);
    // Visor bar
    const visor = box(0.26, 0.05, 0.22, new THREE.MeshStandardMaterial({ color: 0x555560, metalness: 0.8 }));
    visor.position.set(0, 1.78, 0.1);
    g.add(visor);
    // Plume
    const plume = cyl(0.03, 0.01, 0.28, 6, new THREE.MeshStandardMaterial({ color: 0xcc1010 }));
    plume.position.set(0, 1.99, 0);
    g.add(plume);
    addSword(g, 0x5a3a10, 0xd0d0e0);
  }
  return g;
}

/** Dwarf — stocky build, rune-etched armor, axe. */
export function dwarf(career?: string): THREE.Object3D {
  const group = new THREE.Group();
  const armorMat = new THREE.MeshStandardMaterial({ color: 0x5a4a2a, metalness: 0.4, roughness: 0.6 });
  const runeMat  = new THREE.MeshStandardMaterial({ color: 0xd4a030, metalness: 0.6, roughness: 0.4 });
  const skin     = skinMat();

  // Stocky legs (shorter)
  for (const sx of [-0.14, 0.14]) {
    const leg = cyl(0.13, 0.14, 0.42, 8, armorMat);
    leg.position.set(sx, 0.56, 0);
    group.add(leg);
  }
  // Boots
  for (const sx of [-0.14, 0.14]) {
    const boot = cyl(0.13, 0.15, 0.36, 8, new THREE.MeshStandardMaterial({ color: 0x2a1a0a, roughness: 0.9 }));
    boot.position.set(sx, 0.18, 0);
    group.add(boot);
  }
  // Wide torso
  const torso = box(0.58, 0.58, 0.34, armorMat);
  torso.position.set(0, 1.08, 0);
  group.add(torso);
  // Belt rune trim
  const belt = box(0.56, 0.08, 0.32, runeMat);
  belt.position.set(0, 0.82, 0);
  group.add(belt);
  // Shoulders (big pauldrons)
  for (const sx of [-0.4, 0.4]) {
    const p = sph(0.2, armorMat);
    p.scale.set(1.1, 0.8, 1);
    p.position.set(sx, 1.32, 0);
    group.add(p);
    const trim = box(0.25, 0.1, 0.25, runeMat);
    trim.position.set(sx, 1.42, 0);
    group.add(trim);
  }
  // Arms
  for (const sx of [-0.4, 0.4]) {
    const arm = cyl(0.1, 0.11, 0.36, 8, armorMat);
    arm.position.set(sx, 1.1, 0);
    group.add(arm);
  }
  // Head (lower, stocky) with full procedural face.
  // Dwarves have ginger/auburn beards — pass beard: true so the two-layer
  // partial-arc lathe beard replaces the old cone.
  const head = sph(0.2, skin);
  head.position.set(0, 1.6, 0);
  group.add(head);
  buildHumanoidFace(group, 0, 1.6, 0, 0.20, 0xc8905a, {
    hairColor:  0xc87020,   // auburn brows
    beardColor: 0xb86018,   // slightly darker beard
    irisColor:  0x4a3820,   // dark hazel
    browColor:  0x9a6030,
    beard:      true,
  });
  // Helmet
  const helm = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 6, 0, Math.PI * 2, 0, Math.PI * 0.6), armorMat);
  helm.position.set(0, 1.54, 0);
  helm.castShadow = true;
  group.add(helm);
  // Axe
  const haft = cyl(0.04, 0.04, 1.4, 6, new THREE.MeshStandardMaterial({ color: 0x3a2010, roughness: 0.9 }));
  haft.position.set(0.5, 1.0, 0);
  group.add(haft);
  const blade = box(0.28, 0.35, 0.05, new THREE.MeshStandardMaterial({ color: 0x909090, metalness: 0.7, roughness: 0.3 }));
  blade.position.set(0.5, 1.75, 0);
  group.add(blade);

  return group;
}

/** High Elf — slender, silver/blue elegant armor, sword. */
export function highElf(career?: string): THREE.Object3D {
  const g = empireBase(0xc8d8e8, 0x4060a0);
  // Add pointed elf ears on top of the face already laid by empireBase.
  buildHumanoidFace(g, 0, 1.76, 0, 0.19, 0xe8d8c0, {
    elfEars:   true,
    irisColor: 0x3a5038,   // grey-green elven eyes
    hairColor: 0xe8d890,   // pale gold
    browColor: 0xb8a078,
  });
  // Tall pointed helmet
  const helm = cone(0.2, 0.55, 8, new THREE.MeshStandardMaterial({ color: 0xb8c8d8, metalness: 0.7, roughness: 0.3 }));
  helm.position.set(0, 1.88, 0);
  g.add(helm);
  addSword(g, 0xd0c080, 0xe8e8f0);
  return g;
}

/** Chaos — massive spiked black armor. */
export function chaos(career?: string): THREE.Object3D {
  const group = new THREE.Group();
  const chaosArmor = new THREE.MeshStandardMaterial({ color: 0x1a0808, metalness: 0.6, roughness: 0.5 });
  const spikesMat  = new THREE.MeshStandardMaterial({ color: 0x2e0808, metalness: 0.4, roughness: 0.7 });
  const glowMat    = new THREE.MeshStandardMaterial({ color: 0x800000, emissive: 0x500000, emissiveIntensity: 0.5, roughness: 0.4 });

  // Larger/heavier build
  for (const sx of [-0.18, 0.18]) {
    const leg = cyl(0.16, 0.18, 0.55, 8, chaosArmor);
    leg.position.set(sx, 0.61, 0);
    group.add(leg);
    const boot = cyl(0.15, 0.17, 0.42, 8, new THREE.MeshStandardMaterial({ color: 0x0a0808, roughness: 0.9 }));
    boot.position.set(sx, 0.21, 0);
    group.add(boot);
    // Knee spikes
    const kSpike = cone(0.06, 0.2, 6, spikesMat);
    kSpike.position.set(sx, 0.82, 0.12);
    group.add(kSpike);
  }
  // Wide imposing torso
  const torso = box(0.65, 0.65, 0.38, chaosArmor);
  torso.position.set(0, 1.25, 0);
  group.add(torso);
  // Chest rune glow
  const rune = box(0.12, 0.16, 0.04, glowMat);
  rune.position.set(0, 1.3, 0.2);
  group.add(rune);
  // Massive pauldrons with spikes
  for (const sx of [-0.5, 0.5]) {
    const p = sph(0.25, chaosArmor);
    p.scale.set(1.1, 0.9, 1);
    p.position.set(sx, 1.5, 0);
    group.add(p);
    for (const [dy, dz] of [[0.28, 0], [0.1, 0.2]]) {
      const sp = cone(0.06, 0.28, 6, spikesMat);
      sp.position.set(sx, 1.5 + dy, dz);
      group.add(sp);
    }
  }
  // Arms
  for (const sx of [-0.48, 0.48]) {
    const arm = cyl(0.12, 0.13, 0.42, 8, chaosArmor);
    arm.position.set(sx, 1.24, 0);
    group.add(arm);
  }
  // Horned helmet
  const helm = sph(0.26, chaosArmor);
  helm.scale.set(1, 1.1, 1);
  helm.position.set(0, 1.72, 0);
  group.add(helm);
  for (const sx of [-0.2, 0.2]) {
    const horn = cone(0.07, 0.55, 6, spikesMat);
    horn.rotation.z = sx > 0 ? -0.4 : 0.4;
    horn.position.set(sx, 2.0, 0);
    group.add(horn);
  }
  // Chaos weapon (huge axe)
  const haft = cyl(0.05, 0.06, 1.8, 6, new THREE.MeshStandardMaterial({ color: 0x0a0808, roughness: 0.9 }));
  haft.position.set(0.6, 1.1, 0.1);
  group.add(haft);
  const axeB = box(0.4, 0.5, 0.06, new THREE.MeshStandardMaterial({ color: 0x3a0808, metalness: 0.7, roughness: 0.4 }));
  axeB.position.set(0.6, 2.1, 0.1);
  group.add(axeB);

  return group;
}

/** Greenskin — green hunched figure, crude weapon. */
export function greenskin(career?: string): THREE.Object3D {
  const group = new THREE.Group();
  const skinG  = greenSkin();
  const leatherMat = new THREE.MeshStandardMaterial({ color: 0x4a3010, roughness: 0.95 });
  const metalRough = new THREE.MeshStandardMaterial({ color: 0x6a6050, metalness: 0.2, roughness: 0.8 });

  // Hunched posture — shift upper body forward
  for (const sx of [-0.16, 0.16]) {
    const leg = cyl(0.14, 0.16, 0.52, 8, skinG);
    leg.position.set(sx, 0.56, 0);
    group.add(leg);
    const boot = cyl(0.14, 0.16, 0.36, 8, leatherMat);
    boot.position.set(sx, 0.18, 0);
    group.add(boot);
  }
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.55, 4, 8), skinG);
  torso.castShadow = true;
  torso.position.set(0, 1.15, 0.1); // leaning forward
  group.add(torso);
  // Crude leather chest piece
  const chest = box(0.45, 0.38, 0.12, leatherMat);
  chest.position.set(0, 1.2, 0.2);
  group.add(chest);
  // Big arms
  for (const sx of [-0.38, 0.38]) {
    const arm = cyl(0.12, 0.13, 0.44, 8, skinG);
    arm.position.set(sx, 1.15, 0.1);
    group.add(arm);
  }
  // Shoulders (rough leather)
  for (const sx of [-0.38, 0.38]) {
    const p = sph(0.17, leatherMat);
    p.position.set(sx, 1.4, 0.08);
    group.add(p);
  }
  // Big head — lower jaw protrudes (Orc face)
  const head = sph(0.24, skinG);
  head.scale.set(1, 0.95, 1.05);
  head.position.set(0, 1.68, 0.1);
  group.add(head);
  // Jaw / snout
  const jaw = box(0.2, 0.1, 0.14, skinG);
  jaw.position.set(0, 1.6, 0.24);
  group.add(jaw);
  // Tusks
  for (const sx of [-0.08, 0.08]) {
    const tusk = cone(0.03, 0.12, 5, new THREE.MeshStandardMaterial({ color: 0xd8c090 }));
    tusk.rotation.x = Math.PI;
    tusk.position.set(sx, 1.57, 0.28);
    group.add(tusk);
  }
  // Helmet (crude iron bowl)
  const helm = new THREE.Mesh(new THREE.SphereGeometry(0.26, 8, 5, 0, Math.PI * 2, 0, Math.PI * 0.55), metalRough);
  helm.position.set(0, 1.64, 0.06);
  helm.castShadow = true;
  group.add(helm);
  // Choppa (crude cleaver)
  const blade = box(0.32, 0.44, 0.06, metalRough);
  blade.position.set(0.55, 1.8, 0.1);
  group.add(blade);
  const haft = cyl(0.05, 0.05, 1.0, 6, leatherMat);
  haft.position.set(0.55, 1.2, 0.1);
  group.add(haft);

  return group;
}

/** Dark Elf — dark purple/black armor, daggers. */
export function darkElf(career?: string): THREE.Object3D {
  const g = empireBase(0x1a0a20, 0x8020a0);
  // Tall spired helmet
  const helm = cone(0.22, 0.6, 6, new THREE.MeshStandardMaterial({ color: 0x240830, metalness: 0.6, roughness: 0.4 }));
  helm.position.set(0, 1.9, 0);
  g.add(helm);
  // Dark cloakback
  const cloak = box(0.52, 0.9, 0.05, new THREE.MeshStandardMaterial({ color: 0x0a0010, roughness: 0.95, side: THREE.BackSide }));
  cloak.position.set(0, 1.2, -0.18);
  g.add(cloak);
  // Dagger (short blade)
  const dagger = box(0.04, 0.55, 0.04, new THREE.MeshStandardMaterial({ color: 0xc0b0d0, metalness: 0.9, roughness: 0.2 }));
  dagger.position.set(0.52, 1.4, 0.1);
  g.add(dagger);
  return g;
}

/** Main entry — pick mesh by race and optional career. */
export function buildCharacterMesh(race: string, career?: string): THREE.Object3D {
  switch (race) {
    case 'empire':    return empire(career);
    case 'dwarf':     return dwarf(career);
    case 'high_elf':  return highElf(career);
    case 'chaos':     return chaos(career);
    case 'greenskin': return greenskin(career);
    case 'dark_elf':  return darkElf(career);
    default:          return empire();
  }
}
