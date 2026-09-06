import * as THREE from 'three';
import { buildWorldLifeActor } from './WorldLifeAssets';
import { sampleWorldLifeRoute } from './worldLifeMotion';
import type { WorldLifeActorSpawn, WorldLifeDefinition, WorldLifeEmitterSpawn } from './worldLifeTypes';
import type { AssetLoader } from '../game/AssetLoader';
import { worldLifeCharacterProfile } from './worldLifeModels';
import { CIVIC_WALK_SPEED, createCivicWalkClip } from './CivicLocomotion';

export const WORLD_LIFE_LIMITS = { actors: 48, emitters: 24, particles: 384, distance: 100,
  concurrentModelLoads: 3, nearAnimationHz: 30, farAnimationHz: 15, nearAnimationDistance: 40 } as const;

type GroundHeight = (x: number, z: number) => number;
interface Actor {
  spawn: WorldLifeActorSpawn;
  object: THREE.Group;
  phase: number;
  limbs: Map<string, THREE.Object3D>;
  visual: THREE.Object3D | null;
  ownsVisualResources: boolean;
  rig: AmbientRig | null;
}
interface AmbientRig {
  mixer: THREE.AnimationMixer;
  idle: THREE.AnimationAction;
  walk: THREE.AnimationAction | null;
  moving: boolean;
  fromWeight: number;
  walkWeight: number;
  changedAt: number;
  sampledAt: number;
  walkSpeed: number;
}
interface Emitter {
  spawn: WorldLifeEmitterSpawn;
  object: THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial>;
  positions: THREE.BufferAttribute;
  phase: number;
}

/** Owns only decorative actors/effects; it cannot change combat, NPC or quest state. */
export class WorldLife {
  readonly group = new THREE.Group();
  /** Settles once the bounded initial cast load has completed, including safe fallbacks. */
  readonly ready: Promise<void>;
  private readonly actors: Actor[] = [];
  private readonly emitters: Emitter[] = [];
  private readonly sceneryAnimations: Array<{ object: THREE.Object3D; kind: string; baseScaleY: number; baseRotationZ: number }> = [];
  private elapsed = 0;
  private disposed = false;
  private readonly civicWalkClips = new Map<string, THREE.AnimationClip>();

