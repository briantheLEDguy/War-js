import { createHash, randomUUID } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, expect, test } from 'vitest';
import { scenarioCandidateFixture } from './fixtures/scenarioCandidate';
import { requireSameScenarioCandidate, requireScenarioCandidateJournal, scenarioCandidateProof, scenarioCandidateProofDirectory } from '../server/scenarios/candidate-proof';
import { startScenarioHost } from '../server/scenarios/host';
import { scenarioMenuClientArguments } from '../scripts/unreal/scenario-menu-proof';
import { requireScenarioCandidateMenuReport, requireScenarioCandidateQueueJournal, scenarioCandidateQueueEvidence, verifyScenarioInitialBots } from '../scripts/unreal/scenario-proof-evidence';
import type { ScenarioJournal } from '../shared/scenarios/types';

const roots: string[] = [];
const hosts: Awaited<ReturnType<typeof startScenarioHost>>[] = [];
afterEach(async () => { for (const host of hosts.splice(0)) await host.close(); for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true }); });
function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'war-scenario-candidate-')); roots.push(root);
  const candidate = scenarioCandidateFixture(root), options = { repositoryRoot: root, map: candidate.map, fixtureId: randomUUID(), engineRoot: candidate.engineRoot };
  return { root, candidate, options, directory: scenarioCandidateProofDirectory(options) };
}
function nativeReport(proof: ReturnType<typeof scenarioCandidateProof>, match = randomUUID()) {
  return { passed: true, queueReturnVerified: true, reconnectVerified: false, releaseApproved: false, fullSiegeStagesVerified: false, humanPlaytest: false,
    candidateProof: { ...proof, configSha256: 'c'.repeat(64), actualMap: proof.map, actualCityDefinition: proof.cityDefinition,
      actualCityRevision: proof.cityRevision, match, realm: 'aegis', coordinatorRecoveryVerified: false,
      normalizedDuringMatch: true, normalizedAfterReturn: false, transientReviewOverride: true } };
}
function journal(proof: ReturnType<typeof scenarioCandidateProof>, matchId: string): ScenarioJournal {
  return { version: 1, parties: {}, invites: {}, queue: [], tickets: {},
    players: { human: { character: { id: 'human', name: 'Fixture', realm: 'aegis', visual: '/Game/Reviewed', returnMap: '/Game/World', returnPosition: [1, 2, 3], document: {} },
      token: 'private token fixture', party: 'party', phase: 'idle', message: '', possessionReleased: true, departurePrepared: true, campaignReleased: true } },
    matches: { [matchId]: { id: matchId, scenario: 'lower_city', definition: structuredClone(proof.definition), members: ['human'], accepted: ['human'],
      parties: [{ party: 'party', scenario: 'lower_city', since: 1000 }], deadline: 61_000, started: 32_000, phase: 'finished', serverKey: 'private fixture key' } } };
}

test('isolated candidate authority retains the real public id and immutable normalized 18v18 rules', async () => {
  const f = fixture();
  const host = await startScenarioHost({ directory: f.directory, executable: 'unused', project: f.candidate.project, port: 0,
    bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false, candidateProof: f.options }); hosts.push(host);
  expect(host.coordinator.definition('lower_city')).toMatchObject({ id: 'lower_city', map: f.candidate.map, capacity: 18,
    gatherMs: 30_000, acceptMs: 30_000, reconnectMs: 120_000, rulesVersion: 2, battlefield: 'FullSiege', contentRevision: f.candidate.cityRevision });
  expect(host.candidateProof).toMatchObject({ proofOnly: true, statsMode: 'scenario', productionAdmission: false, steamAdmission: false, territorialAcceptance: false });
  const url = `http://127.0.0.1:${(host.server.address() as import('node:net').AddressInfo).port}`;
  const key = readFileSync(path.join(f.directory, 'control-key'), 'utf8');
  const response = await fetch(url + '/host/register', { method: 'POST', headers: { Authorization: 'Bearer ' + key, 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: 'native-character', name: 'Native fixture', realm: 'aegis', visual: '/Game/Reviewed', returnMap: '/Game/World', returnPosition: [1, 2, 3], document: { inventory: { gold: 42 } } }) });
  expect(response.status).toBe(200);
  const token = (await response.json()).data.token;
  const view = await (await fetch(url + '/status', { headers: { Authorization: 'Bearer ' + token } })).json();
  expect(view.data.catalog[0].map).toBe(f.candidate.map);
  expect(JSON.stringify(view)).not.toContain(key);
  expect(JSON.stringify(view)).not.toContain('candidateReceiptPath');
});

