import { readFileSync } from 'node:fs';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import {
  CAMPAIGN_OBJECTIVES_BY_ZONE,
  buildCampaignSnapshot,
  campaignObjectiveCaptureEligibility,
  campaignZoneInfluence,
  objectiveKey,
  type CampaignObjectiveControlState,
  type CampaignZoneControlState,
} from '../src/data/campaign';
import { describeCampaignActivity } from '../src/game/CampaignObjectiveLogic';
import { CampaignLocal } from '../src/services/local/campaignLocal';
import type { ZoneDefinition } from '../src/world/ZoneLoader';

const CITY = 'aegis_capital';
const COURTYARD = `${CITY}_courtyard`;
const VAULT = `${CITY}_vault`;
const THRONE = `${CITY}_throne_room`;
const STORAGE_KEY = 'war-js:campaign-state:aegis-riftbound-v1';
const SIEGE_CONTROL: CampaignZoneControlState = {
  dawnline_expanse: 'riftbound',
  aegis_crownworks: 'riftbound',
  aegis_gate_fortress: 'riftbound',
};

describe('Crownwatch objective progression', () => {
  let storage: Map<string, string>;

  beforeEach(() => {
    storage = new Map();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  function seed(zoneControl: CampaignZoneControlState, objectiveControl: CampaignObjectiveControlState = {}) {
    storage.set(STORAGE_KEY, JSON.stringify({ version: 3, zoneControl, objectiveControl }));
    return new CampaignLocal();
  }

  test('publishes courtyard, vault, and throne objectives with the same prerequisites in the map and runtime catalog', () => {
    const zone = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8')) as ZoneDefinition;
    const objectives = CAMPAIGN_OBJECTIVES_BY_ZONE[CITY];
    expect(zone.rvrObjectives).toEqual(objectives);
    expect(objectives.map(({ id, requiresObjectiveIds }) => ({ id, requiresObjectiveIds }))).toEqual([
      { id: COURTYARD, requiresObjectiveIds: undefined },
      { id: VAULT, requiresObjectiveIds: [COURTYARD] },
      { id: THRONE, requiresObjectiveIds: [COURTYARD, VAULT] },
    ]);
    expect(objectives.every((objective) => objective.type === 'battle_objective')).toBe(true);
  });

  test.each(Object.keys(SIEGE_CONTROL))('keeps city claims locked while the enemy %s is not controlled', async (missingZone) => {
    const campaign = seed({ ...SIEGE_CONTROL, [missingZone]: 'aegis' });
    const snapshot = await campaign.getSnapshot(CITY);
    expect(snapshot.riftbound.citySiegeReady).toBe(false);
    const courtyard = snapshot.activeZone!.objectives.find(({ id }) => id === COURTYARD)!;
    expect(courtyard.capturableBy).not.toContain('riftbound');
    expect(courtyard.captureBlockers.riftbound).toMatch(/enemy T4 front, inner T4 zone, and fortress/);
    await expect(campaign.claimObjective(CITY, COURTYARD, 'riftbound')).rejects.toThrow(/enemy T4 front/);
  });

  test('rejects out-of-order claims and persists partial progress without awarding the city early', async () => {
    let campaign = seed(SIEGE_CONTROL);
    await expect(campaign.claimObjective(CITY, VAULT, 'riftbound')).rejects.toThrow(/Crownwatch Courtyard/);
    await expect(campaign.claimObjective(CITY, THRONE, 'riftbound')).rejects.toThrow(/Crownwatch Courtyard/);

    const courtyard = await campaign.claimObjective(CITY, COURTYARD, 'riftbound');
    expect(courtyard.zoneControlChanged).toBe(false);
    expect(courtyard.snapshot.zones.find(({ id }) => id === CITY)?.control).toBe('aegis');

    campaign = new CampaignLocal();
    let snapshot = await campaign.getSnapshot(CITY);
    expect(snapshot.activeZone!.objectives.find(({ id }) => id === COURTYARD)?.control).toBe('riftbound');
    expect(snapshot.activeZone!.objectives.find(({ id }) => id === VAULT)?.capturableBy).toContain('riftbound');
    await expect(campaign.claimObjective(CITY, THRONE, 'riftbound')).rejects.toThrow(/Crownwatch Vault/);

    const vault = await campaign.claimObjective(CITY, VAULT, 'riftbound');
    expect(vault.zoneControlChanged).toBe(false);
    const throne = await campaign.claimObjective(CITY, THRONE, 'riftbound');
    expect(throne.zoneControlChanged).toBe(true);
    snapshot = await new CampaignLocal().getSnapshot(CITY);
    expect(snapshot.activeZone!.control).toBe('riftbound');
    expect(snapshot.activeZone!.objectives.every(({ control }) => control === 'riftbound')).toBe(true);
    await expect(campaign.claimObjective(CITY, THRONE, 'riftbound')).rejects.toThrow(/Already controlled/);
  });

  test('exposes the next required objective in the existing capture activity HUD', () => {
    const snapshot = buildCampaignSnapshot(CITY, SIEGE_CONTROL, { [objectiveKey(CITY, COURTYARD)]: 'riftbound' });
    const objective = snapshot.activeZone!.objectives.find(({ id }) => id === THRONE)!;
    expect(describeCampaignActivity({
      zoneId: CITY, objective, realm: 'riftbound', spawns: [], enemies: [],
      player: { x: objective.x, z: objective.z }, inventory: [], nowMs: 1000,
    })).toMatchObject({ activity: 'capture', blocker: 'Control 2 · Crownwatch Vault first' });
  });

  test('requires attackers to retain both earlier objectives and campaign pressure', async () => {
    let campaign = seed(SIEGE_CONTROL, {
      [objectiveKey(CITY, COURTYARD)]: 'aegis',
      [objectiveKey(CITY, VAULT)]: 'riftbound',
    });
    await expect(campaign.claimObjective(CITY, THRONE, 'riftbound')).rejects.toThrow(/Crownwatch Courtyard/);

    campaign = seed({ ...SIEGE_CONTROL, aegis_gate_fortress: 'aegis' }, {
      [objectiveKey(CITY, COURTYARD)]: 'riftbound',
      [objectiveKey(CITY, VAULT)]: 'riftbound',
    });
    await expect(campaign.claimObjective(CITY, THRONE, 'riftbound')).rejects.toThrow(/enemy T4 front/);
    expect((await campaign.getSnapshot(CITY)).activeZone!.objectives.find(({ id }) => id === VAULT)?.control).toBe('riftbound');
  });

  test('allows home defenders to retake the city in order without first conquering the enemy campaign', async () => {
    const campaign = seed({ [CITY]: 'riftbound' }, Object.fromEntries(
      [COURTYARD, VAULT, THRONE].map((id) => [objectiveKey(CITY, id), 'riftbound' as const]),
    ));
    expect((await campaign.getSnapshot(CITY)).aegis.citySiegeReady).toBe(false);
    await expect(campaign.claimObjective(CITY, THRONE, 'aegis')).rejects.toThrow(/Crownwatch Courtyard/);
    await campaign.claimObjective(CITY, COURTYARD, 'aegis');
    await expect(campaign.claimObjective(CITY, THRONE, 'aegis')).rejects.toThrow(/Crownwatch Vault/);
    await campaign.claimObjective(CITY, VAULT, 'aegis');
    const throne = await campaign.claimObjective(CITY, THRONE, 'aegis');
    expect(throne.zoneControlChanged).toBe(true);
    expect(throne.snapshot.zones.find(({ id }) => id === CITY)?.control).toBe('aegis');
  });

  test('preserves independent battlefield objectives and applies the same global siege rule to Riftspire', async () => {
    const campaign = new CampaignLocal();
    const field = 'shatterline_expanse';
    await expect(campaign.claimObjective(field, `${field}_east_objective`, 'aegis')).resolves.toMatchObject({
      objective: { control: 'aegis' },
    });
    await expect(campaign.claimObjective(field, `${field}_riftbound_keep`, 'aegis'))
      .rejects.toThrow(/Control all three battlefield objectives first/);
    const riftspireGate = CAMPAIGN_OBJECTIVES_BY_ZONE.riftspire_capital.find(({ type }) => type === 'city_gate')!;
    await expect(campaign.claimObjective('riftspire_capital', riftspireGate.id, 'aegis'))
      .rejects.toThrow(/enemy T4 front/);
    const readyCampaign = seed({ shatterline_expanse: 'aegis', rift_crownworks: 'aegis', rift_gate_fortress: 'aegis' });
    await expect(readyCampaign.claimObjective('riftspire_capital', riftspireGate.id, 'aegis')).resolves.toMatchObject({
      objective: { control: 'aegis' },
    });
    expect(CAMPAIGN_OBJECTIVES_BY_ZONE.riftspire_capital.every(({ requiresObjectiveIds }) => !requiresObjectiveIds)).toBe(true);
  });

  test('fails closed if a prerequisite is missing from the zone objective list', () => {
    const objective = { ...CAMPAIGN_OBJECTIVES_BY_ZONE[CITY][0], control: 'aegis' as const, requiresObjectiveIds: ['missing_objective'] };
    expect(campaignObjectiveCaptureEligibility([objective], objective, 'riftbound', campaignZoneInfluence(CITY), {
      zoneId: CITY, zoneControl: SIEGE_CONTROL,
    })).toEqual({ capturable: false, reason: 'Control missing_objective first' });
  });
});
