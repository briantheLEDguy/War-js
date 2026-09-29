import { createServer, type IncomingMessage } from 'node:http';
import { createSocket } from 'node:dgram';
import { spawn, type ChildProcess } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync, openSync, closeSync, unlinkSync } from 'node:fs';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { fileURLToPath } from 'node:url';
import { ScenarioCoordinator, ScenarioError, sameSecret } from './coordinator';
import type { ScenarioJournal, ScenarioMatch } from '../../shared/scenarios/types';

export function atomicJson(file: string, value: unknown, replace = renameSync) {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(`${file}.tmp`, JSON.stringify(value), { mode: 0o600, flush: true });
  // Windows readers and virus scanners can briefly deny replacement. Never delete
  // the previous durable journal to work around a sharing violation.
  for (let attempt = 0; ; attempt++) {
    try { replace(`${file}.tmp`, file); return; }
    catch (error) {
      if (attempt >= 20 || !['EPERM', 'EBUSY', 'EACCES'].includes((error as NodeJS.ErrnoException).code ?? '')) throw error;
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 25);
    }
  }
}
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const loopback = (ip: string) => ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(ip);
const token = (request: IncomingMessage) => request.headers.authorization?.startsWith('Bearer ') ? request.headers.authorization.slice(7) : '';
interface DevelopmentPeer { id: string; realm: 'aegis' | 'riftbound'; key: string }
export function provisionDevelopmentPeer(directory: string, id: string, realm: string, url: string) {
  if (!/^[a-zA-Z0-9_-]{1,80}$/.test(id) || ['__proto__', 'constructor', 'prototype'].includes(id)
    || !['aegis', 'riftbound'].includes(realm) || !/^http:\/\/[a-zA-Z0-9.-]+:[0-9]+$/.test(url)) throw new Error('Invalid development identity or host URL.');
  mkdirSync(directory, { recursive: true });
  const file = path.join(directory, 'peers.json');
  const peers: DevelopmentPeer[] = existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : [];
  if (peers.some(peer => peer.id === id)) throw new Error('Development identity already exists. Reuse its private config.');
  const peer: DevelopmentPeer = { id, realm: realm as DevelopmentPeer['realm'], key: randomBytes(32).toString('hex') };
  peers.push(peer); atomicJson(file, peers);
  const config = path.join(directory, 'peers', `${id}.json`);
  atomicJson(config, { url, key: peer.key, characterId: id, realm, allowLan: true });
  return config;
}
export function authenticateCampaignHost(directory: string, controlKey: string, credential: string, ip: string, allowLan: boolean): DevelopmentPeer | null {
  if (loopback(ip) && sameSecret(controlKey, credential)) return null;
  const file = path.join(directory, 'peers.json');
  const peers: DevelopmentPeer[] = allowLan && existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : [];
  const peer = peers.find(entry => sameSecret(entry.key, credential));
  if (!peer) throw new ScenarioError(403, 'An explicitly provisioned development character identity is required.');
  return peer;
}
async function body(request: IncomingMessage) {
  const chunks: Buffer[] = []; let length = 0;
  for await (const data of request) { length += data.length; if (length > 2_000_000) throw new ScenarioError(413, 'Request too large.'); chunks.push(data); }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'); }
  catch { throw new ScenarioError(400, 'Invalid JSON.'); }
}
async function freePort() {
  const socket = createSocket('udp4');
  return new Promise<number>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', () => { const port = socket.address().port; socket.close(() => resolve(port)); }); });
}
export function verifyScenery(repository = root) {
  const receipt = JSON.parse(readFileSync(path.join(repository, 'artifacts/unreal/scenario-queues/capital-scenery.json'), 'utf8'));
  const content = path.join(repository, 'unreal/AegisWar/Content');
  const expected = { ...receipt.sourceHashes, ...receipt.layerHashes, [receipt.map]: receipt.mapSha256 } as Record<string, string>;
  if (!receipt.layerHashes || receipt.layers.some((name: string) => !receipt.layerHashes[name])) throw new Error('Scenario scenery layer verification is missing.');
  for (const [name, digest] of Object.entries(expected)) {
    if (!name.startsWith('/Game/')) throw new Error('Invalid scenery source');
    const file = path.resolve(content, `${name.slice(6)}.umap`);
    if (!file.startsWith(content + path.sep) || createHash('sha256').update(readFileSync(file)).digest('hex') !== digest)
      throw new Error('Scenario scenery is stale. Refresh it from the current capital before queuing.');
  }
  if (!receipt.navigationVerified || !receipt.visualVerified) throw new Error('Scenario scenery still requires navigation and visual verification.');
  return receipt.revision as string;
}

