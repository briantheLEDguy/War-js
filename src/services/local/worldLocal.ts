import type { Unsubscribe, WorldService, ZonePlayerBroadcast } from '../types';

/**
 * Local single-player stand-in for multiplayer world state.
 * Tracks only the local player; subscribers receive a 1-element array.
 */
export class WorldLocal implements WorldService {
  private me: ZonePlayerBroadcast | null = null;
  private subs = new Set<(players: ZonePlayerBroadcast[]) => void>();

  async joinZone(_zoneId: string, me: ZonePlayerBroadcast): Promise<void> {
    this.me = me;
    this.broadcast();
  }

  async leaveZone(_zoneId: string): Promise<void> {
    this.me = null;
    this.broadcast();
  }

  async updatePosition(_zoneId: string, me: ZonePlayerBroadcast): Promise<void> {
    this.me = me;
    this.broadcast();
  }

  subscribeToPlayers(
    _zoneId: string,
    cb: (players: ZonePlayerBroadcast[]) => void,
  ): Unsubscribe {
    this.subs.add(cb);
    cb(this.snapshot());
    return () => this.subs.delete(cb);
  }

  private snapshot(): ZonePlayerBroadcast[] {
    return this.me ? [this.me] : [];
  }

  private broadcast() {
    const snap = this.snapshot();
    for (const s of this.subs) s(snap);
  }
}
