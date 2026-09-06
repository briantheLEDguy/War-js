import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { buildCampaignSnapshot, campaignKeepCaptureReward, type CampaignObjectiveStatus, type CampaignZoneStatus } from '../src/data/campaign';
import { Combat } from '../src/game/Combat';
import { Enemy } from '../src/game/Enemy';
import { Game } from '../src/game/Game';
import { KEEP_ENCOUNTER_RADIUS } from '../src/game/KeepEncounter';
import type { CampaignActivity } from '../src/game/CampaignObjectiveLogic';
import type { Player } from '../src/game/Player';
import { services } from '../src/services';
import { useGameStore } from '../src/state/gameStore';
import type { Terrain } from '../src/world/Terrain';
import type { EnemySpawn } from '../src/world/ZoneLoader';
import { makeCharacter, makePlayer, resetGameStore } from './testUtils';

interface KeepGame {
  player: Player;
  combat: Combat;
  enemies: Enemy[];
  objectiveStatus: Map<string, CampaignObjectiveStatus>;
  campaignZoneStatus: CampaignZoneStatus;
  objectiveCapture: unknown;
  objectiveClaimsInFlight: Set<string>;
  updateKeepEncounters(now: number): void;
  updateObjectiveCapture(now: number, blocked: boolean): void;
  campaignActivities(store: ReturnType<typeof useGameStore.getState>): CampaignActivity[];
}

function stagedKeep(eligible = true) {
  const snapshot = buildCampaignSnapshot('brightfen_approach', {}, {}, { brightfen_approach: { aegis: 105 } });
  const zone = snapshot.activeZone!;
  const objective = zone.objectives.find((entry) => entry.id.endsWith('_riftbound_keep'))!;
  if (!eligible) {
    objective.capturableBy = [];
    objective.captureBlockers = { aegis: 'Build 100 realm influence first' };
  }
  const spawn: EnemySpawn = {
    id: 'commander', name: 'Keep Commander', x: objective.x, z: objective.z + 3,
    level: 4, maxHealth: 320, archetype: 'captain', aggroRange: 20, attackDamage: 10,
    attackRange: 2.5, moveSpeed: 0,
    encounter: { type: 'keep_commander', objectiveId: objective.id, realm: 'riftbound', enrageHealthFraction: 0.35 },
  };
  const spawns: EnemySpawn[] = [spawn, ...[-2, 2].map((offset, index) => ({
    id: `guard-${index}`, name: 'Keep Guard', x: objective.x + offset, z: objective.z,
    level: 3, maxHealth: 150, aggroRange: 14, archetype: 'guard' as const,
  }))];
  const combat = new Combat();
  const enemies = spawns.map((entry) => {
    const enemy = new Enemy(entry, { heightAt: () => 0 } as unknown as Terrain);
    enemy.object = new THREE.Object3D();
    enemy.homePosition.set(entry.x, 0, entry.z);
    enemy.resetToHome();
    combat.registerEnemy(enemy);
    return enemy;
  });
  const player = makePlayer({ position: { x: objective.x, y: 0, z: objective.z } });
  useGameStore.getState().setCharacter(makeCharacter({ zoneId: zone.id, level: 8, health: 500, maxHealth: 500 }));
  useGameStore.getState().setEnemies(spawns.map((entry) => ({
    id: entry.id, name: entry.name, level: entry.level, health: entry.maxHealth, maxHealth: entry.maxHealth,
    position: { x: entry.x, y: 0, z: entry.z }, alive: !entry.encounter,
    ...(entry.encounter ? { keepEncounter: { objectiveId: objective.id, phase: 'locked' as const } } : {}),
  })));
  const game = Object.assign(Object.create(Game.prototype), {
    player, combat, enemies, currentZone: { id: zone.id, enemies: spawns },
    objectiveStatus: new Map([[objective.id, objective]]), campaignZoneStatus: zone,
    objectiveCapture: null, objectiveClaimsInFlight: new Set<string>(), disposed: false,
  }) as KeepGame;
  const commander = enemies[0];
  const guards = enemies.slice(1);
  function clearApproach(now = 1000) {
    for (const guard of guards) {
      useGameStore.getState().updateEnemy(guard.spawn.id, { alive: false, health: 0 });
      guard.respawnAt = now;
    }
  }
  return { game, commander, guards, objective, clearApproach, snapshot };
}

const commanderState = () => useGameStore.getState().enemies.find((entry) => entry.id === 'commander')!;

