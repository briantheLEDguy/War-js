import { mkdtempSync, rmSync, writeFileSync, unlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, expect, test } from 'vitest';
import { verifyScenery } from '../server/scenarios/host';
import { sharedCityFixture } from './fixtures/sharedCityContent';
import { ScenarioCoordinator } from '../server/scenarios/coordinator';
import { scenarioCatalog } from '../shared/scenarios/types';

const roots: string[] = [];
afterEach(() => { for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true }); });
function setup() {
  const root = mkdtempSync(path.join(tmpdir(), 'shared-city-')); roots.push(root);
  return { root, ...sharedCityFixture(root) };
}
test('scenario catalogs pin the installed city revision without a hardcoded scenery hash', () => {
  const catalog = scenarioCatalog.map(row => ({ ...row, contentRevision: 'installed-city' }));
  const coordinator = new ScenarioCoordinator(() => {}, undefined, () => 0, catalog);
  expect(coordinator.definition('lower_city').contentRevision).toBe('installed-city');
  expect(scenarioCatalog[0].contentRevision).toBe('');
});
test('a newly published city invalidates the siege until its same revision is reviewed', () => {
  const f = setup();
  f.receipt.cities[0].revision = f.manifest.zones[0].cityRevision = 'next'; f.save();
  expect(() => verifyScenery(f.root)).toThrow('stale');
  f.siege.revision = 'next'; f.save();
  expect(verifyScenery(f.root)).toBe('next');
});
test('old intact scenery cannot pass after the active city changes', () => {
  const f = setup(); expect(verifyScenery(f.root)).toBe('current');
  f.manifest.zones[0].cityRevision = 'next'; f.save();
  expect(() => verifyScenery(f.root)).toThrow('stale');
});
test('siege must reference the identical city levels, without gameplay or copies', () => {
  const f = setup(); f.siege.layers = f.receipt.cities[0].gameplayLevels; f.save();
  expect(() => verifyScenery(f.root)).toThrow('stale');
});
test('duplicate city attachments and missing visual reviews are rejected', () => {
  const f = setup(); f.receipt.cities[0].sceneryLevels.push(f.receipt.cities[0].sceneryLevels[0]); f.save();
  expect(() => verifyScenery(f.root)).toThrow('duplicated');
  f.receipt.cities[0].sceneryLevels.pop(); f.siege.visualVerified = false; f.save();
  expect(() => verifyScenery(f.root)).toThrow('visual verification');
});
test.each(['edit', 'remove'])('a model dependency %s invalidates acceptance', action => {
  const f = setup(); const model = Object.keys(f.receipt.cities[0].dependencyHashes)[0];
  const file = path.join(f.root, 'unreal/AegisWar/Content', model.slice(6) + '.umap');
  if (action === 'edit') writeFileSync(file, 'new mesh'); else unlinkSync(file);
  expect(() => verifyScenery(f.root)).toThrow('stale or missing');
});
