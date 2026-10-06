import { spawn } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { randomUUID } from 'node:crypto';
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';
import { stopCombatUiProcesses, trackCombatUiProcess } from './combat-ui-process';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID();
const output = path.join(repoRoot, 'artifacts/unreal/combat-ui-live', run);
const receipt = path.join(repoRoot, 'unreal/AegisWar/Saved/CombatUiLiveProof', run.replaceAll('-', ''));
mkdirSync(output, { recursive: true });
const socket = createSocket('udp4');
await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
const port = socket.address().port;
await new Promise<void>(resolve => socket.close(resolve));
const children: ReturnType<typeof trackCombatUiProcess>[] = [];
const logs: ReturnType<typeof createWriteStream>[] = [];
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
function start(role: 'server' | 'owner' | 'enemy' | 'friendly') {
  const log = createWriteStream(path.join(output, `${role}.log`)); logs.push(log);
  const entry = role === 'server'
    ? ['/Game/MigrationProof/EngineProof', '-server', `-port=${port}`, '-MULTIHOME=127.0.0.1']
    : [`127.0.0.1:${port}`, '-game'];
  const render = role === 'owner'
    ? ['-WarUiRenderOwner', '-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1920', '-ResY=1080'] : ['-nullrhi'];
  // InterfaceProof opts into existing direct development entry. Without DevelopmentGM,
  // its subsystem stays disabled; only the isolated LiveProof subsystem runs.
  const child = spawn(engine.editorCommand!, [projectPath, ...entry, ...render,
    '-unattended', '-nop4', '-nosound', '-nosplash', '-stdout', '-FullStdOutLogOutput',
    '-WarDevelopmentNetworking', '-WarInterfaceProof', '-WarCombatUiLiveProof', `-WarUiLiveRun=${run}`,
    `-GameUserSettingsINI=${path.join(output, `${role}-preferences.ini`)}`,
    '-PktLag=80', '-PktLagVariance=20', '-PktLoss=2', '-ExecCmds=t.MaxFPS 30'],
  { cwd: repoRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  children.push(trackCombatUiProcess(child, role));
  child.stdout!.pipe(log); child.stderr!.pipe(log);
}
try {
  const deadline = Date.now() + 240000;
  start('server');
  while (!existsSync(path.join(output, 'server.log')) || !readFileSync(path.join(output, 'server.log'), 'utf8').includes(`listening on port ${port}`)) {
    children[0].assertRunning();
    if (Date.now() > deadline) throw new Error(`Server did not listen: ${output}`);
    await delay(300);
  }
  let joined = 0;
  for (const role of ['owner', 'enemy', 'friendly'] as const) {
    start(role); ++joined;
    while ((readFileSync(path.join(output, 'server.log'), 'utf8').match(/Join succeeded:/g) ?? []).length < joined) {
      for (const child of children) child.assertRunning();
      if (Date.now() > deadline) throw new Error(`Client ${role} did not join: ${output}`);
      await delay(300);
    }
  }
  while (!['server', 'owner'].every(role => existsSync(path.join(receipt, `${role}.json`)))) {
    for (const child of children) child.assertRunning();
    if (Date.now() > deadline) throw new Error(`Live UI proof did not finish: ${output}`);
    await delay(300);
  }
  const reports = ['server', 'owner'].map(role => JSON.parse(readFileSync(path.join(receipt, `${role}.json`), 'utf8').replace(/^\uFEFF/, '')));
  if (reports.some(report => report.passed !== true)) throw new Error(`Live UI proof failed: ${JSON.stringify(reports)}`);
  for (const file of ['server.json', 'owner.json', ...[0, 1, 2, 3].map(i => `target-${i}.png`)]) {
    if (!existsSync(path.join(receipt, file))) throw new Error(`Missing native capture: ${file}`);
    copyFileSync(path.join(receipt, file), path.join(output, file));
  }
  writeFileSync(path.join(output, 'proof.json'), JSON.stringify({ passed: true, actualPlayerConnections: 3,
    renderedOwner: true, lagMs: 80, varianceMs: 20, packetLossPercent: 2, reports, visualReviewRequired: true }, null, 2));
  console.log(`Live combat UI player/NPC movement and target-switching proof passed: ${output}`);
} finally {
  try { await stopCombatUiProcesses(children); }
  finally { for (const log of logs) log.end(); }
}
