import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { validateNativeCampaignCharacter, validateNativeCharacterCheckpoint } from '../../shared/siege/character';
import { validateCapitalSiegeSnapshot, validateNativeCapitalSiegeLease } from '../../shared/siege/contract';
import type { CandidateSiegeContentEvidence } from './siege-content-evidence';
import { validateCitadelRecoveryCast, validateCitadelRuntimeEvolution } from './citadel-recovery-runtime';

export interface CitadelRecoveryFile { path: string; sha256: string }
export interface CitadelRecoveryEvidenceFiles {
  version: 1; nativeReport: CitadelRecoveryFile; mutations: CitadelRecoveryFile[]; recovered: CitadelRecoveryFile[];
  wals: CitadelRecoveryFile[]; configs: CitadelRecoveryFile[]; checkpoints: CitadelRecoveryFile[];
  http: CitadelRecoveryFile; processes: CitadelRecoveryFile;
}
export interface CitadelRecoveryBundle {
  report: any; nativeReport: any; mutations: any[]; recovered: any[]; wals: any[]; configs: any[];
  checkpoints: any[]; http: any; processes: any;
}
const FLAGS = ['productionAdmission', 'steamAdmission', 'humanPlaytest', 'visualApproval', 'fullSiegeAdmission',
  'releaseAcceptance', 'victoryAcceptance', 'conquestAcceptance'];
