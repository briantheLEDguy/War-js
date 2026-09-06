import { CAMPAIGN_GRAPH_EDGES, campaignZoneName } from '../../data/campaign';
import { playerRealmForRace } from '../../data/careers';
import { QUESTS, QUESTS_BY_ID, questAvailableToCharacter } from '../../data/quests';
import type { CharacterState, QuestDefinition, QuestProgress } from '../../services/types';
import type { EnemyState } from '../../state/gameStore';
import type { NpcState } from '../../world/NpcSpawner';
import type { ZoneExitMarker } from './mapData';

export interface QuestDestination {
  quest: QuestDefinition;
  stage: 'offer' | 'active' | 'turnin';
  zoneId: string;
  npcId?: string;
  enemyName?: string;
  action: string;
}

export interface QuestNavigation extends QuestDestination {
  label: string;
  position?: { x: number; z: number };
  distance?: number;
  exitId?: string;
}

/** All quest surfaces use the same focus: ready reward, active work, then next offer. */
export function resolveQuestDestination(
  character: CharacterState | null,
  progresses: QuestProgress[],
): QuestDestination | null {
  if (!character) return null;
  const tracked = progresses
    .filter((entry) => entry.status === 'active' || entry.status === 'ready_to_turn_in')
    .filter((entry) => {
      const quest = QUESTS_BY_ID[entry.questId];
      return quest && (!quest.realm || quest.realm === playerRealmForRace(character.race));
    })
    .sort((a, b) => Number(b.status === 'ready_to_turn_in') - Number(a.status === 'ready_to_turn_in'))[0];
  const quest = tracked
    ? QUESTS_BY_ID[tracked.questId]
    : QUESTS.find((entry) => questAvailableToCharacter(entry, progresses, character));
  if (!quest) return null;

  if (!tracked || tracked.status === 'ready_to_turn_in') {
    const turnin = tracked?.status === 'ready_to_turn_in';
    return {
      quest,
      stage: turnin ? 'turnin' : 'offer',
      zoneId: (turnin ? quest.turninZoneId ?? quest.giverZoneId : quest.giverZoneId) ?? character.zoneId,
      npcId: turnin ? quest.turninNpcId ?? quest.giverNpcId : quest.giverNpcId,
      action: turnin ? 'Collect your reward' : 'Meet your dispatch officer',
    };
  }

  const objective = quest.objectives.find((entry) => (tracked.counters[entry.id] ?? 0) < entry.required);
  if (!objective) return null;
  return {
    quest,
    stage: 'active',
    zoneId: objective.zoneId ?? character.zoneId,
    npcId: objective.talkTarget,
    enemyName: objective.killTarget,
    action: objective.description,
  };
}

/** Follow actual bidirectional campaign links; never invent a portal for an unknown zone. */
export function questRoute(from: string, to: string): string[] {
  if (from === to) return [from];
  const queue: string[][] = [[from]];
  const visited = new Set([from]);
  for (let index = 0; index < queue.length; index++) {
    const path = queue[index];
    for (const edge of CAMPAIGN_GRAPH_EDGES) {
      if (edge.fromZoneId !== path[path.length - 1] || visited.has(edge.toZoneId)) continue;
      const next = [...path, edge.toZoneId];
      if (edge.toZoneId === to) return next;
      visited.add(edge.toZoneId);
      queue.push(next);
    }
  }
  return [];
}

export function resolveQuestNavigation(input: {
  character: CharacterState | null;
  progresses: QuestProgress[];
  npcs: NpcState[];
  enemies: EnemyState[];
  exits: ZoneExitMarker[];
  playerPosition: { x: number; z: number };
}): QuestNavigation | null {
  const destination = resolveQuestDestination(input.character, input.progresses);
  if (!destination || !input.character) return null;
  const distance = (position: { x: number; z: number }) => Math.hypot(
    position.x - input.playerPosition.x, position.z - input.playerPosition.z,
  );
  if (input.character.zoneId !== destination.zoneId) {
    const nextZoneId = questRoute(input.character.zoneId, destination.zoneId)[1];
    const exit = input.exits.find((entry) => entry.targetZoneId === nextZoneId);
    return {
      ...destination,
      label: exit ? `Take the exit to ${campaignZoneName(exit.targetZoneId)}` : `Travel to ${campaignZoneName(destination.zoneId)}`,
      position: exit?.position,
      distance: exit ? distance(exit.position) : undefined,
      exitId: exit?.id,
    };
  }
  const npc = input.npcs.find((entry) => entry.id === destination.npcId);
  const enemy = input.enemies
    .filter((entry) => entry.alive && entry.name === destination.enemyName)
    .sort((a, b) => distance(a.position) - distance(b.position))[0];
  const target = npc ?? enemy;
  return {
    ...destination,
    label: npc ? `Speak to ${npc.name}` : destination.action,
    position: target?.position,
    distance: target ? distance(target.position) : undefined,
  };
}
