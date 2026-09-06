import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export const WORLD_LIFE_PROP_KINDS = [
  'life_crate_stack',
  'life_barrels',
  'life_handcart',
  'life_bench',
  'life_lantern',
  'life_clothesline',
  'life_signpost',
  'life_campfire',
  'life_supply_tent',
  'life_planter',
] as const;

export type WorldLifeActorKind = 'citizen' | 'guard' | 'deer' | 'bird';
type Point = [number, number, number];
type Palette = ReturnType<typeof createPalette>;

function createPalette() {
  // Resources belong to one returned object, so disposing one zone cannot affect another.
  const materials = new Map<string, THREE.MeshStandardMaterial>();
  return (color: number, emissive = false) => {
    const key = `${color}:${emissive}`;
    let material = materials.get(key);
    if (!material) {
      material = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.88,
        metalness: 0,
        flatShading: true,
        ...(emissive ? { emissive: color, emissiveIntensity: 1.35 } : {}),
      });
      materials.set(key, material);
    }
    return material;
  };
}

const WOOD = 0x745035;
const WOOD_LIGHT = 0xa07a50;
const WOOD_DARK = 0x46372d;
const IRON = 0x42484a;
const STONE = 0x787567;
const CLOTH = 0xc5b38b;

/** Merge static details per material; moving joints retain their own small batches. */
class Parts {
  private readonly geometries = new Map<THREE.Material, THREE.BufferGeometry[]>();

  constructor(private readonly palette: Palette) {}

  add(
    geometry: THREE.BufferGeometry,
    color: number,
    position: Point,
    rotation: Point = [0, 0, 0],
    scale: Point = [1, 1, 1],
    emissive = false,
  ) {
    const material = this.palette(color, emissive);
    const transform = new THREE.Matrix4().compose(
      new THREE.Vector3(...position),
      new THREE.Quaternion().setFromEuler(new THREE.Euler(...rotation)),
      new THREE.Vector3(...scale),
    );
    geometry.applyMatrix4(transform);
    const nonIndexed = geometry.index ? geometry.toNonIndexed() : geometry;
    if (nonIndexed !== geometry) geometry.dispose();
    const batch = this.geometries.get(material) ?? [];
    batch.push(nonIndexed);
    this.geometries.set(material, batch);
  }

  box(size: Point, position: Point, color: number, rotation: Point = [0, 0, 0]) {
    this.add(new THREE.BoxGeometry(...size), color, position, rotation);
  }

  cylinder(top: number, bottom: number, height: number, position: Point, color: number, rotation: Point = [0, 0, 0]) {
    this.add(new THREE.CylinderGeometry(top, bottom, height, 8), color, position, rotation);
  }

  ball(size: Point, position: Point, color: number) {
    this.add(new THREE.SphereGeometry(1, 8, 5), color, position, [0, 0, 0], size);
  }

  beam(start: Point, end: Point, width: number, color: number) {
    const a = new THREE.Vector3(...start);
    const b = new THREE.Vector3(...end);
    const direction = b.clone().sub(a);
    const geometry = new THREE.CylinderGeometry(width, width, direction.length(), 6);
    geometry.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize()));
    this.add(geometry, color, a.add(b).multiplyScalar(0.5).toArray() as Point);
  }

  finish(group: THREE.Group) {
    for (const [material, parts] of this.geometries) {
      const merged = mergeGeometries(parts, false);
      for (const geometry of parts) geometry.dispose();
      if (!merged) throw new Error('World life primitive geometry must have matching attributes');
      const mesh = new THREE.Mesh(merged, material);
      mesh.castShadow = (material as THREE.MeshStandardMaterial).emissive.getHex() === 0;
      mesh.receiveShadow = true;
      group.add(mesh);
    }
    this.geometries.clear();
  }
}