test('candidate proof cannot adopt ordinary authority storage, LAN or a published map', async () => {
  const f = fixture();
  const base = { executable: 'unused', project: f.candidate.project, port: 0, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false, candidateProof: f.options };
  await expect(startScenarioHost({ ...base, directory: path.join(f.root, 'ordinary') })).rejects.toThrow(/isolated/);
  await expect(startScenarioHost({ ...base, directory: f.directory, allowLan: true })).rejects.toThrow(/loopback/);
  expect(() => scenarioCandidateProof({ ...f.options, map: '/Game/Capitals/Siege/AegisCapital_Siege' })).toThrow(/exact isolated/);
  mkdirSync(f.directory, { recursive: true }); writeFileSync(path.join(f.directory, 'journal.json'), '{}');
  await expect(startScenarioHost({ ...base, directory: f.directory })).rejects.toThrow(/existing authority/);
});

test('same private identity can restart while changed binary, source, receipt or catalog is rejected', async () => {
  const f = fixture(), proof = scenarioCandidateProof(f.options);
  const base = { directory: f.directory, executable: 'unused', project: f.candidate.project, port: 0, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false, candidateProof: f.options };
  let host = await startScenarioHost(base); await host.close();
  host = await startScenarioHost(base); await host.close();
  await expect(startScenarioHost({ ...base, candidateProof: undefined })).rejects.toThrow(/cannot become an ordinary/);
  const file = path.join(f.root, 'unreal/AegisWar/Source/AegisWar/Private/WarScenarioInstance.cpp'), old = readFileSync(file);
  writeFileSync(file, 'changed native source'); expect(() => requireSameScenarioCandidate(f.options, proof)).toThrow(/changed/); writeFileSync(file, old);
  writeFileSync(f.candidate.binary, 'new native DLL'); expect(() => requireSameScenarioCandidate(f.options, proof)).toThrow(/changed/);
  await expect(startScenarioHost(base)).rejects.toThrow(/identity changed/);
});

test('historical or foreign saved matches are rejected rather than rebound to the proof', () => {
  const f = fixture(), proof = scenarioCandidateProof(f.options), id = randomUUID(), saved = journal(proof, id);
  expect(() => requireScenarioCandidateJournal(saved, proof)).not.toThrow();
  delete saved.matches[id].definition; expect(() => requireScenarioCandidateJournal(saved, proof)).toThrow(/historical/);
  saved.matches[id].definition = { ...proof.definition, capacity: 6, rulesVersion: 1, battlefield: 'LowerCity' };
  expect(() => requireScenarioCandidateJournal(saved, proof)).toThrow(/historical/);
});

test('native entry evidence rejects a canonical map, changed city, missing normalization or invented approvals', () => {
  const f = fixture(), proof = scenarioCandidateProof(f.options), good = nativeReport(proof);
  expect(requireScenarioCandidateMenuReport(good, proof, 'c'.repeat(64), { realm: 'aegis', reconnect: false, recovery: false })).toBe(good.candidateProof.match);
  for (const change of [{ actualMap: '/Game/Capitals/Siege/AegisCapital_Siege' }, { actualCityRevision: 'd'.repeat(64) },
    { normalizedDuringMatch: false }, { normalizedAfterReturn: true }, { productionAdmission: true }, { configSha256: 'e'.repeat(64) }]) {
    const bad = structuredClone(good); Object.assign(bad.candidateProof, change);
    expect(() => requireScenarioCandidateMenuReport(bad, proof, 'c'.repeat(64), { realm: 'aegis', reconnect: false, recovery: false })).toThrow(/incomplete/);
  }
  expect(() => requireScenarioCandidateMenuReport({ ...good, fullSiegeStagesVerified: true }, proof, 'c'.repeat(64), { realm: 'aegis', reconnect: false, recovery: false })).toThrow();
});

test('durable gather and campaign return are required in addition to normal empty-seat bot fill', () => {
  const f = fixture(), proof = scenarioCandidateProof(f.options), id = randomUUID(), saved = journal(proof, id);
  expect(() => requireScenarioCandidateQueueJournal(saved, proof, id, 'aegis')).not.toThrow();
  saved.matches[id].parties[0].since = 1001; expect(() => requireScenarioCandidateQueueJournal(saved, proof, id, 'aegis')).toThrow(/gather/);
  saved.matches[id].parties[0].since = 1000; saved.players.human.phase = 'return';
  expect(() => requireScenarioCandidateQueueJournal(saved, proof, id, 'aegis')).toThrow(/campaign return/);
  saved.players.human.phase = 'idle'; saved.players.human.possessionReleased = undefined;
  expect(() => requireScenarioCandidateQueueJournal(saved, proof, id, 'aegis')).toThrow(/campaign return/);
  saved.players.human.possessionReleased = true; saved.matches[id].accepted = [];
  expect(() => requireScenarioCandidateQueueJournal(saved, proof, id, 'aegis')).toThrow(/allocation contract/);
  expect(() => verifyScenarioInitialBots('WAR_SCENARIO_TEAM realm=1 humans=1 bots=17\nWAR_SCENARIO_TEAM realm=2 humans=0 bots=18', { aegis: 1, riftbound: 0 })).not.toThrow();
  expect(() => verifyScenarioInitialBots('WAR_SCENARIO_TEAM realm=1 humans=1 bots=17', { aegis: 1, riftbound: 0 })).toThrow(/both realms/);
});

