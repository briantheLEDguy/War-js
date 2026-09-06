import {
  CAMPAIGN_EDGES,
  CAMPAIGN_LANE_LABELS,
  CAMPAIGN_MAP_HASHES,
  CAMPAIGN_NODES,
  CAMPAIGN_OBJECTIVES,
  CAMPAIGN_REALMS,
  CAMPAIGN_STATIC_VERSION,
} from './campaign.generated';
import type { QuestRewardItem } from '../services/types';

export { CAMPAIGN_LANE_LABELS } from './campaign.generated';

export type CampaignRealm = keyof typeof CAMPAIGN_REALMS;
export type CampaignControl = CampaignRealm | 'contested';
export type CampaignTier = typeof CAMPAIGN_NODES[number]['tier'];
export type CampaignLane = keyof typeof CAMPAIGN_LANE_LABELS;
export type CampaignNodeRole = typeof CAMPAIGN_NODES[number]['nodeRole'];
export type CampaignObjectiveType =
  | 'battle_objective'
  | 'keep'
  | 'fortress'
  | 'city_gate'
  | 'boss';

export interface CampaignZoneNode {
  id: string;
  name: string;
  realm: CampaignRealm;
  tier: CampaignTier;
  lane: CampaignLane;
  nodeRole: CampaignNodeRole;
  theme: string;
  levelBand: string;
  staticMapHash: string;
}

export interface CampaignObjectiveDefinition {
  id: string;
  type: CampaignObjectiveType;
  label: string;
  x: number;
  z: number;
  captureRadius: number;
  defaultRealm: CampaignRealm;
}

export interface CampaignObjectiveStatus extends CampaignObjectiveDefinition {
  control: CampaignControl;
  capturableBy: CampaignRealm[];
  captureBlockers: Partial<Record<CampaignRealm, string>>;
  /** Absolute wall-clock timestamps; an absent realm entry means defense is ready. */
  defenseReadyAt: Partial<Record<CampaignRealm, number>>;
}

export interface CampaignZoneInfluence {
  aegis: number;
  riftbound: number;
  keepSiegeRequired: number;
}

export interface CampaignZoneStatus extends CampaignZoneNode {
  control: CampaignControl;
  current: boolean;
  influence: CampaignZoneInfluence;
  objectives: CampaignObjectiveStatus[];
}

export interface CampaignEdge {
  fromZoneId: string;
  toZoneId: string;
}

export interface CampaignRealmSummary {
  realm: CampaignRealm;
  label: string;
  controlledZones: number;
  targetFortressId: string;
  targetFortressName: string;
  fortressPressureReady: boolean;
  targetCityId: string;
  targetCityName: string;
  citySiegeReady: boolean;
}

export interface CampaignSnapshot {
  staticVersion: string;
  mapHashes: Record<string, string>;
  zones: CampaignZoneStatus[];
  edges: CampaignEdge[];
  activeZone: CampaignZoneStatus | null;
  contestedZones: number;
  aegis: CampaignRealmSummary;
  riftbound: CampaignRealmSummary;
  siegeRule: string;
}

export type CampaignZoneControlState = Partial<Record<string, CampaignControl>>;
export type CampaignObjectiveControlState = Partial<Record<string, CampaignControl>>;
export type CampaignZoneInfluenceState = Partial<Record<string, Partial<Record<CampaignRealm, number>>>>;
export type CampaignObjectiveDefenseState = Partial<Record<string, Partial<Record<CampaignRealm, number>>>>;

export interface CampaignClaimReward {
  xp: number;
  influence: number;
  gold?: number;
  items?: QuestRewardItem[];
}

export interface CampaignClaimResult {
  activity: 'capture' | 'defend';
  snapshot: CampaignSnapshot;
  zoneId: string;
  objectiveId: string;
  realm: CampaignRealm;
  objective: CampaignObjectiveStatus;
  reward: CampaignClaimReward;
  zoneControlChanged: boolean;
}

