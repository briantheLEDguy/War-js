import type { ScenarioRealm } from '../../shared/scenarios/types';
import type { ScenarioJournal } from '../../shared/scenarios/types';
import { scenarioProofCanonical, type ScenarioCandidateProof } from '../../server/scenarios/candidate-proof';
import { createHash } from 'node:crypto';
import { readFileSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { scenarioCandidateProof } from '../../server/scenarios/candidate-proof';

export interface ScenarioCandidateMenuMode { realm: ScenarioRealm; reconnect: boolean; recovery: boolean }

/** A native menu witness proves entry and return only; full stage outcomes remain a separate fixture. */
export function requireScenarioCandidateMenuReport(report: any, proof: ScenarioCandidateProof,
  configSha256: string, mode: ScenarioCandidateMenuMode): string {
  const actual = report?.candidateProof;
  if (!/^[a-f0-9]{64}$/.test(configSha256) || report?.passed !== true || report.queueReturnVerified !== true
    || report.reconnectVerified !== mode.reconnect || report.releaseApproved !== false
    || report.fullSiegeStagesVerified !== false || report.humanPlaytest !== false || !actual
    || ['fixtureId', 'map', 'mapSha256', 'signature', 'geometrySignature', 'cityRevision', 'cityDefinition',
      'scenario', 'capacity', 'rulesVersion', 'battlefield', 'statsMode'].some(key => actual[key] !== (proof as any)[key])
    || actual.configSha256 !== configSha256 || actual.actualMap !== proof.map
    || actual.actualCityDefinition !== proof.cityDefinition || actual.actualCityRevision !== proof.cityRevision
    || actual.normalizedDuringMatch !== true || actual.normalizedAfterReturn !== false
    || actual.proofOnly !== true || actual.transientReviewOverride !== true
    || actual.productionAdmission !== false || actual.steamAdmission !== false || actual.territorialAcceptance !== false
    || actual.releaseApproved !== undefined && actual.releaseApproved !== false
    || actual.realm !== mode.realm || actual.coordinatorRecoveryVerified !== mode.recovery
    || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(actual.match ?? ''))
    throw new Error('Native candidate queue entry/normalization/return is incomplete, stale, or claims unverified admission.');
  return actual.match;
}

/** Match timing and capacity come from the durable authority, rather than a capture label. */
export function requireScenarioCandidateQueueJournal(journal: ScenarioJournal, proof: ScenarioCandidateProof,
  matchId: string, realm: ScenarioRealm): void {
  const match = journal?.matches?.[matchId];
  if (journal?.version !== 1 || !match || match.scenario !== 'lower_city' || !match.definition
    || scenarioProofCanonical(match.definition) !== scenarioProofCanonical(proof.definition)
    || !['running', 'finished'].includes(match.phase) || !Number.isFinite(match.started)
    || !match.members.length || new Set(match.members).size !== match.members.length || !match.parties.length
    || !Array.isArray(match.accepted) || new Set(match.accepted).size !== match.members.length
    || match.members.some(id => !match.accepted.includes(id)))
    throw new Error('Candidate queue evidence lacks the exact durable allocation contract.');
  const counts = { aegis: 0, riftbound: 0 };
  for (const id of match.members) {
    const player = journal.players[id], side = player?.character?.realm;
    if (!player || !['aegis', 'riftbound'].includes(side) || player.phase !== 'idle' || player.match !== undefined
      || player.possessionReleased !== true || player.departurePrepared !== true || player.campaignReleased !== true || player.character.id !== id)
      throw new Error('Candidate scenario members have not acknowledged their actual campaign return.');
    counts[side]++;
  }
  if (counts.aegis > 18 || counts.riftbound > 18 || counts[realm] < 1)
    throw new Error('Candidate scenario capacity or observed realm is invalid.');
  const offerAt = match.deadline - match.definition.acceptMs;
  if (!Number.isFinite(offerAt) || match.started! < offerAt
    || match.parties.some(entry => !Number.isFinite(entry.since) || entry.scenario !== 'lower_city' || entry.since > offerAt)
    || (counts.aegis < 18 || counts.riftbound < 18)
      && offerAt - Math.min(...match.parties.map(entry => entry.since)) < match.definition.gatherMs)
    throw new Error('The ordinary thirty-second gather was not observed.');
}

export function verifyScenarioInitialBots(log: string, counts: Record<ScenarioRealm, number>, capacity = 18): void {
  if (capacity !== 18 || Object.values(counts).some(count => !Number.isInteger(count) || count < 0 || count > capacity)
    || counts.aegis + counts.riftbound < 1) throw new Error('An actual bounded candidate match roster is required.');
  for (const realm of ['aegis', 'riftbound'] as const)
    if (!new RegExp(`WAR_SCENARIO_TEAM realm=${realm === 'aegis' ? 1 : 2} humans=${counts[realm]} bots=${capacity - counts[realm]}\\b`).test(log))
      throw new Error('Normal 18v18 empty-seat bot fill was not observed for both realms.');
}

/** Recheck real files and current candidate bytes; this receipt cannot stand in for full siege outcomes. */
export function scenarioCandidateQueueEvidence(repository: string, map: string, reportPath: string, engineRoot?: string) {
  const document = JSON.parse(readFileSync(reportPath, 'utf8').replace(/^\uFEFF/, ''));
  const proof = scenarioCandidateProof({ repositoryRoot: repository, map, fixtureId: document.fixtureId, engineRoot });
  const directory = realpathSync(path.join(repository, 'artifacts/unreal/scenario-menu', proof.fixtureId));
  if (realpathSync(reportPath) !== path.join(directory, 'report.json') || document.schemaVersion !== 1
    || ['map', 'mapSha256', 'signature', 'cityRevision'].some(key => document[key] !== (proof as any)[key])
    || document.proofOnly !== true || document.queueReturnVerified !== true
    || ['releaseApproved', 'fullSiegeStagesVerified', 'humanPlaytest', 'productionAdmission', 'steamAdmission',
      'territorialAcceptance', 'freshGeometryAdmission'].some(key => document[key] !== false)
    || ['reconnectVerified', 'coordinatorRecoveryVerified', 'partyVerified', 'simultaneousInstancesVerified']
      .some(key => typeof document[key] !== 'boolean')
    || !Array.isArray(document.clients) || !document.clients.length || document.clients.length > 2)
    throw new Error('Private queue proof binding or claimed scope is invalid.');
  const file = (binding: any, expected?: string) => {
    if (!binding || typeof binding.path !== 'string' || !/^[a-f0-9]{64}$/.test(binding.sha256)
      || binding.path.includes('\\') || path.isAbsolute(binding.path) || binding.path.split('/').some((p: string) => !p || p === '.' || p === '..'))
      throw new Error('Invalid private queue evidence file binding.');
    const filename = realpathSync(path.resolve(repository, binding.path)), relative = path.relative(directory, filename);
    if (!relative || relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)
      || expected && filename !== path.join(directory, expected)) throw new Error('Private queue evidence escaped its fixture.');
    const bytes = readFileSync(filename);
    if (createHash('sha256').update(bytes).digest('hex') !== binding.sha256) throw new Error('Private queue evidence bytes changed.');
    return bytes;
  };
  const config = JSON.parse(file(document.candidateProof, 'host/candidate-proof.json').toString('utf8'));
  if (scenarioProofCanonical(config) !== scenarioProofCanonical(proof)) throw new Error('Private queue config changed from the actual candidate.');
  const journal = JSON.parse(file(document.journal, 'host/journal.json').toString('utf8')) as ScenarioJournal;
  const seen = new Set<string>();
  for (const client of document.clients) {
    const native = JSON.parse(file(client.nativeReport).toString('utf8').replace(/^\uFEFF/, ''));
    if (!['aegis', 'riftbound'].includes(client.realm)) throw new Error('Private queue client realm is invalid.');
    const mode = { realm: client.realm as ScenarioRealm, reconnect: document.reconnectVerified, recovery: document.coordinatorRecoveryVerified };
    const match = requireScenarioCandidateMenuReport(native, proof, document.candidateProof.sha256, mode);
    if (match !== client.match || seen.has(client.nativeReport.path)) throw new Error('Private queue native client identity is duplicated or mismatched.');
    seen.add(client.nativeReport.path);
    requireScenarioCandidateQueueJournal(journal, proof, match, mode.realm);
    const roster = journal.matches[match].members.reduce((counts, id) => { counts[journal.players[id].character.realm]++; return counts; }, { aegis: 0, riftbound: 0 });
    const serverLog = file(client.serverLog, `host/instances/${match}/server.log`).toString('utf8');
    verifyScenarioInitialBots(serverLog, roster);
    if (mode.reconnect) verifyScenarioReconnectBots(serverLog, mode.realm, proof.capacity);
    const required = ['login', 'capital', 'queue', 'offer', 'combat', 'hold', 'returned',
      ...(mode.reconnect ? ['before-disconnect', 'reconnect', 'reconnected'] : []), ...(mode.recovery ? ['await-recovery'] : [])];
    if (!Array.isArray(client.captures) || client.captures.length !== required.length
      || new Set(client.captures.map((capture: any) => capture.path)).size !== required.length)
      throw new Error('Private queue capture sequence is incomplete.');
    const nativeDirectory = path.posix.dirname(client.nativeReport.path);
    for (const name of required) {
      const capture = client.captures.find((row: any) => row.path === nativeDirectory + '/' + name + '.png');
      const bytes = file(capture);
      if (bytes.length < 24 || bytes.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a'
        || bytes.readUInt32BE(16) < 1 || bytes.readUInt32BE(20) < 1) throw new Error('Private queue capture is not a rendered PNG file.');
    }
  }
  if (document.partyVerified && (document.clients.length !== 2 || new Set(document.clients.map((c: any) => c.match)).size !== 1)
    || document.simultaneousInstancesVerified && new Set(document.clients.map((c: any) => c.match)).size !== 2)
    throw new Error('Private queue party or independent instance binding is incomplete.');
  return { ...proof, queueReturnVerified: true, reconnectVerified: document.reconnectVerified,
    coordinatorRecoveryVerified: document.coordinatorRecoveryVerified, fullSiegeStagesVerified: false };
}

/** Counts come from the immutable match definition, including resumed historical rounds. */
export function verifyScenarioReconnectBots(log: string, realm: ScenarioRealm, capacity: number): void {
  if (!['aegis', 'riftbound'].includes(realm) || !Number.isInteger(capacity) || ![6, 18].includes(capacity))
    throw new Error('An explicit recorded scenario capacity and realm are required.');
  const team = `WAR_SCENARIO_TEAM realm=${realm === 'aegis' ? 1 : 2}`;
  const replacement = new RegExp(`${team} humans=1 bots=${capacity - 1}\\b[\\s\\S]*`
    + `${team} humans=0 bots=${capacity}\\b[\\s\\S]*${team} humans=1 bots=${capacity - 1}\\b`);
  if (!replacement.test(log)) throw new Error('Temporary bot substitution and removal were not observed during reconnect.');
}
