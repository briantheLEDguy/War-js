import type { OrvrTerrainControls, TerrainPoint } from '../shared/orvrTerrain';

type Realm = 'aegis' | 'riftbound';

export interface OrvrCaravanRoute {
  id: string;
  objectiveId: string;
  realm: Realm;
  destinationKeepId: string;
  points: TerrainPoint[];
  width: number;
  clearanceRadius: number;
  lengthMetres: number;
  assetKey: string;
}

export interface OrvrZoneArtDirection {
  zoneId: string;
  realm: Realm;
  races: string[];
  biomeId: string;
  season: 'spring' | 'summer' | 'autumn' | 'winter';
  cultures: string;
  vegetation: string[];
  fauna: string[];
  palette: string[];
  landmark: string;
  reliefMetres: number;
  vegetationAssetKeys: string[];
  creatureProfileKeys: string[];
  materialSetKey: string;
  architectureAssetKey: string;
  status: 'planned';
  parentZoneId?: string;
  bossProfileKey?: string;
  population?: string;
  optionalCampaignBranch?: boolean;
}

export interface OrvrKeepLayout extends TerrainPoint {
  objectiveId: string;
  realm: Realm;
  quartermaster: TerrainPoint;
  deliveryPoint: TerrainPoint;
  commander: TerrainPoint & { entityId: string };
  postern?: { propId: string; outside: TerrainPoint & { y: number }; inside: TerrainPoint & { y: number }; interactionRadius: number };
  posterns?: Array<{ id: string; label?: string; propId: string; outside: TerrainPoint & { y: number }; inside: TerrainPoint & { y: number }; interactionRadius: number }>;
  gates: Array<TerrainPoint & { id: string; stage: 'outer' | 'inner'; propId: string; width: number; depth: number; height: number; assetKey: string }>;
  siegeSlots: Array<TerrainPoint & { id: string; kind: 'oil' | 'catapult'; y: number; assetKey: string; operatorPosition?: TerrainPoint & { y: number } }>;
  ramSpawn: TerrainPoint & { assetKey: string };
  /** Reserved architectural envelopes; these must never become filled collision boxes. */
  collisionSlots: Array<TerrainPoint & { id: string; width: number; depth: number; height: number }>;
}

export interface OrvrZoneLayout {
  version: string;
  size: number;
  status: 'layout-ready-art-pending' | 'review-ready' | 'complete';
  assetPolicy: {
    mode: 'legacy-transition' | 'authored-required';
    allowNewPrimitiveModels: false;
    requiredAssetKeys: string[];
    optionalAssetKeys: string[];
  };
  battlefieldObjectives: Array<TerrainPoint & { objectiveId: string; initialRealm: 'neutral'; captureRadius: number }>;
  stagingCamps: Array<TerrainPoint & { id: string; realm: Realm; y: number; radius: number; capturable: false; respawnSeconds: number }>;
  keeps: OrvrKeepLayout[];
  caravanRoutes: OrvrCaravanRoute[];
  terrain: OrvrTerrainControls & {
    chunkSize: number;
    chunks: Array<TerrainPoint & { id: string; width: number; depth: number; assetKey: string; collisionAssetKey: string; lodDistances: number[]; status: 'planned' | 'approved' }>;
  };
  biome: {
    id: string;
    season: 'spring' | 'summer' | 'autumn' | 'winter';
    palette: string[];
    vegetationAssetKeys: string[];
    creatureProfileKeys: string[];
    placements?: Array<TerrainPoint & {
      id: string;
      biomeId: string;
      activeSeason: string;
      width: number;
      depth: number;
      count: number;
      seed: number;
      shape: 'rectangle';
      status: 'planned';
      approvedAssetKeys: string[];
      desiredAssetKeys: string[];
      exclude: Array<TerrainPoint & { radius: number }>;
      excludeCorridors: OrvrTerrainControls['clearCorridors'];
    }>;
  };
  populationAssignments: Array<{ entityId: string; race: string; role: string; desiredProfileKey: string; status: 'planned' }>;
}
