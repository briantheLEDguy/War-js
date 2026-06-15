import * as THREE from 'three';
import { buildEnemyGatheringState } from '../data/crafting';
import { INVENTORY_CAPACITY } from '../data/items';
import { services } from '../services';
import { useGameStore, type CombatStatusEffect, type EnemyState } from '../state/gameStore';
import type { Player } from './Player';
import type { Enemy } from './Enemy';
import { followObject, staticTarget, type VfxLayer } from './animation/VfxLayer';
import { checkLevelUp, registerEnemyKill } from './QuestLogic';
import {
  getAbilityActivationFailure,
  tryActivateAbility,
  type AbilityActivationBlockers,
  type AbilityFailureReason,
  type PendingAbilityImpact,
} from './abilities/AbilityRuntime';
import type { AbilityEffect } from './abilities/types';

/** Legacy four-slot animation helper retained for older procedural animators. */
const SLOT_ACTION_ID = ['autoattack', 'heavy_strike', 'ranged_shot', 'bandage'] as const;
const SLOT_ACTION_DURATION = [0.45, 0.85, 0.55, 1.20];

/** Play a legacy slot action and optional class-specific VFX. */
function playSlotAction(
  player: Player,
  slot: number,
  vfx: VfxLayer | null,
  targetEnemy: { position: { x: number; y: number; z: number } } | null = null,
): void {
  const anim = player.animator;
  const id = SLOT_ACTION_ID[slot];
  const dur = SLOT_ACTION_DURATION[slot];
  if (!id) return;
  if (!anim) {
    player.playGlbAction(id, dur);
    return;
  }
  anim.playAction(id, dur);

  if (!vfx) return;
  // VFX should never take down combat — if a build step throws (bad shader,
  // missing target, etc.) we log and continue so the ability still "fires"
  // even if its visuals are missing.
  try {
    const ctx = {
      self: followObject(player.object),
      target: targetEnemy
        ? staticTarget(
            new THREE.Vector3(
              targetEnemy.position.x,
              targetEnemy.position.y,
              targetEnemy.position.z,
            ),
          )
        : null,
    };
    const effect = anim.getActionVfx(id, ctx);
    if (effect) vfx.spawn(effect);
  } catch (err) {
    console.error('VFX spawn failed for action', id, err);
  }
}

const ATTACK_COOLDOWN = 1.5;  // seconds — autoattack
const ATTACK_RANGE    = 3.0;  // melee reach in world units
const RESPAWN_DELAY   = 5000; // milliseconds
const LEASH_RANGE     = 25;   // units from home before enemy resets

type EnemyArchetype = NonNullable<Enemy['spawn']['archetype']>;

interface EnemyAbilityProfile {
  id: string;
  label: string;
  range: number;
  cooldownSec: number;
  windupSec: number;
  kind: 'melee' | 'ranged' | 'cast';
  damage: {
    base: number;
    levelScale: number;
    variance: number;
  };
  status?: {
    id: string;
    label: string;
    kind: 'slow' | 'root' | 'stagger' | 'debuff';
    durationSec: number;
    magnitude?: number;
  };
}

const ENEMY_ABILITY_PROFILES: Record<EnemyArchetype, EnemyAbilityProfile[]> = {
  raider: [
    {
      id: 'raider_hamstring',
      label: 'Hamstring',
      range: 3.2,
      cooldownSec: 5,
      windupSec: 0.25,
      kind: 'melee',
      damage: { base: 6, levelScale: 1.35, variance: 4 },
      status: { id: 'hamstrung', label: 'Hamstrung', kind: 'slow', durationSec: 2.5, magnitude: 0.35 },
    },
  ],
  guard: [
    {
      id: 'guard_shield_bash',
      label: 'Shield Bash',
      range: 3.3,
      cooldownSec: 6,
      windupSec: 0.35,
      kind: 'melee',
      damage: { base: 8, levelScale: 1.45, variance: 3 },
      status: { id: 'shield_bashed', label: 'Shield Bashed', kind: 'stagger', durationSec: 0.8 },
    },
  ],
  caster: [
    {
      id: 'caster_rift_bolt',
      label: 'Rift Bolt',
      range: 16,
      cooldownSec: 4.5,
      windupSec: 0.7,
      kind: 'cast',
      damage: { base: 10, levelScale: 1.8, variance: 5 },
      status: { id: 'rattled', label: 'Rattled', kind: 'debuff', durationSec: 4, magnitude: 0.15 },
    },
  ],
  beast: [
    {
      id: 'beast_pounce',
      label: 'Pounce',
      range: 5,
      cooldownSec: 5,
      windupSec: 0.2,
      kind: 'melee',
      damage: { base: 7, levelScale: 1.6, variance: 4 },
      status: { id: 'pinned', label: 'Pinned', kind: 'root', durationSec: 0.75 },
    },
  ],
  captain: [
    {
      id: 'captain_breaker',
      label: 'Line Breaker',
      range: 4,
      cooldownSec: 5.5,
      windupSec: 0.45,
      kind: 'melee',
      damage: { base: 12, levelScale: 2.0, variance: 5 },
      status: { id: 'pressed', label: 'Pressed', kind: 'debuff', durationSec: 5, magnitude: 0.2 },
    },
  ],
};

