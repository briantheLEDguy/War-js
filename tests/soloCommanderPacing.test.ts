import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { Combat } from '../src/game/Combat';
import { Enemy } from '../src/game/Enemy';
import type { Player } from '../src/game/Player';
import { ResourceRegeneration } from '../src/game/ResourceRegeneration';
import { getCareerAbilityKit } from '../src/game/abilities/abilityData';
import { isAbilityUnlocked } from '../src/game/abilities/abilityProgression';
import { playerAbilityMoveMultiplier } from '../src/game/abilities/playerAbilityEffects';
import type { AbilityDefinition } from '../src/game/abilities/types';
import { enemyAttackContains, type EnemyCastState } from '../src/game/enemyAttackTelegraph';
import { services } from '../src/services';
import type { CharacterState, Vec3 } from '../src/services/types';
import { useGameStore } from '../src/state/gameStore';
import type { Terrain } from '../src/world/Terrain';
import type { EnemySpawn } from '../src/world/ZoneLoader';
import { makeCharacter, makePlayer, resetGameStore } from './testUtils';

vi.mock('../src/game/abilities/AbilityVfx', () => ({ spawnAbilityVfx: vi.fn() }));

const STEP_MS = 50;
const REACTION_MS = 200;
const LIMIT_MS = 180_000;
const WALK_SPEED = 6;
type Policy = 'respond' | 'ignore_warnings';
const generatedZone = JSON.parse(readFileSync(new URL('../public/assets/maps/brightfen_approach.json', import.meta.url), 'utf8')) as {
  id: string; enemies: EnemySpawn[];
};
const representatives: Pick<CharacterState, 'className' | 'race'>[] = [
  { className: 'Siegewright', race: 'dwarf' },
  { className: 'Stoneguard', race: 'dwarf' },
  { className: 'Battle Prelate', race: 'empire' },
  { className: 'Ember Arcanist', race: 'empire' },
  { className: 'Warbrute', race: 'greenskin' },
];

function seededRandom(seed: number): () => number {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 0x1_0000_0000;
  };
}

