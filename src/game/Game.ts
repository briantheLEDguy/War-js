import * as THREE from 'three';
import { services } from '../services';
import type { CharacterState, WorldEditDocument, WorldPropObject } from '../services/types';
import { useGameStore, type EnemyState } from '../state/gameStore';
import { spawnNpcs } from '../world/NpcSpawner';
import { spawnProps, type InteractiveGate, type WorldCollider, type WorldWalkableSurface } from '../world/Props';
import { setupSky } from '../world/Skybox';
import { Terrain } from '../world/Terrain';
import { loadZone, type CraftingStationSpawn, type ZoneTrigger } from '../world/ZoneLoader';
import {
  WorldEditorRuntime,
  type WorldEditorSettings,
  type WorldEditorTool,
} from '../world/editor/WorldEditorRuntime';
import { buildModeToolLabel, cycleBuildModeTool } from '../world/editor/WorldEditorModes';
import {
  cloneWorldEditDocument,
  createEmptyWorldEditDocument,
  makeVersionId,
} from '../world/WorldEditValidation';
import { AssetLoader } from './AssetLoader';
import { FollowCamera } from './Camera';
import { Combat } from './Combat';
import { gatherEnemy, openCraftingStation } from './CraftingLogic';
import { Enemy } from './Enemy';
import { equipmentVisualSignature } from './Equipment';
import { Input } from './Input';
import { Player } from './Player';
import { VfxLayer } from './animation/VfxLayer';

const WALKABLE_SURFACE_STEP_UP = 0.85;

export class Game {
  private renderer!: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera!: FollowCamera;
  private input!: Input;
  private loader = new AssetLoader();
  private terrain = new Terrain({ size: 140, segments: 112 });
  private player!: Player;
  private enemies: Enemy[] = [];
  private npcMixers: THREE.AnimationMixer[] = [];
  private combat = new Combat();
  private vfx!: VfxLayer;

  private lastT = 0;
  private fpsT = 0;
  private fpsFrames = 0;
  private raf = 0;
  private disposed = false;
  private container: HTMLElement;
  private character: CharacterState;
  private saveTimer = 0;
  private equipmentSignature = '';
  private spawnPoint = { x: 0, y: 0, z: 0 };

  private currentZoneName = '';
  private zoneTriggers: ZoneTrigger[] = [];
  private craftingStations: CraftingStationSpawn[] = [];
  private propColliders: WorldCollider[] = [];
  private cameraColliders: WorldCollider[] = [];
  private walkableSurfaces: WorldWalkableSurface[] = [];
  private gates = new Map<string, InteractiveGate>();
  private interactRaycaster = new THREE.Raycaster();
  private worldEditor: WorldEditorRuntime | null = null;
  private publishedWorldEdit: WorldEditDocument | null = null;
  private currentEditorDraft: WorldEditDocument | null = null;
  private editorAutosaveTimer: number | null = null;
  private editorSaveInFlight: Promise<void> = Promise.resolve();

  /** World → screen projection used by HUD for nameplates + damage numbers. */
  worldToScreen(world: THREE.Vector3, out: THREE.Vector2): boolean {
    if (!this.player || !this.camera) return false;
    const v = world.clone().project(this.camera.camera);
    if (v.z < -1 || v.z > 1) return false;
    const rect = this.renderer.domElement.getBoundingClientRect();
    out.x = ((v.x + 1) / 2) * rect.width;
    out.y = ((-v.y + 1) / 2) * rect.height;
    return true;
  }

  get playerPos(): THREE.Vector3 { return this.player?.position ?? new THREE.Vector3(); }
  get zoneName(): string { return this.currentZoneName; }
  get craftingStationMarkers(): Array<{
    id: string;
    label: string;
    kind: CraftingStationSpawn['kind'];
    position: { x: number; y: number; z: number };
  }> {
    return this.craftingStations.map((station) => ({
      id: station.id,
      label: station.label,
      kind: station.kind,
      position: {
        x: station.x,
        y: this.groundHeightAt(station.x, station.z, station.y),
        z: station.z,
      },
    }));
  }

  /** Proxy for the touch joystick — called by TouchControls each pointer-move. */
  setTouchAxis(x: number, z: number) {
    this.input?.setTouchAxis(x, z);
  }

  /** Proxy for the touch jump button. */
  triggerTouchJump() {
    this.input?.triggerTouchJump();
  }

  constructor(container: HTMLElement, character: CharacterState) {
    this.container = container;
    this.character = character;
  }