test('candidate client invokes the actual frontend menu and carries only its exact private proof config', () => {
  const options = { project: 'project', id: randomUUID(), realm: 'aegis', hostConfig: 'host.json', log: 'proof.log', hold: 2 };
  const normal = scenarioMenuClientArguments(options), candidate = scenarioMenuClientArguments({ ...options, candidateProofConfig: 'candidate-proof.json', reconnect: true });
  expect(normal).not.toContain('-WarScenarioCandidateProofConfig=candidate-proof.json');
  expect(candidate).toContain('-WarScenarioCandidateProofConfig=candidate-proof.json');
  expect(candidate).toContain('-WarScenarioProofReconnect');
  expect(candidate).toContain('-WarDevelopmentNetworking');
  expect(normal).not.toContain('-WarDevelopmentNetworking');
  expect(candidate.some(arg => arg.startsWith('/Game/'))).toBe(false);
  expect(() => scenarioMenuClientArguments({ ...options, realm: 'foreign' })).toThrow();
});

test('sealed queue evidence binds each actual file and refuses stale captures, incomplete return or broader claims', () => {
  const f = fixture(), proof = scenarioCandidateProof(f.options), id = randomUUID();
  const output = path.dirname(f.directory), clientDirectory = path.join(output, 'client-' + randomUUID());
  const save = (filename: string, bytes: string | Buffer) => { mkdirSync(path.dirname(filename), { recursive: true }); writeFileSync(filename, bytes);
    return { path: path.relative(f.root, filename).replaceAll(path.sep, '/'), sha256: createHash('sha256').update(bytes).digest('hex') }; };
  const candidateProof = save(path.join(f.directory, 'candidate-proof.json'), JSON.stringify(proof));
  const saved = journal(proof, id), journalBinding = save(path.join(f.directory, 'journal.json'), JSON.stringify(saved));
  const native = nativeReport(proof, id); native.candidateProof.configSha256 = candidateProof.sha256;
  const nativeBinding = save(path.join(clientDirectory, 'report.json'), JSON.stringify(native));
  const serverLog = save(path.join(f.directory, 'instances', id, 'server.log'), 'WAR_SCENARIO_TEAM realm=1 humans=1 bots=17\nWAR_SCENARIO_TEAM realm=2 humans=0 bots=18');
  // Header-only portable bytes exercise file guards, and are explicitly not real native screenshots.
  const png = Buffer.alloc(24); Buffer.from('89504e470d0a1a0a', 'hex').copy(png); png.writeUInt32BE(1280, 16); png.writeUInt32BE(720, 20);
  const names = ['login', 'capital', 'queue', 'offer', 'combat', 'hold', 'returned'];
  const report = { schemaVersion: 1, fixtureId: proof.fixtureId, map: proof.map, mapSha256: proof.mapSha256, signature: proof.signature, cityRevision: proof.cityRevision,
    proofOnly: true, queueReturnVerified: true, reconnectVerified: false, coordinatorRecoveryVerified: false, partyVerified: false, simultaneousInstancesVerified: false,
    releaseApproved: false, fullSiegeStagesVerified: false, humanPlaytest: false, productionAdmission: false, steamAdmission: false, territorialAcceptance: false, freshGeometryAdmission: false,
    candidateProof, journal: journalBinding, clients: [{ realm: 'aegis', match: id, nativeReport: nativeBinding, serverLog,
      captures: names.map(name => save(path.join(clientDirectory, name + '.png'), png)) }] };
  const reportPath = path.join(output, 'report.json'), check = () => scenarioCandidateQueueEvidence(f.root, f.candidate.map, reportPath, f.candidate.engineRoot);
  const write = () => writeFileSync(reportPath, JSON.stringify(report)); write();
  expect(check).not.toThrow();
  report.fullSiegeStagesVerified = true; write(); expect(check).toThrow(/claimed scope/);
  report.fullSiegeStagesVerified = false; write();
  writeFileSync(path.join(clientDirectory, 'combat.png'), 'changed capture'); expect(check).toThrow(/bytes changed/);
  writeFileSync(path.join(clientDirectory, 'combat.png'), png);
  const lost = report.clients[0].captures.pop()!; write(); expect(check).toThrow(/capture sequence/);
  report.clients[0].captures.push(lost); write();
  saved.players.human.phase = 'return'; report.journal = save(path.join(f.directory, 'journal.json'), JSON.stringify(saved)); write();
  expect(check).toThrow(/campaign return/);
});
