import * as THREE from 'three';
import { AssetLoader } from './AssetLoader';
import { cityFallback, shareCityMaterials } from '../world/CityArchitecture';
import { startNpcIdleAnimation, type NpcState } from '../world/NpcSpawner';
import { aegisHouseResidentVariantFor } from '../data/modelOverrides';
import type {
  HouseInteriorVariant,
  InteractiveHousePortal,
  WorldCollider,
} from '../world/Props';

export interface HouseInteriorDefinition {
  variant: HouseInteriorVariant;
  width: number;
  depth: number;
  height: number;
  anchor: THREE.Vector3;
  group: THREE.Group;
  colliders: WorldCollider[];
  exitPortal: InteractiveHousePortal;
  occupants: NpcState[];
  spawn: { x: number; y: number; z: number; rotationY: number };
}

const WALL_THICKNESS = 0.28;
const DOOR_WIDTH = 2.1;

/**
 * Reusable furnished interiors live beyond the authored zone boundary and are
 * shown only while occupied. This keeps exterior towns lightweight while every
 * generated or GM-placed house can offer a consistent, collision-safe room.
 */
export class HouseInteriorRuntime {
  private interiors: Record<string, HouseInteriorDefinition>;
  private activeVariant: HouseInteriorVariant | null = null;
  private cityRoomsLoaded = false;
  private cityRoomsLoading: Promise<void> | null = null;
  private residentMixers = new Map<HouseInteriorVariant, THREE.AnimationMixer[]>();
  private disposed = false;

  constructor(private scene: THREE.Scene) {
    this.interiors = {
      small: createInterior('small', new THREE.Vector3(960, 0, 960), 8.8, 6.4, 4.0),
      large: createInterior('large', new THREE.Vector3(1010, 0, 960), 11.0, 7.8, 4.6),
    };
    for (const interior of Object.values(this.interiors)) {
      interior.group.visible = false;
      scene.add(interior.group);
    }
  }

  get isActive(): boolean {
    return this.activeVariant !== null;
  }

  async loadCityRooms(loader: AssetLoader): Promise<void> {
    if (this.cityRoomsLoaded || this.disposed) return;
    if (this.cityRoomsLoading) return this.cityRoomsLoading;
    this.cityRoomsLoading = this.loadCityRoomContents(loader);
    try { await this.cityRoomsLoading; }
    finally { this.cityRoomsLoading = null; }
  }

