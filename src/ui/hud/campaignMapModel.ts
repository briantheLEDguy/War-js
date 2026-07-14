import {
  CAMPAIGN_GRAPH_EDGES,
  CAMPAIGN_ZONES,
  type CampaignLane,
  type CampaignZoneNode,
} from '../../data/campaign';

export type CampaignMapLevel = 'zone' | 'route' | 'campaign';

export interface CampaignRouteModel {
  lane: CampaignLane;
  label: string;
  realm?: 'aegis' | 'riftbound';
  mainZoneIds: string[];
  branches: Record<string, string[]>;
  zoneIds: string[];
}

export interface CampaignMapNodeTarget {
  level: CampaignMapLevel;
  zoneId: string;
}

const ROUTE_ORDER: CampaignLane[] = [
  'central',
  'aegis_west',
  'aegis_east',
  'riftbound_west',
  'riftbound_east',
];

const ZONE_BY_ID = new Map(CAMPAIGN_ZONES.map((zone) => [zone.id, zone]));
const ADJACENCY = buildAdjacency();
const ROUTES = new Map(ROUTE_ORDER.map((lane) => [lane, buildRoute(lane)]));

export const CAMPAIGN_ROUTE_ORDER = ROUTE_ORDER;

export function campaignRouteForZone(zoneId: string | null | undefined): CampaignRouteModel {
  const zone = zoneId ? ZONE_BY_ID.get(zoneId) : undefined;
  return ROUTES.get(zone?.lane ?? 'central') ?? ROUTES.get('central')!;
}

export function campaignRouteForLane(lane: CampaignLane): CampaignRouteModel {
  return ROUTES.get(lane) ?? ROUTES.get('central')!;
}

export function campaignZoneForId(zoneId: string | null | undefined): CampaignZoneNode | null {
  return zoneId ? ZONE_BY_ID.get(zoneId) ?? null : null;
}

export function defaultCampaignMapZone(currentZoneId: string | null | undefined): string {
  return campaignZoneForId(currentZoneId)?.id ?? 'aegis_capital';
}

export function campaignMapLevelIn(
  level: CampaignMapLevel,
  zoneId: string | null | undefined,
): CampaignMapLevel {
  if (level === 'campaign') return 'route';
  if (level === 'route') return 'zone';
  return 'zone';
}

export function campaignMapLevelOut(level: CampaignMapLevel): CampaignMapLevel {
  if (level === 'zone') return 'route';
  if (level === 'route') return 'campaign';
  return 'campaign';
}

export function campaignMapNodeTarget(
  level: CampaignMapLevel,
  zoneId: string | null | undefined,
): CampaignMapNodeTarget {
  return {
    level: campaignMapLevelIn(level, zoneId),
    zoneId: defaultCampaignMapZone(zoneId),
  };
}

export function campaignRouteMainZoneIds(lane: CampaignLane): string[] {
  return campaignRouteForLane(lane).mainZoneIds;
}