  async start() {
    const container = this.container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    container.replaceChildren(this.renderer.domElement);

    const aspect = container.clientWidth / container.clientHeight;
    this.camera = new FollowCamera(this.renderer.domElement, aspect);
    this.input = new Input(this.renderer.domElement);
    this.vfx = new VfxLayer(this.scene);
    this.combat.setVfxLayer(this.vfx);

    // Zone
    const zone = await loadZone(this.character.zoneId ?? 'zone1');
    if (this.disposed) return; // guard: React Strict Mode may dispose before first await resolves
    this.currentZoneName = zone.name;
    this.publishedWorldEdit = await services.worldEdits
      .getPublished(zone.id)
      .catch((err) => {
        console.warn('[WorldEditor] failed to load published world edit:', err);
        return null;
      });

    // Sky + lights
    await setupSky(this.scene, this.loader, this.renderer, zone.skybox);
    if (this.disposed) return;

    // Terrain
    const terrainMesh = await this.terrain.build(this.loader, {
      size: zone.size,
      segments: zone.segments,
      model: zone.terrainModel,
      diffuseTexture: zone.terrainTexture,
      heightTexture: zone.heightmap,
      flatTerrain: zone.flatTerrain,
    });
    if (this.disposed) return;
    this.scene.add(terrainMesh);

    this.worldEditor = new WorldEditorRuntime({
      scene: this.scene,
      camera: this.camera.camera,
      domElement: this.renderer.domElement,
      loader: this.loader,
      terrain: this.terrain,
      groundHeightAt: this.groundHeightAt,
      onChange: (document) => this.queueWorldEditorAutosave(document),
      onSelectionChange: (object) => useGameStore.getState().setWorldEditorSelectedObjectId(object?.id ?? null),
    });
    this.worldEditor.registerStaticObject(buildStaticTerrainObject(zone.id, zone.terrainModel, terrainMesh), terrainMesh, {
      refresh: () => this.terrain.refreshModelTransform(),
      useAsPlacementSurface: true,
    });

    // Props
    const spawnedProps = await spawnProps(this.scene, this.loader, this.terrain, zone.props);
    if (this.disposed) return;
    this.propColliders = spawnedProps.colliders;
    this.cameraColliders = spawnedProps.cameraColliders;
    this.walkableSurfaces = spawnedProps.walkableSurfaces;
    this.gates = new Map(spawnedProps.gates.map((gate) => [gate.id, gate]));
    for (const object of spawnedProps.objects) {
      this.worldEditor.registerStaticObject(object.definition, object.object);
    }

    await this.worldEditor.loadDocument(this.publishedWorldEdit, false);
    if (this.disposed) return;

    // NPCs
    const spawnedNpcs = await spawnNpcs(
      this.scene,
      this.loader,
      this.terrain,
      zone.npcs ?? [],
      this.groundHeightAt,
    );
    if (this.disposed) return;
    this.npcMixers = spawnedNpcs.mixers;
    useGameStore.getState().setNpcs(spawnedNpcs.states);

    // Zone triggers
    this.zoneTriggers = zone.zoneTriggers ?? [];
    this.craftingStations = zone.craftingStations ?? [];

    // Player
    const sp = zone.spawnPoint ?? { x: 0, y: 0, z: 0 };
    const spawnY = this.groundHeightAt(sp.x, sp.z, sp.y);
    this.spawnPoint = { x: sp.x, y: spawnY, z: sp.z };
    this.character.position = { x: sp.x, y: spawnY, z: sp.z };
    this.player = new Player(this.character, this.terrain, this.groundHeightAt);
    await this.player.build(this.loader, this.scene);
    if (this.disposed) return;
    this.equipmentSignature = equipmentVisualSignature(this.character.equipment);
    await this.player.applyEquipmentVisuals(this.character.equipment, this.loader);
    if (this.disposed) return;

    // Store the respawn point so the HUD can use it
    useGameStore.getState().setRespawnPoint(this.spawnPoint);

    // Enemies
    const enemyState: EnemyState[] = [];
    for (const es of zone.enemies) {
      const e = new Enemy(es, this.terrain, this.groundHeightAt);
      await e.build(this.loader, this.scene);
      this.enemies.push(e);
      this.combat.registerEnemy(e);
      enemyState.push({
        id: es.id,
        name: es.name,
        level: es.level,
        health: es.maxHealth,
        maxHealth: es.maxHealth,
        position: { x: e.position.x, y: e.position.y, z: e.position.z },
        alive: true,
      });
    }
    useGameStore.getState().setEnemies(enemyState);

    // Services: join zone + chat history
    await services.world.joinZone(zone.id, {
      userId: useGameStore.getState().user?.id ?? 'unknown',
      characterId: this.character.id,
      name: this.character.name,
      position: this.spawnPoint,
      rotationY: 0,
    });
    const history = await services.chat.history('zone');
    useGameStore.getState().setChat(history);
    const unsub = services.chat.subscribe((m) => useGameStore.getState().appendChat(m));
    this.onDispose.push(unsub);

    // Resize
    window.addEventListener('resize', this.onResize);

    // Loop
    this.lastT = performance.now();
    this.raf = requestAnimationFrame(this.loop);

    if (useGameStore.getState().gmBuildMode) {
      void this.setWorldEditorActive(true);
    }
  }

