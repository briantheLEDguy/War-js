import type { WorldCollider } from './Props';
export function cityPositionBlocked(position: {
  x: number;
  y: number;
  z: number;
}, colliders: WorldCollider[], radius = .65): boolean {
  return colliders.some(c => {
    if (c.blocksWhen === 'closed' || position.y < (c.minY ?? -Infinity) || position.y > (c.maxY ?? Infinity))
      return false;
    const cos = Math.cos(c.rotY), sin = Math.sin(c.rotY);
    const dx = (position.x - c.x) * cos + (position.z - c.z) * sin;
    const dz = -(position.x - c.x) * sin + (position.z - c.z) * cos;
    return Math.hypot(Math.max(0, Math.abs(dx) - c.width / 2), Math.max(0, Math.abs(dz) - c.depth / 2)) < radius;
  });
}
export function safeCityEntry(position: {
  x: number;
  y: number;
  z: number;
}, spawn: {
  x: number;
  y: number;
  z: number;
}, colliders: WorldCollider[]) {
  return cityPositionBlocked(position, colliders) ? { ...spawn } : position;
}