function buildRoute(lane: CampaignLane): CampaignRouteModel {
  const label = getLaneLabel(lane);
  if (lane === 'central') {
    const mainZoneIds = findPath(
      capitalZoneId('riftbound'),
      capitalZoneId('aegis'),
      (zone) => zone.lane === 'central',
    );
    return {
      lane,
      label,
      mainZoneIds,
      branches: {},
      zoneIds: mainZoneIds,
    };
  }

  const realm = lane.startsWith('aegis_') ? 'aegis' : 'riftbound';
  const capitalId = capitalZoneId(realm);
  const laneZones = CAMPAIGN_ZONES.filter((zone) => zone.lane === lane);
  const t3Zone = laneZones.find((zone) => zone.tier === 'T3' && zone.nodeRole !== 'boss_lair');
  const innerFrontId = t3Zone
    ? [...(ADJACENCY.get(t3Zone.id) ?? [])]
      .map((id) => ZONE_BY_ID.get(id))
      .find((zone) => zone?.lane === 'central' && zone.tier === 'T4' && zone.nodeRole === 'battlefield')?.id
    : undefined;

  const allowedIds = new Set([
    capitalId,
    ...(innerFrontId ? [innerFrontId] : []),
    ...laneZones.filter((zone) => zone.nodeRole !== 'boss_lair').map((zone) => zone.id),
  ]);
  const mainZoneIds = innerFrontId
    ? findPath(capitalId, innerFrontId, (zone) => allowedIds.has(zone.id))
    : laneZones
      .filter((zone) => zone.nodeRole !== 'boss_lair')
      .sort(compareTier)
      .map((zone) => zone.id);

  const branches: Record<string, string[]> = {};
  for (const mainZoneId of mainZoneIds) {
    const branchIds = [...(ADJACENCY.get(mainZoneId) ?? [])]
      .map((id) => ZONE_BY_ID.get(id))
      .filter((zone): zone is CampaignZoneNode =>
        Boolean(zone && zone.lane === lane && zone.nodeRole === 'boss_lair'),
      )
      .sort(compareTier)
      .map((zone) => zone.id);
    if (branchIds.length > 0) branches[mainZoneId] = branchIds;
  }

  return {
    lane,
    label,
    realm,
    mainZoneIds,
    branches,
    zoneIds: mainZoneIds.flatMap((zoneId) => [zoneId, ...(branches[zoneId] ?? [])]),
  };
}

function buildAdjacency(): Map<string, Set<string>> {
  const adjacency = new Map<string, Set<string>>();
  for (const zone of CAMPAIGN_ZONES) adjacency.set(zone.id, new Set());
  for (const edge of CAMPAIGN_GRAPH_EDGES) {
    adjacency.get(edge.fromZoneId)?.add(edge.toZoneId);
    adjacency.get(edge.toZoneId)?.add(edge.fromZoneId);
  }
  return adjacency;
}

function capitalZoneId(realm: 'aegis' | 'riftbound'): string {
  return CAMPAIGN_ZONES.find((zone) => zone.realm === realm && zone.nodeRole === 'capital')?.id
    ?? (realm === 'aegis' ? 'aegis_capital' : 'riftspire_capital');
}

function findPath(
  startId: string,
  endId: string,
  include: (zone: CampaignZoneNode) => boolean,
): string[] {
  if (startId === endId) return [startId];
  const queue = [startId];
  const previous = new Map<string, string | null>([[startId, null]]);

  while (queue.length > 0) {
    const currentId = queue.shift()!;
    for (const nextId of ADJACENCY.get(currentId) ?? []) {
      if (previous.has(nextId)) continue;
      const nextZone = ZONE_BY_ID.get(nextId);
      if (!nextZone || !include(nextZone)) continue;
      previous.set(nextId, currentId);
      if (nextId === endId) return reconstructPath(previous, endId);
      queue.push(nextId);
    }
  }

  return [];
}

function reconstructPath(previous: Map<string, string | null>, endId: string): string[] {
  const path: string[] = [];
  let currentId: string | null = endId;
  while (currentId) {
    path.unshift(currentId);
    currentId = previous.get(currentId) ?? null;
  }
  return path;
}

function compareTier(a: CampaignZoneNode, b: CampaignZoneNode): number {
  return tierOrder(a.tier) - tierOrder(b.tier) || a.id.localeCompare(b.id);
}

function tierOrder(tier: CampaignZoneNode['tier']): number {
  switch (tier) {
    case 'T1': return 1;
    case 'T2': return 2;
    case 'T3': return 3;
    case 'T4': return 4;
    case 'Fortress': return 5;
    case 'City': return 6;
    case 'Boss': return 7;
    default: return 99;
  }
}

function getLaneLabel(lane: CampaignLane): string {
  switch (lane) {
    case 'central': return 'Central Front';
    case 'aegis_west': return 'Aegis West March';
    case 'aegis_east': return 'Aegis East March';
    case 'riftbound_west': return 'Riftbound West March';
    case 'riftbound_east': return 'Riftbound East March';
    default: return lane;
  }
}