  private onResize = () => {
    if (!this.container) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.renderer.setSize(w, h);
    this.camera.resize(w / h);
  };

  private loop = (tMs: number) => {
    if (this.disposed) return;
    const dt = Math.min(0.1, (tMs - this.lastT) / 1000);
    this.lastT = tMs;
    // Hard-guard every frame: if update() or render() throws, log it but
    // keep scheduling new frames. Otherwise a single bad frame kills rAF,
    // freezing input and leaving the minimap stuck at the last position.
    try {
      this.update(dt, tMs);
    } catch (err) {
      console.error('Game.update threw — recovering', err);
    }
    try {
      this.renderer.render(this.scene, this.camera.camera);
    } catch (err) {
      console.error('Renderer threw — recovering', err);
    }
    this.raf = requestAnimationFrame(this.loop);
  };

  private update(dt: number, tMs: number) {
    const store = useGameStore.getState();

    // Handle respawn requested from the death-overlay button
    if (store.pendingRespawn) {
      store.setPendingRespawn(false);
      store.setPlayerDead(false);
      const rp = store.respawnPoint;
      this.player.position.set(
        rp.x,
        this.groundHeightAt(rp.x, rp.z),
        rp.z,
      );
      this.player.object.position.copy(this.player.position);
      store.updateCharacter({
        health: store.character?.maxHealth ?? 100,
        mana: store.character?.maxMana ?? 100,
      });
      // Deaggro all enemies so they don't instantly kill the player again
      for (const enemy of this.enemies) {
        enemy.aggroed = false;
        enemy.attackCooldown = 0;
      }
    }

    // Debug / panels / settings toggles
    if (this.input.wasPressed('Escape') && !store.chatFocused) {
      if (store.wikiOpen) store.setWikiOpen(false);
      else store.toggleSettings();
    }
    if (!store.chatFocused && !useGameStore.getState().settingsOpen && this.input.wasPressed('KeyH')) {
      store.toggleWiki();
    }
    const uiState = useGameStore.getState();
    const settingsOpen = uiState.settingsOpen;
    const wikiOpen = uiState.wikiOpen;
    const uiBlockingOpen = settingsOpen || wikiOpen;
    if (store.gmBuildMode && !store.chatFocused && !uiBlockingOpen && this.input.wasPressed('Tab')) {
      const direction = this.input.isDown('ShiftLeft') || this.input.isDown('ShiftRight') ? -1 : 1;
      const nextTool = cycleBuildModeTool(store.worldEditorTool, direction);
      store.setWorldEditorTool(nextTool);
      this.worldEditor?.setTool(nextTool);
      store.setWorldEditorStatus(`${buildModeToolLabel(nextTool)} mode active.`);
    }
    if (
      store.gmBuildMode &&
      store.worldEditorTool === 'select' &&
      !store.chatFocused &&
      !uiBlockingOpen &&
      (this.input.wasPressed('Delete') || this.input.wasPressed('Backspace'))
    ) {
      this.deleteSelectedWorldEditorObject();
    }
    if (!uiBlockingOpen) {
      if (this.input.wasPressed('Backquote')) store.toggleDebug();
      if (this.input.wasPressed('KeyI')) store.toggleInventory();
      if (this.input.wasPressed('KeyC') && !store.chatFocused) store.toggleCharacterSheet();
      if (this.input.wasPressed('KeyL')) store.toggleQuestLog();
    }

    const currentEquipmentSignature = equipmentVisualSignature(store.character?.equipment);
    if (currentEquipmentSignature !== this.equipmentSignature) {
      this.equipmentSignature = currentEquipmentSignature;
      this.character.equipment = store.character?.equipment;
      void this.player.applyEquipmentVisuals(store.character?.equipment, this.loader);
    }

    // Interact with nearby corpses, crafting stations, or quest-givers.
    if (this.input.wasPressed('KeyE') && !store.chatFocused && !uiBlockingOpen) {
      this.tryGatherNearestCorpse() ||
        this.tryOpenNearestCraftingStation() ||
        this.tryOpenNearestQuestgiver();
    }

    // Chat focus
    if (this.input.wasPressed('Enter') && !store.chatFocused && !uiBlockingOpen) {
      store.setChatFocused(true);
    }

    // Combat inputs (blocked while dead or typing in chat)
    if (!store.chatFocused && !store.playerDead && !uiBlockingOpen && !store.gmBuildMode) {
      if (this.input.mouseLeftClickedThisFrame) {
        const id = this.combat.tryTargetAt(this.input.lastClickNDC, this.camera.camera);
        if (id) {
          store.setTarget(id);
        } else if (!this.tryInteractAt(this.input.lastClickNDC)) {
          store.setTarget(null);
        }
      }
      if (this.input.mouseRightClickedThisFrame) {
        this.tryInteractAt(this.input.lastRightClickNDC);
      }
      const abilityKeys: Array<[string, number]> = [
        ['Digit1', 0],
        ['Digit2', 1],
        ['Digit3', 2],
        ['Digit4', 3],
        ['Digit5', 4],
        ['Digit6', 5],
        ['Digit7', 6],
        ['Digit8', 7],
        ['Digit9', 8],
        ['Digit0', 9],
      ];
      for (const [code, slot] of abilityKeys) {
        if (this.input.wasPressed(code)) this.combat.tryAbility(slot, this.player, tMs);
      }

      // Touch hotbar taps (set by Hotbar component via the store)
      const touchSlot = store.pendingTouchAbility;
      if (touchSlot !== null) {
        store.setPendingTouchAbility(null);
        this.combat.tryAbility(touchSlot, this.player, tMs);
      }
    }

    // Tick
    store.tickCooldowns(dt);
    if (!store.playerDead && !uiBlockingOpen) {
      this.player.update(dt, this.input, this.camera, this.resolvePlayerCollisions);
    }
    if (store.gmBuildMode) {
      this.worldEditor?.setPlayerPose(
        {
          x: this.player.position.x,
          y: this.player.position.y,
          z: this.player.position.z,
        },
        this.player.rotationY,
      );
    }
    this.camera.update(this.player.position, this.input, this.getActiveCameraColliders());
    this.combat.tickAbilityImpacts(tMs);
    this.combat.tickStatusEffects(tMs);
    this.combat.tickEnemies(dt, tMs, this.player);
    this.combat.tickRespawns(tMs);
    this.combat.tickFloatingDamage(tMs);
    this.vfx.update(dt);
    for (const gate of this.gates.values()) gate.mixer?.update(dt);
    for (const mixer of this.npcMixers) mixer.update(dt);

    // Enemy visibility sync
    for (const e of this.enemies) {
      const es = store.enemies.find((x) => x.id === e.spawn.id);
      if (es) e.update(tMs, es.alive);
    }

    // Zone trigger detection
    if (!store.pendingZoneTransition && this.zoneTriggers.length > 0) {
      const px = this.player.position.x;
      const pz = this.player.position.z;
      for (const trigger of this.zoneTriggers) {
        const dx = px - trigger.x;
        const dz = pz - trigger.z;
        if (dx * dx + dz * dz < trigger.radius * trigger.radius) {
          store.setPendingZoneTransition({
            targetZoneId: trigger.targetZoneId,
            targetSpawn: trigger.targetSpawn,
          });
          break;
        }
      }
    }

    // Position sync to world service (every 0.2 s)
    this.saveTimer += dt;
    if (this.saveTimer > 0.2) {
      this.saveTimer = 0;
      void services.world.updatePosition(this.character.zoneId, {
        userId: store.user?.id ?? 'unknown',
        characterId: this.character.id,
        name: this.character.name,
        position: {
          x: this.player.position.x,
          y: this.player.position.y,
          z: this.player.position.z,
        },
        rotationY: this.player.rotationY,
      }).catch(() => {});
    }

    // FPS
    this.fpsFrames++;
    this.fpsT += dt;
    if (this.fpsT >= 0.5) {
      store.setFps(Math.round(this.fpsFrames / this.fpsT));
      this.fpsT = 0;
      this.fpsFrames = 0;
    }

    this.input.endFrame();
  }

