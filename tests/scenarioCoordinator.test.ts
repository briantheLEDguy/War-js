import { describe, expect, it } from 'vitest';
import { ScenarioCoordinator } from '../server/scenarios/coordinator';
import type { ScenarioCharacter, ScenarioJournal } from '../shared/scenarios/types';
const character = (id: string, realm: 'aegis' | 'riftbound' = 'aegis'): ScenarioCharacter => ({
  id, name: id, realm, visual: '/Game/Characters/Test', returnMap: '/Game/Capitals/Test',
  returnPosition: [10, 20, 30], document: { inventory: { gold: 87 }, quests: ['active'], level: 12 },
});
function fixture(beforeSave: () => void = () => {}) {
  let time = 0, saved: ScenarioJournal | undefined, request = 0;
  const c = new ScenarioCoordinator(s => { beforeSave(); saved = structuredClone(s); }, undefined, () => time);
  const add = (id: string, realm: 'aegis' | 'riftbound' = 'aegis') => c.register(character(id, realm));
  const command = (id: string, action: string, target = '') => c.command(id, String(++request), action, target);
  const queue = (id: string) => { command(id, 'ready'); command(id, 'queue', 'lower_city'); };
  const advance = (ms: number) => { time += ms; c.tick(); };
  const start = (ids: string[], release = true) => {
    for (const id of ids) { add(id); queue(id); }
    advance(30_000); for (const id of ids) command(id, 'accept');
    const match = c.state.matches[c.player(ids[0]).match!]; c.allocated(match.id, '127.0.0.1:7780');
    if (release) for (const id of ids) {
      const ticket = c.view(id).ticket!; c.depart(character(id), ticket); c.releaseCampaign(id, ticket);
    }
    return match;
  };
  return { c, add, command, queue, advance, start, saved: () => saved! };
}
describe('shared scenario coordinator', () => {
  it('rolls back failed journal writes without consuming tickets or command retry IDs', () => {
    let failing = false;
    const f = fixture(() => { if (failing) throw new Error('storage unavailable'); });
    const match = f.start(['a']), ticket = f.c.view('a').ticket!;
    failing = true; expect(() => f.c.consume(ticket, match.id, match.serverKey)).toThrow('storage');
    expect(f.c.view('a').phase).toBe('travel'); expect(f.c.view('a').ticket).toBe(ticket);
    failing = false; expect(f.c.consume(ticket, match.id, match.serverKey)).toEqual(character('a'));
    f.add('b'); f.command('b', 'ready'); failing = true;
    expect(() => f.c.command('b', 'retry', 'queue', 'lower_city')).toThrow('storage');
    expect(f.c.view('b').phase).toBe('idle'); failing = false;
    f.c.command('b', 'retry', 'queue', 'lower_city'); expect(f.c.view('b').phase).toBe('queued');
  });
  it('rejects admission until the trusted campaign confirms possession release', () => {
    const f = fixture(); f.add('a'); f.queue('a'); f.advance(30_000); f.command('a', 'accept');
    const match = f.c.state.matches[f.c.player('a').match!]; f.c.allocated(match.id, '127.0.0.1:7780');
    const ticket = f.c.view('a').ticket!;
    expect(() => f.c.consume(ticket, match.id, match.serverKey)).toThrow('possession');
    expect(() => f.c.releaseCampaign('a', ticket)).toThrow('not prepared');
    f.c.depart(character('a'), ticket);
    expect(() => f.c.consume(ticket, match.id, match.serverKey)).toThrow('possession');
    f.c.releaseCampaign('a', ticket);
    expect(f.c.consume(ticket, match.id, match.serverKey)).toEqual(character('a'));
  });
  it('cancels an unstarted departure without restoring an outdated registration snapshot', () => {
    const f = fixture(); f.add('a'); f.queue('a'); f.advance(30_000); f.command('a', 'accept');
    const match = f.c.state.matches[f.c.player('a').match!]; f.c.allocated(match.id, '127.0.0.1:7780');
    f.c.finish(match.id);
    expect(f.c.view('a').phase).toBe('idle'); expect(f.c.view('a').ticket).toBeUndefined();
  });
  it('saves changes made while queued at departure and retries release without admitting twice', () => {
    const f = fixture(), match = f.start(['a'], false), ticket = f.c.view('a').ticket!;
    const latest = { ...character('a'), document: { inventory: { gold: 123 }, level: 13 }, returnPosition: [40, 50, 60] };
    f.c.depart(latest, ticket); f.c.releaseCampaign('a', ticket); f.c.releaseCampaign('a', ticket);
    expect(f.c.consume(ticket, match.id, match.serverKey)).toEqual(latest);
    expect(() => f.c.releaseCampaign('a', ticket)).toThrow();
    f.c.finish(match.id); expect(f.c.restore(f.c.view('a').ticket!, 'a')).toEqual(latest);
  });
  it('gathers for 30 seconds and supports a solo human with bot fill', () => {
    const f = fixture(); f.add('a'); f.queue('a'); f.advance(29_999);
    expect(f.c.view('a').phase).toBe('queued'); f.advance(1);
    expect(f.c.view('a').phase).toBe('offered');
  });
  it('withdraws stale queued parties and hides disconnected invite candidates', () => {
    const f = fixture(); f.add('a'); f.add('b'); f.queue('a');
    expect(f.c.view('a').availablePlayers.map(player => player.id)).toContain('b');
    f.advance(90_000);
    expect(f.c.view('a').phase).toBe('idle');
    expect(f.c.view('a').message).toContain('disconnected');
    expect(f.c.view('a').availablePlayers).toEqual([]);
    expect(f.c.state.queue).toHaveLength(0);
  });
  it('offers a full 18v18 immediately without changing realms', () => {
    const f = fixture(); for (let i = 0; i < 36; i++) { f.add(`p${i}`, i < 18 ? 'aegis' : 'riftbound'); f.queue(`p${i}`); }
    f.advance(0); expect(Object.values(f.c.state.matches)).toHaveLength(1);
    expect(Object.values(f.c.state.matches)[0].members).toHaveLength(36);
    expect(Object.values(f.c.state.matches)[0].definition).toMatchObject({ capacity: 18, rulesVersion: 2, battlefield: 'FullSiege' });
  });
  it('retains historical six-player rules for recovery journals without an allocation snapshot', () => {
    const f = fixture(), match = f.start(['a']);
    const saved = f.saved(); delete saved.matches[match.id].definition;
    const restored = new ScenarioCoordinator(() => {}, saved, () => 40_000);
    expect(restored.matchDefinition(restored.state.matches[match.id])).toMatchObject({ capacity: 6, rulesVersion: 1, battlefield: 'LowerCity' });
    expect(restored.player('a').phase).toBe('return');
    expect(restored.player('a').character.document).toEqual(character('a').document);
  });
  it('requires party readiness and keeps members together', () => {
    const f = fixture(); f.add('a'); f.add('b'); f.command('a', 'invite', 'b');
    f.command('b', 'acceptInvite', f.c.player('a').party); f.command('a', 'ready');
    expect(() => f.command('a', 'queue', 'lower_city')).toThrow('Every party');
    f.command('b', 'ready'); f.command('a', 'queue', 'lower_city'); f.advance(30_000);
    expect(f.c.player('a').match).toBe(f.c.player('b').match);
    expect(() => f.command('b', 'leaveParty')).toThrow();
  });
  it('rejects cross-realm parties and nonleader administration', () => {
    const f = fixture(); f.add('a'); f.add('b', 'riftbound');
    expect(() => f.command('a', 'invite', 'b')).toThrow('same-realm');
    f.add('c'); f.command('a', 'invite', 'c'); f.command('c', 'acceptInvite', f.c.player('a').party);
    expect(() => f.command('c', 'kick', 'a')).toThrow('leader');
    f.command('a', 'leader', 'c'); f.command('c', 'kick', 'a'); expect(f.c.player('a').party).not.toBe(f.c.player('c').party);
  });
  it('bounds parties to six', () => {
    const f = fixture(); f.add('a');
    for (let i = 0; i < 5; i++) { f.add(`p${i}`); f.command('a', 'invite', `p${i}`); f.command(`p${i}`, 'acceptInvite', f.c.player('a').party); }
    f.add('extra'); expect(() => f.command('a', 'invite', 'extra')).toThrow();
  });
  it('does not overfill a realm and creates independent offers', () => {
    const f = fixture(); for (let i = 0; i < 37; i++) { f.add(`p${i}`); f.queue(`p${i}`); }
    f.advance(30_000); f.advance(1); f.advance(1);
    const matches = Object.values(f.c.state.matches); expect(matches).toHaveLength(3);
    expect(matches.map(m => m.members.length)).toEqual([18, 18, 1]);
    expect(new Set(matches.flatMap(m => m.members)).size).toBe(37);
  });
  it('withdraws a declining party while preserving others waiting priority', () => {
    const f = fixture(); f.add('a'); f.add('b'); f.queue('a'); f.queue('b'); f.advance(30_000);
    f.command('a', 'cancel'); expect(f.c.view('a').phase).toBe('idle');
    expect(f.c.state.queue[0].since).toBe(0); expect(f.c.view('b').phase).toBe('queued');
  });
  it('expires nonresponders without withdrawing accepted parties', () => {
    const f = fixture(); f.add('a'); f.add('b'); f.queue('a'); f.queue('b'); f.advance(30_000);
    f.command('b', 'accept'); f.advance(30_000);
    expect(f.c.view('a').phase).toBe('idle'); expect(f.c.view('b').phase).toBe('offered');
  });
  it('deduplicates commands', () => {
    const f = fixture(); f.add('a'); f.command('a', 'ready');
    f.c.command('a', 'same', 'queue', 'lower_city'); f.c.command('a', 'same', 'queue', 'lower_city');
    expect(f.c.state.queue).toHaveLength(1);
  });
  it('requeues allocation failures', () => {
    const f = fixture(); f.add('a'); f.queue('a'); f.advance(30_000); f.command('a', 'accept');
    f.c.allocationFailed(f.c.player('a').match!, 'Map unavailable'); expect(f.c.view('a').phase).toBe('queued');
    expect(f.c.view('a').message).toBe('Map unavailable');
  });
  it('binds single-use tickets to their server and restores the original snapshot', () => {
    const f = fixture(), m = f.start(['a']), ticket = f.c.view('a').ticket!;
    expect(() => f.c.consume(ticket, m.id, 'wrong')).toThrow('authentication');
    expect(f.c.consume(ticket, m.id, m.serverKey)).toEqual(character('a'));
    expect(() => f.c.consume(ticket, m.id, m.serverKey)).toThrow();
    f.command('a', 'leaveMatch'); const back = f.c.view('a').ticket!;
    expect(() => f.c.restore(back, 'a')).toThrow('release');
    f.c.disconnected('a', m.id, m.serverKey);
    expect(f.c.restore(back, 'a')).toEqual(character('a'));
    expect(f.c.restore(back, 'a')).toEqual(character('a')); // A failed native restore can retry.
    expect(f.c.view('a').phase).toBe('return');
    f.c.completeRestore(back, 'a'); expect(() => f.c.restore(back, 'a')).toThrow();
  });
  it('allows reconnect only within the reservation', () => {
    const f = fixture(), m = f.start(['a']); f.c.consume(f.c.view('a').ticket!, m.id, m.serverKey);
    f.c.disconnected('a', m.id, m.serverKey); f.advance(119_999); f.command('a', 'reconnect');
    f.c.consume(f.c.view('a').ticket!, m.id, m.serverKey); f.c.disconnected('a', m.id, m.serverKey);
    f.advance(120_000); expect(f.c.view('a').phase).toBe('return'); expect(() => f.command('a', 'reconnect')).toThrow();
  });
  it('does not extend the seat reservation by requesting a reconnect ticket near expiry', () => {
    const f = fixture(), match = f.start(['a']); f.c.consume(f.c.view('a').ticket!, match.id, match.serverKey);
    f.c.disconnected('a', match.id, match.serverKey); f.advance(119_999); f.command('a', 'reconnect');
    const ticket = f.c.view('a').ticket!; f.advance(2);
    expect(() => f.c.consume(ticket, match.id, match.serverKey)).toThrow();
    expect(f.c.view('a').phase).toBe('return');
  });
  it('can queue a fresh match after a previous reconnect reservation expired', () => {
    const f = fixture(), old = f.start(['a']); f.c.consume(f.c.view('a').ticket!, old.id, old.serverKey);
    f.c.disconnected('a', old.id, old.serverKey); f.advance(120_000);
    f.c.completeRestore(f.c.view('a').ticket!, 'a'); f.c.authenticate(f.c.player('a').token);
    f.queue('a'); f.advance(30_000); f.command('a', 'accept');
    const next = f.c.state.matches[f.c.player('a').match!]; f.c.allocated(next.id, '127.0.0.1:7781');
    const ticket = f.c.view('a').ticket!; f.c.depart(character('a'), ticket); f.c.releaseCampaign('a', ticket);
    expect(f.c.consume(ticket, next.id, next.serverKey)).toEqual(character('a'));
  });
  it('does not let host re-registration overwrite an active match snapshot', () => {
    const f = fixture(); f.start(['a']); f.c.register({ ...character('a'), document: { gold: 0 } });
    expect(f.c.player('a').character.document).toEqual(character('a').document);
  });
  it('recovers characters across coordinator restart and invalidates old admission', () => {
    const f = fixture(), m = f.start(['a']), ticket = f.c.view('a').ticket!;
    let recoveryTime = 0;
    const restarted = new ScenarioCoordinator(() => {}, f.saved(), () => recoveryTime);
    expect(restarted.view('a').phase).toBe('return');
    expect(() => restarted.consume(ticket, m.id, m.serverKey)).toThrow();
    expect(() => restarted.restore(restarted.view('a').ticket!, 'a')).toThrow('release');
    recoveryTime = 20_000;
    expect(restarted.restore(restarted.view('a').ticket!, 'a')).toEqual(character('a'));
  });
  it('preserves recovery for older development journals without departure flags', () => {
    const f = fixture(); f.start(['a']); const journal = f.saved();
    delete journal.players.a.departurePrepared; delete journal.players.a.campaignReleased;
    const restarted = new ScenarioCoordinator(() => {}, journal, () => 0);
    expect(restarted.view('a').phase).toBe('return');
  });
  it('returns members when an instance fails', () => {
    const f = fixture(), m = f.start(['a']); f.c.finish(m.id, 'Server stopped');
    expect(f.c.view('a').phase).toBe('return'); expect(f.c.view('a').message).toBe('Server stopped');
  });
  it('rejects malformed snapshots and reserved object keys at registration and departure', () => {
    const f = fixture();
    for (const id of ['__proto__', 'constructor', 'prototype']) expect(() => f.add(id)).toThrow('Invalid');
    expect(() => f.c.player('constructor')).toThrow('unavailable');
    f.start(['a']);
    expect(() => f.c.depart({ ...character('a'), returnPosition: [NaN, 1, 2] }, f.c.view('a').ticket!)).toThrow('Invalid');
    expect(f.c.player('a').character.returnPosition).toEqual([10, 20, 30]);
  });
});
