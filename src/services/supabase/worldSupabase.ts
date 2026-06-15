import type { Unsubscribe, WorldService, ZonePlayerBroadcast, ZonePlayerPresence } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase `zone_players` + Realtime.
 *   - joinZone:            upsert row (zone_id, user_id)
 *   - leaveZone:            delete row (zone_id, user_id)
 *   - updatePosition:       upsert at ~5 Hz
 *   - subscribeToPlayers:   supabase.channel(`zone:${zoneId}`)
 *                             .on('presence', ...) or broadcast transforms
 *   - findPlayerByName:     GM-only current presence lookup by character name
 */
export class WorldSupabase implements WorldService {
  joinZone(_zoneId: string, _me: ZonePlayerBroadcast): Promise<void> {
    throw new NotImplementedError('WorldSupabase.joinZone');
  }
  leaveZone(_zoneId: string): Promise<void> {
    throw new NotImplementedError('WorldSupabase.leaveZone');
  }
  updatePosition(_zoneId: string, _me: ZonePlayerBroadcast): Promise<void> {
    throw new NotImplementedError('WorldSupabase.updatePosition');
  }
  subscribeToPlayers(
    _zoneId: string,
    _cb: (players: ZonePlayerBroadcast[]) => void,
  ): Unsubscribe {
    throw new NotImplementedError('WorldSupabase.subscribeToPlayers');
  }
  findPlayerByName(_name: string): Promise<ZonePlayerPresence | null> {
    throw new NotImplementedError('WorldSupabase.findPlayerByName');
  }
}
