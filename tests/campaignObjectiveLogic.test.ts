import { describe, expect, test } from 'vitest';
import {
  campaignRealmForCharacter,
  canCaptureCampaignObjective,
  captureProgressPct,
  describeCampaignActivity,
  objectiveDefenders,
  OBJECTIVE_CAPTURE_HOLD_MS,
  OBJECTIVE_DEFENSE_HOLD_MS,
} from '../src/game/CampaignObjectiveLogic';
import { buildCampaignSnapshot, type CampaignObjectiveStatus } from '../src/data/campaign';
import { INVENTORY_CAPACITY } from '../src/data/items';
import type { InventoryItem } from '../src/services/types';
import type { EnemySpawn } from '../src/world/ZoneLoader';
import { makeEnemy } from './testUtils';

describe('campaign objective capture helpers', () => {
  test('derives campaign realm from playable race', () => {
    expect(campaignRealmForCharacter({ race: 'empire' })).toBe('aegis');
    expect(campaignRealmForCharacter({ race: 'dwarf' })).toBe('aegis');
    expect(campaignRealmForCharacter({ race: 'high_elf' })).toBe('aegis');
    expect(campaignRealmForCharacter({ race: 'chaos' })).toBe('riftbound');
    expect(campaignRealmForCharacter({ race: 'greenskin' })).toBe('riftbound');
    expect(campaignRealmForCharacter({ race: 'dark_elf' })).toBe('riftbound');
  });

  test('allows capture only when current control differs from the character realm', () => {
    expect(canCaptureCampaignObjective('riftbound', { race: 'empire' })).toBe(true);
    expect(canCaptureCampaignObjective('contested', { race: 'empire' })).toBe(true);
    expect(canCaptureCampaignObjective('aegis', { race: 'empire' })).toBe(false);
    expect(canCaptureCampaignObjective('riftbound', { race: 'greenskin' })).toBe(false);
    expect(canCaptureCampaignObjective(undefined, null)).toBe(false);
  });

  test('tracks a clamped three-second capture hold', () => {
    expect(captureProgressPct(100, 100)).toBe(0);
    expect(captureProgressPct(100, 100 + OBJECTIVE_CAPTURE_HOLD_MS / 2)).toBe(0.5);
    expect(captureProgressPct(100, 100 + OBJECTIVE_CAPTURE_HOLD_MS * 2)).toBe(1);
  });
});

describe('campaign encounter activity', () => {
  const zoneId = 'sunmeadow_march';
  const zone = buildCampaignSnapshot(zoneId).zones.find((entry) => entry.id === zoneId)!;
  const standard = zone.objectives.find((entry) => entry.type === 'battle_objective')!;
  const objective: CampaignObjectiveStatus = { ...standard, x: 0, z: 0, captureRadius: 13 };
  const spawn: EnemySpawn = {
    id: 'guard', name: 'Guard', level: 3, x: 20, z: 0, maxHealth: 190, archetype: 'guard', aggroRange: 14,
  };

  test('a spawn-bound defender still blocks after being kited beyond the objective ring', () => {
    const guard = makeEnemy({ id: spawn.id, position: { x: 40, y: 0, z: 0 } });
    expect(objectiveDefenders(objective, [spawn], [guard])).toEqual([guard]);
    const activity = describeCampaignActivity({ zoneId, objective, realm: 'aegis', spawns: [spawn],
      enemies: [guard], player: { x: 0, z: 0 }, inventory: [], nowMs: 1000 });
    expect(activity).toMatchObject({ activity: 'defend', defenders: 1, blocker: 'Defeat 1 remaining defender', holdMs: OBJECTIVE_DEFENSE_HOLD_MS });
  });

  test('only living aggressive defenders or aggressive arrivals in the ring block progress', () => {
    const spawns: EnemySpawn[] = [
      spawn,
      { ...spawn, id: 'dead' },
      { ...spawn, id: 'dummy', aggroRange: 0 },
      { ...spawn, id: 'arrival', x: 50 },
      { ...spawn, id: 'distant', x: 50 },
    ];
    const enemies = [
      makeEnemy({ id: 'guard', position: { x: 40, y: 0, z: 0 } }),
      makeEnemy({ id: 'dead', alive: false }),
      makeEnemy({ id: 'dummy' }),
      makeEnemy({ id: 'arrival', position: { x: 1, y: 0, z: 0 } }),
      makeEnemy({ id: 'distant', position: { x: 50, y: 0, z: 0 } }),
    ];
    expect(objectiveDefenders(objective, spawns, enemies).map((enemy) => enemy.id)).toEqual(['guard', 'arrival']);
  });

  test('clearing all defenders enables the friendly eight-second defense and a respawn blocks it again', () => {
    const input = { zoneId, objective, realm: 'aegis' as const, spawns: [spawn], player: { x: 0, z: 0 }, inventory: [], nowMs: 1000 };
    expect(describeCampaignActivity({ ...input, enemies: [makeEnemy({ id: 'guard', alive: false })] }))
      .toMatchObject({ activity: 'defend', defenders: 0, blocker: null, holdMs: 8000 });
    expect(describeCampaignActivity({ ...input, enemies: [makeEnemy({ id: 'guard', alive: true })] }))
      .toMatchObject({ defenders: 1, blocker: 'Defeat 1 remaining defender' });
  });

  test('capture eligibility remains authoritative and valid enemy standards use a three-second hold', () => {
    const input = { zoneId, realm: 'aegis' as const, spawns: [], enemies: [], player: { x: 0, z: 0 }, inventory: [], nowMs: 1000 };
    const enemyObjective: CampaignObjectiveStatus = { ...objective, control: 'riftbound', capturableBy: ['aegis'] };
    expect(describeCampaignActivity({ ...input, objective: enemyObjective }))
      .toMatchObject({ activity: 'capture', blocker: null, holdMs: 3000 });
    expect(describeCampaignActivity({ ...input, objective: { ...enemyObjective, capturableBy: [], captureBlockers: { aegis: 'Build influence first' } } }))
      .toMatchObject({ blocker: 'Build influence first' });
  });

  test('full inventory blocks keep rewards without blocking item-free standard activities', () => {
    const inventory: InventoryItem[] = Array.from({ length: INVENTORY_CAPACITY }, (_, slot) => ({
      key: `occupied-${slot}`, name: 'Occupied slot', qty: 1, slot,
    }));
    const input = { zoneId, realm: 'aegis' as const, spawns: [], enemies: [], player: { x: 0, z: 0 }, inventory, nowMs: 1000 };
    const keep = { ...objective, type: 'keep' as const, control: 'riftbound' as const, capturableBy: ['aegis' as const] };
    expect(describeCampaignActivity({ ...input, objective: keep }).blocker).toContain('Make room');
    expect(describeCampaignActivity({ ...input, objective }).blocker).toBeNull();
  });

  test('defense cooldown expires at its exact wall-clock boundary', () => {
    const input = { zoneId, objective: { ...objective, defenseReadyAt: { aegis: 5000 } }, realm: 'aegis' as const,
      spawns: [], enemies: [], player: { x: 0, z: 0 }, inventory: [] };
    expect(describeCampaignActivity({ ...input, nowMs: 4999 }).blocker).toBe('Defense ready in 1 second');
    expect(describeCampaignActivity({ ...input, nowMs: 5000 }).blocker).toBeNull();
  });
});
