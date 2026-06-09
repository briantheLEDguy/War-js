import * as THREE from 'three';
import { AssetLoader } from '../game/AssetLoader';
import type { WorldPropObject } from '../services/types';
import type { Terrain } from './Terrain';
import type { PropSpawn } from './ZoneLoader';

export interface WorldCollider {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  rotY: number;
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
  isOpen: boolean;
  maxDistance: number;
  openClip: string;
  closeClip: string;
}

export interface SpawnedProps {
  colliders: WorldCollider[];
  cameraColliders: WorldCollider[];
  walkableSurfaces: WorldWalkableSurface[];
  gates: InteractiveGate[];
  objects: SpawnedStaticWorldObject[];
}

export interface SpawnedStaticWorldObject {
  id: string;
  definition: WorldPropObject;
  object: THREE.Object3D;
}

const CAMERA_SOLID_KINDS = new Set([
  'building',
  'wall_segment',
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
  const objects: SpawnedStaticWorldObject[] = [];

  for (const [index, s] of spawns.entries()) {
    const sourceObjectId = s.id ?? `static-prop-${index.toString().padStart(4, '0')}`;
    const pickedFallback = pickFallback(s.kind);
    const fallback = typeof pickedFallback === 'function'
      ? pickedFallback
      : AssetLoader.primitives.rock;
    const model = (s.model || s.assetKey || s.kind === 'dummy')
      ? await resolvePropModel(loader, s.kind, s.model ?? '', s.assetKey)
      : null;
    const animated = s.interaction?.type === 'gate' && model
      ? await loader.loadModelWithAnimations(model, fallback)
      : null;
    const obj = animated
      ? animated.object
      : model
        ? await loader.loadModel(model, fallback)
        : fallback();
    const y = terrain.heightAt(s.x, s.z) + (s.y ?? 0);
    obj.position.set(s.x, y, s.z);
    const propRotY = s.rotY ?? Math.random() * Math.PI * 2;
    const propScale = s.scale ?? 1;
    const propScaleX = propScale * (s.scaleX ?? 1);
    const propScaleY = propScale * (s.scaleY ?? 1);
    const propScaleZ = propScale * (s.scaleZ ?? 1);
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
          blocksWhen: c.blocksWhen ?? 'always',
          interactionId: c.interactionId,
          sourceObjectId,
        };
        colliders.push(collider);
        cameraColliders.push(collider);
      }
    } else if (CAMERA_SOLID_KINDS.has(s.kind)) {
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
      gates.push({
        id: s.interaction.id,
        label: s.interaction.label ?? 'Gate',
        object: obj,
        mixer,
        actions,
        isOpen: s.interaction.startsOpen ?? false,
        maxDistance: s.interaction.maxDistance ?? 18,
        openClip: s.interaction.openClip ?? 'open',
        closeClip: s.interaction.closeClip ?? 'close',
      });
      obj.userData.interactionId = s.interaction.id;
    }
  }

  return { colliders, cameraColliders, walkableSurfaces, gates, objects };
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
  switch (kind) {
    case 'tree':        return AssetLoader.primitives.tree;
    case 'rock':        return AssetLoader.primitives.rock;
    case 'building':    return AssetLoader.primitives.building;
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
