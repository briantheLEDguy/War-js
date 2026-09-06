import { playerRealmForRace } from '../data/careers';
import {
  campaignKeepCaptureReward,
  campaignObjectiveDefenseEligibility,
  isRvrKeepZone,
  type CampaignClaimResult, type CampaignControl, type CampaignObjectiveStatus, type CampaignRealm,
} from '../data/campaign';
import { services } from '../services';
import type { CharacterState, InventoryItem } from '../services/types';
import type { EnemyState } from '../state/gameStore';
import type { EnemySpawn } from '../world/ZoneLoader';
import { campaignRewardInventoryBlocker } from './CampaignRewards';

export const OBJECTIVE_CAPTURE_HOLD_MS = 3000;
export const OBJECTIVE_DEFENSE_HOLD_MS = 8000;

export interface CampaignActivity {
  objective: CampaignObjectiveStatus;
  activity: 'capture' | 'defend';
  distance: number;
  defenders: number;
  blocker: string | null;
  holdMs: number;
  commander?: { name: string; phase: NonNullable<EnemyState['keepEncounter']>['phase']; health: number; maxHealth: number };
}

/** Spawn-bound defenders still contest an objective when pulled outside its ring. */
export function objectiveDefenders(
  objective: Pick<CampaignObjectiveStatus, 'x' | 'z' | 'captureRadius'> & Partial<Pick<CampaignObjectiveStatus, 'id'>>,
  spawns: readonly EnemySpawn[],
  enemies: readonly EnemyState[],
): EnemyState[] {
  const radius = objective.captureRadius + 8;
  return enemies.filter((enemy) => {
    if (!enemy.alive) return false;
    const spawn = spawns.find((entry) => entry.id === enemy.id);
    if (!spawn || !(spawn.aggroRange && spawn.aggroRange > 0)) return false;
    return Boolean(spawn.encounter && spawn.encounter.objectiveId === objective.id) ||
      Math.hypot(spawn.x - objective.x, spawn.z - objective.z) <= radius ||
      Math.hypot(enemy.position.x - objective.x, enemy.position.z - objective.z) <= objective.captureRadius;
  });
}

export function describeCampaignActivity({ zoneId, objective, realm, spawns, enemies, player, inventory, nowMs = Date.now() }: {
  zoneId: string;
  objective: CampaignObjectiveStatus;
  realm: CampaignRealm;
  spawns: readonly EnemySpawn[];
  enemies: readonly EnemyState[];
  player: { x: number; z: number };
  inventory: InventoryItem[];
  nowMs?: number;
}): CampaignActivity {
  const activity = objective.control === realm ? 'defend' : 'capture';
  const eligibility = activity === 'defend'
    ? campaignObjectiveDefenseEligibility(zoneId, objective, realm, nowMs)
    : null;
  let blocker = eligibility
    ? eligibility.defendable ? null : eligibility.reason ?? 'Defense unavailable'
    : objective.capturableBy.includes(realm) ? null : objective.captureBlockers[realm] ?? 'Capture unavailable';
  const defenders = objectiveDefenders(objective, spawns, enemies).length;
  const commanderSpawn = spawns.find((spawn) => spawn.encounter?.objectiveId === objective.id);
  const commanderState = commanderSpawn ? enemies.find((enemy) => enemy.id === commanderSpawn.id) : undefined;
  const commander = commanderState && commanderSpawn ? { name: commanderSpawn.name,
    phase: commanderState.keepEncounter?.phase ?? 'locked', health: commanderState.health, maxHealth: commanderState.maxHealth } : undefined;
  if (!blocker && defenders > 0) blocker = `Defeat ${defenders} remaining defender${defenders === 1 ? '' : 's'}`;
  if (activity === 'capture' && objective.capturableBy.includes(realm) && commander && commander.phase !== 'defeated') {
    const approachRemaining = defenders - (commanderState?.alive ? 1 : 0);
    if (approachRemaining <= 0) blocker = `Defeat ${commander.name}`;
  }
  if (!blocker && activity === 'capture' && objective.type === 'keep' && isRvrKeepZone(zoneId)) {
    blocker = campaignRewardInventoryBlocker(campaignKeepCaptureReward(zoneId), inventory);
  }
  return {
    objective, activity, defenders, blocker, commander,
    distance: Math.hypot(player.x - objective.x, player.z - objective.z),
    holdMs: activity === 'defend' ? OBJECTIVE_DEFENSE_HOLD_MS : OBJECTIVE_CAPTURE_HOLD_MS,
  };
}

export function campaignActivityProgress(startedAtMs: number, nowMs: number, holdMs: number): number {
  return Math.max(0, Math.min(1, (nowMs - startedAtMs) / holdMs));
}

export function campaignRealmForCharacter(character: Pick<CharacterState, 'race'>): CampaignRealm {
  return playerRealmForRace(character.race);
}

export function canCaptureCampaignObjective(
  currentControl: CampaignControl | undefined,
  character: Pick<CharacterState, 'race'> | null | undefined,
): boolean {
  if (!character) return false;
  return currentControl !== campaignRealmForCharacter(character);
}

export function captureProgressPct(startedAtMs: number, nowMs: number): number {
  return campaignActivityProgress(startedAtMs, nowMs, OBJECTIVE_CAPTURE_HOLD_MS);
}

export async function claimObjectiveForCharacter(
  zoneId: string,
  objectiveId: string,
  character: Pick<CharacterState, 'race'>,
  activity: 'capture' | 'defend' = 'capture',
): Promise<CampaignClaimResult> {
  return activity === 'defend'
    ? services.campaign.defendObjective(zoneId, objectiveId, campaignRealmForCharacter(character))
    : services.campaign.claimObjective(zoneId, objectiveId, campaignRealmForCharacter(character));
}
