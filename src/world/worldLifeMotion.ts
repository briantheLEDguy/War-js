export interface WorldLifePoint {
  x: number;
  z: number;
}

export interface WorldLifeRouteSample extends WorldLifePoint {
  /** Rotation around Y, with local +Z as forward. */
  heading: number;
  moving: boolean;
}

interface RouteSegment {
  from: WorldLifePoint;
  to: WorldLifePoint;
  seconds: number;
  heading: number;
}

/** Samples a closed route in absolute time, including a dwell at the origin. */
export function sampleWorldLifeRoute(
  origin: WorldLifePoint,
  route: readonly WorldLifePoint[] | undefined,
  elapsedSeconds: number,
  speed: number,
  pauseSeconds: number,
): WorldLifeRouteSample {
  const start = {
    x: Number.isFinite(origin.x) ? origin.x : 0,
    z: Number.isFinite(origin.z) ? origin.z : 0,
  };
  const stationary: WorldLifeRouteSample = { ...start, heading: 0, moving: false };
  if (!route?.length || !Number.isFinite(speed) || speed <= 0) return stationary;

  const points: WorldLifePoint[] = [start];
  for (const point of route) {
    const previous = points[points.length - 1];
    if (Number.isFinite(point.x) && Number.isFinite(point.z)
      && (point.x !== previous.x || point.z !== previous.z)) {
      points.push(point);
    }
  }
  const last = points[points.length - 1];
  if (points.length > 1 && last.x === start.x && last.z === start.z) points.pop();
  if (points.length < 2) return stationary;

  const pause = Number.isFinite(pauseSeconds) ? Math.max(0, pauseSeconds) : 0;
  const segments: RouteSegment[] = [];
  let cycleSeconds = 0;
  for (let index = 0; index < points.length; index++) {
    const from = points[index];
    const to = points[(index + 1) % points.length];
    const dx = to.x - from.x;
    const dz = to.z - from.z;
    const seconds = Math.hypot(dx, dz) / speed;
    // Reject unrepresentable routes as a whole rather than skipping an edge and teleporting.
    if (!Number.isFinite(seconds) || seconds <= 0) return stationary;
    segments.push({ from, to, seconds, heading: Math.atan2(dx, dz) });
    cycleSeconds += pause + seconds;
  }
  if (!Number.isFinite(cycleSeconds)) return stationary;

  const elapsed = Number.isFinite(elapsedSeconds) ? Math.max(0, elapsedSeconds) : 0;
  let phase = elapsed % cycleSeconds;
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index];
    if (phase < pause) {
      const incoming = segments[(index + segments.length - 1) % segments.length];
      return { ...segment.from, heading: incoming.heading, moving: false };
    }
    phase -= pause;
    if (phase < segment.seconds) {
      const progress = phase / segment.seconds;
      return {
        x: segment.from.x + (segment.to.x - segment.from.x) * progress,
        z: segment.from.z + (segment.to.z - segment.from.z) * progress,
        heading: segment.heading,
        moving: true,
      };
    }
    phase -= segment.seconds;
  }

  // Rounding at the loop seam still lands exactly on the shared endpoint.
  return { ...start, heading: segments[segments.length - 1].heading, moving: pause === 0 };
}
