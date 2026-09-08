import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { WebSocketServer, WebSocket } from 'ws';
import {
  createCampaign, restoreCampaign, addPlayer, removePlayer, submitCommand, advanceSimulation, snapshotFor,
  type CampaignState, type CampaignConfig, type ClientMessage, type ServerMessage, type CampaignEvent, type WorldUpdate,
} from '../src/shared/orvr';
import { DevelopmentAuthenticator, type Authenticator } from './auth';
import { MemoryCampaignRepository, type CampaignRepository } from './persistence';
import { assertCampaignConfigCompatible } from './configCompatibility';

export interface AuthorityOptions {
  host?: string;
  port?: number;
  allowedOrigins?: string[];
  auth: Authenticator;
  repository?: CampaignRepository;
  campaign?: CampaignConfig;
  /** Tests may drive the actual authoritative tick without sleeping. Never accepted from clients. */
  automaticTicks?: boolean;
  reauthenticationMs?: number;
}
interface Connection {
  socket: WebSocket; playerId: string | null; userId: string | null; authenticating: boolean; count: number; windowStart: number;
  token: string | null; characterId: string | null; nextAuthCheckAt: number; revalidating: boolean;
  snapshotKey: string | null;
}

const CRITICAL_EVENTS = new Set([
  'supplies_delivered', 'equipment_purchased', 'gate_repaired', 'objective_captured', 'keep_captured',
  'zone_won', 'front_advanced', 'central_breakthrough', 'city_siege_opened', 'campaign_ended', 'campaign_started',
]);

