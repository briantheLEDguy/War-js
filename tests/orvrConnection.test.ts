import { afterEach, describe, expect, it, vi } from 'vitest';
import { CampaignConnection, campaignHttpUrl } from '../src/game/network/CampaignConnection';
import { addPlayer, createCampaign, snapshotFor, type ServerMessage, type WorldSnapshot } from '../src/shared/orvr';

class Socket {
  static OPEN = 1;
  static CLOSING = 2;
  static instances: Socket[] = [];
  readyState = 1;
  messages: string[] = [];
  onopen?: () => void;
  onmessage?: (event: { data: string }) => void;
  onclose?: (event: { code: number; reason: string }) => void;
  constructor(readonly url: string) { Socket.instances.push(this); }
  send(value: string) { this.messages.push(value); }
  close() { this.readyState = 3; this.onclose?.({ code: 1000, reason: '' }); }
  receive(message: ServerMessage) { this.onmessage?.({ data: JSON.stringify(message) }); }
}
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); Socket.instances = []; });
const move = { type: 'move', direction: { x: 1, z: 0 } } as const;
function authenticated() {
  vi.stubGlobal('WebSocket', Socket);
  const connection = new CampaignConnection('ws://localhost:8788/orvr', { token: 'test-token', characterId: 'player' });
  connection.connect();
  const socket = Socket.instances[0]; socket.onopen?.();
  const state = createCampaign();
  addPlayer(state, { id: 'player', userId: 'account', characterId: 'player', realm: 'aegis' });
  const snapshot = snapshotFor(state, 'player');
  socket.receive({ type: 'snapshot', snapshot });
  return { connection, socket, snapshot };
}
describe('campaign transport', () => {
  it('blocks actions before authentication and rehydrates same-activation updates', () => {
    vi.stubGlobal('WebSocket', Socket);
    const connection = new CampaignConnection('ws://localhost:8788/orvr', { token: 'test-token', characterId: 'player' });
    connection.connect();
    const socket = Socket.instances[0]; socket.onopen?.();
    expect(connection.send({ type: 'move', direction: { x: 1, z: 0 } })).toBe(false);
    const state = createCampaign();
    addPlayer(state, { id: 'player', userId: 'account', characterId: 'player', realm: 'aegis' });
    const initial = snapshotFor(state, 'player');
    socket.receive({ type: 'snapshot', snapshot: initial });
    expect(connection.send({ type: 'move', direction: { x: 1, z: 0 } })).toBe(true);
    const { config: _config, ...zone } = initial.zone!;
    socket.receive({ type: 'update', snapshot: { ...initial, seconds: 8, zone } });
    expect(connection.snapshot?.seconds).toBe(8);
    expect(connection.snapshot?.zone?.config).toEqual(initial.zone!.config);
    socket.receive({ type: 'update', snapshot: { ...initial, seconds: 9, zone: { ...zone, activationId: 'stale' } } });
    expect(connection.snapshot?.seconds).toBe(8);
    connection.close();
  });
  it('derives same-host HTTPS from WSS without retaining query parameters', () => {
    expect(campaignHttpUrl('wss://campaign.example/orvr?debug=yes')).toBe('https://campaign.example');
  });
  it('pauses commands through transfer acknowledgement until the destination snapshot arrives', () => {
    const { connection, socket, snapshot } = authenticated();
    connection.onNotice = vi.fn();
    expect(connection.send(move)).toBe(true);
    expect(connection.send({ type: 'transfer', zoneId: 'ashen_steppe' })).toBe(true);
    expect(connection.send(move)).toBe(false);
    socket.receive({ type: 'result', sequence: 1, result: { ok: false, code: 'stale_activation' } });
    expect(connection.onNotice).not.toHaveBeenCalled();
    socket.receive({ type: 'result', sequence: 2, result: { ok: true } });
    socket.receive({ type: 'snapshot', snapshot });
    expect(connection.send(move)).toBe(false);
    const next: WorldSnapshot = { ...snapshot, zone: { ...snapshot.zone!, id: 'ashen_steppe', activationId: 'next-activation', config: { ...snapshot.zone!.config, id: 'ashen_steppe' } } };
    socket.receive({ type: 'snapshot', snapshot: next });
    expect(connection.send(move)).toBe(true);
    expect(JSON.parse(socket.messages.at(-1)!).command.activationId).toBe('next-activation');
    connection.close();
  });
  it('releases a rejected transfer and preserves purchase rejection notices', () => {
    const { connection, socket, snapshot } = authenticated();
    connection.onNotice = vi.fn();
    connection.send({ type: 'transfer', zoneId: 'ashen_steppe' });
    socket.receive({ type: 'result', sequence: 1, result: { ok: false, code: 'staging_required' } });
    expect(connection.onNotice).toHaveBeenCalledWith('staging required');
    expect(connection.send({ type: 'purchase', keepId: snapshot.zone!.config.keeps[0].id, equipment: 'ram' })).toBe(true);
    socket.receive({ type: 'result', sequence: 2, result: { ok: false, code: 'stale_activation' } });
    expect(connection.onNotice).toHaveBeenCalledWith('stale activation');
    connection.close();
  });
  it('ignores stale sockets and requires a full snapshot after reconnect', () => {
    vi.useFakeTimers();
    const { connection, socket, snapshot } = authenticated();
    connection.connect();
    expect(Socket.instances).toHaveLength(1);
    socket.close();
    vi.advanceTimersByTime(500);
    const replacement = Socket.instances[1]; replacement.onopen?.();
    socket.receive({ type: 'snapshot', snapshot: { ...snapshot, seconds: 999 } });
    socket.onclose?.({ code: 1008, reason: 'old session expired' });
    const { config: _config, ...zone } = snapshot.zone!;
    replacement.receive({ type: 'update', snapshot: { ...snapshot, seconds: 888, zone } });
    expect(connection.snapshot?.seconds).toBe(snapshot.seconds);
    expect(connection.send(move)).toBe(false);
    replacement.receive({ type: 'snapshot', snapshot });
    expect(connection.send(move)).toBe(true);
    vi.advanceTimersByTime(10000);
    expect(Socket.instances).toHaveLength(2);
    connection.close();
  });
  it('reauthenticates refreshed tokens on a new socket and ignores the old connection', () => {
    const { connection, socket, snapshot } = authenticated();
    connection.updateToken('fresh-token');
    expect(socket.readyState).toBe(3);
    const replacement = Socket.instances[1]; replacement.onopen?.();
    expect(JSON.parse(replacement.messages[0]).token).toBe('fresh-token');
    expect(connection.send(move)).toBe(false);
    socket.receive({ type: 'error', code: 'authority_unavailable', message: 'Old error' });
    replacement.receive({ type: 'snapshot', snapshot });
    expect(connection.send(move)).toBe(true);
    connection.updateToken('fresh-token');
    expect(Socket.instances).toHaveLength(2);
    connection.close();
  });
  it('cancels pending reconnects on close and ignores malformed packets', () => {
    vi.useFakeTimers();
    const { connection, socket } = authenticated();
    expect(() => socket.onmessage?.({ data: 'null' })).not.toThrow();
    expect(() => socket.onmessage?.({ data: '{' })).not.toThrow();
    socket.close();
    connection.close();
    vi.advanceTimersByTime(10000);
    expect(Socket.instances).toHaveLength(1);
    expect(connection.send(move)).toBe(false);
  });
});