function crate(parts: Parts, x: number, y: number, z: number, size = 0.78) {
  parts.box([size, size, size], [x, y + size / 2, z], WOOD);
  for (const side of [-1, 1]) {
    for (const edge of [-1, 1]) {
      parts.box([size + 0.06, 0.09, 0.07], [x, y + size / 2 + edge * (size / 2 - 0.07), z + side * size / 2], WOOD_LIGHT);
      parts.box([0.09, size, 0.07], [x + edge * (size / 2 - 0.05), y + size / 2, z + side * size / 2], WOOD_LIGHT);
    }
    parts.box([0.075, size * 1.15, 0.065], [x, y + size / 2, z + side * (size / 2 + 0.015)], WOOD_LIGHT, [0, 0, -0.62]);
  }
  parts.box([0.09, 0.04, size], [x, y + size + 0.02, z], WOOD_LIGHT);
}

function barrel(parts: Parts, x: number, y: number, z: number, scale = 1) {
  parts.cylinder(0.29 * scale, 0.35 * scale, 0.4 * scale, [x, y + 0.61 * scale, z], WOOD);
  parts.cylinder(0.35 * scale, 0.29 * scale, 0.42 * scale, [x, y + 0.21 * scale, z], WOOD);
  for (const height of [0.13, 0.41, 0.69]) {
    const radius = (height === 0.41 ? 0.357 : 0.325) * scale;
    parts.cylinder(radius, radius, 0.055 * scale, [x, y + height * scale, z], IRON);
  }
  parts.cylinder(0.275 * scale, 0.275 * scale, 0.025 * scale, [x, y + 0.821 * scale, z], WOOD_LIGHT);
  parts.box([0.025 * scale, 0.014 * scale, 0.52 * scale], [x, y + 0.84 * scale, z], WOOD_DARK);
}

function hangingCloth(parent: THREE.Group, palette: Palette, name: string, at: Point, color: number, width: number, height: number) {
  const cloth = new THREE.Group();
  cloth.name = name;
  cloth.position.set(...at);
  cloth.userData.worldLifeAnimation = 'cloth';
  const parts = new Parts(palette);
  // Three folds provide a readable silhouette without a transparent, double-sided sheet.
  for (let fold = 0; fold < 3; fold++) {
    parts.box([width / 3 + 0.01, height, 0.025], [(fold - 1) * width / 3, -height / 2, 0], color, [0, fold % 2 ? 0.15 : -0.15, 0]);
  }
  parts.finish(cloth);
  parent.add(cloth);
}

