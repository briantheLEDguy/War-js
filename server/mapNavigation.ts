import type { NavigationProp } from '../src/shared/worldNavigation';
import { colliderHasWalkableTop } from '../src/shared/worldNavigation';
import type { ZoneConfig } from '../src/shared/orvr/protocol';

/** The same local/model yaw and terrain-relative placement used by the rendered map props. */
export function mapPropNavigation(props: NavigationProp[], groundAt: (x: number, z: number) => number,
  dynamicGateProps: ReadonlySet<string> = new Set()): Required<Pick<ZoneConfig, 'collision' | 'walkableSurfaces'>> {
  const collision: NonNullable<ZoneConfig['collision']> = [];
  const walkableSurfaces: NonNullable<ZoneConfig['walkableSurfaces']> = [];
  for (const prop of props) {
    const scale = prop.scale ?? 1;
    const sx = scale * (prop.scaleX ?? 1), sy = scale * (prop.scaleY ?? 1), sz = scale * (prop.scaleZ ?? 1);
    const yawSign = prop.colliderSpace === 'model' ? -1 : 1;
    const placementYaw = yawSign * (prop.rotY ?? 0);
    const placementCos = Math.cos(placementYaw), placementSin = Math.sin(placementYaw);
    const baseY = (prop.heightMode === 'absolute' ? 0 : groundAt(prop.x, prop.z)) + (prop.y ?? 0);
    const location = (x: number, z: number) => ({
      x: prop.x + x * sx * placementCos - z * sz * placementSin,
      z: prop.z + x * sx * placementSin + z * sz * placementCos,
    });
    for (const surface of prop.walkableSurfaces ?? []) {
      walkableSurfaces.push({
        id: surface.id ?? `${prop.id ?? prop.kind}_support_${walkableSurfaces.length}`,
        ...location(surface.x ?? 0, surface.z ?? 0),
        width: surface.width * sx, depth: surface.depth * sz,
        rotY: yawSign * ((prop.rotY ?? 0) + (surface.rotY ?? 0)),
        fromY: baseY + (surface.fromY ?? 0) * sy, toY: baseY + (surface.toY ?? 0) * sy,
        axis: surface.axis ?? 'z',
      });
    }
    if (prop.id && dynamicGateProps.has(prop.id)) continue;
    for (const collider of prop.colliders ?? []) {
      const yaw = yawSign * ((prop.rotY ?? 0) + (collider.rotY ?? 0));
      const c = Math.cos(yaw), s = Math.sin(yaw);
      const { x, z } = location(collider.x ?? 0, collider.z ?? 0);
      const width = collider.width * sx, depth = collider.depth * sz;
      const halfX = (Math.abs(c) * width + Math.abs(s) * depth) / 2;
      const halfZ = (Math.abs(s) * width + Math.abs(c) * depth) / 2;
      collision.push({ minX: x - halfX, maxX: x + halfX, minZ: z - halfZ, maxZ: z + halfZ,
        footprint: { x, z, width, depth, rotY: yaw },
        ...(colliderHasWalkableTop(collider, prop.walkableSurfaces) ? { walkableTop: true } : {}),
        ...(collider.minY === undefined ? {} : { minY: baseY + collider.minY * sy }),
        ...(collider.maxY === undefined ? {} : { maxY: baseY + collider.maxY * sy }),
      });
    }
  }
  return { collision, walkableSurfaces };
}
