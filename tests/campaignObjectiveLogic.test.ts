import { describe, expect, test } from 'vitest';
import {
  campaignRealmForCharacter,
  canCaptureCampaignObjective,
  captureProgressPct,
  OBJECTIVE_CAPTURE_HOLD_MS,
} from '../src/game/CampaignObjectiveLogic';

describe('campaign objective capture helpers', () => {
  test('derives campaign realm from playable race', () => {
    expect(campaignRealmForCharacter({ race: 'empire' })).toBe('aegis');
    expect(campaignRealmForCharacter({ race: 'dwarf' })).toBe('aegis');
    expect(campaignRealmForCharacter({ race: 'high_elf' })).toBe('aegis');
    expect(campaignRealmForCharacter({ race: 'chaos' })).toBe('riftbound');
    expect(campaignRealmForCharacter({ race: 'greenskin' })).toBe('riftbound');
    expect(campaignRealmForCharacter({ race: 'dark_elf' })).toBe('riftbound');
  });

  test('allows capture only when current control differs from the character realm', () => {
    expect(canCaptureCampaignObjective('riftbound', { race: 'empire' })).toBe(true);
    expect(canCaptureCampaignObjective('contested', { race: 'empire' })).toBe(true);
    expect(canCaptureCampaignObjective('aegis', { race: 'empire' })).toBe(false);
    expect(canCaptureCampaignObjective('riftbound', { race: 'greenskin' })).toBe(false);
    expect(canCaptureCampaignObjective(undefined, null)).toBe(false);
  });

  test('tracks a clamped three-second capture hold', () => {
    expect(captureProgressPct(100, 100)).toBe(0);
    expect(captureProgressPct(100, 100 + OBJECTIVE_CAPTURE_HOLD_MS / 2)).toBe(0.5);
    expect(captureProgressPct(100, 100 + OBJECTIVE_CAPTURE_HOLD_MS * 2)).toBe(1);
  });
});