export async function startAuthority(options: AuthorityOptions) {
  const host = options.host ?? '127.0.0.1';
  const development = options.auth instanceof DevelopmentAuthenticator;
  if (development && !['127.0.0.1', '::1', 'localhost'].includes(host)) throw new Error('Development authentication requires a loopback-only bind.');
  const repository: CampaignRepository = options.repository ?? new MemoryCampaignRepository();
  let state: CampaignState;
  let revision: number;
  try {
    const loaded = await repository.load();
    state = loaded ? restoreCampaign(loaded.state) : createCampaign(options.campaign);
    if (loaded && options.campaign) assertCampaignConfigCompatible(state, options.campaign);
    revision = loaded?.revision ?? 0;
    for (const player of Object.values(state.players)) removePlayer(state, player.id);
  } catch (error) {
    await repository.close?.();
    throw error;
  }
  let durableState = structuredClone(state);
  const connections = new Set<Connection>();
  const sessions = new Map<string, Connection>();
  const origins = new Set(options.allowedOrigins ?? ['http://localhost:5173', 'http://127.0.0.1:5173']);
  let closed = false;
  let failed: string | null = null;
  let queue = Promise.resolve();
  let checkpointSeconds = 0;
  let frames = 0;
  let lastStepMs = 0;
  let pendingEvents: CampaignEvent[] = [];
  const reauthenticationMs = Math.max(10, options.reauthenticationMs ?? 60_000);
  const verifySession = async (token: string, characterId: string) => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      return await Promise.race([
        options.auth.verify(token, characterId),
        new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error('Authentication timed out.')), 10_000); timer.unref(); }),
      ]);
    } finally { if (timer) clearTimeout(timer); }
  };
  const enqueue = (work: () => Promise<void>) => {
    queue = queue.then(work).catch(error => {
      state = structuredClone(durableState);
      pendingEvents = [];
      failed = error instanceof Error ? error.message : 'Authority error';
      for (const connection of connections) send(connection.socket, { type: 'error', code: 'authority_unavailable', message: 'The campaign is paused while its server recovers.' });
      console.error('[orvr] Authority paused:', failed);
    });
    return queue;
  };
  const save = async (events: CampaignEvent[]) => {
    pendingEvents.push(...events);
    revision = await repository.commit(revision, state, pendingEvents);
    pendingEvents = [];
    durableState = structuredClone(state);
    checkpointSeconds = 0;
  };
  const publish = () => {
    for (const connection of connections) {
      if (connection.playerId && connection.socket.bufferedAmount < 512_000) {
        const snapshot = snapshotFor(state, connection.playerId);
        const key = `${snapshot.round}:${snapshot.zone?.id}:${snapshot.zone?.activationId}`;
        if (connection.snapshotKey !== key) {
          send(connection.socket, { type: 'snapshot', snapshot });
          connection.snapshotKey = key;
        } else {
          let dynamicZone: WorldUpdate['zone'] = null;
          if (snapshot.zone) {
            const { config: _config, ...zone } = snapshot.zone;
            dynamicZone = zone;
          }
          send(connection.socket, { type: 'update', snapshot: { ...snapshot, zone: dynamicZone } });
        }
      } else if (connection.socket.bufferedAmount >= 512_000) connection.socket.close(1013, 'Connection is too slow; reconnect to resume.');
    }
  };
  const http = createServer(async (request, response) => {
    const origin = request.headers.origin;
    if (origin && !origins.has(origin)) return json(response, 403, { error: 'Origin denied.' });
    if (origin) { response.setHeader('Access-Control-Allow-Origin', origin); response.setHeader('Vary', 'Origin'); }
    if (request.method === 'OPTIONS') {
      response.setHeader('Access-Control-Allow-Methods', 'POST,GET,OPTIONS');
      response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      response.writeHead(204).end(); return;
    }
    if (request.url === '/health' && request.method === 'GET') return json(response, failed ? 503 : 200, {
      ready: !failed, protocol: 1, phase: state.phase, connections: connections.size, frames, lastStepMs,
      authentication: development ? 'development-loopback' : 'supabase',
    });
    if (request.url === '/dev/session' && request.method === 'POST' && options.auth instanceof DevelopmentAuthenticator) {
      const address = request.socket.remoteAddress;
      if (!['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(address ?? '')) return json(response, 403, { error: 'Local development only.' });
      try {
        const body = await bodyJson(request);
        if (body.realm !== 'aegis' && body.realm !== 'riftbound') return json(response, 400, { error: 'Choose a valid realm.' });
        return json(response, 200, options.auth.issue(body.realm, typeof body.name === 'string' ? body.name : ''));
      } catch { return json(response, 400, { error: 'Invalid request.' }); }
    }
    json(response, 404, { error: 'Not found.' });
  });
  const wss = new WebSocketServer({ noServer: true, maxPayload: 16_384, perMessageDeflate: false });
  http.on('upgrade', (request, socket, head) => {
    if (request.url !== '/orvr' || (request.headers.origin && !origins.has(request.headers.origin))) {
      socket.write('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'); socket.destroy(); return;
    }
    wss.handleUpgrade(request, socket, head, ws => wss.emit('connection', ws, request));
  });
  wss.on('connection', (socket: WebSocket) => {
    const connection: Connection = { socket, playerId: null, userId: null, authenticating: false, count: 0, windowStart: Date.now(),
      token: null, characterId: null, nextAuthCheckAt: 0, revalidating: false, snapshotKey: null };
    connections.add(connection);
    const timeout = setTimeout(() => { if (!connection.playerId) socket.close(1008, 'Authentication required.'); }, 10_000);
    socket.on('error', () => { /* Closing the socket below releases its authoritative session. */ });
    socket.on('message', (bytes, binary) => {
      if (binary || closed || failed) return;
      const now = Date.now();
      if (now - connection.windowStart > 1000) { connection.count = 0; connection.windowStart = now; }
      if (++connection.count > 80) { socket.close(1008, 'Command rate exceeded.'); return; }
      let message: ClientMessage;
      try { message = JSON.parse(bytes.toString()); } catch { socket.close(1007, 'Invalid JSON.'); return; }
      if (!message || typeof message !== 'object') { socket.close(1007, 'Invalid message.'); return; }
      if (message.type === 'hello') {
        if (connection.playerId || connection.authenticating || message.version !== 1 || typeof message.token !== 'string' || typeof message.characterId !== 'string') {
          socket.close(1008, 'Invalid authentication request.'); return;
        }
        connection.authenticating = true;
        void verifySession(message.token, message.characterId).then(identity => enqueue(async () => {
          if (socket.readyState !== WebSocket.OPEN || failed || closed) return;
          // One active character per account. Reconnection replaces the old transport, never duplicates a body.
          for (const previous of sessions.values()) if (previous !== connection && previous.userId === identity.userId) {
            if (previous.playerId) removePlayer(state, previous.playerId);
            if (previous.playerId) sessions.delete(previous.playerId);
            previous.socket.close(4001, 'Session resumed elsewhere.');
            previous.playerId = null;
          }
          const prior = state.players[identity.id];
          if (prior && (prior.userId !== identity.userId || prior.characterId !== identity.characterId || prior.realm !== identity.realm)) {
            send(socket, { type: 'error', code: 'identity_mismatch', message: 'This character no longer matches its campaign session.' });
            socket.close(1008, 'Character identity changed.'); return;
          }
          const result = addPlayer(state, { ...identity, zoneId: typeof message.zoneId === 'string' ? message.zoneId : undefined });
          if (!result.ok) { send(socket, { type: 'error', code: result.code ?? 'join_failed', message: 'Unable to join this campaign.' }); socket.close(1008, 'Unable to join.'); return; }
          connection.playerId = identity.id;
          connection.userId = identity.userId;
          connection.token = message.token;
          connection.characterId = message.characterId;
          connection.nextAuthCheckAt = Date.now() + reauthenticationMs;
          sessions.set(identity.id, connection);
          clearTimeout(timeout);
          await save(result.events);
          publish();
        })).catch(() => { send(socket, { type: 'error', code: 'authentication_failed', message: 'Please sign in again.' }); socket.close(1008, 'Authentication failed.'); });
        return;
      }
      if (!connection.playerId) { socket.close(1008, 'Authentication required.'); return; }
      if (message.type === 'ping' && typeof message.nonce === 'string' && message.nonce.length < 100) {
        send(socket, { type: 'pong', nonce: message.nonce }); return;
      }
      if (message.type !== 'command' || !message.command || typeof message.command !== 'object') {
        socket.close(1008, 'Unknown command.'); return;
      }
      const command = message.command;
      void enqueue(async () => {
        if (!connection.playerId || failed || closed || sessions.get(connection.playerId) !== connection || socket.readyState !== WebSocket.OPEN) return;
        const result = submitCommand(state, connection.playerId, command);
        if (result.events.some(event => CRITICAL_EVENTS.has(event.type))) await save(result.events);
        else pendingEvents.push(...result.events);
        send(socket, { type: 'result', sequence: command.sequence, result });
      });
    });
    socket.on('close', () => {
      clearTimeout(timeout); connections.delete(connection);
      if (!connection.playerId || closed) return;
      const playerId = connection.playerId;
      void enqueue(async () => {
        if (failed || sessions.get(playerId) !== connection) return;
        sessions.delete(playerId);
        const result = removePlayer(state, playerId);
        await save(result.events); publish();
      });
    });
  });
  const step = (seconds = .05) => enqueue(async () => {
    if (closed || failed) return;
    const started = performance.now();
    const events = advanceSimulation(state, seconds);
    checkpointSeconds += seconds;
    if (events.some(event => CRITICAL_EVENTS.has(event.type)) || checkpointSeconds >= 5) await save(events);
    else pendingEvents.push(...events);
    frames++;
    if (frames % 2 === 0 || events.length) publish();
    lastStepMs = performance.now() - started;
  });
  try {
    await new Promise<void>((resolve, reject) => { http.once('error', reject); http.listen(options.port ?? 8788, host, () => resolve()); });
  } catch (error) {
    wss.close();
    await repository.close?.();
    throw error;
  }
  const revalidate = () => {
    for (const connection of connections) {
      if (closed || failed || !connection.playerId || !connection.token || !connection.characterId || connection.revalidating
        || connection.nextAuthCheckAt > Date.now() || sessions.get(connection.playerId) !== connection) continue;
      connection.revalidating = true;
      const playerId = connection.playerId;
      void verifySession(connection.token, connection.characterId).then(identity => enqueue(async () => {
        if (sessions.get(playerId) !== connection || closed) return;
        const player = state.players[playerId];
        if (identity.id !== playerId || identity.userId !== player?.userId || identity.characterId !== player.characterId || identity.realm !== player.realm) {
          connection.socket.close(1008, 'Character identity changed.'); return;
        }
        connection.nextAuthCheckAt = Date.now() + reauthenticationMs;
      })).catch(() => {
        if (sessions.get(playerId) === connection) connection.socket.close(1008, 'Session expired; sign in again.');
      }).finally(() => { connection.revalidating = false; });
    }
  };
  const authInterval = setInterval(revalidate, Math.min(1_000, reauthenticationMs));
  let ticking = false;
  const interval = options.automaticTicks === false ? null : setInterval(() => {
    if (ticking) return;
    ticking = true;
    void step().finally(() => { ticking = false; });
  }, 50);
  const address = http.address();
  if (!address || typeof address === 'string') throw new Error('Authority did not bind a TCP port.');
  return {
    url: `ws://${host.includes(':') ? `[${host}]` : host}:${address.port}/orvr`,
    httpUrl: `http://${host.includes(':') ? `[${host}]` : host}:${address.port}`,
    step,
    inspect: () => structuredClone(state),
    async close() {
      if (closed) return;
      closed = true;
      if (interval) clearInterval(interval);
      clearInterval(authInterval);
      for (const connection of connections) connection.socket.terminate();
      await queue;
      for (const player of Object.values(state.players)) removePlayer(state, player.id);
      try { if (!failed) await save([]); } finally { await repository.close?.(); }
      wss.close();
      await new Promise<void>(resolve => http.close(() => resolve()));
    },
  };
}

function send(socket: WebSocket, message: ServerMessage): void {
  if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}
function json(response: ServerResponse, status: number, value: unknown): void {
  response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }).end(JSON.stringify(value));
}
async function bodyJson(request: IncomingMessage): Promise<Record<string, unknown>> {
  let text = '';
  for await (const chunk of request) { text += chunk; if (text.length > 4096) throw new Error('Request too large.'); }
  return JSON.parse(text);
}
