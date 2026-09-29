import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync, writeFileSync } from 'node:fs';
import { spawn, type ChildProcess } from 'node:child_process';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';
import { startScenarioHost } from '../../server/scenarios/host';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID(), output = path.join(repoRoot, 'artifacts/unreal/scenario-menu', run);
mkdirSync(output, { recursive: true });
const directory = path.join(output, 'host');
const connectionRetry = process.argv.includes('--connection-retry');
let host = await startScenarioHost({ directory, executable: engine.editorCommand, project: projectPath,
  port: 0, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false });
let hostOpen = true;
async function stopHost() { if (hostOpen) { hostOpen = false; await host.close(); } }
const sideArg = process.argv.indexOf('--realm');
const realms = sideArg >= 0 ? [process.argv[sideArg + 1]] : ['aegis', 'riftbound'];
const children: ChildProcess[] = [];
const proofFolders: string[] = [];
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
    const child = spawn(engine.editorCommand!, [projectPath, '-game', '-unattended', '-nop4', '-nosound', '-nosplash',
      '-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1280', '-ResY=720', '-WarScenarioMenuProof',
      `-WarScenarioMenuRun=${id}`, `-WarScenarioProofRealm=${realm}`, `-WarScenarioHostConfig=${path.join(directory, connectionRetry ? 'retry-host.json' : 'host.json')}`,
      ...(connectionRetry ? ['-WarScenarioProofConnectionRetry'] : []),
      ...(party ? [`-WarScenarioProofParty=${party}`] : []), `-WarScenarioProofHold=${hold}`,
      ...(recovery ? ['-WarScenarioProofRecovery'] : []),
      ...(process.argv.includes('--reconnect') ? ['-WarScenarioProofReconnect'] : []),
      '-ExecCmds=t.MaxFPS 30', `-abslog=${path.join(output, `${realm}${party}.log`)}`], { windowsHide: true, stdio: 'ignore' });
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
    if (process.argv.includes('--reconnect')) for (const name of ['before-disconnect', 'reconnect', 'reconnected'])
      if (!existsSync(path.join(proof, `${name}.png`))) throw new Error(`Missing reconnect capture ${name}`);
    if (process.argv.includes('--reconnect')) {
      const match = Object.values(host.coordinator.state.matches).find(value => value.members.some(id => host.coordinator.player(id).character.realm === realm));
      const log = match ? readFileSync(path.join(directory, 'instances', match.id, 'server.log'), 'utf8') : '';
      const team = `WAR_SCENARIO_TEAM realm=${realm === 'aegis' ? 1 : 2}`;
      const replacement = new RegExp(`${team} humans=1 bots=5[\\s\\S]*${team} humans=0 bots=6[\\s\\S]*${team} humans=1 bots=5`);
      if (!replacement.test(log)) throw new Error('Temporary bot substitution and removal were not observed during reconnect.');
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
      port, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false });
    hostOpen = true;
    writeFileSync(path.join(proofFolders[0], 'retry-ready'), '');
    const error = await result; if (error) throw error;
    if (Object.keys(host.coordinator.state.players).length !== 1) throw new Error('Retry created duplicate character registrations.');
  } else if (process.argv.includes('--recovery')) {
    const result = client('riftbound', '', 2, true).then(() => null, error => error as Error);
    const deadline = Date.now() + 300_000;
    while (!proofFolders.some(folder => existsSync(path.join(folder, 'await-recovery.png')))) {
      if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error('Client did not reach the recovery checkpoint.');
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    const port = (host.server.address() as AddressInfo).port;
    await stopHost();
    host = await startScenarioHost({ directory, executable: engine.editorCommand!, project: projectPath,
      port, bind: '127.0.0.1', advertise: '127.0.0.1', allowLan: false });
    hostOpen = true;
    const error = await result; if (error) throw error;
    console.log(JSON.stringify({ coordinatorRestartAndInstanceLoss: true, output }));
  } else if (process.argv.includes('--party')) {
    const results = await Promise.allSettled([client(realms[0], 'leader'), client(realms[0], 'member')]);
    for (const result of results) if (result.status === 'rejected') throw result.reason;
    const matches = Object.values(host.coordinator.state.matches);
    if (matches.length !== 1 || matches[0].members.length !== 2) throw new Error('Party did not travel together into one match.');
  } else if (process.argv.includes('--instances')) {
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
} finally {
  clearInterval(observer);
  for (const child of children) if (child.exitCode === null && child.signalCode === null) child.kill();
  await stopHost();
}
