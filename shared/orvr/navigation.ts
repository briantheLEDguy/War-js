import { createOrvrGridHeightSampler, type OrvrTerrainControls } from '../orvrTerrain';
import { colliderBlocksBody, supportedGroundHeight } from '../worldNavigation';
import type { Position, ZoneConfig } from './protocol';

// Derived samples stay outside saved campaign state. Static map controls are replaced as a revision.
const groundSamplers = new WeakMap<ZoneConfig, {
  terrain: OrvrTerrainControls; version: string; size: number; segments: number;
  at: (x: number, z: number) => number;
}>();

export function campaignGroundHeight(config: ZoneConfig, position: Position): number {
  if (!config.terrain && !config.walkableSurfaces?.length) return position.y;
  let ground = 0;
  if (config.terrain) {
    const size = config.terrainSize ?? config.bounds.maxX - config.bounds.minX;
    const segments = config.terrainSegments ?? 128;
    let sampler = groundSamplers.get(config);
    if (!sampler || sampler.terrain !== config.terrain || sampler.version !== config.terrain.sourceVersion
      || sampler.size !== size || sampler.segments !== segments) {
      sampler = { terrain: config.terrain, version: config.terrain.sourceVersion, size, segments,
        at: createOrvrGridHeightSampler(config.terrain, size, segments) };
      groundSamplers.set(config, sampler);
    }
    ground = sampler.at(position.x, position.z);
  }
  return supportedGroundHeight(position.x, position.z, position.y, ground, config.walkableSurfaces ?? []);
}

/** Missing vertical bounds retain legacy full-height blockers; authored lintels and undercrofts do not. */
export function campaignColliderBlocksHeight(collider: NonNullable<ZoneConfig['collision']>[number], feetY: number, height = 1.8): boolean {
  return colliderBlocksBody(collider, feetY, height);
}

/** Broad bounds accelerate rejection; the authored rotated wall decides actual contact. */
export function campaignColliderContains(collider: NonNullable<ZoneConfig['collision']>[number], position: Position, radius: number): boolean {
  if (position.x < collider.minX - radius || position.x > collider.maxX + radius
    || position.z < collider.minZ - radius || position.z > collider.maxZ + radius) return false;
  const box = collider.footprint;
  if (!box) return true;
  const dx = position.x - box.x, dz = position.z - box.z;
  const c = Math.cos(box.rotY), s = Math.sin(box.rotY);
  const localX = dx * c + dz * s, localZ = -dx * s + dz * c;
  const gapX = Math.max(0, Math.abs(localX) - box.width / 2);
  const gapZ = Math.max(0, Math.abs(localZ) - box.depth / 2);
  return gapX * gapX + gapZ * gapZ <= radius * radius;
}