function distance(a: Vec3, b: Vec3): number {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

function pointFrom(origin: Vec3, toward: Vec3, radius: number): Vec3 {
  const d = distance(origin, toward);
  return { x: origin.x + (d > 0.01 ? (toward.x - origin.x) / d : 0) * radius,
    y: 0, z: origin.z + (d > 0.01 ? (toward.z - origin.z) / d : 1) * radius };
}

function dodgeDestination(cast: EnemyCastState, player: Player, home: Vec3): Vec3 {
  const footprint = cast.footprint;
  if (footprint.shape === 'circle') {
    return pointFrom(footprint.origin, distance(footprint.origin, home) > 2 ? home : player.position, footprint.radius + 0.6);
  }
  // Pick the nearer side of the committed cone, with a bias toward the courtyard.
  const sides = [-1, 1].map((sign) => ({
    x: footprint.origin.x + Math.sin(footprint.rotationY + sign * Math.PI / 2) * 3.2,
    y: 0,
    z: footprint.origin.z + Math.cos(footprint.rotationY + sign * Math.PI / 2) * 3.2,
  }));
  return sides.sort((a, b) => distance(a, player.position) + distance(a, home) * 0.1 -
    distance(b, player.position) - distance(b, home) * 0.1)[0];
}

function walkToward(player: Player, destination: Vec3, now: number): void {
  const effects = useGameStore.getState().playerStatusEffects.filter((effect) => effect.expiresAt > now);
  const blocked = effects.some((effect) => effect.kind === 'root' || effect.kind === 'stagger');
  const slow = Math.max(0, ...effects.filter((effect) => effect.kind === 'slow').map((effect) => effect.magnitude ?? 0.35));
  const speed = blocked ? 0 : WALK_SPEED * Math.max(0.2, 1 - slow) * playerAbilityMoveMultiplier(effects, now);
  const d = distance(player.position, destination);
  if (d > 0) Object.assign(player.position, pointFrom(player.position, destination, Math.min(d, speed * STEP_MS / 1000)));
  player.object.position.set(player.position.x, player.position.y, player.position.z);
}

function interrupts(ability: AbilityDefinition): boolean {
  return ability.effects.some((effect) => effect.status?.kind === 'silence' || effect.status?.kind === 'stagger');
}

function damageScore(ability: AbilityDefinition): number {
  const character = useGameStore.getState().character!;
  const resource = useGameStore.getState().abilityResource?.current ?? 0;
  return ability.effects.reduce((score, effect) => {
    if (effect.kind !== 'damage' || !effect.amount) return score;
    const amount = effect.amount;
    return score + (amount.min + amount.max) / 2 + character.strength * (amount.statScale ?? 0) +
      character.level * (amount.levelScale ?? 0) + (ability.resource.spendAllCareer ? resource : ability.resource.careerCost ?? 0) * (amount.resourceScale ?? 0);
  }, 0);
}

/** Open, flat courtyard after guards are cleared; no equipment, consumables, or resource refills.
 * Inputs are sampled every 200 ms. Stay at 3 m, react to warnings after 200 ms,
 * try a ready interrupt while walking out, and pause ordinary attacks until the warning ends.
 * Outside warnings: heal below 65%, otherwise use the largest ready damage packet.
 * The comparison policy ignores warnings and keeps attacking; control attacks can still interrupt incidentally.
 * Actual ability validation, GCD, release delays, regeneration, status ticks, and enemy AI remain live.
 * This tests a repeatable informed policy, not human reaction, exploration, or expedition duration.
 */
function simulateSolo(career: Pick<CharacterState, 'className' | 'race'>, policy: Policy) {
  const spawn = generatedZone.enemies.find((entry) => entry.encounter?.realm === (career.race === 'greenskin' ? 'aegis' : 'riftbound'))!;
  expect(spawn.encounter?.type).toBe('keep_commander');
  const enemy = new Enemy(spawn, { heightAt: () => 0 } as unknown as Terrain);
  enemy.object = new THREE.Object3D();
  enemy.homePosition.set(spawn.x, 0, spawn.z);
  enemy.resetToHome();
  const player = makePlayer({ position: { x: spawn.x, y: 0, z: spawn.z + 3 } });
  // CharacterLocal's level-one pools plus four checkLevelUp gains.
  useGameStore.getState().setCharacter(makeCharacter({ ...career, id: `solo-${career.className}`, level: 5,
    zoneId: generatedZone.id, xp: 0, health: 180, maxHealth: 180, mana: 140, maxMana: 140, strength: 18,
    position: { ...player.position }, equipment: {},
  }));
  useGameStore.getState().setEnemies([{ id: spawn.id, name: spawn.name, level: spawn.level,
    position: { x: spawn.x, y: 0, z: spawn.z }, health: spawn.maxHealth, maxHealth: spawn.maxHealth, alive: true,
    keepEncounter: { objectiveId: spawn.encounter!.objectiveId, phase: 'engaged' },
  }]);
  useGameStore.getState().setTarget(spawn.id);
  const combat = new Combat();
  combat.registerEnemy(enemy);
  combat.setAbilityMovementHandler((request) => {
    if (distance(request.destination, enemy.homePosition) > 20) return false;
    Object.assign(player.position, request.destination);
    player.object.position.set(player.position.x, player.position.y, player.position.z);
    return true;
  });
  const regeneration = new ResourceRegeneration();
  const abilities = getCareerAbilityKit(career.className).abilities.filter((ability) => isAbilityUnlocked(ability, 5));
  const activations: { name: string; slot: number; at: number; previousGcd: number }[] = [];
  const violations: string[] = [];
  let warning: EnemyCastState | null = null;
  let destination: Vec3 | null = null;
  let dodged = 0;
  let interrupted = 0;
  let hitBySpecial = 0;
  let minHealth = 180;
  let minMana = 140;
  let damageTaken = 0;
  let elapsed = 0;
  let maxEnemyDistance = 0;
  let previousEnemyHealth = spawn.maxHealth;

  for (elapsed = 0; elapsed <= LIMIT_MS; elapsed += STEP_MS) {
    const now = 1000 + elapsed;
    const store = useGameStore.getState();
    if (store.playerDead || !store.enemies[0].alive) break;
    const cast = store.enemies[0].activeCast;
    if (cast && cast.startedAt !== warning?.startedAt) {
      warning = cast;
      destination = dodgeDestination(cast, player, enemy.homePosition);
    }
    const reacting = cast && now - cast.startedAt >= REACTION_MS;
    if (reacting && policy === 'respond') walkToward(player, destination!, now);
    else if (!cast && distance(player.position, enemy.position) > 3) {
      walkToward(player, pointFrom(enemy.position, player.position, 3), now);
    }
    player.rotationY = Math.atan2(enemy.position.x - player.position.x, enemy.position.z - player.position.z);
    player.object.rotation.y = player.rotationY;

    if (elapsed % REACTION_MS === 0) {
      const ranked = abilities.filter((ability) => {
        if (cast && policy === 'respond') return reacting && interrupts(ability) && !ability.effects.some((effect) => effect.kind === 'movement');
        if (damageScore(ability) > 0) return true;
        return store.character!.health < store.character!.maxHealth * 0.65 && ability.effects.some((effect) => effect.kind === 'heal');
      }).sort((a, b) => {
        const score = (ability: AbilityDefinition) => damageScore(ability) +
          (store.character!.health < store.character!.maxHealth * 0.65 && ability.effects.some((effect) => effect.kind === 'heal') ? 1000 : 0);
        return score(b) - score(a) || a.slot - b.slot;
      });
      for (const ability of ranked) {
        // Self-area abilities must actually reach the enemy before spending their cooldown.
        if (ability.targeting.target === 'self' && damageScore(ability) > 0 && distance(player.position, enemy.position) > (ability.targeting.radius ?? 0)) continue;
        const previousGcd = useGameStore.getState().globalCooldownUntil;
        if (combat.tryAbility(ability.slot, player, now)) {
          activations.push({ name: ability.name, slot: ability.slot, at: now, previousGcd });
          break;
        }
      }
    }
    store.tickCooldowns(STEP_MS / 1000);
    combat.tickAbilityImpacts(now);
    combat.tickStatusEffects(now);
    const beforeEnemies = useGameStore.getState().character!.health;
    combat.tickEnemies(STEP_MS / 1000, now, player);
    const afterEnemies = useGameStore.getState();
    damageTaken += Math.max(0, beforeEnemies - afterEnemies.character!.health);
    minHealth = Math.min(minHealth, afterEnemies.character!.health);
    minMana = Math.min(minMana, afterEnemies.character!.mana);
    if (cast && !afterEnemies.enemies[0].activeCast && afterEnemies.enemies[0].alive) {
      if (now < cast.dueAt) interrupted++;
      else if (enemyAttackContains(cast.footprint, player.position)) hitBySpecial++;
      else dodged++;
      warning = null;
      destination = null;
    }
    if (afterEnemies.enemies[0].health > previousEnemyHealth) violations.push('Enemy reset');
    previousEnemyHealth = afterEnemies.enemies[0].health;
    maxEnemyDistance = Math.max(maxEnemyDistance, distance(enemy.position, enemy.homePosition));
    if (!afterEnemies.playerDead) {
      const patch = regeneration.tick(afterEnemies.character, STEP_MS / 1000, enemy.aggroed);
      if (patch) afterEnemies.updateCharacter(patch);
    }
    const character = useGameStore.getState().character!;
    const resource = useGameStore.getState().abilityResource!;
    if (!Number.isFinite(character.health) || character.health < 0 || character.health > character.maxHealth ||
      !Number.isFinite(character.mana) || character.mana < 0 || character.mana > character.maxMana ||
      !Number.isFinite(resource.current) || resource.current < 0 || resource.current > resource.max) violations.push('Invalid resource pool');
    combat.tickFloatingDamage(now);
  }
  const state = useGameStore.getState();
  return { className: career.className, policy, bossHealth: spawn.maxHealth, seconds: elapsed / 1000,
    won: !state.enemies[0].alive && !state.playerDead, playerDead: state.playerDead, endHealth: state.character!.health, minHealth,
    damageTaken, minMana, endMana: state.character!.mana, dodged, interrupted, hitBySpecial,
    activations, violations, maxEnemyDistance, enemyRespawnAt: enemy.respawnAt,
  };
}

describe('deterministic solo Tier 1 commander feasibility', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ playerDead: false, quests: [], chat: [], inventory: [] });
    vi.spyOn(Math, 'random').mockImplementation(seededRandom(20260906));
    vi.spyOn(services.inventory, 'update').mockResolvedValue(undefined);
    vi.spyOn(services.characters, 'save').mockResolvedValue(undefined);
    vi.spyOn(services.quests, 'update').mockResolvedValue(undefined);
  });
  afterEach(() => vi.restoreAllMocks());

  test.each(representatives.flatMap((career) => (['respond', 'ignore_warnings'] as const).map((policy) => ({ ...career, policy }))))(
    '$className reaches a bounded outcome using $policy and only level 5 skills', (career) => {
    const result = simulateSolo(career, career.policy);
    if (process.env.SOLO_COMMANDER_REPORT === '1') {
      const { activations, violations, ...metrics } = result;
      console.info(JSON.stringify({ ...metrics, casts: activations.length, skills: [...new Set(activations.map((entry) => entry.name))], violations }));
    }
    expect(result.won || result.playerDead, JSON.stringify(result)).toBe(true);
    expect(result.seconds).toBeLessThanOrEqual(LIMIT_MS / 1000);
    if (career.policy === 'respond') {
      expect(result.won, JSON.stringify(result)).toBe(true);
      expect(result.minHealth).toBeGreaterThan(0);
      expect(result.dodged + result.interrupted).toBeGreaterThan(0);
    } else {
      expect(result.dodged).toBe(0);
      expect(result.hitBySpecial).toBeGreaterThan(0);
    }
    expect(result.violations).toEqual([]);
    expect(result.maxEnemyDistance).toBeLessThan(25);
    expect(result.enemyRespawnAt).toBeNull();
    expect(result.activations.length).toBeGreaterThan(1);
    for (const activation of result.activations) {
      expect(activation.at).toBeGreaterThanOrEqual(activation.previousGcd);
      expect(isAbilityUnlocked(getCareerAbilityKit(career.className).abilities[activation.slot], 5)).toBe(true);
    }
  });
});
