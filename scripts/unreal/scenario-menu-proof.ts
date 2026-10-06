import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync, writeFileSync } from 'node:fs';
import { spawn, type ChildProcess } from 'node:child_process';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';
import { startScenarioHost } from '../../server/scenarios/host';
import { requireScenarioCandidateMenuReport, requireScenarioCandidateQueueJournal, scenarioCandidateQueueEvidence, verifyScenarioReconnectBots } from './scenario-proof-evidence';
import { requireSameScenarioCandidate, scenarioCandidateProof, type ScenarioCandidateProofOptions } from '../../server/scenarios/candidate-proof';
import type { ScenarioRealm } from '../../shared/scenarios/types';

export interface ScenarioMenuClientOptions {
  project: string; id: string; realm: string; hostConfig: string; log: string; hold: number;
  connectionRetry?: boolean; party?: string; recovery?: boolean; reconnect?: boolean; candidateProofConfig?: string;
}
export function scenarioMenuClientArguments(options: ScenarioMenuClientOptions): string[] {
  if (!['aegis', 'riftbound'].includes(options.realm) || !Number.isFinite(options.hold) || options.hold < 0
    || options.party && !['leader', 'member'].includes(options.party)) throw new Error('Invalid native menu proof options.');
  // Start at the normal frontend/capital; only the trusted dedicated allocation uses the candidate map.
  return [options.project, '-game', '-unattended', '-nop4', '-nosound', '-nosplash',
    '-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1280', '-ResY=720', '-WarScenarioMenuProof',
    `-WarScenarioMenuRun=${options.id}`, `-WarScenarioProofRealm=${options.realm}`, `-WarScenarioHostConfig=${options.hostConfig}`,
    ...(options.candidateProofConfig ? ['-WarDevelopmentNetworking', `-WarScenarioCandidateProofConfig=${options.candidateProofConfig}`] : []),
    ...(options.connectionRetry ? ['-WarScenarioProofConnectionRetry'] : []),
    ...(options.party ? [`-WarScenarioProofParty=${options.party}`] : []), `-WarScenarioProofHold=${options.hold}`,
    ...(options.recovery ? ['-WarScenarioProofRecovery'] : []), ...(options.reconnect ? ['-WarScenarioProofReconnect'] : []),
    '-ExecCmds=t.MaxFPS 30', `-abslog=${options.log}`];
}

