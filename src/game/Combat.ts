import * as THREE from 'three';
import { services } from '../services';
import { useGameStore, type EnemyState } from '../state/gameStore';
import type { Player } from './Player';
import type { Enemy } from './Enemy';
import { followObject, staticTarget, type VfxLayer } from './animation/VfxLayer';

/**
 * Map hotbar slot index → animation action id that the player's animator
 * should play when the ability fires successfully. The animator validates
 * / ignores ids it doesn't recognize, so this is safe to call for any
 * career (Warrior Priest is the only class with a rig today).
 *
 *   slot 0 — autoattack
 *   slot 1 — heavy strike (Slot 1 ability)
 *   slot 2 — ranged shot  (Slot 2 ability)
 *   slot 3 — bandage      (Slot 3 self-heal)
 */
const SLOT_ACTION_ID = ['autoattack', 'heavy_strike', 'ranged_shot', 'bandage'] as const;

/** Action durations in seconds, mirrored across careers that share the slot. */
const SLOT_ACTION_DURATION = [0.45, 0.85, 0.55, 1.20];

/**
 * Play the slot's animation and any class-specific VFX. Pulled into a helper
 * so every ability branch spawns both in lockstep (the alternative is six
 * near-identical copies of this boilerplate across `tryAbility`).
 *
 * `targetEnemy` is optional — only outgoing abilities (damage) pass one. Self
 * buffs / heals don't need an enemy target; their VFX anchor to `self`.
 */
function playSlotAction(
  player: Player,
  slot: number,
  vfx: VfxLayer | null,
  targetEnemy: { position: { x: number; y: number; z: number } } | null = null,
): void {
  const anim = player.animator;
  if (!anim) return;
  const id = SLOT_ACTION_ID[slot];
  const dur = SLOT_ACTION_DURATION[slot];
  if (!id) return;
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

export class Combat {
  private enemiesById = new Map<string, Enemy>();
  /** VFX layer set by `Game` at start — combat spawns class FX through it. */
  private vfx: VfxLayer | null = null;

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

  /** Slot 0 — Autoattack: 5–10 dmg, 1.5 s CD, melee range. */
  tryAutoattack(player: Player, now: number): boolean {
    const store = useGameStore.getState();
    if (!store.targetId || store.hotbarCooldowns[0] > 0) return false;
    const target = store.enemies.find((e) => e.id === store.targetId);
    if (!target || !target.alive) return false;
    if (dist2D(target.position, player.position) > ATTACK_RANGE) return false;

    const dmg = 5 + Math.floor(Math.random() * 6);
    const newHp = Math.max(0, target.health - dmg);
    store.updateEnemy(store.targetId, { health: newHp });
    store.setHotbarCooldown(0, ATTACK_COOLDOWN);
    store.pushDamage(makeDmg(now, dmg, 'damage', target.position));
    playSlotAction(player, 0, this.vfx, target);
    if (newHp <= 0) this.killEnemy(store.targetId, target, now, store);
    return true;
  }

  /**
   * Slots 1-3 abilities.
   *
   * 1 — Heavy Strike: 12–24 dmg, melee, 5 s CD, 10 mana
   * 2 — Ranged Shot:   5–12 dmg, 10 u range, 3 s CD, 8 mana
   * 3 — Bandage:       35–50 HP self-heal, 10 s CD, 15 mana
   */
  tryAbility(slot: number, player: Player, now: number): boolean {
    const store = useGameStore.getState();
    if (store.hotbarCooldowns[slot] > 0) return false;
    const { character, updateCharacter } = store;

    if (slot === 1) {
      if (!character || character.mana < 10) return false;
      const target = this.resolveTarget(store, ATTACK_RANGE, player);
      if (!target) return false;
      const dmg = 12 + Math.floor(Math.random() * 13);
      const newHp = Math.max(0, target.health - dmg);
      store.updateEnemy(target.id, { health: newHp });
      store.setHotbarCooldown(1, 5.0);
      updateCharacter({ mana: Math.max(0, character.mana - 10) });
      store.pushDamage(makeDmg(now, dmg, 'damage', target.position));
      playSlotAction(player, 1, this.vfx, target);
      if (newHp <= 0) this.killEnemy(target.id, target, now, store);
      return true;
    }

    if (slot === 2) {
      if (!character || character.mana < 8) return false;
      const target = this.resolveTarget(store, 10.0, player);
      if (!target) return false;
      const dmg = 5 + Math.floor(Math.random() * 8);
      const newHp = Math.max(0, target.health - dmg);
      store.updateEnemy(target.id, { health: newHp });
      store.setHotbarCooldown(2, 3.0);
      updateCharacter({ mana: Math.max(0, character.mana - 8) });
      store.pushDamage(makeDmg(now, dmg, 'damage', target.position));
      playSlotAction(player, 2, this.vfx, target);
      if (newHp <= 0) this.killEnemy(target.id, target, now, store);
      return true;
    }

    if (slot === 3) {
      if (!character || character.mana < 15) return false;
      if (character.health >= character.maxHealth) return false;
      const heal = 35 + Math.floor(Math.random() * 16);
      updateCharacter({
        health: Math.min(character.maxHealth, character.health + heal),
        mana: Math.max(0, character.mana - 15),
      });
      store.setHotbarCooldown(3, 10.0);
      store.pushDamage(makeDmg(now, heal, 'heal', player.position));
      playSlotAction(player, 3, this.vfx, null);
      return true;
    }

    return false;
  }

  // ---------------------------------------------------------------------------
  // Enemy AI
  // ---------------------------------------------------------------------------

  /** Chase, attack, and leash enemies each game tick. */
  tickEnemies(dt: number, now: number, player: Player) {
    const store = useGameStore.getState();
    if (store.playerDead) return;

    for (const e of store.enemies) {
      if (!e.alive) continue;
      const enemy = this.enemiesById.get(e.id);
      if (!enemy) continue;

      const aggroRange  = enemy.spawn.aggroRange  ?? 0;
      if (aggroRange <= 0) continue; // passive — skip AI

      const attackRange = enemy.spawn.attackRange  ?? 2.5;
      const moveSpeed   = enemy.spawn.moveSpeed    ?? 3.5;
      const baseDmg     = enemy.spawn.attackDamage ?? 5;

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
      }
      if (!enemy.aggroed) continue;

      // Chase
      if (distToPlayer > attackRange * 0.9) {
        enemy.moveToward(player.position, moveSpeed, dt);
        store.updateEnemy(e.id, { position: vecToPlain(enemy.position) });
      }

      // Melee attack
      enemy.attackCooldown = Math.max(0, enemy.attackCooldown - dt);
      if (enemy.attackCooldown <= 0 && distToPlayer <= attackRange + 0.5) {
        enemy.attackCooldown = 2.0 + Math.random() * 0.5;
        const dmg = baseDmg + Math.floor(Math.random() * 4);
        const { character, updateCharacter, setPlayerDead } = store;
        if (character) {
          const newHp = Math.max(0, character.health - dmg);
          updateCharacter({ health: newHp });
          store.pushDamage(makeDmg(now, dmg, 'damage', player.position));
          if (newHp <= 0) setPlayerDead(true);
        }
      }
    }
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
    }
    store.updateEnemy(targetId, { alive: false });

    // XP
    if (store.character) {
      const xpGain = 20 + target.level * 10;
      store.updateCharacter({ xp: store.character.xp + xpGain });
    }

    // Loot
    this.tryLootDrop(store);
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
    if (!canStack && usedSlots.size >= 16) return;

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
