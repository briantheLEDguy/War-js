import type { Unsubscribe, WorldService, ZonePlayerBroadcast, ZonePlayerPresence } from '../types';

/**
 * Local single-player stand-in for multiplayer world state.
 * Tracks only the local player; subscribers receive a 1-element array.
 */
export class WorldLocal implements WorldService {
  private me: ZonePlayerPresence | null = null;
  private subs = new Set<(players: ZonePlayerBroadcast[]) => void>();

  async joinZone(zoneId: string, me: ZonePlayerBroadcast): Promise<void> {
    this.me = { ...me, zoneId };
    this.broadcast();
  }

  async leaveZone(_zoneId: string): Promise<void> {
    this.me = null;
    this.broadcast();
  }

  async updatePosition(zoneId: string, me: ZonePlayerBroadcast): Promise<void> {
    this.me = { ...me, zoneId };
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

  async findPlayerByName(name: string): Promise<ZonePlayerPresence | null> {
    const needle = normalizeName(name);
    if (!needle || normalizeName(this.me?.name) !== needle) return null;
    return this.me ? { ...this.me, position: { ...this.me.position } } : null;
  }

  private snapshot(): ZonePlayerBroadcast[] {
    return this.me ? [this.me] : [];
  }

  private broadcast() {
    const snap = this.snapshot();
    for (const s of this.subs) s(snap);
  }
}

function normalizeName(name: string | null | undefined): string {
  return name?.trim().toLowerCase() ?? '';
}
