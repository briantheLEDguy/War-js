import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { verifySharedCities } from '../../server/scenarios/city-content';
import { requireNativeCitadelImport } from './citadel-import-evidence';
import { requireNativeCitadelLighting } from './citadel-lighting-evidence';
import { requireCitadelPackageOwnership, requireNativePackageHash } from './native-package-evidence';
import { defaultEngineRoot } from './toolchain';
import { requireNativeCitadelTerrain } from './citadel-terrain-evidence';

export interface SiegeContentEvidence { cityRevision: string; mapSha256: string }

export interface CandidateSiegeContentEvidence extends SiegeContentEvidence {
  map: string; signature: string; geometrySignature: string;
}

/** New recipes cannot launch a fixture against inherited, stale navigation. */
export function requireCandidateSiegeNavigation(directory: string, receipt: any, blueprint: any): void {
  if ((blueprint.recipeVersion ?? 0) < 11) return;
  const binding = receipt.navigation;
  if (binding?.file !== 'navigation.json' || !/^[a-f0-9]{64}$/.test(binding.sha256 ?? ''))
    throw new Error('Build fresh candidate navigation before launching the native siege fixture.');
  const bytes = readFileSync(path.join(directory, binding.file));
  if (createHash('sha256').update(bytes).digest('hex') !== binding.sha256)
    throw new Error('Candidate navigation receipt changed; rebuild and verify before launch.');
  const navigation = JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/, ''));
  const expected: number[][] = [];
  for (const point of [...blueprint.objectives, ...blueprint.optionalObjectives, ...blueprint.teamSpawns,
    ...blueprint.routes.flatMap((row: any) => row.points),
    ...(blueprint.spawnApproaches ?? []).flatMap((row: any) => row.points)]) {
    if (!Array.isArray(point) || point.length !== 3 || !point.every(Number.isFinite))
      throw new Error('Candidate navigation ledger contains an invalid waypoint.');
    if (!expected.some(previous => previous.every((value, i) => value === point[i]))) expected.push(point);
  }
  const probes: string[] = typeof navigation.probe === 'string'
    ? (navigation.probe as string).split(/\r?\n/).filter(row => row.trim()) : [];
  if (navigation.schemaVersion !== 1 || navigation.passed !== true || navigation.anchorsReachable !== true
    || navigation.map !== receipt.siegeMap || navigation.signature !== blueprint.signature
    || navigation.cityRevision !== receipt.city.revision || binding.cityRevision !== navigation.cityRevision
    || navigation.mapSha256 !== receipt.packageHashes[receipt.siegeMap] || binding.mapSha256 !== navigation.mapSha256
    || navigation.packageHashes?.[receipt.siegeMap] !== navigation.mapSha256
    || JSON.stringify(navigation.points) !== JSON.stringify(expected) || probes.length !== expected.length
    || probes.some((row, i) => !row.startsWith(`${i} projected=1 connected=1 `))
    || ['physicalTraversalVerified', 'convoyVerified', 'fullSiegeApproved', 'visualApproved', 'releaseAcceptance']
      .some(name => navigation[name] !== false))
    throw new Error('Candidate navigation is incomplete, stale or claims unverified acceptance.');
}

