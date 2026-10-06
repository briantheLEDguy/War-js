import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { afterEach, expect, test } from 'vitest';
import { campaignCandidateContentEvidence, startNativeSiegeProofAuthority } from '../server/nativeSiegeProof';
import { initialCapitalSiegeSnapshot } from '../shared/siege/contract';
import { citadelCandidateImportFixture } from './fixtures/citadelCandidateImport';
import { citadelLightingFixture } from './fixtures/citadelLighting';
import { citadelTerrainFixture } from './fixtures/citadelTerrain';

const roots: string[] = [];
const hosts: Awaited<ReturnType<typeof startNativeSiegeProofAuthority>>[] = [];
afterEach(async () => {
  await Promise.all(hosts.splice(0).map(host => host.close()));
  await Promise.all(roots.splice(0).map(root => rm(root, { recursive: true, force: true })));
});

async function candidate() {
  const root = await mkdtemp(path.join(os.tmpdir(), 'war-native-siege-proof-')); roots.push(root);
  const revision = '0123456789ab', signature = 'a'.repeat(64);
  const prefix = `/Game/WorldRebuild/AegisCitadel_${revision}`, map = `${prefix}/SiegeCandidate`;
  const receiptPath = path.join(root, 'artifacts/unreal/aegis-citadel', revision);
  await mkdir(receiptPath, { recursive: true });
  const scripts = path.join(root, 'scripts/unreal'); await mkdir(scripts, { recursive: true });
  await writeFile(path.join(scripts, 'stage-aegis-citadel.py'), 'fixture stage recipe');
  await writeFile(path.join(scripts, 'citadel_stage_contract.py'), 'fixture stage dependency');
  const hashes: Record<string, string> = {};
  async function asset(name: string) {
    const file = path.join(root, 'unreal/AegisWar/Content', name.slice(6)) + '.umap';
    await mkdir(path.dirname(file), { recursive: true });
    const contents = `Portable test package bytes only: ${name}`;
    await writeFile(file, contents); hashes[name] = createHash('sha256').update(contents).digest('hex');
    return file;
  }
  for (const name of [map, `${prefix}/City`, `${prefix}/Layers/GothicCitadel`, '/Game/OriginalCampaign', '/Game/RetainedServices', '/Game/ModelDependency']) await asset(name);
  const lighting = citadelLightingFixture(root, revision);
  const terrain = citadelTerrainFixture(root, revision, lighting.sourceHashes);
  lighting.outsideMaskPreservation.forEach((row: any) => { row.explicitTerrainCarves = row.source.endsWith('/authored') ? ['occupied_commander_hall'] : []; });
  Object.assign(hashes, lighting.packageHashes);
  const sceneryLevels = [...new Set([`${prefix}/Layers/GothicCitadel`, ...lighting.sceneryLevels])], origin = [0, 0, 0];
  const dependencyHashes = { '/Game/ModelDependency': hashes['/Game/ModelDependency'] };
  const revisionPayload = JSON.stringify({ scenery: Object.fromEntries(sceneryLevels.map(name => [name, hashes[name]])),
    dependencies: dependencyHashes, origin });
  const cityRevision = createHash('sha256').update(revisionPayload).digest('hex');
  const imported = citadelCandidateImportFixture(root, revision, signature);
  const city = { schemaVersion: 1, revision, signature, geometrySignature: imported.geometrySignature, published: false, nativeImported: true,
    nativeImportConvention: imported.nativeImportConvention, bindings: imported.bindings, proofStart: imported.proofStart,
    materialBindings:imported.materialBindings,
    stageRecipeSha256: createHash('sha256').update('fixture stage recipe').digest('hex'),
    stageDependencySha256: { 'citadel_stage_contract.py': createHash('sha256').update('fixture stage dependency').digest('hex'), ...terrain.stageDependencySha256 },
    sharedLightingChanges: lighting.sharedLightingChanges, nativeCloudPlacement: lighting.nativeCloudPlacement, terrainCarves: terrain.terrainCarves,
    outsideMaskPreservation: lighting.outsideMaskPreservation,
    exposureUsesExtendedEV100: false, exposureUnits: 'native_luminance',
    siegeMap: map, sourceHashes: { '/Game/OriginalCampaign': hashes['/Game/OriginalCampaign'], ...lighting.sourceHashes, ...terrain.sourceHashes },
    packageHashes: { [map]: hashes[map], [`${prefix}/City`]: hashes[`${prefix}/City`],
      [`${prefix}/Layers/GothicCitadel`]: hashes[`${prefix}/Layers/GothicCitadel`], ...imported.packageHashes, ...lighting.packageHashes, ...terrain.packageHashes },
    city: { definition: `${prefix}/City`, revision: cityRevision, revisionPayload, origin, sceneryLevels, dependencyHashes,
      packageHashes: { [`${prefix}/City`]: hashes[`${prefix}/City`], [`${prefix}/Layers/GothicCitadel`]: hashes[`${prefix}/Layers/GothicCitadel`],
        ...lighting.packageHashes } }, sceneryLevels,
    retainedGameplayLevels: ['/Game/RetainedServices'] };
  await writeFile(path.join(receiptPath, 'blueprint.json'), JSON.stringify({ revision, signature, teamSpawns: imported.teamSpawns,
    lightingTreatment: lighting.lightingTreatment, terrainCarves: terrain.planTerrainCarves, sourceRecipes: terrain.sourceRecipes, baseline: terrain.baseline }));
  await writeFile(path.join(receiptPath, 'candidate.json'), JSON.stringify(city));
  const packages = { map: `${prefix}/CampaignCandidate`, layer: `${prefix}/CampaignRoutingCandidate`,
    overlay: `${prefix}/CampaignSiegeOverlay`, frontend: `${prefix}/CapitalPresentationCandidate` };
  for (const name of Object.values(packages)) await asset(name);
  const staged = { schemaVersion: 1, revision, published: false, ...packages,
    packageHashes: Object.fromEntries(Object.values(packages).map(name => [name, hashes[name]])),
    sourceHashes: city.sourceHashes, build: { map: packages.map, layer: packages.layer },
    manifest: { mainMap: packages.map, layer: packages.layer, mainSha256: hashes[packages.map],
      packageHashes: { [packages.layer]: hashes[packages.layer], [packages.overlay]: hashes[packages.overlay],
        '/Game/RetainedServices': hashes['/Game/RetainedServices'], ...city.packageHashes },
      zones: [{ id: 'aegis_capital', cityDefinition: city.city.definition, cityRevision, citadelRevision: revision,
        levels: { ...Object.fromEntries(city.sceneryLevels.map((level, i) => [`scenery_${i}`, level])),
          gameplay_0: '/Game/RetainedServices', live_siege: packages.overlay } }] } };
  await writeFile(path.join(receiptPath, 'publication-candidate.json'), JSON.stringify(staged));
  return { root, map, packages, hashes, receiptPath, staged, cityRevision, asset, engineRoot: lighting.engineRoot };
}
const character = { id: 'actual_native_row', name: 'Native proof row', realm: 'aegis', visual: '/Game/Characters/Reviewed',
  returnMap: '/Game/World', returnPosition: [1, 2, 3], document: { zone: 'aegis_capital',
    inventory: { revision: 12, gold: 87, items: ['earned_item'] }, runtime: { health: 555, mana: 444, dead: false } } };

