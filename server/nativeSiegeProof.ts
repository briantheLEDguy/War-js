import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { candidateSiegeContentEvidence, type CandidateSiegeContentEvidence } from '../scripts/unreal/siege-content-evidence';
import { createCampaign, type PlayerIdentity, type Realm } from '../shared/orvr';
import { startAuthority } from './authority';
import { DevelopmentAuthenticator } from './auth';
import { FileCampaignRepository } from './persistence';
import { requireCitadelPackageOwnership, requireNativePackageHash } from '../scripts/unreal/native-package-evidence';
import { defaultEngineRoot } from '../scripts/unreal/toolchain';

const json = (filename: string): any => JSON.parse(readFileSync(filename, 'utf8').replace(/^\uFEFF/, ''));
function verifyPackages(repository: string, hashes: unknown, engineRoot = defaultEngineRoot()): void {
  if (!hashes || typeof hashes !== 'object' || Array.isArray(hashes) || !Object.keys(hashes).length)
    throw new Error('Prepared campaign proof package hashes are missing.');
  for (const [name, expected] of Object.entries(hashes)) {
    requireNativePackageHash(repository, name, expected, engineRoot);
  }
}

/** Prepared live-world proof verifies retained routing/services, but grants no published admission. */
export function campaignCandidateContentEvidence(repository: string, map: string,
  engineRoot = defaultEngineRoot()): CandidateSiegeContentEvidence {
  const match = /^\/Game\/WorldRebuild\/AegisCitadel_([a-f0-9]{12})\/CampaignCandidate$/.exec(map);
  if (!match) throw new Error('An exact prepared live campaign candidate is required.');
  const prefix = map.slice(0, map.lastIndexOf('/'));
  const isolated = candidateSiegeContentEvidence(repository, `${prefix}/SiegeCandidate`, engineRoot);
  const directory = path.join(repository, 'artifacts/unreal/aegis-citadel', match[1]);
  const city = json(path.join(directory, 'candidate.json'));
  const staged = json(path.join(directory, 'publication-candidate.json'));
  const packages = { map, layer: `${prefix}/CampaignRoutingCandidate`, overlay: `${prefix}/CampaignSiegeOverlay`,
    frontend: `${prefix}/CapitalPresentationCandidate` };
  const capital = staged.manifest?.zones?.filter((zone: any) => zone.id === 'aegis_capital');
  const expectedLevels = [...city.sceneryLevels, ...city.retainedGameplayLevels, packages.overlay].sort();
  if (staged.schemaVersion !== 1 || staged.revision !== match[1] || staged.published !== false
    || Object.entries(packages).some(([key, value]) => staged[key] !== value || !staged.packageHashes?.[value])
    || staged.manifest?.mainMap !== map || staged.manifest?.layer !== packages.layer
    || staged.build?.map !== map || staged.build?.layer !== packages.layer
    || staged.manifest?.mainSha256 !== staged.packageHashes[map]
    || capital?.length !== 1 || capital[0].cityDefinition !== city.city.definition
    || capital[0].cityRevision !== isolated.cityRevision || capital[0].citadelRevision !== match[1]
    || JSON.stringify(Object.values(capital[0].levels ?? {}).sort()) !== JSON.stringify(expectedLevels))
    throw new Error('Prepared live campaign bindings differ from the isolated citadel source.');
  verifyPackages(repository, staged.packageHashes, engineRoot);
  verifyPackages(repository, staged.sourceHashes, engineRoot);
  verifyPackages(repository, staged.manifest.packageHashes, engineRoot);
  requireCitadelPackageOwnership(staged.sourceHashes, false);
  for (const hashes of [staged.packageHashes, staged.manifest.packageHashes]) requireCitadelPackageOwnership(hashes, true);
  return { ...isolated, map, mapSha256: staged.packageHashes[map] };
}

function proofEvidence(repository: string, map: string, engineRoot = defaultEngineRoot()): CandidateSiegeContentEvidence {
  return map.endsWith('/CampaignCandidate') ? campaignCandidateContentEvidence(repository, map, engineRoot)
    : candidateSiegeContentEvidence(repository, map, engineRoot);
}

/** No ordinary campaign player sessions can mutate this isolated native-host fixture. */
class NativeProofAuthenticator extends DevelopmentAuthenticator {
  override issue(_realm: Realm, _name: string): never { throw new Error('This authority accepts only its private native proof host.'); }
  override async verify(_token: string, _characterId: string): Promise<PlayerIdentity> {
    throw new Error('Ordinary campaign admission is closed in this proof fixture.');
  }
}

