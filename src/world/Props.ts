import * as THREE from 'three';
import { AssetLoader } from '../game/AssetLoader';
import type { WorldPropObject } from '../services/types';
import {
  isPrefabCameraSolidKind,
  prefabFallbackKindForKind,
} from './editor/PrefabCatalog';
import type { Terrain } from './Terrain';
import type { PropSpawn } from './ZoneLoader';

export interface WorldCollider {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  rotY: number;
  minY?: number;
  maxY?: number;
  blocksWhen: 'always' | 'closed';
  interactionId?: string;
  sourceObjectId?: string;
}

export interface WorldWalkableSurface {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  rotY: number;
  fromY: number;
  toY: number;
  axis: 'x' | 'z';
  sourceObjectId?: string;
}

export interface InteractiveGate {
  id: string;
  label: string;
  object: THREE.Object3D;
  mixer: THREE.AnimationMixer | null;
  actions: Map<string, THREE.AnimationAction>;
  fallbackVisual: GateFallbackVisual | null;
  isOpen: boolean;
  maxDistance: number;
  openClip: string;
  closeClip: string;
}

export type HouseInteriorVariant = 'small' | 'large';

export interface InteractiveHousePortal {
  id: string;
  label: string;
  object: THREE.Object3D;
  interiorVariant: HouseInteriorVariant;
  maxDistance: number;
  direction: 'enter' | 'exit';
}

export interface GateFallbackVisual {
  progress: number;
  target: number;
  speed: number;
}

export interface SpawnedProps {
  colliders: WorldCollider[];
  cameraColliders: WorldCollider[];
  walkableSurfaces: WorldWalkableSurface[];
  gates: InteractiveGate[];
  housePortals: InteractiveHousePortal[];
  objects: SpawnedStaticWorldObject[];
}

export interface SpawnedStaticWorldObject {
  id: string;
  definition: WorldPropObject;
  object: THREE.Object3D;
}

const CAMERA_SOLID_KINDS = new Set([
  'building',
  'castle_floor',
  'wall_segment',
  'rift_house',
  'rift_wall_segment',
  'rift_tower',
  'rift_obelisk',
  'rift_brazier',
  'rift_spike_cluster',
  'tower',
  'gate',
  'castle',
  'castle_gate',
  'castle_door',
  'temple',
  'statue',
  'fountain',
  'vendor_stall',
]);
const PATH_TERRAIN_SAMPLE_SPACING = 3.25;
const PATH_VISUAL_LIFT = 0.035;

/**
 * Spawns props described by zone JSON. Each prop either loads a .glb or
 * uses a primitive fallback. Positions are snapped to terrain height.
 */
