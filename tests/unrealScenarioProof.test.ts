import { expect, test } from 'vitest';
import { verifyScenarioReconnectBots } from '../scripts/unreal/scenario-proof-evidence';

const log = (capacity: number, realm = 1) => [
  `WAR_SCENARIO_TEAM realm=${realm} humans=1 bots=${capacity - 1}`,
  `WAR_SCENARIO_TEAM realm=${realm} humans=0 bots=${capacity}`,
  `WAR_SCENARIO_TEAM realm=${realm} humans=1 bots=${capacity - 1}`,
].join('\n');

test('reconnect evidence uses current 18v18 or historical 6v6 recorded capacity', () => {
  expect(() => verifyScenarioReconnectBots(log(18), 'aegis', 18)).not.toThrow();
  expect(() => verifyScenarioReconnectBots(log(6, 2), 'riftbound', 6)).not.toThrow();
  expect(() => verifyScenarioReconnectBots(log(6), 'aegis', 18)).toThrow(/substitution/);
  expect(() => verifyScenarioReconnectBots(log(18), 'riftbound', 18)).toThrow(/substitution/);
});

test('initial fill and missing return cannot stand in for a reconnect reservation', () => {
  expect(() => verifyScenarioReconnectBots(log(18).split('\n').slice(0, 2).join('\n'), 'aegis', 18))
    .toThrow(/substitution/);
  expect(() => verifyScenarioReconnectBots(log(18).replace('bots=18', 'bots=180'), 'aegis', 18))
    .toThrow(/substitution/);
  expect(() => verifyScenarioReconnectBots(log(18), 'aegis', 12)).toThrow(/recorded/);
});
