import type { WorldWalkableSurface } from './Props';

export interface CityPoint { x: number; y: number; z: number }

/** XZ membership is static, including lift cages. Store surface references so
 * moving lift heights remain current without rebuilding the spatial index. */
export class CraterFloorIndex {
  private cells = new Map<string, WorldWalkableSurface[]>();
  private readonly cellSize = 32;
  constructor(surfaces: readonly WorldWalkableSurface[]) {
    for (const surface of surfaces) {
      const cos = Math.abs(Math.cos(surface.rotY)), sin = Math.abs(Math.sin(surface.rotY));
      const halfX = (surface.width * cos + surface.depth * sin) / 2 + .015;
      const halfZ = (surface.width * sin + surface.depth * cos) / 2 + .015;
      for (let x = Math.floor((surface.x-halfX)/this.cellSize); x <= Math.floor((surface.x+halfX)/this.cellSize); x++) {
        for (let z = Math.floor((surface.z-halfZ)/this.cellSize); z <= Math.floor((surface.z+halfZ)/this.cellSize); z++) {
          const key = `${x},${z}`, entries = this.cells.get(key) ?? [];
          entries.push(surface); this.cells.set(key, entries);
        }
      }
    }
  }
  at(x: number, z: number): readonly WorldWalkableSurface[] {
    return this.cells.get(`${Math.floor(x/this.cellSize)},${Math.floor(z/this.cellSize)}`) ?? [];
  }
}

export interface CraterCityDefinition {
  version: string;
  basinY: number;
  levels: Array<{ id: string; name: string; y: number; radius: number }>;
  recovery: CityPoint[];
  lights?: Array<CityPoint & {color:string;intensity:number;distance:number}>;
  routes: Array<{ id: string; width: number; points: CityPoint[] }>;
  lifts: Array<{ id: string; name: string; propId: string; x: number; z: number; stops: Array<{ name: string; y: number }> }>;
  interiors: Array<{ id: string; name: string; entry: CityPoint; propId: string }>;
  formations: Array<{ id: string; teams: CityPoint[][] }>;
}

/** A floor is reachable only from its own height. Never raycast from the rim:
 * that selects bridge decks and roofs above lower streets and rooms. */
export function supportHeight(x: number, z: number, surface: WorldWalkableSurface): number | null {
  const cos = Math.cos(surface.rotY), sin = Math.sin(surface.rotY);
  const dx = (x - surface.x) * cos + (z - surface.z) * sin;
  const dz = -(x - surface.x) * sin + (z - surface.z) * cos;
  // Authoring coordinates are rounded to millimetres; tolerate only the seam,
  // not a player-sized gap between neighboring modules.
  if (Math.abs(dx) > surface.width / 2 + .015 || Math.abs(dz) > surface.depth / 2 + .015) return null;
  const span = surface.axis === 'x' ? surface.width : surface.depth;
  const t = Math.max(0, Math.min(1, (surface.axis === 'x' ? dx : dz) / span + .5));
  return surface.fromY + t * (surface.toY - surface.fromY);
}

export function craterGround(x: number, z: number, currentY: number, surfaces: readonly WorldWalkableSurface[], basinY = -300): number {
  if (![x,z,currentY].every(Number.isFinite)) return basinY - 30;
  let best = basinY - 30;
  for (const surface of surfaces) {
    const y = supportHeight(x, z, surface);
    if (y !== null && y <= currentY + .85 && y > best) best = y;
  }
  return best;
}

export function recoverCraterEntry(position: CityPoint, arrival: CityPoint, surfaces: readonly WorldWalkableSurface[]): CityPoint {
  const ground = craterGround(position.x, position.z, position.y, surfaces);
  return [position.x,position.y,position.z].every(Number.isFinite) && Math.abs(ground - position.y) <= 3
    ? { ...position, y: ground } : { ...arrival };
}

/** Recovery is always on a fixed, loaded floor, never an absent or moving cage. */
export function fixedCraterRecovery(city: CraterCityDefinition, position: CityPoint, arrival: CityPoint, surfaces: readonly WorldWalkableSurface[]): CityPoint | null {
  const moving = new Set(city.lifts.map(l => l.propId));
  const fixed = surfaces.filter(s => !s.sourceObjectId || !moving.has(s.sourceObjectId));
  const candidates = [position, arrival, ...city.recovery].filter(p => Number.isFinite(p.x+p.y+p.z)
    && Math.abs(craterGround(p.x,p.z,p.y,fixed,city.basinY)-p.y)<.85);
  candidates.sort((a,b) => Math.hypot(a.x-position.x,a.y-position.y,a.z-position.z)-Math.hypot(b.x-position.x,b.y-position.y,b.z-position.z));
  return candidates[0] ? {...candidates[0]} : null;
}

export function craterLevel(city: CraterCityDefinition, y: number) {
  return city.levels.reduce((a, b) => Math.abs(a.y - y) <= Math.abs(b.y - y) ? a : b);
}

/** Pure lift motion is also used by the collision and passenger controller. */
export function advanceLift(y: number, target: number, dt: number, speed = 9): number {
  return y + Math.sign(target - y) * Math.min(Math.abs(target - y), speed * Math.max(0, dt));
}