  private tryGatherNearestCorpse(): boolean {
    const store = useGameStore.getState();
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { id: string; dist: number } | null = null;

    for (const enemy of store.enemies) {
      if (enemy.alive || !enemy.gathering || enemy.gathering.harvested) continue;
      const d = Math.hypot(px - enemy.position.x, pz - enemy.position.z);
      if (d <= 4 && (!best || d < best.dist)) best = { id: enemy.id, dist: d };
    }

    return best ? gatherEnemy(best.id) : false;
  }

  private tryOpenNearestCraftingStation(): boolean {
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { station: CraftingStationSpawn; dist: number } | null = null;

    for (const station of this.craftingStations) {
      const radius = station.radius ?? 5;
      const d = Math.hypot(px - station.x, pz - station.z);
      if (d <= radius && (!best || d < best.dist)) best = { station, dist: d };
    }

    if (!best) return false;
    openCraftingStation(best.station.kind, best.station.label);
    return true;
  }

  private tryOpenNearestQuestgiver(): boolean {
    const store = useGameStore.getState();
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { id: string; dist: number } | null = null;

    for (const npc of store.npcs) {
      if (npc.role !== 'questgiver') continue;
      const d = Math.hypot(px - npc.position.x, pz - npc.position.z);
      if (d < 4 && (!best || d < best.dist)) best = { id: npc.id, dist: d };
    }

    if (!best) return false;
    store.setActiveQuestDialogNpcId(best.id);
    return true;
  }