/** Candidate proofs bind all native dependencies without granting admission. */
export function candidateSiegeContentEvidence(repository: string, map: string,
  engineRoot = defaultEngineRoot()): CandidateSiegeContentEvidence {
  const match = /^\/Game\/WorldRebuild\/AegisCitadel_([a-f0-9]{12})\/SiegeCandidate$/.exec(map);
  if (!match) throw new Error('An exact isolated citadel siege candidate is required.');
  const directory = path.join(repository, 'artifacts/unreal/aegis-citadel', match[1]);
  const read = (name: string) => JSON.parse(readFileSync(path.join(directory, name), 'utf8').replace(/^\uFEFF/, ''));
  const receipt = read('candidate.json');
  const blueprint = read('blueprint.json');
  if (receipt.schemaVersion !== 1 || receipt.published !== false || receipt.siegeMap !== map
    || receipt.revision !== match[1] || blueprint.revision !== match[1]
    || !/^[a-f0-9]{64}$/.test(receipt.signature) || receipt.signature !== blueprint.signature
    || !/^[a-f0-9]{64}$/.test(receipt.geometrySignature) || !/^[a-f0-9]{64}$/.test(receipt.city?.revision)
    || receipt.nativeImported !== true || !receipt.packageHashes?.[map] || !Object.keys(receipt.sourceHashes ?? {}).length)
    throw new Error('The candidate receipt is incomplete or belongs to another revision.');
  const stageHash = (name: string) => createHash('sha256')
    .update(readFileSync(path.join(repository, 'scripts/unreal', name))).digest('hex');
  if (!/^[a-f0-9]{64}$/.test(receipt.stageRecipeSha256 ?? '')
    || stageHash('stage-aegis-citadel.py') !== receipt.stageRecipeSha256
    || !receipt.stageDependencySha256?.['citadel_stage_contract.py']
    || Object.entries(receipt.stageDependencySha256).some(([name, expected]) =>
      !/^[A-Za-z0-9_-]+\.py$/.test(name) || !/^[a-f0-9]{64}$/.test(String(expected)) || stageHash(name) !== expected))
    throw new Error('Candidate staging recipe or dependency changed; repeat the bounded native preparation.');
  const city = receipt.city;
  for (const hashes of [receipt.sourceHashes, city.dependencyHashes]) requireCitadelPackageOwnership(hashes, false);
  for (const hashes of [receipt.packageHashes, city.packageHashes]) requireCitadelPackageOwnership(hashes, true);
  const equalHashes = (left: any, right: any) => left && right && !Array.isArray(left) && !Array.isArray(right)
    && JSON.stringify(Object.keys(left).sort()) === JSON.stringify(Object.keys(right).sort())
    && Object.keys(left).every(name => left[name] === right[name]);
  if (Object.keys(receipt.sourceHashes).some(name => receipt.packageHashes[name] !== undefined
    && receipt.packageHashes[name] !== receipt.sourceHashes[name]))
    throw new Error('Conflicting owned/source package hashes in the candidate receipt.');
  const boundHashes = { ...receipt.sourceHashes, ...receipt.packageHashes };
  if (city.definition !== `/Game/WorldRebuild/AegisCitadel_${match[1]}/City`
    || !Array.isArray(city.sceneryLevels) || !city.sceneryLevels.length
    || new Set(city.sceneryLevels).size !== city.sceneryLevels.length
    || JSON.stringify(city.sceneryLevels) !== JSON.stringify(receipt.sceneryLevels)
    || !Array.isArray(city.origin) || city.origin.length !== 3 || !city.origin.every(Number.isFinite)
    || !city.packageHashes || [city.definition, ...city.sceneryLevels].some(name =>
      !boundHashes[name] || city.packageHashes[name] !== boundHashes[name])
    || !Object.keys(city.dependencyHashes ?? {}).length || typeof city.revisionPayload !== 'string'
    || createHash('sha256').update(city.revisionPayload).digest('hex') !== city.revision)
    throw new Error('Candidate shared city hashes or revision payload are inconsistent.');
  let payload: any;
  try { payload = JSON.parse(city.revisionPayload); } catch { throw new Error('Invalid candidate city revision payload.'); }
  if (!payload || JSON.stringify(Object.keys(payload).sort()) !== '["dependencies","origin","scenery"]'
    || !equalHashes(payload.scenery, Object.fromEntries(city.sceneryLevels.map((name: string) => [name, city.packageHashes[name]])))
    || !equalHashes(payload.dependencies, city.dependencyHashes) || JSON.stringify(payload.origin) !== JSON.stringify(city.origin))
    throw new Error('Candidate city revision payload differs from its actual scenery, dependencies or origin.');
  for (const hashes of [receipt.packageHashes, receipt.sourceHashes, city.packageHashes, city.dependencyHashes]) for (const [packageName, expected] of Object.entries(hashes)) {
    requireNativePackageHash(repository, packageName, expected, engineRoot);
  }
  requireNativeCitadelImport(directory, receipt, blueprint);
  requireNativeCitadelLighting(receipt, blueprint);
  requireNativeCitadelTerrain(repository, directory);
  requireCandidateSiegeNavigation(directory, receipt, blueprint);
  return { map, signature: receipt.signature, geometrySignature: receipt.geometrySignature,
    cityRevision: receipt.city.revision, mapSha256: receipt.packageHashes[map] };
}

export function siegeContentEvidence(repository: string): SiegeContentEvidence {
  const city = verifySharedCities(repository).find(row => row.id === 'aegis_capital')!;
  const map = path.join(repository, 'unreal/AegisWar/Content/Capitals/Siege/AegisCapital_Siege.umap');
  return { cityRevision: city.revision, mapSha256: createHash('sha256').update(readFileSync(map)).digest('hex') };
}

export function requireSameSiegeContent(before: SiegeContentEvidence, after: SiegeContentEvidence): void {
  if (!/^[a-f0-9]{64}$/.test(before.cityRevision) || !/^[a-f0-9]{64}$/.test(before.mapSha256)
      || before.cityRevision !== after.cityRevision || before.mapSha256 !== after.mapSha256)
    throw new Error('City or siege overlay changed during verification; repeat the proof.');
}
