import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, expect, test } from 'vitest';
import { citadelPerformanceBaselineEvidence } from '../scripts/unreal/citadel-performance-baseline';
import { PRESERVED_AEGIS_CITY } from '../scripts/unreal/citadel-performance';
const roots: string[] = [];
afterEach(() => roots.splice(0).forEach(root => rmSync(root, { recursive: true, force: true })));
const sha = (s: string) => createHash('sha256').update(s).digest('hex');
function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-performance-baseline-')); roots.push(root);
  const write = (file: string, bytes: string) => { mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes); };
  const source = PRESERVED_AEGIS_CITY.path, scenery = '/Game/Preserved/Scenery', dependency = '/Game/Preserved/Mesh';
  for (const name of [source, scenery, dependency]) write(path.join(root, 'unreal/AegisWar/Content', name.slice(6)) + '.uasset', name);
  const sourceHashes = { [source]: sha(source), [scenery]: sha(scenery) }, dependencyHashes = { [dependency]: sha(dependency) };
  write(path.join(root, 'artifacts/unreal/shared-cities/current.json'), JSON.stringify({ cities: [{ id: 'aegis_capital',
    definition: source, revision: PRESERVED_AEGIS_CITY.revision, sceneryLevels: [scenery], packageHashes: sourceHashes, dependencyHashes }] }));
  const helper = path.join(root, 'scripts/unreal/stage-citadel-performance-baseline.py'); write(helper, 'PORTABLE TEST SOURCE ONLY');
  const payload = { fixtureMode: 'earned_progression', sourceCity: { ...PRESERVED_AEGIS_CITY }, sourceHashes, dependencyHashes,
    objectives: Array.from({ length: 8 }, () => [0, 0, 0]), optionalObjectives: Array.from({ length: 3 }, () => [0, 0, 0]),
    teamSpawns: Array.from({ length: 6 }, () => [0, 0, 0]), performanceFormations: [0, 1, 2].map(stage => ({ stage })) };
  const signaturePayload = JSON.stringify(payload), signature = sha(signaturePayload), revision = signature.slice(0, 12);
  const map = `/Game/WorldRebuild/AegisCitadel_${revision}/PerformanceBaseline`;
  write(path.join(root, 'unreal/AegisWar/Content', map.slice(6)) + '.umap', 'PORTABLE OVERLAY ONLY');
  const manifest: any = { ...payload, schemaVersion: 1, revision, signature, signaturePayload, map, geometrySignature: PRESERVED_AEGIS_CITY.revision,
    nativeImported: true, performanceBaseline: true, isolatedStageWindows: false, packageHashes: { [map]: sha('PORTABLE OVERLAY ONLY') },
    stageBaselineRecipeSha256: sha(readFileSync(helper, 'utf8')), sourceHashesUnchanged: true, nativeBattlefield: {
      actor: map + '.PerformanceBaseline:PersistentLevel.Field', definitionVersion: 2,
      cityDefinition: source + '.City', cityRevision: PRESERVED_AEGIS_CITY.revision },
    ...Object.fromEntries(['progressionAcceptance', 'victoryAcceptance', 'conquestAcceptance', 'routeAcceptance', 'visualApproval',
      'productionAdmission', 'steamAdmission', 'fullSiegeAdmission'].map(key => [key, false])) };
  const file = path.join(root, 'artifacts/unreal/aegis-citadel/performance-baseline', revision, 'baseline.json');
  const save = () => write(file, JSON.stringify(manifest)); save(); return { root, manifest, map, save, scenery };
}
test('preserved-city performance loader binds untouched published bytes without a candidate import or admission receipt', () => {
  const f = fixture(); const result = citadelPerformanceBaselineEvidence(f.root, f.map);
  expect(result.cityRevision).toBe(PRESERVED_AEGIS_CITY.revision); expect(result.geometrySignature).toBe(PRESERVED_AEGIS_CITY.revision);
  for (const change of [
    () => { f.manifest.fullSiegeAdmission = true; },
    () => { f.manifest.isolatedStageWindows = true; },
    () => { f.manifest.fixtureMode = 'isolated_stage_windows'; },
    () => { f.manifest.nativeBattlefield.cityRevision = sha('changed'); },
    () => { f.manifest.objectives[0][0] = 1; },
    () => { f.manifest.packageHashes['/Game/Escape'] = sha('escape'); },
  ]) { const original = JSON.stringify(f.manifest); change(); f.save();
    expect(() => citadelPerformanceBaselineEvidence(f.root, f.map)).toThrow();
    f.manifest = Object.assign(f.manifest, JSON.parse(original)); f.save(); }
});
test('a changed original scenery package invalidates the baseline even when all retained identity labels match', () => {
  const f = fixture(); writeFileSync(path.join(f.root, 'unreal/AegisWar/Content', f.scenery.slice(6)) + '.uasset', 'modified');
  expect(() => citadelPerformanceBaselineEvidence(f.root, f.map)).toThrow(/dependency changed/);
});
