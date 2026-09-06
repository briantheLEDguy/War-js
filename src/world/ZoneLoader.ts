import { applyBiomeKits } from './BiomeKit';
import { applyZonePaths } from './PathKit';
import type { WorldLifeDefinition } from './worldLifeTypes';
import type { CanalDefinition } from './CityWater';
import type {
  CampaignLane,
  CampaignNodeRole,
  CampaignObjectiveType,
  CampaignRealm,
  CampaignTier,
} from '../data/campaign';
import type {
  CraftingProfessionId,
  CraftingStationKind,
  EquipSlot,
  ItemKind,
  WorldPropInteraction,
} from '../services/types';

export interface PropSpawn {
  /** Optional stable GM-editor id for static map props. Generated from prop index when omitted. */
  id?: string;
  kind: 'tree' | 'rock' | 'building' | 'dummy' | string;
  x: number;
  /** Optional vertical offset from terrain height. */
  y?: number;
  z: number;
  rotY?: number;
  scale?: number;
  /** Optional non-uniform scale for generated strips such as roads and trails. */
  scaleX?: number;
  scaleY?: number;
  scaleZ?: number;
  /** Optional .glb under /public/assets/models/ */
  model?: string;
  /** Optional reviewed architecture LOD1 and LOD2 filenames. */
  lodModels?: string[];
  /** Optional asset-index static key. Prefer this over direct model names. */
  assetKey?: string;
  /** If false, registers colliders/metadata without rendering a visible mesh. */
  visible?: boolean;
  /** Opt into mesh-local Three.js yaw for colliders and walkable surfaces. */
  colliderSpace?: 'model';
  colliders?: Array<{
    id?: string;
    /** Local offset from prop origin. */
    x?: number;
    z?: number;
    width: number;
    depth: number;
    rotY?: number;
    /** Optional local lower vertical bound for player collision. */
    minY?: number;
    /** Optional local upper vertical bound for player collision. */
    maxY?: number;
    blocksWhen?: 'always' | 'closed';
    interactionId?: string;
  }>;
  walkableSurfaces?: Array<{
    id?: string;
    /** Local offset from prop origin. */
    x?: number;
    z?: number;
    width: number;
    depth: number;
    rotY?: number;
    /** Local height at the low edge of the surface. */
    fromY?: number;
    /** Local height at the high edge of the surface. */
    toY?: number;
    /** Local axis used for the height ramp. Defaults to z. */
    axis?: 'x' | 'z';
  }>;
  interaction?: WorldPropInteraction;
}

export interface BiomeKitPlacement {
  id: string;
  biomeId: 'evergreen_pnw' | string;
  activeSeason?: 'spring' | 'summer' | 'autumn' | 'winter';
  x: number;
  z: number;
  width: number;
  depth: number;
  count: number;
  /** Deterministic scatter seed. */
  seed?: number;
  /** Optional vertical offset from terrain height for all generated props. */
  y?: number;
  /** Rotates the scatter patch around its center. */
  rotY?: number;
  /** Ellipse keeps landscaping soft; rectangle is useful for hedgelines. */
  shape?: 'ellipse' | 'rectangle';
  /** Optional subset of the kit's prop kinds for courtyards, planters, or edges. */
  allowedKinds?: string[];
  /** Holes inside the scatter patch for gates, roads, plazas, or spawn areas. */
  exclude?: Array<{
    x: number;
    z: number;
    radius: number;
  }>;
  /** Rectangular holes for large structures such as castles or plazas. */
  excludeRectangles?: Array<{
    x: number;
    z: number;
    width: number;
    depth: number;
    rotY?: number;
  }>;
  /** Polyline corridors that stay free of generated biome scatter. */
  excludeCorridors?: Array<{
    id: string;
    points: Array<{ x: number; z: number }>;
    radius: number;
  }>;
}

export interface EnemySpawn {
  id: string;
  name: string;
  level: number;
  x: number;
  /** Optional height hint above terrain for stacked walkable floors. */
  y?: number;
  z: number;
  maxHealth: number;
  /** Optional asset-index character profile key. Prefer this for humanoid enemies. */
  characterProfileKey?: string;
  /** Optional asset-index static key. Prefer this over direct model names. */
  assetKey?: string;
  model?: string;
  /** Lightweight combat behavior profile used by the enemy AI. */
  archetype?: 'raider' | 'guard' | 'caster' | 'beast' | 'captain';
  /** Optional staged keep finale; ordinary field captains remain independent quest targets. */
  encounter?: {
    type: 'keep_commander';
    objectiveId: string;
    realm: 'aegis' | 'riftbound';
    enrageHealthFraction: number;
  };
  /** 0 = passive (never aggros). Default: 0 */
  aggroRange?: number;
  /** Melee reach when attacking player. Default: 2.5 */
  attackRange?: number;
  /** Preferred stand-off distance for ranged/caster enemies. */
  preferredRange?: number;
  /** Base damage per hit. Default: 5 */
  attackDamage?: number;
  /** Movement speed in units/sec. Default: 3.5 */
  moveSpeed?: number;
}

