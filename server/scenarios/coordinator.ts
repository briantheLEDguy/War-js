import { randomBytes, randomUUID, timingSafeEqual } from 'node:crypto';
import { scenarioCatalog, type ScenarioCharacter, type ScenarioJournal, type ScenarioMatch, type ScenarioQueueEntry } from '../../shared/scenarios/types';

export class ScenarioError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
const reject = (message: string): never => { throw new ScenarioError(409, message); };
export function sameSecret(a: string, b: string): boolean {
  const x = Buffer.from(a), y = Buffer.from(b);
  return x.length >= 32 && x.length === y.length && timingSafeEqual(x, y);
}
const secret = () => randomBytes(32).toString('hex');
function validateCharacter(character: ScenarioCharacter) {
  if (!character || typeof character.id !== 'string' || !/^[a-zA-Z0-9_-]{1,80}$/.test(character.id)
    || ['__proto__', 'constructor', 'prototype'].includes(character.id) || !['aegis', 'riftbound'].includes(character.realm)
    || typeof character.name !== 'string' || !character.name.trim() || character.name.length > 64
    || typeof character.visual !== 'string' || !character.visual.startsWith('/Game/')
    || typeof character.returnMap !== 'string' || !character.returnMap.startsWith('/Game/')
    || !Array.isArray(character.returnPosition) || character.returnPosition.length !== 3 || !character.returnPosition.every(Number.isFinite)
    || !character.document || typeof character.document !== 'object' || Array.isArray(character.document))
    throw new ScenarioError(400, 'Invalid trusted character snapshot.');
}
const empty = (): ScenarioJournal => ({ version: 1, players: {}, parties: {}, invites: {}, queue: [], matches: {}, tickets: {} });

