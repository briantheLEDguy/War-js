import * as THREE from 'three';
import type { EnemySpawn } from '../world/ZoneLoader';
import type { Terrain } from '../world/Terrain';
import { AssetLoader } from './AssetLoader';

export class Enemy {
  object!: THREE.Object3D;
  position = new THREE.Vector3();
  respawnAt: number | null = null;

  constructor(public spawn: EnemySpawn, private terrain: Terrain) {}

  async build(loader: AssetLoader, scene: THREE.Scene): Promise<void> {
    this.object = await loader.loadModel(
      this.spawn.model ?? 'dummy.glb',
      () => AssetLoader.primitives.dummy(),
    );
    this.position.set(
      this.spawn.x,
      this.terrain.heightAt(this.spawn.x, this.spawn.z),
      this.spawn.z,
    );
    this.object.position.copy(this.position);
    scene.add(this.object);
  }

  update(now: number, alive: boolean) {
    if (alive) {
      if (!this.object.visible) this.object.visible = true;
    } else {
      this.object.visible = false;
    }
  }

  setVisible(v: boolean) {
    this.object.visible = v;
  }
}
