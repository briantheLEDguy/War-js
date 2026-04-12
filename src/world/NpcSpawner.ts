import * as THREE from 'three';
import { AssetLoader } from '../game/AssetLoader';
import type { Terrain } from './Terrain';
import type { NpcSpawn } from './ZoneLoader';

export interface NpcState {
  id: string;
  name: string;
  title?: string;
  role: NpcSpawn['role'];
  position: { x: number; y: number; z: number };
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
): Promise<NpcState[]> {
  const states: NpcState[] = [];

  for (const s of spawns) {
    const fallback = pickNpcFallback(s.role);
    const obj = s.role && (s as { model?: string }).model
      ? await loader.loadModel((s as { model?: string }).model!, fallback)
      : fallback();

    const y = terrain.heightAt(s.x, s.z);
    obj.position.set(s.x, y, s.z);
    obj.rotation.y = s.rotY ?? 0;
    scene.add(obj);

    states.push({
      id: s.id,
      name: s.name,
      title: s.title,
      role: s.role,
      position: { x: s.x, y, z: s.z },
    });
  }

  return states;
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
