import * as THREE from 'three';
import { AssetLoader } from '../game/AssetLoader';
import type { Terrain } from './Terrain';
import type { NpcSpawn } from './ZoneLoader';

type GroundResolver = (x: number, z: number, currentY?: number) => number;

export interface NpcState {
  id: string;
  name: string;
  title?: string;
  role: NpcSpawn['role'];
  position: { x: number; y: number; z: number };
}

export interface SpawnedNpcs {
  states: NpcState[];
  mixers: THREE.AnimationMixer[];
}

/**
 * Spawns static NPC meshes from zone JSON. NPCs have no combat AI — they are
 * vendors, trainers, bankers, and ambient characters faithful to WAR's city layouts.
 * Their positions are pushed into gameStore.npcs so NameplateLayer can render them.
 */
export async function spawnNpcs(
  scene: THREE.Scene,
  loader: AssetLoader,
  terrain: Terrain,
  spawns: NpcSpawn[],
  groundHeightAt: GroundResolver = (x, z) => terrain.heightAt(x, z),
): Promise<SpawnedNpcs> {
  const states: NpcState[] = [];
  const mixers: THREE.AnimationMixer[] = [];

  for (const s of spawns) {
    const fallback = pickNpcFallback(s.role);
    const model = s.model ?? pickNpcRoleModel(s.role);
    const { object: obj, animations } = model
      ? await loader.loadModelWithAnimations(model, fallback)
      : { object: fallback(), animations: [] };
    if (s.role === 'guard') prepareGuardNpcRuntimeObject(obj);

    const heightHint = terrain.heightAt(s.x, s.z) + (s.y ?? 0);
    const y = groundHeightAt(s.x, s.z, heightHint);
    obj.position.set(s.x, y, s.z);
    obj.rotation.y = s.rotY ?? 0;
    scene.add(obj);

    const mixer = startIdleAnimation(obj, animations);
    if (mixer) mixers.push(mixer);

    states.push({
      id: s.id,
      name: s.name,
      title: s.title,
      role: s.role,
      position: { x: s.x, y, z: s.z },
    });
  }

  return { states, mixers };
}

function pickNpcFallback(role: NpcSpawn['role']) {
  switch (role) {
    case 'guard':      return AssetLoader.primitives.npc_guard;
    case 'vendor':     return AssetLoader.primitives.npc_vendor;
    case 'trainer':    return AssetLoader.primitives.npc_trainer;
    case 'banker':     return AssetLoader.primitives.npc_banker;
    case 'questgiver': return AssetLoader.primitives.npc_quest;
    case 'ambient':    return AssetLoader.primitives.humanoid;
    default:           return AssetLoader.primitives.humanoid;
  }
}

function pickNpcRoleModel(role: NpcSpawn['role']): string | undefined {
  switch (role) {
    case 'guard': return 'guard_male.glb';
    default:      return undefined;
  }
}

function prepareGuardNpcRuntimeObject(object: THREE.Object3D): void {
  object.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;

    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;

    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      if (!material) continue;
      material.side = THREE.FrontSide;
      material.transparent = false;
      material.depthWrite = true;
      material.depthTest = true;
      material.needsUpdate = true;
    }
  });
}

function startIdleAnimation(
  object: THREE.Object3D,
  animations: THREE.AnimationClip[],
): THREE.AnimationMixer | null {
  if (animations.length === 0) return null;

  const idle = animations.find((clip) => clip.name.toLowerCase() === 'idle') ?? animations[0];
  const mixer = new THREE.AnimationMixer(object);
  const action = mixer.clipAction(idle);
  action.setLoop(THREE.LoopRepeat, Infinity);
  action.enabled = true;
  action.play();

  if (idle.duration > 0) {
    const phase = Math.abs(Math.sin(object.position.x * 12.9898 + object.position.z * 78.233));
    mixer.setTime(phase * idle.duration);
  }

  return mixer;
}