const NATIVE_FLAGS = [...FLAGS, 'progressionAcceptance', 'routeAcceptance'];
const hash = (value: string | Buffer) => createHash('sha256').update(value).digest('hex');
export const recoveryCanonical = (value: any): string => {
  if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Nonfinite recovery evidence number.');
  if (Array.isArray(value)) return '[' + value.map(v => v === undefined ? 'null' : recoveryCanonical(v)).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).filter(k => value[k] !== undefined).sort().map(k => JSON.stringify(k) + ':' + recoveryCanonical(value[k])).join(',') + '}';
  const result = JSON.stringify(value); if (result === undefined) throw new Error('Non-JSON recovery evidence value.'); return result;
};
const same = (a: any, b: any) => recoveryCanonical(a) === recoveryCanonical(b);
const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
const integer = (n: unknown, min = 0) => Number.isSafeInteger(n) && (n as number) >= min;
const hex = (value: unknown) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const receipt = (value: string) => value.replaceAll('-', '').toLowerCase();
const receipts = (value: any): string[] => {
  if (!Array.isArray(value) || value.some(v => typeof v !== 'string')) throw new Error('Missing complete runtime receipts.');
  const rows = value.map(receipt).sort();
  if (new Set(rows).size !== rows.length) throw new Error('Duplicate character transaction receipts.');
  return rows;
};
/** Epoch combat state is checked separately at every recovery/cast boundary below. */
function durable(character: any): any {
  validateNativeCampaignCharacter(character);
  const copy: any = structuredClone(character), runtime = copy.document.runtime;
  delete copy.returnPosition;
  for (const key of ['health', 'mana', 'abilities', 'capturedAtUnixMs', 'combat']) delete runtime[key];
  runtime.rewards = receipts(runtime.rewards); runtime.questKills = receipts(runtime.questKills);
  return copy;
}
function witness(row: any, character: any, returned: boolean): void {
  if (row?.characterId !== character.id || row.zone !== character.document.zone || row.normalized !== false
    || row.pending !== false || row.movementHeld !== false || row.member !== !returned || row.alive !== true || row.modelReady !== true
    || row.sceneReady !== true || row.physicalReady !== true || row.zoneMatches !== true || row.combatLevel !== 40
    || row.capsuleRadiusCm !== 42 || row.capsuleHalfHeightCm !== 96 || row.safeReturn !== returned
    || !Array.isArray(row.position) || row.position.length !== 3 || !row.position.every(finite)
    || !Array.isArray(row.validatedCenter) || row.validatedCenter.length !== 3 || !row.validatedCenter.every(finite)
    || Math.hypot(row.position[0] - row.validatedCenter[0], row.position[1] - row.validatedCenter[1]) > 1
    || Math.abs(row.position[2] - row.validatedCenter[2]) > 5 || !same(row.position, character.returnPosition)
    || character.document.runtime.dead !== false)
    throw new Error('Recovery requires actual normal character, model, floor and protected return witnesses.');
}
function ack(row: any, id: string, revision?: number, sequence?: number): boolean {
  return row?.forwarded === true && row.responseStatus === 200 && row.ack?.version === 1
    && row.ack.characterId === id && integer(row.ack.revision, 1) && typeof row.ack.recoveryPending === 'boolean'
    && (revision === undefined || row.ack.revision === revision) && (sequence === undefined || row.ack.walSequence === sequence);
}
export function validateCitadelCharacterRecovery(bundle: CitadelRecoveryBundle, expected: CandidateSiegeContentEvidence): void {
  const { report: r, nativeReport: native, configs, mutations, recovered, wals, checkpoints, http, processes } = bundle;
  const players = ['aegis', 'riftbound'].flatMap(realm => Array.from({ length: 18 }, (_, i) => `proof-${expected.signature.slice(0, 12)}-${realm}-${i}`));
  if (r?.schemaVersion !== 1 || r.passed !== true || r.recoveryOnly !== true || r.proofOnly !== true
    || r.contentReviewOverride !== true || !/^[a-z0-9][a-z0-9_-]{0,63}$/.test(r.fixtureId ?? '')
    || r.hostId !== `citadel-proof-${r.fixtureId}` || !same(r.players, players)
    || !/^\/Game\/WorldRebuild\/AegisCitadel_[a-f0-9]{12}\/CampaignCandidate$/.test(expected.map) || ['map', 'mapSha256', 'signature', 'cityRevision', 'geometrySignature'].some(k => r[k] !== expected[k as keyof CandidateSiegeContentEvidence])
    || r.normalCharacterRecoveryVerified !== true || ['outcomeRecoveryVerified', 'equipmentMutationVerified', 'deadIntentVerified', ...FLAGS].some(k => r[k] !== false)
    || configs.length !== 3 || checkpoints.length !== 3 || mutations.length !== 2 || recovered.length !== 2 || wals.length !== 2
    || !Array.isArray(r.cases) || r.cases.length !== 2 || !Array.isArray(r.http) || r.http.length !== 3
    || http?.schemaVersion !== 1 || http.fixtureId !== r.fixtureId || http.hostId !== r.hostId || !same(http.attempts, r.http)
    || processes?.schemaVersion !== 1 || processes.fixtureId !== r.fixtureId || processes.hostId !== r.hostId || processes.attempts?.length !== 3)
    throw new Error('Fresh three-process character recovery is incomplete, stale or claims broader acceptance.');
  const target = players[0], pids = new Set<number>(); let activation = '', previousEnd = 0;
  for (let attempt = 0; attempt < 3; attempt++) {
    const config = configs[attempt], setup = config.recovery, process = processes.attempts[attempt];
    if (!same(Object.fromEntries(Object.keys(expected).map(k => [k, config[k]])), expected)
      || config.proofOnly !== true || config.contentReviewOverride !== true || config.recoveryOnly !== true || !same(config.players, players)
      || setup?.version !== 1 || setup.attempt !== attempt || setup.fixtureId !== r.fixtureId
      || setup.binaryPath !== r.binaryPath || setup.binarySha256 !== r.binarySha256 || !same(setup.sourceHashes, r.sourceHashes)
      || setup.receiptA !== hash(`${r.fixtureId}:reward-a`).slice(0, 32) || setup.receiptB !== hash(`${r.fixtureId}:reward-b`).slice(0, 32)
      || !Array.isArray(setup.expected) || setup.expected.length !== attempt
      || process.attempt !== attempt || !integer(process.pid, 1) || pids.has(process.pid)
      || !finite(process.startedAt) || !finite(process.endedAt) || process.startedAt < previousEnd || process.endedAt <= process.startedAt
      || process.configSha256 !== r.evidence.configs[attempt].sha256
      || (attempt < 2 ? process.termination !== 'SIGKILL' || process.killRequested !== true || process.requestId !== r.cases[attempt].requestId
        || !(process.signalCode === 'SIGKILL' || integer(process.exitCode, 1))
        : process.termination !== 'normal_exit' || process.killRequested !== false || process.exitCode !== 0 || process.signalCode !== null))
      throw new Error('Recovery attempts do not bind three distinct owned native processes and exact configs.');
    pids.add(process.pid); previousEnd = process.endedAt;
    for (let index = 0; index < attempt; index++) {
      const binding = setup.expected[index];
      if (binding.sha256 !== r.evidence.mutations[index].sha256
        || !binding.path.replaceAll('\\', '/').endsWith(`/Saved/CitadelSiegeProof/${r.fixtureId}/attempt-${index}/mutation.json`))
        throw new Error('Native resume config does not bind the original mutation witnesses.');
    }
    const rows = r.http[attempt];
    if (!Array.isArray(rows) || !rows.length || rows.some((row: any, index: number) => row.index !== index
      || row.hostId !== r.hostId || !/^[a-z]+$/.test(row.route) || !hex(row.bodySha256) || typeof row.forwarded !== 'boolean'
      || row.characterSha256 !== undefined && !hex(row.characterSha256))) throw new Error('Actual private HTTP sequence is malformed.');
    if (rows.some((row: any) => row.route === 'restored' && row.returned === true))
      throw new Error('Recovery return requires a full current character checkpoint; a restore acknowledgement cannot release custody.');
    if (players.some(id => !rows.some((row: any) => row.route === 'membership' && row.action === 'join'
      && row.characterId === id && row.forwarded === true && row.responseStatus === 200 && hex(row.characterSha256))))
      throw new Error('Every native attempt requires all thirty-six actual approved character baselines.');
    const checkpoint = checkpoints[attempt], journal = checkpoint.state?.nativeSiegeJournal, entries = journal?.characters;
    if (!integer(checkpoint.revision, 1) || checkpoint.state?.id !== r.hostId || checkpoint.state.phase !== 'city'
      || checkpoint.state.results?.length !== 0 || !entries || Object.keys(entries).length !== 36)
      throw new Error('Recovery requires the actual unfinished private authority journal and all thirty-six full documents.');
    for (const id of players) {
      const record = entries[`${r.hostId}:${id}`]; validateNativeCharacterCheckpoint(record);
      if (record.hostId !== r.hostId || record.characterId !== id || record.realm !== (id.includes('-aegis-') ? 'aegis' : 'riftbound')
        || record.character.returnMap !== expected.map || activation && record.activationId !== activation)
        throw new Error('A recovered full document belongs to another identity or encounter.');
      activation ||= record.activationId;
    }
    const lease = journal.leases?.[activation];
    validateNativeCapitalSiegeLease(lease);
    if (!lease || !same(lease, checkpoint.state.zones?.aegis_capital?.nativeSiege) || lease.hostId !== r.hostId
      || lease.contentRevision !== expected.cityRevision || lease.result !== undefined || lease.snapshot.phase === 'finished')
      throw new Error('Character recovery cannot claim encounter settlement or replace its owning lease.');
  }
  for (let attempt = 0; attempt < 2; attempt++) {
    const c = r.cases[attempt], m = mutations[attempt], wal = wals[attempt], config = configs[attempt], reward = config.recovery[attempt ? 'receiptB' : 'receiptA'];
    if (c.mode !== (attempt ? 'after_commit' : 'before_commit') || c.nodeCommittedBeforeKill !== Boolean(attempt)
      || !integer(c.baseRevision, 1) || c.walSequence !== attempt + 1 || !/^[a-zA-Z0-9_-]{1,100}$/.test(c.requestId ?? '')
      || c.nodeRevision !== c.baseRevision + attempt || c.walSha256 !== r.evidence.wals[attempt].sha256
      || !hex(c.replayBodySha256) || c.nativeAckWithheld !== true || c.processKilled !== true
      || c.nativeMutationFileSha256 !== r.evidence.mutations[attempt].sha256 || !/^[^/\\]+\.json$/.test(c.walFilename ?? '')
      || m.schemaVersion !== 1 || m.attempt !== attempt || m.fixtureId !== r.fixtureId || m.mutationSucceeded !== true
      || ['map', 'mapSha256', 'signature', 'cityRevision'].some(k => m[k] !== r[k]) || m.configSha256 !== r.evidence.configs[attempt].sha256
      || receipt(m.receipt ?? '') !== reward || m.before?.id !== target || m.after?.id !== target
      || m.witness?.characterId !== target || m.witness.pending !== true || m.witness.movementHeld !== true || m.witness.normalized !== false)
      throw new Error('Both interruptions must bind actual successful native reward mutations and held original WAL files.');
    validateNativeCampaignCharacter(m.before); validateNativeCampaignCharacter(m.after);
    const cast=validateCitadelRecoveryCast(m.cast,m.after.document.runtime,target,m.after.realm);
    validateCitadelRuntimeEvolution(m.before.document.runtime,m.after.document.runtime);
    if (attempt) validateCitadelRuntimeEvolution(recovered[0].character.document.runtime,m.before.document.runtime,cast);
    const wanted = structuredClone(durable(m.before)), beforeInventory = wanted.document.inventory;
    beforeInventory.revision += 1; beforeInventory.characterProgression.xp += 25; beforeInventory.characterProgression.gold += 7;
    wanted.document.runtime.rewards = [...wanted.document.runtime.rewards, reward].sort();
    if (!same(wanted, durable(m.after)) || (attempt && !same(durable(m.before), durable(recovered[0].character))))
      throw new Error('Recovery reward changed or lost inventory, equipment, quests or receipt state.');
    if (wal.schemaVersion !== 1 || wal.hostId !== r.hostId || wal.body?.hostId !== r.hostId || wal.body.activationId !== activation
      || wal.body.characterId !== target || wal.body.requestId !== c.requestId || wal.body.baseRevision !== c.baseRevision
      || wal.body.walSequence !== c.walSequence || !same(wal.body.character, m.after)
      || m.wal?.filename!==c.walFilename || m.wal.sha256!==c.walSha256 || m.wal.requestId!==c.requestId
      || m.wal.baseRevision!==c.baseRevision || m.wal.walSequence!==c.walSequence) throw new Error('Actual flushed WAL differs from the native full character mutation.');
    const interrupted = r.http[attempt].find((row: any) => row.route === 'replay' && row.requestId === c.requestId);
    if (!interrupted || interrupted.characterSha256 !== hash(recoveryCanonical(m.after)) || interrupted.baseRevision !== c.baseRevision
      || interrupted.walSequence !== c.walSequence || interrupted.bodySha256 !== c.replayBodySha256 || (attempt ? !ack(interrupted, target, c.baseRevision + 1, c.walSequence)
        : interrupted.forwarded !== false || interrupted.responseStatus !== undefined || interrupted.ack !== undefined))
      throw new Error('HTTP witnesses do not prove the before-commit and committed-before-native-ACK boundaries.');
    const saved = checkpoints[attempt].state.nativeSiegeJournal.characters[`${r.hostId}:${target}`];
    if (saved.revision !== c.nodeRevision || saved.scope !== 'participant' || saved.returned !== false
      || (attempt ? saved.walSequence !== c.walSequence || !same(saved.character, m.after)
        : (saved.walSequence ?? 0) >= c.walSequence || !same(durable(saved.character), durable(m.before))))
      throw new Error('Interrupted canonical journal does not contain the actual selected CAS revision.');
    if (!attempt) validateCitadelRuntimeEvolution(saved.character.document.runtime,m.before.document.runtime,cast);
    const restored = recovered[attempt], nextRows = r.http[attempt + 1];
    if (restored.schemaVersion !== 1 || restored.attempt !== attempt + 1 || restored.fixtureId !== r.fixtureId
      || restored.map !== r.map || restored.signature !== r.signature || restored.configSha256 !== r.evidence.configs[attempt + 1].sha256
      || restored.heldObserved !== true || !same(durable(restored.character), durable(m.after)))
      throw new Error('Actual recovered native character lost persistent fields or its protection hold.');
    validateCitadelRuntimeEvolution(m.after.document.runtime,restored.character.document.runtime);
    witness(restored.witness, restored.character, false);
    const replay = nextRows.find((row: any) => row.route === 'replay' && row.requestId === c.requestId && ack(row, target, c.baseRevision + 1, c.walSequence));
    const restore = nextRows.find((row: any) => row.route === 'restore' && row.characterId === target && row.responseStatus === 200);
    const restoredAck = nextRows.find((row: any) => row.route === 'restored' && ack(row, target, c.baseRevision + 1, c.walSequence) && row.ack.recoveryPending === false);
    if (!replay || !restore || !restoredAck || !(replay.index < restore.index && restore.index < restoredAck.index))
      throw new Error('Original WAL replay, canonical restore and readiness ACK must occur in order.');
  }
  if (native.schemaVersion !== 1 || native.passed !== true || native.recoveryOnly !== true || native.proofOnly !== true
    || native.attempt !== 2 || native.fixtureId !== r.fixtureId || native.heldObserved !== true
    || ['map', 'mapSha256', 'cityRevision', 'signature'].some(k => native[k] !== r[k])
    || native.configSha256 !== r.evidence.configs[2].sha256 || !same(native.bindings, configs[2].recovery)
    || NATIVE_FLAGS.some(k => native[k] !== false) || native.characters?.length !== 36 || native.returnWitnesses?.length !== 36
    || new Set(native.characters.map((c: any) => c.id)).size !== 36 || new Set(native.returnWitnesses.map((w: any) => w.characterId)).size !== 36)
    throw new Error('Native final normal-return report is incomplete or claims broader recovery acceptance.');
  validateCapitalSiegeSnapshot(native.unfinishedSiege);
  if (native.unfinishedSiege.phase === 'finished' || native.unfinishedSiege.completed.includes(7)) throw new Error('Narrow character recovery cannot prove victory or defeat settlement.');
  const final = checkpoints[2].state, records = final.nativeSiegeJournal.characters;
  for (const id of players) {
    const actual = native.characters.find((c: any) => c.id === id), saved = records[`${r.hostId}:${id}`], initial = checkpoints[0].state.nativeSiegeJournal.characters[`${r.hostId}:${id}`].character;
    if (!actual || saved.scope !== 'evacuation' || saved.returned !== true || saved.recoveryPending !== false
      || saved.respawnPending !== false || !final.zones.aegis_capital.nativeSiege.safeEvacuationZones[actual.realm]?.includes(actual.document.zone)
      || !same(durable(saved.character), durable(actual))) throw new Error('Full normal return is not backed by the canonical owning-host safe-zone document.');
    validateCitadelRuntimeEvolution(saved.character.document.runtime,actual.document.runtime);
    witness(native.returnWitnesses.find((w: any) => w.characterId === id), actual, true);
    const expectedState = structuredClone(durable(id === target ? mutations[1].after : initial)); expectedState.document.zone = actual.document.zone;
    if (!same(expectedState, durable(actual))) throw new Error('Normal return lost complete inventory, equipment, quests or reward receipts.');
    validateCitadelRuntimeEvolution((id===target ? mutations[1].after : initial).document.runtime,actual.document.runtime);
    const rows = r.http[2], leave = rows.find((x: any) => x.route === 'membership' && x.characterId === id && x.action === 'leave' && x.forwarded && x.responseStatus === 200);
    const participant = rows.find((x: any) => x.route === 'checkpoint' && x.scope === 'participant' && x.returned === true && ack(x, id));
    const evacuation = rows.find((x: any) => x.route === 'checkpoint' && x.scope === 'evacuation' && x.returned !== true && ack(x, id));
    const returned = rows.find((x: any) => x.route === 'checkpoint' && x.scope === 'evacuation' && x.returned === true && ack(x, id, saved.revision, saved.walSequence ?? 0));
    if (!leave || !participant || !evacuation || !returned || !(leave.index < participant.index && participant.index < evacuation.index && evacuation.index < returned.index)
      || returned.characterSha256 !== hash(recoveryCanonical(saved.character)) || returned.ack.recoveryPending !== false)
      throw new Error('Participant leave, durable return, separate evacuation and safe returned full-document ACK must occur in order.');
  }
}