describe('staged keep encounter integration', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ inventory: [], quests: [], chat: [], campaignRewardNotice: null,
      playerDead: false, chatFocused: false, gmBuildMode: false, gmFlyingMode: false, pendingZoneTransition: null });
    vi.spyOn(services.inventory, 'update').mockResolvedValue();
    vi.spyOn(services.characters, 'save').mockResolvedValue();
    vi.spyOn(services.campaign, 'claimObjective').mockRejectedValue(new Error('Unexpected capture'));
  });
  afterEach(() => vi.restoreAllMocks());

  test('stays dormant until both campaign eligibility and cleared approach are satisfied, then summons once', () => {
    const { game, commander, objective, clearApproach } = stagedKeep(false);
    game.updateKeepEncounters(1000);
    expect(commanderState()).toMatchObject({ alive: false, keepEncounter: { phase: 'locked' } });
    objective.capturableBy = ['aegis'];
    objective.captureBlockers = {};
    game.updateKeepEncounters(1100);
    expect(commanderState().alive).toBe(false);
    clearApproach();
    game.updateKeepEncounters(1200);
    expect(commanderState()).toMatchObject({ alive: true, health: 320, keepEncounter: { phase: 'ready' } });
    expect(commander.respawnAt).toBeNull();
    expect(useGameStore.getState().targetId).toBe('commander');
    game.updateKeepEncounters(1300);
    expect(useGameStore.getState().chat.filter((entry) => entry.body.includes('enters the courtyard'))).toHaveLength(1);
    expect(game.campaignActivities(useGameStore.getState())[0].blocker).toBe('Defeat Keep Commander');
  });

  test('pauses guard respawns during the fight and defeated capture window, then completes the full hold', async () => {
    const { game, commander, guards, objective, clearApproach, snapshot } = stagedKeep();
    clearApproach();
    game.updateKeepEncounters(1000);
    commander.aggroed = true;
    game.updateKeepEncounters(2000);
    game.combat.tickRespawns(2000);
    expect(guards.every((guard) => guard.respawnAt! >= 7000)).toBe(true);
    expect(useGameStore.getState().enemies.filter((entry) => entry.id.startsWith('guard')).every((entry) => !entry.alive)).toBe(true);
    game.updateObjectiveCapture(2000, false);
    game.updateObjectiveCapture(7000, false);
    expect(services.campaign.claimObjective).not.toHaveBeenCalled();

    useGameStore.getState().updateEnemy('commander', { health: 1 });
    expect(game.combat.tryAbility(0, game.player, 7100)).toBe(true);
    game.combat.tickAbilityImpacts(7500);
    expect(commanderState()).toMatchObject({ alive: false, keepEncounter: { phase: 'defeated' } });
    expect(commander.respawnAt).toBeNull();
    game.updateKeepEncounters(30_000);
    game.combat.tickRespawns(30_000);
    expect(guards.every((guard) => guard.respawnAt! >= 35_000)).toBe(true);
    expect(game.campaignActivities(useGameStore.getState())[0].blocker).toBeNull();
    vi.mocked(services.campaign.claimObjective).mockResolvedValue({
      activity: 'capture', snapshot, zoneId: snapshot.activeZone!.id, objectiveId: objective.id, realm: 'aegis',
      objective: { ...objective, control: 'aegis' }, reward: campaignKeepCaptureReward(snapshot.activeZone!.id), zoneControlChanged: true,
    });
    game.updateObjectiveCapture(30_000, false);
    game.updateObjectiveCapture(32_999, false);
    expect(services.campaign.claimObjective).not.toHaveBeenCalled();
    game.updateObjectiveCapture(33_000, false);
    await vi.waitFor(() => expect(game.objectiveClaimsInFlight.size).toBe(0), { interval: 1 });
    expect(services.campaign.claimObjective).toHaveBeenCalledExactlyOnceWith('brightfen_approach', objective.id, 'aegis');
    expect(useGameStore.getState().campaignRewardNotice?.itemNames).toContain("Brightfen Approach Victor's Amulet");
    objective.control = 'aegis';
    game.updateKeepEncounters(34_000);
    expect(commanderState()).toMatchObject({ alive: false, keepEncounter: { phase: 'locked' } });
    expect(game.campaignActivities(useGameStore.getState())).toEqual([]);
  });

  test.each(['death', 'leave courtyard', 'leash', 'eligibility lost'] as const)('%s resets commander, guards and pending attacks', (cause) => {
    const { game, commander, guards, objective, clearApproach } = stagedKeep();
    clearApproach();
    game.updateKeepEncounters(1000);
    game.combat.tickEnemies(0.1, 1100, game.player);
    game.updateKeepEncounters(1200);
    expect(commanderState().keepEncounter?.phase).toBe('engaged');
    expect(commander.pendingAbility).not.toBeNull();
    useGameStore.getState().updateEnemy('commander', { health: 25,
      statusEffects: [{ id: 'test-slow', label: 'Slow', kind: 'slow', expiresAt: 9000, sourceAbilityId: 'test' }] });
    expect(game.combat.tryAbility(0, game.player, 1220)).toBe(true);
    if (cause === 'death') useGameStore.getState().setPlayerDead(true);
    if (cause === 'leave courtyard') game.player.position.x = objective.x + KEEP_ENCOUNTER_RADIUS + 1;
    if (cause === 'leash') {
      commander.position.x += 30;
      game.combat.tickEnemies(0.1, 1250, game.player);
    }
    if (cause === 'eligibility lost') objective.capturableBy = [];
    game.updateKeepEncounters(1300);
    expect(commanderState()).toMatchObject({ alive: false, health: 320, activeCast: null, statusEffects: [], keepEncounter: { phase: 'locked' } });
    expect(commander.pendingAbility).toBeNull();
    expect(commander.aggroed).toBe(false);
    expect(useGameStore.getState().targetId).toBeNull();
    expect(guards.every((guard) => guard.respawnAt === null)).toBe(true);
    expect(useGameStore.getState().enemies.filter((entry) => entry.id.startsWith('guard')).every((entry) => entry.alive && entry.health === 150)).toBe(true);
    // A player attack released before the reset must not strike the newly restored encounter.
    game.combat.resetEnemy('commander', true);
    game.combat.tickAbilityImpacts(9000);
    expect(commanderState().health).toBe(320);
  });

  test('leaving after victory resets the approach instead of preserving an unlimited capture shortcut', () => {
    const { game, objective, clearApproach } = stagedKeep();
    clearApproach();
    game.updateKeepEncounters(1000);
    useGameStore.getState().updateEnemy('commander', { health: 1 });
    expect(game.combat.tryAbility(0, game.player, 1100)).toBe(true);
    game.combat.tickAbilityImpacts(1500);
    expect(commanderState().keepEncounter?.phase).toBe('defeated');
    game.player.position.x = objective.x + KEEP_ENCOUNTER_RADIUS + 1;
    game.updateKeepEncounters(1600);
    expect(commanderState().keepEncounter?.phase).toBe('locked');
    game.player.position.x = objective.x;
    game.updateKeepEncounters(1700);
    expect(commanderState().alive).toBe(false);
    expect(game.campaignActivities(useGameStore.getState())[0].blocker).toBe('Defeat 2 remaining defenders');
    expect(services.campaign.claimObjective).not.toHaveBeenCalled();
  });

  test('a pending self-area attack cannot hit guards or a commander restored after a reset', () => {
    const { game, objective, clearApproach } = stagedKeep();
    clearApproach();
    game.updateKeepEncounters(1000);
    // Reliquary Smash has no target ID and resolves around the release position.
    expect(game.combat.tryAbility(5, game.player, 1100)).toBe(true);
    objective.capturableBy = [];
    game.updateKeepEncounters(1101);
    expect(commanderState().keepEncounter?.phase).toBe('locked');
    // Even a subsequent restoration cannot inherit damage from the failed attempt.
    game.combat.resetEnemy('commander', true);
    game.combat.tickAbilityImpacts(5000);
    for (const enemy of useGameStore.getState().enemies) {
      expect(enemy.health, enemy.id).toBe(enemy.maxHealth);
      expect(enemy.statusEffects, enemy.id).toEqual([]);
    }
  });

  test('a ranged hit at 22 metres engages the commander and preserves the fight across enrage', () => {
    const { game, commander, clearApproach } = stagedKeep();
    clearApproach();
    game.updateKeepEncounters(1000);
    game.player.position.x = commander.position.x + 22;
    game.player.position.z = commander.position.z;
    useGameStore.getState().updateCharacter({ className: 'Ember Arcanist' });
    useGameStore.getState().updateEnemy('commander', { health: 120 });
    game.combat.tickEnemies(0, 1100, game.player);
    expect(commander.aggroed).toBe(false);
    expect(game.combat.tryAbility(0, game.player, 1200)).toBe(true);
    game.combat.tickAbilityImpacts(3000);
    expect(commanderState().health).toBeGreaterThan(0);
    expect(commanderState().health).toBeLessThanOrEqual(112);
    expect(commander.aggroed).toBe(true);
    game.updateKeepEncounters(3000);
    game.combat.tickEnemies(0, 3000, game.player);
    game.updateKeepEncounters(3100);
    expect(commanderState()).toMatchObject({ alive: true, keepEncounter: { phase: 'enraged' } });
    expect(useGameStore.getState().enemies.filter((entry) => entry.id.startsWith('guard')).every((entry) => !entry.alive)).toBe(true);
    expect(useGameStore.getState().chat.some((entry) => entry.body.includes('regrouped'))).toBe(false);
  });

  test('announces enrage once at the health threshold', () => {
    const { game, commander, clearApproach } = stagedKeep();
    clearApproach();
    game.updateKeepEncounters(1000);
    commander.aggroed = true;
    useGameStore.getState().updateEnemy('commander', { health: 112 });
    game.updateKeepEncounters(1200);
    game.updateKeepEncounters(1300);
    expect(commanderState().keepEncounter?.phase).toBe('enraged');
    expect(useGameStore.getState().chat.filter((entry) => entry.body.includes('last stand'))).toHaveLength(1);
  });
});