export interface NativeSiegeProofOptions {
  repositoryRoot: string;
  map: string;
  /** Private Saved namespace. Reuse requires an explicit resume of the identical candidate. */
  fixtureId: string;
  resume?: boolean;
  /** Actual configured installation; portable fixtures explicitly inject their isolated bytes. */
  engineRoot?: string;
}

/** Runs the real HTTP/journal path against explicitly seeded test territory, never the ordinary campaign journal. */
export async function startNativeSiegeProofAuthority(options: NativeSiegeProofOptions) {
  if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(options.fixtureId)) throw new Error('Invalid isolated native proof fixture identity.');
  const repositoryRoot = path.resolve(options.repositoryRoot), evidence = proofEvidence(repositoryRoot, options.map, options.engineRoot);
  const root = path.join(repositoryRoot, 'unreal/AegisWar/Saved/CitadelSiegeProof');
  const directory = path.join(root, options.fixtureId);
  const hostId = `citadel-proof-${options.fixtureId}`, campaignId = hostId;
  const checkpointPath = path.join(directory, 'campaign.json'), hostConfigPath = path.join(directory, 'host.json');
  const fixture = { schemaVersion: 1, fixtureId: options.fixtureId, hostId, campaignId, ...evidence,
    proofOnly: true, contentReviewOverride: true, ordinaryTerritorialAcceptance: false,
    productionAdmission: false, steamAdmission: false, characterStateSource: 'native-capture',
    seededTerritory: { dawnline_expanse: 'riftbound', aegis_crownworks: 'riftbound',
      aegis_gate_fortress: 'riftbound', sunmeadow_march: 'aegis' } };
  await mkdir(root, { recursive: true });
  let key: string;
  if (options.resume) {
    const saved = JSON.parse(await readFile(path.join(directory, 'fixture.json'), 'utf8'));
    if (JSON.stringify(saved) !== JSON.stringify(fixture)) throw new Error('The isolated proof identity or native candidate changed.');
    key = (await readFile(path.join(directory, 'bootstrap-key'), 'utf8')).trim();
    if (!/^[a-f0-9]{64}$/.test(key)) throw new Error('Invalid private proof bootstrap credential.');
    const checkpoint = JSON.parse(await readFile(checkpointPath, 'utf8'));
    if (checkpoint.state?.id !== campaignId) throw new Error('The proof journal belongs to another campaign.');
  } else {
    await mkdir(directory);
    key = randomBytes(32).toString('hex');
    await writeFile(path.join(directory, 'fixture.json'), JSON.stringify(fixture), { flag: 'wx', mode: 0o600, flush: true });
    await writeFile(path.join(directory, 'bootstrap-key'), key, { flag: 'wx', mode: 0o600, flush: true });
    const repository = new FileCampaignRepository(checkpointPath);
    try {
      if (await repository.load()) throw new Error('A fresh native proof cannot overwrite an existing journal.');
      const state = createCampaign({ id: campaignId });
      state.phase = 'city';
      for (const zone of Object.values(state.zones)) zone.status = 'inactive';
      for (const [zoneId, realm] of Object.entries(fixture.seededTerritory)) {
        state.zones[zoneId].status = 'secured'; state.zones[zoneId].victor = realm as Realm;
      }
      const city = state.zones.aegis_capital;
      city.cityAttacker = 'riftbound'; city.status = 'staging'; city.stagingRemaining = 180;
      city.activation = 1; city.activationId = `${campaignId}:1:aegis_capital:1`; city.cityRemaining = 1800;
      await repository.commit(0, state);
    } finally { await repository.close(); }
  }
  const server = await startAuthority({ host: '127.0.0.1', port: 0, auth: new NativeProofAuthenticator(),
    repository: new FileCampaignRepository(checkpointPath), automaticTicks: false,
    nativeSiege: { bootstrapKey: key, verifyContent: () => {
      if (JSON.stringify(proofEvidence(repositoryRoot, options.map, options.engineRoot)) !== JSON.stringify(evidence))
        throw new Error('Native candidate changed during the isolated host proof.');
      return evidence.cityRevision;
    } } });
  try {
    await writeFile(hostConfigPath, JSON.stringify({ ...fixture, url: server.httpUrl, key }), { mode: 0o600, flush: true });
  } catch (error) { await server.close(); throw error; }
  return { server, hostConfigPath, checkpointPath, evidence, fixture,
    async close() { await server.close(); } };
}