export async function spawnProps(
  scene: THREE.Scene,
  loader: AssetLoader,
  terrain: Terrain,
  spawns: PropSpawn[],
): Promise<SpawnedProps> {
  const colliders: WorldCollider[] = [];
  const cameraColliders: WorldCollider[] = [];
  const walkableSurfaces: WorldWalkableSurface[] = [];
  const gates: InteractiveGate[] = [];
  const housePortals: InteractiveHousePortal[] = [];
  const objects: SpawnedStaticWorldObject[] = [];

  for (const [index, s] of spawns.entries()) {
    const sourceObjectId = s.id ?? `static-prop-${index.toString().padStart(4, '0')}`;
    const propRotY = s.rotY ?? Math.random() * Math.PI * 2;
    const propScale = s.scale ?? 1;
    let propScaleX = propScale * (s.scaleX ?? 1);
    let propScaleY = propScale * (s.scaleY ?? 1);
    let propScaleZ = propScale * (s.scaleZ ?? 1);
    let animated: Awaited<ReturnType<AssetLoader['loadModelWithAnimations']>> | null = null;
    let obj: THREE.Object3D;
    let y = terrain.heightAt(s.x, s.z) + (s.y ?? 0);

    if (s.visible === false) {
      obj = new THREE.Group();
      obj.visible = false;
    } else if (isTerrainPathKind(s.kind)) {
      obj = buildTerrainPathObject(s.kind, terrain, s.x, s.z, propRotY, propScaleX, propScaleZ, s.y ?? 0);
      propScaleX = 1;
      propScaleY = 1;
      propScaleZ = 1;
    } else {
      const pickedFallback = pickFallback(s.kind);
      const fallback = typeof pickedFallback === 'function'
        ? pickedFallback
        : AssetLoader.primitives.rock;
      const model = (s.model || s.assetKey || s.kind === 'dummy')
        ? await resolvePropModel(loader, s.kind, s.model ?? '', s.assetKey)
        : null;
      animated = s.interaction?.type === 'gate' && model
        ? await loader.loadModelWithAnimations(model, fallback)
        : null;
      obj = animated
        ? animated.object
        : model
          ? await loader.loadModel(model, fallback)
          : fallback();
    }

    obj.position.set(s.x, y, s.z);
    obj.rotation.y = propRotY;
    obj.scale.set(propScaleX, propScaleY, propScaleZ);
    obj.userData.worldEditObjectId = sourceObjectId;
    obj.traverse((node) => {
      node.userData.worldEditObjectId = sourceObjectId;
    });
    scene.add(obj);

    objects.push({
      id: sourceObjectId,
      definition: {
        id: sourceObjectId,
        type: 'prop',
        kind: s.kind,
        label: s.kind.replaceAll('_', ' '),
        model: s.model,
        assetKey: s.assetKey,
        transform: {
          position: { x: s.x, y, z: s.z },
          rotation: { x: 0, y: propRotY, z: 0 },
          scale: { x: propScaleX, y: propScaleY, z: propScaleZ },
        },
        colliders: s.colliders ? cloneJson(s.colliders) : undefined,
        walkableSurfaces: s.walkableSurfaces ? cloneJson(s.walkableSurfaces) : undefined,
        interaction: s.interaction ? cloneJson(s.interaction) : undefined,
        createdAt: 0,
        updatedAt: 0,
      },
      object: obj,
    });

    if (s.colliders) {
      for (const c of s.colliders) {
        const localX = (c.x ?? 0) * propScaleX;
        const localZ = (c.z ?? 0) * propScaleZ;
        const cos = Math.cos(propRotY);
        const sin = Math.sin(propRotY);
        const collider = {
          id: c.id ?? `${s.kind}-collider-${colliders.length}`,
          x: s.x + localX * cos - localZ * sin,
          z: s.z + localX * sin + localZ * cos,
          width: c.width * propScaleX,
          depth: c.depth * propScaleZ,
          rotY: propRotY + (c.rotY ?? 0),
          minY: c.minY === undefined ? undefined : y + c.minY * propScaleY,
          maxY: c.maxY === undefined ? undefined : y + c.maxY * propScaleY,
          blocksWhen: c.blocksWhen ?? 'always',
          interactionId: c.interactionId,
          sourceObjectId,
        };
        colliders.push(collider);
        cameraColliders.push(collider);
      }
    } else if (CAMERA_SOLID_KINDS.has(s.kind) || isPrefabCameraSolidKind(s.kind)) {
      const cameraCollider = buildCameraColliderFromObject(
        obj,
        s.kind,
        cameraColliders.length,
        s.interaction?.type === 'gate' ? 'closed' : 'always',
        s.interaction?.id,
        sourceObjectId,
      );
      if (cameraCollider) cameraColliders.push(cameraCollider);
    }

    if (s.walkableSurfaces) {
      for (const surface of s.walkableSurfaces) {
        const localX = (surface.x ?? 0) * propScaleX;
        const localZ = (surface.z ?? 0) * propScaleZ;
        const cos = Math.cos(propRotY);
        const sin = Math.sin(propRotY);
        walkableSurfaces.push({
          id: surface.id ?? `${s.kind}-walkable-${walkableSurfaces.length}`,
          x: s.x + localX * cos - localZ * sin,
          z: s.z + localX * sin + localZ * cos,
          width: surface.width * propScaleX,
          depth: surface.depth * propScaleZ,
          rotY: propRotY + (surface.rotY ?? 0),
          fromY: y + (surface.fromY ?? 0) * propScaleY,
          toY: y + (surface.toY ?? 0) * propScaleY,
          axis: surface.axis ?? 'z',
          sourceObjectId,
        });
      }
    }

    if (s.interaction?.type === 'gate') {
      const actions = new Map<string, THREE.AnimationAction>();
      const mixer = animated && animated.animations.length > 0
        ? new THREE.AnimationMixer(obj)
        : null;
      if (mixer && animated) {
        for (const clip of animated.animations) {
          actions.set(clip.name, mixer.clipAction(clip));
        }
      }
      const startsOpen = s.interaction.startsOpen ?? false;
      const fallbackVisual = hasGateFallbackLeaves(obj)
        ? {
            progress: startsOpen ? 1 : 0,
            target: startsOpen ? 1 : 0,
            speed: 4,
          }
        : null;
      if (fallbackVisual) applyGateFallbackVisual(obj, fallbackVisual.progress);
      gates.push({
        id: s.interaction.id,
        label: s.interaction.label ?? 'Gate',
        object: obj,
        mixer,
        actions,
        fallbackVisual,
        isOpen: startsOpen,
        maxDistance: s.interaction.maxDistance ?? 18,
        openClip: s.interaction.openClip ?? 'open',
        closeClip: s.interaction.closeClip ?? 'close',
      });
      obj.userData.interactionId = s.interaction.id;
    }
    if (s.interaction?.type === 'house_portal') {
      housePortals.push({
        id: s.interaction.id,
        label: s.interaction.label ?? 'House Door',
        object: obj,
        interiorVariant: s.interaction.interiorVariant ?? 'small',
        maxDistance: s.interaction.maxDistance ?? 9,
        direction: 'enter',
      });
      obj.userData.housePortalId = s.interaction.id;
      obj.traverse((node) => {
        node.userData.housePortalId = s.interaction?.id;
      });
    }
  }

  return { colliders, cameraColliders, walkableSurfaces, gates, housePortals, objects };
}

