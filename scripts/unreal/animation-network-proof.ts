import { spawn, type ChildProcess } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { createHash } from 'node:crypto';
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = `${Date.now()}-${process.pid}`;
const output = path.join(repoRoot, 'artifacts/unreal/animation-replacement/network', run);
const receipts = path.join(repoRoot, 'unreal/AegisWar/Saved/AnimationNetworkProof', run);
mkdirSync(output, { recursive: true });
const socket = createSocket('udp4');
await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
const port = socket.address().port;
await new Promise<void>(resolve => socket.close(resolve));
const children: ChildProcess[] = [];
const logs: ReturnType<typeof createWriteStream>[] = [];
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
function start(role: string) {
  const log = createWriteStream(path.join(output, `${role}.log`)); logs.push(log);
  const options = role === 'server' ? ['/Game/MigrationProof/EngineProof', '-server', `-port=${port}`, '-MULTIHOME=127.0.0.1'] : [`127.0.0.1:${port}`, '-game'];
  const child = spawn(engine.editorCommand!, [projectPath, ...options, '-unattended', '-nop4', '-nosound', '-nosplash', '-nullrhi', '-stdout', '-FullStdOutLogOutput',
    '-WarDevelopmentNetworking', '-WarAnimationNetworkProof', `-WarProofRun=${run}`, `-WarAnimationProofRole=${role}`, '-ExecCmds=t.MaxFPS 30'],
    { cwd: repoRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout!.pipe(log); child.stderr!.pipe(log); children.push(child);
}
try {
  start('server'); const deadline = Date.now() + 480000;
  while (!existsSync(path.join(output, 'server.log')) || !readFileSync(path.join(output, 'server.log'), 'utf8').includes(`IpNetDriver listening on port ${port}`)) {
    if (Date.now() > deadline || children[0].exitCode !== null) throw new Error('Server failed to listen: '+output);
    await delay(300);
  }
  start('client');
  while (!readFileSync(path.join(output, 'server.log'), 'utf8').includes('WAR_SUPPLIED_ANIMATION_STARTED')) {
    if (Date.now() > deadline || children[0].exitCode !== null) throw new Error('Server did not start ability execution');
    await delay(300);
  }
  await delay(6000); start('late-client');
  const roles = ['server', 'client', 'late-client'];
  while (!roles.every(role => existsSync(path.join(receipts, `${role}.json`)))) {
    for (const role of roles) {
      const file = path.join(receipts, `${role}.json`);
      if (existsSync(file) && !JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, '')).passed) throw new Error('Failed proof receipt: '+file);
    }
    if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error('Incomplete network proof: '+output);
    await delay(500);
  }
  const reports = roles.map(role => JSON.parse(readFileSync(path.join(receipts, `${role}.json`), 'utf8').replace(/^\uFEFF/, '')));
  if (reports.some(report => !report.passed || report.uniqueVariants !== 41) || !reports[2].joinedDuringAction)
    throw new Error('Network presentation or late-join proof failed: '+JSON.stringify(reports.map(({samples: _, ...report}) => report)));
  const server = new Map<string, {start: number; duration: number}>(reports[0].samples.map((row: {key: string; serial: number; start: number; duration: number}) => [`${row.key}:${row.serial}`, row]));
  // The authority keeps its receipt current until both clients finish.
  for (const report of reports.slice(1)) for (const row of report.samples) {
    const authoritative = server.get(`${row.key}:${row.serial}`);
    if (!authoritative || authoritative.start !== row.start || authoritative.duration !== row.duration)
      throw new Error('Replicated timing differs from authority: '+row.key);
    if (Math.abs(row.age-row.evaluatedTime) > .12) throw new Error('Client evaluated the wrong action phase');
    if (row.poseLag < -.001 || row.poseLag > row.frameDelta + .05) throw new Error('Client evaluated a stale pose');
  }
  const presentationManifestSha256 = createHash('sha256').update(readFileSync(path.join(repoRoot,'artifacts/unreal/animation-replacement/presentations.json'))).digest('hex');
  const report = { run, passed: true, transport: 'loopback UDP', graphicalAcceptance: false, steamAcceptance: false, presentationManifestSha256, reports };
  writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2)+'\n');
  console.log(JSON.stringify({ animationNetworkProofPassed: true, report: path.join(output, 'report.json') }));
} finally {
  for (const child of children) if (child.exitCode === null) child.kill();
  await Promise.all(children.map(child => child.exitCode !== null ? Promise.resolve() : new Promise<void>(resolve => { child.once('exit', () => resolve()); setTimeout(resolve, 5000); })));
  for (const log of logs) log.end();
}
