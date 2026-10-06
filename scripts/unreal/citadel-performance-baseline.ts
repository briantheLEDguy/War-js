import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { PRESERVED_AEGIS_CITY } from './citadel-performance';
import { defaultEngineRoot } from './toolchain';
import type { CandidateSiegeContentEvidence } from './siege-content-evidence';
import { requireNativePackageHash } from './native-package-evidence';

export interface CitadelPerformanceBaselineManifest {
  schemaVersion: 1; revision: string; signature: string; signaturePayload: string;
  map: string; nativeImported: true; performanceBaseline: true; isolatedStageWindows: false;
  fixtureMode: 'earned_progression';
  sourceCity: typeof PRESERVED_AEGIS_CITY;
  sourceHashes: Record<string, string>; dependencyHashes: Record<string, string>; packageHashes: Record<string, string>;
  objectives: number[][]; optionalObjectives: number[][]; teamSpawns: number[][]; performanceFormations: unknown[];
}
const hash = (bytes: string | Buffer) => createHash('sha256').update(bytes).digest('hex');
const read = (file: string) => JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const canonical = (value: any): any => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const same = (a: any, b: any) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

/** Unchanged published scenery is benchmarked separately from candidate import/admission. */
export function citadelPerformanceBaselineEvidence(repository: string, map: string,
  engineRoot = defaultEngineRoot()): CandidateSiegeContentEvidence & { baselinePath: string } {
  const revision = /^\/Game\/WorldRebuild\/AegisCitadel_([a-f0-9]{12})\/PerformanceBaseline$/.exec(map)?.[1];
  if (!revision) throw new Error('An exact private performance baseline map is required.');
  const baselinePath = path.join(repository, 'artifacts/unreal/aegis-citadel/performance-baseline', revision, 'baseline.json');
  const manifest = read(baselinePath);
  const fields = ['fixtureMode', 'sourceCity', 'sourceHashes', 'dependencyHashes', 'objectives', 'optionalObjectives', 'teamSpawns', 'performanceFormations'];
  if (manifest.schemaVersion !== 1 || manifest.revision !== revision || manifest.map !== map
    || manifest.nativeImported !== true || manifest.performanceBaseline !== true || manifest.isolatedStageWindows !== false
    || manifest.fixtureMode !== 'earned_progression'
    || !same(manifest.sourceCity, PRESERVED_AEGIS_CITY) || manifest.geometrySignature !== PRESERVED_AEGIS_CITY.revision
    || manifest.sourceHashesUnchanged !== true || manifest.nativeBattlefield?.definitionVersion !== 2
    || manifest.nativeBattlefield?.cityDefinition !== `${PRESERVED_AEGIS_CITY.path}.City`
    || manifest.nativeBattlefield?.cityRevision !== PRESERVED_AEGIS_CITY.revision
    || typeof manifest.nativeBattlefield?.actor !== 'string' || !manifest.nativeBattlefield.actor.startsWith(map + '.')
    || typeof manifest.signaturePayload !== 'string' || hash(manifest.signaturePayload) !== manifest.signature
    || manifest.signature.slice(0, 12) !== revision
    || ['progressionAcceptance', 'victoryAcceptance', 'conquestAcceptance', 'routeAcceptance', 'visualApproval',
      'productionAdmission', 'steamAdmission', 'fullSiegeAdmission'].some(key => manifest[key] !== false))
    throw new Error('Baseline is not the preserved city or claims unverified gameplay/admission.');
  const payload = JSON.parse(manifest.signaturePayload);
  if (!same(Object.keys(payload).sort(), fields.slice().sort()) || fields.some(key => !same(payload[key], manifest[key])))
    throw new Error('Baseline signature payload differs from actual mapped floors, cameras or source packages.');
  for (const [key, count] of [['objectives', 8], ['optionalObjectives', 3], ['teamSpawns', 6]] as const)
    if (!Array.isArray(manifest[key]) || manifest[key].length !== count || manifest[key].some((p: any) =>
      !Array.isArray(p) || p.length !== 3 || !p.every((v: any) => typeof v === 'number' && Number.isFinite(v))))
      throw new Error('Baseline requires the actual mapped original anchors and spawns.');
  if (!Array.isArray(manifest.performanceFormations) || manifest.performanceFormations.length !== 3)
    throw new Error('Baseline requires all three signed functional crowd formations.');
  const published = read(path.join(repository, 'artifacts/unreal/shared-cities/current.json')).cities
    .find((city: any) => city.id === 'aegis_capital');
  if (!published || published.definition !== PRESERVED_AEGIS_CITY.path || published.revision !== PRESERVED_AEGIS_CITY.revision
    || !published.packageHashes || !published.dependencyHashes
    || Object.entries(published.packageHashes).some(([name, value]) => manifest.sourceHashes?.[name] !== value)
    || !same(published.dependencyHashes, manifest.dependencyHashes))
    throw new Error('Baseline no longer matches all original published city packages/dependencies.');
  const union: Record<string, string> = {};
  for (const hashes of [manifest.sourceHashes, manifest.dependencyHashes, manifest.packageHashes]) {
    if (!hashes || Array.isArray(hashes) || !Object.keys(hashes).length) throw new Error('Baseline package ownership/hash map is missing.');
    for (const [name, expected] of Object.entries(hashes)) {
      if (!/^\/(?:Game|Engine)\/[A-Za-z0-9_/-]+$/.test(name) || name.includes('..') || !/^[a-f0-9]{64}$/.test(String(expected))
        || union[name] && union[name] !== expected) throw new Error('Invalid or conflicting baseline package identity.');
      union[name] = String(expected);
      requireNativePackageHash(repository, name, expected, engineRoot);
    }
  }
  if (!manifest.packageHashes[map] || Object.keys(manifest.packageHashes).some(name =>
    !name.startsWith(`/Game/WorldRebuild/AegisCitadel_${revision}/`) || manifest.sourceHashes[name] || manifest.dependencyHashes[name]))
    throw new Error('Baseline overlay ownership escaped its private namespace.');
  if (manifest.stageBaselineRecipeSha256 !== hash(readFileSync(path.join(repository, 'scripts/unreal/stage-citadel-performance-baseline.py'))))
    throw new Error('Baseline staging recipe changed; repeat actual private preparation.');
  return { map, mapSha256: manifest.packageHashes[map], cityRevision: PRESERVED_AEGIS_CITY.revision,
    signature: manifest.signature, geometrySignature: PRESERVED_AEGIS_CITY.revision, baselinePath };
}
