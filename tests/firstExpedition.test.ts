import { readFileSync } from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { QUESTS, QUESTS_BY_ID, migrateQuestProgressForRealm, questAvailableToCharacter } from '../src/data/quests';
import { playerRealmForRace, type PlayableRace } from '../src/data/careers';
import { getItemDefinition } from '../src/data/items';
import { acceptQuest, checkLevelUp, questsOfferedBy, questsReadyToTurnIn, registerEnemyKill, turnInQuest } from '../src/game/QuestLogic';
import { newlyUnlockedAbilities } from '../src/game/abilities/abilityProgression';
import { services } from '../src/services';
import type { QuestProgress } from '../src/services/types';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, resetGameStore } from './testUtils';

const expeditions = [
  { race: 'empire' as const, prefix: 'dawnline', capital: 'aegis_capital', field: 'brightfen_approach' },
  { race: 'greenskin' as const, prefix: 'cinderfen', capital: 'riftspire_capital', field: 'cinderfen_outskirts' },
];

function activeQuest(questId: string, counters?: Record<string, number>): QuestProgress {
  return {
    questId,
    status: 'active',
    counters: counters ?? Object.fromEntries(QUESTS_BY_ID[questId].objectives.map((objective) => [objective.id, 0])),
  };
}

interface ExpeditionMap {
  campaign: { tier: string };
  npcs: Array<{ id: string; role: string }>;
  enemies: Array<{ name: string; level: number; archetype: string; characterProfileKey: string }>;
  zoneTriggers: Array<{ targetZoneId: string }>;
}

function readMap(zoneId: string): ExpeditionMap {
  return JSON.parse(readFileSync(path.join(process.cwd(), 'public', 'assets', 'maps', `${zoneId}.json`), 'utf8'));
}

