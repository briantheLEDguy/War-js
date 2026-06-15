import * as THREE from 'three';
import {
  aegisEnemyGuardVariantFor,
} from '../data/modelOverrides';
import type { EnemySpawn } from '../world/ZoneLoader';
import type { Terrain } from '../world/Terrain';
import { AssetLoader } from './AssetLoader';
import { StaticModelAnimator } from './animation/StaticModelAnimator';

type GroundResolver = (x: number, z: number, currentY?: number) => number;

export class Enemy {
  object!: THREE.Object3D;
  position = new THREE.Vector3();
  homePosition = new THREE.Vector3();
  respawnAt: number | null = null;
  private glbMixer: THREE.AnimationMixer | null = null;
  private glbActions = new Map<string, THREE.AnimationAction>();
  private activeLoopAction: THREE.AnimationAction | null = null;
  private activeLoopClipName: string | null = null;
  private defaultLoopClipName: string | null = null;
  private activeOneShot: THREE.AnimationAction | null = null;
  private oneShotTime = 0;
  private lastAnimTime: number | null = null;
  private animator: StaticModelAnimator | null = null;
  private lastSpeed = 0;

  /** True while chasing the player. */
  aggroed = false;
  /** Seconds until the next attack can land. */
  attackCooldown = 0;
  /** Seconds until the next archetype ability can begin casting. */
  abilityCooldown = 0;
  /** Pending archetype ability cast, resolved by Combat once its windup finishes. */
  pendingAbility: { abilityId: string; dueAt: number } | null = null;

  constructor(
    public spawn: EnemySpawn,
    private terrain: Terrain,
    private groundHeightAt: GroundResolver = (x, z) => terrain.heightAt(x, z),
  ) {}

  async build(loader: AssetLoader, scene: THREE.Scene): Promise<void> {
    const fallback = pickEnemyFallback(this.spawn);
    const guardVariant = aegisEnemyGuardVariantFor(
      this.spawn.archetype,
      this.spawn.characterProfileKey,
      this.spawn.name,
      this.spawn.id,
    );
    if (guardVariant) {
      const guardModel = await loader.resolveCharacterModel(guardVariant.profileKey)
        ?? guardVariant.fallbackModel;
      const { object, animations } = await loader.loadModelFull(guardModel, fallback);
      this.object = object;
      this.prepareAnimationMixer(animations);
      this.place(scene);
      return;
    }

    const profileModel = this.spawn.characterProfileKey
      ? await loader.resolveCharacterModel(this.spawn.characterProfileKey)
      : null;
    if (profileModel) {
      const { object, animations } = await loader.loadModelFull(profileModel, fallback);
      this.object = object;
      this.prepareAnimationMixer(animations);
      this.place(scene);
      return;
    }

    const fallbackModel = this.spawn.model ?? 'prop_training_dummy_t1.glb';
    const staticAssetKey = this.spawn.assetKey ?? (!this.spawn.model || this.spawn.model === 'dummy.glb' ? 'dummy' : null);
    const model = staticAssetKey
      ? await loader.resolveStaticModel(staticAssetKey, fallbackModel)
      : fallbackModel;
    const { object, animations } = await loader.loadModelFull(
      model,
      fallback,
    );
    this.object = object;
    this.prepareAnimationMixer(animations);
    this.place(scene);
  }

  private prepareAnimationMixer(animations: THREE.AnimationClip[]): void {
    this.glbMixer = null;
    this.glbActions.clear();
    this.activeLoopAction = null;
    this.activeLoopClipName = null;
    this.defaultLoopClipName = null;
    this.activeOneShot = null;
    this.oneShotTime = 0;
    this.animator = null;

    if (animations.length > 0) {
      this.glbMixer = new THREE.AnimationMixer(this.object);
      for (const clip of animations) {
        this.glbActions.set(clip.name, this.glbMixer.clipAction(clip));
      }

      this.defaultLoopClipName =
        this.findClipName('idle') ??
        this.findClipName('combat_idle') ??
        animations[0].name;
      this.playLoop(this.defaultLoopClipName);
    }

    if (!this.hasExplicitLocomotion()) {
      this.animator = new StaticModelAnimator(this.object, {
        preserveMixedPose: animations.length > 0,
      });
    }
  }

