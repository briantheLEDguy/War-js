/** Authored ground samples shared by rendering, movement and prop placement. */
export interface CityElevation {
  segments: number;
  /** Regions constant along x outside this interval need no dense x grid. */
  detailX?: [number, number];
  /** Flat regions outside this interval need no dense rendering grid. */
  detailZ?: [number, number];
  heights: number[];
}

export function cityHeightAt(field: CityElevation, size: number, x: number, z: number): number {
  const s = field.segments;
  const fx = Math.max(0, Math.min(s, (x / size + .5) * s));
  const fz = Math.max(0, Math.min(s, (z / size + .5) * s));
  const ix = Math.min(s - 1, Math.floor(fx)), iz = Math.min(s - 1, Math.floor(fz));
  const tx = fx - ix, tz = fz - iz;
  const h = (dx: number, dz: number) => field.heights[(iz + dz) * (s + 1) + ix + dx];
  // Match the two triangles used by citySurfaceGeometry, including their diagonal.
  return tz >= tx
    ? h(0, 0) + tz * (h(0, 1) - h(0, 0)) + tx * (h(1, 1) - h(0, 1))
    : h(0, 0) + tx * (h(1, 0) - h(0, 0)) + tz * (h(1, 1) - h(1, 0));
}
