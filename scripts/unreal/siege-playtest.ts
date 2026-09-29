import { spawn, type ChildProcess } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { createWriteStream, mkdirSync, readFileSync, existsSync, writeFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';

export type SiegeProcess = 'server' | 'aegis' | 'riftbound';
export function siegeArguments(role: SiegeProcess, port: number, width = 1280, height = 720): string[] {
  if (!['server', 'aegis', 'riftbound'].includes(role) || !Number.isInteger(port) || port < 1024 || port > 65535)
    throw new Error('Invalid siege process or loopback port.');
  if (![width, height].every(value => Number.isInteger(value) && value >= 480 && value <= 7680))
    throw new Error('Invalid playtest dimensions.');
  const common = ['-WarDevelopmentNetworking', '-WarSiegePlaytest', '-nop4', '-nosplash', '-stdout', '-FullStdOutLogOutput'];
  return role === 'server'
    ? [projectPath, '/Game/Capitals/Siege/AegisCapital_Siege', ...common, '-server', '-nullrhi', '-unattended', '-MULTIHOME=127.0.0.1', `-port=${port}`]
    : [projectPath, `127.0.0.1:${port}`, ...common, '-game', '-windowed', `-ResX=${width}`, `-ResY=${height}`, '-ForceRes', '-ExecCmds=t.MaxFPS 45'];
}

export function siegeStartupStatus(log: string): { listening: boolean; blocked: string | null; contentReady: boolean } {
  const latest = [...log.matchAll(/WAR_SIEGE_CONTENT_(READY|BLOCKED)([^\r\n]*)/g)].at(-1);
  return { listening: log.includes('IpNetDriver listening on port'),
    blocked: latest?.[1] === 'BLOCKED' ? latest[2].trim() : null, contentReady: latest?.[1] === 'READY' };
}

export function validateSiegeRounds(report: any): void {
  if (report?.passed !== true || report.humanPlaytest !== false || report.releaseApproved !== false
    || !Number.isFinite(report.movementCm) || report.movementCm < 1000
    || !Number.isInteger(report.actionRequests) || report.actionRequests <= 0
    || !Array.isArray(report.rounds) || report.rounds.length !== 3
    || report.rounds.some((r: any, index: number) => r.round !== index + 1 || !Number.isFinite(r.elapsed)
      || r.elapsed <= 0 || r.elapsed > 961 || !Number.isInteger(r.deaths) || r.deaths < 0
      || typeof r.attackersWon !== 'boolean' || !Number.isInteger(r.milestones) || r.milestones < 0 || r.milestones > 4
      || (r.attackersWon ? r.milestones !== 4 : r.elapsed < 839))) {
    throw new Error('Three complete normal-timed siege rounds with client movement/actions are required.');
  }
}

async function run() {
  const args = parseArguments(process.argv.slice(2), ['--dry-run', '--smoke', '--automated'], ['--width', '--height']);
  if (args.has('--smoke') && args.has('--automated')) throw new Error('Choose smoke or full automated rounds.');
  const width = Number(args.get('--width') ?? 1280), height = Number(args.get('--height') ?? 720);
  siegeArguments('server', 17777, width, height);
  const engine = inspectToolchain(defaultEngineRoot());
  if (args.has('--dry-run')) {
    console.log(JSON.stringify({ command: engine.editorCommand, processes: ['server', 'aegis', 'riftbound'].map(role => siegeArguments(role as SiegeProcess, 17777, width, height)), blockers: engine.blockers, executed: false }, null, 2));
    return;
  }
  if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
  const socket = createSocket('udp4');
  await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
  const port = socket.address().port;
  await new Promise<void>(resolve => socket.close(() => resolve()));
  const output = path.join(repoRoot, 'artifacts/unreal/siege/playtests', `${Date.now()}-${process.pid}`);
  const runId = randomUUID();
  const proof = path.join(repoRoot, 'unreal/AegisWar/Saved/SiegePlaytestProof', runId.replaceAll('-', ''));
  mkdirSync(output, { recursive: true });
  const children: ChildProcess[] = [];
  const ended = (child: ChildProcess) => child.exitCode !== null || child.signalCode !== null;
  const streams: ReturnType<typeof createWriteStream>[] = [];
  let stopping = false;
  const stop = () => { stopping = true; for (const child of children) if (!ended(child)) child.kill(); };
  process.once('SIGINT', stop); process.once('SIGTERM', stop);
  let spawnError: Error | undefined;
  const start = (role: SiegeProcess) => {
    const stream = createWriteStream(path.join(output, `${role}.log`)); streams.push(stream);
    const invocation = siegeArguments(role, port, width, height);
    if (args.has('--smoke') && role !== 'server') invocation.push('-nullrhi', '-unattended');
    if (args.has('--automated')) {
      invocation.push('-WarSiegeAutomation', `-WarSiegeProofRun=${runId}`, `-WarSiegeProofRole=${role}`);
      if (role !== 'server') {
        invocation.splice(invocation.findIndex(value => value.startsWith('-ExecCmds=')), 1);
        invocation.push('-RenderOffscreen', '-unattended', '-NoVSync',
          '-ExecCmds=t.MaxFPS 30,sg.ShadowQuality 1,sg.ViewDistanceQuality 1');
      }
    }
    const child = spawn(engine.editorCommand!, invocation, { cwd: repoRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    child.once('error', error => { spawnError = error; });
    child.stdout!.pipe(stream); child.stderr!.pipe(stream); children.push(child);
  };
  const delay = () => new Promise(resolve => setTimeout(resolve, 500));
  try {
    start('server');
    const startupDeadline = Date.now() + 180_000;
    let log = '';
    while (!stopping) {
      if (spawnError) throw spawnError;
      if (ended(children[0]) || Date.now() > startupDeadline) throw new Error(`Siege server did not start. Inspect ${output}`);
      const logPath = path.join(output, 'server.log');
      log = existsSync(logPath) ? readFileSync(logPath, 'utf8') : '';
      if (siegeStartupStatus(log).listening) break;
      await delay();
    }
    if (stopping) return;
    start('aegis');
    // Wait for server admission so assignment stays deterministic despite shader startup.
    while (!stopping) {
      if (spawnError) throw spawnError;
      log = readFileSync(path.join(output, 'server.log'), 'utf8');
      if (log.includes('WAR_SIEGE_JOIN realm=1')) break;
      if (children.some(ended) || Date.now() > startupDeadline) throw new Error(`First client did not join. Inspect ${output}`);
      await delay();
    }
    if (stopping) return;
    start('riftbound');
    console.log(`Siege playtest logs: ${output}\n${args.has('--automated') ? `Automated normal-timed rounds; captures and client reports: ${proof}` : 'Choose a class and Ready in both clients. Closing either client ends this playtest.'}`);
    const smokeDeadline = Date.now() + 60_000;
    const roundsDeadline = Date.now() + 55 * 60_000;
    while (!stopping && !children.some(ended)) {
      if (spawnError) throw spawnError;
      if (args.has('--automated')) {
        log = readFileSync(path.join(output, 'server.log'), 'utf8');
        const state = siegeStartupStatus(log);
        if (state.blocked) throw new Error(`Content blocked: ${state.blocked}`);
        if (log.includes('WAR_SIEGE_BLOCKED')) throw new Error(`Runtime match failure; inspect ${output}`);
        const reports = ['aegis', 'riftbound'].map(role => path.join(proof, role, 'report.json'));
        if (reports.every(existsSync)) {
          const clients = reports.map(file => JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, '')));
          clients.forEach(validateSiegeRounds);
          writeFileSync(path.join(output, 'automated.json'), JSON.stringify({ runId, proof, clients, releaseApproved: false }, null, 2));
          console.log(`Three automated network rounds and rematches passed. Captures: ${proof}`); return;
        }
        if (Date.now() > roundsDeadline) throw new Error(`Automated rounds timed out; inspect ${output}`);
      }
      if (args.has('--smoke')) {
        log = readFileSync(path.join(output, 'server.log'), 'utf8');
        const state = siegeStartupStatus(log);
        const clientsReady = ['aegis', 'riftbound'].every(role => {
          const file = path.join(output, `${role}.log`);
          return existsSync(file) && readFileSync(file, 'utf8').includes('WAR_SIEGE_LOBBY_READY');
        });
        if (log.includes('WAR_SIEGE_JOIN realm=2') && clientsReady) {
          if (state.blocked) throw new Error(`Both clients joined, but siege content is blocked: ${state.blocked}`);
          if (state.contentReady) { console.log('Two-client admission and replicated lobby startup verified; gameplay and visuals are not verified.'); return; }
        }
        if (Date.now() > smokeDeadline) throw new Error(`Two-client startup timed out. Inspect ${output}`);
      }
      await delay();
    }
    if (spawnError) throw spawnError;
    if ((args.has('--smoke') || args.has('--automated')) && !stopping) throw new Error(`A playtest process exited before verification. Inspect ${output}`);
  } finally {
    stop();
    await Promise.all(children.map(child => ended(child) ? Promise.resolve() : new Promise<void>(resolve => {
      const timeout = setTimeout(resolve, 5000); child.once('exit', () => { clearTimeout(timeout); resolve(); });
    })));
    for (const stream of streams) stream.end();
    process.removeListener('SIGINT', stop); process.removeListener('SIGTERM', stop);
  }
}

if (isMain(import.meta.url)) run().catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
