import type { GateKind, KeepState } from '../../shared/orvr/protocol';
import type { OrvrZoneLayout } from '../../world/orvrTypes';

export interface CampaignGateBinding { keepId: string; stage: GateKind }
export function campaignGateBindings(layout?: OrvrZoneLayout): Map<string, CampaignGateBinding> {
  return new Map(layout?.keeps.flatMap(keep => keep.gates.map(gate => [gate.propId, { keepId: keep.objectiveId, stage: gate.stage }] as const)) ?? []);
}

/** Breaches and subsequent repairs follow authority snapshots, never local gate interaction. */
export function campaignGateVisible(binding: CampaignGateBinding, keeps: Record<string, KeepState>): boolean {
  return (keeps[binding.keepId]?.gates[binding.stage]?.health ?? 0) > 0;
}

export function sceneryDistanceLod(distance: number, available: number, distances: number[]): number {
  let level = 0;
  for (let index = 1; index < Math.min(available, distances.length); index++) if (distance >= distances[index]) level = index;
  return level;
}
