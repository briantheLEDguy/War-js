import type { PropSpawn, ZoneDefinition } from './ZoneLoader';

type BiomeSeason = 'spring' | 'summer' | 'autumn' | 'winter';

interface BiomePropOption {
  kind: string;
  weight: number;
  minScale: number;
  maxScale: number;
}

interface BiomeKitDefinition {
  id: string;
  defaultSeason: BiomeSeason;
  props: BiomePropOption[];
  seasons?: Partial<Record<BiomeSeason, BiomePropOption[]>>;
}

const EVERGREEN_PNW_SUMMER: BiomePropOption[] = [
  { kind: 'pnw_douglas_fir', weight: 7, minScale: 0.75, maxScale: 1.35 },
  { kind: 'pnw_western_red_cedar', weight: 5, minScale: 0.8, maxScale: 1.25 },
  { kind: 'pnw_hemlock', weight: 4, minScale: 0.65, maxScale: 1.15 },
  { kind: 'pnw_sword_fern', weight: 7, minScale: 0.65, maxScale: 1.35 },
  { kind: 'pnw_low_shrub', weight: 5, minScale: 0.6, maxScale: 1.25 },
  { kind: 'pnw_grass_clump', weight: 8, minScale: 0.55, maxScale: 1.35 },
  { kind: 'pnw_wildflower_clump', weight: 4, minScale: 0.45, maxScale: 1.05 },
  { kind: 'pnw_mossy_boulder', weight: 3, minScale: 0.65, maxScale: 1.45 },
  { kind: 'pnw_fallen_log', weight: 2, minScale: 0.7, maxScale: 1.25 },
];

const BIOME_KITS: Record<string, BiomeKitDefinition> = {
  evergreen_pnw: {
    id: 'evergreen_pnw',
    defaultSeason: 'summer',
    props: EVERGREEN_PNW_SUMMER,
    seasons: {
      summer: EVERGREEN_PNW_SUMMER,
    },
  },
};

export function applyBiomeKits(zone: ZoneDefinition): ZoneDefinition {
  if (!zone.biomeKits?.length) return zone;

  const pathCorridors = buildPathCorridors(zone);
  const biomeProps = zone.biomeKits.flatMap((placement) => {
    const kit = BIOME_KITS[placement.biomeId];
    if (!kit) {
      console.warn(`[BiomeKit] unknown biome kit "${placement.biomeId}" in zone "${zone.id}"`);
      return [];
    }
    return expandBiomePlacement(kit, placement, pathCorridors);
  });

  return {
    ...zone,
    props: [...zone.props, ...biomeProps],
  };
}

function expandBiomePlacement(
  kit: BiomeKitDefinition,
  placement: NonNullable<ZoneDefinition['biomeKits']>[number],
  pathCorridors: NonNullable<NonNullable<ZoneDefinition['biomeKits']>[number]['excludeCorridors']>,
): PropSpawn[] {
  const season = placement.activeSeason ?? kit.defaultSeason;
  const seasonProps = kit.seasons?.[season] ?? kit.props;
  const options = placement.allowedKinds?.length
    ? seasonProps.filter((option) => placement.allowedKinds?.includes(option.kind))
    : seasonProps;
  if (options.length === 0) {
    console.warn(`[BiomeKit] placement "${placement.id}" has no matching prop kinds`);
    return [];
  }

  const rng = createRng(hashSeed(`${placement.id}:${placement.seed ?? 0}`));
  const props: PropSpawn[] = [];
  const count = Math.max(0, Math.floor(placement.count));
  const shape = placement.shape ?? 'ellipse';
  const maxAttempts = count * 12;

  for (let attempts = 0; props.length < count && attempts < maxAttempts; attempts++) {
    const point = shape === 'rectangle'
      ? rectanglePoint(rng, placement.width, placement.depth)
      : ellipsePoint(rng, placement.width, placement.depth);
    const rotated = rotatePoint(point.x, point.z, placement.rotY ?? 0);
    const x = placement.x + rotated.x;
    const z = placement.z + rotated.z;

    if (
      isExcluded(
        x,
        z,
        placement.exclude,
        placement.excludeRectangles,
        [...pathCorridors, ...(placement.excludeCorridors ?? [])],
      )
    ) {
      continue;
    }

    const option = chooseWeighted(options, rng);
    const scale = lerp(option.minScale, option.maxScale, rng());
    props.push({
      kind: option.kind,
      x: roundCoord(x),
      z: roundCoord(z),
      y: placement.y,
      rotY: roundAngle(rng() * Math.PI * 2),
      scale: roundScale(scale),
    });
  }

  return props;
}