export async function scenarioMenuProofMain(rawArgs = process.argv.slice(2)): Promise<void> {
const args = parseArguments(rawArgs, ['--connection-retry', '--recovery', '--party', '--instances', '--reconnect', '--dry-run'],
  ['--realm', '--map', '--engine-root']);
const cases = ['--connection-retry', '--recovery', '--party', '--instances'].filter(flag => args.has(flag));
if (cases.length > 1 || args.has('--reconnect') && cases.length || args.has('--map') && args.has('--connection-retry'))
  throw new Error('Run queue, reconnect, party, coordinator recovery and connection retry as separate truthful cases.');

const engineRoot = args.get('--engine-root') ?? defaultEngineRoot();
const engine = inspectToolchain(engineRoot);
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID(), output = path.join(repoRoot, 'artifacts/unreal/scenario-menu', run);
const candidateOptions: ScenarioCandidateProofOptions | undefined = args.has('--map')
  ? { repositoryRoot: repoRoot, map: args.get('--map')!, fixtureId: run, engineRoot } : undefined;
if (args.has('--dry-run')) {
  const proof = candidateOptions ? scenarioCandidateProof(candidateOptions) : undefined;
  console.log(JSON.stringify({ dryRun: true, map: proof?.map, cityRevision: proof?.cityRevision,
    capacity: proof?.capacity, rulesVersion: proof?.rulesVersion, productionAdmission: false,
    steamAdmission: false, territorialAcceptance: false, fullSiegeStagesVerified: false, nativeRun: false }));
  return;
}
mkdirSync(output, { recursive: true });
const directory = path.join(output, 'host');
const connectionRetry = args.has('--connection-retry');
let host = await startScenarioHost({ directory, executable: engine.editorCommand, project: projectPath,
  port: 0, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false, candidateProof: candidateOptions });
let hostOpen = true;
async function stopHost() { if (hostOpen) { hostOpen = false; await host.close(); } }
const realms = args.has('--realm') ? [args.get('--realm')!] : ['aegis', 'riftbound'];
const children: ChildProcess[] = [];
const proofFolders: string[] = [];
const candidateReports: { realm: string; match: string; nativeReport: { path: string; sha256: string }; serverLog: { path: string; sha256: string }; captures: { path: string; sha256: string }[] }[] = [];
const fileEvidence = (file: string) => ({ path: path.relative(repoRoot, file).replaceAll(path.sep, '/'),
  sha256: createHash('sha256').update(readFileSync(file)).digest('hex') });
let overlappingInstances = false;
const observer = setInterval(() => {
  const occupied = Object.values(host.coordinator.state.matches).filter(match => match.phase === 'running'
    && match.members.some(id => host.coordinator.player(id).phase === 'playing'));
  overlappingInstances ||= occupied.length >= 2;
}, 250);
async function client(realm: string, party = '', hold = 2, recovery = false) {
    if (!['aegis', 'riftbound'].includes(realm)) throw new Error('Unknown proof realm');
    const id = randomUUID(), proof = path.join(repoRoot, 'unreal/AegisWar/Saved/ScenarioMenuProof', id.replaceAll('-', ''));
    proofFolders.push(proof);
    const child = spawn(engine.editorCommand!, scenarioMenuClientArguments({ project: projectPath, id, realm,
      hostConfig: path.join(directory, connectionRetry ? 'retry-host.json' : 'host.json'),
      log: path.join(output, `${realm}${party}.log`), hold, connectionRetry, party, recovery,
      reconnect: args.has('--reconnect'), candidateProofConfig: host.candidateProofPath }), { windowsHide: true, stdio: 'ignore' });
    children.push(child);
    const timer = setTimeout(() => child.kill(), 650_000);
    const code = await new Promise<number | null>((resolve, reject) => { child.once('error', reject); child.once('exit', resolve); });
    clearTimeout(timer);
    const file = path.join(proof, 'report.json');
    if (code !== 0 || !existsSync(file)) throw new Error(`Scenario queue proof failed: ${output}; ${proof}`);
    const report = JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
    if (!report.passed || report.releaseApproved !== false) throw new Error(JSON.stringify(report));
    for (const name of connectionRetry ? ['login', 'capital', 'host-missing', 'host-unavailable', 'connected'] : ['login', 'capital', 'queue', 'offer', 'combat', 'hold', 'returned'])
      if (!existsSync(path.join(proof, `${name}.png`))) throw new Error(`Missing capture ${name}`);
    if (args.has('--reconnect')) for (const name of ['before-disconnect', 'reconnect', 'reconnected'])
      if (!existsSync(path.join(proof, `${name}.png`))) throw new Error(`Missing reconnect capture ${name}`);
    if (args.has('--reconnect')) {
      const match = Object.values(host.coordinator.state.matches).find(value => value.members.some(id => host.coordinator.player(id).character.realm === realm));
      const log = match ? readFileSync(path.join(directory, 'instances', match.id, 'server.log'), 'utf8') : '';
      if (!match) throw new Error('No recorded match exists for the reconnect proof.');
      verifyScenarioReconnectBots(log, realm as 'aegis' | 'riftbound', host.coordinator.matchDefinition(match).capacity);
    }
    if (host.candidateProof) {
      requireSameScenarioCandidate(candidateOptions!, host.candidateProof);
      const match = requireScenarioCandidateMenuReport(report, host.candidateProof, fileEvidence(host.candidateProofPath!).sha256,
        { realm: realm as ScenarioRealm, reconnect: args.has('--reconnect'), recovery });
      const saved = path.join(output, `client-${id}`); mkdirSync(saved);
      copyFileSync(file, path.join(saved, 'report.json'));
      const names = ['login', 'capital', 'queue', 'offer', 'combat', 'hold', 'returned',
        ...(args.has('--reconnect') ? ['before-disconnect', 'reconnect', 'reconnected'] : []),
        ...(recovery ? ['await-recovery'] : [])];
      for (const name of names) copyFileSync(path.join(proof, `${name}.png`), path.join(saved, `${name}.png`));
      candidateReports.push({ realm, match, nativeReport: fileEvidence(path.join(saved, 'report.json')),
        serverLog: fileEvidence(path.join(directory, 'instances', match, 'server.log')),
        captures: names.map(name => fileEvidence(path.join(saved, `${name}.png`))) });
    }
    console.log(JSON.stringify({ realm, party, proof, ...report }));
}
try {
  if (connectionRetry) {
    const result = client('aegis').then(() => null, error => error as Error);
    const checkpoint = async (name: string) => {
      const deadline = Date.now() + 240_000;
      while (!proofFolders.some(folder => existsSync(path.join(folder, `${name}.png`)))) {
        if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error(`Connection proof did not reach ${name}: ${output}`);
        await new Promise(resolve => setTimeout(resolve, 250));
      }
    };
    await checkpoint('host-missing');
    const port = (host.server.address() as AddressInfo).port;
    await stopHost();
    copyFileSync(path.join(directory, 'host.json'), path.join(directory, 'retry-host.json'));
    writeFileSync(path.join(proofFolders[0], 'retry-offline'), '');
    await checkpoint('host-unavailable');
    host = await startScenarioHost({ directory, executable: engine.editorCommand!, project: projectPath,
      port, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false, candidateProof: candidateOptions });
    hostOpen = true;
    writeFileSync(path.join(proofFolders[0], 'retry-ready'), '');
    const error = await result; if (error) throw error;
    if (Object.keys(host.coordinator.state.players).length !== 1) throw new Error('Retry created duplicate character registrations.');
  } else if (args.has('--recovery')) {
    const result = client('riftbound', '', 2, true).then(() => null, error => error as Error);
    const deadline = Date.now() + 300_000;
    while (!proofFolders.some(folder => existsSync(path.join(folder, 'await-recovery.png')))) {
      if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error('Client did not reach the recovery checkpoint.');
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    const port = (host.server.address() as AddressInfo).port;
    await stopHost();
    host = await startScenarioHost({ directory, executable: engine.editorCommand!, project: projectPath,
      port, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false, candidateProof: candidateOptions });
    hostOpen = true;
    const error = await result; if (error) throw error;
    console.log(JSON.stringify({ coordinatorRestartAndInstanceLoss: true, output }));
  } else if (args.has('--party')) {
    const results = await Promise.allSettled([client(realms[0], 'leader'), client(realms[0], 'member')]);
    for (const result of results) if (result.status === 'rejected') throw result.reason;
    const matches = Object.values(host.coordinator.state.matches);
    if (matches.length !== 1 || matches[0].members.length !== 2) throw new Error('Party did not travel together into one match.');
  } else if (args.has('--instances')) {
    const first = client('riftbound', '', 180).then(() => null, error => error as Error);
    const deadline = Date.now() + 240_000;
    while (!Object.values(host.coordinator.state.players).some(player => player.phase === 'playing')) {
      if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error('First instance did not admit its player.');
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    const second = client('aegis', '', 30).then(() => null, error => error as Error);
    for (const error of await Promise.all([first, second])) if (error) throw error;
    if (!overlappingInstances) throw new Error('Two independently occupied instances were not observed simultaneously.');
    console.log(JSON.stringify({ simultaneousInstances: true, output }));
  } else {
    for (const realm of realms) await client(realm);
  }
  if (host.candidateProof) {
    requireSameScenarioCandidate(candidateOptions!, host.candidateProof);
    if (!candidateReports.length) throw new Error('No actual candidate queue client report was observed.');
    for (const client of candidateReports)
      requireScenarioCandidateQueueJournal(host.coordinator.state, host.candidateProof, client.match, client.realm as ScenarioRealm);
    // Stop owned instances before sealing the final journal and logs; close may durably finish an idle match.
    await stopHost();
    for (const client of candidateReports) client.serverLog = fileEvidence(path.join(directory, 'instances', client.match, 'server.log'));
    const report = { schemaVersion: 1, fixtureId: run, map: host.candidateProof.map, mapSha256: host.candidateProof.mapSha256,
      signature: host.candidateProof.signature, cityRevision: host.candidateProof.cityRevision, proofOnly: true,
      candidateProof: fileEvidence(host.candidateProofPath!), journal: fileEvidence(path.join(directory, 'journal.json')),
      queueReturnVerified: true, reconnectVerified: args.has('--reconnect'), coordinatorRecoveryVerified: args.has('--recovery'),
      partyVerified: args.has('--party'), simultaneousInstancesVerified: args.has('--instances') && overlappingInstances,
      releaseApproved: false, fullSiegeStagesVerified: false, humanPlaytest: false, productionAdmission: false,
      steamAdmission: false, territorialAcceptance: false, freshGeometryAdmission: false, clients: candidateReports };
    const reportPath = path.join(output, 'report.json'); writeFileSync(reportPath, JSON.stringify(report), { mode: 0o600, flush: true });
    scenarioCandidateQueueEvidence(repoRoot, host.candidateProof.map, reportPath, engineRoot);
    console.log(JSON.stringify({ candidateQueueProof: reportPath, ...report }));
  }
} finally {
  clearInterval(observer);
  for (const child of children) if (child.exitCode === null && child.signalCode === null) child.kill();
  await stopHost();
}
}
if (isMain(import.meta.url)) {
  scenarioMenuProofMain().catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
}
