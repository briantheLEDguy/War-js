import type { PropSpawn } from '../../world/ZoneLoader';

export const ZONE_MAP_MAX_ZOOM = 8;

export function isMapPathProp(prop: PropSpawn): boolean {
  return ['path_dirt', 'path_brick', 'path_cobblestone'].includes(prop.kind);
}

/** Bound backing-store memory independently of the atlas's CSS zoom. */
export function mapResolutionScale(width: number, height: number, pixelRatio: number, zoom: number): number {
  return Math.min(pixelRatio * Math.max(1, zoom), 4096 / Math.max(width, height));
}

export interface MapSymbol {
  id: string;
  position: { x: number; y: number };
  radius: number;
  priority?: boolean;
}

/** Keep hit targets and icons together; leaders retain the exact world location. */
export function layoutMapSymbols<T extends MapSymbol>(symbols: T[], screenScale: number): T[] {
  const scale = Math.max(0.01, screenScale);
  const placed: T[] = [];
  const sorted = [...symbols].sort((a, b) => Number(Boolean(b.priority)) - Number(Boolean(a.priority)) || a.id.localeCompare(b.id));
  const buckets = new Map<string, T[]>();
  const cell = 32 / scale;
  for (const symbol of sorted) {
    let position = symbol.position;
    const overlaps = (point: typeof position) => {
      const cx = Math.floor(point.x / cell), cy = Math.floor(point.y / cell);
      for (let x = cx - 1; x <= cx + 1; x++) for (let y = cy - 1; y <= cy + 1; y++) {
        if (buckets.get(`${x}:${y}`)?.some(other => Math.hypot(point.x - other.position.x, point.y - other.position.y) < symbol.radius + other.radius + 3 / scale)) return true;
      }
      return false;
    };
    // Search outward deterministically, including coincident resources and guards.
    for (let ring = 1; overlaps(position); ring++) {
      const count = ring * 8;
      for (let i = 0; i < count; i++) {
        const angle = i / count * Math.PI * 2;
        position = { x: symbol.position.x + Math.cos(angle) * ring * 14 / scale, y: symbol.position.y + Math.sin(angle) * ring * 14 / scale };
        if (!overlaps(position)) break;
      }
    }
    const item = { ...symbol, position };
    placed.push(item);
    const key = `${Math.floor(position.x / cell)}:${Math.floor(position.y / cell)}`;
    const bucket = buckets.get(key) ?? [];
    bucket.push(item);
    buckets.set(key, bucket);
  }
  return placed;
}
