import type { IncomingMessage, ServerResponse } from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import { DevelopmentError, DevelopmentService, record } from './service';

async function readBody(request: IncomingMessage): Promise<any> {
  const chunks: Buffer[] = []; let length = 0;
  for await (const chunk of request) {
    length += chunk.length;
    if (length > 9_000_000) throw new DevelopmentError(413, 'Request too large.');
    chunks.push(Buffer.from(chunk));
  }
  try { return record(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
  catch (error) { if (error instanceof DevelopmentError) throw error; throw new DevelopmentError(400, 'Invalid JSON.'); }
}
function bearer(request: IncomingMessage): string {
  const auth = request.headers.authorization;
  if (!auth?.startsWith('Bearer ') || auth.length > 16_384) throw new DevelopmentError(401, 'Authentication required.');
  return auth.slice(7);
}
export function privateKeyMatches(provided: string, expected: string): boolean {
  const actual = Buffer.from(provided), wanted = Buffer.from(expected);
  return wanted.length >= 32 && actual.length === wanted.length && timingSafeEqual(actual, wanted);
}
export function developmentHandler(service: DevelopmentService, internal?: { key: string; runId: string; serverId: string }) {
  // Bounded admission-rate protection. The private VPN is an additional boundary.
  const windows = new Map<string, { start: number; count: number }>();
  return async (request: IncomingMessage, response: ServerResponse) => {
    response.setHeader('Content-Type', 'application/json');
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    try {
      const ip = request.socket.remoteAddress ?? 'unknown', now = Date.now();
      for (const [key, value] of windows) if (now - value.start > 60_000) windows.delete(key);
      const rate = windows.get(ip) ?? { start: now, count: 0 };
      if (++rate.count > 600 || windows.size > 1000) throw new DevelopmentError(429, 'Too many requests.');
      windows.set(ip, rate);
      const path = new URL(request.url ?? '/', 'https://development.invalid').pathname;
      let result: unknown;
      if (internal) {
        if (!['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(ip)
          || !privateKeyMatches(bearer(request), internal.key)) throw new DevelopmentError(403, 'Server authentication required.');
        const body = await readBody(request);
        if (request.method !== 'POST') throw new DevelopmentError(405, 'POST required.');
        if (path === '/claim') result = await service.claim(internal.runId, internal.serverId, body.epoch);
        else if (path === '/consume') result = await service.consume(body.ticket, internal.runId, internal.serverId, body.epoch);
        else if (path === '/member') result = await service.member(body.userId);
        else if (path === '/ability-server') result = await service.abilityServer(internal.runId, internal.serverId, body);
        else if (path === '/checkpoint') result = await service.checkpoint(body.actorId, internal.runId, internal.serverId,
          body.epoch, body.revision, body.document, body.requestId);
        else throw new DevelopmentError(404, 'Unknown server route.');
      } else {
        const member = await service.identity(bearer(request));
        if (request.method === 'GET' && path === '/session') result = { userId: member.user_id,
          status: member.status, role: member.role, generation: member.generation, admissionOpen: service.admissionOpen };
        else if (request.method === 'GET' && /^\/abilities\/[a-z0-9_-]+\/(workspaces|versions|deployments|tests)(\/[0-9a-f-]+)?$/.test(path)) {
          const [, , environment, kind, id] = path.split('/'); result = await service.readAbilities(member, environment, kind, id);
        } else if (request.method === 'GET' && /^\/(drafts|versions|runs)(\/[0-9a-f-]+)?$/.test(path)) {
          const [,kind,id] = path.split('/'); result = await service.read(member, kind, id);
        } else if (request.method === 'POST' && path === '/operations') {
          const body = await readBody(request); result = await service.userOperation(member, body.requestId, body.action, body.body);
        } else if (request.method === 'POST' && path === '/join') result = await service.issue(member, await readBody(request));
        else throw new DevelopmentError(404, 'Unknown route.');
      }
      response.end(JSON.stringify({ data: result }));
    } catch (error) {
      response.statusCode = error instanceof DevelopmentError ? error.status : 500;
      response.end(JSON.stringify({ error: error instanceof DevelopmentError ? error.message : 'Request failed.' }));
    }
  };
}