export const CAMPAIGN_OBJECTIVE_CAPTURE_XP = 75;
export const CAMPAIGN_BATTLE_OBJECTIVE_INFLUENCE = 25;
export const CAMPAIGN_BATTLEFIELD_SWEEP_INFLUENCE = 25;
export const CAMPAIGN_KEEP_SIEGE_INFLUENCE_REQUIRED = 100;
export const CAMPAIGN_OBJECTIVE_DEFENSE_XP = 50;
export const CAMPAIGN_OBJECTIVE_DEFENSE_INFLUENCE = 35;
export const CAMPAIGN_OBJECTIVE_DEFENSE_COOLDOWN_MS = 180_000;

export const CAMPAIGN_SIEGE_RULE =
  'A city siege opens when a realm controls the enemy T4 front, inner T4 zone, and fortress.';

export const CAMPAIGN_ZONES: CampaignZoneNode[] = CAMPAIGN_NODES.map((node) => ({ ...node }));

export const CAMPAIGN_ZONE_BY_ID: Record<string, CampaignZoneNode> = Object.fromEntries(
  CAMPAIGN_ZONES.map((zone) => [zone.id, zone]),
);

export const CAMPAIGN_GRAPH_EDGES: CampaignEdge[] = CAMPAIGN_EDGES.flatMap(([fromZoneId, toZoneId]) => ([
  { fromZoneId, toZoneId },
  { fromZoneId: toZoneId, toZoneId: fromZoneId },
]));

export const CAMPAIGN_BIDIRECTIONAL_EDGES = CAMPAIGN_GRAPH_EDGES;

export const CAMPAIGN_OBJECTIVES_BY_ZONE: Record<string, CampaignObjectiveDefinition[]> =
  Object.fromEntries(
    Object.entries(CAMPAIGN_OBJECTIVES).map(([zoneId, objectives]) => [
      zoneId,
      objectives.map((objective) => ({
        ...objective,
        type: objective.type as CampaignObjectiveType,
        defaultRealm: objective.defaultRealm as CampaignRealm,
      })),
    ]),
  );

export const CAMPAIGN_STATIC_MAP_HASHES: Record<string, string> = { ...CAMPAIGN_MAP_HASHES };

const DEFAULT_CONTESTED_ZONE_IDS = new Set(['dawnline_expanse', 'shatterline_expanse']);

const AEGIS_PRESSURE_ZONES = ['shatterline_expanse', 'rift_crownworks'];
const AEGIS_CITY_SIEGE_ZONES = ['shatterline_expanse', 'rift_crownworks', 'rift_gate_fortress'];
const RIFTBOUND_PRESSURE_ZONES = ['dawnline_expanse', 'aegis_crownworks'];
const RIFTBOUND_CITY_SIEGE_ZONES = ['dawnline_expanse', 'aegis_crownworks', 'aegis_gate_fortress'];

export function isCampaignZoneId(zoneId: string | null | undefined): boolean {
  return Boolean(zoneId && CAMPAIGN_ZONE_BY_ID[zoneId]);
}

export function campaignZoneName(zoneId: string): string {
  return CAMPAIGN_ZONE_BY_ID[zoneId]?.name ?? zoneId;
}

export function defaultCampaignZoneControl(zoneId: string): CampaignControl {
  const zone = CAMPAIGN_ZONE_BY_ID[zoneId];
  if (!zone) return 'contested';
  return DEFAULT_CONTESTED_ZONE_IDS.has(zoneId) ? 'contested' : zone.realm;
}

export function defaultCampaignObjectiveControl(
  zoneId: string,
  objectiveId: string,
): CampaignControl {
  const objective = CAMPAIGN_OBJECTIVES_BY_ZONE[zoneId]?.find((entry) => entry.id === objectiveId);
  if (objective?.type === 'keep') return objective.defaultRealm;
  const zoneDefault = defaultCampaignZoneControl(zoneId);
  if (zoneDefault !== 'contested') return zoneDefault;
  return objective?.defaultRealm ?? 'contested';
}

