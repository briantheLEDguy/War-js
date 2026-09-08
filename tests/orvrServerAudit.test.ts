import { afterEach, describe, expect, it, vi } from 'vitest';
import { once } from 'node:events';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { WebSocket } from 'ws';
import { startAuthority } from '../server/authority';
import { DevelopmentAuthenticator } from '../server/auth';
import { FileCampaignRepository, MemoryCampaignRepository } from '../server/persistence';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { createCampaign, defaultZoneConfig } from '../src/shared/orvr';
import type { CampaignEvent, CampaignState, ServerMessage } from '../src/shared/orvr';

class JournalRepository extends MemoryCampaignRepository {
  journals: CampaignEvent[][] = [];
  holdNext = false;
  unblock: (() => void) | null = null;
  override async commit(revision: number, state: CampaignState, events: CampaignEvent[] = []) {
    if (this.holdNext) {
      this.holdNext = false;
      await new Promise<void>(resolve => { this.unblock = resolve; });
    }
    this.journals.push(structuredClone(events));
    return super.commit(revision, state);
  }
}

describe('ORvR transport and persistence regressions', () => {
  const authorities: Awaited<ReturnType<typeof startAuthority>>[] = [];
  afterEach(async () => { await Promise.all(authorities.splice(0).map(authority => authority.close())); });

  async function connect(authority: Awaited<ReturnType<typeof startAuthority>>, credentials: { token: string; characterId: string }) {
    const socket = new WebSocket(authority.url, { origin: 'http://localhost:5173' });
    const messages: ServerMessage[] = [];
    socket.on('message', bytes => messages.push(JSON.parse(bytes.toString())));
    await once(socket, 'open');
    socket.send(JSON.stringify({ type: 'hello', version: 1, ...credentials, zoneId: 'sunmeadow_march' }));
    await vi.waitFor(() => expect(messages.some(message => message.type === 'snapshot')).toBe(true));
    return { socket, messages, id: credentials.characterId };
  }

  it('does not let a queued close from an old socket disconnect its replacement', async () => {
    const repository = new JournalRepository();
    const auth = new DevelopmentAuthenticator();
    const verify = vi.spyOn(auth, 'verify');
    const authority = await startAuthority({ port: 0, auth, repository, automaticTicks: false });
    authorities.push(authority);
    const credentials = auth.issue('aegis', 'Scout');
    const old = await connect(authority, credentials);
    repository.holdNext = true;
    const blocked = authority.step(5);
    await vi.waitFor(() => expect(repository.unblock).toBeTypeOf('function'));
    const replacing = connect(authority, credentials);
    await vi.waitFor(() => expect(verify).toHaveBeenCalledTimes(2));
    const oldClosed = once(old.socket, 'close');
    old.socket.close();
    await oldClosed;
    repository.unblock!();
    await blocked;
    const current = await replacing;
    await authority.step(.1);
    expect(current.socket.readyState).toBe(WebSocket.OPEN);
    expect(authority.inspect().players[current.id].connected).toBe(true);
    expect(Object.values(authority.inspect().players).filter(player => player.connected)).toHaveLength(1);
  });

  it('revalidates active credentials and closes a revoked session', async () => {
    const delegate = new DevelopmentAuthenticator();
    let revoked = false;
    const auth = { verify: async (token: string, characterId: string) => {
      if (revoked) throw new Error('Revoked');
      return delegate.verify(token, characterId);
    } };
    const authority = await startAuthority({ port: 0, auth, automaticTicks: false, reauthenticationMs: 20 });
    authorities.push(authority);
    const client = await connect(authority, delegate.issue('aegis', 'Scout'));
    const closed = once(client.socket, 'close');
    revoked = true;
    expect((await closed)[0]).toBe(1008);
    await vi.waitFor(() => expect(authority.inspect().players[client.id].connected).toBe(false));
  });

  it('coalesces combat writes but flushes its ordered journal before acknowledging a supply purchase', async () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.staging.aegis = config.staging.riftbound = { x: 0, y: 0, z: 80 };
    config.keeps[0].quartermaster = { ...config.staging.aegis };
    const state = createCampaign({ zones: [config] });
    const keep = state.zones.sunmeadow_march.keeps[config.keeps[0].id];
    keep.supplies = 500; keep.level = 2;
    const repository = new JournalRepository();
    repository.checkpoint = { revision: 1, state };
    const auth = new DevelopmentAuthenticator();
    const authority = await startAuthority({ port: 0, auth, repository, automaticTicks: false });
    authorities.push(authority);
    const a = await connect(authority, auth.issue('aegis', 'A'));
    const b = await connect(authority, auth.issue('riftbound', 'B'));
    const count = repository.journals.length;
    const activationId = authority.inspect().zones.sunmeadow_march.activationId;
    a.socket.send(JSON.stringify({ type: 'command', command: { version: 1, sequence: 1, activationId, action: { type: 'attack', targetId: b.id } } }));
    await vi.waitFor(() => expect(a.messages.some(message => message.type === 'result' && message.sequence === 1 && message.result.ok)).toBe(true));
    expect(repository.journals).toHaveLength(count);
    a.socket.send(JSON.stringify({ type: 'command', command: { version: 1, sequence: 2, activationId, action: { type: 'purchase', keepId: keep.id, equipment: 'ram' } } }));
    await vi.waitFor(() => expect(a.messages.some(message => message.type === 'result' && message.sequence === 2 && message.result.ok)).toBe(true));
    expect(repository.journals).toHaveLength(count + 1);
    const journal = repository.journals.at(-1)!;
    expect(journal.map(event => event.type)).toEqual(['damage', 'equipment_purchased']);
    expect(journal[0].id).toBeLessThan(journal[1].id);
    expect(repository.checkpoint!.state.zones.sunmeadow_march.keeps[keep.id].supplies).toBe(400);
  });

  it('sends static map configuration once per activation and limits subsequent wire updates', async () => {
    const auth = new DevelopmentAuthenticator();
    const authority = await startAuthority({ port: 0, auth, automaticTicks: false, campaign: { zones: await loadCampaignMapConfigs() } });
    authorities.push(authority);
    const client = await connect(authority, auth.issue('aegis', 'Scout'));
    await authority.step(.05); await authority.step(.05);
    await vi.waitFor(() => expect(client.messages.some(message => message.type === 'update')).toBe(true));
    const first = client.messages.find(message => message.type === 'snapshot')!;
    const update = client.messages.find(message => message.type === 'update')!;
    expect(first.type === 'snapshot' && first.snapshot.zone?.config.terrain).toBeDefined();
    expect(update.type === 'update' && update.snapshot.zone && 'config' in update.snapshot.zone).toBe(false);
    expect(Buffer.byteLength(JSON.stringify(update))).toBeLessThan(Buffer.byteLength(JSON.stringify(first)) * .65);
    expect(Buffer.byteLength(JSON.stringify(update))).toBeLessThan(8_000);
    client.socket.send(JSON.stringify({ type: 'command', command: {
      version: 1, sequence: 1, activationId: authority.inspect().zones.sunmeadow_march.activationId,
      action: { type: 'transfer', zoneId: 'ashen_steppe' },
    } }));
    await vi.waitFor(() => expect(client.messages.some(message => message.type === 'result' && message.result.ok)).toBe(true));
    await authority.step(.05); await authority.step(.05);
    await vi.waitFor(() => expect(client.messages.some(message => message.type === 'snapshot' && message.snapshot.zone?.id === 'ashen_steppe')).toBe(true));
  });

  it('recovers a file lease only when its recorded process no longer exists', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'war-orvr-lease-'));
    const filename = join(directory, 'campaign.json');
    const repository = new FileCampaignRepository(filename);
    try {
      const child = spawn(process.execPath, ['-e', 'process.exit(0)'], { windowsHide: true });
      const pid = child.pid;
      await once(child, 'exit');
      expect(pid).toBeTypeOf('number');
      await writeFile(`${filename}.lock`, JSON.stringify({ pid }));
      expect(await repository.load()).toBeNull();
      await repository.commit(0, createCampaign());
      expect((await repository.load().catch(error => error)).message).toMatch(/already open/);
    } finally { await repository.close(); await rm(directory, { recursive: true, force: true }); }
  });
});