  private async loadCityRoomContents(loader: AssetLoader): Promise<void> {
    for (const [index, variant] of (['tavern', 'shop', 'chapel', 'civic'] as const).entries()) {
      if (this.disposed) return;
      const room = createInterior(variant, new THREE.Vector3(1060 + index * 50, 0, 960), 12, 12, 5);
      this.interiors[variant] = room;
      room.group.visible = false;
      this.scene.add(room.group);
      // Retain the exit, lights and occupants; authored meshes replace the old
      // domestic shell and furniture for these public-building variants.
      for (const child of [...room.group.children]) {
        if (child === room.exitPortal.object || child instanceof THREE.Light || child.name.includes('resident')) continue;
        room.group.remove(child);
        child.traverse(node => {
          if (node instanceof THREE.Mesh) { node.geometry.dispose(); }
        });
      }
      const shell = await loader.loadModel('prop_aegis_room.glb', () => cityFallback('aegis_room'));
      if (this.disposed) return;
      shareCityMaterials(shell, loader); room.group.add(shell);
      const furniture: Array<{kind:string;x:number;z:number}> = variant === 'chapel'
        ? [{kind:'altar',x:0,z:-4},{kind:'table',x:-3,z:0},{kind:'table',x:3,z:0}]
        : variant === 'shop' ? [{kind:'stall',x:-3,z:-2},{kind:'table',x:3,z:-3}]
        : variant === 'civic' ? [{kind:'table',x:0,z:-4},{kind:'table',x:-3,z:0},{kind:'table',x:3,z:0}]
        : [{kind:'table',x:-3,z:-3},{kind:'table',x:3,z:-3},{kind:'table',x:-3,z:1},{kind:'table',x:3,z:1}];
      for (const [i, item] of furniture.entries()) {
        const object=await loader.loadModel(`prop_aegis_${item.kind}.glb`,()=>cityFallback(`aegis_${item.kind}`));
        if (this.disposed) return;
        shareCityMaterials(object,loader); object.position.set(item.x,0,item.z);room.group.add(object);
        room.colliders.push({id:`${variant}-furniture-${i}`,x:room.anchor.x+item.x,z:room.anchor.z+item.z,width:3,depth:2.6,rotY:0,minY:0,maxY:1.7,blocksWhen:'always'});
      }
      room.occupants.forEach((npc,i)=>{
        npc.title = variant === 'tavern' ? 'Tavern Guest' : variant === 'chapel' ? 'Vigil Attendant' : variant === 'shop' ? 'Shop Assistant' : 'Civic Clerk';
        const person=room.group.getObjectByName(`${variant}-resident-${i+1}`);
        if(person) { person.position.set(i===0?-4.8:4.8,0,-4.8);npc.position.x=room.anchor.x+person.position.x;npc.position.z=room.anchor.z+person.position.z; }
      });
      room.exitPortal.label = 'Return to the city';
    }
    for (const room of Object.values(this.interiors)) {
      const mixers: THREE.AnimationMixer[] = [];
      this.residentMixers.set(room.variant, mixers);
      for (const [index, npc] of room.occupants.entries()) {
        const placeholder = room.group.getObjectByName(npc.id);
        if (!placeholder || this.disposed) return;
        const selection = aegisHouseResidentVariantFor(room.variant, index);
        const model = await loader.resolveCharacterModel(selection.profileKey) ?? selection.fallbackModel;
        if (this.disposed) return;
        const { object, animations } = await loader.loadModelFull(model, AssetLoader.primitives.humanoid);
        if (this.disposed) { releaseResidentSkeletons(object); return; }
        object.name = npc.id;
        object.position.copy(placeholder.position);
        object.rotation.copy(placeholder.rotation);
        // Revision4 bodies already carry their adult/child proportions and scale.
        object.traverse(node => { if (node instanceof THREE.Mesh) node.castShadow = true; });
        room.group.remove(placeholder);
        placeholder.traverse(node => {
          if (node instanceof THREE.Mesh) node.geometry.dispose();
        });
        room.group.add(object);
        const mixer = startNpcIdleAnimation(object, animations);
        if (mixer) mixers.push(mixer);
      }
    }
    this.cityRoomsLoaded = true;
  }

  update(dt: number): void {
    if (!this.activeVariant || this.disposed) return;
    for (const mixer of this.residentMixers.get(this.activeVariant) ?? []) mixer.update(dt);
  }

  get activeInterior(): HouseInteriorDefinition | null {
    return this.activeVariant ? this.interiors[this.activeVariant] : null;
  }

  /** Off-map rooms have their own floor; the city heightfield must not lift occupants. */
  getFloorHeightAt(x: number, z: number): number | null {
    const room = this.activeInterior;
    if (!room || Math.abs(x - room.anchor.x) > room.width / 2 + WALL_THICKNESS
      || Math.abs(z - room.anchor.z) > room.depth / 2 + WALL_THICKNESS) return null;
    return room.anchor.y;
  }

  enter(variant: HouseInteriorVariant): HouseInteriorDefinition {
    this.deactivate();
    const interior = this.interiors[variant] ?? this.interiors.small;
    interior.group.visible = true;
    this.activeVariant = interior.variant;
    return interior;
  }

  deactivate(): void {
    for (const interior of Object.values(this.interiors)) interior.group.visible = false;
    this.activeVariant = null;
  }

  getColliders(): WorldCollider[] {
    return this.activeInterior?.colliders ?? [];
  }

  getCameraColliders(): WorldCollider[] {
    return this.getColliders();
  }

  getExitPortal(): InteractiveHousePortal | null {
    return this.activeInterior?.exitPortal ?? null;
  }

  getOccupants(): NpcState[] {
    return this.activeInterior?.occupants ?? [];
  }