export function buildCampaignSnapshot(
  currentZoneId: string | null | undefined,
  zoneControl: CampaignZoneControlState = {},
  objectiveControl: CampaignObjectiveControlState = {},
  influenceState: CampaignZoneInfluenceState = {},
  defenseState: CampaignObjectiveDefenseState = {},
): CampaignSnapshot {
  const zones = CAMPAIGN_ZONES.map((zone): CampaignZoneStatus => {
    const influence = campaignZoneInfluence(zone.id, influenceState);
    const baseObjectives = (CAMPAIGN_OBJECTIVES_BY_ZONE[zone.id] ?? []).map((objective) => ({
      ...objective,
      control: objectiveControl[objectiveKey(zone.id, objective.id)]
        ?? defaultCampaignObjectiveControl(zone.id, objective.id),
      defenseReadyAt: { ...defenseState[objectiveKey(zone.id, objective.id)] },
    }));
    const objectives = baseObjectives.map((objective) => {
      const captureBlockers: Partial<Record<CampaignRealm, string>> = {};
      const capturableBy = (Object.keys(CAMPAIGN_REALMS) as CampaignRealm[]).filter((realm) => {
        const eligibility = campaignObjectiveCaptureEligibility(baseObjectives, objective, realm, influence);
        if (!eligibility.capturable && eligibility.reason) captureBlockers[realm] = eligibility.reason;
        return eligibility.capturable;
      });
      return {
        ...objective,
        capturableBy,
        captureBlockers,
      };
    });
    return {
      ...zone,
      current: zone.id === currentZoneId,
      control: zoneControl[zone.id] ?? defaultCampaignZoneControl(zone.id),
      influence,
      objectives,
    };
  });

  return {
    staticVersion: CAMPAIGN_STATIC_VERSION,
    mapHashes: { ...CAMPAIGN_STATIC_MAP_HASHES },
    zones,
    edges: CAMPAIGN_GRAPH_EDGES,
    activeZone: zones.find((zone) => zone.current) ?? null,
    contestedZones: zones.filter((zone) => zone.control === 'contested' && zone.nodeRole !== 'boss_lair').length,
    aegis: realmSummary('aegis', zones),
    riftbound: realmSummary('riftbound', zones),
    siegeRule: CAMPAIGN_SIEGE_RULE,
  };
}

export function objectiveKey(zoneId: string, objectiveId: string): string {
  return `${zoneId}:${objectiveId}`;
}

export function campaignZoneInfluence(
  zoneId: string,
  influenceState: CampaignZoneInfluenceState = {},
): CampaignZoneInfluence {
  const entry = influenceState[zoneId] ?? {};
  return {
    aegis: Math.max(0, Math.floor(entry.aegis ?? 0)),
    riftbound: Math.max(0, Math.floor(entry.riftbound ?? 0)),
    keepSiegeRequired: CAMPAIGN_KEEP_SIEGE_INFLUENCE_REQUIRED,
  };
}

export function isRvrKeepZone(zoneId: string): boolean {
  const role = CAMPAIGN_ZONE_BY_ID[zoneId]?.nodeRole;
  return role === 'battlefield' || role === 'fortress';
}

export function campaignObjectiveCaptureEligibility(
  objectives: Array<CampaignObjectiveDefinition & { control: CampaignControl }>,
  objective: CampaignObjectiveDefinition & { control: CampaignControl },
  realm: CampaignRealm,
  influence: CampaignZoneInfluence,
): { capturable: boolean; reason?: string } {
  if (objective.control === realm) {
    return { capturable: false, reason: 'Already controlled' };
  }

  if (objective.type !== 'keep') return { capturable: true };

  const battleObjectives = objectives.filter((entry) => entry.type === 'battle_objective');
  if (battleObjectives.length > 0 && battleObjectives.some((entry) => entry.control !== realm)) {
    return { capturable: false, reason: 'Control all three battlefield objectives first' };
  }

  if (influence[realm] < influence.keepSiegeRequired) {
    return {
      capturable: false,
      reason: `Build ${influence.keepSiegeRequired} realm influence first`,
    };
  }

  return { capturable: true };
}