function buildCameraColliderFromObject(
  obj: THREE.Object3D,
  kind: string,
  index: number,
  blocksWhen: WorldCollider['blocksWhen'],
  interactionId?: string,
  sourceObjectId?: string,
): WorldCollider | null {
  obj.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(obj);
  if (box.isEmpty()) return null;
  const size = box.getSize(new THREE.Vector3());
  if (size.x < 0.25 || size.z < 0.25) return null;
  const center = box.getCenter(new THREE.Vector3());
  return {
    id: `${kind}-camera-${index}`,
    x: center.x,
    z: center.z,
    width: size.x,
    depth: size.z,
    rotY: 0,
    blocksWhen,
    interactionId,
    sourceObjectId,
  };
}

function isTerrainPathKind(kind: string): boolean {
  return kind === 'path_dirt' || kind === 'path_cobblestone';
}

function buildTerrainPathObject(
  kind: string,
  terrain: Terrain,
  centerX: number,
  centerZ: number,
  rotY: number,
  width: number,
  depth: number,
  visualOffset: number,
): THREE.Object3D {
  const group = new THREE.Group();
  const baseY = terrain.heightAt(centerX, centerZ) + visualOffset;
  const isCobblestone = kind === 'path_cobblestone';
  group.add(buildTerrainPathRibbon({
    terrain,
    centerX,
    centerZ,
    baseY,
    rotY,
    x0: -width / 2,
    x1: width / 2,
    z0: -depth / 2,
    z1: depth / 2,
    yLift: PATH_VISUAL_LIFT,
    material: new THREE.MeshStandardMaterial({
      color: isCobblestone ? 0x716e66 : 0x5f4a31,
      roughness: isCobblestone ? 0.9 : 0.96,
      side: THREE.DoubleSide,
    }),
  }));
  return group;
}