function confined(root: string, file: string): string {
  if (typeof file !== 'string' || !file || path.isAbsolute(file) || file.includes('\\')) throw new Error('Repository-relative recovery evidence path required.');
  const resolved = realpathSync(path.resolve(root, file)), relative = path.relative(realpathSync(root), resolved);
  if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Recovery evidence escaped repository confinement.');
  return resolved;
}
export function citadelCharacterRecoveryEvidence(repository: string, binding: CitadelRecoveryFile, expected: CandidateSiegeContentEvidence): CitadelRecoveryBundle {
  const load = (ref: CitadelRecoveryFile) => { const file = confined(repository, ref?.path); const bytes = readFileSync(file);
    if (!hex(ref.sha256) || hash(bytes) !== ref.sha256) throw new Error('Recovery evidence file changed.');
    return JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/, '')); };
  const report = load(binding), files: CitadelRecoveryEvidenceFiles = report.evidence;
  if (files?.version !== 1) throw new Error('Recovery requires fresh individually hash-bound process evidence.');
  const directory = path.join('artifacts/unreal/citadel-reference/recovery-proofs', report.fixtureId).replaceAll('\\', '/') + '/';
  const references = [binding, files.nativeReport, files.http, files.processes, ...(files.mutations ?? []), ...(files.recovered ?? []), ...(files.wals ?? []), ...(files.configs ?? []), ...(files.checkpoints ?? [])];
  if (references.length !== 16 || new Set(references.map(ref => ref?.path)).size !== 16) throw new Error('Recovery requires sixteen distinct owned evidence files.');
  for (const ref of references)
    if (!ref?.path.startsWith(directory) || ref.path.slice(directory.length).includes('/')) throw new Error('Recovery evidence belongs to another owned run.');
  const binary = path.join(repository, 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll');
  if (path.resolve(report.binaryPath ?? '') !== path.resolve(binary) || hash(readFileSync(binary)) !== report.binarySha256) throw new Error('Recovery compiled binary is stale.');
  const sourceRoot = path.join(repository, 'unreal/AegisWar/Source');
  const nativeFiles = (directory: string): string[] => readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory()
    ? nativeFiles(path.join(directory, entry.name)) : /\.(cpp|h|cs)$/.test(entry.name) ? [path.join(directory, entry.name)] : []);
  const actual = nativeFiles(sourceRoot).sort();
  if (!report.sourceHashes || !['WarCitadelSiegeProof.cpp', 'WarCampaignSiegeSubsystem.cpp'].every(name => actual.includes(path.join(sourceRoot, 'AegisWar/Private', name)))
    || actual.length > 1024 || !same(actual, Object.keys(report.sourceHashes).sort())
    || actual.some(file => path.relative(realpathSync(sourceRoot), realpathSync(file)).startsWith('..') || hash(readFileSync(file)) !== report.sourceHashes[file]))
    throw new Error('Recovery must bind every current native source file.');
  if (!/^\/Game\/WorldRebuild\/AegisCitadel_[a-f0-9]{12}\/CampaignCandidate$/.test(expected.map)
    || hash(readFileSync(path.join(repository, 'unreal/AegisWar/Content', expected.map.slice(6) + '.umap'))) !== expected.mapSha256)
    throw new Error('Recovery actual campaign map is stale.');
  const bundle: CitadelRecoveryBundle = { report, nativeReport: load(files.nativeReport), mutations: files.mutations.map(load),
    recovered: files.recovered.map(load), wals: files.wals.map(load), configs: files.configs.map(load),
    checkpoints: files.checkpoints.map(load), http: load(files.http), processes: load(files.processes) };
  validateCitadelCharacterRecovery(bundle, expected); return bundle;
}
