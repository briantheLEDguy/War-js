import { readFileSync } from 'node:fs';
import { expect, test } from 'vitest';
import { campaignGateBindings, campaignGateVisible, sceneryDistanceLod } from '../src/game/network/CampaignSceneryPresentation';
import { frontierPropDistances } from '../src/world/FrontierProps';
import { createCampaign } from '../src/shared/orvr/simulation';
import type { OrvrZoneLayout } from '../src/world/orvrTypes';

test('actual map gate prop IDs follow the matching authoritative keep stage through breach and repair', () => {
  const map = JSON.parse(readFileSync(`${process.cwd()}/public/assets/maps/sunmeadow_march.json`, 'utf8')) as { orvrLayout: OrvrZoneLayout };
  const bindings = campaignGateBindings(map.orvrLayout);
  expect(bindings.size).toBe(4);
  const campaign = createCampaign();
  const zone = campaign.zones.sunmeadow_march;
  for (const keep of map.orvrLayout.keeps) for (const gate of keep.gates) {
    const binding = bindings.get(gate.propId)!;
    expect(binding).toEqual({ keepId: keep.objectiveId, stage: gate.stage });
    expect(campaignGateVisible(binding, zone.keeps)).toBe(true);
    zone.keeps[keep.objectiveId].gates[gate.stage].health = 0;
    expect(campaignGateVisible(binding, zone.keeps)).toBe(false);
    zone.keeps[keep.objectiveId].gates[gate.stage].health = 1;
    expect(campaignGateVisible(binding, zone.keeps)).toBe(true);
  }
  expect(campaignGateVisible({ keepId: 'unknown', stage: 'outer' }, zone.keeps)).toBe(false);
});

test('nature uses tighter LOD and visibility budgets than large keep architecture', () => {
  const tree = frontierPropDistances('frontier_sunmeadow_oak_pasture');
  const meadow = frontierPropDistances('frontier_sunmeadow_meadow');
  expect([0, 35, 95].map(distance => sceneryDistanceLod(distance, 3, tree.lod))).toEqual([0, 1, 2]);
  expect(sceneryDistanceLod(500, 1, tree.lod)).toBe(0);
  expect(tree.cull).toBe(600); expect(meadow.cull).toBe(80); expect(meadow.lod).toEqual([0, 12, 30]);
  expect(frontierPropDistances('frontier_sunmeadow_hawthorn').lod).toEqual([0, 18, 55]);
  expect(frontierPropDistances('frontier_sunmeadow_keep_gatehouse').lod).toEqual([0, 90, 240]);
});
