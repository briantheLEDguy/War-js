import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import { acceptQuest, registerEnemyKill, turnInQuest } from '../src/game/QuestLogic';
import { QUESTS } from '../src/data/quests';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, resetGameStore } from './testUtils';
import { repoRoot } from '../scripts/unreal/toolchain';

const fixturePath = path.join(repoRoot, 'migration/fixtures/quests.json');
function capture() {
  const random = vi.spyOn(Math, 'random').mockReturnValue(0.5);
  try {
    const cases = (['aegis', 'riftbound'] as const).map(realm => {
      resetGameStore();
      const chain = QUESTS.filter(quest => quest.realm === realm);
      useGameStore.setState({ character: makeCharacter({ race: realm === 'aegis' ? 'empire' : 'chaos',
        level: 1, xp: 0, gold: 0, strength: 10, health: 100, maxHealth: 100, mana: 100, maxMana: 100,
        zoneId: chain[0].giverZoneId! }), quests: [], inventory: [], chat: [] });
      const steps: unknown[] = [];
      const snapshot = (action: string) => {
        const state = useGameStore.getState();
        const c = state.character!;
        steps.push(JSON.parse(JSON.stringify({ action, quests: state.quests,
          inventory: state.inventory.map(({ key, qty, slot, kind, equipSlot, affix }) => ({ key, qty, slot, kind, equipSlot, affix })),
          character: { level: c.level, xp: c.xp, gold: c.gold, strength: c.strength,
            maxHealth: c.maxHealth, maxMana: c.maxMana } })));
      };
      acceptQuest(QUESTS.find(quest => quest.realm !== realm)!.id);
      snapshot('reject_other_realm');
      acceptQuest(chain[1].id);
      snapshot('reject_missing_prerequisite');
      for (const quest of chain) {
        useGameStore.getState().updateCharacter({ zoneId: 'zone1' });
        acceptQuest(quest.id); snapshot(`${quest.id}:reject_wrong_giver_zone`);
        useGameStore.getState().updateCharacter({ zoneId: quest.giverZoneId! });
        acceptQuest(quest.id); snapshot(`${quest.id}:accept`);
        acceptQuest(quest.id); snapshot(`${quest.id}:duplicate_accept`);
        registerEnemyKill(quest.objectives[0].killTarget!, 'zone1');
        snapshot(`${quest.id}:reject_wrong_kill_zone`);
        for (const objective of quest.objectives) {
          for (let i = 0; i < objective.required + 1; i++) registerEnemyKill(objective.killTarget!, objective.zoneId);
        }
        snapshot(`${quest.id}:kills_complete_and_clamped`);
        useGameStore.getState().updateCharacter({ zoneId: 'zone1' });
        turnInQuest(quest.id); snapshot(`${quest.id}:reject_wrong_turnin_zone`);
        useGameStore.getState().updateCharacter({ zoneId: quest.turninZoneId! });
        const inventory = useGameStore.getState().inventory;
        useGameStore.setState({ inventory: Array.from({ length: 24 }, (_, slot) => ({
          key: 'jewel_amulet_bloodglass', name: 'Occupied', qty: 1, kind: 'armor' as const, equipSlot: 'neck' as const, slot })) });
        turnInQuest(quest.id); snapshot(`${quest.id}:reject_full_bag`);
        useGameStore.setState({ inventory });
        turnInQuest(quest.id); snapshot(`${quest.id}:complete`);
        turnInQuest(quest.id); snapshot(`${quest.id}:duplicate_turnin`);
      }
      return { realm, steps };
    });
    return { schemaVersion: 1, randomUnit: 0.5, sources: ['src/game/QuestLogic.ts', 'src/data/quests.ts'].map(source => ({
      source, sha256: createHash('sha256').update(readFileSync(path.join(repoRoot, source), 'utf8').replace(/\r\n/g, '\n')).digest('hex') })), cases };
  } finally { random.mockRestore(); resetGameStore(); useGameStore.setState({ quests: [], inventory: [], chat: [] }); }
}

describe('browser expedition quest fixtures', () => {
  it('records both complete chains, rejection paths and reward retry behavior', () => {
    const actual = capture();
    if (process.env.WAR_UPDATE_QUEST_FIXTURES === '1') writeFileSync(fixturePath, JSON.stringify(actual, null, 2) + '\n');
    expect(JSON.parse(readFileSync(fixturePath, 'utf8'))).toEqual(actual);
    for (const entry of actual.cases) {
      const last = entry.steps.at(-1) as { quests: { status: string }[]; character: { gold: number } };
      expect(last.quests).toHaveLength(4);
      expect(last.quests.every(quest => quest.status === 'completed')).toBe(true);
      expect(last.character.gold).toBe(108);
    }
  });
});