  private resolvePlayerCollisions = (position: THREE.Vector3, radius: number): void => {
    const activeColliders = [
      ...this.propColliders.filter((collider) => !this.isStaticSourceSuppressed(collider.sourceObjectId)),
      ...(this.worldEditor?.getColliders() ?? []),
    ];
    if (activeColliders.length === 0) return;
    for (let pass = 0; pass < 3; pass += 1) {
      let moved = false;
      for (const collider of activeColliders) {
        if (!this.isColliderActive(collider)) continue;
        moved = pushCircleOutOfCollider(position, radius, collider) || moved;
      }
      if (!moved) break;
    }
  };

  private getActiveCameraColliders(): WorldCollider[] {
    const colliders = [
      ...this.cameraColliders.filter((collider) => !this.isStaticSourceSuppressed(collider.sourceObjectId)),
      ...(this.worldEditor?.getCameraColliders() ?? []),
    ];
    if (colliders.length === 0) return colliders;
    return colliders.filter((collider) => this.isColliderActive(collider));
  }

  private groundHeightAt = (x: number, z: number, currentY?: number): number => {
    let height = this.terrain.heightAt(x, z);
    const reachableY = (currentY ?? height) + WALKABLE_SURFACE_STEP_UP;
    const walkables = [
      ...this.walkableSurfaces.filter((surface) => !this.isStaticSourceSuppressed(surface.sourceObjectId)),
      ...(this.worldEditor?.getWalkableSurfaces() ?? []),
    ];
    for (const surface of walkables) {
      const surfaceHeight = getWalkableSurfaceHeight(x, z, surface);
      if (surfaceHeight !== null && surfaceHeight <= reachableY) {
        height = Math.max(height, surfaceHeight);
      }
    }
    return height;
  };

  private isStaticSourceSuppressed(sourceObjectId?: string): boolean {
    return this.worldEditor?.isStaticObjectSuppressed(sourceObjectId) ?? false;
  }

  async setWorldEditorActive(active: boolean): Promise<void> {
    if (!this.worldEditor) return;
    const store = useGameStore.getState();
    store.setWorldEditorStatus(active ? 'Loading GM draft...' : 'Leaving GM build mode...');

    if (!active) {
      this.currentEditorDraft = null;
      await this.worldEditor.loadDocument(this.publishedWorldEdit, false);
      this.worldEditor.setActive(false);
      store.setWorldEditorStatus('GM build mode closed.');
      return;
    }

    const zoneId = this.character.zoneId;
    let draft = await services.worldEdits.getDraft(zoneId).catch((err) => {
      console.warn('[WorldEditor] failed to load GM draft:', err);
      return null;
    });
    if (!draft) {
      draft = this.publishedWorldEdit
        ? cloneWorldEditDocument(this.publishedWorldEdit, {
            versionId: makeVersionId('draft'),
            status: 'draft',
            parentVersionId: this.publishedWorldEdit.versionId,
            publishedAt: undefined,
            updatedAt: Date.now(),
          })
        : createEmptyWorldEditDocument(zoneId, 'draft');
      await services.worldEdits.saveDraft(zoneId, { replaceDocument: this.withAuthor(draft) });
    }

    this.currentEditorDraft = draft;
    await this.worldEditor.loadDocument(draft, true, {
      undoBaseline: this.createWorldEditorLiveBaseline(zoneId, draft),
    });
    this.worldEditor.setSettings(store.worldEditorSettings);
    this.worldEditor.setTool(store.worldEditorTool);
    store.setWorldEditorStatus('GM build mode active. Draft autosave is enabled.');
  }

