import * as THREE from 'three';
import { AssetLoader, type CharacterAssetResolution } from '../AssetLoader';
import { Terrain } from '../../world/Terrain';
import { loadZone, type ZoneDefinition, type PropSpawn } from '../../world/ZoneLoader';
import type { WorldSnapshot, Position } from '../../shared/orvr/protocol';
import type { CampaignConnection } from './CampaignConnection';
import { assembleCampaignEquipment, campaignAnimationClips, campaignNpcProfile, resolveCampaignEquipment, type CampaignEquipmentModule } from './CampaignCharacterPresentation';
import { StaticPropInstances } from '../StaticPropInstances';
import { frontierPropDistances } from '../../world/FrontierProps';
import { campaignGateBindings, campaignGateVisible, sceneryDistanceLod, type CampaignGateBinding } from './CampaignSceneryPresentation';

/** One queue bounds GLB parsing across all chunks and actors in a stage. */
export class CampaignAssetQueue {
  private active = 0;
  private closed = false;
  private waiting: Array<{ start: () => void; cancel: () => void }> = [];
  constructor(private readonly limit = 4) {}
  run<T>(task: () => Promise<T>, priority = false): Promise<T> {
    return new Promise((resolve, reject) => {
      if (this.closed) { reject(new Error('Campaign stage released')); return; }
      const job = {
        start: () => {
          this.active++;
          void Promise.resolve().then(task).then(resolve, reject).finally(() => { this.active--; this.pump(); });
        },
        cancel: () => reject(new Error('Campaign stage released')),
      };
      if (priority) this.waiting.unshift(job); else this.waiting.push(job);
      this.pump();
    });
  }
  private pump(): void { while (!this.closed && this.active < this.limit && this.waiting.length) this.waiting.shift()!.start(); }
  close(): void { this.closed = true; for (const job of this.waiting) job.cancel(); this.waiting.length = 0; }
}

export function campaignLodLevel(distance: number, levels: number, actor = false): number {
  const desired = actor ? distance < 30 ? 0 : distance < 95 ? 1 : 2 : distance < 90 ? 0 : distance < 240 ? 1 : 2;
  return Math.max(0, Math.min(desired, levels - 1));
}

export function campaignChunkDistance(chunk: { x: number; z: number }, position: { x: number; z: number }): number {
  return Math.hypot(Math.max(0, Math.abs(chunk.x - position.x) - 150), Math.max(0, Math.abs(chunk.z - position.z) - 150));
}

/** Sky colors describe the atmosphere; terrain/soil palettes must never color the whole sky. */
function campaignAtmosphere(biomeId?: string, season?: string): { sky: string; fog: string; sun: string; ground: string } {
  const climates: Record<string, 'temperate' | 'wetland' | 'alpine' | 'dry' | 'volcanic'> = {
    temperate_farmland: 'temperate', temperate_floodplain: 'temperate', cool_old_growth: 'temperate',
    freshwater_fen: 'wetland', clear_river_valley: 'temperate', alpine_foothills: 'alpine',
    geothermal_marsh: 'wetland', drowned_forest: 'wetland', wet_moorland: 'wetland',
    semiarid_steppe: 'dry', cold_conifer_pass: 'alpine', volcanic_badlands: 'volcanic',
    fortified_highlands: 'temperate', temperate_frontier: 'temperate', dry_war_frontier: 'dry',
    volcanic_highlands: 'volcanic', alpine_fortress: 'alpine', volcanic_fortress: 'volcanic',
  };
  const profiles = {
    temperate: { sky: '#819bb8', fog: '#b0bece', sun: '#fff2da', ground: '#53504a' },
    wetland: { sky: '#8b9fac', fog: '#b0bec4', sun: '#eef2ee', ground: '#49514b' },
    alpine: { sky: '#8ca9c4', fog: '#c4d3de', sun: '#eff5ff', ground: '#68737a' },
    dry: { sky: '#8a9db4', fog: '#c3bdb1', sun: '#fff0d8', ground: '#655546' },
    volcanic: { sky: '#7b8799', fog: '#a2a4ac', sun: '#f5ddca', ground: '#51494a' },
  };
  return profiles[climates[biomeId ?? ''] ?? (season === 'winter' ? 'alpine' : 'temperate')];
}

