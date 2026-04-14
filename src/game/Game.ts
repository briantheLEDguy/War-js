import * as THREE from 'three';
import { services } from '../services';
import type { CharacterState } from '../services/types';
import { useGameStore, type EnemyState } from '../state/gameStore';
import { spawnNpcs } from '../world/NpcSpawner';
import { spawnProps } from '../world/Props';
import { setupSky } from '../world/Skybox';
import { Terrain } from '../world/Terrain';
import { loadZone, type ZoneTrigger } from '../world/ZoneLoader';
import { AssetLoader } from './AssetLoader';
import { FollowCamera } from './Camera';
import { Combat } from './Combat';
import { Enemy } from './Enemy';
import { Input } from './Input';
import { Player } from './Player';
import { VfxLayer } from './animation/VfxLayer';

export class Game {
  private renderer!: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera!: FollowCamera;
  private input!: Input;
  private loader = new AssetLoader();
  private terrain = new Terrain({ size: 140, segments: 112 });
  private player!: Player;
  private enemies: Enemy[] = [];
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
  private spawnPoint = { x: 0, y: 0, z: 0 };

  private currentZoneName = '';
  private zoneTriggers: ZoneTrigger[] = [];

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
    container.appendChild(this.renderer.domElement);

    const aspect = container.clientWidth / container.clientHeight;
    this.camera = new FollowCamera(this.renderer.domElement, aspect);
    this.input = new Input(this.renderer.domElement);
    this.vfx = new VfxLayer(this.scene);
    this.combat.setVfxLayer(this.vfx);

    // Zone
    const zone = await loadZone(this.character.zoneId ?? 'zone1');
    if (this.disposed) return; // guard: React Strict Mode may dispose before first await resolves
    this.currentZoneName = zone.name;

    // Sky + lights
    await setupSky(this.scene, this.loader, this.renderer, zone.skybox);
    if (this.disposed) return;

    // Terrain
    const terrainMesh = await this.terrain.build(this.loader, {
      size: zone.size,
      segments: zone.segments,
      diffuseTexture: zone.terrainTexture,
      heightTexture: zone.heightmap,
      flatTerrain: zone.flatTerrain,
    });
    if (this.disposed) return;
    this.scene.add(terrainMesh);

    // Props
    await spawnProps(this.scene, this.loader, this.terrain, zone.props);
    if (this.disposed) return;

    // NPCs
    const npcStates = await spawnNpcs(this.scene, this.loader, this.terrain, zone.npcs ?? []);
    if (this.disposed) return;
    useGameStore.getState().setNpcs(npcStates);

    // Zone triggers
    this.zoneTriggers = zone.zoneTriggers ?? [];

    // Player
    const sp = zone.spawnPoint ?? { x: 0, y: 0, z: 0 };
    this.spawnPoint = sp;
    this.character.position = { x: sp.x, y: 0, z: sp.z };
    this.player = new Player(this.character, this.terrain);
    await this.player.build(this.loader, this.scene);
    if (this.disposed) return;

    // Store the respawn point so the HUD can use it
    useGameStore.getState().setRespawnPoint(sp);

    // Enemies
    const enemyState: EnemyState[] = [];
    for (const es of zone.enemies) {
      const e = new Enemy(es, this.terrain);
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
      position: { x: sp.x, y: 0, z: sp.z },
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
    this.update(dt, tMs);
    this.renderer.render(this.scene, this.camera.camera);
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
        this.terrain.heightAt(rp.x, rp.z),
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

    // Debug / inventory toggle
    if (this.input.wasPressed('Backquote')) store.toggleDebug();
    if (this.input.wasPressed('KeyI')) store.toggleInventory();

    // Chat focus
    if (this.input.wasPressed('Enter') && !store.chatFocused) store.setChatFocused(true);

    // Combat inputs (blocked while dead or typing in chat)
    if (!store.chatFocused && !store.playerDead) {
      if (this.input.mouseLeftClickedThisFrame) {
        const id = this.combat.tryTargetAt(this.input.lastClickNDC, this.camera.camera);
        store.setTarget(id);
      }
      if (this.input.wasPressed('Digit1')) this.combat.tryAutoattack(this.player, tMs);
      if (this.input.wasPressed('Digit2')) this.combat.tryAbility(1, this.player, tMs);
      if (this.input.wasPressed('Digit3')) this.combat.tryAbility(2, this.player, tMs);
      if (this.input.wasPressed('Digit4')) this.combat.tryAbility(3, this.player, tMs);

      // Touch hotbar taps (set by Hotbar component via the store)
      const touchSlot = store.pendingTouchAbility;
      if (touchSlot !== null) {
        store.setPendingTouchAbility(null);
        if (touchSlot === 0) this.combat.tryAutoattack(this.player, tMs);
        else this.combat.tryAbility(touchSlot, this.player, tMs);
      }
    }

    // Tick
    store.tickCooldowns(dt);
    if (!store.playerDead) this.player.update(dt, this.input, this.camera);
    this.camera.update(this.player.position, this.input);
    this.combat.tickEnemies(dt, tMs, this.player);
    this.combat.tickRespawns(tMs);
    this.combat.tickFloatingDamage(tMs);
    this.vfx.update(dt);

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

  private onDispose: Array<() => void> = [];

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    window.removeEventListener('resize', this.onResize);
    this.input?.dispose();
    this.camera?.dispose();
    for (const fn of this.onDispose) {
      try { fn(); } catch { /* ignore */ }
    }
    try { void services.world.leaveZone(this.character.zoneId); } catch { /* ignore */ }
    this.vfx?.dispose();
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
