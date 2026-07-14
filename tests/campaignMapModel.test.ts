import { describe, expect, test } from 'vitest';
import { CAMPAIGN_ZONES } from '../src/data/campaign';
import {
  CAMPAIGN_ROUTE_ORDER,
  campaignMapLevelIn,
  campaignMapLevelOut,
  campaignRouteForLane,
  campaignRouteForZone,
  defaultCampaignMapZone,
} from '../src/ui/hud/campaignMapModel';

describe('campaign map route model', () => {
  test('exposes the central and four faction lanes in campaign order', () => {
    expect(CAMPAIGN_ROUTE_ORDER).toEqual([
      'central',
      'aegis_west',
      'aegis_east',
      'riftbound_west',
      'riftbound_east',
    ]);

    expect(campaignRouteForLane('central').mainZoneIds).toEqual([
      'riftspire_capital',
      'rift_gate_fortress',
      'rift_crownworks',
      'shatterline_expanse',
      'dawnline_expanse',
      'aegis_crownworks',
      'aegis_gate_fortress',
      'aegis_capital',
    ]);
  });

  test('builds faction routes from graph edges and preserves boss branches', () => {
    const aegisWest = campaignRouteForLane('aegis_west');
    expect(aegisWest.mainZoneIds).toEqual([
      'aegis_capital',
      'sunmeadow_march',
      'greybrook_crossing',
      'ironwood_redoubt',
      'aegis_crownworks',
    ]);
    expect(aegisWest.branches).toEqual({
      sunmeadow_march: ['wardens_hollow'],
      greybrook_crossing: ['briarwatch_den'],
      ironwood_redoubt: ['stormbarrow_lair'],
    });
    expect(aegisWest.zoneIds).toEqual([
      'aegis_capital',
      'sunmeadow_march',
      'wardens_hollow',
      'greybrook_crossing',
      'briarwatch_den',
      'ironwood_redoubt',
      'stormbarrow_lair',
      'aegis_crownworks',
    ]);

    expect(campaignRouteForZone('gorepine_warrens').lane).toBe('riftbound_east');
    expect(campaignRouteForLane('riftbound_east').branches).toEqual({
      ashen_steppe: ['ashfang_pit'],
      gorepine_pass: ['gorepine_warrens'],
      obsidian_scar: ['obsidian_maw'],
    });
  });

  test('assigns every generated campaign node to an inspectable route', () => {
    const routedZoneIds = new Set(
      CAMPAIGN_ROUTE_ORDER.flatMap((lane) => campaignRouteForLane(lane).zoneIds),
    );

    expect(routedZoneIds).toEqual(new Set(CAMPAIGN_ZONES.map((zone) => zone.id)));
    for (const zone of CAMPAIGN_ZONES) {
      expect(campaignRouteForZone(zone.id).zoneIds).toContain(zone.id);
    }
  });

  test('navigates exactly one tier at a time and defaults invalid zones safely', () => {
    expect(campaignMapLevelIn('campaign', 'aegis_capital')).toBe('route');
    expect(campaignMapLevelIn('route', 'aegis_capital')).toBe('zone');
    expect(campaignMapLevelIn('zone', 'aegis_capital')).toBe('zone');
    expect(campaignMapLevelOut('zone')).toBe('route');
    expect(campaignMapLevelOut('route')).toBe('campaign');
    expect(campaignMapLevelOut('campaign')).toBe('campaign');
    expect(defaultCampaignMapZone('not-a-zone')).toBe('aegis_capital');
    expect(defaultCampaignMapZone('dawnline_expanse')).toBe('dawnline_expanse');
  });
});
