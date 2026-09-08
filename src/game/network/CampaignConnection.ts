import type { PlayerAction, ServerMessage, WorldSnapshot } from '../../shared/orvr/protocol';

export interface CampaignCredentials { token: string; characterId: string }
export type ConnectionStatus = 'connecting' | 'online' | 'reconnecting' | 'closed';

export class CampaignConnection {
  private socket: WebSocket | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;
  private attempt = 0;
  private sequence = 0;
  private ready = false;
  private pendingTransfer: { sequence: number; zoneId: string; previousActivation: string } | null = null;
  private sentActions = new Map<number, PlayerAction['type']>();
  snapshot: WorldSnapshot | null = null;
  onSnapshot: (snapshot: WorldSnapshot) => void = () => undefined;
  onStatus: (status: ConnectionStatus) => void = () => undefined;
  onNotice: (message: string) => void = () => undefined;
  constructor(readonly url: string, private readonly credentials: CampaignCredentials) { this.credentials = { ...credentials }; }
  connect(): void {
    if (this.closed || (this.socket && this.socket.readyState < WebSocket.CLOSING)) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.ready = false;
    this.pendingTransfer = null;
    this.sentActions.clear();
    this.onStatus(this.attempt ? 'reconnecting' : 'connecting');
    let socket: WebSocket;
    try { socket = new WebSocket(this.url); }
    catch { this.onNotice('The campaign server address is invalid.'); this.close(); return; }
    this.socket = socket;
    let receivedSnapshot = false;
    const current = () => !this.closed && this.socket === socket;
    socket.onopen = () => {
      if (!current()) return;
      this.ready = false;
      this.sequence = 0;
      socket.send(JSON.stringify({ type: 'hello', version: 1, ...this.credentials }));
    };
    socket.onmessage = event => {
      if (!current()) return;
      let message: ServerMessage;
      try { message = JSON.parse(event.data); } catch { return; }
      if (!message || typeof message !== 'object') return;
      if (message.type === 'update') {
        if (!receivedSnapshot || !message.snapshot) return;
        const previous = this.snapshot?.zone;
        const next = message.snapshot.zone;
        if (next && (!previous || next.id !== previous.id || next.activationId !== previous.activationId)) return;
        const snapshot: WorldSnapshot = { ...message.snapshot, zone: next ? { ...next, config: previous!.config } : null };
        message = { type: 'snapshot', snapshot };
      }
      if (message.type === 'snapshot') {
        if (!message.snapshot) return;
        receivedSnapshot = true;
        this.ready = true;
        this.attempt = 0;
        this.snapshot = message.snapshot;
        this.sequence = Math.max(this.sequence, message.snapshot.self?.lastSequence ?? 0);
        const transfer = this.pendingTransfer;
        if (transfer && transfer.zoneId === message.snapshot.zone?.id && transfer.previousActivation !== message.snapshot.zone?.activationId) this.pendingTransfer = null;
        this.onStatus('online'); this.onSnapshot(message.snapshot);
      } else if (message.type === 'error') {
        if (message.code === 'authority_unavailable') this.ready = false;
        this.onNotice(message.message);
      } else if (message.type === 'result' && message.result) {
        const actionType = this.sentActions.get(message.sequence);
        this.sentActions.delete(message.sequence);
        if (!message.result.ok) {
          if (this.pendingTransfer?.sequence === message.sequence) this.pendingTransfer = null;
          // Movement already in flight can arrive after a zone transition. Other failures remain visible.
          if (actionType !== 'move' || message.result.code !== 'stale_activation') {
            this.onNotice((message.result.code ?? 'Action unavailable').replaceAll('_', ' '));
          }
        }
      }
    };
    socket.onclose = event => {
      if (!current()) return;
      this.socket = null;
      this.ready = false;
      if ([1008, 4001].includes(event.code)) { this.onNotice(event.reason || 'Sign in again to resume.'); this.close(); return; }
      this.onStatus('reconnecting');
      this.timer = setTimeout(() => { this.timer = null; this.connect(); }, Math.min(8000, 500 * 2 ** this.attempt++));
    };
    socket.onerror = () => { if (current()) this.ready = false; };
  }
  send(action: PlayerAction): boolean {
    const activationId = this.snapshot?.zone?.activationId;
    if (!activationId || !this.ready || this.pendingTransfer || this.socket?.readyState !== WebSocket.OPEN || this.closed) return false;
    const sequence = ++this.sequence;
    this.sentActions.set(sequence, action.type);
    if (this.sentActions.size > 512) this.sentActions.delete(this.sentActions.keys().next().value!);
    if (action.type === 'transfer') this.pendingTransfer = { sequence, zoneId: action.zoneId, previousActivation: activationId };
    try { this.socket.send(JSON.stringify({ type: 'command', command: { version: 1, sequence, activationId, action } })); }
    catch {
      this.sentActions.delete(sequence);
      this.pendingTransfer = null;
      this.ready = false;
      this.socket.close();
      return false;
    }
    return true;
  }
  updateToken(token: string): void {
    if (this.closed || !token || token === this.credentials.token) return;
    this.credentials.token = token;
    // The authority authenticates once per socket and periodically revalidates that token.
    const previous = this.socket;
    this.socket = null;
    this.ready = false;
    previous?.close();
    this.attempt = 1;
    this.connect();
  }
  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.ready = false;
    this.pendingTransfer = null;
    this.sentActions.clear();
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const socket = this.socket;
    this.socket = null;
    socket?.close(); this.onStatus('closed');
  }
}

export function campaignHttpUrl(websocketUrl: string): string {
  const url = new URL(websocketUrl);
  url.protocol = url.protocol === 'wss:' ? 'https:' : 'http:';
  url.pathname = ''; url.search = ''; url.hash = '';
  return url.toString().replace(/\/$/, '');
}