describe('first expedition availability and progress', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ quests: [], inventory: [], chat: [] });
    vi.spyOn(services.quests, 'update').mockResolvedValue();
    vi.spyOn(services.inventory, 'update').mockResolvedValue();
    vi.spyOn(services.characters, 'save').mockResolvedValue();
  });

  afterEach(() => vi.restoreAllMocks());

  test.each(['empire', 'dwarf', 'high_elf', 'chaos', 'greenskin', 'dark_elf'] as PlayableRace[])(
    '%s gets one realm-appropriate starter and can navigate to its giver from another zone',
    (race) => {
      const character = makeCharacter({ race, level: 1, zoneId: 'dawnline_expanse' });
      const available = QUESTS.filter((quest) => questAvailableToCharacter(quest, [], character));
      expect(available).toHaveLength(1);
      expect(available[0].realm).toBe(playerRealmForRace(race));
      expect(questsOfferedBy(available[0].giverNpcId, [], character)).toEqual([]);
      expect(questsOfferedBy(available[0].giverNpcId, [], {
        ...character, zoneId: available[0].giverZoneId!,
      })).toEqual(available);
    },
  );

  test('enforces realm, level, prerequisites and current giver zone when accepting', () => {
    const first = QUESTS_BY_ID['dawnline-01-scouting'];
    const captain = QUESTS_BY_ID['dawnline-03-captain'];
    const previous: QuestProgress[] = [{ questId: captain.prereqQuestId!, status: 'completed', counters: {} }];
    expect(questAvailableToCharacter(captain, [], makeCharacter())).toBe(false);
    expect(questAvailableToCharacter(captain, previous, makeCharacter({ level: 1 }))).toBe(false);
    expect(questAvailableToCharacter(captain, previous, makeCharacter())).toBe(true);
    expect(questAvailableToCharacter(first, [], null)).toBe(false);

    useGameStore.getState().setCharacter(makeCharacter({ race: 'greenskin', zoneId: first.giverZoneId }));
    acceptQuest(first.id);
    expect(useGameStore.getState().quests).toEqual([]);
    useGameStore.getState().setCharacter(makeCharacter({ zoneId: 'brightfen_approach' }));
    acceptQuest(first.id);
    expect(useGameStore.getState().quests).toEqual([]);
    useGameStore.getState().setCharacter(makeCharacter({ zoneId: first.giverZoneId }));
    acceptQuest(first.id);
    expect(useGameStore.getState().quests).toEqual([activeQuest(first.id)]);
  });

  test.each(expeditions)('$prefix credits only kills in the expedition zone', ({ race, prefix, field }) => {
    const questId = `${prefix}-01-scouting`;
    useGameStore.getState().setCharacter(makeCharacter({ race, zoneId: field }));
    useGameStore.getState().setQuests([activeQuest(questId, { 'kill-raiders': 3 })]);

    registerEnemyKill('Campaign Raider', 'dawnline_expanse');
    expect(useGameStore.getState().quests[0]).toEqual(activeQuest(questId, { 'kill-raiders': 3 }));
    registerEnemyKill('Campaign Raider');
    expect(useGameStore.getState().quests[0]).toEqual({
      questId, status: 'ready_to_turn_in', counters: { 'kill-raiders': 4 },
    });
  });

  test.each(expeditions)('$prefix requires the actual field captain', ({ race, prefix, field }) => {
    const questId = `${prefix}-03-captain`;
    const captain = QUESTS_BY_ID[questId].objectives[0].killTarget!;
    useGameStore.getState().setCharacter(makeCharacter({ race, zoneId: field }));
    useGameStore.getState().setQuests([activeQuest(questId)]);
    registerEnemyKill('Objective Guard');
    registerEnemyKill('Keep Captain');
    registerEnemyKill(captain, 'dawnline_expanse');
    expect(useGameStore.getState().quests[0]).toEqual(activeQuest(questId));
    registerEnemyKill(captain);
    expect(useGameStore.getState().quests[0].status).toBe('ready_to_turn_in');
  });

  test('does not credit an opposing-realm saved quest', () => {
    const progress = activeQuest('dawnline-01-scouting');
    useGameStore.getState().setCharacter(makeCharacter({ race: 'greenskin', zoneId: 'brightfen_approach' }));
    useGameStore.getState().setQuests([progress]);
    registerEnemyKill('Campaign Raider');
    expect(useGameStore.getState().quests).toEqual([progress]);
  });

  test('filters ready turn-ins by realm when a character is supplied', () => {
    const ready: QuestProgress = {
      questId: 'dawnline-01-scouting', status: 'ready_to_turn_in', counters: { 'kill-raiders': 4 },
    };
    expect(questsReadyToTurnIn('brightfen_approach_dispatch', [ready], makeCharacter())).toHaveLength(1);
    expect(questsReadyToTurnIn('brightfen_approach_dispatch', [ready], makeCharacter({ race: 'greenskin' }))).toEqual([]);
    expect(questsReadyToTurnIn('brightfen_approach_dispatch', [ready], null)).toEqual([]);
    expect(questsReadyToTurnIn('brightfen_approach_dispatch', [ready])).toHaveLength(1);
  });

  test('announces each learned ability once when one reward spans several levels', () => {
    useGameStore.getState().setCharacter(makeCharacter({ level: 1, xp: 650 }));
    checkLevelUp();
    expect(useGameStore.getState().character!.level).toBe(3);
    const learned = useGameStore.getState().chat.filter((message) => message.body.startsWith('New ability:'));
    expect(learned.map((message) => message.body)).toEqual(
      newlyUnlockedAbilities('Battle Prelate', 1, 3).map((ability) =>
        `New ability: ${ability.name}. Your hotbar has been updated.`,
      ),
    );
    checkLevelUp();
    expect(useGameStore.getState().chat.filter((message) => message.body.startsWith('New ability:'))).toEqual(learned);
  });

  test('preserves legacy completion and ready-to-turn-in counters without replaying rewards', () => {
    const completed: QuestProgress = {
      questId: 'dawnline-01-scouting', status: 'completed', counters: { 'kill-raiders': 4 },
    };
    const ready: QuestProgress = {
      questId: 'dawnline-03-captain', status: 'ready_to_turn_in', counters: { 'kill-captain': 1 },
    };
    useGameStore.getState().setCharacter(makeCharacter({ zoneId: 'brightfen_approach' }));
    useGameStore.getState().setQuests([completed, ready]);
    acceptQuest(completed.questId);
    registerEnemyKill('Campaign Raider');
    expect(useGameStore.getState().quests).toEqual([completed, ready]);
    expect(questAvailableToCharacter(QUESTS_BY_ID[completed.questId], [completed], makeCharacter())).toBe(false);
    turnInQuest(ready.questId);
    const gold = useGameStore.getState().character!.gold;
    turnInQuest(ready.questId);
    expect(useGameStore.getState().character!.gold).toBe(gold);
    expect(useGameStore.getState().quests[1]).toEqual({ ...ready, status: 'completed' });
  });

  test.each(expeditions)('$prefix hands off inside the frontier and awards universal gear', ({ race, prefix, field, capital }) => {
    const quest = QUESTS_BY_ID[`${prefix}-04-keep`];
    const ready: QuestProgress = {
      questId: quest.id, status: 'ready_to_turn_in', counters: { 'kill-keep-guards': 1 },
    };
    useGameStore.getState().setCharacter(makeCharacter({ race, zoneId: capital }));
    useGameStore.getState().setQuests([ready]);
    turnInQuest(quest.id);
    expect(useGameStore.getState().quests[0].status).toBe('ready_to_turn_in');
    useGameStore.getState().updateCharacter({ zoneId: field });
    turnInQuest(quest.id);
    expect(useGameStore.getState().quests[0].status).toBe('completed');
    expect(useGameStore.getState().inventory[0]).toMatchObject({ kind: 'armor', equipSlot: 'neck' });
    expect(useGameStore.getState().inventory[0].affix!.strengthBonus).toBeGreaterThanOrEqual(3);
    for (const expeditionQuest of QUESTS.filter((entry) => entry.realm === quest.realm)) {
      for (const reward of expeditionQuest.reward.items ?? []) {
        const item = getItemDefinition(reward.key)!;
        expect(item.consumable || item.equipSlot === 'neck').toBeTruthy();
      }
    }
  });
});