test('isolated actual-host HTTP proof persists captured state and resumes without touching the ordinary campaign', async () => {
  const fixture = await candidate();
  const ordinary = path.join(fixture.root, 'unreal/AegisWar/Saved/CampaignSiege/ordinary.json');
  await mkdir(path.dirname(ordinary), { recursive: true }); await writeFile(ordinary, 'ordinary owner journal');
  const options = { repositoryRoot: fixture.root, map: fixture.packages.map, fixtureId: 'actual-host', engineRoot: fixture.engineRoot };
  let host = await startNativeSiegeProofAuthority(options); hosts.push(host);
  const config = JSON.parse(await readFile(host.hostConfigPath, 'utf8'));
  expect(config).toMatchObject({ proofOnly: true, map: fixture.packages.map, contentReviewOverride: true,
    ordinaryTerritorialAcceptance: false, productionAdmission: false, steamAdmission: false });
  expect(JSON.parse(await readFile(path.join(path.dirname(host.hostConfigPath), 'fixture.json'), 'utf8')).key).toBeUndefined();
  const call = async (route: string, credential: string, body = {}) => {
    const response = await fetch(`${host.server.httpUrl}/native/siege/${route}`, { method: 'POST',
      headers: { Authorization: `Bearer ${credential}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ hostId: config.hostId, ...body }) });
    return { status: response.status, ...await response.json() };
  };
  expect((await fetch(`${host.server.httpUrl}/dev/session`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ realm: 'aegis' }) })).status).toBe(400);
  let token = (await call('register', config.key)).data.token;
  const lease = (await call('activate', token, { requestId: 'activate', rulesVersion: 2, contentRevision: fixture.cityRevision })).data;
  expect(lease).toMatchObject({ stats: 'campaign', capacity: 18, safeEvacuationZones:
    { aegis: ['sunmeadow_march'], riftbound: ['aegis_gate_fortress'] } });
  expect(host.server.inspect().nativeSiegeJournal?.characters).toBeUndefined();
  expect((await call('membership', token, { requestId: 'join', activationId: lease.activationId,
    action: 'join', characterId: character.id, realm: character.realm, character })).status).toBe(200);
  expect((await call('update', token, { requestId: 'checkpoint', activationId: lease.activationId, sequence: 1,
    snapshot: { ...initialCapitalSiegeSnapshot(), phase: 'active', remaining: 800, elapsed: 40 }, characters: [character] })).status).toBe(200);
  const earned = structuredClone(character);
  earned.document.inventory.revision = 13; earned.document.inventory.gold = 999;
  earned.document.runtime.health = 0; earned.document.runtime.dead = true;
  const walPath = path.join(path.dirname(host.hostConfigPath), 'native-local-wal.json');
  await writeFile(walPath, JSON.stringify({ requestId: 'mutation_wal', activationId: lease.activationId,
    characterId: character.id, baseRevision: 2, walSequence: 1, character: earned }), { mode: 0o600, flush: true });
  // Native local flush completed, but the process is interrupted before its HTTP mutation ACK.
  await host.close(); hosts.splice(hosts.indexOf(host), 1);
  host = await startNativeSiegeProofAuthority({ ...options, resume: true }); hosts.push(host);
  token = (await call('register', config.key)).data.token;
  const replayBody = JSON.parse(await readFile(walPath, 'utf8'));
  const replayed = await call('replay', token, replayBody);
  expect(replayed).toMatchObject({ status: 200, data: { revision: 3, walSequence: 1, recoveryPending: true, respawnPending: true } });
  expect((await call('replay', token, replayBody)).data.revision).toBe(3);
  const restored = await call('restore', token, { requestId: 'restore', characterId: character.id });
  expect(restored.data).toMatchObject({ character: earned, recoveryPending: true });
  expect((await call('restored', token, { requestId: 'restore_ack', characterId: character.id,
    revision: restored.data.revision })).status).toBe(200);
  expect(await readFile(ordinary, 'utf8')).toBe('ordinary owner journal');
  await expect(startNativeSiegeProofAuthority(options)).rejects.toThrow();
});

test('fresh and resumed fixtures reject changed dependencies rather than manufacturing content review', async () => {
  const fixture = await candidate(), options = { repositoryRoot: fixture.root, map: fixture.map, fixtureId: 'stale', engineRoot: fixture.engineRoot };
  const host = await startNativeSiegeProofAuthority(options); hosts.push(host);
  const config = JSON.parse(await readFile(host.hostConfigPath, 'utf8'));
  const send = async (route: string, credential: string, body = {}) => {
    const response = await fetch(`${host.server.httpUrl}/native/siege/${route}`, { method: 'POST',
      headers: { Authorization: `Bearer ${credential}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ hostId: config.hostId, ...body }) });
    return { status: response.status, ...await response.json() };
  };
  const token = (await send('register', config.key)).data.token;
  await writeFile(path.join(fixture.root, 'unreal/AegisWar/Content/OriginalCampaign.umap'), 'changed owner source');
  expect((await send('activate', token, { requestId: 'activate', rulesVersion: 2, contentRevision: fixture.cityRevision })).status).toBe(503);
  await host.close(); hosts.splice(hosts.indexOf(host), 1);
  await expect(startNativeSiegeProofAuthority({ ...options, resume: true })).rejects.toThrow(/dependency changed/);
  await expect(startNativeSiegeProofAuthority({ ...options, fixtureId: '../ordinary' })).rejects.toThrow(/identity/);
});

test('prepared campaign proof requires unchanged actual routing, services and live overlay bindings', async () => {
  const fixture = await candidate();
  expect(campaignCandidateContentEvidence(fixture.root, fixture.packages.map, fixture.engineRoot)).toMatchObject({ map: fixture.packages.map,
    mapSha256: fixture.hashes[fixture.packages.map], cityRevision: fixture.cityRevision });
  fixture.staged.manifest.zones[0].levels.live_siege = '/Game/OtherOverlay';
  await writeFile(path.join(fixture.receiptPath, 'publication-candidate.json'), JSON.stringify(fixture.staged));
  expect(() => campaignCandidateContentEvidence(fixture.root, fixture.packages.map, fixture.engineRoot)).toThrow(/bindings differ/);
});
