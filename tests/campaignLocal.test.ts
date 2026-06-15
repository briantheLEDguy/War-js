import { describe, expect, test } from 'vitest';
import {
  CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE,
  CAMPAIGN_BATTLEFIELD_SWEEP_INFLUENCE,
  CAMPAIGN_KEEP_SIEGE_INFLUENCE_REQUIRED,
  CAMPAIGN_OBJECTIVE_CAPTURE_XP,
} from '../src/data/campaign';
import { CampaignLocal } from '../src/services/local/campaignLocal';

describe('local campaign influence and keep capture', () => {
  test('builds influence from BO captures and gates enemy keeps until unlocked', async () => {
    const campaign = new CampaignLocal();
    await campaign.resetCampaign();

    const zoneId = 'shatterline_expanse';
    await expect(
      campaign.claimObjective(zoneId, `${zoneId}_riftbound_keep`, 'aegis'),
    ).rejects.toThrow(/Control all three battlefield objectives first/);

    const west = await campaign.claimObjective(zoneId, `${zoneId}_west_objective`, 'aegis');
    expect(west.reward).toEqual({
      xp: CAMPAIGN_OBJECTIVE_CAPTURE_XP,
      influence: CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE,
    });

    await campaign.claimObjective(zoneId, `${zoneId}_central_objective`, 'aegis');
    await expect(
      campaign.claimObjective(zoneId, `${zoneId}_riftbound_keep`, 'aegis'),
    ).rejects.toThrow(/Control all three battlefield objectives first/);

    const east = await campaign.claimObjective(zoneId, `${zoneId}_east_objective`, 'aegis');
    expect(east.reward).toEqual({
      xp: CAMPAIGN_OBJECTIVE_CAPTURE_XP,
      influence: CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE + CAMPAIGN_BATTLEFIELD_SWEEP_INFLUENCE,
    });

    const unlockedZone = east.snapshot.zones.find((zone) => zone.id === zoneId);
    expect(unlockedZone?.influence.aegis).toBe(CAMPAIGN_KEEP_SIEGE_INFLUENCE_REQUIRED);
    expect(
      unlockedZone?.objectives.find((objective) => objective.id === `${zoneId}_riftbound_keep`)?.capturableBy,
    ).toContain('aegis');

    const keep = await campaign.claimObjective(zoneId, `${zoneId}_riftbound_keep`, 'aegis');
    const capturedZone = keep.snapshot.zones.find((zone) => zone.id === zoneId);
    expect(keep.zoneControlChanged).toBe(true);
    expect(capturedZone?.control).toBe('aegis');
  });
});
