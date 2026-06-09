import * as THREE from 'three';
import type { EnemySpawn } from '../world/ZoneLoader';
import type { Terrain } from '../world/Terrain';
import { AssetLoader } from './AssetLoader';

type GroundResolver = (x: number, z: number, currentY?: number) => number;

export class Enemy {
  object!: THREE.Object3D;
  position = new THREE.Vector3();
  homePosition = new THREE.Vector3();
  respawnAt: number | null = null;
  private glbMixer: THREE.AnimationMixer | null = null;
  private glbActions = new Map<string, THREE.AnimationAction>();
  private activeOneShot: THREE.AnimationAction | null = null;
  private oneShotTime = 0;
  private lastAnimTime: number | null = null;

  /** True while chasing the player. */
  aggroed = false;
  /** Seconds until the next attack can land. */
  attackCooldown = 0;

  constructor(
    public spawn: EnemySpawn,
    private terrain: Terrain,
    private groundHeightAt: GroundResolver = (x, z) => terrain.heightAt(x, z),
  ) {}

  async build(loader: AssetLoader, scene: THREE.Scene): Promise<void> {
    const fallbackModel = this.spawn.model ?? 'prop_training_dummy_t1.glb';
    const staticAssetKey = this.spawn.assetKey ?? (!this.spawn.model || this.spawn.model === 'dummy.glb' ? 'dummy' : null);
    const model = staticAssetKey
      ? await loader.resolveStaticModel(staticAssetKey, fallbackModel)
      : fallbackModel;
    const { object, animations } = await loader.loadModelFull(
      model,
      () => AssetLoader.primitives.dummy(),
    );
    this.object = object;

    if (animations.length > 0) {
      this.glbMixer = new THREE.AnimationMixer(this.object);
      for (const clip of animations) {
        this.glbActions.set(clip.name, this.glbMixer.clipAction(clip));
      }

      const idle = this.glbActions.get('idle');
      if (idle) {
        idle.setLoop(THREE.LoopRepeat, Infinity);
        idle.play();
      }
    }

    const heightHint = this.terrain.heightAt(this.spawn.x, this.spawn.z) + (this.spawn.y ?? 0);
    const y = this.groundHeightAt(this.spawn.x, this.spawn.z, heightHint);
    this.position.set(this.spawn.x, y, this.spawn.z);
    this.homePosition.copy(this.position);
    this.object.position.copy(this.position);
    scene.add(this.object);
  }

  playHitReact(): void {
    const action = this.glbActions.get('hit_react');
    if (!action) return;

    action.reset();
    action.enabled = true;
    action.clampWhenFinished = false;
    action.setLoop(THREE.LoopOnce, 1);
    action.fadeIn(0.05);
    action.play();

    this.activeOneShot = action;
    this.oneShotTime = action.getClip().duration;
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

  update(now: number, alive: boolean) {
    if (alive) {
      if (!this.object.visible) this.object.visible = true;
      if (this.glbMixer) {
        const dt = this.lastAnimTime === null
          ? 0
          : Math.min(0.1, (now - this.lastAnimTime) / 1000);
        this.lastAnimTime = now;

        if (this.activeOneShot) {
          this.oneShotTime = Math.max(0, this.oneShotTime - dt);
          if (this.oneShotTime <= 0) {
            this.activeOneShot.fadeOut(0.08);
            this.activeOneShot = null;
          }
        }

        this.glbMixer.update(dt);
      }
    } else {
      this.object.visible = false;
      this.lastAnimTime = now;
    }
  }

  setVisible(v: boolean) {
    this.object.visible = v;
  }
}
