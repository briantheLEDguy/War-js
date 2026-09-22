/** JSON-safe support geometry shared by local movement and the campaign authority. */
export interface WalkableSurface {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  rotY: number;
  fromY: number;
  toY: number;
  axis: 'x' | 'z';
}

/** Structural subset of zone props; the server must not import browser world-loading code. */
export interface NavigationProp {
  id?: string;
  kind: string;
  x: number;
  z: number;
  y?: number;
  heightMode?: 'absolute';
  scale?: number;
  scaleX?: number;
  scaleY?: number;
  scaleZ?: number;
  rotY?: number;
  colliderSpace?: 'model';
  colliders?: Array<{ x?: number; z?: number; width: number; depth: number; rotY?: number; minY?: number; maxY?: number; blocksWhen?: 'always' | 'closed' }>;
  walkableSurfaces?: Array<Pick<WalkableSurface, 'width' | 'depth'> & Partial<Omit<WalkableSurface, 'width' | 'depth'>>>;
}

export const WALKABLE_STEP_UP = .85;

/** Only a measured flat support on the same slab permits stepping past its riser. */
export function colliderHasWalkableTop(collider: NonNullable<NavigationProp['colliders']>[number],
  surfaces: NavigationProp['walkableSurfaces']): boolean {
  if (collider.maxY === undefined) return false;
  return (surfaces ?? []).some(surface => Math.abs((surface.fromY ?? 0) - collider.maxY!) < .001
    && Math.abs((surface.toY ?? 0) - collider.maxY!) < .001
    && Math.abs((surface.x ?? 0) - (collider.x ?? 0)) < .001
    && Math.abs((surface.z ?? 0) - (collider.z ?? 0)) < .001
    && Math.abs((surface.rotY ?? 0) - (collider.rotY ?? 0)) < .001
    && surface.width >= collider.width * .9 && surface.depth >= collider.depth * .9);
}

export function colliderBlocksBody(collider: { minY?: number; maxY?: number; walkableTop?: boolean },
  feetY: number, height = 1.8): boolean {
  // A cylinder overlaps the next riser before its centre reaches that tread.
  // Keep the exact slab for head/underside collisions and skip only reachable tops.
  if (height <= 1.8 && collider.walkableTop && collider.maxY !== undefined
    && collider.maxY <= feetY + WALKABLE_STEP_UP) return false;
  return (collider.minY === undefined || feetY + height > collider.minY + .01)
    && (collider.maxY === undefined || feetY < collider.maxY - .01);
}

export function walkableSurfaceHeight(x: number, z: number, surface: WalkableSurface): number | null {
  const dx = x - surface.x, dz = z - surface.z;
  const cos = Math.cos(surface.rotY), sin = Math.sin(surface.rotY);
  const localX = dx * cos + dz * sin, localZ = -dx * sin + dz * cos;
  const halfW = surface.width / 2, halfD = surface.depth / 2;
  if (localX < -halfW || localX > halfW || localZ < -halfD || localZ > halfD) return null;
  const t = surface.axis === 'x' ? (localX + halfW) / surface.width : (localZ + halfD) / surface.depth;
  return surface.fromY + (surface.toY - surface.fromY) * Math.max(0, Math.min(1, t));
}

/** A higher roof cannot pull a player off a lower floor or teleport them onto a wallwalk. */
export function supportedGroundHeight(x: number, z: number, currentY: number, groundY: number, surfaces: readonly WalkableSurface[]): number {
  let height = groundY;
  for (const surface of surfaces) {
    const candidate = walkableSurfaceHeight(x, z, surface);
    if (candidate !== null && candidate <= currentY + WALKABLE_STEP_UP) height = Math.max(height, candidate);
  }
  return height;
}