  setWorldEditorTool(tool: WorldEditorTool): void {
    this.worldEditor?.setTool(tool);
  }

  setWorldEditorSettings(settings: Partial<WorldEditorSettings>): void {
    this.worldEditor?.setSettings(settings);
  }

  worldEditorUndo(): void {
    this.worldEditor?.undo();
  }

  worldEditorRedo(): void {
    this.worldEditor?.redo();
  }

  deleteSelectedWorldEditorObject(): boolean {
    const store = useGameStore.getState();
    if (store.worldEditorTool !== 'select') return false;
    const deleted = this.worldEditor?.deleteSelectedObject() ?? false;
    store.setWorldEditorStatus(deleted ? 'Deleted selected object.' : 'No selected object to delete.');
    return deleted;
  }

  async stampWorldEditorPrefabAtPlayer(): Promise<void> {
    if (!this.player || !this.worldEditor) return;
    await this.worldEditor.stampPrefabAtPlayer({
      x: this.player.position.x,
      y: this.player.position.y,
      z: this.player.position.z,
    });
  }

  async applyWorldEditorToolAtPlayer(): Promise<void> {
    if (!this.player || !this.worldEditor) return;
    await this.worldEditor.applyToolAtPlayer({
      x: this.player.position.x,
      y: this.player.position.y,
      z: this.player.position.z,
    });
  }

  async saveWorldEditorDraft(): Promise<void> {
    const save = this.saveWorldEditorDraftNow();
    this.editorSaveInFlight = save.catch(() => {});
    await save;
  }

  private async saveWorldEditorDraftNow(): Promise<void> {
    if (!this.worldEditor?.currentDocument) return;
    if (this.editorAutosaveTimer !== null) {
      window.clearTimeout(this.editorAutosaveTimer);
      this.editorAutosaveTimer = null;
    }
    const doc = this.withAuthor(this.worldEditor.currentDocument);
    this.currentEditorDraft = await services.worldEdits.saveDraft(this.character.zoneId, {
      replaceDocument: doc,
    });
    useGameStore.getState().setWorldEditorStatus('GM draft saved.');
  }

  async publishWorldEditorDraft(notes: string): Promise<void> {
    await this.saveWorldEditorDraft();
    const published = await services.worldEdits.publishDraft(this.character.zoneId, notes);
    this.publishedWorldEdit = published;
    const nextDraft = await services.worldEdits.getDraft(this.character.zoneId);
    const nextDocument = nextDraft ?? cloneWorldEditDocument(published, {
      versionId: makeVersionId('draft'),
      status: 'draft',
      parentVersionId: published.versionId,
      publishedAt: undefined,
      updatedAt: Date.now(),
    });
    this.currentEditorDraft = nextDocument;
    await this.worldEditor?.loadDocument(nextDocument, true, {
      undoBaseline: this.createWorldEditorLiveBaseline(this.character.zoneId, nextDocument),
    });
    useGameStore.getState().setWorldEditorStatus(`Published ${published.versionId}.`);
  }

  async resetWorldEditorDraftToLive(): Promise<void> {
    if (!this.worldEditor) return;
    if (this.editorAutosaveTimer !== null) {
      window.clearTimeout(this.editorAutosaveTimer);
      this.editorAutosaveTimer = null;
    }

    const store = useGameStore.getState();
    const zoneId = this.character.zoneId;
    store.setWorldEditorStatus('Resetting draft to live...');
    await this.editorSaveInFlight;

    const live = await services.worldEdits.getPublished(zoneId);
    this.publishedWorldEdit = live;
    const now = Date.now();
    const draft = live
      ? cloneWorldEditDocument(live, {
          versionId: makeVersionId('draft'),
          status: 'draft',
          parentVersionId: live.versionId,
          publishedAt: undefined,
          updatedAt: now,
        })
      : createEmptyWorldEditDocument(zoneId, 'draft', {
          notes: 'Reset to static live baseline',
          updatedAt: now,
        });

    this.currentEditorDraft = await services.worldEdits.saveDraft(zoneId, {
      replaceDocument: this.withAuthor(draft),
    });
    await this.worldEditor.loadDocument(this.currentEditorDraft, true, {
      undoBaseline: this.createWorldEditorLiveBaseline(zoneId, this.currentEditorDraft),
    });
    this.worldEditor.setSettings(store.worldEditorSettings);
    this.worldEditor.setTool(store.worldEditorTool);
    store.setWorldEditorStatus(
      live
        ? 'Draft reset to the live published world.'
        : 'Draft reset to static zone data.',
    );
  }