describe('legacy Riftbound expedition migration', () => {
  test('preserves active, ready and completed progress, leaves Aegis saves intact, and is idempotent', () => {
    const saved: QuestProgress[] = [
      { questId: 'dawnline-01-scouting', status: 'completed', counters: { 'kill-raiders': 4 } },
      { questId: 'dawnline-02-guards', status: 'ready_to_turn_in', counters: { 'kill-guards': 2, 'kill-raiders-2': 3 } },
      { questId: 'dawnline-03-captain', status: 'active', counters: { 'kill-captain': 0 } },
      { questId: 'future-quest', status: 'available', counters: {} },
    ];
    const original = structuredClone(saved);
    const migrated = migrateQuestProgressForRealm(saved, 'dark_elf');
    expect(migrated).toEqual(saved.map((progress) => ({
      ...progress, questId: progress.questId.replace(/^dawnline-/, 'cinderfen-'),
    })));
    expect(saved).toEqual(original);
    expect(migrateQuestProgressForRealm(migrated, 'dark_elf')).toEqual(migrated);
    expect(migrateQuestProgressForRealm(saved, 'empire')).toEqual(saved);
  });

  test('merges an existing counterpart by furthest status and maximum counters in either order', () => {
    const saved: QuestProgress[] = [
      { questId: 'dawnline-02-guards', status: 'completed', counters: { 'kill-guards': 2, 'kill-raiders-2': 1 } },
      { questId: 'cinderfen-02-guards', status: 'active', counters: { 'kill-guards': 1, 'kill-raiders-2': 3 } },
    ];
    const expected: QuestProgress[] = [{
      questId: 'cinderfen-02-guards', status: 'completed', counters: { 'kill-guards': 2, 'kill-raiders-2': 3 },
    }];
    expect(migrateQuestProgressForRealm(saved, 'greenskin')).toEqual(expected);
    expect(migrateQuestProgressForRealm([...saved].reverse(), 'greenskin')).toEqual(expected);
    expect(migrateQuestProgressForRealm(expected, 'greenskin')).toEqual(expected);
  });

  test('makes complementary active copies ready to turn in without requiring another kill', () => {
    const saved: QuestProgress[] = [
      { questId: 'dawnline-02-guards', status: 'active', counters: { 'kill-guards': 2, 'kill-raiders-2': 1 } },
      { questId: 'cinderfen-02-guards', status: 'active', counters: { 'kill-guards': 0, 'kill-raiders-2': 3 } },
    ];
    const expected: QuestProgress[] = [{
      questId: 'cinderfen-02-guards', status: 'ready_to_turn_in', counters: { 'kill-guards': 2, 'kill-raiders-2': 3 },
    }];
    expect(migrateQuestProgressForRealm(saved, 'greenskin')).toEqual(expected);
    expect(migrateQuestProgressForRealm([...saved].reverse(), 'greenskin')).toEqual(expected);
    expect(migrateQuestProgressForRealm(expected, 'greenskin')).toEqual(expected);
  });
});

