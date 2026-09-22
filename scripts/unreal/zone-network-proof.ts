import { spawn, type ChildProcess } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { createHash } from 'node:crypto';
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';

const engine = inspectToolchain(defaultEngineRoot());
if (engine.blockers.length || !engine.editorCommand) throw new Error(engine.blockers.join('\n'));
const receipt = JSON.parse(readFileSync(path.join(repoRoot, 'artifacts/unreal/world-portals/build.json'), 'utf8'));
if (!receipt.partitionManifest) throw new Error('Attach the partitioned world first.');
const manifest = JSON.parse(readFileSync(path.join(repoRoot, 'artifacts/unreal/world-portals', receipt.partitionManifest), 'utf8'));
const packages = [...new Set<string>([receipt.map, receipt.layer, ...Object.keys(manifest.packageHashes)])];
function fingerprints() {
  return Object.fromEntries(packages.map(asset => {
    if (!asset.startsWith('/Game/') || asset.includes('..')) throw new Error('Invalid world package path.');
    const file = path.join(repoRoot, 'unreal/AegisWar/Content', `${asset.slice(6)}.umap`);
    return [asset, createHash('sha256').update(readFileSync(file)).digest('hex')];
  }));
}
const packageHashes = fingerprints();
const run = `${Date.now()}-${process.pid}`;
const output = path.join(repoRoot, 'artifacts/unreal/world-portals/network', run);
mkdirSync(output, { recursive: true });
const socket = createSocket('udp4');
await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
const port = socket.address().port;
await new Promise<void>(resolve => socket.close(resolve));
const children: ChildProcess[] = [];
const logs: ReturnType<typeof createWriteStream>[] = [];
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
function start(name: string, args: string[]) {
  const log = createWriteStream(path.join(output, `${name}-stdout.log`)); logs.push(log);
  const child = spawn(engine.editorCommand!, [projectPath, ...args, '-unattended', '-nop4', '-nosplash', '-nosound',
    '-nullrhi', '-stdout', '-FullStdOutLogOutput', '-WarDevelopmentNetworking', '-WarZoneNetworkProof',
    `-WarProofRun=${run}`, '-ExecCmds=t.MaxFPS 60', `-abslog=${path.join(output, `${name}.log`)}`],
  { cwd: repoRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout!.pipe(log); child.stderr!.pipe(log); children.push(child);
  child.on('error', error => log.write(String(error)));
}
try {
  start('server', [receipt.map, '-server', `-port=${port}`, '-MULTIHOME=127.0.0.1']);
  const serverLog = path.join(output, 'server.log');
  const deadline = Date.now() + 180000;
  while (!existsSync(serverLog) || !readFileSync(serverLog, 'utf8').includes('listening on port')) {
    if (Date.now() > deadline || children[0].exitCode !== null) throw new Error(`Server startup failed; see ${output}`);
    await delay(250);
  }
  start('client-1', [`127.0.0.1:${port}`, '-game']);
  start('client-2', [`127.0.0.1:${port}`, '-game']);
  const reportFile = path.join(repoRoot, 'unreal/AegisWar/Saved/ZoneNetworkProof', run, 'report.json');
  while (!existsSync(reportFile)) {
    if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error(`Proof did not complete; see ${output}`);
    await delay(250);
  }
  const report = JSON.parse(readFileSync(reportFile, 'utf8').replace(/^\uFEFF/, ''));
  const clientResidency = ['client_aegis_sunmeadow_march.json', 'client_rift_riftspire_capital.json'].map(name => {
    const file = path.join(path.dirname(reportFile), name);
    if (!existsSync(file)) throw new Error(`Missing actual-client residency evidence: ${name}; see ${output}`);
    const row = JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
    if (!row.onlyCurrentZoneLoaded || row.persistentStaticMeshes !== 0 || !row.lightingMatchesZone) {
      throw new Error(`Client content isolation failed: ${name}`);
    }
    return row;
  });
  if (JSON.stringify(fingerprints()) !== JSON.stringify(packageHashes)) throw new Error('Saved world changed during the network proof.');
  writeFileSync(path.join(output, 'report.json'), JSON.stringify({ ...report, map: receipt.map,
    transport: 'loopback UDP', platform: process.platform, packageHashes, clientResidency, productionAccepted: false }, null, 2));
  if (!report.passed || report.twoClientStreaming !== true || report.stage !== 5) throw new Error(`Zone isolation failed; see ${output}`);
  console.log(JSON.stringify({ twoClientStreamingPassed: true, report: path.join(output, 'report.json') }));
} finally {
  for (const child of children) if (child.exitCode === null) child.kill();
  await Promise.all(children.map(child => child.exitCode !== null || !child.pid ? Promise.resolve()
    : new Promise<void>(resolve => { child.once('exit', () => resolve()); setTimeout(resolve, 5000); })));
  for (const log of logs) log.end();
}
