import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';
import { applyCityWeathering } from './CityWeathering';
import { civicFallback } from './CityCivicFallback';
import { citadelDecorationFallback } from './CityCitadelFallback';
const palettes = new WeakMap<AssetLoader, Map<string, THREE.Material>>();
export const CITY_LOD_DISTANCES = [0, 55, 110] as const;
/** The authored kit uses the same material definitions in every GLB. Intern them
* per loader so repeated image references also share GPU texture allocation. */
export function shareCityMaterials(object: THREE.Object3D, loader: AssetLoader): void {
  let palette = palettes.get(loader);
  if (!palette) {
    palette = new Map();
    palettes.set(loader, palette);
  }
  object.traverse(node => {
    if (!(node instanceof THREE.Mesh))
      return;
    const intern = (material: THREE.Material) => {
      if (!material.name) return material;
      const existing = palette!.get(material.name);
      if (existing)
        return existing;
      for (const value of Object.values(material))
        if (value instanceof THREE.Texture)
          value.anisotropy = 8;
      if (material instanceof THREE.MeshStandardMaterial && !material.name.includes('glass')) applyCityWeathering(material);
      // Authored flagstone floors sit on the terrain's walk height. A depth bias
      // prevents coplanar flicker without separating the visible and walkable floor.
      if (material.name === 'aegis_flagstone') {
        material.polygonOffset = true;
        material.polygonOffsetFactor = -1;
        material.polygonOffsetUnits = -1;
      }
      palette!.set(material.name, material);
      return material;
    };
    node.material = Array.isArray(node.material) ? node.material.map(intern) : intern(node.material);
  });
}
export function cityFallback(kind: string): THREE.Group {
  if (kind.startsWith('aegis_civic_') && kind !== 'aegis_civic_hall') return civicFallback(kind);
  const decoration = citadelDecorationFallback(kind);
  if (decoration) return decoration;
  const group = new THREE.Group();
  const stone = new THREE.MeshStandardMaterial({ color: 0x454743, roughness: .9 });
  const brick = new THREE.MeshStandardMaterial({ color: 0x663d30, roughness: .9 });
  const box = (w: number, h: number, d: number, x = 0, y = h / 2, z = 0) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), kind.includes('house') ? brick : stone);
    mesh.position.set(x, y, z);
    group.add(mesh);
  };
  if (kind === 'aegis_garden_linden' || kind === 'aegis_garden_cypress') {
    const cypress = kind.endsWith('cypress');
    box(.55, 4, .55);
    const crown = new THREE.Mesh(cypress ? new THREE.ConeGeometry(1.4, 7, 10)
      : new THREE.SphereGeometry(2.7, 12, 8), new THREE.MeshStandardMaterial({ color: 0x36582b, roughness: .9 }));
    crown.position.y = cypress ? 6.25 : 5.4;
    group.add(crown);
    return group;
  }
  if (kind.startsWith('aegis_flowerbed_')) {
    box(4, .38, 2);
    const flowers = new THREE.Mesh(new THREE.BoxGeometry(3.6, .35, 1.6),
      new THREE.MeshStandardMaterial({ color: kind.endsWith('roses') ? 0x873744 : 0x615580, roughness: .9 }));
    flowers.position.y = .55;
    group.add(flowers);
    return group;
  }
  if (kind === 'aegis_citadel') {
    box(72, .4, 62, 0, -.2, 18);
    for (const x of [-20.5,20.5]) box(31, 36, 1.4, x, 18, 48.3);
    box(10, 24, 1.4, 0, 24, 48.3);
    for (const x of [-21.5,21.5]) box(29, 36, 1.4, x, 18, -12.3);
    box(14, 30.6, 1.4, 0, 20.7, -12.3);
    for (const x of [-35.3,35.3]) box(1.4, 36, 62, x, 18, 18);
    box(75, 2, 65, 0, 36, 18);
    box(17, 32, 20, 0, 52, 18);
    const spire = (x: number, z: number, base: number, radius: number, height: number) => {
      const lantern = new THREE.Mesh(new THREE.CylinderGeometry(radius * .82, radius, height * .32, 8), stone);
      lantern.position.set(x, base + height * .16, z);
      group.add(lantern);
      const needle = new THREE.Mesh(new THREE.ConeGeometry(radius * .91, height * .68, 8), stone);
      needle.position.set(x, base + height * .66, z);
      group.add(needle);
    };
    spire(0, 18, 68, 8.7, 57);
    for (const x of [-44, 44]) for (const z of [-10, 46]) {
      box(11, 44, 11, x, 22, z);
      spire(x, z, 44, 5.65, z > 0 ? 34 : 43);
    }
    for (const x of [-31, -21, -11, 11, 21, 31]) spire(x, 50, 39, 1.35, Math.abs(x) === 21 ? 12 : 15);
    box(68, .4, 2, 0, 5.8, -10.7);
    for (const x of [-32,32]) box(6, .4, 60, x, 5.8, 18);
  }
  else if (kind === 'aegis_mountain_passage') {
    box(20, .4, 24, 0, -.2);
    for (const x of [-9.5,9.5]) box(1, 18, 24, x);
    box(20, 2, 24, 0, 19);
  }
  else if (kind === 'aegis_mountain_redoubt') {
    box(120, .4, 96, 0, -.2);
    for (const x of [-35,35]) box(50, 32, 1, x, 16, 47.5);
    box(20, 18, 1, 0, 23, 47.5);
    box(120, 32, 1, 0, 16, -47.5);
    for (const x of [-59.5,59.5]) {
      box(1, 32, 31, x, 16, 32.5);
      if (x > 0) box(1, 32, 55, x, 16, -20.5);
      else {
        box(1, 32, 33, x, 16, -9.5);
        box(1, 32, 14, x, 16, -41);
        box(1, 22, 8, x, 21, -30);
      }
      box(1, 22, 10, x, 21, 12);
    }
    for (const x of [-42,42]) for (const z of [-28,-8,28]) box(3, 32, 3, x, 16, z);
    for (const [a,b] of [[-60,-40],[-28,-9],[9,28],[40,60]]) box(b-a, 28, 1, (a+b)/2, 14, 4);
    box(120, 16, 1, 0, 20, 4);
    box(120, 2, 96, 0, 33);
  }
  else if (kind === 'aegis_mountain_vault') {
    box(48, .4, 84, 0, -.2);
    for (const z of [-41.5,41.5]) box(48, 20, 1, 0, 10, z);
    box(1, 20, 84, -23.5);
    for (const [z,depth] of [[32.5,19],[-3.5,33],[-35,14]]) box(1, 20, depth, 23.5, 10, z);
    for (const [z,depth] of [[18,10],[-24,8]]) box(1, 10, depth, 23.5, 15, z);
    for (const x of [-16,16]) for (const z of [-28,28]) box(3, 20, 3, x, 10, z);
    box(48, 2, 84, 0, 21);
  }
  else if (kind === 'aegis_mountain_seal') box(14, 14, 3.2);
  else if (kind.includes('bridge')) {
    const w = kind.endsWith('wide') ? 8 : 4;
    box(w, .4, 12, 0, -.2);
    box(.5, 1.3, 12, -w / 2);
    box(.5, 1.3, 12, w / 2);
  }
  else if (kind.endsWith('gatehouse') || kind.endsWith('water_gate')) {
    box(2, 10, 4, -6);
    box(2, 10, 4, 6);
    box(14, 2, 4, 0, 11);
  }
  else if ((kind.endsWith('wall') || kind.endsWith('wall_entry'))) {
    box(12, 12, 3);
    for (let x = -5; x <= 5; x += 2)
      box(1, 1, 3, x, 12.5);
  }
  else if (kind.endsWith('tower'))
    box(9, 12, 9);
  else if (kind.endsWith('embankment'))
    box(8, 3, .8, 0, -1.5);
  else if (kind.endsWith('railing'))
    box(8, .15, .15, 0, 1.3);
  else if (kind.endsWith('portcullis')) {
    for (let x = -4; x <= 4; x++)
      box(.18, 8, .3, x);
  }
  else if (kind.endsWith('paving'))
    box(4, .05, 4, 0, -.025);
  else if (kind.endsWith('lantern'))
    box(.18, 4, .18);
  else if (kind.endsWith('stairs')) {
    for (let i = 0; i < 24; i++)
      box(3, (i + 1) * .25, 1, 0, (i + 1) * .125, 11.5 - i);
  }
  else if (kind.endsWith('room')) {
    box(12, .2, 12, 0, -.1);
    box(12, 5, .3, 0, 2.5, -6);
    box(.3, 5, 12, -6);
    box(.3, 5, 12, 6);
    box(4.6, 5, .3, -3.7, 2.5, 6);
    box(4.6, 5, .3, 3.7, 2.5, 6);
  }
  else if (kind.endsWith('table') || kind.endsWith('altar') || kind.endsWith('stall'))
    box(3, 1.3, 2.6);
  else if (kind.endsWith('sign'))
    box(1.6, .8, .15, 0, 2.8);
  else {
    box(8, 8, 8);
    const roof = new THREE.Mesh(new THREE.ConeGeometry(6.5, 4, 4), stone);
    roof.position.y = 10;
    roof.rotation.y = Math.PI / 4;
    group.add(roof);
  }
  return group;
}
export async function architectureLods(base: THREE.Object3D, models: string[], kind: string, loader: AssetLoader): Promise<THREE.LOD> {
  const lod = new THREE.LOD();
  shareCityMaterials(base, loader);
  lod.addLevel(base, 0);
  for (const [i, model] of models.slice(0, 2).entries()) {
    const object = await loader.loadModel(model, () => cityFallback(kind));
    shareCityMaterials(object, loader);
    lod.addLevel(object, CITY_LOD_DISTANCES[i + 1], .12);
  }
  return lod;
}
