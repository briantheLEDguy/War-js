import type { Unsubscribe, WorldService, ZonePlayerBroadcast } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase `zone_players` + Realtime.
 *   - joinZone:            upsert row (zone_id, user_id)
 *   - leaveZone:            delete row (zone_id, user_id)
 *   - updatePosition:       upsert at ~5 Hz
 *   - subscribeToPlayers:   supabase.channel(`zone:${zoneId}`)
 *                             .on('presence', ...) or broadcast transforms
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
}
