import { describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { sharedCityFixture } from './fixtures/sharedCityContent';
import { verifyFullCapitalSiege } from '../server/scenarios/city-content';

describe('full capital siege publication gate', () => {
  it('requires fresh full siege and evacuation proof beyond historical lower-city acceptance', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'aegis-full-siege-'));
    try {
      const fixture = sharedCityFixture(root);
      expect(() => verifyFullCapitalSiege(root)).toThrow();
      const folder = path.join(root, 'artifacts/unreal/citadel-siege'); mkdirSync(folder, { recursive: true });
      const routes = JSON.stringify({ version: 2, objectives: [0, 1, 2, 3, 4, 5, 6, 7] });
      writeFileSync(path.join(folder, 'route-plan.json'), routes);
      const approval = { version: 1, rulesVersion: 2, battlefieldDefinitionVersion: 2, revision: 'current', capacity: 18,
        objectiveCount: 8, optionalCount: 3, routePlanSha256: createHash('sha256').update(routes).digest('hex'),
        packageHashes: { [fixture.siege.map]: fixture.siege.mapSha256 }, geometryVerified: true, navigationVerified: true,
        traversalVerified: true, visualVerified: true, rulesVerified: true, liveCapitalVerified: true, scenarioVerified: true, evacuationVerified: false };
      const save = () => writeFileSync(path.join(folder, 'full-siege-approval.json'), JSON.stringify(approval));
      save(); expect(() => verifyFullCapitalSiege(root)).toThrow('incomplete');
      approval.evacuationVerified = true; save(); expect(verifyFullCapitalSiege(root)).toBe('current');
      writeFileSync(path.join(folder, 'route-plan.json'), routes + '\n');
      expect(() => verifyFullCapitalSiege(root)).toThrow('route proof is stale');
    } finally { rmSync(root, { recursive: true, force: true }); }
  });
});
