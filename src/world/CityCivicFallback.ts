import * as THREE from 'three';

/** Small, correctly sized stand-ins keep a missing civic GLB from becoming a
 * house-sized obstacle. Mounted pieces preserve the authored mounting origin. */
export function civicFallback(kind: string): THREE.Group {
  const group = new THREE.Group();
  const iron = new THREE.MeshStandardMaterial({ color: 0x28393d, metalness: .7, roughness: .4 });
  const brass = new THREE.MeshStandardMaterial({ color: 0xb28a46, metalness: .7, roughness: .4 });
  const teal = new THREE.MeshStandardMaterial({ color: 0x285e59, roughness: .4 });
  const glow = new THREE.MeshStandardMaterial({ color: 0xffcc78, emissive: 0xffa546, emissiveIntensity: 1.3 });
  const box = (w: number, h: number, d: number, x: number, y: number, z: number, material = iron) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
    mesh.position.set(x, y, z);
    group.add(mesh);
  };
  const lantern = (x: number, y: number, z: number) => {
    box(.4, .5, .4, x, y, z, glow);
    box(.55, .08, .55, x, y + .29, z, brass);
    box(.55, .08, .55, x, y - .29, z, brass);
  };
  if (kind === 'aegis_civic_streetlight') {
    box(.8, .2, .8, 0, .1, 0, brass);
    box(.15, 4.1, .15, 0, 2.15, 0);
    box(2.2, .1, .1, 0, 4.1, 0);
    for (const x of [-1.05, 1.05]) {
      box(.06, .5, .06, x, 3.85, 0);
      lantern(x, 3.25, 0);
    }
  } else if (kind === 'aegis_civic_wall_lantern') {
    box(.24, .7, .1, 0, .34, 0);
    box(.07, .07, .8, 0, .8, .4);
    lantern(0, .13, .73);
  } else if (kind.startsWith('aegis_civic_sign_')) {
    box(2.2, 1.52, .16, 0, 2.83, 0, teal);
    box(2.4, .12, .12, 0, 3.89, 0);
    for (const x of [-.77, .77]) box(.035, .3, .035, x, 3.72, 0, brass);
  } else if (kind === 'aegis_civic_relief') {
    box(2.6, 2.2, .2, 0, 1.1, 0, brass);
    box(2.35, 1.9, .1, 0, 1.12, .13, teal);
  } else if (kind === 'aegis_civic_bench') {
    box(2.8, .1, .8, 0, .53, 0, teal);
    box(2.8, .7, .12, 0, 1.1, -.4, teal);
    for (const x of [-1.12, 1.12]) box(.12, .5, .8, x, .25, 0);
  } else if (kind === 'aegis_civic_orrery') {
    box(1.2, 1.4, 1.2, 0, .7, 0, teal);
    for (const angle of [0, Math.PI / 2]) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(.85, .04, 4, 20), brass);
      ring.position.y = 2.36;
      ring.rotation.y = angle;
      group.add(ring);
    }
  } else if (kind === 'aegis_civic_waymarker') {
    box(.15, 3.5, .15, 0, 1.75, 0);
    for (let i = 0; i < 3; i++) box(1.64, .34, .13, 0, 2.9 - i * .44, .1, teal);
  }
  // Unused materials have no GPU allocation; retain only materials on meshes.
  const used = new Set<THREE.Material>();
  group.traverse(node => { if (node instanceof THREE.Mesh) used.add(node.material as THREE.Material); });
  for (const material of [iron, brass, teal, glow]) if (!used.has(material)) material.dispose();
  return group;
}