export interface HostOptions { directory: string; executable: string; project: string; port: number; bind: string; advertise: string; allowLan: boolean }
function lockJournal(directory: string) {
  mkdirSync(directory, { recursive: true });
  const file = path.join(directory, 'host.lock');
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const descriptor = openSync(file, 'wx', 0o600);
      try { writeFileSync(descriptor, String(process.pid)); } finally { closeSync(descriptor); }
      return () => { unlinkSync(file); };
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
      const pid = Number(readFileSync(file, 'utf8'));
      if (!Number.isInteger(pid) || pid <= 0) throw new Error('Invalid scenario host lock; inspect the private recovery directory.');
      try { process.kill(pid, 0); }
      catch (probe) {
        if ((probe as NodeJS.ErrnoException).code === 'ESRCH') { unlinkSync(file); continue; }
      }
      throw new Error('A scenario host already owns this recovery directory.');
    }
  }
  throw new Error('Could not acquire scenario recovery storage.');
}
export async function startScenarioHost(options: HostOptions) {
  if (!options.allowLan && !loopback(options.bind)) throw new Error('LAN binding requires explicit --allow-lan.');
  const unlock = lockJournal(options.directory);
  try {
  mkdirSync(options.directory, { recursive: true });
  const keyFile = path.join(options.directory, 'control-key');
  const key = existsSync(keyFile) ? readFileSync(keyFile, 'utf8') : randomBytes(32).toString('hex');
  if (!existsSync(keyFile)) writeFileSync(keyFile, key, { mode: 0o600 });
  const journal = path.join(options.directory, 'journal.json');
  let storageFailed = false;
  const coordinator = new ScenarioCoordinator(s => {
    try { atomicJson(journal, s); storageFailed = false; }
    catch (error) { storageFailed = true; throw error; }
  }, existsSync(journal) ? JSON.parse(readFileSync(journal, 'utf8')) as ScenarioJournal : undefined);
  const processes = new Map<string, ChildProcess>(), allocating = new Set<string>();
  const url = `http://${options.advertise}:${options.port}`;
  let stopped = false;
  const record = (action: () => void) => { try { action(); } catch { storageFailed = true; } };
  async function allocate(match: ScenarioMatch) {
    allocating.add(match.id);
    try {
      const contentRevision = verifyScenery();
      if (contentRevision !== coordinator.definition(match.scenario).contentRevision) throw new Error('Scenario catalog and installed city revision differ. Refresh the catalog and scenery together.');
      const port = await freePort(), directory = path.join(options.directory, 'instances', match.id);
      mkdirSync(directory, { recursive: true });
      const config = path.join(directory, 'instance.json'), log = path.join(directory, 'server.log');
      atomicJson(config, { url: `http://127.0.0.1:${options.port}`, match: match.id, key: match.serverKey,
        contentRevision, members: match.members.map(id => ({ id, realm: coordinator.player(id).character.realm })), allowLan: options.allowLan });
      const child = spawn(options.executable, [options.project, coordinator.definition(match.scenario).map,
        '-server', '-nullrhi', '-unattended', '-nop4', '-nosplash', '-WarDevelopmentNetworking', '-WarSiegePlaytest',
        `-WarScenarioInstance=${config}`, `-port=${port}`, `-MULTIHOME=${options.bind}`, `-abslog=${log}`, '-forcelogflush'], { windowsHide: true, stdio: 'ignore' });
      processes.set(match.id, child);
      child.on('error', () => { if (coordinator.state.matches[match.id]?.phase === 'running') record(() => coordinator.finish(match.id, 'Scenario process failed. Your campaign character is safe.')); });
      child.on('exit', () => { processes.delete(match.id); if (!stopped && coordinator.state.matches[match.id]?.phase === 'running') record(() => coordinator.finish(match.id, 'Scenario server stopped. Return to your campaign character.')); });
      const deadline = Date.now() + 180_000;
      while (Date.now() < deadline) {
        if (stopped || child.exitCode !== null || child.signalCode !== null) throw new Error('Scenario server stopped during startup.');
        const text = existsSync(log) ? readFileSync(log, 'utf8') : '';
        if (text.includes('WAR_SIEGE_CONTENT_BLOCKED')) throw new Error('Scenario map or models failed validation.');
        if (text.includes('WAR_SIEGE_CONTENT_READY') && text.includes('IpNetDriver listening on port')) {
          coordinator.allocated(match.id, `${options.advertise}:${port}`); return;
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      throw new Error('Scenario server startup timed out.');
    } catch (error) {
      processes.get(match.id)?.kill();
      record(() => coordinator.allocationFailed(match.id, error instanceof Error ? error.message : 'Scenario allocation failed.'));
    } finally { allocating.delete(match.id); }
  }
  const rates = new Map<string, { at: number; count: number }>();
  const server = createServer(async (request, response) => {
    response.setHeader('Content-Type', 'application/json'); response.setHeader('Cache-Control', 'no-store');
    try {
      if (storageFailed) throw new ScenarioError(503, 'Scenario recovery storage is temporarily unavailable. Please retry shortly.');
      const ip = request.socket.remoteAddress ?? '';
      if (!options.allowLan && !loopback(ip)) throw new ScenarioError(403, 'Remote scenario access is closed.');
      for (const [id, rate] of rates) if (Date.now() - rate.at > 60_000) rates.delete(id);
      const rate = rates.get(ip) ?? { at: Date.now(), count: 0 }; rate.count++; rates.set(ip, rate);
      if (rate.count > 3000 || rates.size > 256) throw new ScenarioError(429, 'Too many requests.');
      const route = new URL(request.url ?? '/', url).pathname;
      let result: unknown;
      if (route.startsWith('/host/')) {
        const peer = authenticateCampaignHost(options.directory, key, token(request), ip, options.allowLan);
        if (request.method !== 'POST') throw new ScenarioError(405, 'POST required.');
        const data = await body(request);
        if (peer) {
          const character = route === '/host/register' ? data : route === '/host/depart' ? data.character : undefined;
          if ((character && (character.id !== peer.id || character.realm !== peer.realm)) || (!character && data.id !== peer.id))
            throw new ScenarioError(403, 'Development identity is bound to another character or realm.');
        }
        if (route === '/host/register') result = coordinator.register(data);
        else if (route === '/host/depart') result = coordinator.depart(data.character, data.ticket);
        else if (route === '/host/released') result = coordinator.releaseCampaign(data.id, data.ticket);
        else if (route === '/host/restore') result = coordinator.restore(data.ticket, data.id);
        else if (route === '/host/restored') result = coordinator.completeRestore(data.ticket, data.id);
        else throw new ScenarioError(404, 'Unknown host route.');
      } else if (route.startsWith('/instance/')) {
        if (!loopback(ip)) throw new ScenarioError(403, 'Local instance required.');
        if (request.method !== 'POST') throw new ScenarioError(405, 'POST required.');
        const data = await body(request), match = coordinator.verifyServer(data.match, token(request));
        if (route === '/instance/consume') result = coordinator.consume(data.ticket, match.id, token(request));
        else if (route === '/instance/disconnect') { coordinator.disconnected(data.id, match.id, token(request)); result = {}; }
        else if (route === '/instance/finish') { coordinator.finish(match.id); result = {}; }
        else if (route === '/instance/roster') result = { phase: match.phase, members: match.members.map(id => ({ id, realm: coordinator.player(id).character.realm, phase: coordinator.player(id).phase })) };
        else throw new ScenarioError(404, 'Unknown instance route.');
      } else {
        const id = coordinator.authenticate(token(request));
        if (route === '/status' && request.method === 'GET') result = coordinator.view(id);
        else if (route === '/command' && request.method === 'POST') { const data = await body(request); result = coordinator.command(id, data.requestId, data.action, data.target); }
        else throw new ScenarioError(404, 'Unknown scenario route.');
      }
      response.end(JSON.stringify({ data: result }));
    } catch (error) {
      response.statusCode = error instanceof ScenarioError ? error.status : 500;
      response.end(JSON.stringify({ error: error instanceof ScenarioError ? error.message : 'Scenario host could not complete the request.' }));
    }
  });
  await new Promise<void>((resolve, reject) => { server.once('error', reject); server.listen(options.port, options.bind, resolve); });
  options = { ...options, port: (server.address() as AddressInfo).port };
  atomicJson(path.join(options.directory, 'host.json'), { url: `http://127.0.0.1:${options.port}`, key, allowLan: options.allowLan });
  const timer = setInterval(() => {
    try {
    if (storageFailed) { atomicJson(journal, coordinator.state); storageFailed = false; }
    coordinator.tick();
    for (const match of Object.values(coordinator.state.matches)) {
      if (match.phase === 'allocating' && !allocating.has(match.id)) void allocate(match);
      if (match.phase === 'finished' && processes.has(match.id)) { processes.get(match.id)?.kill(); processes.delete(match.id); }
      if (match.phase === 'running' && match.members.every(id => {
        const player = coordinator.player(id); return ['return', 'idle'].includes(player.phase) && player.possessionReleased !== false;
      })) coordinator.finish(match.id);
    }
    } catch { storageFailed = true; }
  }, 1000);
  return { server, coordinator, close: async () => {
    stopped = true; clearInterval(timer);
    for (const [id, child] of processes) { child.kill(); record(() => coordinator.finish(id, 'Scenario host stopped. Your character is recoverable.')); }
    await new Promise<void>(resolve => server.close(() => resolve()));
    try { if (storageFailed) atomicJson(journal, coordinator.state); } finally { unlock(); }
  } };
  } catch (error) { unlock(); throw error; }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const value = (name: string, fallback: string) => { const i = process.argv.indexOf(name); return i < 0 ? fallback : process.argv[i + 1]; };
  const engine = process.env.UNREAL_ENGINE_ROOT ?? 'C:/Program Files/Epic Games/UE_5.8';
  if (process.argv.includes('--provision-peer')) {
    const config = provisionDevelopmentPeer(path.join(root, 'unreal/AegisWar/Saved/ScenarioHost'), value('--provision-peer', ''),
      value('--realm', ''), value('--url', ''));
    console.log(`Private development character config created: ${config}`);
    process.exit(0);
  }
  const host = await startScenarioHost({ directory: path.join(root, 'unreal/AegisWar/Saved/ScenarioHost'),
    executable: value('--editor', path.join(engine, 'Engine/Binaries/Win64/UnrealEditor.exe')),
    project: path.join(root, 'unreal/AegisWar/AegisWar.uproject'), port: Number(value('--port', '8788')),
    bind: value('--bind', '127.0.0.1'), advertise: value('--advertise', '127.0.0.1'), allowLan: process.argv.includes('--allow-lan') });
  console.log('Scenario host ready. Launch the game, enter a character, then open Scenario from the in-game menu.');
  for (const signal of ['SIGINT', 'SIGTERM'] as const) process.once(signal, () => { void host.close().then(() => process.exit(0)); });
}