describe('generated first expedition routes', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ quests: [], inventory: [], chat: [] });
    vi.spyOn(services.quests, 'update').mockResolvedValue();
    vi.spyOn(services.inventory, 'update').mockResolvedValue();
    vi.spyOn(services.characters, 'save').mockResolvedValue();
  });

  afterEach(() => vi.restoreAllMocks());

  test.each(expeditions)('$prefix has a direct Tier 1 route and all handoffs and targets exist', ({ prefix, capital, field }) => {
    const capitalMap = readMap(capital);
    const fieldMap = readMap(field);
    expect(capitalMap.zoneTriggers.some((trigger) => trigger.targetZoneId === field)).toBe(true);
    expect(fieldMap.campaign.tier).toBe('T1');
    for (const quest of QUESTS.filter((entry) => entry.id.startsWith(`${prefix}-`))) {
      const giverMap = readMap(quest.giverZoneId!);
      const turninMap = readMap(quest.turninZoneId!);
      expect(giverMap.npcs.some((npc) => npc.id === quest.giverNpcId && npc.role === 'questgiver')).toBe(true);
      expect(turninMap.npcs.some((npc) => npc.id === quest.turninNpcId && npc.role === 'questgiver')).toBe(true);
      for (const objective of quest.objectives) {
        expect(objective.zoneId).toBe(field);
        expect(fieldMap.enemies.some((enemy) => enemy.name === objective.killTarget)).toBe(true);
      }
    }
    const captainName = QUESTS_BY_ID[`${prefix}-03-captain`].objectives[0].killTarget;
    expect(fieldMap.enemies.find((enemy) => enemy.name === captainName)).toMatchObject({
      level: 4,
      archetype: 'captain',
      characterProfileKey: expect.stringMatching(/^enemy_(aegis|riftbound)_keep_captain_captain$/),
    });
  });

  test.each(expeditions)('$prefix reaches its gear reward from level one without additional kills', ({ race, prefix, capital, field }) => {
    const map = readMap(field);
    useGameStore.getState().setCharacter(makeCharacter({ race, zoneId: capital, level: 1, xp: 0 }));
    for (const quest of QUESTS.filter((entry) => entry.id.startsWith(`${prefix}-`))) {
      useGameStore.getState().updateCharacter({ zoneId: quest.giverZoneId });
      acceptQuest(quest.id);
      expect(useGameStore.getState().quests.find((progress) => progress.questId === quest.id)?.status).toBe('active');
      useGameStore.getState().updateCharacter({ zoneId: field });
      for (const objective of quest.objectives) {
        const enemy = map.enemies.find((entry) => entry.name === objective.killTarget)!;
        for (let count = 0; count < objective.required; count++) {
          const character = useGameStore.getState().character!;
          useGameStore.getState().updateCharacter({ xp: character.xp + 20 + enemy.level * 10 });
          registerEnemyKill(enemy.name);
          checkLevelUp();
        }
      }
      expect(useGameStore.getState().quests.find((progress) => progress.questId === quest.id)?.status).toBe('ready_to_turn_in');
      turnInQuest(quest.id);
    }
    expect(useGameStore.getState().quests.every((quest) => quest.status === 'completed')).toBe(true);
    expect(useGameStore.getState().character).toMatchObject({ level: 5, gold: 108 });
    expect(useGameStore.getState().inventory.some((item) => item.equipSlot === 'neck')).toBe(true);
  });
});