  dispose(scene: THREE.Scene): void {
    this.disposed = true;
    for (const mixers of this.residentMixers.values()) {
      for (const mixer of mixers) { mixer.stopAllAction(); mixer.uncacheRoot(mixer.getRoot()); }
    }
    this.residentMixers.clear();
    const releasedSkeletons = new Set<THREE.Skeleton>();
    for (const interior of Object.values(this.interiors)) {
      releaseResidentSkeletons(interior.group, releasedSkeletons);
      scene.remove(interior.group);
    }
    this.deactivate();
  }
}

/** Instance skeletons own bone textures; geometry/materials remain loader-owned. */
function releaseResidentSkeletons(root: THREE.Object3D, released = new Set<THREE.Skeleton>()): void {
  root.traverse(node => {
    if (node instanceof THREE.SkinnedMesh && !released.has(node.skeleton)) {
      released.add(node.skeleton);
      node.skeleton.dispose();
    }
  });
}

function createInterior(
  variant: HouseInteriorVariant,
  anchor: THREE.Vector3,
  width: number,
  depth: number,
  height: number,
): HouseInteriorDefinition {
  const group = new THREE.Group();
  group.name = `house-interior-${variant}`;
  group.position.copy(anchor);

  const plaster = material(0x514c43, 0.92);
  const timber = material(0x24170f, 0.84);
  const floorMat = material(0x35251a, 0.88);
  const stone = material(0x3d3b38, 0.95);
  const iron = material(0x171717, 0.55, 0.55);
  const cloth = material(variant === 'large' ? 0x49312b : 0x35404a, 0.9);

  addBox(group, 'plank-floor', [width, 0.2, depth], [0, -0.1, 0], floorMat);
  addBox(group, 'north-wall', [width, height, WALL_THICKNESS], [0, height / 2, -depth / 2], plaster);
  addBox(group, 'west-wall', [WALL_THICKNESS, height, depth], [-width / 2, height / 2, 0], plaster);
  addBox(group, 'east-wall', [WALL_THICKNESS, height, depth], [width / 2, height / 2, 0], plaster);
  const southSegment = (width - DOOR_WIDTH) / 2;
  addBox(group, 'south-wall-left', [southSegment, height, WALL_THICKNESS], [-(DOOR_WIDTH + southSegment) / 2, height / 2, depth / 2], plaster);
  addBox(group, 'south-wall-right', [southSegment, height, WALL_THICKNESS], [(DOOR_WIDTH + southSegment) / 2, height / 2, depth / 2], plaster);
  addBox(group, 'door-header', [DOOR_WIDTH, height - 2.75, WALL_THICKNESS], [0, 2.75 + (height - 2.75) / 2, depth / 2], timber);
  addBox(group, 'ceiling', [width, 0.18, depth], [0, height + 0.08, 0], timber);

  // Exposed structural beams make the room read as the same timber-built house.
  for (const x of [-width / 2 + 0.18, 0, width / 2 - 0.18]) {
    addBox(group, 'wall-post', [0.24, height, 0.24], [x, height / 2, -depth / 2 + 0.08], timber);
  }
  for (const z of [-depth * 0.28, depth * 0.28]) {
    addBox(group, 'ceiling-beam', [width, 0.24, 0.26], [0, height - 0.08, z], timber);
  }

  addHearth(group, -width / 2 + 0.65, -depth / 2 + 1.05, stone, iron);
  addTableSet(group, variant === 'large' ? 1.4 : 0.8, 0.2, timber);
  addBed(group, width / 2 - 1.35, -depth / 2 + 1.6, timber, cloth, variant === 'large');
  addShelves(group, -width / 2 + 0.48, 0.65, timber);
  addChest(group, width / 2 - 0.8, depth / 2 - 0.7, timber, iron);
  addRug(group, variant === 'large' ? -1.6 : -1.1, -0.0, variant === 'large' ? 3.2 : 2.5, cloth);

  if (variant === 'large') {
    addBox(group, 'room-divider', [0.2, 2.65, depth * 0.46], [2.1, 1.325, -0.7], timber);
    addBox(group, 'writing-desk', [2.2, 0.18, 0.85], [-2.9, 1.0, -2.6], timber);
  }

  const door = createDoor(DOOR_WIDTH * 0.88, 2.7, timber, iron);
  door.name = `${variant}-interior-exit-door`;
  door.position.set(0, 0, depth / 2 - 0.12);
  door.rotation.y = Math.PI;
  door.userData.housePortalId = `${variant}-interior-exit`;
  door.traverse((node) => { node.userData.housePortalId = `${variant}-interior-exit`; });
  group.add(door);

  const occupants = addOccupants(group, variant, width, depth, anchor);
  const warmLight = new THREE.PointLight(0xffb05a, variant === 'large' ? 65 : 48, 15, 1.8);
  warmLight.position.set(-width / 2 + 1.2, 2.2, -depth / 2 + 1.2);
  group.add(warmLight);
  const fillLight = new THREE.PointLight(0xffd3a0, 26, 12, 2);
  fillLight.position.set(width / 3, 2.8, depth / 4);
  group.add(fillLight);

  const colliders = buildRoomColliders(variant, anchor, width, depth, height);
  return {
    variant,
    width,
    depth,
    height,
    anchor,
    group,
    colliders,
    occupants,
    spawn: {
      x: anchor.x,
      y: 0,
      z: anchor.z + depth / 2 - 2.6,
      rotationY: Math.PI,
    },
    exitPortal: {
      id: `${variant}-interior-exit`,
      label: 'Leave House',
      object: door,
      interiorVariant: variant,
      maxDistance: 4.2,
      direction: 'exit',
    },
  };
}

