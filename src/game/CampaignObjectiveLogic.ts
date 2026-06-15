import { playerRealmForRace } from '../data/careers';
import type { CampaignClaimResult, CampaignControl, CampaignRealm } from '../data/campaign';
import { services } from '../services';
import type { CharacterState } from '../services/types';

export const OBJECTIVE_CAPTURE_HOLD_MS = 3000;

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
  return Math.max(0, Math.min(1, (nowMs - startedAtMs) / OBJECTIVE_CAPTURE_HOLD_MS));
}

export async function claimObjectiveForCharacter(
  zoneId: string,
  objectiveId: string,
  character: Pick<CharacterState, 'race'>,
): Promise<CampaignClaimResult> {
  return services.campaign.claimObjective(zoneId, objectiveId, campaignRealmForCharacter(character));
}
