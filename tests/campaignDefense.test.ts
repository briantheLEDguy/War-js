import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import {
  CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS,
  campaignKeepCaptureReward,
  campaignObjectiveDefenseEligibility,
  type CampaignRealm,
  type CampaignSnapshot,
} from '../src/data/campaign';
import { getItemDefinition } from '../src/data/items';
import { CampaignLocal } from '../src/services/local/campaignLocal';
import { CampaignSupabase } from '../src/services/supabase/campaignSupabase';

const NOW = 1_800_000_000_000;
const STORAGE_KEY = 'war-js:campaign-state:aegis-riftbound-v1';
const HOME_ZONE = 'brightfen_approach';
const WEST = `${HOME_ZONE}_west_objective`;

describe('friendly campaign objective defense', () => {
  let storage: Map<string, string>;

  beforeEach(() => {
    storage = new Map();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
    });
    vi.spyOn(Date, 'now').mockReturnValue(NOW);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test.each([
    { zoneId: HOME_ZONE, realm: 'aegis' as const, enemy: 'riftbound' },
    { zoneId: 'cinderfen_outskirts', realm: 'riftbound' as const, enemy: 'aegis' },
  ])('$realm can defend three home standards and earn a rewarded keep victory', async ({ zoneId, realm, enemy }) => {
    const campaign = new CampaignLocal();
    const keepId = `${zoneId}_${enemy}_keep`;
    await expect(campaign.claimObjective(zoneId, keepId, realm)).rejects.toThrow(/Build 100 realm influence first/);
    await expect(campaign.claimObjective(zoneId, `${zoneId}_west_objective`, realm)).rejects.toThrow(/Already controlled/);

    for (const direction of ['west', 'central', 'east']) {
      const defense = await campaign.defendObjective(zoneId, `${zoneId}_${direction}_objective`, realm);
      expect(defense.activity).toBe('defend');
      expect(defense.reward).toEqual({ xp: 50, influence: 35 });
      expect(defense.zoneControlChanged).toBe(false);
      expect(defense.objective.control).toBe(realm);
      expect(defense.objective.defenseReadyAt[realm]).toBe(NOW + 180_000);
    }

    const snapshot = await campaign.getSnapshot(zoneId);
    expect(snapshot.activeZone?.influence[realm]).toBe(105);
    expect(snapshot.activeZone?.objectives.find((objective) => objective.id === keepId)?.capturableBy).toContain(realm);
    const keep = await campaign.claimObjective(zoneId, keepId, realm);
    expect(keep.activity).toBe('capture');
    expect(keep.reward).toMatchObject({ xp: 300, influence: 0, gold: 30 });
    expect(keep.reward.items).toEqual([{
      key: 'jewel_amulet_bloodglass',
      name: expect.stringContaining("Victor's Amulet"),
      qty: 1,
      kind: 'armor',
      equipSlot: 'neck',
      strengthRoll: { min: 8, max: 10 },
    }]);
    expect(getItemDefinition(keep.reward.items![0].key)?.equipSlot).toBe('neck');
    await expect(campaign.claimObjective(zoneId, keepId, realm)).rejects.toThrow(/Already controlled/);
  });

  test('persists a realm cooldown through reload and allows defense exactly at expiry', async () => {
    const campaign = new CampaignLocal();
    const defense = await campaign.defendObjective(HOME_ZONE, WEST, 'aegis');
    await expect(campaign.defendObjective(HOME_ZONE, WEST, 'aegis')).rejects.toThrow(/Defense ready in 180 seconds/);
    const reloaded = new CampaignLocal();
    const snapshot = await reloaded.getSnapshot(HOME_ZONE);
    expect(snapshot.activeZone?.objectives.find((objective) => objective.id === WEST)?.defenseReadyAt)
      .toEqual({ aegis: NOW + CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS });
    expect(snapshot.activeZone?.influence.aegis).toBe(35);

    // A caller cannot alter the service cooldown by mutating a returned snapshot.
    defense.objective.defenseReadyAt.aegis = 0;
    await expect(campaign.defendObjective(HOME_ZONE, WEST, 'aegis')).rejects.toThrow(/Defense ready/);
    vi.mocked(Date.now).mockReturnValue(NOW + CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS - 1);
    await expect(reloaded.defendObjective(HOME_ZONE, WEST, 'aegis')).rejects.toThrow(/Defense ready in 1 second/);
    vi.mocked(Date.now).mockReturnValue(NOW + CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS);
    const repeat = await reloaded.defendObjective(HOME_ZONE, WEST, 'aegis');
    expect(repeat.snapshot.zones.find((zone) => zone.id === HOME_ZONE)?.influence.aegis).toBe(70);
  });

  test('keeps cooldowns per realm when a standard changes hands', async () => {
    const campaign = new CampaignLocal();
    await campaign.defendObjective(HOME_ZONE, WEST, 'aegis');
    await campaign.claimObjective(HOME_ZONE, WEST, 'riftbound');
    const riftDefense = await campaign.defendObjective(HOME_ZONE, WEST, 'riftbound');
    expect(riftDefense.objective.defenseReadyAt).toEqual({
      aegis: NOW + CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS,
      riftbound: NOW + CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS,
    });
    await campaign.claimObjective(HOME_ZONE, WEST, 'aegis');
    await expect(campaign.defendObjective(HOME_ZONE, WEST, 'aegis')).rejects.toThrow(/Defense ready/);
  });

  test('rejects duplicate simultaneous claims without duplicate influence', async () => {
    const campaign = new CampaignLocal();
    const results = await Promise.allSettled([
      campaign.defendObjective(HOME_ZONE, WEST, 'aegis'),
      campaign.defendObjective(HOME_ZONE, WEST, 'aegis'),
    ]);
    expect(results.map((result) => result.status)).toEqual(['fulfilled', 'rejected']);
    expect((await campaign.getSnapshot(HOME_ZONE)).activeZone?.influence.aegis).toBe(35);
  });

  test('rejects hostile, non-standard, capital and unknown objectives without changing state', async () => {
    const campaign = new CampaignLocal();
    const before = await campaign.getSnapshot();
    await expect(campaign.defendObjective(HOME_ZONE, WEST, 'riftbound')).rejects.toThrow(/Only friendly objectives/);
    await expect(campaign.defendObjective(HOME_ZONE, `${HOME_ZONE}_aegis_keep`, 'aegis'))
      .rejects.toThrow(/Only battlefield and fortress standards/);
    await expect(campaign.defendObjective('aegis_capital', 'aegis_capital_courtyard', 'aegis'))
      .rejects.toThrow(/Only battlefield and fortress standards/);
    await expect(campaign.defendObjective(HOME_ZONE, 'missing_objective', 'aegis')).rejects.toThrow(/Unknown campaign objective/);
    await expect(campaign.defendObjective('missing_zone', WEST, 'aegis')).rejects.toThrow(/Unknown campaign objective/);
    expect(await campaign.getSnapshot()).toEqual(before);
    expect(storage.size).toBe(0);
  });

  test('loads older campaign saves with defense available and preserves their influence', async () => {
    storage.set(STORAGE_KEY, JSON.stringify({
      version: 2, zoneControl: {}, objectiveControl: {}, influence: { [HOME_ZONE]: { aegis: 70 } },
    }));
    const campaign = new CampaignLocal();
    const before = await campaign.getSnapshot(HOME_ZONE);
    expect(before.activeZone?.influence.aegis).toBe(70);
    expect(before.activeZone?.objectives.every((objective) => Object.keys(objective.defenseReadyAt).length === 0)).toBe(true);
    await campaign.defendObjective(HOME_ZONE, WEST, 'aegis');
    expect((await campaign.getSnapshot(HOME_ZONE)).activeZone?.influence.aegis).toBe(105);
    expect(JSON.parse(storage.get(STORAGE_KEY)!).version).toBe(3);
  });

  test('reset clears persisted cooldowns and broadcasts current-zone defense updates', async () => {
    const campaign = new CampaignLocal();
    const updates: CampaignSnapshot[] = [];
    const unsubscribe = campaign.subscribeSnapshot((snapshot) => updates.push(snapshot), HOME_ZONE);
    await campaign.defendObjective(HOME_ZONE, WEST, 'aegis');
    expect(updates.at(-1)?.activeZone?.influence.aegis).toBe(35);
    await campaign.resetCampaign();
    expect(updates.at(-1)?.activeZone?.influence.aegis).toBe(0);
    expect(updates.at(-1)?.activeZone?.objectives.find((objective) => objective.id === WEST)?.defenseReadyAt).toEqual({});
    unsubscribe();
    const count = updates.length;
    const reloaded = new CampaignLocal();
    await reloaded.defendObjective(HOME_ZONE, WEST, 'aegis');
    expect(updates).toHaveLength(count);
  });

  test('allows defenses on fortress standards while preserving siege readiness rules', async () => {
    const campaign = new CampaignLocal();
    const zoneId = 'aegis_gate_fortress';
    for (const direction of ['west', 'central', 'east']) {
      await campaign.defendObjective(zoneId, `${zoneId}_${direction}_objective`, 'aegis');
    }
    const capture = await campaign.claimObjective(zoneId, `${zoneId}_riftbound_keep`, 'aegis');
    expect(capture.reward).toMatchObject({ xp: 1500, gold: 150 });
    expect(capture.snapshot.aegis.citySiegeReady).toBe(false);
    expect(capture.snapshot.riftbound.citySiegeReady).toBe(false);
  });

  test('keeps the backend defense API as an explicit unimplemented stub', () => {
    expect(() => new CampaignSupabase().defendObjective(HOME_ZONE, WEST, 'aegis'))
      .toThrow(/NotImplementedError: CampaignSupabase.defendObjective/);
  });
});

