import type { CampaignObjectiveStatus, CampaignRealm } from '../data/campaign';
import type { EnemyState } from '../state/gameStore';
import type { EnemySpawn } from '../world/ZoneLoader';

export const KEEP_ENCOUNTER_RADIUS = 45;

export function keepApproachDefenders(objective: CampaignObjectiveStatus, spawns: readonly EnemySpawn[]): EnemySpawn[] {
  return spawns.filter((spawn) => !spawn.encounter && (spawn.aggroRange ?? 0) > 0 &&
    Math.hypot(spawn.x - objective.x, spawn.z - objective.z) <= objective.captureRadius + 8);
}

export type KeepEncounterDecision = 'locked' | 'reset' | 'approach' | 'summon' | 'fight' | 'defeated' | 'secured';

/** A commander is one staged encounter, independent of the optional field-captain quest. */
export function decideKeepEncounter({ objective, realm, commander, defenders, player, playerDead }: {
  objective: CampaignObjectiveStatus;
  realm: CampaignRealm;
  commander: EnemyState;
  defenders: readonly EnemyState[];
  player: { x: number; z: number };
  playerDead: boolean;
}): KeepEncounterDecision {
  if (objective.control === realm) return 'secured';
  const underway = Boolean(commander.keepEncounter && commander.keepEncounter.phase !== 'locked');
  const inArea = Math.hypot(player.x - objective.x, player.z - objective.z) <= KEEP_ENCOUNTER_RADIUS;
  if (!objective.capturableBy.includes(realm)) return underway ? 'reset' : 'locked';
  if (playerDead || !inArea) return underway ? 'reset' : 'approach';
  if (commander.keepEncounter?.phase === 'defeated') return 'defeated';
  if (commander.alive) return 'fight';
  if (defenders.some((enemy) => enemy.alive)) return 'approach';
  return 'summon';
}