/** A trigger volume that transports the player to another zone. */
export interface ZoneTrigger {
  id: string;
  /** Shown in travel UI, e.g. "Travel to Brightfen Approach" */
  label: string;
  x: number;
  z: number;
  /** Radius in world units — player within this distance activates the trigger. */
  radius: number;
  targetZoneId: string;
  targetSpawn?: { x: number; y: number; z: number };
}

/** A static NPC (vendor, trainer, banker, etc.) — no combat AI. */
export interface NpcSpawn {
  id: string;
  name: string;
  /** Sub-title shown in nameplate, e.g. "Merchant", "Master Trainer" */
  title?: string;
  role: 'vendor' | 'trainer' | 'banker' | 'questgiver' | 'guard' | 'ambient';
  x: number;
  /** Optional height hint above terrain for stacked walkable floors. */
  y?: number;
  z: number;
  rotY?: number;
  /** Optional asset-index character profile key. Prefer this over direct model names. */
  characterProfileKey?: string;
  /** Optional .glb under /public/assets/models/ */
  model?: string;
}

/** A non-combat interaction point that opens gathering/crafting UI. */
export interface CraftingStationSpawn {
  id: string;
  label: string;
  kind: CraftingStationKind;
  x: number;
  y?: number;
  z: number;
  radius?: number;
}

export type ResourceNodeKind =
  | 'herb'
  | 'ore'
  | 'wood'
  | 'water'
  | 'soil'
  | 'scrap'
  | 'relic';

export interface ResourceNodeSpawn {
  id: string;
  label: string;
  kind: ResourceNodeKind;
  professionId: CraftingProfessionId;
  x: number;
  y?: number;
  z: number;
  radius?: number;
  xp: number;
  respawnSeconds: number;
  /** Stable id of the visible prop that represents this node. */
  visualPropId?: string;
  loot: Array<{
    key: string;
    qty: number;
    name?: string;
    kind?: ItemKind;
    equipSlot?: EquipSlot;
    chance: number;
    minQty?: number;
    maxQty?: number;
  }>;
}

export interface RvrObjectiveDefinition {
  id: string;
  type: CampaignObjectiveType;
  label: string;
  x: number;
  z: number;
  captureRadius: number;
  defaultRealm: CampaignRealm;
  /** Same-zone objectives that the capturing realm must still control. */
  requiresObjectiveIds?: readonly string[];
}

export interface ZoneCampaignMetadata {
  realm: CampaignRealm;
  tier: CampaignTier;
  lane: CampaignLane;
  laneLabel: string;
  nodeRole: CampaignNodeRole;
  levelBand: string;
}