  private place(scene: THREE.Scene): void {
    const heightHint = this.terrain.heightAt(this.spawn.x, this.spawn.z) + (this.spawn.y ?? 0);
    const y = this.groundHeightAt(this.spawn.x, this.spawn.z, heightHint);
    this.position.set(this.spawn.x, y, this.spawn.z);
    this.homePosition.copy(this.position);
    this.object.position.copy(this.position);
    scene.add(this.object);
  }

  playHitReact(): void {
    if (this.playOneShot('hit_react')) return;
    this.animator?.playAction('hit_react', 0.25);
  }

  /**
   * Move toward a world-space target at `speed` units/sec.
   * Updates both this.position and the mesh.
   */
  moveToward(target: THREE.Vector3, speed: number, dt: number) {
    const dx = target.x - this.position.x;
    const dz = target.z - this.position.z;
    const dist = Math.hypot(dx, dz);
    if (dist < 0.05) {
      this.lastSpeed = 0;
      return;
    }
    const step = Math.min(speed * dt, dist);
    const nx = dx / dist;
    const nz = dz / dist;
    this.position.x += nx * step;
    this.position.z += nz * step;
    this.object.position.x = this.position.x;
    this.object.position.z = this.position.z;
    // Face movement direction
    this.object.rotation.y = Math.atan2(nx, nz);
    if (dt > 0) this.lastSpeed = Math.max(this.lastSpeed, step / dt);
  }

  /**
   * Move directly away from a world-space target at `speed` units/sec.
   * Used by ranged enemy archetypes to keep stand-off spacing.
   */
  moveAwayFrom(target: THREE.Vector3, speed: number, dt: number) {
    const dx = this.position.x - target.x;
    const dz = this.position.z - target.z;
    const dist = Math.hypot(dx, dz);
    if (dist < 0.05) {
      this.lastSpeed = 0;
      return;
    }
    const step = speed * dt;
    const nx = dx / dist;
    const nz = dz / dist;
    this.position.x += nx * step;
    this.position.z += nz * step;
    this.object.position.x = this.position.x;
    this.object.position.z = this.position.z;
    this.object.rotation.y = Math.atan2(-nx, -nz);
    if (dt > 0) this.lastSpeed = Math.max(this.lastSpeed, step / dt);
  }

  faceToward(target: THREE.Vector3): void {
    const dx = target.x - this.position.x;
    const dz = target.z - this.position.z;
    if (Math.hypot(dx, dz) < 0.05) return;
    this.object.rotation.y = Math.atan2(dx, dz);
  }

  playAttackAction(kind: 'melee' | 'ranged' | 'cast'): void {
    const actionName = kind === 'cast'
      ? 'cast'
      : kind === 'ranged'
        ? 'attack_ranged'
        : 'attack_melee';
    if (this.playOneShot(actionName)) return;
    this.animator?.playAction(actionName, kind === 'cast' ? 0.75 : 0.45);
  }

  /** Snap back to spawn point and clear aggro state. */
  resetToHome() {
    this.position.copy(this.homePosition);
    this.object.position.copy(this.homePosition);
    this.aggroed = false;
    this.attackCooldown = 0;
    this.abilityCooldown = 0;
    this.pendingAbility = null;
    this.lastSpeed = 0;
  }

  update(now: number, alive: boolean) {
    if (alive) {
      if (!this.object.visible) this.object.visible = true;
      if (this.glbMixer) {
        const dt = this.lastAnimTime === null
          ? 0
          : Math.min(0.1, (now - this.lastAnimTime) / 1000);
        this.lastAnimTime = now;
        const speed = this.lastSpeed;
        this.lastSpeed = 0;

        if (this.activeOneShot) {
          this.oneShotTime = Math.max(0, this.oneShotTime - dt);
          if (this.oneShotTime <= 0) {
            this.activeOneShot.fadeOut(0.08);
            this.activeOneShot = null;
            this.activeLoopClipName = null;
          }
        } else {
          this.updateGlbLocomotion(speed);
        }

        this.glbMixer.update(dt);
        this.animator?.update({ dt, speed, airborne: false });
      } else if (this.animator) {
        const dt = this.lastAnimTime === null
          ? 0
          : Math.min(0.1, (now - this.lastAnimTime) / 1000);
        this.lastAnimTime = now;
        const speed = this.lastSpeed;
        this.lastSpeed = 0;
        this.animator.update({ dt, speed, airborne: false });
      }
    } else {
      this.object.visible = false;
      this.lastAnimTime = now;
      this.lastSpeed = 0;
    }
  }

