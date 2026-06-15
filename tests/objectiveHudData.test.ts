import { describe, expect, test } from 'vitest';
import { formatDistance, questNpcStatus, resolveTrackedQuests } from '../src/ui/hud/objectiveHudData';
import type { CharacterState, QuestProgress } from '../src/services/types';
import type { EnemyState } from '../src/state/gameStore';
import type { NpcState } from '../src/world/NpcSpawner';

const character: CharacterState = {
  id: 'char-objectives',
  name: 'Objective Tester',
  className: 'Battle Prelate',
  race: 'empire',
  bodyVariant: 'm',
  level: 1,
  zoneId: 'aegis_capital',
  xp: 0,
  health: 100,
  maxHealth: 100,
  mana: 50,
  maxMana: 50,
  strength: 10,
  gold: 0,
  position: { x: 0, y: 0, z: 0 },
  rotationY: 0,
};

const questNpc: NpcState = {
  id: 'quest-1',
  name: 'Wilhelm Krupp',
  title: 'Dispatch Officer',
  role: 'questgiver',
  position: { x: 0, y: 0, z: 42 },
};

function questProgress(overrides: Partial<QuestProgress> = {}): QuestProgress {
  return {
    questId: 'dawnline-01-scouting',
    status: 'active',
    counters: { 'kill-raiders': 1 },
    ...overrides,
  };
}

function enemy(overrides: Partial<EnemyState> = {}): EnemyState {
  return {
    id: 'gob-raider',
    name: 'Campaign Raider',
    level: 1,
    health: 60,
    maxHealth: 60,
    position: { x: 0, y: 0, z: 24 },
    alive: true,
    ...overrides,
  };
}

describe('objective HUD data', () => {
  test('tracks active quests with nearest enemy distance context', () => {
    const tracked = resolveTrackedQuests({
      progresses: [questProgress()],
      npcs: [questNpc],
      enemies: [enemy(), enemy({ id: 'far-raider', position: { x: 0, y: 0, z: 80 } })],
      playerPosition: { x: 0, z: 10 },
    });

    expect(tracked).toHaveLength(1);
    expect(tracked[0].title).toBe('Scouts of the Dawnline');
    expect(tracked[0].rows[0]).toMatchObject({
      current: 1,
      required: 4,
      complete: false,
      context: { label: 'Campaign Raider', distance: 14 },
    });
  });

  test('prioritizes ready turn-ins and exposes quest NPC availability', () => {
    const status = questNpcStatus('quest-1', [questProgress({
      status: 'ready_to_turn_in',
      counters: { 'kill-raiders': 4 },
    })], character);
    const tracked = resolveTrackedQuests({
      progresses: [questProgress({
        status: 'ready_to_turn_in',
        counters: { 'kill-raiders': 4 },
      })],
      npcs: [questNpc],
      enemies: [],
      playerPosition: { x: 0, z: 2 },
    });

    expect(status.readyCount).toBe(1);
    expect(status.offerCount).toBe(0);
    expect(tracked[0].ready).toBe(true);
    expect(tracked[0].turnIn).toMatchObject({ label: 'Wilhelm Krupp', distance: 40 });
  });

  test('formats distances into stable HUD labels', () => {
    expect(formatDistance(undefined)).toBe('');
    expect(formatDistance(4.2)).toBe('4m');
    expect(formatDistance(27)).toBe('25m');
    expect(formatDistance(146)).toBe('150m');
  });
});