export interface ZoneDefinition {
  id: string;
  name: string;
  size: number;
  segments: number;
  skybox?: string;         // .hdr file
  terrainTexture?: string; // .png/.jpg
  /** Optional .glb under /public/assets/models/ used as the visible terrain. */
  terrainModel?: string;
  heightmap?: string;      // .png (phase 2)
  /** If true, terrain is completely flat (y=0 everywhere). Use for city zones. */
  flatTerrain?: boolean;
  /** Static campaign data version for generated Aegis/Riftbound maps. */
  staticMapVersion?: string;
  /** Hash of the committed static map data, excluding this hash field. */
  staticMapHash?: string;
  /** Campaign metadata for generated RvR zones. */
  campaign?: ZoneCampaignMetadata;
  /** Capturable objectives, keeps, fortresses, city gates, or boss goals. */
  rvrObjectives?: RvrObjectiveDefinition[];
  props: PropSpawn[];
  enemies: EnemySpawn[];
  spawnPoint?: { x: number; y: number; z: number };
  /** Zone exit triggers — walk into them to travel to another zone. */
  zoneTriggers?: ZoneTrigger[];
  /** Static NPCs: vendors, trainers, bankers, guards, etc. */
  npcs?: NpcSpawn[];
  /** Local cosmetic population and atmosphere, authored alongside static props. */
  ambientLife?: WorldLifeDefinition;
  /** Crafting workbenches and cultivation plots opened with the interact key. */
  craftingStations?: CraftingStationSpawn[];
  /** Data-driven harvest nodes opened with the interact key. */
  resourceNodes?: ResourceNodeSpawn[];
  /** Data-driven landscaping kits expanded into props when the zone loads. */
  biomeKits?: BiomeKitPlacement[];
  /** Non-blocking visual walking paths generated into props when the zone loads. */
  paths?: PathDefinition[];
  cityLayoutVersion?: string;
  cityExpansion?: {
    version: string;
    houses: number;
    trees: number;
    flowerbeds: number;
    districtCounts: Record<string, { houses: number; trees: number; flowerbeds: number }>;
  };
  cityElevation?: import('./CityElevation').CityElevation;
  cityCitadel?: {
    enclosure: { minX: number; maxX: number; minZ: number; maxZ: number };
    entranceGateIds: string[];
    keepGateId: string;
    interior: { name: string; minX: number; maxX: number; minZ: number; maxZ: number; galleryHeight: number };
    siege?: {
      objectiveOrder: string[];
      thronePropId: string;
      rooms: Array<{id: string; name: string; purpose: string; bounds: {minX: number; maxX: number; minZ: number; maxZ: number}; entry: {x: number; z: number}; floorY: number}>;
      vaultStaging: {south: Array<{x: number; z: number}>; north: Array<{x: number; z: number}>};
      decorationKinds: string[];
      decorationCount: number;
    };
    /** Connected world geometry; sealed future branches do not register travel triggers. */
    mountainExtension?: {
      name: string;
      bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
      internalGateId: string;
      battleHall: { minX: number; maxX: number; minZ: number; maxZ: number };
      commandChamber: { minX: number; maxX: number; minZ: number; maxZ: number };
      vault?: { minX: number; maxX: number; minZ: number; maxZ: number; gateIds: string[] };
      throneGateIds?: string[];
      staging: { south: Array<{ x: number; z: number }>; north: Array<{ x: number; z: number }> };
      routes: Array<{ id: string; name: string; width: number; points: Array<{ x: number; z: number }> }>;
      futureConnections: Array<{
        id: 'crypts' | 'vault'; name: string; status: 'sealed'; portalPropId: string;
        approach: { x: number; y: number; z: number };
        reservedBounds: { minX: number; maxX: number; minZ: number; maxZ: number };
      }>;
    };
  };
  cityBattlefield?: {
    name: string;
    playersPerTeam: number;
    bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
    staging: { south: Array<{ x: number; z: number }>; north: Array<{ x: number; z: number }> };
    approaches: Array<{ x: number; z: number; width: number }>;
  };
  cityDetailCounts?: { infillBuildings: number; streetFurnishings: number; courtFeatures: number };
  cityCivicDecorations?: {
    version: number;
    districtCounts: Record<string, { lights: number; artwork: number; furniture: number }>;
    mountedLanterns: number;
    streetlights: number;
    publicArt: number;
    tradeSigns: number;
    furniture: number;
  };
  canals?: CanalDefinition[];
  cityDistricts?: Array<{ id: string; name: string; x: number; z: number }>;
  explorationPlaces?: Array<{ name: string; x: number; z: number }>;
  atmosphere?: { fogColor: string; sunColor: string; sunIntensity: number };
}

export interface PathDefinition {
  id: string;
  style: 'dirt_trail' | 'cobblestone_avenue' | 'brick_walkway';
  /** Disable inferred joins for authored streets separated by water or walls. */
  autoConnect?: boolean;
  width: number;
  points: Array<{ x: number; z: number }>;
  y?: number;
}

export async function loadZone(id: string): Promise<ZoneDefinition> {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}assets/maps/${id}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const zone = applyZonePaths((await res.json()) as ZoneDefinition);
    return applyBiomeKits(zone);
  } catch (err) {
    console.warn(`[ZoneLoader] missing ${id}.json, using built-in default:`, err);
    return applyBiomeKits(applyZonePaths(buildInDefault(id)));
  }
}

function buildInDefault(id: string): ZoneDefinition {
  const props: PropSpawn[] = [];
  for (let i = 0; i < 24; i++) {
    const r = 8 + Math.random() * 30;
    const a = Math.random() * Math.PI * 2;
    props.push({
      kind: Math.random() < 0.7 ? 'tree' : 'rock',
      x: Math.cos(a) * r,
      z: Math.sin(a) * r,
    });
  }
  props.push({ kind: 'building', x: 12, z: -14, rotY: 0.7 });
  props.push({ kind: 'building', x: -15, z: 10, rotY: -0.4, scale: 0.9 });

  return {
    id,
    name: 'Training Outskirts',
    size: 120,
    segments: 96,
    terrainTexture: 'grass.png',
    skybox: 'sky.hdr',
    spawnPoint: { x: 0, y: 0, z: 0 },
    props,
    enemies: [
      {
        id: 'dummy-1',
        name: 'Training Dummy',
        level: 1,
        x: 5,
        z: -3,
        maxHealth: 60,
      },
      {
        id: 'dummy-2',
        name: 'Heavy Dummy',
        level: 3,
        x: -4,
        z: -5,
        maxHealth: 120,
      },
    ],
  };
}