  setVisible(v: boolean) {
    this.object.visible = v;
  }

  private hasExplicitLocomotion(): boolean {
    return Boolean(this.findClipName('walk') || this.findClipName('run'));
  }

  private updateGlbLocomotion(speed: number): void {
    if (!this.glbMixer) return;

    const run = this.findClipName('run');
    if (speed > 4.4 && run) {
      this.playLoop(run);
      return;
    }

    const walk = this.findClipName('walk');
    if (speed > 0.12 && walk) {
      this.playLoop(walk);
      return;
    }

    this.playLoop(this.defaultLoopClipName);
  }

  private playLoop(clipName: string | null): void {
    if (!clipName || this.activeLoopClipName === clipName || this.activeOneShot) return;
    const next = this.findAction(clipName);
    if (!next) return;

    const previous = this.activeLoopAction;
    loopAction(next);
    if (previous && previous !== next) previous.fadeOut(0.12);

    this.activeLoopAction = next;
    this.activeLoopClipName = clipName;
  }

  private playOneShot(clipName: string): boolean {
    const action = this.findAction(clipName);
    if (!action) return false;

    if (this.activeOneShot && this.activeOneShot !== action) {
      this.activeOneShot.fadeOut(0.05);
    }
    this.activeLoopAction?.fadeOut(0.06);

    action.reset();
    action.enabled = true;
    action.clampWhenFinished = false;
    action.setLoop(THREE.LoopOnce, 1);
    action.fadeIn(0.05);
    action.play();

    this.activeOneShot = action;
    this.oneShotTime = action.getClip().duration;
    return true;
  }

  private findAction(clipName: string): THREE.AnimationAction | null {
    const exact = this.glbActions.get(clipName);
    if (exact) return exact;
    const lower = clipName.toLowerCase();
    for (const [name, action] of this.glbActions) {
      const normalized = name.toLowerCase();
      if (normalized === lower || normalized.endsWith(`|${lower}`)) {
        return action;
      }
    }
    for (const [name, action] of this.glbActions) {
      if (name.toLowerCase().includes(lower)) {
        return action;
      }
    }
    return null;
  }

  private findClipName(clipName: string): string | null {
    const lower = clipName.toLowerCase();
    for (const name of this.glbActions.keys()) {
      const normalized = name.toLowerCase();
      if (normalized === lower || normalized.endsWith(`|${lower}`)) {
        return name;
      }
    }
    for (const name of this.glbActions.keys()) {
      if (name.toLowerCase().includes(lower)) {
        return name;
      }
    }
    return null;
  }
}

function loopAction(action: THREE.AnimationAction): void {
  action.reset();
  action.enabled = true;
  action.clampWhenFinished = false;
  action.setLoop(THREE.LoopRepeat, Infinity);
  action.fadeIn(0.12);
  action.play();
}

function pickEnemyFallback(spawn: EnemySpawn) {
  if (spawn.assetKey === 'dummy' || /dummy|target/i.test(spawn.name)) {
    return AssetLoader.primitives.dummy;
  }
  if (spawn.archetype === 'caster') return () => AssetLoader.primitives.humanoid(0x4d315c);
  if (spawn.archetype === 'guard' || spawn.archetype === 'captain') return AssetLoader.primitives.npc_guard;
  if (spawn.archetype === 'beast') return () => AssetLoader.primitives.humanoid(0x4f6d31);
  return () => AssetLoader.primitives.humanoid(0x6d3a2a);
}