  private queueWorldEditorAutosave(document: WorldEditDocument): void {
    this.currentEditorDraft = this.withAuthor(document);
    const store = useGameStore.getState();
    store.setWorldEditorStatus('Draft changed. Autosaving...');
    if (this.editorAutosaveTimer !== null) window.clearTimeout(this.editorAutosaveTimer);
    this.editorAutosaveTimer = window.setTimeout(() => {
      this.editorAutosaveTimer = null;
      void this.saveWorldEditorDraft().catch((err) => {
        console.warn('[WorldEditor] autosave failed:', err);
        useGameStore.getState().setWorldEditorStatus(`Autosave failed: ${(err as Error).message}`);
      });
    }, 1200);
  }

  private createWorldEditorLiveBaseline(zoneId: string, draft: WorldEditDocument): WorldEditDocument {
    if (this.publishedWorldEdit) {
      return cloneWorldEditDocument(this.publishedWorldEdit, {
        versionId: draft.versionId,
        zoneId,
        status: 'draft',
        parentVersionId: this.publishedWorldEdit.versionId,
        authorUserId: draft.authorUserId,
        authorEmail: draft.authorEmail,
        notes: draft.notes,
        createdAt: draft.createdAt,
        updatedAt: draft.updatedAt,
        publishedAt: undefined,
      });
    }

    return createEmptyWorldEditDocument(zoneId, 'draft', {
      versionId: draft.versionId,
      parentVersionId: draft.parentVersionId,
      authorUserId: draft.authorUserId,
      authorEmail: draft.authorEmail,
      notes: draft.notes,
      createdAt: draft.createdAt,
      updatedAt: draft.updatedAt,
    });
  }

  private withAuthor(document: WorldEditDocument): WorldEditDocument {
    const user = useGameStore.getState().user;
    return {
      ...document,
      authorUserId: user?.id ?? document.authorUserId,
      authorEmail: user?.email ?? document.authorEmail,
    };
  }

  private isColliderActive(collider: WorldCollider): boolean {
    if (collider.blocksWhen === 'always') return true;
    if (!collider.interactionId) return true;
    return !this.gates.get(collider.interactionId)?.isOpen;
  }

  private tryInteractAt(ndc: Float32Array): boolean {
    if (!this.player || this.gates.size === 0) return false;
    this.interactRaycaster.setFromCamera(
      new THREE.Vector2(ndc[0], ndc[1]),
      this.camera.camera,
    );
    const gateObjects = Array.from(this.gates.values(), (gate) => gate.object);
    const hits = this.interactRaycaster.intersectObjects(gateObjects, true);
    for (const hit of hits) {
      const gate = this.findGateForObject(hit.object);
      if (!gate) continue;
      if (!this.isGateInRange(gate)) continue;
      this.toggleGate(gate);
      return true;
    }
    const fallbackGate = this.findGateNearRay();
    if (fallbackGate) {
      this.toggleGate(fallbackGate);
      return true;
    }
    return false;
  }

  private findGateNearRay(): InteractiveGate | null {
    let best: { gate: InteractiveGate; score: number } | null = null;
    for (const gate of this.gates.values()) {
      if (!this.isGateInRange(gate)) continue;
      const box = new THREE.Box3().setFromObject(gate.object);
      if (box.isEmpty()) continue;
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const rayDistance = this.interactRaycaster.ray.distanceSqToPoint(sphere.center);
      const radius = Math.max(2.5, sphere.radius * 1.2);
      if (rayDistance > radius * radius) continue;
      if (!best || rayDistance < best.score) best = { gate, score: rayDistance };
    }
    return best?.gate ?? null;
  }

  private isGateInRange(gate: InteractiveGate): boolean {
    const dx = gate.object.position.x - this.player.position.x;
    const dz = gate.object.position.z - this.player.position.z;
    return Math.hypot(dx, dz) <= gate.maxDistance;
  }

  private findGateForObject(object: THREE.Object3D): InteractiveGate | null {
    let node: THREE.Object3D | null = object;
    while (node) {
      const id = node.userData.interactionId as string | undefined;
      if (id && this.gates.has(id)) return this.gates.get(id)!;
      node = node.parent;
    }
    return null;
  }

  private toggleGate(gate: InteractiveGate): void {
    const opening = !gate.isOpen;
    gate.isOpen = opening;
    const clipName = opening ? gate.openClip : gate.closeClip;
    if (!gate.mixer) return;
    const actions = Array.from(gate.actions.entries())
      .filter(([name]) => name === clipName || name.startsWith(`${clipName}.`))
      .map(([, action]) => action);
    if (actions.length === 0) return;

    for (const existing of gate.actions.values()) existing.stop();
    for (const action of actions) {
      action.reset();
      action.enabled = true;
      action.clampWhenFinished = true;
      action.setLoop(THREE.LoopOnce, 1);
      action.play();
    }
  }