function buildPathCorridors(
  zone: ZoneDefinition,
): NonNullable<NonNullable<ZoneDefinition['biomeKits']>[number]['excludeCorridors']> {
  if (!zone.paths?.length) return [];
  return zone.paths
    .filter((path) => path.points.length > 1)
    .map((path) => ({
      id: path.id,
      points: path.points,
      radius: path.width / 2 + 2.75,
    }));
}

function createRng(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashSeed(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function chooseWeighted(options: BiomePropOption[], rng: () => number): BiomePropOption {
  const total = options.reduce((sum, option) => sum + option.weight, 0);
  let pick = rng() * total;
  for (const option of options) {
    pick -= option.weight;
    if (pick <= 0) return option;
  }
  return options[options.length - 1];
}

function ellipsePoint(rng: () => number, width: number, depth: number): { x: number; z: number } {
  const angle = rng() * Math.PI * 2;
  const radius = Math.sqrt(rng());
  return {
    x: Math.cos(angle) * radius * width * 0.5,
    z: Math.sin(angle) * radius * depth * 0.5,
  };
}

function rectanglePoint(rng: () => number, width: number, depth: number): { x: number; z: number } {
  return {
    x: (rng() - 0.5) * width,
    z: (rng() - 0.5) * depth,
  };
}

function rotatePoint(x: number, z: number, rotY: number): { x: number; z: number } {
  const cos = Math.cos(rotY);
  const sin = Math.sin(rotY);
  return {
    x: x * cos - z * sin,
    z: x * sin + z * cos,
  };
}

function isExcluded(
  x: number,
  z: number,
  exclude: NonNullable<NonNullable<ZoneDefinition['biomeKits']>[number]['exclude']> | undefined,
  excludeRectangles: NonNullable<NonNullable<ZoneDefinition['biomeKits']>[number]['excludeRectangles']> | undefined,
  excludeCorridors: NonNullable<NonNullable<ZoneDefinition['biomeKits']>[number]['excludeCorridors']>,
): boolean {
  if (exclude?.some((entry) => {
    const dx = x - entry.x;
    const dz = z - entry.z;
    return dx * dx + dz * dz <= entry.radius * entry.radius;
  })) {
    return true;
  }

  if (excludeRectangles?.some((entry) => pointInRectangle(x, z, entry))) {
    return true;
  }

  return excludeCorridors.some((corridor) => pointInCorridor(x, z, corridor.points, corridor.radius));
}

function pointInRectangle(
  x: number,
  z: number,
  rectangle: NonNullable<NonNullable<ZoneDefinition['biomeKits']>[number]['excludeRectangles']>[number],
): boolean {
  const dx = x - rectangle.x;
  const dz = z - rectangle.z;
  const cos = Math.cos(-(rectangle.rotY ?? 0));
  const sin = Math.sin(-(rectangle.rotY ?? 0));
  const localX = dx * cos - dz * sin;
  const localZ = dx * sin + dz * cos;
  return Math.abs(localX) <= rectangle.width / 2 && Math.abs(localZ) <= rectangle.depth / 2;
}

function pointInCorridor(
  x: number,
  z: number,
  points: Array<{ x: number; z: number }>,
  radius: number,
): boolean {
  if (points.length < 2) return false;
  const radiusSq = radius * radius;
  for (let i = 0; i < points.length - 1; i += 1) {
    if (distanceToSegmentSq(x, z, points[i], points[i + 1]) <= radiusSq) return true;
  }
  return false;
}

function distanceToSegmentSq(
  x: number,
  z: number,
  a: { x: number; z: number },
  b: { x: number; z: number },
): number {
  const dx = b.x - a.x;
  const dz = b.z - a.z;
  const lenSq = dx * dx + dz * dz;
  if (lenSq === 0) {
    const ax = x - a.x;
    const az = z - a.z;
    return ax * ax + az * az;
  }

  const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / lenSq));
  const px = a.x + dx * t;
  const pz = a.z + dz * t;
  const pxDx = x - px;
  const pzDz = z - pz;
  return pxDx * pxDx + pzDz * pzDz;
}

function lerp(min: number, max: number, t: number): number {
  return min + (max - min) * t;
}

function roundCoord(value: number): number {
  return Math.round(value * 10) / 10;
}

function roundAngle(value: number): number {
  return Math.round(value * 10000) / 10000;
}

function roundScale(value: number): number {
  return Math.round(value * 100) / 100;
}