export function campaignObjectiveDefenseEligibility(
  zoneId: string,
  objective: Pick<CampaignObjectiveStatus, 'type' | 'control' | 'defenseReadyAt'>,
  realm: CampaignRealm,
  nowMs: number = Date.now(),
): { defendable: boolean; reason?: string } {
  if (!isRvrKeepZone(zoneId) || objective.type !== 'battle_objective') {
    return { defendable: false, reason: 'Only battlefield and fortress standards can be defended' };
  }
  if (objective.control !== realm) {
    return { defendable: false, reason: 'Only friendly objectives can be defended' };
  }
  const readyAt = objective.defenseReadyAt[realm] ?? 0;
  if (readyAt > nowMs) {
    const seconds = Math.ceil((readyAt - nowMs) / 1000);
    return { defendable: false, reason: `Defense ready in ${seconds} second${seconds === 1 ? '' : 's'}` };
  }
  return { defendable: true };
}

export function campaignKeepCaptureReward(zoneId: string): CampaignClaimReward {
  const zone = CAMPAIGN_ZONE_BY_ID[zoneId];
  const tier = zone?.tier === 'Fortress' ? 5 : Number(zone?.tier.replace('T', '')) || 1;
  const strength = 5 + tier * 3;
  return {
    xp: 300 * tier,
    influence: 0,
    gold: 30 * tier,
    items: [{
      key: 'jewel_amulet_bloodglass',
      name: `${campaignZoneName(zoneId)} Victor's Amulet`,
      qty: 1,
      kind: 'armor',
      equipSlot: 'neck',
      strengthRoll: { min: strength, max: strength + 2 },
    }],
  };
}

export function formatCampaignControl(control: CampaignControl): string {
  switch (control) {
    case 'aegis':
      return CAMPAIGN_REALMS.aegis.shortLabel;
    case 'riftbound':
      return CAMPAIGN_REALMS.riftbound.shortLabel;
    case 'contested':
    default:
      return 'Contested';
  }
}

function realmSummary(realm: CampaignRealm, zones: CampaignZoneStatus[]): CampaignRealmSummary {
  const attackingAegis = realm === 'aegis';
  const pressureZones = attackingAegis ? AEGIS_PRESSURE_ZONES : RIFTBOUND_PRESSURE_ZONES;
  const cityZones = attackingAegis ? AEGIS_CITY_SIEGE_ZONES : RIFTBOUND_CITY_SIEGE_ZONES;
  const targetFortressId = attackingAegis ? 'rift_gate_fortress' : 'aegis_gate_fortress';
  const targetCityId = attackingAegis ? 'riftspire_capital' : 'aegis_capital';

  return {
    realm,
    label: CAMPAIGN_REALMS[realm].label,
    controlledZones: zones.filter((zone) => zone.control === realm && zone.nodeRole !== 'boss_lair').length,
    targetFortressId,
    targetFortressName: campaignZoneName(targetFortressId),
    fortressPressureReady: pressureZones.every((zoneId) => zoneControlIs(zones, zoneId, realm)),
    targetCityId,
    targetCityName: campaignZoneName(targetCityId),
    citySiegeReady: cityZones.every((zoneId) => zoneControlIs(zones, zoneId, realm)),
  };
}

function zoneControlIs(
  zones: CampaignZoneStatus[],
  zoneId: string,
  realm: CampaignRealm,
): boolean {
  return zones.find((zone) => zone.id === zoneId)?.control === realm;
}
