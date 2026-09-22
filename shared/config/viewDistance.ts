export const VIEW_DISTANCE_MIN = 200;
export const VIEW_DISTANCE_MAX = 1000;
export const VIEW_DISTANCE_STEP = 25;
export const DEFAULT_VIEW_DISTANCE = 500;

export function clampViewDistance(value: unknown, fallback = DEFAULT_VIEW_DISTANCE): number {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.max(VIEW_DISTANCE_MIN, Math.min(VIEW_DISTANCE_MAX, value))
    : fallback;
}

export function viewDistanceFogNear(viewDistance: number): number {
  return Math.max(50, Math.round(viewDistance * 0.28));
}

export function formatViewDistance(viewDistance: number): string {
  return `${Math.round(viewDistance)} m`;
}