describe('campaign defense and reward data', () => {
  test.each([
    ['brightfen_approach', 300, 30, 8],
    ['glassriver_ford', 600, 60, 11],
    ['highvale_rampart', 900, 90, 14],
    ['dawnline_expanse', 1200, 120, 17],
    ['aegis_gate_fortress', 1500, 150, 20],
  ] as const)('%s awards equipment and XP appropriate to its campaign tier', (zoneId, xp, gold, strength) => {
    const reward = campaignKeepCaptureReward(zoneId);
    expect(reward).toMatchObject({ xp, gold, influence: 0 });
    expect(reward.items).toHaveLength(1);
    expect(reward.items![0].strengthRoll).toEqual({ min: strength, max: strength + 2 });
  });

  test('uses absolute cooldown timestamps consistently for runtime eligibility', () => {
    const objective = {
      type: 'battle_objective' as const,
      control: 'aegis' as CampaignRealm,
      defenseReadyAt: { aegis: NOW + 180_000 },
    };
    expect(campaignObjectiveDefenseEligibility(HOME_ZONE, objective, 'aegis', NOW).defendable).toBe(false);
    expect(campaignObjectiveDefenseEligibility(HOME_ZONE, objective, 'aegis', NOW + 180_000).defendable).toBe(true);
  });
});
