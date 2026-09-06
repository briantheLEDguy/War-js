import type { CampaignClaimResult, CampaignRealm, CampaignSnapshot } from '../../data/campaign';
import type { CampaignService, Unsubscribe } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase campaign persistence and Realtime.
 *
 * Static seed tables:
 *   - campaign_static_zones(zone_id, name, realm, tier, lane, node_role,
 *     static_map_version, map_hash)
 *   - campaign_edges(from_zone_id, to_zone_id)
 *   - campaign_objectives(zone_id, objective_id, objective_type, label, x, z,
 *     capture_radius, default_realm)
 *
 * Dynamic tables:
 *   - campaign_zone_state(zone_id, controlled_by, locked, updated_at)
 *   - campaign_objective_state(zone_id, objective_id, controlled_by,
 *     claimed_by_user_id, updated_at)
 *   - campaign_zone_influence(zone_id, aegis_influence, riftbound_influence,
 *     updated_at)
 *
 * Subscribe through a `campaign` Realtime channel and rebuild the same
 * CampaignSnapshot shape used by CampaignLocal.
 */
export class CampaignSupabase implements CampaignService {
  getSnapshot(_currentZoneId?: string | null): Promise<CampaignSnapshot> {
    throw new NotImplementedError('CampaignSupabase.getSnapshot');
  }

  subscribeSnapshot(
    _cb: (snapshot: CampaignSnapshot) => void,
    _currentZoneId?: string | null,
  ): Unsubscribe {
    throw new NotImplementedError('CampaignSupabase.subscribeSnapshot');
  }

  claimObjective(
    _zoneId: string,
    _objectiveId: string,
    _realm: CampaignRealm,
  ): Promise<CampaignClaimResult> {
    throw new NotImplementedError('CampaignSupabase.claimObjective');
  }

  defendObjective(
    _zoneId: string,
    _objectiveId: string,
    _realm: CampaignRealm,
  ): Promise<CampaignClaimResult> {
    // TODO(phase2): Atomically validate friendly control and the realm cooldown before rewarding defense.
    throw new NotImplementedError('CampaignSupabase.defendObjective');
  }

  resetCampaign(): Promise<CampaignSnapshot> {
    throw new NotImplementedError('CampaignSupabase.resetCampaign');
  }
}
