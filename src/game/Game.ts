import * as THREE from 'three';
import { isResourceNodeAvailable } from '../data/crafting';
import type { CampaignControl, CampaignObjectiveStatus, CampaignRealm } from '../data/campaign';
import {
  defaultZoneSpawnPoint,
  normalizePlayableZoneId,
  zoneWasNormalized,
} from '../data/zoneRouting';
import { services } from '../services';
import type { CharacterState, WorldEditDocument, WorldPropObject } from '../services/types';
import { contextPromptKey, useGameStore, type AbilityFeedbackKind, type ContextPromptState, type EnemyState, type PlayerStatusEffect } from '../state/gameStore';
import { spawnNpcs, type NpcState } from '../world/NpcSpawner';
import { spawnProps, type InteractiveGate, type InteractiveHousePortal, type WorldCollider, type WorldWalkableSurface } from '../world/Props';
import { applySceneViewDistance, setupSky } from '../world/Skybox';
import { Terrain } from '../world/Terrain';
import {
  loadZone,
  type CraftingStationSpawn,
  type ResourceNodeSpawn,
  type RvrObjectiveDefinition,
  type ZoneDefinition,
  type ZoneTrigger,
} from '../world/ZoneLoader';
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
import {
  canCaptureCampaignObjective,
  captureProgressPct,
  campaignRealmForCharacter,
  claimObjectiveForCharacter,
} from './CampaignObjectiveLogic';
import { FollowCamera } from './Camera';
import { Combat } from './Combat';
import { gatherEnemy, gatherResourceNode, openCraftingStation } from './CraftingLogic';
import { Enemy } from './Enemy';
import { equipmentVisualSignature } from './Equipment';
import { Input } from './Input';
import { HouseInteriorRuntime } from './HouseInteriorRuntime';
import { Player } from './Player';
import { checkLevelUp } from './QuestLogic';
import { ResourceRegeneration } from './ResourceRegeneration';
import {
  resolveZoneEntryPoint,
  ZONE_TRANSITION_GRACE_MS,
  zoneTransitionCanArm,
} from './ZoneTransition';
import { VfxLayer } from './animation/VfxLayer';

