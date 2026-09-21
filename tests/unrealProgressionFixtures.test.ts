import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { checkLevelUp } from '../src/game/QuestLogic';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, resetGameStore } from './testUtils';
import { repoRoot } from '../scripts/unreal/toolchain';

const source = 'src/game/QuestLogic.ts';
const fixturePath = path.join(repoRoot, 'migration/fixtures/progression.json');
function capture() {
  const cases = [0, 249, 250, 649, 650, 1199, 1200, 4900, 5000].map(xpReward => {
    resetGameStore();
    const input = { level: 1, xp: 0, gold: 7, health: 32, maxHealth: 100, mana: 15, maxMana: 100, strength: 10 };
    const goldReward = 25;
    useGameStore.setState({ character: makeCharacter({ ...input, xp: xpReward, gold: input.gold + goldReward }), chat: [] });
    checkLevelUp();
    const current = useGameStore.getState().character!;
    const expected = Object.fromEntries(Object.keys(input).map(key => [key, current[key as keyof typeof input]]));
    return { name: `reward_${xpReward}`, input, xpReward, goldReward, expected };
  });
  resetGameStore();
  return { schemaVersion: 1, source, sourceSha256: createHash('sha256')
    .update(readFileSync(path.join(repoRoot, source), 'utf8').replace(/\r\n/g, '\n')).digest('hex'), cases };
}

describe('browser progression reference fixtures', () => {
  it('retains exact threshold, multi-level, growth and pool restoration behavior', () => {
    const actual = capture();
    if (process.env.WAR_UPDATE_PROGRESSION_FIXTURES === '1') writeFileSync(fixturePath, JSON.stringify(actual, null, 2) + '\n');
    expect(JSON.parse(readFileSync(fixturePath, 'utf8'))).toEqual(actual);
    expect(actual.cases.find(entry => entry.xpReward === 650)?.expected).toMatchObject({ level: 3, xp: 0, health: 140, mana: 120, strength: 14 });
    expect(actual.cases.find(entry => entry.xpReward === 249)?.expected).toMatchObject({ level: 1, xp: 249, health: 32, mana: 15 });
  });
});
