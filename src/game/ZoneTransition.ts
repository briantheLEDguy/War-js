export const ZONE_TRANSITION_GRACE_MS = 1000;

export interface ZoneEntryPoint {
  x: number;
  y: number;
  z: number;
}

type ZoneEntryPointInput = Partial<ZoneEntryPoint> | null | undefined;

export function resolveZoneEntryPoint(
  characterPosition: ZoneEntryPointInput,
  zoneSpawnPoint: ZoneEntryPointInput,
): ZoneEntryPoint {
  const candidate = isFiniteHorizontalPoint(characterPosition)
    ? characterPosition
    : zoneSpawnPoint;

  if (!isFiniteHorizontalPoint(candidate)) {
    return { x: 0, y: 0, z: 0 };
  }

  return {
    x: candidate.x,
    y: Number.isFinite(candidate.y) ? candidate.y : 0,
    z: candidate.z,
  };
}

export function zoneTransitionCanArm(
  nowMs: number,
  graceUntilMs: number,
  playerInsideTrigger: boolean,
): boolean {
  return nowMs >= graceUntilMs && !playerInsideTrigger;
}

function isFiniteHorizontalPoint(point: ZoneEntryPointInput): point is ZoneEntryPoint {
  return Boolean(point && Number.isFinite(point.x) && Number.isFinite(point.z));
}
