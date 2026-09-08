import { afterEach, describe, expect, it, vi } from 'vitest';
import { WebSocket } from 'ws';
import { once } from 'node:events';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startAuthority } from '../server/authority';
import { DevelopmentAuthenticator } from '../server/auth';
import { FileCampaignRepository, MemoryCampaignRepository } from '../server/persistence';
import { createCampaign, type ServerMessage, type Realm } from '../src/shared/orvr';

describe('shared ORvR WebSocket authority', () => {
  const servers: Awaited<ReturnType<typeof startAuthority>>[] = [];
  afterEach(async () => { await Promise.all(servers.splice(0).map(server => server.close())); });
  async function server(repository = new MemoryCampaignRepository()) {
    const auth = new DevelopmentAuthenticator();
    const authority = await startAuthority({ port: 0, auth, repository, automaticTicks: false });
    servers.push(authority);
    return { authority, auth, repository };
  }
  async function connect(authority: Awaited<ReturnType<typeof startAuthority>>, auth: DevelopmentAuthenticator, realm: Realm = 'aegis', credentials = auth.issue(realm, 'Scout')) {
    const socket = new WebSocket(authority.url, { origin: 'http://localhost:5173' });
    const messages: ServerMessage[] = [];
    socket.on('message', bytes => messages.push(JSON.parse(bytes.toString())));
    await once(socket, 'open');
    socket.send(JSON.stringify({ type: 'hello', version: 1, ...credentials, zoneId: 'sunmeadow_march' }));
    await vi.waitFor(() => expect(messages.some(message => message.type === 'snapshot')).toBe(true));
    return { socket, messages, id: credentials.characterId, credentials };
  }
  it('authenticates 36 actual sockets, enforces 18 per realm, queues overflow and rejects replay', async () => {
    const { authority, auth, repository } = await server();
    const clients = await Promise.all(Array.from({ length: 36 }, (_, i) => connect(authority, auth, i < 18 ? 'aegis' : 'riftbound')));
    const extra = await connect(authority, auth);
    expect(Object.values(authority.inspect().players).filter(player => !player.queued)).toHaveLength(36);
    expect(authority.inspect().players[extra.id].queued).toBe(true);
    const first = clients[0];
    const activationId = authority.inspect().zones.sunmeadow_march.activationId;
    const command = { version: 1, sequence: 1, activationId, action: { type: 'move', direction: { x: 1, z: 0 } } };
    first.socket.send(JSON.stringify({ type: 'command', command }));
    first.socket.send(JSON.stringify({ type: 'command', command }));
    await vi.waitFor(() => expect(first.messages.filter(message => message.type === 'result')).toHaveLength(2));
    const results = first.messages.filter(message => message.type === 'result');
    expect(results[0].result.ok).toBe(true);
    expect(results[1].result.ok).toBe(false);
    expect(repository.checkpoint?.state.players[first.id].userId).toBe(first.id);
    clients[1].socket.close();
    await vi.waitFor(() => expect(authority.inspect().players[extra.id].queued).toBe(false));
    await authority.step(.1);
    expect((await (await fetch(`${authority.httpUrl}/health`)).json()).ready).toBe(true);
  }, 15_000);
  it('reconnects one identity without a duplicate body and denies forged authentication', async () => {
    const { authority, auth } = await server();
    const first = await connect(authority, auth);
    const activationId = authority.inspect().zones.sunmeadow_march.activationId;
    const command = { version: 1, sequence: 7, activationId, action: { type: 'move', direction: { x: 1, z: 0 } } };
    first.socket.send(JSON.stringify({ type: 'command', command }));
    await vi.waitFor(() => expect(authority.inspect().players[first.id].lastSequence).toBe(7));
    await authority.step(.2);
    const position = authority.inspect().players[first.id].position;
    const resumed = await connect(authority, auth, 'aegis', first.credentials);
    await vi.waitFor(() => expect(first.socket.readyState).toBe(WebSocket.CLOSED));
    expect(Object.values(authority.inspect().players).filter(player => player.connected)).toHaveLength(1);
    expect(authority.inspect().players[resumed.id].connected).toBe(true);
    expect(authority.inspect().players[resumed.id].position).toEqual(position);
    expect(authority.inspect().players[resumed.id].lastSequence).toBe(7);
    expect(authority.inspect().players[resumed.id].direction).toEqual({ x: 0, z: 0 });
    resumed.socket.send(JSON.stringify({ type: 'command', command }));
    await vi.waitFor(() => expect(resumed.messages.some(message => message.type === 'result' && !message.result.ok)).toBe(true));
    const forged = new WebSocket(authority.url);
    await once(forged, 'open');
    const closed = once(forged, 'close');
    forged.send(JSON.stringify({ type: 'hello', version: 1, characterId: first.id, token: first.credentials.token + 'x' }));
    expect((await closed)[0]).toBe(1008);
  });
  it('pauses and restores the last durable state when persistence fails', async () => {
    const { authority, auth, repository } = await server();
    const client = await connect(authority, auth);
    const durable = structuredClone(repository.checkpoint!.state);
    const log = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(repository, 'commit').mockRejectedValue(new Error('Database unavailable'));
    await authority.step(5);
    expect(authority.inspect()).toEqual(durable);
    expect((await fetch(`${authority.httpUrl}/health`)).status).toBe(503);
    await vi.waitFor(() => expect(client.messages.some(message => message.type === 'error' && message.code === 'authority_unavailable')).toBe(true));
    log.mockRestore();
  });
  it('writes atomic file checkpoints and rejects a second live writer', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'war-orvr-'));
    const filename = join(directory, 'campaign.json');
    const first = new FileCampaignRepository(filename);
    const second = new FileCampaignRepository(filename);
    try {
      expect(await first.load()).toBeNull();
      await expect(second.load()).rejects.toThrow();
      const state = createCampaign();
      await first.commit(0, state);
      expect(JSON.parse(await readFile(filename, 'utf8')).state.id).toBe(state.id);
      await first.close();
      expect((await second.load())?.revision).toBe(1);
    } finally { await first.close(); await second.close(); await rm(directory, { recursive: true, force: true }); }
  });
});
