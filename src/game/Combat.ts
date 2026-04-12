import * as THREE from 'three';
import { useGameStore } from '../state/gameStore';
import type { Player } from './Player';
import type { Enemy } from './Enemy';

const ATTACK_COOLDOWN = 1.5;
const ATTACK_RANGE = 3.0;
const RESPAWN_DELAY = 5.0;

export class Combat {
  private enemiesById = new Map<string, Enemy>();

  registerEnemy(e: Enemy) {
    this.enemiesById.set(e.spawn.id, e);
  }

  /** Raycast against enemy hit-regions; select closest hit id. */
  tryTargetAt(ndc: Float32Array, camera: THREE.Camera): string | null {
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(ndc[0], ndc[1]), camera);
    const { enemies } = useGameStore.getState();
    let best: { id: string; dist: number } | null = null;
    for (const e of enemies) {
      if (!e.alive) continue;
      const enemy = this.enemiesById.get(e.id);
      if (!enemy) continue;
      // Sphere intersect around enemy position
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

  /** Attempt to fire slot 0 (autoattack). Returns true if fired. */
  tryAutoattack(player: Player, now: number): boolean {
    const store = useGameStore.getState();
    const targetId = store.targetId;
    if (!targetId) return false;
    if (store.hotbarCooldowns[0] > 0) return false;
    const target = store.enemies.find((e) => e.id === targetId);
    if (!target || !target.alive) return false;
    const dx = target.position.x - player.position.x;
    const dz = target.position.z - player.position.z;
    const dist = Math.hypot(dx, dz);
    if (dist > ATTACK_RANGE) return false;

    const dmg = 5 + Math.floor(Math.random() * 6);
    const newHp = Math.max(0, target.health - dmg);
    store.updateEnemy(targetId, { health: newHp });
    store.setHotbarCooldown(0, ATTACK_COOLDOWN);
    store.pushDamage({
      id: `${now}-${Math.random().toString(36).slice(2, 7)}`,
      amount: dmg,
      worldPos: { x: target.position.x, y: target.position.y + 2.1, z: target.position.z },
      spawnedAt: now,
      kind: 'damage',
    });
    if (newHp <= 0) {
      const enemyObj = this.enemiesById.get(targetId);
      if (enemyObj) enemyObj.respawnAt = now + RESPAWN_DELAY;
      store.updateEnemy(targetId, { alive: false });
      // Award XP
      const { character, updateCharacter } = store;
      if (character) {
        const xpGain = 20 + target.level * 10;
        const xp = character.xp + xpGain;
        updateCharacter({ xp });
      }
    }
    return true;
  }

  /** Handle respawns each frame. */
  tickRespawns(now: number) {
    const store = useGameStore.getState();
    for (const e of store.enemies) {
      const enemy = this.enemiesById.get(e.id);
      if (!enemy) continue;
      if (!e.alive && enemy.respawnAt && now >= enemy.respawnAt) {
        enemy.respawnAt = null;
        store.updateEnemy(e.id, { alive: true, health: enemy.spawn.maxHealth });
      }
    }
  }

  /** Simple enemy behavior: dummies don't move/attack back (Phase 1). */
  tickEnemies(_dt: number, _player: Player) {
    // Phase 2 hook: add chase/attack AI here
  }

  /** Expire old floating damage numbers (>1.2s). */
  tickFloatingDamage(now: number) {
    const store = useGameStore.getState();
    const expired = store.floatingDamage.filter((d) => now - d.spawnedAt > 1200);
    for (const d of expired) store.expireDamage(d.id);
  }
}