export class Combat {
  private enemiesById = new Map<string, Enemy>();
  /** VFX layer set by `Game` at start — combat spawns class FX through it. */
  private vfx: VfxLayer | null = null;
  private pendingImpacts: PendingAbilityImpact[] = [];

  registerEnemy(e: Enemy) {
    this.enemiesById.set(e.spawn.id, e);
  }

  /** Inject the per-scene VFX layer. Safe to call once at Game.start(). */
  setVfxLayer(layer: VfxLayer) {
    this.vfx = layer;
  }

  // ---------------------------------------------------------------------------
  // Targeting
  // ---------------------------------------------------------------------------

  /** Raycast against enemy hit-spheres; returns the id of the closest hit. */
  tryTargetAt(ndc: Float32Array, camera: THREE.Camera): string | null {
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(ndc[0], ndc[1]), camera);
    const { enemies } = useGameStore.getState();
    let best: { id: string; dist: number } | null = null;
    for (const e of enemies) {
      if (!e.alive) continue;
      const enemy = this.enemiesById.get(e.id);
      if (!enemy) continue;
      const center = new THREE.Vector3(e.position.x, e.position.y + 1.2, e.position.z);
      const sphere = new THREE.Sphere(center, 1.0);
      const hit = new THREE.Vector3();
      if (raycaster.ray.intersectSphere(sphere, hit)) {
        const d = raycaster.ray.origin.distanceTo(hit);
        if (!best || d < best.dist) best = { id: e.id, dist: d };
      }
    }
    return best?.id ?? null;
  }

  // ---------------------------------------------------------------------------
  // Player abilities
  // ---------------------------------------------------------------------------

