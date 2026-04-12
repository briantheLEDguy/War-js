import * as THREE from 'three';
import { AssetLoader } from '../game/AssetLoader';
import type { Terrain } from './Terrain';
import type { PropSpawn } from './ZoneLoader';

/**
 * Spawns props described by zone JSON. Each prop either loads a .glb or
 * uses a primitive fallback. Positions are snapped to terrain height.
 */
export async function spawnProps(
  scene: THREE.Scene,
  loader: AssetLoader,
  terrain: Terrain,
  spawns: PropSpawn[],
): Promise<void> {
  for (const s of spawns) {
    const fallback = pickFallback(s.kind);
    const obj = s.model
      ? await loader.loadModel(s.model, fallback)
      : fallback();
    const y = terrain.heightAt(s.x, s.z);
    obj.position.set(s.x, y, s.z);
    obj.rotation.y = s.rotY ?? Math.random() * Math.PI * 2;
    if (s.scale) obj.scale.setScalar(s.scale);
    scene.add(obj);
  }
}

function pickFallback(kind: string) {
  switch (kind) {
    case 'tree':
      return AssetLoader.primitives.tree;
    case 'rock':
      return AssetLoader.primitives.rock;
    case 'building':
      return AssetLoader.primitives.building;
    case 'dummy':
      return AssetLoader.primitives.dummy;
    default:
      return AssetLoader.primitives.rock;
  }
}