/** Ready-made scenery remains available without downloads or model approval dependencies. */
export function buildWorldLifeProp(kind: string): THREE.Object3D | null {
  if (!(WORLD_LIFE_PROP_KINDS as readonly string[]).includes(kind)) return null;
  const root = new THREE.Group();
  root.name = kind;
  const palette = createPalette();
  const parts = new Parts(palette);

  switch (kind) {
    case 'life_crate_stack':
      crate(parts, -0.43, 0, 0.1);
      crate(parts, 0.45, 0, 0.05, 0.7);
      crate(parts, -0.36, 0.82, 0.1, 0.6);
      break;
    case 'life_barrels':
      barrel(parts, -0.35, 0, 0.15);
      barrel(parts, 0.33, 0, -0.02, 0.84);
      barrel(parts, 0, 0, 0.68, 0.7);
      break;
    case 'life_handcart': {
      parts.box([1.1, 0.13, 1.55], [0, 0.65, 0], WOOD_DARK);
      for (const side of [-1, 1]) {
        for (let plank = 0; plank < 3; plank++) {
          parts.box([0.08, 0.12, 1.6], [side * 0.54, 0.83 + plank * 0.16, 0], WOOD);
        }
        for (const end of [-0.69, 0.69]) {
          parts.box([0.11, 0.64, 0.1], [side * 0.54, 0.97, end], WOOD_LIGHT);
        }
        parts.box([0.1, 0.11, 1.85], [side * 0.43, 0.69, 1.3], WOOD, [-0.12, 0, 0]);
        parts.add(new THREE.TorusGeometry(0.42, 0.055, 4, 12), IRON, [side * 0.72, 0.475, -0.13], [0, Math.PI / 2, 0]);
        for (let spoke = 0; spoke < 4; spoke++) {
          parts.box([0.09, 0.81, 0.05], [side * 0.72, 0.475, -0.13], WOOD_LIGHT, [spoke * Math.PI / 4, 0, 0]);
        }
      }
      parts.beam([-0.8, 0.475, -0.13], [0.8, 0.475, -0.13], 0.08, IRON);
      parts.box([0.8, 0.08, 0.1], [0, 0.475, -0.13], WOOD_DARK);
      for (let plank = 0; plank < 3; plank++) parts.box([1.05, 0.12, 0.07], [0, 0.83 + plank * 0.16, -0.77], WOOD);
      crate(parts, 0.1, 0.725, -0.27, 0.58);
      parts.ball([0.26, 0.35, 0.3], [-0.2, 1.03, 0.39], CLOTH);
      break;
    }
    case 'life_bench':
      for (const x of [-0.72, 0.72]) {
        parts.box([0.16, 0.52, 0.58], [x, 0.26, 0], WOOD_DARK);
        parts.box([0.12, 1.06, 0.12], [x, 0.53, -0.23], WOOD);
      }
      for (const z of [-0.16, 0.02, 0.2]) parts.box([1.95, 0.1, 0.16], [0, 0.53, z], WOOD_LIGHT);
      for (const y of [0.79, 1.0]) parts.box([1.98, 0.16, 0.09], [0, y, -0.25], WOOD_LIGHT);
      parts.box([1.45, 0.12, 0.12], [0, 0.22, 0], WOOD);
      break;
    case 'life_lantern':
      parts.cylinder(0.15, 0.26, 0.22, [0, 0.11, 0], STONE);
      parts.box([0.11, 2.4, 0.11], [0, 1.2, 0], WOOD_DARK);
      parts.box([0.72, 0.09, 0.1], [0.26, 2.37, 0], WOOD);
      parts.beam([0.03, 1.96, 0], [0.48, 2.33, 0], 0.032, IRON);
      parts.beam([0.5, 2.35, 0], [0.5, 2.13, 0], 0.025, IRON);
      parts.add(new THREE.BoxGeometry(0.24, 0.34, 0.24), 0xffc96b, [0.5, 1.94, 0], [0, 0, 0], [1, 1, 1], true);
      for (const x of [0.35, 0.65]) for (const z of [-0.15, 0.15]) parts.box([0.04, 0.39, 0.04], [x, 1.94, z], IRON);
      parts.box([0.36, 0.07, 0.36], [0.5, 1.73, 0], IRON);
      parts.cylinder(0, 0.28, 0.17, [0.5, 2.19, 0], IRON);
      break;
    case 'life_clothesline':
      for (const x of [-1.65, 1.65]) {
        parts.cylinder(0.05, 0.07, 2.25, [x, 1.125, 0], WOOD);
        parts.box([0.1, 0.1, 0.4], [x, 2.2, 0], WOOD_LIGHT);
      }
      parts.beam([-1.65, 2.16, 0], [0, 2.04, 0], 0.015, WOOD_DARK);
      parts.beam([0, 2.04, 0], [1.65, 2.16, 0], 0.015, WOOD_DARK);
      [-0.98, 0, 1.02].forEach((x, i) => {
        const y = 2.04 + Math.abs(x) * 0.073;
        hangingCloth(root, palette, `cloth-${i}`, [x, y, 0], [CLOTH, 0x718a8e, 0xa67b61][i], 0.72, i === 1 ? 1.1 : 0.78);
        for (const offset of [-0.24, 0.24]) parts.box([0.03, 0.1, 0.05], [x + offset, y, 0], WOOD_LIGHT);
      });
      break;
    case 'life_signpost':
      parts.cylinder(0.09, 0.12, 2.1, [0, 1.05, 0], WOOD_DARK);
      parts.box([1.15, 0.27, 0.1], [0.2, 1.72, 0], WOOD_LIGHT);
      parts.box([0.87, 0.24, 0.1], [-0.15, 1.36, 0.01], WOOD);
      for (const y of [1.72, 1.36]) parts.ball([0.035, 0.035, 0.025], [0, y, 0.07], IRON);
      parts.box([0.19, 0.19, 0.095], [0.74, 1.72, 0], WOOD_LIGHT, [0, 0, Math.PI / 4]);
      parts.box([0.165, 0.165, 0.095], [-0.56, 1.36, 0.01], WOOD, [0, 0, Math.PI / 4]);
      break;
    case 'life_campfire': {
      for (let i = 0; i < 10; i++) {
        const angle = i * Math.PI / 5;
        parts.ball([0.2, 0.13, 0.17], [Math.sin(angle) * 0.62, 0.13, Math.cos(angle) * 0.62], STONE);
      }
      for (const angle of [-0.7, 0.7]) parts.cylinder(0.1, 0.12, 1.0, [0, 0.17, 0], WOOD_DARK, [Math.PI / 2, 0, angle]);
      const fire = new THREE.Group();
      fire.name = 'flame';
      fire.position.y = 0.23;
      fire.userData.worldLifeAnimation = 'flame';
      const flames = new Parts(palette);
      flames.add(new THREE.ConeGeometry(0.3, 0.7, 6), 0xf28c38, [0, 0.35, 0], [0, 0, 0.13], [1, 1, 1], true);
      flames.add(new THREE.ConeGeometry(0.18, 0.5, 5), 0xffd372, [0.1, 0.25, 0.13], [0, 0, -0.2], [1, 1, 1], true);
      flames.finish(fire);
      root.add(fire);
      break;
    }
    case 'life_supply_tent': {
      for (const z of [-1.35, 1.35]) {
        parts.cylinder(0.05, 0.07, 2.2, [0, 1.1, z], WOOD);
        for (const side of [-1, 1]) parts.beam([0, 2.19, z], [side * 1.47, 0.06, z], 0.035, WOOD);
      }
      parts.beam([0, 2.2, -1.43], [0, 2.2, 1.43], 0.055, WOOD_DARK);
      const roofLength = Math.hypot(1.42, 2.07);
      for (const side of [-1, 1]) {
        parts.box([roofLength, 0.05, 2.72], [side * 0.71, 1.17, 0], CLOTH, [0, 0, -side * Math.atan2(2.07, 1.42)]);
        parts.beam([side * 0.78, 1.2, -1.33], [side * 1.8, 0.07, -1.62], 0.013, WOOD_DARK);
        parts.cylinder(0.035, 0.045, 0.23, [side * 1.8, 0.115, -1.62], WOOD);
      }
      parts.box([2.0, 0.035, 2.0], [0, 0.02, -0.15], 0x685645);
      crate(parts, -0.35, 0.04, -0.55, 0.62);
      parts.ball([0.27, 0.18, 0.58], [0.35, 0.21, -0.3], 0x82907b);
      hangingCloth(root, palette, 'cloth-0', [0, 2.1, -1.34], 0xa39270, 0.6, 1.75);
      break;
    }
    case 'life_planter':
      parts.box([1.35, 0.52, 0.68], [0, 0.26, 0], WOOD);
      parts.box([1.2, 0.05, 0.55], [0, 0.535, 0], 0x433c2b);
      for (const z of [-0.35, 0.35]) parts.box([1.43, 0.08, 0.075], [0, 0.55, z], WOOD_LIGHT);
      for (const x of [-0.69, 0.69]) parts.box([0.075, 0.08, 0.7], [x, 0.55, 0], WOOD_LIGHT);
      for (let i = 0; i < 7; i++) {
        const x = (i % 4 - 1.5) * 0.27;
        const z = i < 4 ? -0.15 : 0.16;
        const height = 0.27 + (i % 3) * 0.07;
        parts.beam([x, 0.55, z], [x + 0.06, 0.55 + height, z], 0.019, 0x526546);
        parts.ball([0.15, 0.06, 0.1], [x, 0.68, z], 0x71844b);
        parts.ball([0.1, 0.07, 0.09], [x + 0.06, 0.55 + height, z], i % 2 ? 0xcb9c5e : 0xb5899d);
      }
      break;
  }
  parts.finish(root);
  root.userData.worldLifeKind = kind;
  return root;
}

