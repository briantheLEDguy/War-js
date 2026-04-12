export interface PropSpawn {
  kind: 'tree' | 'rock' | 'building' | 'dummy' | string;
  x: number;
  z: number;
  rotY?: number;
  scale?: number;
  /** Optional .glb under /public/assets/models/ */
  model?: string;
}

export interface EnemySpawn {
  id: string;
  name: string;
  level: number;
  x: number;
  z: number;
  maxHealth: number;
  model?: string;
  /** 0 = passive (never aggros). Default: 0 */
  aggroRange?: number;
  /** Melee reach when attacking player. Default: 2.5 */
  attackRange?: number;
  /** Base damage per hit. Default: 5 */
  attackDamage?: number;
  /** Movement speed in units/sec. Default: 3.5 */
  moveSpeed?: number;
}

/** A trigger volume that transports the player to another zone. */
export interface ZoneTrigger {
  id: string;
  /** Shown in travel UI, e.g. "Travel to Reikland" */
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
  z: number;
  rotY?: number;
}

export interface ZoneDefinition {
  id: string;
  name: string;
  size: number;
  segments: number;
  skybox?: string;         // .hdr file
  terrainTexture?: string; // .png/.jpg
  heightmap?: string;      // .png (phase 2)
  /** If true, terrain is completely flat (y=0 everywhere). Use for city zones. */
  flatTerrain?: boolean;
  props: PropSpawn[];
  enemies: EnemySpawn[];
  spawnPoint?: { x: number; y: number; z: number };
  /** Zone exit triggers — walk into them to travel to another zone. */
  zoneTriggers?: ZoneTrigger[];
  /** Static NPCs: vendors, trainers, bankers, guards, etc. */
  npcs?: NpcSpawn[];
}

export async function loadZone(id: string): Promise<ZoneDefinition> {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}assets/maps/${id}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as ZoneDefinition;
  } catch (err) {
    console.warn(`[ZoneLoader] missing ${id}.json, using built-in default:`, err);
    return buildInDefault(id);
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
    name: 'Nordland Outskirts',
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