function buildRoomColliders(
  variant: string,
  anchor: THREE.Vector3,
  width: number,
  depth: number,
  height: number,
): WorldCollider[] {
  const segment = (width - DOOR_WIDTH) / 2;
  const collider = (id: string, x: number, z: number, w: number, d: number): WorldCollider => ({
    id: `${variant}-interior-${id}`,
    x: anchor.x + x,
    z: anchor.z + z,
    width: w,
    depth: d,
    rotY: 0,
    minY: -0.2,
    maxY: height + 0.3,
    blocksWhen: 'always',
  });
  return [
    collider('north-wall', 0, -depth / 2, width, WALL_THICKNESS),
    collider('west-wall', -width / 2, 0, WALL_THICKNESS, depth),
    collider('east-wall', width / 2, 0, WALL_THICKNESS, depth),
    collider('south-left', -(DOOR_WIDTH + segment) / 2, depth / 2, segment, WALL_THICKNESS),
    collider('south-right', (DOOR_WIDTH + segment) / 2, depth / 2, segment, WALL_THICKNESS),
  ];
}

function addOccupants(
  group: THREE.Group,
  variant: HouseInteriorVariant,
  width: number,
  depth: number,
  anchor: THREE.Vector3,
): NpcState[] {
  const placements = variant === 'large'
    ? [
        { name: 'Elra Venn', title: 'Householder', x: -1.9, z: -0.5, rotY: 0.5 },
        { name: 'Tomas Venn', title: 'Journeyman', x: 1.1, z: 0.3, rotY: -1.8 },
        { name: 'Nella Venn', title: 'Resident', x: -2.8, z: 2.1, rotY: 2.4 },
      ]
    : [
        { name: 'Mara Tull', title: 'Householder', x: -1.2, z: -0.4, rotY: 0.6 },
        { name: 'Old Bren', title: 'Resident', x: 1.5, z: -1.4, rotY: -1.2 },
      ];
  return placements.map((placement, index) => {
    const person = AssetLoader.primitives.humanoid();
    person.name = `${variant}-resident-${index + 1}`;
    person.position.set(placement.x, 0, placement.z);
    person.rotation.y = placement.rotY;
    person.scale.setScalar(0.92 + index * 0.04);
    person.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (mesh.isMesh) mesh.castShadow = true;
    });
    group.add(person);
    return {
      id: `${variant}-resident-${index + 1}`,
      name: placement.name,
      title: placement.title,
      role: 'ambient' as const,
      position: { x: anchor.x + placement.x, y: 0, z: anchor.z + placement.z },
    };
  });
}

