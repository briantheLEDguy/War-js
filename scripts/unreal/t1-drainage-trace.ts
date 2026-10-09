import type { FieldPoint } from '../../shared/terrainField';

export interface DrainageSeed {
  id: string; x: number; z: number; depth: number; width: number; maximumLength: number;
}

/** Author downhill controls in metres. This search runs during authoring, never movement authority. */
export function traceDrainage(seed: DrainageSeed, height: (x: number, z: number) => number,
  inside: (x: number, z: number, radius: number) => boolean) {
  if (!seed.id || ![seed.x, seed.z, seed.depth, seed.width, seed.maximumLength].every(Number.isFinite)
    || seed.depth < .1 || seed.depth > 24 || seed.width < 6 || seed.width > 60
    || seed.maximumLength < 32 || seed.maximumLength > 400) throw new Error('Invalid bounded drainage seed');
  const step = 8, course = [{ x: seed.x, z: seed.z, y: height(seed.x, seed.z) }];
  if (!Number.isFinite(course[0].y)) throw new Error('Nonfinite drainage ground');
  if (!inside(seed.x, seed.z, seed.width * 1.25)) return null;
  let length = 0;
  for (let i = 1; i < 50 && length + step <= seed.maximumLength; i++) {
    const p = course.at(-1)!;
    let best: { x: number; z: number; y: number; score: number } | undefined;
    for (let direction = 0; direction < 16; direction++) {
      const angle = direction * Math.PI / 8, x = p.x + Math.cos(angle) * step, z = p.z + Math.sin(angle) * step;
      if (!inside(x, z, seed.width * 1.25)) continue;
      const y = height(x, z);
      if (!Number.isFinite(y)) throw new Error('Nonfinite drainage ground');
      if (y >= p.y - .05) continue;
      let previous = p.y, clear = true;
      for (let j = 1; j <= 8; j++) {
        const h = height(p.x + (x - p.x) * j / 8, p.z + (z - p.z) * j / 8);
        if (!Number.isFinite(h)) throw new Error('Nonfinite drainage ground');
        if (h > previous + .15) { clear = false; break; }
        previous = h;
      }
      if (!clear) continue;
      const last = course.length > 1 ? course[course.length - 2] : undefined;
      const turn = last ? 1 - ((p.x - last.x) * (x - p.x) + (p.z - last.z) * (z - p.z)) / (step * step) : 0;
      const score = (p.y - y) / step - turn * .035;
      if (!best || score > best.score) best = { x, z, y, score };
    }
    if (!best) break;
    course.push({ x: best.x, z: best.z, y: best.y }); length += step;
  }
  if (course.length < 5 || course[0].y - course.at(-1)!.y < seed.depth * .7) return null;
  const points: FieldPoint[] = course.map((p, i) => ({ x: p.x, z: p.z,
    width: seed.width * (.8 + .4 * i / (course.length - 1)),
    height: seed.depth * Math.sin(Math.PI * i / (course.length - 1)) ** .9 }));
  points.at(-1)!.height = 0;
  // Cap depth against the downstream control, so tapering does not author an uphill outlet.
  for (let i = points.length - 2; i >= 0; i--) points[i].height = Math.max(0, Math.min(points[i].height,
    course[i].y - (course[i + 1].y - points[i + 1].height) - .02));
  points[0].height = 0;
  return { id: seed.id, points, length, sourceDrop: course[0].y - course.at(-1)!.y };
}