/** Back-compat alias: slot 0 is now the first career ability. */
  tryAutoattack(player: Player, now: number): boolean {
    return this.tryAbility(0, player, now);
  }

  /** Activate a data-driven career ability by hotbar slot. */
  tryAbility(slot: number, player: Player, now: number): boolean {
    const result = tryActivateAbility({
      slot,
      player,
      now,
      vfx: this.vfx,
      getEnemyObject: (id) => this.enemiesById.get(id)?.object ?? null,
    });
    if (!result) return false;
    this.pendingImpacts.push(...result.impacts);
    return true;
  }

  getAbilityFailure(
    slot: number,
    player: Player,
    now: number,
    blockers: AbilityActivationBlockers = {},
  ): AbilityFailureReason | null {
    return getAbilityActivationFailure({
      slot,
      player,
      now,
      vfx: this.vfx,
      getEnemyObject: (id) => this.enemiesById.get(id)?.object ?? null,
    }, blockers);
  }

  /** Resolve delayed release/projectile impacts from activated abilities. */
  tickAbilityImpacts(now: number): void {
    if (this.pendingImpacts.length === 0) return;
    const ready: PendingAbilityImpact[] = [];
    const pending: PendingAbilityImpact[] = [];
    for (const impact of this.pendingImpacts) {
      if (impact.dueAt <= now) ready.push(impact);
      else pending.push(impact);
    }
    this.pendingImpacts = pending;
    for (const impact of ready) this.applyAbilityImpact(impact, now);
  }

  /** Expire enemy status tags produced by ability effects. */
  tickStatusEffects(now: number): void {
    const store = useGameStore.getState();
    store.clearExpiredPlayerStatusEffects(now);
    for (const enemy of store.enemies) {
      if (!enemy.statusEffects?.length) continue;
      const active = enemy.statusEffects.filter((effect) => effect.expiresAt > now);
      if (active.length !== enemy.statusEffects.length) {
        store.updateEnemy(enemy.id, { statusEffects: active });
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Enemy AI
  // ---------------------------------------------------------------------------

  /** Chase, attack, and leash enemies each game tick. */
  tickEnemies(dt: number, now: number, player: Player) {
    const store = useGameStore.getState();
    if (store.playerDead) {
      for (const enemy of this.enemiesById.values()) enemy.pendingAbility = null;
      return;
    }

    for (const e of store.enemies) {
      const enemy = this.enemiesById.get(e.id);
      if (!enemy) continue;
      if (!e.alive) {
        enemy.pendingAbility = null;
        continue;
      }

      const aggroRange  = enemy.spawn.aggroRange  ?? 0;
      if (aggroRange <= 0) continue; // passive — skip AI

      const attackRange = enemy.spawn.attackRange  ?? 2.5;
      const moveSpeed   = (enemy.spawn.moveSpeed ?? 3.5) * enemyMoveMultiplier(e, now);
      const baseDmg     = enemy.spawn.attackDamage ?? 5;
      const archetype = enemy.spawn.archetype ?? 'raider';
      const abilityProfile = ENEMY_ABILITY_PROFILES[archetype];
      const preferredRange = enemy.spawn.preferredRange
        ?? (archetype === 'caster' ? 12 : attackRange * 0.85);
      const castingBlocked =
        hasBlockingStatus(e, 'silence', now) ||
        hasBlockingStatus(e, 'stagger', now);

      const distToPlayer  = dist2D(player.position, enemy.position);
      const distFromHome  = enemy.position.distanceTo(enemy.homePosition);

      // Leash: too far from home → reset
      if (distFromHome > LEASH_RANGE) {
        enemy.resetToHome();
        store.updateEnemy(e.id, {
          health: enemy.spawn.maxHealth,
          position: vecToPlain(enemy.homePosition),
        });
        continue;
      }

      // Aggro acquisition / drop
      if (!enemy.aggroed && distToPlayer <= aggroRange) {
        enemy.aggroed = true;
      } else if (enemy.aggroed && distToPlayer > LEASH_RANGE) {
        enemy.aggroed = false;
        enemy.pendingAbility = null;
      }
      if (!enemy.aggroed) continue;

      if (castingBlocked) enemy.pendingAbility = null;
      enemy.faceToward(player.position);

      // Movement: melee enemies close; casters maintain a stand-off band.
      let moved = false;
      if (distToPlayer > preferredRange + 0.75 && moveSpeed > 0) {
        enemy.moveToward(player.position, moveSpeed, dt);
        moved = true;
      } else if (archetype === 'caster' && distToPlayer < preferredRange - 2 && moveSpeed > 0) {
        enemy.moveAwayFrom(player.position, moveSpeed * 0.85, dt);
        moved = true;
      }
      if (moved) {
        store.updateEnemy(e.id, { position: vecToPlain(enemy.position) });
      }

      this.tickEnemyAbilityCast(enemy, e, player, now, store);
      enemy.abilityCooldown = Math.max(0, enemy.abilityCooldown - dt);
      if (!castingBlocked && !enemy.pendingAbility && enemy.abilityCooldown <= 0) {
        this.tryStartEnemyAbility(enemy, abilityProfile, dist2D(player.position, enemy.position), now);
      }

      // Melee attack
      enemy.attackCooldown = Math.max(0, enemy.attackCooldown - dt);
      if (
        archetype !== 'caster' &&
        enemy.attackCooldown <= 0 &&
        dist2D(player.position, enemy.position) <= attackRange + 0.5 &&
        !hasBlockingStatus(e, 'stagger', now)
      ) {
        enemy.attackCooldown = 2.0 + Math.random() * 0.5;
        const dmg = baseDmg + Math.floor(Math.random() * 4);
        const { character, updateCharacter, setPlayerDead } = store;
        if (character) {
          enemy.playAttackAction('melee');
          const newHp = Math.max(0, character.health - dmg);
          updateCharacter({ health: newHp });
          store.pushDamage(makeDmg(now, dmg, 'damage', player.position));
          if (newHp <= 0) setPlayerDead(true);
        }
      }
    }
  }

  private tryStartEnemyAbility(
    enemy: Enemy,
    abilities: EnemyAbilityProfile[],
    distanceToPlayer: number,
    now: number,
  ): void {
    const ability = abilities.find((entry) => distanceToPlayer <= entry.range);
    if (!ability) return;
    enemy.pendingAbility = {
      abilityId: ability.id,
      dueAt: now + ability.windupSec * 1000,
    };
    enemy.abilityCooldown = ability.cooldownSec;
    enemy.playAttackAction(ability.kind);
  }

  private tickEnemyAbilityCast(
    enemy: Enemy,
    state: EnemyState,
    player: Player,
    now: number,
    store: ReturnType<typeof useGameStore.getState>,
  ): void {
    const pending = enemy.pendingAbility;
    if (!pending || pending.dueAt > now) return;

    const ability = enemyAbilityById(enemy.spawn.archetype ?? 'raider', pending.abilityId);
    enemy.pendingAbility = null;
    if (!ability) return;
    if (
      hasBlockingStatus(state, 'silence', now) ||
      hasBlockingStatus(state, 'stagger', now) ||
      dist2D(player.position, enemy.position) > ability.range + 1.5
    ) {
      return;
    }

    this.applyEnemyAbility(enemy, state, ability, player, now, store);
  }

  private applyEnemyAbility(
    enemy: Enemy,
    state: EnemyState,
    ability: EnemyAbilityProfile,
    player: Player,
    now: number,
    store: ReturnType<typeof useGameStore.getState>,
  ): void {
    const current = useGameStore.getState();
    const character = current.character;
    if (!character || current.playerDead) return;

    const dmg = Math.max(
      1,
      Math.round(
        ability.damage.base +
        state.level * ability.damage.levelScale +
        Math.random() * ability.damage.variance,
      ),
    );
    const newHp = Math.max(0, character.health - dmg);
    current.updateCharacter({ health: newHp });
    current.pushDamage(makeDmg(now, dmg, 'damage', player.position));

    if (ability.status) {
      current.addPlayerStatusEffect({
        id: `${ability.status.id}-${state.id}`,
        label: ability.status.label,
        kind: ability.status.kind,
        expiresAt: now + ability.status.durationSec * 1000,
        magnitude: ability.status.magnitude,
        sourceEnemyId: state.id,
      });
    }

    store.appendChat({
      id: `enemy-ability-${Date.now()}-${state.id}-${ability.id}`,
      channel: 'system',
      from: state.name,
      body: `${state.name} used ${ability.label}.`,
      timestamp: Date.now(),
    });

    enemy.faceToward(player.position);
    if (newHp <= 0) current.setPlayerDead(true);
  }

  // ---------------------------------------------------------------------------
  // Periodic ticks
  // ---------------------------------------------------------------------------

  /** Respawn dead enemies once their timer expires. */
  tickRespawns(now: number) {
    const store = useGameStore.getState();
    for (const e of store.enemies) {
      const enemy = this.enemiesById.get(e.id);
      if (!enemy) continue;
      if (!e.alive && enemy.respawnAt !== null && now >= enemy.respawnAt) {
        enemy.respawnAt = null;
        enemy.resetToHome();
        store.updateEnemy(e.id, {
          alive: true,
          health: enemy.spawn.maxHealth,
          position: vecToPlain(enemy.homePosition),
          gathering: undefined,
        });
      }
    }
  }

  /** Remove floating damage numbers older than 1.2 s. */
  tickFloatingDamage(now: number) {
    const store = useGameStore.getState();
    const expired = store.floatingDamage.filter((d) => now - d.spawnedAt > 1200);
    for (const d of expired) store.expireDamage(d.id);
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private applyAbilityImpact(impact: PendingAbilityImpact, now: number): void {
    const store = useGameStore.getState();
    const targets = this.resolveImpactTargets(impact, store.enemies);

    for (const effect of impact.effects) {
      if (effect.kind === 'heal') {
        this.applyHeal(effect, impact, now, store);
        continue;
      }

      if (effect.kind === 'damage') {
        for (const target of targets) {
          this.applyDamageToEnemy(effect, impact, target, now, store);
        }
        continue;
      }

      if (effect.kind === 'status' && effect.status) {
        for (const target of targets) {
          this.applyStatusToEnemy(effect.status, impact, target, now, store);
        }
      }
    }
  }

  private resolveImpactTargets(
    impact: PendingAbilityImpact,
    enemies: EnemyState[],
  ): EnemyState[] {
    const shape = impact.ability.targeting.shape;
    const radius = impact.ability.targeting.radius ?? 0;

    if (shape === 'area' || shape === 'deployable') {
      const center = impact.ability.targeting.target === 'self'
        ? impact.sourcePosition
        : currentTargetPosition(impact, enemies) ?? impact.center;
      return enemies.filter((enemy) =>
        enemy.alive && dist2D(enemy.position, center) <= Math.max(1, radius),
      );
    }

    if (shape === 'cone') {
      return enemies.filter((enemy) =>
        enemy.alive &&
        dist2D(enemy.position, impact.sourcePosition) <= impact.ability.targeting.range &&
        isInsideCone(impact.sourcePosition, impact.sourceRotationY, enemy.position),
      );
    }

    if (!impact.targetId) return [];
    const target = enemies.find((enemy) => enemy.id === impact.targetId && enemy.alive);
    return target ? [target] : [];
  }

  private applyDamageToEnemy(
    effect: AbilityEffect,
    impact: PendingAbilityImpact,
    target: EnemyState,
    now: number,
    store: ReturnType<typeof useGameStore.getState>,
  ): void {
    if (!effect.amount) return;
    const latest = useGameStore.getState().enemies.find((enemy) => enemy.id === target.id);
    if (!latest || !latest.alive) return;

    const amount = rollAmount(effect.amount, impact);
    const newHp = Math.max(0, latest.health - amount);
    store.updateEnemy(latest.id, { health: newHp });
    store.pushDamage(makeDmg(now, amount, 'damage', latest.position));
    this.enemiesById.get(latest.id)?.playHitReact();

    if (newHp <= 0) {
      this.killEnemy(latest.id, { ...latest, health: newHp }, now, store);
    }
  }

  private applyHeal(
    effect: AbilityEffect,
    impact: PendingAbilityImpact,
    now: number,
    store: ReturnType<typeof useGameStore.getState>,
  ): void {
    if (!effect.amount || !store.character) return;
    const amount = rollAmount(effect.amount, impact);
    const newHp = Math.min(store.character.maxHealth, store.character.health + amount);
    if (newHp === store.character.health) return;
    store.updateCharacter({ health: newHp });
    store.pushDamage(makeDmg(now, amount, 'heal', impact.sourcePosition));
  }

  private applyStatusToEnemy(
    status: NonNullable<AbilityEffect['status']>,
    impact: PendingAbilityImpact,
    target: EnemyState,
    now: number,
    store: ReturnType<typeof useGameStore.getState>,
  ): void {
    const effect: CombatStatusEffect = {
      id: `${status.id}-${impact.ability.id}`,
      label: status.label,
      kind: status.kind,
      expiresAt: now + status.durationSec * 1000,
      magnitude: status.magnitude,
      sourceAbilityId: impact.ability.id,
    };
    const active = (target.statusEffects ?? [])
      .filter((existing) => existing.id !== effect.id && existing.expiresAt > now);
    store.updateEnemy(target.id, { statusEffects: [...active, effect] });
  }

  private resolveTarget(
    store: ReturnType<typeof useGameStore.getState>,
    maxRange: number,
    player: Player,
  ): EnemyState | null {
    if (!store.targetId) return null;
    const target = store.enemies.find((e) => e.id === store.targetId);
    if (!target || !target.alive) return null;
    if (dist2D(target.position, player.position) > maxRange) return null;
    return target;
  }

  private killEnemy(
    targetId: string,
    target: EnemyState,
    now: number,
    store: ReturnType<typeof useGameStore.getState>,
  ) {
    const enemyObj = this.enemiesById.get(targetId);
    if (enemyObj) {
      enemyObj.respawnAt = now + RESPAWN_DELAY;
      enemyObj.aggroed = false;
      enemyObj.attackCooldown = 0;
      enemyObj.abilityCooldown = 0;
      enemyObj.pendingAbility = null;
    }
    store.updateEnemy(targetId, {
      alive: false,
      gathering: buildEnemyGatheringState(target.name),
    });

    // XP
    if (store.character) {
      const xpGain = 20 + target.level * 10;
      store.updateCharacter({ xp: store.character.xp + xpGain });
    }

    // Loot
    this.tryLootDrop(store);

    // Quest progress + level-up check from the kill's XP award.
    registerEnemyKill(target.name);
    checkLevelUp();
    store.completeGuidedTask('kill');
  }

  private tryLootDrop(store: ReturnType<typeof useGameStore.getState>) {
    if (Math.random() > 0.65) return;

    const table = [
      { key: 'potion_health', name: 'Health Potion', qty: 1 },
      { key: 'potion_health', name: 'Health Potion', qty: 1 },
      { key: 'bread',         name: 'Hunk of Bread',  qty: 1 },
      { key: 'potion_mana',   name: 'Mana Potion',    qty: 1 },
    ];
    const drop = table[Math.floor(Math.random() * table.length)];

    // Check capacity
    const inv = store.inventory;
    const usedSlots = new Set(inv.map((i) => i.slot));
    const canStack  = inv.some((i) => i.key === drop.key && i.qty < 99);
    if (!canStack && usedSlots.size >= INVENTORY_CAPACITY) return;

    store.addInventoryItem(drop);

    // Persist asynchronously
    if (store.character) {
      void services.inventory
        .update(store.character.id, useGameStore.getState().inventory)
        .catch(() => {});
    }

    store.appendChat({
      id: `loot-${Date.now()}`,
      channel: 'system',
      from: 'System',
      body: `You found: ${drop.name}`,
      timestamp: Date.now(),
    });
  }
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function dist2D(
  a: { x: number; z: number },
  b: { x: number; z: number },
): number {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

function currentTargetPosition(
  impact: PendingAbilityImpact,
  enemies: EnemyState[],
): { x: number; y: number; z: number } | null {
  if (!impact.targetId) return null;
  return enemies.find((enemy) => enemy.id === impact.targetId)?.position ?? null;
}

function isInsideCone(
  origin: { x: number; z: number },
  rotationY: number,
  point: { x: number; z: number },
): boolean {
  const dx = point.x - origin.x;
  const dz = point.z - origin.z;
  const dist = Math.hypot(dx, dz);
  if (dist <= 0.001) return true;
  const forwardX = Math.sin(rotationY);
  const forwardZ = Math.cos(rotationY);
  const dot = (dx / dist) * forwardX + (dz / dist) * forwardZ;
  return dot >= Math.cos(Math.PI / 4);
}

function rollAmount(
  amount: NonNullable<AbilityEffect['amount']>,
  impact: PendingAbilityImpact,
): number {
  const rolled = amount.min + Math.random() * (amount.max - amount.min);
  const stat = (amount.statScale ?? 0) * impact.sourceStrength;
  const level = (amount.levelScale ?? 0) * impact.sourceLevel;
  const resource = (amount.resourceScale ?? 0) * impact.resourceSpent;
  return Math.max(1, Math.round(rolled + stat + level + resource));
}

function enemyMoveMultiplier(enemy: EnemyState, now: number): number {
  const active = (enemy.statusEffects ?? []).filter((effect) => effect.expiresAt > now);
  if (active.some((effect) => effect.kind === 'root' || effect.kind === 'stagger')) return 0;
  const strongestSlow = active
    .filter((effect) => effect.kind === 'slow')
    .reduce((best, effect) => Math.max(best, effect.magnitude ?? 0.3), 0);
  return Math.max(0.15, 1 - strongestSlow);
}

function hasBlockingStatus(enemy: EnemyState, kind: CombatStatusEffect['kind'], now: number): boolean {
  return (enemy.statusEffects ?? []).some((effect) => effect.kind === kind && effect.expiresAt > now);
}

function enemyAbilityById(
  archetype: EnemyArchetype,
  abilityId: string,
): EnemyAbilityProfile | null {
  return ENEMY_ABILITY_PROFILES[archetype].find((ability) => ability.id === abilityId) ?? null;
}

function vecToPlain(v: { x: number; y: number; z: number }) {
  return { x: v.x, y: v.y, z: v.z };
}

function makeDmg(
  now: number,
  amount: number,
  kind: 'damage' | 'heal' | 'miss',
  pos: { x: number; y: number; z: number },
) {
  return {
    id: `${now}-${Math.random().toString(36).slice(2, 7)}`,
    amount,
    worldPos: { x: pos.x, y: pos.y + 2.1, z: pos.z },
    spawnedAt: now,
    kind,
  };
}