function addHearth(group: THREE.Group, x: number, z: number, stone: THREE.Material, iron: THREE.Material): void {
  addBox(group, 'hearth-base', [1.25, 0.35, 1.05], [x, 0.175, z], stone);
  addBox(group, 'hearth-back', [1.3, 2.25, 0.28], [x, 1.125, z - 0.46], stone);
  addBox(group, 'hearth-hood', [1.5, 0.24, 1.1], [x, 2.2, z - 0.08], stone);
  const fire = new THREE.Mesh(new THREE.SphereGeometry(0.25, 10, 7), new THREE.MeshStandardMaterial({ color: 0xff6a20, emissive: 0xff3b00, emissiveIntensity: 2.2 }));
  fire.scale.set(1, 0.8, 0.55);
  fire.position.set(x, 0.48, z - 0.2);
  group.add(fire);
  addBox(group, 'hearth-grate', [0.9, 0.12, 0.18], [x, 0.42, z + 0.05], iron);
}

function addTableSet(group: THREE.Group, x: number, z: number, timber: THREE.Material): void {
  addBox(group, 'table-top', [2.25, 0.18, 1.25], [x, 1.0, z], timber);
  for (const dx of [-0.85, 0.85]) for (const dz of [-0.42, 0.42]) addBox(group, 'table-leg', [0.16, 0.95, 0.16], [x + dx, 0.48, z + dz], timber);
  for (const dz of [-1.0, 1.0]) {
    addBox(group, 'bench-seat', [1.8, 0.16, 0.42], [x, 0.58, z + dz], timber);
    addBox(group, 'bench-leg', [0.14, 0.56, 0.36], [x - 0.62, 0.28, z + dz], timber);
    addBox(group, 'bench-leg', [0.14, 0.56, 0.36], [x + 0.62, 0.28, z + dz], timber);
  }
}

function addBed(group: THREE.Group, x: number, z: number, timber: THREE.Material, cloth: THREE.Material, large: boolean): void {
  const width = large ? 1.65 : 1.35;
  addBox(group, 'bed-frame', [width, 0.35, 2.55], [x, 0.38, z], timber);
  addBox(group, 'bed-mattress', [width - 0.14, 0.3, 2.35], [x, 0.68, z], cloth);
  addBox(group, 'bed-headboard', [width, 1.35, 0.18], [x, 0.8, z - 1.25], timber);
}

function addShelves(group: THREE.Group, x: number, z: number, timber: THREE.Material): void {
  for (const y of [0.55, 1.25, 1.95]) addBox(group, 'shelf', [0.72, 0.12, 2.1], [x, y, z], timber);
  addBox(group, 'shelf-post', [0.14, 2.1, 0.14], [x, 1.05, z - 0.88], timber);
  addBox(group, 'shelf-post', [0.14, 2.1, 0.14], [x, 1.05, z + 0.88], timber);
}

function addChest(group: THREE.Group, x: number, z: number, timber: THREE.Material, iron: THREE.Material): void {
  addBox(group, 'chest', [1.15, 0.72, 0.72], [x, 0.36, z], timber);
  addBox(group, 'chest-band', [1.2, 0.12, 0.77], [x, 0.48, z], iron);
}

function addRug(group: THREE.Group, x: number, z: number, size: number, cloth: THREE.Material): void {
  addBox(group, 'woven-rug', [size, 0.035, size * 0.58], [x, 0.025, z], cloth);
}

function createDoor(width: number, height: number, timber: THREE.Material, iron: THREE.Material): THREE.Group {
  const group = new THREE.Group();
  addBox(group, 'door-leaf', [width, height, 0.18], [0, height / 2, 0], timber);
  for (const y of [0.55, height - 0.55]) addBox(group, 'door-strap', [width * 0.9, 0.1, 0.08], [0, y, -0.13], iron);
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.025, 6, 12), iron);
  handle.position.set(width * 0.27, height * 0.53, -0.16);
  handle.rotation.x = Math.PI / 2;
  group.add(handle);
  return group;
}

function addBox(
  parent: THREE.Object3D,
  name: string,
  size: [number, number, number],
  position: [number, number, number],
  surface: THREE.Material,
): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), surface);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function material(color: number, roughness: number, metalness = 0.02): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}