const WALKABLE_SURFACE_STEP_UP = 0.85;
const CORPSE_INTERACT_RADIUS = 4;
const RESOURCE_NODE_INTERACT_RADIUS = 4.5;
const QUEST_INTERACT_RADIUS = 4;
const TARGETABLE_ENEMY_PROMPT_RADIUS = 12;
const HUD_FEEDBACK_DURATION_MS = 1800;
const ABILITY_KEYS: Array<[string, number]> = [
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
  private resourceRegeneration = new ResourceRegeneration();
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
  private appliedViewDistance = 0;

  private currentZoneName = '';
  private currentZone: ZoneDefinition | null = null;
  private zoneTriggers: ZoneTrigger[] = [];
  private zoneTransitionArmed = false;
  private zoneTransitionGraceUntilMs = 0;
  private craftingStations: CraftingStationSpawn[] = [];
  private resourceNodes: ResourceNodeSpawn[] = [];
  private objectiveControl = new Map<string, CampaignControl>();
  private objectiveStatus = new Map<string, CampaignObjectiveStatus>();
  private objectiveCapture: { objectiveId: string; startedAtMs: number; realm: CampaignRealm } | null = null;
  private objectiveClaimsInFlight = new Set<string>();
  private propColliders: WorldCollider[] = [];
  private cameraColliders: WorldCollider[] = [];
  private walkableSurfaces: WorldWalkableSurface[] = [];
  private gates = new Map<string, InteractiveGate>();
  private housePortals = new Map<string, InteractiveHousePortal>();
  private houseInteriors: HouseInteriorRuntime | null = null;
  private houseReturn: { position: THREE.Vector3; rotationY: number } | null = null;
  private zoneNpcStates: NpcState[] = [];
  private interactRaycaster = new THREE.Raycaster();
  private worldEditor: WorldEditorRuntime | null = null;
  private publishedWorldEdit: WorldEditDocument | null = null;
  private currentEditorDraft: WorldEditDocument | null = null;
  private editorAutosaveTimer: number | null = null;
  private editorSaveInFlight: Promise<void> = Promise.resolve();
  private lastContextualPromptKey = '';

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
  get zoneDefinition(): ZoneDefinition | null { return this.currentZone; }
  teleportPlayerTo(
    point: { x: number; y?: number; z: number },
    rotationY = this.player?.rotationY ?? this.character.rotationY,
  ): { x: number; y: number; z: number } {
    if (!this.player) throw new Error('Player is not ready.');
    if (!Number.isFinite(point.x) || !Number.isFinite(point.z)) {
      throw new Error('Teleport target must include finite x and z coordinates.');
    }

    const yHint = Number.isFinite(point.y) ? point.y : undefined;
    const nextPosition = {
      x: point.x,
      y: this.groundHeightAt(point.x, point.z, yHint),
      z: point.z,
    };
    this.player.teleportTo(nextPosition, rotationY);
    this.character.position = nextPosition;
    this.character.rotationY = rotationY;
    this.zoneTransitionArmed = false;
    this.zoneTransitionGraceUntilMs = performance.now() + ZONE_TRANSITION_GRACE_MS;

    const store = useGameStore.getState();
    store.updateCharacter({ position: nextPosition, rotationY });
    store.setPlayerDead(false);
    for (const enemy of this.enemies) {
      enemy.aggroed = false;
      enemy.attackCooldown = 0;
    }
    void services.characters.save(this.character.id, { position: nextPosition, rotationY });
    void services.world.updatePosition(this.character.zoneId, {
      userId: store.user?.id ?? 'unknown',
      characterId: this.character.id,
      name: this.character.name,
      position: nextPosition,
      rotationY,
    }).catch(() => {});
    return nextPosition;
  }

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
  get resourceNodeMarkers(): Array<{
    id: string;
    label: string;
    kind: ResourceNodeSpawn['kind'];
    available: boolean;
    position: { x: number; y: number; z: number };
  }> {
    const zoneId = this.currentZone?.id;
    const craftingState = useGameStore.getState().craftingState;
    return this.resourceNodes.map((node) => ({
      id: node.id,
      label: node.label,
      kind: node.kind,
      available: Boolean(zoneId && isResourceNodeAvailable(craftingState, zoneId, node.id)),
      position: {
        x: node.x,
        y: this.groundHeightAt(node.x, node.z, node.y),
        z: node.z,
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
    const normalizedZoneId = normalizePlayableZoneId(this.character.zoneId, this.character.race);
    if (zoneWasNormalized(this.character.zoneId, normalizedZoneId)) {
      this.character.zoneId = normalizedZoneId;
      this.character.position = defaultZoneSpawnPoint(normalizedZoneId);
      void services.characters.save(this.character.id, {
        zoneId: normalizedZoneId,
        position: this.character.position,
      });
    }
    const zone = await loadZone(normalizedZoneId);
    if (this.disposed) return; // guard: React Strict Mode may dispose before first await resolves
    this.currentZoneName = zone.name;
    this.currentZone = zone;
    void this.warnIfCampaignMapOutOfDate(zone);
    this.publishedWorldEdit = await services.worldEdits
      .getPublished(zone.id)
      .catch((err) => {
        console.warn('[WorldEditor] failed to load published world edit:', err);
        return null;
      });

    // Sky + lights
    await setupSky(this.scene, this.loader, this.renderer, zone.skybox, useGameStore.getState().settings.viewDistance);
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
    this.housePortals = new Map(spawnedProps.housePortals.map((portal) => [portal.id, portal]));
    this.houseInteriors = new HouseInteriorRuntime(this.scene);
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
    this.zoneNpcStates = spawnedNpcs.states;
    useGameStore.getState().setNpcs(this.zoneNpcStates);

    // Zone triggers
    this.zoneTriggers = zone.zoneTriggers ?? [];
    this.craftingStations = zone.craftingStations ?? [];
    this.resourceNodes = zone.resourceNodes ?? [];
    try {
      const campaignUnsubscribe = services.campaign.subscribeSnapshot((snapshot) => {
        const active = snapshot.zones.find((entry) => entry.id === zone.id);
        this.objectiveStatus = new Map(
          (active?.objectives ?? []).map((objective) => [objective.id, objective]),
        );
        this.objectiveControl = new Map(
          (active?.objectives ?? []).map((objective) => [objective.id, objective.control]),
        );
      }, zone.id);
      this.onDispose.push(campaignUnsubscribe);
    } catch (err) {
      console.warn('[Campaign] objective capture subscription unavailable:', err);
    }

    // Player
    const entryPoint = resolveZoneEntryPoint(this.character.position, zone.spawnPoint);
    const entryY = this.groundHeightAt(entryPoint.x, entryPoint.z, entryPoint.y);
    const safeRespawnPoint = resolveZoneEntryPoint(zone.spawnPoint, defaultZoneSpawnPoint(zone.id));
    const respawnY = this.groundHeightAt(safeRespawnPoint.x, safeRespawnPoint.z, safeRespawnPoint.y);
    this.spawnPoint = { x: safeRespawnPoint.x, y: respawnY, z: safeRespawnPoint.z };
    this.character.position = { x: entryPoint.x, y: entryY, z: entryPoint.z };
    this.zoneTransitionArmed = false;
    this.zoneTransitionGraceUntilMs = performance.now() + ZONE_TRANSITION_GRACE_MS;
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
      position: this.character.position,
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

  private async warnIfCampaignMapOutOfDate(zone: ZoneDefinition): Promise<void> {
    if (!zone.staticMapVersion || !zone.staticMapHash) return;
    const snapshot = await services.campaign.getSnapshot(zone.id).catch((err) => {
      console.warn('[Campaign] failed to load campaign metadata:', err);
      return null;
    });
    if (!snapshot) return;
    const expectedHash = snapshot.mapHashes[zone.id];
    if (snapshot.staticVersion !== zone.staticMapVersion || expectedHash !== zone.staticMapHash) {
      console.warn(
        `[Campaign] static map mismatch for ${zone.id}: asset ${zone.staticMapVersion}/${zone.staticMapHash}, ` +
        `campaign ${snapshot.staticVersion}/${expectedHash ?? 'missing'}`,
      );
    }
  }

  private onResize = () => {
    if (!this.container) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.renderer.setSize(w, h);
    this.camera.resize(w / h);
  };

  private applyViewDistanceSetting(viewDistance: number): void {
    if (viewDistance === this.appliedViewDistance) return;
    const applied = applySceneViewDistance(this.scene, viewDistance);
    this.appliedViewDistance = applied;
    if (this.camera) {
      this.camera.camera.far = Math.max(1200, applied + 200);
      this.camera.camera.updateProjectionMatrix();
    }
  }

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
    this.applyViewDistanceSetting(store.settings.viewDistance);

    // Handle respawn requested from the death-overlay button
    if (store.pendingRespawn) {
      store.setPendingRespawn(false);
      store.setPlayerDead(false);
      const rp = store.respawnPoint;
      const nextPosition = {
        x: rp.x,
        y: this.groundHeightAt(rp.x, rp.z, rp.y),
        z: rp.z,
      };
      const maxHealth = store.character?.maxHealth ?? 100;
      const maxMana = store.character?.maxMana ?? 100;
      this.player.teleportTo(nextPosition);
      this.character.position = nextPosition;
      this.character.health = maxHealth;
      this.character.mana = maxMana;
      store.updateCharacter({
        health: maxHealth,
        mana: maxMana,
        position: nextPosition,
      });
      // Deaggro all enemies so they don't instantly kill the player again
      for (const enemy of this.enemies) {
        enemy.aggroed = false;
        enemy.attackCooldown = 0;
      }
      void services.characters.save(this.character.id, {
        health: maxHealth,
        mana: maxMana,
        position: nextPosition,
        rotationY: this.player.rotationY,
      });
      void services.world.updatePosition(this.character.zoneId, {
        userId: store.user?.id ?? 'unknown',
        characterId: this.character.id,
        name: this.character.name,
        position: nextPosition,
        rotationY: this.player.rotationY,
      }).catch(() => {});
    }

    // Debug / panels / settings toggles
    if (
      !store.chatFocused &&
      !useGameStore.getState().settingsOpen &&
      !useGameStore.getState().worldMapOpen &&
      !useGameStore.getState().gmMenuOpen &&
      this.input.wasPressed('KeyH')
    ) {
      store.toggleWiki();
    }
    if (
      !store.chatFocused &&
      !useGameStore.getState().settingsOpen &&
      !useGameStore.getState().wikiOpen &&
      !useGameStore.getState().gmMenuOpen &&
      this.input.wasPressed('KeyM')
    ) {
      store.toggleWorldMap();
    }
    const uiState = useGameStore.getState();
    const settingsOpen = uiState.settingsOpen;
    const wikiOpen = uiState.wikiOpen;
    const worldMapOpen = uiState.worldMapOpen;
    const gmMenuOpen = uiState.gmMenuOpen;
    const uiBlockingOpen = settingsOpen || wikiOpen || worldMapOpen || gmMenuOpen;
    this.updateGuidedTaskProgress(store);
    this.updateObjectiveCapture(tMs, uiBlockingOpen);
    this.updateContextualPrompt(uiState, uiBlockingOpen);
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
    if (this.input.wasPressed('KeyE') && !store.chatFocused && !uiBlockingOpen && !store.gmFlyingMode) {
      const interacted = this.tryGatherNearestCorpse() ||
        this.tryGatherNearestResourceNode() ||
        this.tryOpenNearestCraftingStation() ||
        this.tryOpenNearestQuestgiver() ||
        this.tryUseNearestHousePortal() ||
        this.tryToggleNearestGate();
      if (interacted) store.completeGuidedTask('interact');
    }

    // Chat focus
    if (this.input.wasPressed('Enter') && !store.chatFocused && !uiBlockingOpen) {
      store.setChatFocused(true);
    }

    const attemptedAbilitySlot = this.consumeAbilityAttempt(store);
    if (attemptedAbilitySlot !== null) {
      this.handleAbilityAttempt(attemptedAbilitySlot, tMs, {
        chatFocused: store.chatFocused,
        playerDead: store.playerDead,
        uiBlockingOpen,
        gmBuildMode: store.gmBuildMode,
      });
    }

    // Combat targeting inputs (blocked while dead or typing in chat)
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
    }

    // Tick
    store.tickCooldowns(dt);
    if (!store.playerDead && !uiBlockingOpen) {
      this.player.update(
        dt,
        this.input,
        this.camera,
        this.resolvePlayerCollisions,
        store.gmFlyingMode
          ? store.gmMoveSpeedMultiplier
          : playerMoveMultiplier(store.playerStatusEffects, tMs) * store.gmMoveSpeedMultiplier,
        { flying: store.gmFlyingMode },
      );
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
    this.camera.update(
      this.player.position,
      this.input,
      this.getActiveCameraColliders(),
      this.terrain.heightAt.bind(this.terrain),
    );
    this.combat.tickAbilityImpacts(tMs);
    this.combat.tickStatusEffects(tMs);
    this.combat.tickEnemies(dt, tMs, this.player);
    this.tickResourceRegeneration(dt);
    this.combat.tickRespawns(tMs);
    this.combat.tickFloatingDamage(tMs);
    this.vfx.update(dt);
    for (const gate of this.getAllGates()) {
      gate.mixer?.update(dt);
      updateGateFallbackVisual(gate, dt);
    }
    for (const mixer of this.npcMixers) mixer.update(dt);

    // Enemy visibility sync
    for (const e of this.enemies) {
      const es = store.enemies.find((x) => x.id === e.spawn.id);
      if (es) e.update(tMs, es.alive);
    }

    // Zone trigger detection
    const zoneTrigger = this.findContainingZoneTrigger();
    if (!this.zoneTransitionArmed) {
      this.zoneTransitionArmed = zoneTransitionCanArm(tMs, this.zoneTransitionGraceUntilMs, Boolean(zoneTrigger));
    } else if (!store.pendingZoneTransition && zoneTrigger) {
      const targetZoneId = normalizePlayableZoneId(zoneTrigger.targetZoneId, this.character.race);
      store.setPendingZoneTransition({
        targetZoneId,
        targetSpawn: zoneWasNormalized(zoneTrigger.targetZoneId, targetZoneId)
          ? defaultZoneSpawnPoint(targetZoneId)
          : zoneTrigger.targetSpawn,
      });
    }

    // Position sync to world service (every 0.2 s)
    this.saveTimer += dt;
    if (this.saveTimer > 0.2 && !this.houseInteriors?.isActive) {
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

  private findContainingZoneTrigger(): ZoneTrigger | null {
    if (!this.player || this.zoneTriggers.length === 0) return null;
    const px = this.player.position.x;
    const pz = this.player.position.z;
    for (const trigger of this.zoneTriggers) {
      const dx = px - trigger.x;
      const dz = pz - trigger.z;
      if (dx * dx + dz * dz < trigger.radius * trigger.radius) return trigger;
    }
    return null;
  }

  private consumeAbilityAttempt(store: ReturnType<typeof useGameStore.getState>): number | null {
    const touchSlot = store.pendingTouchAbility;
    if (touchSlot !== null) store.setPendingTouchAbility(null);

    for (const [code, slot] of ABILITY_KEYS) {
      if (this.input.wasPressed(code)) return slot;
    }

    return touchSlot !== null && touchSlot >= 0 && touchSlot < ABILITY_KEYS.length
      ? touchSlot
      : null;
  }

  private tickResourceRegeneration(dt: number): void {
    const store = useGameStore.getState();
    if (store.playerDead || !store.character) {
      this.resourceRegeneration.reset();
      return;
    }

    const patch = this.resourceRegeneration.tick(store.character, dt);
    if (!patch) return;

    store.updateCharacter(patch);
    Object.assign(this.character, patch);
  }

  private updateGuidedTaskProgress(store: ReturnType<typeof useGameStore.getState>): void {
    store.clearExpiredAbilityFeedback(Date.now());
    if (!this.player) return;

    if (!store.guidedTasks.move) {
      const distanceFromSpawn = Math.hypot(
        this.player.position.x - this.spawnPoint.x,
        this.player.position.z - this.spawnPoint.z,
      );
      const keyboardMove =
        this.input.isDown('KeyW') ||
        this.input.isDown('KeyA') ||
        this.input.isDown('KeyS') ||
        this.input.isDown('KeyD') ||
        this.input.isDown('Space');
      const touchMove = Math.hypot(this.input.touchMoveX, this.input.touchMoveZ) > 0.1;
      if (distanceFromSpawn > 1.5 || keyboardMove || touchMove) {
        store.completeGuidedTask('move');
      }
    }

    if (!store.guidedTasks.camera && (this.input.mouseLeftDown || this.input.mouseRightDown)) {
      store.completeGuidedTask('camera');
    }
  }

  private handleAbilityAttempt(
    slot: number,
    tMs: number,
    state: {
      chatFocused: boolean;
      playerDead: boolean;
      uiBlockingOpen: boolean;
      gmBuildMode: boolean;
    },
  ): void {
    if (!this.player) return;

    if (state.playerDead) {
      this.showAbilityFeedback(
        this.combat.getAbilityFailure(slot, this.player, tMs, { playerDead: true }) ?? {
          code: 'dead_player',
          message: 'You are dead.',
        },
      );
      return;
    }

    const blockedMessage = state.chatFocused
      ? 'Close chat to use abilities.'
      : state.uiBlockingOpen
        ? 'Close the guide or settings to use abilities.'
        : state.gmBuildMode
          ? 'Leave GM build mode to use abilities.'
          : '';
    if (blockedMessage) {
      this.showAbilityFeedback(
        this.combat.getAbilityFailure(slot, this.player, tMs, {
          uiBlocked: true,
          uiBlockedMessage: blockedMessage,
        }) ?? { code: 'blocked_ui', message: blockedMessage },
      );
      return;
    }

    if (this.combat.tryAbility(slot, this.player, tMs)) return;

    const failure = this.combat.getAbilityFailure(slot, this.player, tMs);
    if (failure) this.showAbilityFeedback(failure);
  }

  private showAbilityFeedback(failure: { code: string; message: string; ability?: { name: string } }): void {
    useGameStore.getState().showAbilityFeedback({
      message: failure.message,
      abilityName: failure.ability?.name,
      kind: abilityFeedbackKind(failure.code),
      durationMs: HUD_FEEDBACK_DURATION_MS,
    });
  }

  private updateContextualPrompt(
    store: ReturnType<typeof useGameStore.getState>,
    uiBlockingOpen: boolean,
  ): void {
    if (!this.player || store.chatFocused || store.playerDead || uiBlockingOpen || store.gmBuildMode) {
      this.publishContextualPrompt(null);
      return;
    }

    this.publishContextualPrompt(
      this.findHarvestPrompt(store) ??
        this.findResourceNodePrompt(store) ??
      this.findCraftingPrompt() ??
      this.findQuestgiverPrompt(store) ??
        this.findHousePortalPrompt() ??
        this.findGatePrompt() ??
        this.findObjectivePrompt(store) ??
        this.findEnemyPrompt(store),
    );
  }

  private publishContextualPrompt(prompt: ContextPromptState | null): void {
    const key = contextPromptKey(prompt);
    if (key === this.lastContextualPromptKey) return;
    this.lastContextualPromptKey = key;
    useGameStore.getState().setContextPrompt(prompt);
  }

  private findHarvestPrompt(store: ReturnType<typeof useGameStore.getState>): ContextPromptState | null {
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { enemy: EnemyState; dist: number } | null = null;

    for (const enemy of store.enemies) {
      if (enemy.alive || !enemy.gathering || enemy.gathering.harvested) continue;
      const dist = Math.hypot(px - enemy.position.x, pz - enemy.position.z);
      if (dist <= CORPSE_INTERACT_RADIUS && (!best || dist < best.dist)) best = { enemy, dist };
    }

    if (!best) return null;
    const { enemy } = best;
    return {
      kind: 'gathering',
      action: 'E',
      label: `${enemy.gathering?.actionLabel ?? 'Harvest'} ${enemy.gathering?.corpseLabel ?? enemy.name}`,
      detail: enemy.name,
      distance: best.dist,
    };
  }

  private findResourceNodePrompt(store: ReturnType<typeof useGameStore.getState>): ContextPromptState | null {
    const best = this.findNearestResourceNode(store);
    if (!best) return null;
    return {
      kind: 'gathering',
      action: 'E',
      label: `Gather ${best.node.label}`,
      detail: resourceNodeKindLabel(best.node.kind),
      distance: best.dist,
    };
  }

  private findCraftingPrompt(): ContextPromptState | null {
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { station: CraftingStationSpawn; dist: number } | null = null;

    for (const station of this.craftingStations) {
      const radius = station.radius ?? 5;
      const dist = Math.hypot(px - station.x, pz - station.z);
      if (dist <= radius && (!best || dist < best.dist)) best = { station, dist };
    }

    if (!best) return null;
    return {
      kind: 'crafting',
      action: 'E',
      label: `Use ${best.station.label}`,
      detail: 'Crafting station',
      distance: best.dist,
    };
  }

  private findQuestgiverPrompt(store: ReturnType<typeof useGameStore.getState>): ContextPromptState | null {
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { npc: (typeof store.npcs)[number]; dist: number } | null = null;

    for (const npc of store.npcs) {
      if (npc.role !== 'questgiver') continue;
      const dist = Math.hypot(px - npc.position.x, pz - npc.position.z);
      if (dist < QUEST_INTERACT_RADIUS && (!best || dist < best.dist)) best = { npc, dist };
    }

    if (!best) return null;
    return {
      kind: 'quest',
      action: 'E',
      label: `Talk to ${best.npc.name}`,
      detail: best.npc.title,
      distance: best.dist,
    };
  }

  private findGatePrompt(): ContextPromptState | null {
    const best = this.findNearestGate();
    if (!best) return null;
    return {
      kind: 'gate',
      action: 'E',
      label: `${best.gate.isOpen ? 'Close' : 'Open'} ${best.gate.label}`,
      distance: best.dist,
    };
  }

  private findHousePortalPrompt(): ContextPromptState | null {
    const best = this.findNearestHousePortal();
    if (!best) return null;
    return {
      kind: 'house',
      action: 'E',
      label: best.portal.direction === 'exit' ? 'Leave House' : best.portal.label,
      detail: best.portal.direction === 'exit' ? 'Return to the street' : 'Enter furnished interior',
      distance: best.dist,
    };
  }

  private findObjectivePrompt(store: ReturnType<typeof useGameStore.getState>): ContextPromptState | null {
    const best = this.findCapturableObjective(store);
    if (!best) return null;
    const capture = this.objectiveCapture?.objectiveId === best.objective.id
      ? Math.round(captureProgressPct(this.objectiveCapture.startedAtMs, performance.now()) * 100)
      : 0;
    return {
      kind: 'objective',
      action: 'Hold',
      label: `Capture ${best.objective.label}`,
      detail: capture > 0 ? `${capture}%` : 'Stand in the objective area',
      distance: best.dist,
    };
  }

  private findEnemyPrompt(store: ReturnType<typeof useGameStore.getState>): ContextPromptState | null {
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { enemy: EnemyState; dist: number } | null = null;

    for (const enemy of store.enemies) {
      if (!enemy.alive) continue;
      const dist = Math.hypot(px - enemy.position.x, pz - enemy.position.z);
      if (dist <= TARGETABLE_ENEMY_PROMPT_RADIUS && (!best || dist < best.dist)) {
        best = { enemy, dist };
      }
    }

    if (!best) return null;
    const selected = store.targetId === best.enemy.id;
    return {
      kind: 'target',
      action: selected ? '1-0' : 'LMB',
      label: selected ? `Use abilities on ${best.enemy.name}` : `Target ${best.enemy.name}`,
      detail: `Lv ${best.enemy.level}`,
      distance: best.dist,
    };
  }

  private updateObjectiveCapture(tMs: number, uiBlockingOpen: boolean): void {
    const store = useGameStore.getState();
    if (
      !this.player ||
      !this.currentZone ||
      store.chatFocused ||
      store.playerDead ||
      uiBlockingOpen ||
      store.gmBuildMode
    ) {
      this.objectiveCapture = null;
      return;
    }

    const best = this.findCapturableObjective(store);
    if (!best) {
      this.objectiveCapture = null;
      return;
    }

    const realm = campaignRealmForCharacter(store.character!);
    if (
      !this.objectiveCapture ||
      this.objectiveCapture.objectiveId !== best.objective.id ||
      this.objectiveCapture.realm !== realm
    ) {
      this.objectiveCapture = { objectiveId: best.objective.id, startedAtMs: tMs, realm };
      return;
    }

    if (captureProgressPct(this.objectiveCapture.startedAtMs, tMs) < 1) return;
    if (this.objectiveClaimsInFlight.has(best.objective.id)) return;

    this.objectiveClaimsInFlight.add(best.objective.id);
    this.objectiveCapture = null;
    void claimObjectiveForCharacter(this.currentZone.id, best.objective.id, store.character!)
      .then((result) => {
        const snapshot = result.snapshot;
        const active = snapshot.zones.find((entry) => entry.id === this.currentZone?.id);
        this.objectiveStatus = new Map(
          (active?.objectives ?? []).map((objective) => [objective.id, objective]),
        );
        this.objectiveControl = new Map(
          (active?.objectives ?? []).map((objective) => [objective.id, objective.control]),
        );
        const updated = active?.objectives.find((objective) => objective.id === best.objective.id);
        const currentStore = useGameStore.getState();
        if (result.reward.xp > 0 && currentStore.character) {
          currentStore.updateCharacter({ xp: currentStore.character.xp + result.reward.xp });
          checkLevelUp();
        }
        useGameStore.getState().completeGuidedTask('interact');
        const rewardCopy = result.reward.xp > 0
          ? ` +${result.reward.xp} XP, +${result.reward.influence} influence.`
          : '';
        const controlCopy = result.zoneControlChanged && active
          ? ` ${active.name} is now controlled by ${campaignControlLabel(active.control)}.`
          : '';
        useGameStore.getState().appendChat({
          id: `objective-capture-${Date.now()}-${best.objective.id}`,
          channel: 'system',
          from: 'System',
          body: `Captured ${best.objective.label} for ${campaignControlLabel(updated?.control ?? realm)}.${rewardCopy}${controlCopy}`,
          timestamp: Date.now(),
        });
      })
      .catch((err) => {
        console.warn('[Campaign] objective capture failed:', err);
      })
      .finally(() => {
        this.objectiveClaimsInFlight.delete(best.objective.id);
      });
  }

  private findNearestResourceNode(
    store: ReturnType<typeof useGameStore.getState>,
  ): { node: ResourceNodeSpawn; dist: number } | null {
    const zoneId = this.currentZone?.id;
    if (!zoneId || !this.player) return null;
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { node: ResourceNodeSpawn; dist: number } | null = null;

    for (const node of this.resourceNodes) {
      if (!isResourceNodeAvailable(store.craftingState, zoneId, node.id)) continue;
      const radius = node.radius ?? RESOURCE_NODE_INTERACT_RADIUS;
      const dist = Math.hypot(px - node.x, pz - node.z);
      if (dist <= radius && (!best || dist < best.dist)) best = { node, dist };
    }

    return best;
  }

  private findCapturableObjective(
    store: ReturnType<typeof useGameStore.getState>,
  ): { objective: RvrObjectiveDefinition; control: CampaignControl; dist: number } | null {
    const objectives = this.currentZone?.rvrObjectives ?? [];
    if (!this.player || !store.character || objectives.length === 0) return null;
    const px = this.player.position.x;
    const pz = this.player.position.z;
    const realm = campaignRealmForCharacter(store.character);
    let best: { objective: RvrObjectiveDefinition; control: CampaignControl; dist: number } | null = null;

    for (const objective of objectives) {
      if (this.objectiveClaimsInFlight.has(objective.id)) continue;
      const status = this.objectiveStatus.get(objective.id);
      const control = status?.control ?? this.objectiveControl.get(objective.id) ?? objective.defaultRealm;
      if (!canCaptureCampaignObjective(control, store.character)) continue;
      if (status && !status.capturableBy.includes(realm)) continue;
      const dist = Math.hypot(px - objective.x, pz - objective.z);
      if (dist <= objective.captureRadius && (!best || dist < best.dist)) {
        best = { objective, control, dist };
      }
    }

    return best;
  }

  private tryGatherNearestCorpse(): boolean {
    const store = useGameStore.getState();
    const px = this.player.position.x;
    const pz = this.player.position.z;
    let best: { id: string; dist: number } | null = null;

    for (const enemy of store.enemies) {
      if (enemy.alive || !enemy.gathering || enemy.gathering.harvested) continue;
      const d = Math.hypot(px - enemy.position.x, pz - enemy.position.z);
      if (d <= CORPSE_INTERACT_RADIUS && (!best || d < best.dist)) best = { id: enemy.id, dist: d };
    }

    return best ? gatherEnemy(best.id) : false;
  }

  private tryGatherNearestResourceNode(): boolean {
    const zoneId = this.currentZone?.id;
    if (!zoneId) return false;
    const best = this.findNearestResourceNode(useGameStore.getState());
    return best ? gatherResourceNode(zoneId, best.node) : false;
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
      if (d < QUEST_INTERACT_RADIUS && (!best || d < best.dist)) best = { id: npc.id, dist: d };
    }

    if (!best) return false;
    store.setActiveQuestDialogNpcId(best.id);
    return true;
  }

  private tryToggleNearestGate(): boolean {
    const best = this.findNearestGate();
    if (!best) return false;
    this.toggleGate(best.gate);
    return true;
  }

  private tryUseNearestHousePortal(): boolean {
    const best = this.findNearestHousePortal();
    if (!best) return false;
    this.useHousePortal(best.portal);
    return true;
  }

  private resolvePlayerCollisions = (position: THREE.Vector3, radius: number): void => {
    const activeColliders = [
      ...this.propColliders.filter((collider) => !this.isStaticSourceSuppressed(collider.sourceObjectId)),
      ...(this.worldEditor?.getColliders() ?? []),
      ...(this.houseInteriors?.getColliders() ?? []),
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
      ...(this.houseInteriors?.getCameraColliders() ?? []),
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
    const playerY = this.player?.position.y;
    if (playerY !== undefined) {
      if (collider.minY !== undefined && playerY < collider.minY) return false;
      if (collider.maxY !== undefined && playerY > collider.maxY) return false;
    }
    if (collider.blocksWhen === 'always') return true;
    if (!collider.interactionId) return true;
    return !this.findGateById(collider.interactionId)?.isOpen;
  }

  private tryInteractAt(ndc: Float32Array): boolean {
    const gates = this.getVisibleGates();
    const housePortals = this.getVisibleHousePortals();
    if (!this.player || (gates.length === 0 && housePortals.length === 0)) return false;
    this.interactRaycaster.setFromCamera(
      new THREE.Vector2(ndc[0], ndc[1]),
      this.camera.camera,
    );
    const interactiveObjects = [
      ...housePortals.map((portal) => portal.object),
      ...gates.map((gate) => gate.object),
    ];
    const hits = this.interactRaycaster.intersectObjects(interactiveObjects, true);
    for (const hit of hits) {
      const housePortal = this.findHousePortalForObject(hit.object);
      if (housePortal && this.isHousePortalInRange(housePortal)) {
        this.useHousePortal(housePortal);
        return true;
      }
      const gate = this.findGateForObject(hit.object);
      if (!gate) continue;
      if (!this.isGateInRange(gate)) continue;
      this.toggleGate(gate);
      return true;
    }
    const fallbackHousePortal = this.findHousePortalNearRay();
    if (fallbackHousePortal) {
      this.useHousePortal(fallbackHousePortal);
      return true;
    }
    const fallbackGate = this.findGateNearRay();
    if (fallbackGate) {
      this.toggleGate(fallbackGate);
      return true;
    }
    return false;
  }

  private findHousePortalNearRay(): InteractiveHousePortal | null {
    let best: { portal: InteractiveHousePortal; score: number } | null = null;
    for (const portal of this.getVisibleHousePortals()) {
      if (!this.isHousePortalInRange(portal)) continue;
      const box = new THREE.Box3().setFromObject(portal.object);
      if (box.isEmpty()) continue;
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const rayDistance = this.interactRaycaster.ray.distanceSqToPoint(sphere.center);
      const radius = Math.max(1.4, Math.min(3.2, sphere.radius * 0.38));
      if (rayDistance > radius * radius) continue;
      if (!best || rayDistance < best.score) best = { portal, score: rayDistance };
    }
    return best?.portal ?? null;
  }

  private findHousePortalForObject(object: THREE.Object3D): InteractiveHousePortal | null {
    let node: THREE.Object3D | null = object;
    while (node) {
      const id = node.userData.housePortalId as string | undefined;
      if (id) {
        const portal = this.findHousePortalById(id);
        if (portal) return portal;
      }
      node = node.parent;
    }
    return null;
  }

  private findNearestHousePortal(): { portal: InteractiveHousePortal; dist: number } | null {
    if (!this.player) return null;
    let best: { portal: InteractiveHousePortal; dist: number } | null = null;
    for (const portal of this.getVisibleHousePortals()) {
      const point = portal.object.getWorldPosition(new THREE.Vector3());
      const dist = Math.hypot(point.x - this.player.position.x, point.z - this.player.position.z);
      if (dist > portal.maxDistance) continue;
      if (!best || dist < best.dist) best = { portal, dist };
    }
    return best;
  }

  private isHousePortalInRange(portal: InteractiveHousePortal): boolean {
    if (!this.player) return false;
    const point = portal.object.getWorldPosition(new THREE.Vector3());
    return Math.hypot(point.x - this.player.position.x, point.z - this.player.position.z) <= portal.maxDistance;
  }

  private getVisibleHousePortals(): InteractiveHousePortal[] {
    if (this.houseInteriors?.isActive) {
      const exit = this.houseInteriors.getExitPortal();
      return exit ? [exit] : [];
    }
    return [
      ...this.housePortals.values(),
      ...(this.worldEditor?.getHousePortals() ?? []),
    ].filter((portal) => portal.object.visible);
  }

  private findHousePortalById(id: string): InteractiveHousePortal | null {
    const exit = this.houseInteriors?.getExitPortal();
    if (exit?.id === id) return exit;
    return this.housePortals.get(id)
      ?? this.worldEditor?.getHousePortals().find((portal) => portal.id === id)
      ?? null;
  }

  private useHousePortal(portal: InteractiveHousePortal): void {
    if (portal.direction === 'exit') {
      this.leaveHouseInterior();
      return;
    }
    if (!this.player || !this.houseInteriors || this.houseInteriors.isActive) return;
    this.houseReturn = {
      position: this.player.position.clone(),
      rotationY: this.player.rotationY,
    };
    const interior = this.houseInteriors.enter(portal.interiorVariant);
    this.camera.setIndoorMode(true);
    this.movePlayerWithinZone(interior.spawn, interior.spawn.rotationY);
    useGameStore.getState().setNpcs(this.houseInteriors.getOccupants());
    useGameStore.getState().appendChat({
      id: `house-enter-${Date.now()}`,
      channel: 'system',
      from: 'System',
      body: `Entered ${portal.label.replace(/^Enter\s+/i, '')}.`,
      timestamp: Date.now(),
    });
  }

  private leaveHouseInterior(): void {
    if (!this.player || !this.houseInteriors?.isActive || !this.houseReturn) return;
    const destination = this.houseReturn;
    this.houseInteriors.deactivate();
    this.camera.setIndoorMode(false);
    this.movePlayerWithinZone(destination.position, destination.rotationY);
    this.houseReturn = null;
    useGameStore.getState().setNpcs(this.zoneNpcStates);
    void services.characters.save(this.character.id, {
      position: this.character.position,
      rotationY: this.character.rotationY,
    });
  }

  private movePlayerWithinZone(
    point: { x: number; y: number; z: number },
    rotationY: number,
  ): void {
    const next = { x: point.x, y: point.y, z: point.z };
    this.player.teleportTo(next, rotationY);
    this.character.position = next;
    this.character.rotationY = rotationY;
    useGameStore.getState().updateCharacter({ position: next, rotationY });
  }

  private findGateNearRay(): InteractiveGate | null {
    let best: { gate: InteractiveGate; score: number } | null = null;
    for (const gate of this.getVisibleGates()) {
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

  private findNearestGate(): { gate: InteractiveGate; dist: number } | null {
    const gates = this.getVisibleGates();
    if (!this.player || gates.length === 0) return null;

    let best: { gate: InteractiveGate; dist: number } | null = null;
    for (const gate of gates) {
      const dx = gate.object.position.x - this.player.position.x;
      const dz = gate.object.position.z - this.player.position.z;
      const dist = Math.hypot(dx, dz);
      if (dist > gate.maxDistance) continue;
      if (!best || dist < best.dist) best = { gate, dist };
    }

    return best;
  }

  private findGateForObject(object: THREE.Object3D): InteractiveGate | null {
    let node: THREE.Object3D | null = object;
    while (node) {
      const id = node.userData.interactionId as string | undefined;
      if (id) {
        const gate = this.findGateById(id);
        if (gate) return gate;
      }
      node = node.parent;
    }
    return null;
  }

  private getAllGates(): InteractiveGate[] {
    return [
      ...this.gates.values(),
      ...(this.worldEditor?.getGates() ?? []),
    ];
  }

  private getVisibleGates(): InteractiveGate[] {
    return this.getAllGates().filter((gate) => gate.object.visible);
  }

  private findGateById(id: string): InteractiveGate | null {
    return this.gates.get(id)
      ?? this.worldEditor?.getGates().find((gate) => gate.id === id)
      ?? null;
  }

  private toggleGate(gate: InteractiveGate): void {
    const opening = !gate.isOpen;
    gate.isOpen = opening;
    if (gate.fallbackVisual) gate.fallbackVisual.target = opening ? 1 : 0;
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

  dispose(options: { persistCharacter?: boolean } = {}) {
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
    this.houseInteriors?.dispose(this.scene);
    this.worldEditor?.dispose();
    if (this.editorAutosaveTimer !== null) {
      window.clearTimeout(this.editorAutosaveTimer);
      this.editorAutosaveTimer = null;
    }
    this.renderer?.dispose();
    if (this.renderer?.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
    if (options.persistCharacter ?? true) {
      // Persist character snapshot
      const persistedPosition = this.houseReturn?.position ?? this.player?.position ?? new THREE.Vector3();
      const persistedRotation = this.houseReturn?.rotationY ?? this.player?.rotationY ?? 0;
      void services.characters.save(this.character.id, {
        position: {
          x: persistedPosition.x,
          y: persistedPosition.y,
          z: persistedPosition.z,
        },
        rotationY: persistedRotation,
      });
    }
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

function updateGateFallbackVisual(gate: InteractiveGate, dt: number): void {
  const visual = gate.fallbackVisual;
  if (!visual) return;
  if (Math.abs(visual.progress - visual.target) < 0.001) {
    visual.progress = visual.target;
  } else {
    const direction = visual.target > visual.progress ? 1 : -1;
    visual.progress += direction * visual.speed * dt;
    if (
      (direction > 0 && visual.progress > visual.target) ||
      (direction < 0 && visual.progress < visual.target)
    ) {
      visual.progress = visual.target;
    }
  }
  applyGateFallbackVisual(gate.object, visual.progress);
}

function applyGateFallbackVisual(object: THREE.Object3D, progress: number): void {
  const clamped = Math.max(0, Math.min(1, progress));
  object.traverse((node) => {
    const side = node.userData.gateLeafSide;
    if (typeof side !== 'number') return;
    node.rotation.y = -side * (Math.PI / 2) * clamped;
  });
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

function resourceNodeKindLabel(kind: ResourceNodeSpawn['kind']): string {
  switch (kind) {
    case 'herb': return 'Herb';
    case 'ore': return 'Ore';
    case 'wood': return 'Timber';
    case 'water': return 'Water';
    case 'soil': return 'Soil';
    case 'scrap': return 'Scrap';
    case 'relic': return 'Relic';
    default: return 'Resource';
  }
}

function campaignControlLabel(control: CampaignControl): string {
  switch (control) {
    case 'aegis': return 'Aegis';
    case 'riftbound': return 'Riftbound';
    case 'contested':
    default: return 'Contested';
  }
}

function playerMoveMultiplier(effects: PlayerStatusEffect[], now: number): number {
  const active = effects.filter((effect) => effect.expiresAt > now);
  if (active.some((effect) => effect.kind === 'root' || effect.kind === 'stagger')) return 0;
  const strongestSlow = active
    .filter((effect) => effect.kind === 'slow')
    .reduce((best, effect) => Math.max(best, effect.magnitude ?? 0.35), 0);
  return Math.max(0.2, 1 - strongestSlow);
}

function abilityFeedbackKind(code: string): AbilityFeedbackKind {
  switch (code) {
    case 'cooldown': return 'cooldown';
    case 'insufficient_mana':
    case 'insufficient_resource':
      return 'resource';
    case 'no_target':
      return 'target';
    case 'out_of_range':
      return 'range';
    default:
      return 'blocked';
  }
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
