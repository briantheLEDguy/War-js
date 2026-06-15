import { QUESTS, QUESTS_BY_ID } from '../../data/quests';
import type { CharacterState, QuestDefinition, QuestProgress, Vec3 } from '../../services/types';
import type { EnemyState } from '../../state/gameStore';
import type { NpcState } from '../../world/NpcSpawner';

export interface DistanceContext {
  label: string;
  distance?: number;
}

export interface ObjectiveTrackerRow {
  id: string;
  description: string;
  current: number;
  required: number;
  complete: boolean;
  context?: DistanceContext;
}

export interface ObjectiveTrackerQuest {
  questId: string;
  title: string;
  status: QuestProgress['status'];
  ready: boolean;
  rows: ObjectiveTrackerRow[];
  turnIn?: DistanceContext;
}

export interface QuestNpcStatus {
  readyCount: number;
  offerCount: number;
}

export function distance2d(a: Pick<Vec3, 'x' | 'z'>, b: Pick<Vec3, 'x' | 'z'>): number {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

export function formatDistance(distance: number | undefined): string {
  if (distance === undefined || !Number.isFinite(distance)) return '';
  if (distance < 10) return `${Math.max(1, Math.round(distance))}m`;
  if (distance < 100) return `${Math.round(distance / 5) * 5}m`;
  return `${Math.round(distance / 10) * 10}m`;
}

export function questNpcStatus(
  npcId: string,
  progresses: QuestProgress[],
  character: CharacterState | null,
): QuestNpcStatus {
  const byId = new Map(progresses.map((progress) => [progress.questId, progress] as const));
  const readyCount = QUESTS.filter((quest) => (quest.turninNpcId ?? quest.giverNpcId) === npcId)
    .filter((quest) => byId.get(quest.id)?.status === 'ready_to_turn_in')
    .length;
  const offerCount = character
    ? QUESTS.filter((quest) => quest.giverNpcId === npcId)
      .filter((quest) => character.level >= quest.minLevel)
      .filter((quest) => {
        if (!quest.prereqQuestId) return true;
        return byId.get(quest.prereqQuestId)?.status === 'completed';
      })
      .filter((quest) => {
        const own = byId.get(quest.id);
        return !own || own.status === 'available';
      })
      .length
    : 0;

  return { readyCount, offerCount };
}

export function resolveTrackedQuests(input: {
  progresses: QuestProgress[];
  npcs: NpcState[];
  enemies: EnemyState[];
  playerPosition?: Pick<Vec3, 'x' | 'z'> | null;
}): ObjectiveTrackerQuest[] {
  const tracked = input.progresses
    .filter((progress) => progress.status === 'active' || progress.status === 'ready_to_turn_in')
    .map((progress) => {
      const definition = QUESTS_BY_ID[progress.questId];
      if (!definition) return null;
      return resolveTrackedQuest(definition, progress, input.npcs, input.enemies, input.playerPosition);
    })
    .filter((quest): quest is ObjectiveTrackerQuest => quest !== null);

  return tracked.sort((a, b) => Number(b.ready) - Number(a.ready));
}

function resolveTrackedQuest(
  definition: QuestDefinition,
  progress: QuestProgress,
  npcs: NpcState[],
  enemies: EnemyState[],
  playerPosition?: Pick<Vec3, 'x' | 'z'> | null,
): ObjectiveTrackerQuest {
  const rows = definition.objectives.map((objective) => {
    const current = progress.counters[objective.id] ?? 0;
    const complete = current >= objective.required;
    return {
      id: objective.id,
      description: objective.description,
      current,
      required: objective.required,
      complete,
      context: complete
        ? undefined
        : objectiveContext(objective.killTarget, objective.talkTarget, npcs, enemies, playerPosition),
    };
  });

  return {
    questId: progress.questId,
    title: definition.title,
    status: progress.status,
    ready: progress.status === 'ready_to_turn_in',
    rows,
    turnIn: progress.status === 'ready_to_turn_in'
      ? npcContext(definition.turninNpcId ?? definition.giverNpcId, npcs, playerPosition)
      : undefined,
  };
}

function objectiveContext(
  killTarget: string | undefined,
  talkTarget: string | undefined,
  npcs: NpcState[],
  enemies: EnemyState[],
  playerPosition?: Pick<Vec3, 'x' | 'z'> | null,
): DistanceContext | undefined {
  if (killTarget) {
    const nearest = nearestEnemyByName(killTarget, enemies, playerPosition);
    if (nearest) {
      return {
        label: nearest.enemy.name,
        distance: nearest.distance,
      };
    }
    return { label: killTarget };
  }

  if (talkTarget) return npcContext(talkTarget, npcs, playerPosition);

  return undefined;
}

function npcContext(
  npcId: string,
  npcs: NpcState[],
  playerPosition?: Pick<Vec3, 'x' | 'z'> | null,
): DistanceContext | undefined {
  const npc = npcs.find((entry) => entry.id === npcId);
  if (!npc) return undefined;
  return {
    label: npc.name,
    distance: playerPosition ? distance2d(playerPosition, npc.position) : undefined,
  };
}

function nearestEnemyByName(
  name: string,
  enemies: EnemyState[],
  playerPosition?: Pick<Vec3, 'x' | 'z'> | null,
): { enemy: EnemyState; distance?: number } | null {
  const matches = enemies.filter((enemy) => enemy.alive && enemy.name === name);
  if (matches.length === 0) return null;
  if (!playerPosition) return { enemy: matches[0] };

  let best: { enemy: EnemyState; distance: number } | null = null;
  for (const enemy of matches) {
    const distance = distance2d(playerPosition, enemy.position);
    if (!best || distance < best.distance) best = { enemy, distance };
  }
  return best;
}
