import { spawn, type ChildProcess } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot } from './toolchain';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const args = parseArguments(process.argv.slice(2), ['--rendered', '--inventory-ui'], ['--engine-root', '--packaged-root']);
if (args.has('--inventory-ui') && !args.has('--rendered')) throw new Error('Inventory UI proof requires --rendered.');
const packagedRoot = args.has('--packaged-root') ? path.resolve(args.get('--packaged-root')!) : undefined;
const packagedClient = packagedRoot && path.join(packagedRoot, 'AegisWar/Binaries/Win64/AegisWar.exe');
if (packagedClient && !existsSync(packagedClient)) throw new Error('Packaged Windows client does not exist.');
const engine = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
if (engine.blockers.length || !engine.editorCommand) throw new Error(engine.blockers.join('\n'));
const run = `${Date.now()}-${process.pid}`;
const output = path.join(repoRoot, 'artifacts/unreal/network', run);
const receiptDirectory = path.join(repoRoot, 'unreal/AegisWar/Saved/NetworkProof', run);
mkdirSync(output, { recursive: true });
if (!existsSync(path.join(repoRoot, 'artifacts/unreal/proof-map.json'))) throw new Error('Prepare the proof map first.');
const socket = createSocket('udp4');
await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
const port = socket.address().port;
await new Promise<void>(resolve => socket.close(resolve));
const children: ChildProcess[] = [];
const logs: ReturnType<typeof createWriteStream>[] = [];
const common = ['-unattended', '-nop4', '-nosplash', '-nosound', '-stdout', '-FullStdOutLogOutput',
  '-WarDevelopmentNetworking', '-WarNetworkProof', `-WarProofRun=${run}`, '-NoAsyncLoadingThread', '-ExecCmds=t.MaxFPS 60'];
if (args.has('--inventory-ui')) common.push('-WarInventoryProofUI');

function start(name: string, options: string[]): ChildProcess {
  const log = createWriteStream(path.join(output, `${name}-stdout.log`)); logs.push(log);
  const standalone = name.startsWith('client') && packagedClient;
  const rendering = name.startsWith('client') && args.has('--rendered')
    ? ['-RenderOffscreen', '-WarProofScreenshot', '-ResX=1280', '-ResY=720', '-windowed'] : ['-nullrhi'];
  const child = spawn(standalone || engine.editorCommand!, [...(standalone ? [] : [projectPath]), ...options, ...common, ...rendering, `-abslog=${path.join(output, `${name}.log`)}`],
    { cwd: repoRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout!.pipe(log); child.stderr!.pipe(log);
  children.push(child);
  child.on('error', error => { log.write(String(error)); });
  return child;
}

try {
  start('server', ['/Game/MigrationProof/EngineProof', '-server', `-port=${port}`, '-MULTIHOME=127.0.0.1']);
  const serverLog = path.join(output, 'server.log');
  const started = Date.now();
  while (!existsSync(serverLog) || !readFileSync(serverLog, 'utf8').includes('listening on port')) {
    if (Date.now() - started > 60000 || children[0].exitCode !== null) throw new Error(`Server did not listen; see ${serverLog}`);
    await delay(250);
  }
  start('client-1', [`127.0.0.1:${port}`, '-game']);
  start('client-2', [`127.0.0.1:${port}`, '-game']);
  const roles = ['server', 'client-aegis', 'client-riftbound'];
  const receiptPath = (role: string) => path.join(role !== 'server' && packagedRoot
    ? path.join(packagedRoot, 'AegisWar/Saved/NetworkProof', run) : receiptDirectory, `${role}.json`);
  const deadline = Date.now() + 120000;
  while (!roles.every(role => existsSync(receiptPath(role)))) {
    if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error(`Network proof did not finish; see ${output}`);
    await delay(250);
  }
  const receipts = roles.map(role => JSON.parse(readFileSync(receiptPath(role), 'utf8').replace(/^\uFEFF/, '')));
  if (args.has('--rendered')) {
    const screenshots = roles.slice(1).map(role => receiptPath(role).replace(/\.json$/, '.png'));
    while (!screenshots.every(filename => existsSync(filename))) {
      if (Date.now() > deadline || children.some(child => child.exitCode !== null)) throw new Error(`Rendered proof did not capture screenshots; see ${output}`);
      await delay(250);
    }
    for (const [index, filename] of screenshots.entries()) writeFileSync(path.join(output, `${roles[index + 1]}.png`), readFileSync(filename));
  }
  if (receipts.some((receipt, index) => receipt.schemaVersion !== 1 || receipt.role !== roles[index] || receipt.passed !== true
      || receipt.inventoryAuthorityAndPrivacy !== true || receipt.observedReplicatedMovement !== true || receipt.defenderHealth !== 100
      || receipt.combatBeforeHealing !== true || receipt.consumableAuthority !== true
      || receipt.craftingAuthority !== true
      || receipt.salvageAuthority !== true
      || receipt.cultivationAuthority !== true
      || (index < 2 && receipt.attackerMana !== 100)
      || (index > 0 && (receipt.autonomousProxy !== true || receipt.movementAnimation !== true || receipt.strikeAnimation !== true)))
      || receipts[1].strikeRequests !== 2) throw new Error(`Network proof failed: ${JSON.stringify(receipts)}`);
  const report = { schemaVersion: 1, run, passed: true, platform: process.platform, transport: 'loopback UDP',
    server: 'Unreal Editor dedicated process (not a packaged Linux server)',
    clients: packagedRoot ? 'Packaged Windows Development clients' : 'Unreal Editor game clients',
    renderer: args.has('--rendered') ? 'Offscreen real renderer; screenshots require review' : 'NullRHI',
    graphicalAcceptance: false, receipts };
  writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ networkProofPassed: true, report: path.join(output, 'report.json') }));
} finally {
  for (const child of children) {
    if (child.exitCode === null) child.kill();
  }
  await Promise.all(children.map(child => child.exitCode !== null || child.pid === undefined ? Promise.resolve()
    : new Promise<void>(resolve => { child.once('exit', () => resolve()); setTimeout(resolve, 5000); })));
  for (const log of logs) log.end();
}