  private onDispose: Array<() => void> = [];

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    window.removeEventListener('resize', this.onResize);
    this.input?.dispose();
    this.camera?.dispose();
    for (const mixer of this.npcMixers) mixer.stopAllAction();
    for (const fn of this.onDispose) {
      try { fn(); } catch { /* ignore */ }
    }
    try { void services.world.leaveZone(this.character.zoneId); } catch { /* ignore */ }
    this.vfx?.dispose();
    this.worldEditor?.dispose();
    if (this.editorAutosaveTimer !== null) {
      window.clearTimeout(this.editorAutosaveTimer);
      this.editorAutosaveTimer = null;
    }
    this.renderer?.dispose();
    if (this.renderer?.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
    // Persist character snapshot
    void services.characters.save(this.character.id, {
      position: {
        x: this.player?.position.x ?? 0,
        y: this.player?.position.y ?? 0,
        z: this.player?.position.z ?? 0,
      },
      rotationY: this.player?.rotationY ?? 0,
    });
  }
}

function pushCircleOutOfCollider(
  position: THREE.Vector3,
  radius: number,
  collider: WorldCollider,
): boolean {
  const dx = position.x - collider.x;
  const dz = position.z - collider.z;
  const cos = Math.cos(collider.rotY);
  const sin = Math.sin(collider.rotY);
  const localX = dx * cos + dz * sin;
  const localZ = -dx * sin + dz * cos;
  const halfW = collider.width / 2;
  const halfD = collider.depth / 2;
  const clampedX = clamp(localX, -halfW, halfW);
  const clampedZ = clamp(localZ, -halfD, halfD);
  let pushX = localX - clampedX;
  let pushZ = localZ - clampedZ;
  const distSq = pushX * pushX + pushZ * pushZ;

  if (distSq > 0 && distSq < radius * radius) {
    const dist = Math.sqrt(distSq);
    const push = radius - dist;
    pushX = (pushX / dist) * push;
    pushZ = (pushZ / dist) * push;
  } else if (distSq === 0 && Math.abs(localX) <= halfW && Math.abs(localZ) <= halfD) {
    const penX = halfW + radius - Math.abs(localX);
    const penZ = halfD + radius - Math.abs(localZ);
    if (penX < penZ) {
      pushX = (localX >= 0 ? 1 : -1) * penX;
      pushZ = 0;
    } else {
      pushX = 0;
      pushZ = (localZ >= 0 ? 1 : -1) * penZ;
    }
  } else {
    return false;
  }

  position.x += pushX * cos - pushZ * sin;
  position.z += pushX * sin + pushZ * cos;
  return true;
}

function getWalkableSurfaceHeight(
  x: number,
  z: number,
  surface: WorldWalkableSurface,
): number | null {
  const dx = x - surface.x;
  const dz = z - surface.z;
  const cos = Math.cos(surface.rotY);
  const sin = Math.sin(surface.rotY);
  const localX = dx * cos + dz * sin;
  const localZ = -dx * sin + dz * cos;
  const halfW = surface.width / 2;
  const halfD = surface.depth / 2;
  if (localX < -halfW || localX > halfW || localZ < -halfD || localZ > halfD) return null;

  const t = surface.axis === 'x'
    ? (localX + halfW) / surface.width
    : (localZ + halfD) / surface.depth;
  return surface.fromY + (surface.toY - surface.fromY) * clamp(t, 0, 1);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function buildStaticTerrainObject(
  zoneId: string,
  model: string | undefined,
  object: THREE.Object3D,
): WorldPropObject {
  const now = 0;
  return {
    id: `static-terrain-${zoneId}`,
    type: 'prop',
    kind: 'terrain',
    label: 'terrain',
    model,
    transform: objectTransform(object),
    createdAt: now,
    updatedAt: now,
  };
}

function objectTransform(object: THREE.Object3D): WorldPropObject['transform'] {
  return {
    position: {
      x: round(object.position.x),
      y: round(object.position.y),
      z: round(object.position.z),
    },
    rotation: {
      x: round(object.rotation.x),
      y: round(object.rotation.y),
      z: round(object.rotation.z),
    },
    scale: {
      x: round(object.scale.x),
      y: round(object.scale.y),
      z: round(object.scale.z),
    },
  };
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