/** One serialized authority for parties, leases and admission. Persist before replying. */
export class ScenarioCoordinator {
  readonly state: ScenarioJournal;
  private durable: ScenarioJournal;
  private receipts = new Map<string, Set<string>>();
  private durableReceipts = new Map<string, Set<string>>();
  constructor(private save: (state: ScenarioJournal) => void = () => {}, restored?: ScenarioJournal,
    private now = () => Date.now()) {
    if (restored && restored.version !== 1) throw new Error('Unsupported scenario journal');
    this.state = restored ?? empty();
    this.durable = structuredClone(this.state);
    if (restored) {
      this.state.queue = []; this.state.tickets = {};
      for (const match of Object.values(this.state.matches)) match.phase = 'finished';
      for (const player of Object.values(this.state.players)) {
        player.phase = ['playing', 'disconnected', 'return'].includes(player.phase)
          || (player.phase === 'travel' && player.departurePrepared !== false) ? 'return' : 'idle';
        player.message = 'Scenario host restarted. Your campaign character is recoverable.';
        // Orphaned instances revoke possession after their coordinator heartbeat expires.
        player.possessionReleased = true; player.restoreAfter = this.now() + 20_000;
      }
      this.persist();
    }
  }
  private persist() {
    try {
      this.save(this.state); this.durable = structuredClone(this.state);
      this.durableReceipts = new Map([...this.receipts].map(([id, values]) => [id, new Set(values)]));
    }
    catch (error) {
      // A failed durable write must not consume an admission lease or deduplicate
      // a command that the caller was told had failed.
      Object.assign(this.state, structuredClone(this.durable));
      this.receipts = new Map([...this.durableReceipts].map(([id, values]) => [id, new Set(values)]));
      throw error;
    }
  }
  definition(id: string) { return scenarioCatalog.find(s => s.id === id) ?? reject('Unknown scenario.'); }
  player(id: string) { return Object.hasOwn(this.state.players, id) ? this.state.players[id] : reject('Character is unavailable.'); }
  authenticate(token: string): string {
    const entry = Object.values(this.state.players).find(p => sameSecret(p.token, token));
    if (!entry) throw new ScenarioError(401, 'Scenario authentication required.');
    entry.lastSeen = this.now();
    return entry.character.id;
  }
  /** Only the trusted campaign host may register/update a character document. */
  register(character: ScenarioCharacter) {
    validateCharacter(character);
    const existing = this.state.players[character.id];
    if (existing) {
      if (existing.character.realm !== character.realm) reject('Character realm cannot change.');
      if (existing.phase !== 'idle') return { token: existing.token, phase: existing.phase };
      existing.character = structuredClone(character);
    } else {
      const party = randomUUID();
      this.state.parties[party] = { id: party, leader: character.id, members: [character.id], ready: [] };
      this.state.players[character.id] = { character: structuredClone(character), token: secret(), party, phase: 'idle', message: '', lastSeen: this.now() };
    }
    this.persist(); return { token: this.player(character.id).token, phase: this.player(character.id).phase };
  }
  private party(id: string) { return this.state.parties[this.player(id).party]; }
  private idleParty(id: string) {
    const party = this.party(id);
    if (party.members.some(member => this.player(member).phase !== 'idle')) reject('Leave the queue or finish the match before changing the party.');
    return party;
  }
  private leader(id: string) {
    const party = this.idleParty(id);
    if (party.leader !== id) reject('Only the party leader can do that.');
    return party;
  }
  private detach(id: string) {
    const party = this.party(id);
    party.members = party.members.filter(m => m !== id); party.ready = [];
    if (!party.members.length) delete this.state.parties[party.id];
    else if (party.leader === id) party.leader = party.members[0];
    const next = randomUUID(); this.player(id).party = next;
    this.state.parties[next] = { id: next, leader: id, members: [id], ready: [] };
  }
  command(id: string, requestId: string, action: string, target = '') {
    if (!/^[a-zA-Z0-9_-]{1,80}$/.test(requestId)) throw new ScenarioError(400, 'A request ID is required.');
    const receipts = this.receipts.get(id) ?? new Set<string>();
    if (receipts.has(requestId)) return this.view(id);
    const player = this.player(id);
    if (action === 'invite') {
      const party = this.leader(id), other = this.player(target);
      if (party.members.length >= 6 || other.character.realm !== player.character.realm || other.party === party.id) reject('Invite requires an available same-realm player and party space.');
      this.idleParty(target);
      const invites = this.state.invites[target] ??= [];
      if (!invites.includes(party.id)) invites.push(party.id);
    } else if (action === 'acceptInvite') {
      const own = this.idleParty(id), party = this.state.parties[target];
      if (own.members.length !== 1 || !party || !(this.state.invites[id] ?? []).includes(target)) reject('Invitation is no longer available.');
      this.idleParty(party.leader);
      if (party.members.length >= 6 || this.player(party.leader).character.realm !== player.character.realm) reject('Party is full or belongs to another realm.');
      delete this.state.parties[own.id]; party.members.push(id); party.ready = []; player.party = party.id;
      this.state.invites[id] = [];
    } else if (action === 'declineInvite') {
      this.state.invites[id] = (this.state.invites[id] ?? []).filter(p => p !== target);
    } else if (action === 'leaveParty') { this.idleParty(id); this.detach(id); }
    else if (action === 'kick' || action === 'leader') {
      const party = this.leader(id);
      if (target === id || !party.members.includes(target)) reject('Choose another party member.');
      if (action === 'kick') this.detach(target); else party.leader = target;
    } else if (action === 'ready' || action === 'unready') {
      const party = this.idleParty(id); party.ready = party.ready.filter(m => m !== id);
      if (action === 'ready') party.ready.push(id);
    } else if (action === 'queue') {
      this.definition(target); const party = this.leader(id);
      if (party.members.some(m => !party.ready.includes(m))) reject('Every party member must be ready.');
      this.state.queue.push({ party: party.id, scenario: target, since: this.now() });
      for (const member of party.members) { this.player(member).phase = 'queued'; this.player(member).message = 'Gathering players; empty slots fill with bots after 30 seconds.'; }
    } else if (action === 'cancel') {
      if (player.phase === 'offered') this.rejectOffer(player.match!, player.party);
      else if (player.phase === 'queued') this.withdraw(player.party);
      else reject('There is no cancellable queue entry.');
    } else if (action === 'accept') {
      const match = this.state.matches[player.match ?? ''];
      if (player.phase !== 'offered' || !match || match.deadline <= this.now()) reject('Match offer has expired.');
      if (!match.accepted.includes(id)) match.accepted.push(id);
      if (match.members.every(m => match.accepted.includes(m))) {
        match.phase = 'allocating'; for (const member of match.members) {
          this.player(member).phase = 'allocating'; this.player(member).message = 'Preparing a dedicated scenario instance.';
        }
      }
    } else if (action === 'leaveMatch') {
      if (!['playing', 'travel', 'disconnected'].includes(player.phase)) reject('No match to leave.');
      this.returnPlayer(id, 'Returning to your campaign character.');
    } else if (action === 'reconnect') {
      const match = this.state.matches[player.match ?? ''];
      if (player.phase !== 'disconnected' || !match || match.phase !== 'running'
        || this.now() - player.disconnectedAt! >= this.definition(match.scenario).reconnectMs) reject('Reconnect reservation expired.');
      player.phase = 'travel'; this.issueTicket(id, match.id, 'join');
    } else reject('Unknown scenario command.');
    receipts.add(requestId); if (receipts.size > 256) receipts.delete(receipts.values().next().value!);
    this.receipts.set(id, receipts); this.persist(); return this.view(id);
  }
  private withdraw(party: string) {
    this.state.queue = this.state.queue.filter(e => e.party !== party);
    for (const id of this.state.parties[party].members) { this.player(id).phase = 'idle'; this.player(id).match = undefined; this.player(id).message = 'Queue entry withdrawn.'; }
  }
  private rejectOffer(id: string, withdrawn: string) {
    const match = this.state.matches[id]; if (!match || match.phase !== 'offered') return;
    match.phase = 'finished';
    for (const entry of match.parties) {
      if (entry.party === withdrawn) this.withdraw(entry.party);
      else {
        this.state.queue.push(entry);
        for (const member of this.state.parties[entry.party].members) { this.player(member).phase = 'queued'; this.player(member).match = undefined; }
      }
    }
  }
  tick() {
    const now = this.now();
    for (const entry of [...this.state.queue]) {
      const party = this.state.parties[entry.party];
      if (party.members.some(id => now - (this.player(id).lastSeen ?? 0) >= 90_000)) {
        this.withdraw(party.id); party.ready = [];
        for (const id of party.members) this.player(id).message = 'A party member disconnected. Ready again when everyone is online.';
      }
    }
    for (const [key, ticket] of Object.entries(this.state.tickets)) if (ticket.expires <= now) delete this.state.tickets[key];
    for (const match of Object.values(this.state.matches)) if (match.phase === 'offered' && match.deadline <= now) {
      const missing = new Set(match.members.filter(m => !match.accepted.includes(m)).map(m => this.player(m).party));
      const first = missing.values().next().value;
      if (first) { this.rejectOffer(match.id, first); for (const party of missing) this.withdraw(party); }
    }
    for (const player of Object.values(this.state.players)) {
      if (player.phase === 'disconnected' && now - player.disconnectedAt! >= this.definition(this.state.matches[player.match!].scenario).reconnectMs)
        this.returnPlayer(player.character.id, 'Reconnect reservation expired. Your campaign character is safe.');
      if (player.phase === 'travel' && !Object.values(this.state.tickets).some(t => t.player === player.character.id && t.kind === 'join'))
        this.returnPlayer(player.character.id, 'Scenario connection timed out. Return to your campaign character.');
    }
    for (const definition of scenarioCatalog) {
      const entries = this.state.queue.filter(e => e.scenario === definition.id).sort((a, b) => a.since - b.since);
      if (!entries.length) continue;
      const counts = { aegis: 0, riftbound: 0 }; const selected: ScenarioQueueEntry[] = [];
      for (const entry of entries) {
        const party = this.state.parties[entry.party], realm = this.player(party.leader).character.realm;
        if (counts[realm] + party.members.length <= definition.capacity) { counts[realm] += party.members.length; selected.push(entry); }
      }
      if (now - entries[0].since < definition.gatherMs && (counts.aegis < definition.capacity || counts.riftbound < definition.capacity)) continue;
      const id = randomUUID(), members = selected.flatMap(e => this.state.parties[e.party].members);
      this.state.matches[id] = { id, scenario: definition.id, parties: selected, members, accepted: [], deadline: now + definition.acceptMs, phase: 'offered', serverKey: secret() };
      this.state.queue = this.state.queue.filter(e => !selected.includes(e));
      for (const member of members) { const p = this.player(member); p.phase = 'offered'; p.match = id; p.message = 'Match found. Accept within 30 seconds.'; }
    }
    this.persist();
  }
  allocated(id: string, endpoint: string) {
    const match = this.state.matches[id]; if (!match || match.phase !== 'allocating') reject('Allocation is no longer current.');
    if (!/^[a-zA-Z0-9.-]+:[0-9]{1,5}$/.test(endpoint)) reject('Invalid server endpoint.');
    match.endpoint = endpoint; match.phase = 'running'; match.started = this.now();
    for (const member of match.members) {
      const player = this.player(member);
      player.phase = 'travel'; player.departurePrepared = false; player.campaignReleased = false;
      player.disconnectedAt = undefined;
      player.message = 'Match ready. Transferring your character.'; this.issueTicket(member, id, 'join');
    }
    this.persist();
  }
  depart(character: ScenarioCharacter, ticket: string) {
    validateCharacter(character);
    const player = this.player(character.id), lease = this.state.tickets[ticket];
    if (player.phase !== 'travel' || !lease || lease.player !== character.id || lease.kind !== 'join'
      || lease.expires <= this.now() || character.realm !== player.character.realm) reject('Departure reservation is no longer valid.');
    // Capture the authoritative campaign state at departure, not when the panel opened.
    if (player.campaignReleased) reject('Campaign possession has already been released.');
    player.character = structuredClone(character); player.departurePrepared = true; this.persist();
    return { endpoint: this.state.matches[lease.match].endpoint, ticket };
  }
  releaseCampaign(id: string, ticket: string) {
    const player = this.player(id), lease = this.state.tickets[ticket];
    if (player.phase !== 'travel' || !player.departurePrepared || !lease || lease.player !== id
      || lease.kind !== 'join' || lease.expires <= this.now()) reject('Campaign departure is not prepared.');
    player.campaignReleased = true; this.persist();
    return { endpoint: this.state.matches[lease.match].endpoint, ticket };
  }
  allocationFailed(id: string, message: string) {
    const match = this.state.matches[id]; if (!match || match.phase !== 'allocating') return;
    match.phase = 'finished';
    for (const entry of match.parties) this.state.queue.push(entry);
    for (const member of match.members) { const p = this.player(member); p.phase = 'queued'; p.match = undefined; p.message = message; }
    this.persist();
  }
  private issueTicket(player: string, match: string, kind: 'join' | 'return') {
    for (const [key, ticket] of Object.entries(this.state.tickets)) if (ticket.player === player) delete this.state.tickets[key];
    const owner = this.player(player);
    const reservationEnd = kind === 'join' && owner.disconnectedAt !== undefined
      ? owner.disconnectedAt + this.definition(this.state.matches[match].scenario).reconnectMs : Infinity;
    const token = secret(); this.state.tickets[token] = { player, match, kind, expires: Math.min(this.now() + 120_000, reservationEnd) }; return token;
  }
  private returnPlayer(id: string, message: string) {
    const p = this.player(id); p.message = message;
    if (p.phase === 'travel' && !p.departurePrepared && !p.campaignReleased) {
      p.phase = 'idle'; p.match = undefined; this.party(id).ready = [];
      for (const [key, ticket] of Object.entries(this.state.tickets)) if (ticket.player === id) delete this.state.tickets[key];
      return;
    }
    p.phase = 'return';
    this.issueTicket(id, p.match ?? '', 'return');
  }
  verifyServer(matchId: string, key: string): ScenarioMatch {
    const match = this.state.matches[matchId];
    if (!match || !sameSecret(match.serverKey, key)) throw new ScenarioError(403, 'Instance authentication required.');
    return match;
  }
  consume(ticket: string, matchId: string, serverKey: string) {
    const match = this.verifyServer(matchId, serverKey), lease = this.state.tickets[ticket];
    if (match.phase !== 'running' || !lease || lease.kind !== 'join' || lease.match !== matchId || lease.expires <= this.now()) reject('Admission ticket expired, consumed, or belongs to another match.');
    const player = this.player(lease.player);
    if (player.phase !== 'travel') reject('Character is already possessed or no longer admitted.');
    if (!player.campaignReleased) reject('Campaign possession has not been released.');
    delete this.state.tickets[ticket]; player.phase = 'playing'; player.disconnectedAt = undefined; player.possessionReleased = false;
    player.message = this.definition(match.scenario).name;
    this.persist(); return structuredClone(player.character);
  }
  disconnected(id: string, matchId: string, key: string) {
    const match = this.verifyServer(matchId, key), p = this.player(id);
    if (p.match !== match.id) return;
    if (p.phase === 'return') { p.possessionReleased = true; this.persist(); return; }
    if (p.phase !== 'playing') return;
    p.possessionReleased = true;
    p.phase = 'disconnected'; p.disconnectedAt = this.now(); p.message = 'Disconnected. Your seat is reserved for 120 seconds.'; this.persist();
  }
  finish(matchId: string, message = 'Scenario finished. Return to your campaign character.') {
    const match = this.state.matches[matchId]; if (!match || match.phase === 'finished') return;
    match.phase = 'finished';
    for (const id of match.members) if (this.player(id).match === matchId) {
      this.player(id).possessionReleased = true;
      if (['playing', 'disconnected', 'travel'].includes(this.player(id).phase)) this.returnPlayer(id, message);
    }
    this.persist();
  }
  /** Keep recovery durable until the campaign host confirms a successfully restored pawn. */
  restore(ticket: string, id: string) {
    const p = this.player(id), lease = this.state.tickets[ticket];
    if (!lease || lease.kind !== 'return' || lease.player !== id || lease.expires <= this.now() || p.phase !== 'return') reject('Return ticket is invalid or already used.');
    if (p.possessionReleased === false || (p.restoreAfter ?? 0) > this.now()) reject('Waiting for the scenario server to release your character. Recovery will retry automatically.');
    return structuredClone(p.character);
  }
  completeRestore(ticket: string, id: string) {
    this.restore(ticket, id);
    const p = this.player(id);
    delete this.state.tickets[ticket]; p.phase = 'idle'; p.match = undefined; this.party(id).ready = [];
    p.disconnectedAt = undefined;
    p.message = 'Returned to your campaign character.';
    this.persist(); return {};
  }
  view(id: string) {
    const p = this.player(id), party = this.party(id), match = this.state.matches[p.match ?? ''];
    let ticket = Object.entries(this.state.tickets).find(([, value]) => value.player === id)?.[0];
    if (p.phase === 'return' && !ticket) { ticket = this.issueTicket(id, p.match ?? '', 'return'); this.persist(); }
    return {
      id, phase: p.phase, message: p.message, catalog: scenarioCatalog,
      party: { ...party, members: party.members.map(member => ({ id: member, name: this.player(member).character.name, ready: party.ready.includes(member) })) },
      invites: (this.state.invites[id] ?? []).filter(key => this.state.parties[key]).map(key => ({ id: key, name: this.player(this.state.parties[key].leader).character.name })),
      availablePlayers: Object.values(this.state.players).filter(other => other.party !== p.party && other.character.realm === p.character.realm
        && other.phase === 'idle' && this.now() - (other.lastSeen ?? 0) < 90_000).map(other => ({ id: other.character.id, name: other.character.name })),
      match: match ? { id: match.id, deadline: match.deadline, accepted: match.accepted.includes(id), endpoint: match.endpoint } : null,
      ticket: ['travel', 'return'].includes(p.phase) ? ticket : undefined,
      returnMap: p.phase === 'return' ? p.character.returnMap : undefined,
    };
  }
}
