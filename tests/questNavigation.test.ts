import { describe, expect, test } from 'vitest';
import { resolveQuestDestination, resolveQuestNavigation, questRoute } from '../src/ui/hud/questNavigation';
import { buildMarkers, DEFAULT_VISIBLE } from '../src/ui/hud/mapData';
import type { CharacterState, QuestProgress } from '../src/services/types';

const character: CharacterState = {
  id: 'navigation-test', name: 'Recruit', race: 'empire', className: 'Ember Arcanist',
  bodyVariant: 'm', level: 1, xp: 0, zoneId: 'aegis_capital',
  health: 100, maxHealth: 100, mana: 100, maxMana: 100, gold: 0, strength: 10,
  position: { x: 0, y: 0, z: 0 }, rotationY: 0,
};
const active: QuestProgress = {
  questId: 'dawnline-01-scouting', status: 'active', counters: { 'kill-raiders': 0 },
};
const exits = [
  { id: 'fortress', label: 'Starfall Gate', targetZoneId: 'aegis_gate_fortress', position: { x: 0, z: 10 } },
  { id: 'brightfen', label: 'Brightfen Approach', targetZoneId: 'brightfen_approach', position: { x: 30, z: 40 } },
];
const input = { character, progresses: [active], npcs: [], enemies: [], exits, playerPosition: { x: 0, z: 0 } };

describe('expedition navigation', () => {
  test('routes each fresh realm character to its own dispatch officer', () => {
    expect(resolveQuestDestination(character, [])).toMatchObject({ stage: 'offer', npcId: 'quest-1', zoneId: 'aegis_capital' });
    expect(resolveQuestDestination({ ...character, race: 'chaos', zoneId: 'riftspire_capital' }, []))
      .toMatchObject({ stage: 'offer', npcId: 'riftspire_dispatch', zoneId: 'riftspire_capital' });
  });

  test('selects the real T1 exit, even when the fortress exit is nearer', () => {
    expect(resolveQuestNavigation(input)).toMatchObject({
      stage: 'active', zoneId: 'brightfen_approach', exitId: 'brightfen', distance: 50,
      label: 'Take the exit to Brightfen Approach', position: { x: 30, z: 40 },
    });
    expect(questRoute('aegis_capital', 'brightfen_approach')).toEqual(['aegis_capital', 'brightfen_approach']);
    expect(questRoute('riftspire_capital', 'cinderfen_outskirts')).toEqual(['riftspire_capital', 'cinderfen_outskirts']);
  });

  test('does not invent a portal or a distance when the required exit is unavailable', () => {
    const navigation = resolveQuestNavigation({ ...input, exits: [exits[0]] });
    expect(navigation?.position).toBeUndefined();
    expect(navigation?.distance).toBeUndefined();
    expect(questRoute('missing-zone', 'brightfen_approach')).toEqual([]);
  });

  test('switches from travel to nearest living target inside the objective zone', () => {
    const enemy = { id: 'raider', name: 'Campaign Raider', level: 3, health: 100, maxHealth: 100, alive: true, position: { x: 6, y: 0, z: 8 } };
    expect(resolveQuestNavigation({
      ...input, character: { ...character, zoneId: 'brightfen_approach' },
      enemies: [{ ...enemy, id: 'dead', alive: false, position: { x: 0, y: 0, z: 0 } }, enemy],
    })).toMatchObject({ distance: 10, position: enemy.position });
  });

  test('routes a ready quest to its field officer, then selects the next local offer', () => {
    const ready = { ...active, status: 'ready_to_turn_in' as const, counters: { 'kill-raiders': 4 } };
    expect(resolveQuestDestination(character, [ready]))
      .toMatchObject({ stage: 'turnin', zoneId: 'brightfen_approach', npcId: 'brightfen_approach_dispatch' });
    expect(resolveQuestDestination(character, [{ ...ready, status: 'completed' }]))
      .toMatchObject({ stage: 'offer', zoneId: 'brightfen_approach', npcId: 'brightfen_approach_dispatch', quest: { id: 'dawnline-02-guards' } });
  });

  test('map and HUD resolve the same focused destination while respecting quest filters', () => {
    const markerInput = {
      ...input, quests: input.progresses, craftingStations: [], resourceNodes: [], visible: DEFAULT_VISIBLE,
    };
    const focused = buildMarkers(markerInput).filter((marker) => marker.focused);
    expect(focused).toHaveLength(1);
    expect(focused[0]).toMatchObject({ kind: 'quests', position: resolveQuestNavigation(input)?.position, edgeLabel: '50m' });
    expect(buildMarkers({ ...markerInput, visible: { ...DEFAULT_VISIBLE, quests: false } }).some((marker) => marker.focused)).toBe(false);
  });

  test('no character or completed expedition has no stale focus', () => {
    expect(resolveQuestDestination(null, [active])).toBeNull();
    const completed = ['scouting', 'guards', 'captain', 'keep'].map((suffix, index) => ({
      questId: `dawnline-0${index + 1}-${suffix}`, status: 'completed' as const, counters: {},
    }));
    expect(resolveQuestDestination({ ...character, level: 8 }, completed)).toBeNull();
  });

  test('an incompatible legacy quest cannot hide the character’s own expedition', () => {
    const riftbound = { ...character, race: 'greenskin' as const, zoneId: 'riftspire_capital' };
    for (const status of ['active', 'ready_to_turn_in'] as const) {
      expect(resolveQuestDestination(riftbound, [{ ...active, status }]))
        .toMatchObject({ stage: 'offer', npcId: 'riftspire_dispatch' });
    }
  });
});
