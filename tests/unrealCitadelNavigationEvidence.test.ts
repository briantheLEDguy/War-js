import { createHash } from 'node:crypto';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { requireCandidateSiegeNavigation } from '../scripts/unreal/siege-content-evidence';

describe('fresh navigation before native siege enrollment', () => {
  it('requires the exact saved map, city, complete ledger and ordinary probe results', () => {
    const directory = mkdtempSync(path.join(os.tmpdir(), 'citadel-navigation-'));
    try {
      const map = '/Game/WorldRebuild/AegisCitadel_abcdef123456/SiegeCandidate';
      const blueprint = { recipeVersion: 11, signature: 'a'.repeat(64), objectives: [[0, 0, 0]],
        optionalObjectives: [[1, 0, 0]], teamSpawns: [[2, 0, 0]],
        routes: [{ points: [[0, 0, 0], [1, 0, 0]] }], spawnApproaches: [{ points: [[2, 0, 0], [3, 0, 0]] }] };
      const receipt = { siegeMap: map, city: { revision: 'b'.repeat(64) },
        packageHashes: { [map]: 'c'.repeat(64) }, navigation: {} as any };
      const navigation = { schemaVersion: 1, passed: true, anchorsReachable: true, map,
        signature: blueprint.signature, cityRevision: receipt.city.revision, mapSha256: receipt.packageHashes[map],
        packageHashes: receipt.packageHashes, points: [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]],
        probe: Array.from({ length: 4 }, (_, i) => `${i} projected=1 connected=1 position=fixture`).join('\n'),
        physicalTraversalVerified: false, convoyVerified: false, fullSiegeApproved: false,
        visualApproved: false, releaseAcceptance: false };
      const save = (value: any) => {
        const bytes = JSON.stringify(value);
        writeFileSync(path.join(directory, 'navigation.json'), bytes);
        receipt.navigation = { file: 'navigation.json', sha256: createHash('sha256').update(bytes).digest('hex'),
          cityRevision: navigation.cityRevision, mapSha256: navigation.mapSha256 };
      };
      expect(() => requireCandidateSiegeNavigation(directory, receipt, blueprint)).toThrow(/Build fresh/);
      save(navigation);
      expect(() => requireCandidateSiegeNavigation(directory, receipt, blueprint)).not.toThrow();
      for (const change of [{ passed: false }, { anchorsReachable: false }, { map: map + '_old' },
        { mapSha256: 'd'.repeat(64) }, { cityRevision: 'e'.repeat(64) }, { signature: 'f'.repeat(64) },
        { points: navigation.points.slice(1) }, { points: [...navigation.points].reverse() },
        { probe: navigation.probe.replace('2 projected=1 connected=1', '2 projected=1 connected=0') },
        { probe: navigation.probe.split('\n').slice(1).join('\n') }, { fullSiegeApproved: true }]) {
        save({ ...navigation, ...change });
        expect(() => requireCandidateSiegeNavigation(directory, receipt, blueprint)).toThrow(/incomplete, stale/);
      }
      save(navigation);
      writeFileSync(path.join(directory, 'navigation.json'), JSON.stringify({ ...navigation, passed: false }));
      expect(() => requireCandidateSiegeNavigation(directory, receipt, blueprint)).toThrow(/receipt changed/);
      save(navigation); receipt.navigation.file = '../navigation.json';
      expect(() => requireCandidateSiegeNavigation(directory, receipt, blueprint)).toThrow(/Build fresh/);
      save(navigation); receipt.navigation.mapSha256 = 'd'.repeat(64);
      expect(() => requireCandidateSiegeNavigation(directory, receipt, blueprint)).toThrow(/incomplete, stale/);
    } finally { rmSync(directory, { recursive: true, force: true }); }
  });
  it('preserves historical receipt semantics', () => {
    expect(() => requireCandidateSiegeNavigation('unused', {}, { recipeVersion: 10 })).not.toThrow();
  });
});