  constructor(
    scene: THREE.Scene,
    definition: WorldLifeDefinition | undefined,
    private readonly realm: 'aegis' | 'riftbound',
    private readonly groundHeightAt: GroundHeight,
    private readonly scenery: THREE.Object3D[] = [],
    private readonly loader?: AssetLoader,
  ) {
    this.group.name = 'world-life';
    for (const prop of scenery) {
      prop.traverse((object) => {
        const kind = object.userData.worldLifeAnimation;
        if (kind === 'flame' || kind === 'cloth') {
          this.sceneryAnimations.push({ object, kind, baseScaleY: object.scale.y, baseRotationZ: object.rotation.z });
        }
      });
    }
    for (const spawn of (definition?.actors ?? []).slice(0, WORLD_LIFE_LIMITS.actors)) {
      if (!isFinitePoint(spawn) || !['citizen', 'guard', 'deer', 'bird'].includes(spawn.kind)) continue;
      const object = new THREE.Group();
      object.name = spawn.id;
      object.scale.setScalar(finiteClamp(spawn.scale, 1, 0.25, 3));
      const actor: Actor = { spawn, object, limbs: new Map(), phase: seedFor(spawn.id) * 23,
        visual: null, ownsVisualResources: false, rig: null };
      if (!loader || !worldLifeCharacterProfile(spawn, realm)) this.mountFallback(actor);
      this.actors.push(actor);
      this.group.add(object);
    }

    let remainingParticles = WORLD_LIFE_LIMITS.particles as number;
    for (const spawn of (definition?.emitters ?? []).slice(0, WORLD_LIFE_LIMITS.emitters)) {
      if (remainingParticles <= 0) break;
      if (!isFinitePoint(spawn) || !['smoke', 'embers', 'motes'].includes(spawn.kind)) continue;
      const count = Math.min(remainingParticles, Math.floor(finiteClamp(spawn.count, 12, 1, 48)));
      remainingParticles -= count;
      const geometry = new THREE.BufferGeometry();
      const positions = new THREE.BufferAttribute(new Float32Array(count * 3), 3);
      positions.setUsage(THREE.DynamicDrawUsage);
      geometry.setAttribute('position', positions);
      const smoke = spawn.kind === 'smoke';
      const material = new THREE.PointsMaterial({
        color: smoke ? 0x9e968a : spawn.kind === 'embers' ? 0xffad55 : 0xc8d998,
        size: smoke ? 0.85 : spawn.kind === 'embers' ? 0.085 : 0.065,
        transparent: true,
        opacity: smoke ? 0.15 : 0.65,
        depthWrite: false,
        blending: smoke ? THREE.NormalBlending : THREE.AdditiveBlending,
      });
      // Soft round particles without image downloads or one sprite/draw call per mote.
      material.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <opaque_fragment>',
          'diffuseColor.a *= 1.0 - smoothstep(0.12, 0.5, length(gl_PointCoord - vec2(0.5)));\n#include <opaque_fragment>',
        );
      };
      const object = new THREE.Points(geometry, material);
      object.name = spawn.id;
      object.position.set(spawn.x, groundHeightAt(spawn.x, spawn.z) + finiteClamp(spawn.y, 0.5, -10, 50), spawn.z);
      // The bounds cover the entire emitter animation, not its initial zero buffer.
      geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 2, 0), finiteClamp(spawn.radius, 1, 0.1, 20) + 6);
      this.emitters.push({ spawn, object, positions, phase: seedFor(spawn.id) * 10 });
      this.group.add(object);
    }
    scene.add(this.group);
    this.update(0, { x: 0, z: 0 }, WORLD_LIFE_LIMITS.distance);
    this.ready = this.loadReviewedActors();
  }

  private mountFallback(actor: Actor): void {
    const visual = buildWorldLifeActor(actor.spawn.kind, this.realm, actor.spawn.variant ?? 0);
    actor.visual = visual;
    actor.ownsVisualResources = true;
    visual.traverse(node => { if (node.name) actor.limbs.set(node.name, node); });
    actor.object.add(visual);
  }

  private async loadReviewedActors(): Promise<void> {
    if (!this.loader) return;
    const waiting = this.actors.filter(actor => !actor.visual);
    let cursor = 0;
    await Promise.all(Array.from({ length: Math.min(waiting.length, WORLD_LIFE_LIMITS.concurrentModelLoads) }, async () => {
      while (!this.disposed && cursor < waiting.length) await this.loadReviewedActor(waiting[cursor++]);
    }));
  }

  private async loadReviewedActor(actor: Actor): Promise<void> {
    let visual: THREE.Object3D | null = null;
    try {
      const profile = worldLifeCharacterProfile(actor.spawn, this.realm)!;
      const asset = await this.loader!.resolveCharacterAsset(profile);
      if (this.disposed) return;
      if (!asset) { this.mountFallback(actor); return; }
      // Empty loader fallback avoids caching a particular actor's procedural appearance.
      const loaded = await this.loader!.loadModelWithAnimations(asset.model, () => new THREE.Group());
      visual = loaded.object;
      if (this.disposed) { releaseActorSkeletons(visual); return; }
      let clips = loaded.animations;
      if (asset.animationPack) {
        const packed = await this.loader!.loadCharacterAnimations(asset, visual);
        if (packed.length) clips = packed;
      }
      if (this.disposed) { releaseActorSkeletons(visual); return; }
      const idle = clips.find(clip => clip.name.toLowerCase() === 'idle');
      let hasMesh = false;
      visual.traverse(node => { if ((node as THREE.Mesh).isMesh) hasMesh = true; });
      if (!hasMesh || !idle || !Number.isFinite(idle.duration) || idle.duration <= 0) {
        releaseActorSkeletons(visual);
        this.mountFallback(actor);
        return;
      }
      let walk = clips.find(clip => clip.name.toLowerCase() === 'walk');
      if (walk && (!Number.isFinite(walk.duration) || walk.duration <= 0)) walk = undefined;
      const civic = asset.skeletonId === 'aegis_people_v1';
      if (!walk && civic) {
        walk = this.civicWalkClips.get(asset.model);
        if (!walk) {
          walk = createCivicWalkClip(visual) ?? undefined;
          if (walk) this.civicWalkClips.set(asset.model, walk);
        }
      }
      const mixer = new THREE.AnimationMixer(visual);
      const idleAction = mixer.clipAction(idle).setLoop(THREE.LoopRepeat, Infinity).play();
      const walkAction = walk ? mixer.clipAction(walk).setLoop(THREE.LoopRepeat, Infinity).setEffectiveWeight(0).play() : null;
      actor.rig = { mixer, idle: idleAction, walk: walkAction, moving: false,
        fromWeight: 0, walkWeight: 0, changedAt: this.elapsed, sampledAt: -Infinity, walkSpeed: civic ? CIVIC_WALK_SPEED : 2.4 };
      actor.visual = visual;
      actor.object.userData.characterProfileKey = profile;
      actor.object.userData.characterModel = asset.model;
      actor.object.add(visual);
      // Establish a relaxed pose before the first frame after the asynchronous mount.
      this.sampleRig(actor, false, 0, this.elapsed + actor.phase, true);
    } catch {
      if (actor.rig) {
        actor.rig.mixer.stopAllAction();
        actor.rig.mixer.uncacheRoot(actor.rig.mixer.getRoot());
        actor.rig = null;
      }
      if (visual) { visual.removeFromParent(); releaseActorSkeletons(visual); }
      actor.visual = null;
      if (!this.disposed) this.mountFallback(actor);
    }
  }

  private sampleRig(actor: Actor, moving: boolean, speed: number, time: number, immediately: boolean): void {
    const rig = actor.rig!;
    moving &&= Boolean(rig.walk);
    if (moving !== rig.moving) {
      rig.fromWeight = immediately ? Number(moving) : rig.walkWeight;
      rig.moving = moving;
      rig.changedAt = this.elapsed;
    }
    rig.walkWeight = THREE.MathUtils.lerp(rig.fromWeight, Number(moving), Math.min(1, (this.elapsed - rig.changedAt) / .18));
    rig.idle.setEffectiveWeight(1 - rig.walkWeight);
    rig.idle.time = time % rig.idle.getClip().duration;
    if (rig.walk) {
      rig.walk.setEffectiveWeight(rig.walkWeight);
      rig.walk.time = time * speed / (rig.walkSpeed * actor.object.scale.x) % rig.walk.getClip().duration;
    }
    rig.mixer.update(0);
    rig.sampledAt = this.elapsed;
  }

  update(dt: number, viewer: { x: number; z: number }, viewDistance: number): void {
    if (this.disposed) return;
    this.elapsed += Number.isFinite(dt) ? Math.max(0, dt) : 0;
    const distance = finiteClamp(viewDistance, WORLD_LIFE_LIMITS.distance, 15, WORLD_LIFE_LIMITS.distance);
    const distanceSq = distance * distance;
    for (const animation of this.sceneryAnimations) {
      if (animation.kind === 'flame') {
        animation.object.scale.y = animation.baseScaleY * (1 + Math.sin(this.elapsed * 11) * 0.12);
      } else {
        animation.object.rotation.z = animation.baseRotationZ + Math.sin(this.elapsed * 1.5 + animation.object.position.x) * 0.045;
      }
    }
    for (const actor of this.actors) {
      const { spawn, object, phase, limbs } = actor;
      const time = this.elapsed + phase;
      const speed = actor.rig && !actor.rig.walk ? 0 : finiteClamp(spawn.speed, spawn.kind === 'bird' ? 3 : 0.9, 0, 6);
      const movement = sampleWorldLifeRoute(spawn, spawn.route, time, speed,
        finiteClamp(spawn.pauseSeconds, spawn.kind === 'bird' ? 0 : 3, 0, 60));
      object.position.x = movement.x;
      object.position.z = movement.z;
      const wasVisible = object.visible;
      const actorDistanceSq = squaredDistance(object.position, viewer);
      object.visible = actorDistanceSq <= distanceSq;
      // Absolute-time sampling keeps distant actors on schedule without ticking their rigs.
      if (!object.visible) continue;
      const bird = spawn.kind === 'bird';
      object.position.y = this.groundHeightAt(movement.x, movement.z)
        + (bird ? 7 + Math.sin(time * 0.7) * 0.7 + phase % 4 : 0);
      object.rotation.y = movement.heading;
      if (actor.rig) {
        const hz = actorDistanceSq <= WORLD_LIFE_LIMITS.nearAnimationDistance ** 2
          ? WORLD_LIFE_LIMITS.nearAnimationHz : WORLD_LIFE_LIMITS.farAnimationHz;
        if (!wasVisible || movement.moving !== actor.rig.moving || this.elapsed - actor.rig.sampledAt >= 1 / hz) {
          this.sampleRig(actor, movement.moving, speed, time, !wasVisible);
        }
        continue;
      }
      const stride = movement.moving ? Math.sin(time * (spawn.kind === 'deer' ? 7 : 5)) * 0.45 : 0;
      setRotation(limbs, 'leg-left', 'x', stride);
      setRotation(limbs, 'leg-right', 'x', -stride);
      setRotation(limbs, 'arm-left', 'x', -stride * 0.65);
      setRotation(limbs, 'arm-right', 'x', stride * 0.65);
      setRotation(limbs, 'leg-back-left', 'x', -stride);
      setRotation(limbs, 'leg-back-right', 'x', stride);
      setRotation(limbs, 'wing-left', 'z', Math.sin(time * 8) * 0.5);
      setRotation(limbs, 'wing-right', 'z', -Math.sin(time * 8) * 0.5);
      setRotation(limbs, 'head', 'x', spawn.kind === 'deer' && !movement.moving ? 0.25 + Math.sin(time) * 0.12 : 0);
      if (!movement.moving && !bird) object.rotation.y += Math.sin(time * 0.4) * 0.08;
    }
    for (const emitter of this.emitters) {
      const { spawn, object, phase, positions } = emitter;
      object.visible = squaredDistance(object.position, viewer) <= distanceSq;
      if (!object.visible) continue;
      const time = this.elapsed + phase;
      const radius = finiteClamp(spawn.radius, 1, 0.1, 20);
      for (let index = 0; index < positions.count; index += 1) {
        const angle = index * 2.39996 + phase;
        const life = (time * (spawn.kind === 'embers' ? 0.55 : 0.16) + index / positions.count) % 1;
        const spread = radius * (spawn.kind === 'smoke' ? 0.2 + life * 0.8 : 1);
        positions.setXYZ(index,
          Math.cos(angle + time * 0.14) * spread + (spawn.kind === 'smoke' ? life * 1.4 : 0),
          spawn.kind === 'motes' ? 0.6 + Math.sin(time * 0.6 + index) * 0.4 : life * (spawn.kind === 'smoke' ? 5 : 2.5),
          Math.sin(angle + time * 0.14) * spread);
      }
      positions.needsUpdate = true;
    }
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.group.removeFromParent();
    // Geometry/materials/textures belong to AssetLoader's cache; only cloned skeletons
    // and animation bindings belong to an individual loaded ambient actor.
    for (const actor of this.actors) {
      if (actor.rig) {
        actor.rig.mixer.stopAllAction();
        actor.rig.mixer.uncacheRoot(actor.rig.mixer.getRoot());
      }
      if (actor.visual && !actor.ownsVisualResources) {
        releaseActorSkeletons(actor.visual);
        actor.visual.removeFromParent();
      }
    }
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    const collectResources = (node: THREE.Object3D) => {
      const renderable = node as THREE.Mesh;
      if (renderable.geometry) geometries.add(renderable.geometry);
      if (renderable.material) {
        for (const material of Array.isArray(renderable.material) ? renderable.material : [renderable.material]) materials.add(material);
      }
    };
    this.group.traverse(collectResources);
    // These are independently built fallback props, never loader-cached GLB resources.
    for (const prop of this.scenery) {
      prop.removeFromParent();
      prop.traverse(collectResources);
    }
    for (const geometry of geometries) geometry.dispose();
    for (const material of materials) material.dispose();
    this.group.clear();
    this.actors.length = 0;
    this.emitters.length = 0;
    this.sceneryAnimations.length = 0;
    this.civicWalkClips.clear();
  }
}

function releaseActorSkeletons(root: THREE.Object3D): void {
  const skeletons = new Set<THREE.Skeleton>();
  root.traverse(node => { if ((node as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((node as THREE.SkinnedMesh).skeleton); });
  for (const skeleton of skeletons) skeleton.dispose();
}

function setRotation(limbs: Map<string, THREE.Object3D>, name: string, axis: 'x' | 'z', value: number): void {
  const limb = limbs.get(name);
  if (limb) limb.rotation[axis] = value;
}
function squaredDistance(a: { x: number; z: number }, b: { x: number; z: number }): number {
  return (a.x - b.x) ** 2 + (a.z - b.z) ** 2;
}
function isFinitePoint(point: { x: number; z: number }): boolean {
  return Number.isFinite(point.x) && Number.isFinite(point.z);
}
function finiteClamp(value: number | undefined, fallback: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value! : fallback));
}
function seedFor(id: string): number {
  let hash = 2166136261;
  for (const character of id) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (hash >>> 0) / 4294967296;
}
