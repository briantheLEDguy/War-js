import { describe, expect, it } from 'vitest';
import { access, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { assertCampaignConfigCompatible } from '../server/configCompatibility';
import { startAuthority } from '../server/authority';
import { DevelopmentAuthenticator } from '../server/auth';
import { FileCampaignRepository } from '../server/persistence';
import { createCampaign, defaultZoneConfig } from '../src/shared/orvr';
import type { AbilityRule, CampaignConfig } from '../src/shared/orvr';

const strike: AbilityRule = { id: 'prelate.strike', cooldownSeconds: 1, range: 3, damage: 20 };
const heal: AbilityRule = { id: 'prelate.heal', cooldownSeconds: 2, range: 20, healing: 10 };

function configuration(): CampaignConfig {
  const zone = defaultZoneConfig('sunmeadow_march');
  zone.terrain = { sourceVersion: 'authored-test-v1', landforms: [], clearCorridors: [],
    flattenAreas: [{ id: 'hill', x: 100, z: 100, radius: 50, feather: 20, height: 8 }] };
  return { id: 'saved-campaign', zones: [zone], abilities: [strike, heal] };
}

describe('saved campaign static configuration compatibility', () => {
  it('accepts equivalent JSON definitions regardless of object insertion order or ability registration order', () => {
    const config = configuration();
    const saved = createCampaign(config);
    const reverseObjectKeys = (value: unknown): unknown => {
      if (Array.isArray(value)) return value.map(reverseObjectKeys);
      if (!value || typeof value !== 'object') return value;
      return Object.fromEntries(Object.entries(value).reverse().map(([key, nested]) => [key, reverseObjectKeys(nested)]));
    };
    const reordered = reverseObjectKeys(config) as CampaignConfig;
    reordered.abilities!.reverse();
    expect(() => assertCampaignConfigCompatible(saved, reordered)).not.toThrow();
    saved.zones.sunmeadow_march.keeps.sunmeadow_march_aegis_keep.supplies = 500;
    saved.zones.sunmeadow_march.keeps.sunmeadow_march_aegis_keep.gates.outer.health = 300;
    expect(() => assertCampaignConfigCompatible(saved, reordered)).not.toThrow();
  });

  it('rejects changed, removed, or added ability rules and reports their IDs', () => {
    const config = configuration();
    const saved = createCampaign(config);
    expect(() => assertCampaignConfigCompatible(saved, { ...config, abilities: [{ ...strike, damage: 25 }, heal] })).toThrow(/ability rules: prelate.strike/);
    expect(() => assertCampaignConfigCompatible(saved, { ...config, abilities: [strike] })).toThrow(/ability rules: prelate.heal/);
    expect(() => assertCampaignConfigCompatible(saved, { ...config, abilities: [strike, heal, { ...strike, id: 'prelate.new' }] })).toThrow(/ability rules: prelate.new/);
  });

  it('rejects changed collision, routes, and campaign identity without modifying the saved simulation', () => {
    const config = configuration();
    const saved = createCampaign(config);
    const original = JSON.stringify(saved);
    const modified = structuredClone(config);
    modified.zones![0].collision = [{ minX: 0, minZ: 0, maxX: 1, maxZ: 1 }];
    modified.zones![0].objectives[0].routes!.aegis![1].x += 10;
    expect(() => assertCampaignConfigCompatible(saved, modified)).toThrow(/sunmeadow_march \[collision, objectives\]/);
    expect(() => assertCampaignConfigCompatible(saved, { ...config, id: 'another-campaign' })).toThrow(/campaign ID saved-campaign differs from another-campaign/);
    expect(JSON.stringify(saved)).toBe(original);
  });

  it('stops startup on changed terrain, releases the lease, and preserves the original checkpoint bytes', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'war-orvr-compatible-'));
    const filename = join(directory, 'campaign.json');
    const config = configuration();
    const original = JSON.stringify({ revision: 7, state: createCampaign(config) });
    const repository = new FileCampaignRepository(filename);
    try {
      await writeFile(filename, original);
      const updated = structuredClone(config);
      updated.zones![0].terrain!.flattenAreas[0].height = 12;
      await expect(startAuthority({ port: 0, auth: new DevelopmentAuthenticator(), repository, campaign: updated, automaticTicks: false }))
        .rejects.toThrow(/sunmeadow_march \[terrain\].*checkpoint has been preserved/);
      expect(await readFile(filename, 'utf8')).toBe(original);
      await expect(access(`${filename}.lock`)).rejects.toMatchObject({ code: 'ENOENT' });
      const matching = await startAuthority({ port: 0, auth: new DevelopmentAuthenticator(), repository: new FileCampaignRepository(filename),
        campaign: config, automaticTicks: false });
      try { expect(matching.inspect().zones.sunmeadow_march.config.terrain!.flattenAreas[0].height).toBe(8); }
      finally { await matching.close(); }
    } finally { await repository.close(); await rm(directory, { recursive: true, force: true }); }
  });
});