function buildTerrainPathRibbon(opts: {
  terrain: Terrain;
  centerX: number;
  centerZ: number;
  baseY: number;
  rotY: number;
  x0: number;
  x1: number;
  z0: number;
  z1: number;
  yLift: number;
  material: THREE.Material;
}): THREE.Mesh {
  const width = Math.abs(opts.x1 - opts.x0);
  const depth = Math.abs(opts.z1 - opts.z0);
  const xSegments = Math.max(1, Math.ceil(width / PATH_TERRAIN_SAMPLE_SPACING));
  const zSegments = Math.max(1, Math.ceil(depth / PATH_TERRAIN_SAMPLE_SPACING));
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const cos = Math.cos(opts.rotY);
  const sin = Math.sin(opts.rotY);

  for (let zi = 0; zi <= zSegments; zi += 1) {
    const zT = zi / zSegments;
    const localZ = opts.z0 + (opts.z1 - opts.z0) * zT;
    for (let xi = 0; xi <= xSegments; xi += 1) {
      const xT = xi / xSegments;
      const localX = opts.x0 + (opts.x1 - opts.x0) * xT;
      const worldX = opts.centerX + localX * cos + localZ * sin;
      const worldZ = opts.centerZ - localX * sin + localZ * cos;
      positions.push(
        localX,
        opts.terrain.heightAt(worldX, worldZ) + opts.yLift - opts.baseY,
        localZ,
      );
      uvs.push(xT, zT);
    }
  }

  for (let zi = 0; zi < zSegments; zi += 1) {
    for (let xi = 0; xi < xSegments; xi += 1) {
      const a = zi * (xSegments + 1) + xi;
      const b = a + 1;
      const c = a + xSegments + 1;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  const mesh = new THREE.Mesh(geometry, opts.material);
  mesh.receiveShadow = true;
  return mesh;
}

async function resolvePropModel(
  loader: AssetLoader,
  kind: string,
  model: string,
  assetKey?: string,
): Promise<string> {
  const staticAssetKey = assetKey ?? (kind === 'dummy' || model === 'dummy.glb' ? 'dummy' : null);
  if (staticAssetKey) {
    return loader.resolveStaticModel(staticAssetKey, model || 'prop_training_dummy_t1.glb');
  }
  return model;
}

function pickFallback(kind: string) {
  const primitives = AssetLoader.primitives as unknown as Record<string, () => THREE.Object3D>;
  const catalogFallbackKind = prefabFallbackKindForKind(kind);
  if (catalogFallbackKind && primitives[catalogFallbackKind]) {
    return primitives[catalogFallbackKind];
  }
  switch (kind) {
    case 'tree':        return AssetLoader.primitives.tree;
    case 'rock':        return AssetLoader.primitives.rock;
    case 'building':    return AssetLoader.primitives.building;
    case 'castle_floor': return AssetLoader.primitives.castle_floor;
    case 'rift_house': return AssetLoader.primitives.rift_house;
    case 'rift_wall_segment': return AssetLoader.primitives.rift_wall_segment;
    case 'rift_tower': return AssetLoader.primitives.rift_tower;
    case 'rift_obelisk': return AssetLoader.primitives.rift_obelisk;
    case 'rift_brazier': return AssetLoader.primitives.rift_brazier;
    case 'rift_spike_cluster': return AssetLoader.primitives.rift_spike_cluster;
    case 'dummy':       return AssetLoader.primitives.dummy;
    // Biome kit props
    case 'pnw_douglas_fir': return AssetLoader.primitives.pnw_douglas_fir;
    case 'pnw_western_red_cedar': return AssetLoader.primitives.pnw_western_red_cedar;
    case 'pnw_hemlock': return AssetLoader.primitives.pnw_hemlock;
    case 'pnw_sword_fern': return AssetLoader.primitives.pnw_sword_fern;
    case 'pnw_grass_clump': return AssetLoader.primitives.pnw_grass_clump;
    case 'pnw_wildflower_clump': return AssetLoader.primitives.pnw_wildflower_clump;
    case 'pnw_low_shrub': return AssetLoader.primitives.pnw_low_shrub;
    case 'pnw_mossy_boulder': return AssetLoader.primitives.pnw_mossy_boulder;
    case 'pnw_fallen_log': return AssetLoader.primitives.pnw_fallen_log;
    case 'pnw_path_edge_stone': return AssetLoader.primitives.pnw_path_edge_stone;
    case 'path_dirt':
    case 'dirt_path_strip': return AssetLoader.primitives.dirt_path_strip;
    case 'path_cobblestone':
    case 'cobblestone_path_strip': return AssetLoader.primitives.cobblestone_path_strip;
    // WAR city props
    case 'wall_segment': return AssetLoader.primitives.wall_segment;
    case 'tower':       return AssetLoader.primitives.tower;
    case 'gate':        return AssetLoader.primitives.gate;
    case 'castle':      return AssetLoader.primitives.castle;
    case 'castle_gate': return AssetLoader.primitives.castle_gate;
    case 'castle_door': return AssetLoader.primitives.castle_door;
    case 'castle_stairs': return AssetLoader.primitives.castle_stairs;
    case 'temple':      return AssetLoader.primitives.temple;
    case 'statue':      return AssetLoader.primitives.statue;
    case 'fountain':    return AssetLoader.primitives.fountain;
    case 'banner_post': return AssetLoader.primitives.banner_post;
    case 'vendor_stall': return AssetLoader.primitives.vendor_stall;
    case 'steps':       return AssetLoader.primitives.steps;
    case 'bridge':      return AssetLoader.primitives.bridge;
    case 'dock':        return AssetLoader.primitives.dock;
    default:            return AssetLoader.primitives.rock;
  }
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function hasGateFallbackLeaves(object: THREE.Object3D): boolean {
  let found = false;
  object.traverse((node) => {
    if (typeof node.userData.gateLeafSide === 'number') found = true;
  });
  return found;
}

function applyGateFallbackVisual(object: THREE.Object3D, progress: number): void {
  const clamped = Math.max(0, Math.min(1, progress));
  object.traverse((node) => {
    const side = node.userData.gateLeafSide;
    if (typeof side !== 'number') return;
    node.rotation.y = -side * (Math.PI / 2) * clamped;
  });
}