/** Metallic equipment needs reflected sky/ground light as well as the direct sun. */
function campaignEnvironment(renderer: THREE.WebGLRenderer, atmosphere: ReturnType<typeof campaignAtmosphere>): THREE.WebGLRenderTarget {
  const width = 64, height = 32, pixels = new Float32Array(width * height * 4);
  const sky = new THREE.Color(atmosphere.sky), horizon = new THREE.Color(atmosphere.fog), ground = new THREE.Color(atmosphere.ground);
  const color = new THREE.Color();
  for (let y = 0; y < height; y++) {
    const elevation = -Math.cos(y / (height - 1) * Math.PI);
    color.copy(horizon).lerp(elevation >= 0 ? sky : ground, Math.sqrt(Math.abs(elevation)));
    for (let x = 0; x < width; x++) pixels.set([color.r, color.g, color.b, 1], (y * width + x) * 4);
  }
  const texture = new THREE.DataTexture(pixels, width, height, THREE.RGBAFormat, THREE.FloatType);
  texture.mapping = THREE.EquirectangularReflectionMapping; texture.needsUpdate = true;
  const generator = new THREE.PMREMGenerator(renderer);
  try { return generator.fromEquirectangular(texture); }
  finally { generator.dispose(); texture.dispose(); }
}

/** Skeleton clones own bone textures; geometry/materials remain owned by their shared loader. */
export function releaseCampaignActor(root: THREE.Object3D, mixers: THREE.AnimationMixer[] = []): void {
  for (const mixer of mixers) { mixer.stopAllAction(); mixer.uncacheRoot(mixer.getRoot()); }
  const skeletons = new Set<THREE.Skeleton>();
  root.traverse(object => { if ((object as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((object as THREE.SkinnedMesh).skeleton); });
  for (const skeleton of skeletons) skeleton.dispose();
  root.removeFromParent();
}

interface Visual { object: THREE.Object3D; mixer?: THREE.AnimationMixer; moving?: THREE.AnimationAction; idle?: THREE.AnimationAction }
interface Actor {
  object: THREE.Group; target: THREE.Vector3; signature: string; models: string[]; asset?: CharacterAssetResolution;
  levels: Map<number, Visual>; pending: Set<number>; failed: Set<number>; selected: number; desired: number; valid: boolean; moving: boolean;
  animationTime: number; animationAccumulator: number;
  equipment: CampaignEquipmentModule[];
}
interface ActorDescription { id: string; position: Position; profile?: string; staticKey?: string; self: boolean; signature: string; selectable?: boolean; facing?: number }
interface Scenery { object: THREE.Group; models: string[]; levels: Map<number, THREE.Object3D>; pending: Set<number>; failed: Set<number>; selected: number; desired: number; batchable: boolean; distances: number[]; cull: number; inRange: boolean; gate?: CampaignGateBinding }
interface Chunk { x: number; z: number; props: PropSpawn[]; group: THREE.Group; loaded: boolean; loading: boolean; loader: AssetLoader | null; instances: Scenery[]; batches?: StaticPropInstances }
interface Stage {
  id: string; scene: THREE.Scene; loader: AssetLoader; terrain: Terrain; map: ZoneDefinition; chunks: Chunk[];
  sun: THREE.DirectionalLight;
  environment: THREE.WebGLRenderTarget;
  actors: Map<string, Actor>; pending: Set<string>; unavailable: Map<string, string>; desiredActors: Map<string, ActorDescription>;
  queue: CampaignAssetQueue; generation: number;
  gates: Map<string, CampaignGateBinding>;
}
const emptyModel = () => new THREE.Group();
const hasMesh = (root: THREE.Object3D) => { let found = false; root.traverse(object => { if ((object as THREE.Mesh).isMesh) found = true; }); return found; };

/** Presentation only: authoritative movement, captures, damage and supplies run on the server. */
export class SharedCampaignRenderer {
  private renderer: THREE.WebGLRenderer;
  private camera = new THREE.PerspectiveCamera(55, 1, .15, 1100);
  private stage: Stage | null = null;
  private snapshot: WorldSnapshot | null = null;
  private loadingId = '';
  private generation = 0;
  private disposed = false;
  private keys = new Set<string>();
  private yaw = 0;
  private pitch = .48;
  private zoom = 16;
  private orbiting = false;
  private clock = new THREE.Clock();
  private moveClock = 0;
  private streamingClock = 0;
  private cameraTarget = new THREE.Vector3();
  private previousPosition = new THREE.Vector3();
  private selfPosition = new THREE.Vector3();
  private observer: ResizeObserver;
  onTarget: (id: string | null) => void = () => undefined;
  onNotice: (message: string) => void = () => undefined;
  constructor(private readonly container: HTMLElement, private readonly connection: CampaignConnection) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.domElement.tabIndex = 0;
    this.renderer.domElement.setAttribute('aria-label', 'Shared campaign world. Use WASD to move, right drag to look, click a target.');
    container.append(this.renderer.domElement);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(container); this.resize();
    window.addEventListener('keydown', this.keyDown); window.addEventListener('keyup', this.keyUp);
    window.addEventListener('blur', this.blur);
    this.renderer.domElement.addEventListener('pointerdown', this.pointerDown);
    window.addEventListener('pointermove', this.pointerMove); window.addEventListener('pointerup', this.pointerUp);
    this.renderer.domElement.addEventListener('wheel', this.wheel, { passive: false });
    this.renderer.domElement.addEventListener('contextmenu', this.contextMenu);
    this.renderer.setAnimationLoop(this.frame);
  }
  update(snapshot: WorldSnapshot): void {
    this.snapshot = snapshot;
    if (snapshot.zone && snapshot.zone.id !== this.stage?.id && snapshot.zone.id !== this.loadingId) void this.load(snapshot.zone.id);
    if (snapshot.self && this.stage?.id === snapshot.self.zoneId) this.updateActors();
  }
  private async load(id: string): Promise<void> {
    const generation = ++this.generation;
    this.loadingId = id;
    const loader = new AssetLoader();
    const scene = new THREE.Scene();
    let environment: THREE.WebGLRenderTarget | undefined;
    try {
      const map = await loadZone(id);
      if (this.disposed || generation !== this.generation) { loader.dispose(scene); return; }
      const palette = map.orvrLayout?.biome.palette;
      const atmosphere = campaignAtmosphere(map.orvrLayout?.biome.id, map.orvrLayout?.biome.season);
      environment = campaignEnvironment(this.renderer, atmosphere);
      scene.environment = environment.texture;
      scene.background = new THREE.Color(atmosphere.sky);
      scene.fog = new THREE.Fog(map.atmosphere?.fogColor ?? atmosphere.fog, 380, 850);
      scene.add(new THREE.HemisphereLight('#bdd3ec', atmosphere.ground, .75));
      const sun = new THREE.DirectionalLight(map.atmosphere?.sunColor ?? atmosphere.sun, map.atmosphere?.sunIntensity ?? 1.8); sun.position.set(-70, 110, -55);
      sun.castShadow = true;
      sun.shadow.mapSize.set(2048, 2048);
      Object.assign(sun.shadow.camera, { left: -70, right: 70, top: 70, bottom: -70, near: 1, far: 300 });
      sun.shadow.camera.updateProjectionMatrix();
      sun.shadow.bias = -.0002; sun.shadow.normalBias = .06;
      scene.add(sun, sun.target);
      const opts = {
        size: map.size, segments: map.segments, flatTerrain: map.flatTerrain, model: map.terrainModel,
        canals: map.canals, cityElevation: map.cityElevation, authoredCrater: Boolean(map.craterCity),
        orvrTerrain: map.orvrLayout?.terrain, biomePalette: palette, authoredChunks: map.orvrLayout?.terrain.chunks,
        roads: map.orvrLayout ? map.paths : undefined,
      };
      const terrain = new Terrain(opts);
      scene.add(await terrain.build(loader, opts));
      const buckets = new Map<string, Chunk>();
      for (const prop of map.props ?? []) {
        if (prop.visible === false || (!prop.model && !prop.assetKey)) continue;
        const x = Math.floor((prop.x + map.size / 2) / 300) * 300 - map.size / 2 + 150;
        const z = Math.floor((prop.z + map.size / 2) / 300) * 300 - map.size / 2 + 150;
        const key = `${x}:${z}`;
        if (!buckets.has(key)) {
          const group = new THREE.Group(); scene.add(group);
          buckets.set(key, { x, z, props: [], group, loaded: false, loading: false, loader: null, instances: [] });
        }
        buckets.get(key)!.props.push(prop);
      }
      const next: Stage = {
        id, scene, loader, terrain, map, sun, environment, chunks: [...buckets.values()], actors: new Map(), pending: new Set(),
        unavailable: new Map(), desiredActors: new Map(), queue: new CampaignAssetQueue(4), generation, gates: campaignGateBindings(map.orvrLayout),
      };
      if (this.disposed || generation !== this.generation || this.snapshot?.zone?.id !== id) { scene.environment = null; environment.dispose(); loader.dispose(scene); return; }
      const previous = this.stage; this.stage = next;
      if (this.snapshot.self) this.cameraTarget.set(this.snapshot.self.position.x, this.snapshot.self.position.y, this.snapshot.self.position.z);
      if (previous) this.releaseStage(previous);
      this.updateActors(); this.stream();
      this.onNotice(map.orvrLayout?.status === 'complete' ? '' : 'Campaign playtest · replacement environment art is still in production.');
    } catch (error) {
      scene.environment = null; environment?.dispose();
      loader.dispose(scene);
      if (!this.disposed && generation === this.generation) this.onNotice(`Unable to load this zone: ${error instanceof Error ? error.message : 'asset error'}`);
    } finally { if (generation === this.generation) this.loadingId = ''; }
  }
  private async sceneryModels(loader: AssetLoader, prop: PropSpawn): Promise<string[]> {
    const frontier = prop.assetKey?.startsWith('frontier_') || /(?:^|\/)(?:prop_)?frontier_[^/]+\.glb$/i.test(prop.model ?? '');
    if (frontier) return prop.assetKey ? loader.resolveApprovedAssetModels(prop.assetKey, 'staticProps') : [];
    if (prop.assetKey) {
      const reviewed = await loader.resolveApprovedAssetModels(prop.assetKey, 'staticProps');
      if (reviewed.length) return reviewed;
    }
    const filename = prop.model ?? await loader.resolveStaticModel(prop.assetKey!, '');
    return filename ? [...new Set([filename, ...(prop.lodModels ?? [])])] : [];
  }
  private async loadChunk(stage: Stage, chunk: Chunk): Promise<void> {
    chunk.loading = true;
    const loader = new AssetLoader(); chunk.loader = loader;
    try {
      for (let offset = 0; offset < chunk.props.length; offset += 4) {
        if (this.disposed || stage !== this.stage || chunk.loader !== loader) return;
        await Promise.all(chunk.props.slice(offset, offset + 4).map(async prop => {
          const models = await stage.queue.run(() => this.sceneryModels(loader, prop));
          if (!models.length || stage !== this.stage || this.disposed || chunk.loader !== loader) return;
          const object = new THREE.Group(); object.name = prop.id ?? models[0];
          object.position.set(prop.x, (prop.heightMode === 'absolute' ? 0 : stage.terrain.heightAt(prop.x, prop.z)) + (prop.y ?? 0), prop.z);
          object.rotation.set(prop.rotX ?? 0, prop.rotY ?? 0, prop.rotZ ?? 0);
          object.scale.set((prop.scale ?? 1) * (prop.scaleX ?? 1), (prop.scale ?? 1) * (prop.scaleY ?? 1), (prop.scale ?? 1) * (prop.scaleZ ?? 1));
          const gate = stage.gates.get(prop.id ?? '');
          const policy = prop.assetKey?.startsWith('frontier_') ? frontierPropDistances(prop.assetKey) : { lod: [0, 90, 240], cull: Infinity };
          const instance: Scenery = { object, models, levels: new Map(), pending: new Set(), failed: new Set(), selected: -1, desired: 0,
            batchable: Boolean(prop.assetKey?.startsWith('frontier_') && !prop.interaction && !gate), gate,
            distances: policy.lod, cull: policy.cull, inRange: true };
          chunk.instances.push(instance); chunk.group.add(object);
          const position = this.snapshot?.self?.position ?? object.position;
          const distance = Math.hypot(prop.x - position.x, prop.z - position.z);
          instance.desired = sceneryDistanceLod(distance, models.length, instance.distances);
          instance.inRange = distance < instance.cull;
          object.visible = instance.inRange && (!gate || campaignGateVisible(gate, this.snapshot?.zone?.keeps ?? {}));
          if (object.visible) await this.loadSceneryLevel(stage, chunk, instance, instance.desired);
        }));
      }
      if (chunk.loader === loader) chunk.loaded = true;
    } catch { /* Unavailable optional meshes remain absent; no visible substitute is generated. */ }
    finally { if (chunk.loader === loader) { chunk.loading = false; chunk.loaded = true; } }
  }
  private async loadSceneryLevel(stage: Stage, chunk: Chunk, instance: Scenery, level: number): Promise<void> {
    if (instance.pending.has(level) || instance.failed.has(level) || !chunk.loader) return;
    const existing = instance.levels.get(level);
    if (existing) { this.selectSceneryLevel(instance, level); return; }
    const loader = chunk.loader; instance.pending.add(level);
    try {
      const object = await stage.queue.run(() => loader.loadModel(instance.models[level], emptyModel));
      if (stage !== this.stage || this.disposed || chunk.loader !== loader) { releaseCampaignActor(object); return; }
      if (!hasMesh(object)) throw new Error('Reviewed scenery model unavailable');
      object.visible = false; instance.object.add(object); instance.levels.set(level, object);
      if (instance.desired === level || instance.selected < 0) this.selectSceneryLevel(instance, level);
    } catch { instance.failed.add(level); }
    finally { instance.pending.delete(level); }
    if (instance.selected < 0) {
      const alternative = instance.models.findIndex((_, index) => !instance.failed.has(index) && !instance.pending.has(index));
      if (alternative >= 0) await this.loadSceneryLevel(stage, chunk, instance, alternative);
    }
  }
  private selectSceneryLevel(instance: Scenery, level: number): void {
    instance.selected = level;
    for (const [index, object] of instance.levels) object.visible = index === level;
  }
  private unloadChunk(chunk: Chunk): void {
    chunk.batches?.dispose(); chunk.batches = undefined;
    const loader = chunk.loader; chunk.loader = null;
    if (loader) loader.dispose(chunk.group);
    chunk.group.clear(); chunk.instances.length = 0; chunk.loaded = false; chunk.loading = false;
  }
  private stream(): void {
    const stage = this.stage, self = this.snapshot?.self;
    if (!stage || !self || self.zoneId !== stage.id) return;
    const chunks = [...stage.chunks].sort((a, b) => campaignChunkDistance(a, self.position) - campaignChunkDistance(b, self.position));
    for (const chunk of chunks) {
      const distance = campaignChunkDistance(chunk, self.position);
      chunk.group.visible = distance < 500;
      if (distance > 650) { if (chunk.loader) this.unloadChunk(chunk); continue; }
      if (distance < 360 && !chunk.loaded && !chunk.loading) void this.loadChunk(stage, chunk);
      if (!chunk.group.visible) continue;
      for (const instance of chunk.instances) {
        const distance = Math.hypot(instance.object.position.x - self.position.x, instance.object.position.z - self.position.z);
        instance.desired = sceneryDistanceLod(distance, instance.models.length, instance.distances);
        instance.inRange = distance < instance.cull;
        instance.object.visible = instance.inRange && (!instance.gate || campaignGateVisible(instance.gate, this.snapshot?.zone?.keeps ?? {}));
        if (instance.object.visible && instance.selected !== instance.desired) void this.loadSceneryLevel(stage, chunk, instance, instance.desired);
      }
      chunk.batches ??= new StaticPropInstances(chunk.group);
      chunk.batches.update(chunk.instances.filter(instance => instance.batchable && instance.inRange).map(instance => instance.object));
      for (const instance of chunk.instances) if (!instance.inRange) instance.object.visible = false;
    }
    for (const [id, actor] of stage.actors) {
      const distance = id === self.id ? 0 : Math.hypot(actor.target.x - self.position.x, actor.target.z - self.position.z);
      actor.object.visible = distance < 450;
      actor.desired = campaignLodLevel(distance, actor.models.length, true);
      if (actor.object.visible && actor.selected !== actor.desired) void this.loadActorLevel(stage, actor, actor.desired);
    }
  }
  private updateActors(): void {
    const stage = this.stage, snapshot = this.snapshot;
    if (!stage || !snapshot?.zone || snapshot.zone.id !== stage.id) return;
    for (const chunk of stage.chunks) for (const instance of chunk.instances) if (instance.gate) {
      instance.object.visible = instance.inRange && campaignGateVisible(instance.gate, snapshot.zone.keeps);
    }
    const wanted = new Map<string, ActorDescription>();
    const add = (id: string, position: Position, profile: string | undefined, health: number, self = false, staticKey?: string) => {
      if (health > 0) wanted.set(id, { id, position, profile, staticKey, self, signature: staticKey ?? profile ?? '' });
    };
    for (const player of snapshot.players) add(player.id, player.position, player.avatarProfileKey, player.health, player.id === snapshot.self?.id);
    if (snapshot.self && !wanted.has(snapshot.self.id)) add(snapshot.self.id, snapshot.self.position, snapshot.self.avatarProfileKey, snapshot.self.health, true);
    const assignments = stage.map.orvrLayout?.populationAssignments ?? [];
    for (const npc of Object.values(snapshot.zone.npcs)) {
      const assignment = assignments.find(entry => entry.entityId === npc.id) ?? (npc.objectiveId
        ? assignments.find(entry => entry.entityId.startsWith(npc.objectiveId!.replace(/_objective$/, '') + '_') && entry.role === 'guard')
        : undefined);
      const profile = campaignNpcProfile({ id: npc.id, role: npc.kind, race: assignment?.race, realm: npc.realm })
        ?? campaignNpcProfile({ id: npc.id, role: npc.kind, realm: npc.realm });
      if (profile) add(npc.id, npc.position, profile, npc.health);
    }
    // Authored service populations have no local combat authority and cannot be selected as PvP targets.
    for (const npc of stage.map.npcs ?? []) {
      if (snapshot.zone.npcs[npc.id]) continue;
      const self = snapshot.self?.position;
      if (!self || Math.hypot(npc.x - self.x, npc.z - self.z) > 260) continue;
      const assignment = assignments.find(entry => entry.entityId === npc.id);
      const profile = campaignNpcProfile({ id: npc.id, role: assignment?.role ?? npc.role, race: assignment?.race, profileKey: npc.characterProfileKey });
      if (!profile) continue;
      const id = `population:${npc.id}`;
      const y = (npc.heightMode === 'absolute' ? 0 : stage.terrain.heightAt(npc.x, npc.z)) + (npc.y ?? 0);
      wanted.set(id, { id, position: { x: npc.x, y, z: npc.z }, profile, self: false, signature: profile, selectable: false, facing: npc.rotY ?? 0 });
    }
    for (const wagon of Object.values(snapshot.zone.caravans)) if (wagon.status === 'moving' || wagon.status === 'waiting') add(wagon.id, wagon.position, undefined, wagon.health, false, 'frontier_supply_wagon');
    const equipmentKeys = { ram: 'frontier_battering_ram', oil: 'frontier_oil_cauldron', catapult: 'frontier_field_catapult' };
    for (const machine of Object.values(snapshot.zone.equipment)) add(machine.id, machine.position, undefined, machine.health, false, equipmentKeys[machine.kind]);
    stage.desiredActors = wanted;
    for (const [id, actor] of stage.actors) if (!wanted.has(id) || wanted.get(id)!.signature !== actor.signature) {
      this.releaseActor(actor); stage.actors.delete(id);
    }
    for (const [id, description] of wanted) {
      const actor = stage.actors.get(id);
      if (actor) { actor.target.set(description.position.x, description.position.y, description.position.z); continue; }
      if (!stage.pending.has(id) && stage.unavailable.get(id) !== description.signature) void this.createActor(stage, description);
    }
  }
  private async createActor(stage: Stage, description: ActorDescription): Promise<void> {
    const { id } = description;
    stage.pending.add(id);
    let actor: Actor | undefined;
    try {
      const asset = description.staticKey ? undefined : await stage.queue.run(() => stage.loader.resolveCharacterAsset(description.profile ?? ''), true);
      let models: string[];
      if (description.staticKey) models = await stage.loader.resolveApprovedAssetModels(description.staticKey, 'staticProps');
      else if (asset) {
        models = await stage.loader.resolveApprovedAssetModels(description.profile ?? '', 'characterProfiles');
      } else models = [];
      if (!models.length) { stage.unavailable.set(id, description.signature); return; }
      const equipment = asset ? await resolveCampaignEquipment(stage.loader, description.profile ?? '', asset) : [];
      const latest = stage.desiredActors.get(id);
      if (!latest || latest.signature !== description.signature || stage !== this.stage || this.disposed) return;
      const object = new THREE.Group();
      if (description.selectable !== false) object.userData.campaignEntityId = id;
      object.rotation.y = description.facing ?? 0;
      object.position.set(latest.position.x, latest.position.y, latest.position.z);
      actor = {
        object, target: object.position.clone(), signature: description.signature, models, asset: asset ?? undefined,
        levels: new Map(), pending: new Set(), failed: new Set(), selected: -1, desired: 0, valid: true, moving: false, animationTime: 0, animationAccumulator: 0, equipment,
      };
      const self = this.snapshot?.self?.position ?? latest.position;
      actor.desired = campaignLodLevel(description.self ? 0 : Math.hypot(latest.position.x - self.x, latest.position.z - self.z), models.length, true);
      await this.loadActorLevel(stage, actor, actor.desired);
      const current = stage.desiredActors.get(id);
      if (actor.selected < 0 || !current || current.signature !== description.signature || stage !== this.stage || this.disposed) {
        this.releaseActor(actor); stage.unavailable.set(id, description.signature); return;
      }
      actor.target.set(current.position.x, current.position.y, current.position.z); actor.object.position.copy(actor.target);
      stage.actors.set(id, actor); stage.scene.add(object);
    } catch {
      if (actor) this.releaseActor(actor);
      if (stage === this.stage && !this.disposed) stage.unavailable.set(id, description.signature);
    } finally { stage.pending.delete(id); }
  }
  private async loadActorLevel(stage: Stage, actor: Actor, level: number): Promise<void> {
    if (!actor.valid || actor.pending.has(level) || actor.failed.has(level)) return;
    const existing = actor.levels.get(level);
    if (existing) { this.selectActorLevel(actor, level); return; }
    actor.pending.add(level);
    let object: THREE.Object3D | undefined;
    try {
      const loaded = await stage.queue.run(() => stage.loader.loadModelFull(actor.models[level], emptyModel), true);
      object = loaded.object;
      if (!actor.valid || stage !== this.stage || this.disposed) { releaseCampaignActor(object); return; }
      if (!hasMesh(object)) throw new Error('Reviewed actor model unavailable');
      await assembleCampaignEquipment(object, actor.equipment, level, stage.loader,
        load => stage.queue.run(load, true), () => actor.valid && stage === this.stage && !this.disposed);
      const pack = actor.asset ? await stage.queue.run(() => stage.loader.loadCharacterAnimations(actor.asset!, object!), true) : [];
      if (!actor.valid || stage !== this.stage || this.disposed) { releaseCampaignActor(object); return; }
      const clips = campaignAnimationClips(loaded.animations, pack);
      const mixer = clips.length ? new THREE.AnimationMixer(object) : undefined;
      const idle = clips.find(clip => /^idle$/i.test(clip.name)) ?? clips.find(clip => /idle/i.test(clip.name));
      const moving = clips.find(clip => /^run$/i.test(clip.name)) ?? clips.find(clip => /walk|run/i.test(clip.name));
      const visual = { object, mixer, idle: idle && mixer?.clipAction(idle), moving: moving && mixer?.clipAction(moving) };
      object.visible = false; actor.object.add(object); actor.levels.set(level, visual);
      if (level === actor.desired || actor.selected < 0) this.selectActorLevel(actor, level);
    } catch { actor.failed.add(level); if (object) releaseCampaignActor(object); }
    finally { actor.pending.delete(level); }
    if (actor.valid && actor.selected < 0 && stage === this.stage && !this.disposed) {
      const alternative = actor.models.findIndex((_, index) => !actor.failed.has(index) && !actor.pending.has(index));
      if (alternative >= 0) await this.loadActorLevel(stage, actor, alternative);
    }
  }
  private selectActorLevel(actor: Actor, level: number): void {
    actor.selected = level; actor.animationAccumulator = 0;
    for (const [index, visual] of actor.levels) {
      visual.object.visible = index === level;
      if (index !== level) continue;
      this.setActorMotion(visual, actor.moving);
      visual.mixer?.setTime(actor.animationTime);
    }
  }
  private setActorMotion(visual: Visual, moving: boolean): void {
    if (moving && visual.moving) { visual.idle?.stop(); visual.moving.play(); }
    else { visual.moving?.stop(); visual.idle?.play(); }
  }
  private releaseActor(actor: Actor): void {
    actor.valid = false;
    releaseCampaignActor(actor.object, [...actor.levels.values()].flatMap(visual => visual.mixer ? [visual.mixer] : []));
    actor.levels.clear();
  }
  private releaseStage(stage: Stage): void {
    stage.scene.environment = null; stage.environment.dispose();
    stage.queue.close(); stage.desiredActors.clear();
    for (const actor of stage.actors.values()) this.releaseActor(actor);
    stage.actors.clear();
    for (const chunk of stage.chunks) this.unloadChunk(chunk);
    stage.loader.dispose(stage.scene);
  }
  private frame = () => {
    const dt = Math.min(this.clock.getDelta(), .08), stage = this.stage, self = this.snapshot?.self;
    this.moveClock += dt; this.streamingClock += dt;
    if (this.moveClock >= .05) {
      this.moveClock = 0;
      const forward = Number(this.keys.has('KeyW')) - Number(this.keys.has('KeyS'));
      const right = Number(this.keys.has('KeyD')) - Number(this.keys.has('KeyA'));
      this.connection.send({ type: 'move', direction: { x: right * Math.cos(this.yaw) - forward * Math.sin(this.yaw), z: -forward * Math.cos(this.yaw) - right * Math.sin(this.yaw) } });
    }
    if (this.streamingClock >= .5) { this.streamingClock = 0; this.stream(); }
    if (!stage || !self || self.zoneId !== stage.id) return;
    for (const [id, actor] of stage.actors) {
      const previous = this.previousPosition.copy(actor.object.position);
      const distance = previous.distanceTo(actor.target);
      if (distance > 20) actor.object.position.copy(actor.target);
      else actor.object.position.lerp(actor.target, 1 - Math.exp(-dt * (id === self.id ? 20 : 12)));
      const moving = previous.distanceToSquared(actor.object.position) > dt * dt * .01;
      if (moving) actor.object.rotation.y = Math.atan2(actor.target.x - previous.x, actor.target.z - previous.z);
      const visual = actor.levels.get(actor.selected);
      if (moving !== actor.moving) { actor.moving = moving; if (visual) this.setActorMotion(visual, moving); }
      actor.animationTime += dt; actor.animationAccumulator += dt;
      const viewerDistance = Math.hypot(actor.target.x - self.position.x, actor.target.z - self.position.z);
      const interval = viewerDistance < 85 ? 0 : viewerDistance < 180 ? 1 / 15 : 1 / 8;
      if (actor.object.visible && actor.animationAccumulator >= interval) { visual?.mixer?.update(actor.animationAccumulator); actor.animationAccumulator = 0; }
    }
    const body = stage.actors.get(self.id)?.object.position ?? this.selfPosition.set(self.position.x, self.position.y, self.position.z);
    // Keep nearby architecture/characters grounded without allocating a zone-wide shadow map.
    const shadowStep = 140 / 2048;
    const shadowX = Math.round(body.x / shadowStep) * shadowStep;
    const shadowZ = Math.round(body.z / shadowStep) * shadowStep;
    stage.sun.target.position.set(shadowX, body.y, shadowZ);
    stage.sun.position.set(shadowX - 70, body.y + 110, shadowZ - 55);
    this.cameraTarget.lerp(body, 1 - Math.exp(-dt * 18));
    this.camera.position.set(this.cameraTarget.x + Math.sin(this.yaw) * this.zoom * Math.cos(this.pitch), this.cameraTarget.y + 2 + Math.sin(this.pitch) * this.zoom, this.cameraTarget.z + Math.cos(this.yaw) * this.zoom * Math.cos(this.pitch));
    this.camera.lookAt(this.cameraTarget.x, this.cameraTarget.y + 1.8, this.cameraTarget.z);
    this.renderer.render(stage.scene, this.camera);
  };
  private resize(): void { const w = Math.max(1, this.container.clientWidth), h = Math.max(1, this.container.clientHeight); this.renderer.setSize(w, h); this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); }
  private keyDown = (event: KeyboardEvent) => { if (!(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLSelectElement) && !(event.target instanceof HTMLTextAreaElement) && !(event.target as HTMLElement)?.isContentEditable && !event.ctrlKey && !event.metaKey) this.keys.add(event.code); };
  private keyUp = (event: KeyboardEvent) => { this.keys.delete(event.code); };
  private blur = () => { this.keys.clear(); this.orbiting = false; this.connection.send({ type: 'move', direction: { x: 0, z: 0 } }); };
  private pointerDown = (event: PointerEvent) => {
    if (event.button === 2) { this.orbiting = true; return; }
    if (event.button !== 0 || !this.stage) return;
    const rect = this.renderer.domElement.getBoundingClientRect();
    const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), this.camera);
    const hits = ray.intersectObjects([...this.stage.actors.values()].filter(actor => actor.object.visible).map(actor => actor.object), true);
    for (const hit of hits) for (let object: THREE.Object3D | null = hit.object; object; object = object.parent) if (object.userData.campaignEntityId) { this.onTarget(object.userData.campaignEntityId); return; }
    this.onTarget(null);
  };
  private pointerMove = (event: PointerEvent) => { if (this.orbiting) { this.yaw -= event.movementX * .006; this.pitch = THREE.MathUtils.clamp(this.pitch + event.movementY * .004, .1, 1.25); } };
  private pointerUp = () => { this.orbiting = false; };
  private wheel = (event: WheelEvent) => { event.preventDefault(); this.zoom = THREE.MathUtils.clamp(this.zoom + event.deltaY * .02, 4, 70); };
  private contextMenu = (event: Event) => event.preventDefault();
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true; this.generation++; this.renderer.setAnimationLoop(null); this.observer.disconnect();
    window.removeEventListener('keydown', this.keyDown); window.removeEventListener('keyup', this.keyUp); window.removeEventListener('blur', this.blur);
    window.removeEventListener('pointermove', this.pointerMove); window.removeEventListener('pointerup', this.pointerUp);
    this.renderer.domElement.removeEventListener('pointerdown', this.pointerDown); this.renderer.domElement.removeEventListener('wheel', this.wheel); this.renderer.domElement.removeEventListener('contextmenu', this.contextMenu);
    if (this.stage) this.releaseStage(this.stage);
    this.stage = null; this.renderer.dispose(); this.renderer.domElement.remove();
  }
}