function joint(root: THREE.Group, palette: Palette, name: string, position: Point, fill: (parts: Parts) => void) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(...position);
  const parts = new Parts(palette);
  fill(parts);
  parts.finish(group);
  root.add(group);
  return group;
}

/** Actors face +Z. Named joints use their attachment point as the animation pivot. */
export function buildWorldLifeActor(kind: WorldLifeActorKind, realm: 'aegis' | 'riftbound', variant: number): THREE.Group {
  const root = new THREE.Group();
  root.name = `life-${kind}`;
  root.userData.worldLifeKind = kind;
  const palette = createPalette();
  const parts = new Parts(palette);
  const index = Number.isFinite(variant) ? Math.abs(Math.trunc(variant)) % 4 : 0;

  if (kind === 'bird') {
    const feather = [0x7f8584, 0x6b727c, 0x8c7765, 0x66776b][index];
    parts.ball([0.09, 0.1, 0.19], [0, 0.18, 0], feather);
    parts.ball([0.075, 0.07, 0.075], [0, 0.28, 0.13], feather);
    parts.cylinder(0, 0.037, 0.11, [0, 0.27, 0.22], 0xc3a66d, [Math.PI / 2, 0, 0]);
    parts.box([0.12, 0.025, 0.16], [0, 0.15, -0.18], feather, [-0.3, 0, 0]);
    for (const side of [-1, 1]) {
      parts.beam([side * 0.035, 0.1, 0.02], [side * 0.035, 0.012, 0.04], 0.01, WOOD_DARK);
      parts.box([0.026, 0.018, 0.06], [side * 0.035, 0.009, 0.055], WOOD_DARK);
      parts.ball([0.011, 0.014, 0.012], [side * 0.064, 0.3, 0.16], 0x252524);
      joint(root, palette, side < 0 ? 'wing-left' : 'wing-right', [side * 0.06, 0.22, -0.02], wing => {
        wing.ball([0.17, 0.025, 0.11], [side * 0.13, 0, -0.04], feather);
        wing.box([0.2, 0.015, 0.09], [side * 0.24, -0.01, -0.1], feather, [0, side * 0.35, 0]);
      });
    }
  } else if (kind === 'deer') {
    const fur = [0x9c7952, 0x8a6c4c, 0xb28d60, 0x907b5b][index];
    parts.ball([0.3, 0.35, 0.65], [0, 0.99, 0], fur);
    parts.ball([0.2, 0.18, 0.52], [0, 0.85, 0.04], 0xc4ad82);
    parts.ball([0.09, 0.1, 0.21], [0, 1.1, -0.64], 0xc4ad82);
    for (const side of [-1, 1]) {
      for (const front of [true, false]) {
        const name = front ? (side < 0 ? 'leg-left' : 'leg-right') : (side < 0 ? 'leg-back-left' : 'leg-back-right');
        joint(root, palette, name, [side * 0.2, 0.91, front ? 0.4 : -0.4], leg => {
          leg.cylinder(0.07, 0.035, 0.79, [0, -0.395, 0], fur);
          leg.box([0.09, 0.12, 0.16], [0, -0.85, 0.025], WOOD_DARK);
        });
      }
    }
    joint(root, palette, 'head', [0, 1.03, 0.46], head => {
      head.cylinder(0.14, 0.2, 0.63, [0, 0.24, 0.1], fur, [0.4, 0, 0]);
      head.ball([0.15, 0.17, 0.28], [0, 0.55, 0.24], fur);
      head.ball([0.105, 0.08, 0.1], [0, 0.48, 0.47], WOOD_DARK);
      for (const side of [-1, 1]) {
        head.ball([0.075, 0.17, 0.055], [side * 0.15, 0.72, 0.17], fur);
        head.ball([0.014, 0.02, 0.02], [side * 0.14, 0.58, 0.32], 0x252524);
      }
    });
  } else {
    const guard = kind === 'guard';
    const clothing = realm === 'aegis' ? [0x62788c, 0x8b7658, 0x6d8366, 0x9a7967] : [0x835866, 0x776e86, 0x7b7855, 0x956d55];
    const cloth = guard ? (realm === 'aegis' ? 0x4c6983 : 0x743f51) : clothing[index];
    const skin = [0xd3ac86, 0x9a7251, 0xbe936f, 0x7f5b47][index];
    const metal = realm === 'aegis' ? 0x929b9a : 0x666875;
    parts.cylinder(0.24, 0.29, 0.59, [0, 1.075, 0], cloth);
    parts.cylinder(0.249, 0.26, 0.065, [0, 1.015, 0], WOOD_DARK);
    parts.box([0.09, 0.075, 0.045], [0, 1.015, 0.26], 0xc0a56d);
    parts.cylinder(0.075, 0.085, 0.1, [0, 1.41, 0], skin);
    parts.ball([0.14, 0.18, 0.13], [0, 1.61, 0], skin);
    parts.ball([0.045, 0.045, 0.065], [0, 1.59, 0.115], skin);
    if (guard) {
      parts.cylinder(0.245, 0.27, 0.27, [0, 1.23, 0], metal);
      parts.box([0.17, 0.36, 0.04], [0, 1.14, 0.255], cloth);
      parts.ball([0.153, 0.15, 0.147], [0, 1.68, -0.015], metal);
      parts.box([0.21, 0.045, 0.045], [0, 1.69, 0.136], metal);
    } else {
      parts.cylinder(0.16, 0.155, 0.1, [0, 1.755, -0.015], cloth);
      parts.cylinder(0.19, 0.19, 0.035, [0, 1.71, 0.008], cloth);
      parts.box([0.06, 0.54, 0.055], [0.02, 1.17, 0.245], WOOD_DARK, [0, 0, -0.53]);
      parts.box([0.23, 0.25, 0.12], [0.25, 0.92, 0.1], WOOD);
      parts.box([0.245, 0.09, 0.14], [0.25, 1.025, 0.11], WOOD_LIGHT);
    }
    for (const side of [-1, 1]) {
      joint(root, palette, side < 0 ? 'leg-left' : 'leg-right', [side * 0.135, 0.82, 0], leg => {
        leg.cylinder(0.105, 0.077, 0.65, [0, -0.325, 0], guard ? metal : 0x544d45);
        leg.box([0.18, 0.16, 0.29], [0, -0.74, 0.06], WOOD_DARK);
        leg.cylinder(0.089, 0.081, 0.19, [0, -0.66, 0], WOOD_DARK);
      });
      joint(root, palette, side < 0 ? 'arm-left' : 'arm-right', [side * 0.29, 1.335, 0], arm => {
        arm.cylinder(0.105, 0.073, 0.41, [side * 0.025, -0.19, 0], cloth, [0, 0, side * 0.12]);
        arm.ball([0.066, 0.085, 0.066], [side * 0.05, -0.44, 0.025], skin);
        if (guard) arm.ball([0.13, 0.09, 0.14], [0, -0.02, 0], metal);
        if (guard && side < 0) {
          arm.box([0.35, 0.49, 0.075], [-0.07, -0.32, 0.13], WOOD_DARK);
          arm.box([0.28, 0.42, 0.03], [-0.07, -0.32, 0.182], cloth);
          arm.ball([0.08, 0.08, 0.04], [-0.07, -0.3, 0.211], metal);
        }
      });
    }
  }
  parts.finish(root);
  return root;
}
