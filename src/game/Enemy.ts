import * as THREE from 'three';
import type { EnemySpawn } from '../world/ZoneLoader';
import type { Terrain } from '../world/Terrain';
import { AssetLoader } from './AssetLoader';

export class Enemy {
  object!: THREE.Object3D;
  position = new THREE.Vector3();
  homePosition = new THREE.Vector3();
  respawnAt: number | null = null;

  /** True while chasing the player. */
  aggroed = false;
  /** Seconds until the next attack can land. */
  attackCooldown = 0;

  constructor(public spawn: EnemySpawn, private terrain: Terrain) {}

  async build(loader: AssetLoader, scene: THREE.Scene): Promise<void> {
    this.object = await loader.loadModel(
      this.spawn.model ?? 'dummy.glb',
      () => AssetLoader.primitives.dummy(),
    );
    const y = this.terrain.heightAt(this.spawn.x, this.spawn.z);
    this.position.set(this.spawn.x, y, this.spawn.z);
    this.homePosition.copy(this.position);
    this.object.position.copy(this.position);
    scene.add(this.object);
  }

  /**
   * Move toward a world-space target at `speed` units/sec.
   * Updates both this.position and the mesh.
   */
  moveToward(target: THREE.Vector3, speed: number, dt: number) {
    const dx = target.x - this.position.x;
    const dz = target.z - this.position.z;
    const dist = Math.hypot(dx, dz);
    if (dist < 0.05) return;
    const step = Math.min(speed * dt, dist);
    const nx = dx / dist;
    const nz = dz / dist;
    this.position.x += nx * step;
    this.position.z += nz * step;
    this.object.position.x = this.position.x;
    this.object.position.z = this.position.z;
    // Face movement direction
    this.object.rotation.y = Math.atan2(nx, nz);
  }

  /** Snap back to spawn point and clear aggro state. */
  resetToHome() {
    this.position.copy(this.homePosition);
    this.object.position.copy(this.homePosition);
    this.aggroed = false;
    this.attackCooldown = 0;
  }

  update(_now: number, alive: boolean) {
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
