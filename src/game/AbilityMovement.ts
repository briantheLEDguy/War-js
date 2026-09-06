import * as THREE from 'three';
import type { Vec3 } from '../services/types';

/** Sweep the entire move before committing it; a blocked dash never crosses a wall or spends its cost. */
export function resolveAbilityMovement(
  origin: Vec3,
  destination: Vec3,
  groundHeightAt: (x: number, z: number, currentY?: number) => number,
  resolveCollision: (position: THREE.Vector3, radius: number) => void,
): Vec3 | null {
  if (![origin.x, origin.y, origin.z, destination.x, destination.z].every(Number.isFinite)) return null;
  const distance = Math.hypot(destination.x - origin.x, destination.z - origin.z);
  if (distance > 12.01 || distance < 0.01) return null;
  const steps = Math.ceil(distance / 0.2);
  let previousHeight = groundHeightAt(origin.x, origin.z, origin.y);
  for (let step = 1; step <= steps; step++) {
    const x = origin.x + (destination.x - origin.x) * step / steps;
    const z = origin.z + (destination.z - origin.z) * step / steps;
    const height = groundHeightAt(x, z, previousHeight);
    if (!Number.isFinite(height) || Math.abs(height - previousHeight) > 0.85) return null;
    const probe = new THREE.Vector3(x, height, z);
    resolveCollision(probe, 0.45);
    if (Math.hypot(probe.x - x, probe.z - z) > 0.01) return null;
    previousHeight = height;
  }
  return { x: destination.x, y: previousHeight, z: destination.z };
}
