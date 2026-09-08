/** Lossless runs of [exclusive sample end, height]; keep dense fields when smaller. */
export function compactCityElevation(field) {
  if (!field.heights) return field;
  const { heights, ...metadata } = field;
  if (heights.length !== (field.segments + 1) ** 2 || !heights.every(Number.isFinite)) {
    throw new Error('City elevation must contain one finite height per grid sample.');
  }
  const heightRuns = [];
  for (let index = 0; index < heights.length; index++) {
    const previous = heightRuns.at(-1);
    if (previous && previous[1] === heights[index]) previous[0] = index + 1;
    else heightRuns.push([index + 1, heights[index]]);
  }
  return heightRuns.length * 2 < heights.length ? { ...metadata, heightRuns } : field;
}

function sampleHeight(field, index) {
  if (field.heights) return field.heights[index];
  // Cumulative run ends allow random access without expanding the dense grid.
  const runs = field.heightRuns;
  let low = 0, high = runs.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (index < runs[middle][0]) high = middle;
    else low = middle + 1;
  }
  return runs[low][1];
}

/** Shared by Node authoring and the browser so scenery and movement use identical floors. */
export function cityHeightAt(field, size, x, z) {
  const s = field.segments;
  const fx = Math.max(0, Math.min(s, (x / size + .5) * s));
  const fz = Math.max(0, Math.min(s, (z / size + .5) * s));
  const ix = Math.min(s - 1, Math.floor(fx)), iz = Math.min(s - 1, Math.floor(fz));
  const tx = fx - ix, tz = fz - iz;
  const h = (dx, dz) => sampleHeight(field, (iz + dz) * (s + 1) + ix + dx);
  // Match the two triangles used by citySurfaceGeometry, including their diagonal.
  const h00 = h(0, 0), h11 = h(1, 1);
  if (tz >= tx) {
    const h01 = h(0, 1);
    return h00 + tz * (h01 - h00) + tx * (h11 - h01);
  }
  const h10 = h(1, 0);
  return h00 + tx * (h10 - h00) + tz * (h11 - h10);
}
