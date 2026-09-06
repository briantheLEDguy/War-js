import type { Vec3 } from '../services/types';

export type EnemyAttackFootprint =
  | { shape: 'cone'; origin: Vec3; rotationY: number; range: number; halfAngleRad: number }
  | { shape: 'circle'; origin: Vec3; radius: number };

export interface EnemyCastState {
  abilityId: string;
  label: string;
  startedAt: number;
  dueAt: number;
  progress: number;
  responseCue: string;
  footprint: EnemyAttackFootprint;
}

/** Visuals and damage share the frozen footprint; neither follows a dodging player. */
export function enemyAttackContains(footprint: EnemyAttackFootprint, position: Vec3): boolean {
  const dx = position.x - footprint.origin.x;
  const dz = position.z - footprint.origin.z;
  const distance = Math.hypot(dx, dz);
  if (footprint.shape === 'circle') return distance <= footprint.radius;
  if (distance > footprint.range) return false;
  if (distance < 0.001) return true;
  const facingDot = (dx * Math.sin(footprint.rotationY) + dz * Math.cos(footprint.rotationY)) / distance;
  return facingDot >= Math.cos(footprint.halfAngleRad);
}

export function enemyCastProgress(cast: Pick<EnemyCastState, 'startedAt' | 'dueAt'>, now: number): number {
  return Math.max(0, Math.min(1, (now - cast.startedAt) / Math.max(1, cast.dueAt - cast.startedAt)));
}
