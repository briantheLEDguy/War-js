import * as THREE from 'three';
import type { PathDefinition } from './ZoneDefinition';

type Point = { x: number; z: number };
export interface RoadSurfaceOptions { vergeWidth?: number }
const HEIGHT_OFFSET = .045;
const MAX_EDGE_SPACING = 2;
const pointKey = (point: Point) => `${point.x.toFixed(5)},${point.z.toFixed(5)}`;

function uniqueRuns(path: PathDefinition, seen: Set<string>): Point[][] {
  if (!Number.isFinite(path.width) || path.width <= 0 || path.points.some(point => !Number.isFinite(point.x) || !Number.isFinite(point.z))) return [];
  const points: Point[] = [];
  for (const point of path.points) if (!points.length || Math.hypot(point.x - points.at(-1)!.x, point.z - points.at(-1)!.z) > .001) points.push(point);
  const runs: Point[][] = [];
  let run: Point[] = [];
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], key = `${path.width}:${[pointKey(a), pointKey(b)].sort().join('|')}`;
    if (seen.has(key)) { if (run.length > 1) runs.push(run); run = []; continue; }
    seen.add(key);
    if (!run.length) run.push(a);
    run.push(b);
  }
  if (run.length > 1) runs.push(run);
  return runs;
}

/** Fit authored bend joins before subdivision, so short resampled edges cannot fold behind a miter. */
export function roadSurfaceGeometry(paths: readonly PathDefinition[], heightAt: (x: number, z: number) => number, options: RoadSurfaceOptions = {}): THREE.BufferGeometry {
  if (options.vergeWidth !== undefined && (!Number.isFinite(options.vergeWidth) || options.vergeWidth < .3 || options.vergeWidth > 6)) throw new Error('Invalid road verge width');
  const edges = (half: number) => ({ inner: half - Math.min(options.vergeWidth === undefined ? .35 : options.vergeWidth / 3, half * .25),
    outer: half + (options.vergeWidth === undefined ? Math.min(.6, half * .5) : options.vergeWidth * 2 / 3) });
  const positions: number[] = [], uvs: number[] = [], colors: number[] = [], indices: number[] = [];
  const seen = new Set<string>();
  const runs = paths.flatMap((path, owner) => uniqueRuns(path, seen).map(points => ({ path, points, owner })));
  const junctionNodes = new Map<string, { point: Point; owners: Set<number>; neighbors: Set<string>; endpoint: boolean; halfWidth: number }>();
  for (const { path, points, owner } of runs) points.forEach((point, index) => {
    const key = pointKey(point);
    let node = junctionNodes.get(key);
    if (!node) { node = { point, owners: new Set(), neighbors: new Set(), endpoint: false, halfWidth: 0 }; junctionNodes.set(key, node); }
    node.owners.add(owner); node.endpoint ||= index === 0 || index === points.length - 1;
    if (index > 0) node.neighbors.add(pointKey(points[index - 1]));
    if (index < points.length - 1) node.neighbors.add(pointKey(points[index + 1]));
    node.halfWidth = Math.max(node.halfWidth, path.width / 2);
  });
  const nodes = [...junctionNodes.values()].sort((a, b) => a.point.x - b.point.x || a.point.z - b.point.z);
  const junctions = nodes.filter(node => node.endpoint && node.owners.size > 1 && node.neighbors.size > 1);
  const terminals = nodes.filter(node => node.endpoint && node.neighbors.size === 1);
  const caps = nodes.filter(node => node.endpoint && (node.owners.size > 1 || node.neighbors.size === 1));
  const vertex = (point: Point, alpha: number) => {
    const height = heightAt(point.x, point.z);
    if (!Number.isFinite(height)) throw new Error(`Non-finite road terrain height at ${point.x},${point.z}`);
    const index = positions.length / 3;
    positions.push(point.x, height + HEIGHT_OFFSET, point.z);
    uvs.push(point.x / 2, -point.z / 2); colors.push(1, 1, 1, alpha);
    return index;
  };
  const triangle = (a: number, b: number, c: number) => {
    const ax = positions[a * 3], az = positions[a * 3 + 2];
    const signedArea = (positions[b * 3 + 2] - az) * (positions[c * 3] - ax) - (positions[b * 3] - ax) * (positions[c * 3 + 2] - az);
    if (signedArea > 1e-9) indices.push(a, b, c);
    else if (signedArea < -1e-9) indices.push(a, c, b);
  };
  for (const { path, points } of runs) {
    const normals = points.slice(1).map((b, i) => {
      const a = points[i], length = Math.hypot(b.x - a.x, b.z - a.z);
      return { x: -(b.z - a.z) / length, z: (b.x - a.x) / length };
    });
    const half = path.width / 2, { inner, outer } = edges(half);
    const interiorCount = Math.max(1, Math.ceil(inner * 2 / MAX_EDGE_SPACING));
    const vergeSteps = Math.ceil((outer - inner) / MAX_EDGE_SPACING);
    const verge = Array.from({ length: vergeSteps }, (_, i) => inner + (i + 1) / vergeSteps * (outer - inner));
    const bands = [...verge.slice().reverse().map(n => -n), ...Array.from({ length: interiorCount + 1 }, (_, index) => -inner + index * inner * 2 / interiorCount), ...verge];
    const sections = points.map((point, index) => {
      const a = normals[Math.max(0, index - 1)], b = normals[Math.min(normals.length - 1, index)];
      const denominator = 1 + a.x * b.x + a.z * b.z;
      let nx = denominator > .001 ? (a.x + b.x) / denominator : a.x;
      let nz = denominator > .001 ? (a.z + b.z) / denominator : a.z;
      // Bound extreme authored hairpins; normal road bends retain their exact perpendicular width.
      const miterLength = Math.hypot(nx, nz);
      if (miterLength > 2) { nx *= 2 / miterLength; nz *= 2 / miterLength; }
      return bands.map(offset => ({ x: point.x + nx * offset, z: point.z + nz * offset }));
    });
    let previous = -1;
    const row = (section: Point[]) => {
      const start = positions.length / 3;
      for (const [band, point] of section.entries()) {
        vertex(point, Math.max(0, Math.min(1, (outer - Math.abs(bands[band])) / (outer - inner))));
      }
      if (previous >= 0) for (let band = 0; band < bands.length - 1; band++) {
        triangle(previous + band, previous + band + 1, start + band + 1);
        triangle(previous + band, start + band + 1, start + band);
      }
      previous = start;
    };
    row(sections[0]);
    for (let index = 1; index < sections.length; index++) {
      const a = sections[index - 1], b = sections[index];
      const count = Math.max(1, Math.ceil(Math.max(...a.map((point, band) => Math.hypot(point.x - b[band].x, point.z - b[band].z))) / MAX_EDGE_SPACING));
      for (let step = 1; step <= count; step++) row(a.map((point, band) => ({
        x: point.x + (b[band].x - point.x) * step / count, z: point.z + (b[band].z - point.z) * step / count,
      })));
    }
  }
  const ribbonIndexCount = indices.length;
  // One feathered apron rounds each junction or physical dead end; interior alignment samples get none.
  for (const { point, halfWidth } of caps) {
    const { inner, outer } = edges(halfWidth);
    // Leave room for the roughly 1m circumferential edge so ring diagonals also stay below 2m.
    const rings = Math.max(1, Math.ceil(inner / Math.sqrt(MAX_EDGE_SPACING ** 2 - 1)));
    const vergeRings = Math.ceil((outer - inner) / Math.sqrt(MAX_EDGE_SPACING ** 2 - 1));
    const radii = [...Array.from({ length: rings }, (_, index) => inner * (index + 1) / rings),
      ...Array.from({ length: vergeRings }, (_, index) => inner + (index + 1) / vergeRings * (outer - inner))];
    const segments = Math.max(24, Math.ceil(Math.PI * 2 * outer));
    const center = vertex(point, 1);
    let previous: number[] | null = null;
    for (const radius of radii) {
      const current = Array.from({ length: segments }, (_, index) => {
        const angle = index * Math.PI * 2 / segments;
        return vertex({ x: point.x + Math.cos(angle) * radius, z: point.z + Math.sin(angle) * radius }, Math.max(0, Math.min(1, (outer - radius) / (outer - inner))));
      });
      for (let index = 0; index < segments; index++) {
        const next = (index + 1) % segments;
        if (!previous) triangle(center, current[index], current[next]);
        else {
          triangle(previous[index], current[index], current[next]);
          triangle(previous[index], current[next], previous[next]);
        }
      }
      previous = current;
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 4));
  geometry.setIndex(indices); geometry.computeVertexNormals();
  if (indices.length) geometry.computeTangents();
  geometry.computeBoundingBox(); geometry.computeBoundingSphere();
  geometry.userData.roadJunctions = junctions.map(({ point, halfWidth }) => ({ x: point.x, z: point.z, width: halfWidth * 2 }));
  geometry.userData.roadTerminals = terminals.map(({ point, halfWidth }) => ({ x: point.x, z: point.z, width: halfWidth * 2 }));
  geometry.userData.roadRibbonIndexCount = ribbonIndexCount;
  return geometry;
}
