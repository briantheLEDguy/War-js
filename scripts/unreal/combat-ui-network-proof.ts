import { spawn } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';
import { stopCombatUiProcesses, trackCombatUiProcess } from './combat-ui-process';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = `${Date.now()}-${process.pid}`;
const output = path.join(repoRoot, 'artifacts/unreal/combat-ui-network', run);
const receipts = path.join(repoRoot, 'unreal/AegisWar/Saved/CombatNetworkProof', run);
mkdirSync(output, { recursive: true });
const socket = createSocket('udp4');
await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
const port = socket.address().port;
await new Promise<void>(resolve => socket.close(resolve));
const children: ReturnType<typeof trackCombatUiProcess>[] = [];
const logs: ReturnType<typeof createWriteStream>[] = [];
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
function start(role: 'server' | 'client') {
  const log = createWriteStream(path.join(output, `${role}.log`)); logs.push(log);
  const entry = role === 'server' ? ['/Game/MigrationProof/EngineProof', '-server', `-port=${port}`, '-MULTIHOME=127.0.0.1'] : [`127.0.0.1:${port}`, '-game'];
  const child = spawn(engine.editorCommand!, [projectPath, ...entry, '-unattended', '-nop4', '-nosound', '-nosplash', '-nullrhi', '-stdout', '-FullStdOutLogOutput',
    '-WarDevelopmentNetworking', '-WarCombatNetworkProof', '-WarCombatUiNetworkProof', `-WarProofRun=${run}`, '-PktLag=80', '-PktLagVariance=20', '-PktLoss=2', '-ExecCmds=t.MaxFPS 60'],
  { cwd: repoRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  children.push(trackCombatUiProcess(child, role));
  child.stdout!.pipe(log); child.stderr!.pipe(log);
}
try {
  start('server'); const deadline = Date.now() + 240000;
  while (!existsSync(path.join(output, 'server.log')) || !readFileSync(path.join(output, 'server.log'), 'utf8').includes(`listening on port ${port}`)) {
    children[0].assertRunning();
    if (Date.now() > deadline) throw new Error(`Server did not listen: ${output}`);
    await delay(300);
  }
  start('client');
  while (!['server', 'client'].every(role => existsSync(path.join(receipts, `${role}.json`)))) {
    for (const child of children) child.assertRunning();
    if (Date.now() > deadline) throw new Error(`Combat network proof did not finish: ${output}`);
    await delay(300);
  }
  const reports = ['server', 'client'].map(role => JSON.parse(readFileSync(path.join(receipts, `${role}.json`), 'utf8').replace(/^\uFEFF/, '')));
  if (reports.some(report => report.passed !== true)) throw new Error(`Combat network proof failed: ${JSON.stringify(reports)}`);
  writeFileSync(path.join(output, 'proof.json'), JSON.stringify({ passed: true, lagMs: 80, varianceMs: 20, packetLossPercent: 2, reports }, null, 2));
  console.log(`Combat UI relationship and health replication verified under emulated network delay: ${output}`);
} finally {
  try { await stopCombatUiProcesses(children); }
  finally { for (const log of logs) log.end(); }
}
