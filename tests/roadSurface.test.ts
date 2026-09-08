import { afterEach, expect, test, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { buildRoadSurface, roadSurfaceGeometry } from '../src/world/RoadSurface';
import { ResourceDisposer } from '../src/game/ResourceDisposer';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { PathDefinition, ZoneDefinition } from '../src/world/ZoneLoader';
import { defaultZoneConfigs } from '../src/shared/orvr/config';
import { Terrain } from '../src/world/Terrain';
// @ts-expect-error Executable road authoring source is intentionally an mjs module.
import { composeOrvrRoads } from '../scripts/campaign/orvr-road-network.mjs';

afterEach(() => vi.restoreAllMocks());
const path = (points: Array<[number, number]>, width = 12): PathDefinition => ({ id: 'road', style: 'dirt_trail', width, points: points.map(([x, z]) => ({ x, z })) });
const loader = (loadTexture: () => Promise<THREE.Texture | null>) => ({ loadTexture } as unknown as AssetLoader);

function verifyTriangles(geometry: THREE.BufferGeometry) {
  const positions = geometry.getAttribute('position'), indices = geometry.getIndex()!, seen = new Set<string>();
  let area = 0;
  for (let i = 0; i < indices.count; i += 3) {
    const a = indices.getX(i), b = indices.getX(i + 1), c = indices.getX(i + 2);
    const signedArea = (positions.getZ(b) - positions.getZ(a)) * (positions.getX(c) - positions.getX(a))
      - (positions.getX(b) - positions.getX(a)) * (positions.getZ(c) - positions.getZ(a));
    expect(signedArea).toBeGreaterThan(1e-8);
    area += signedArea / 2;
    const key = [a, b, c].map(index => `${positions.getX(index).toFixed(5)},${positions.getZ(index).toFixed(5)}`).sort().join('|');
    expect(seen.has(key)).toBe(false); seen.add(key);
  }
  for (const attribute of Object.values(geometry.attributes)) expect(Array.from(attribute.array).every(Number.isFinite)).toBe(true);
  expect(Number.isFinite(geometry.boundingSphere!.radius)).toBe(true);
  return area;
}

function opacityAt(geometry: THREE.BufferGeometry, x: number, z: number, indexCount = geometry.getIndex()!.count) {
  const positions = geometry.getAttribute('position'), alpha = geometry.getAttribute('color'), indices = geometry.getIndex()!;
  let opacity = 0;
  for (let index = 0; index < indexCount; index += 3) {
    const a = indices.getX(index), b = indices.getX(index + 1), c = indices.getX(index + 2);
    const ax = positions.getX(a), az = positions.getZ(a), bx = positions.getX(b), bz = positions.getZ(b), cx = positions.getX(c), cz = positions.getZ(c);
    const denominator = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz);
    const u = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / denominator;
    const v = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / denominator;
    if (u >= -1e-5 && v >= -1e-5 && u + v <= 1.00001) opacity = Math.max(opacity, alpha.getW(a) * u + alpha.getW(b) * v + alpha.getW(c) * (1 - u - v));
  }
  return opacity;
}

test('straight and right-angle roads retain full width without folded bend triangles', () => {
  const terminalArea = 42 * 6.6 ** 2 * Math.sin(Math.PI * 2 / 42) / 2;
  const straight = roadSurfaceGeometry([path([[0, 0], [20, 0]])], () => 0);
  expect(verifyTriangles(straight)).toBeCloseTo(20 * 13.2 + 2 * terminalArea, 3);
  expect(straight.boundingBox!.min.z).toBeCloseTo(-6.6); expect(straight.boundingBox!.max.z).toBeCloseTo(6.6);
  const bend = roadSurfaceGeometry([path([[0, 0], [10, 0], [10, 10]])], () => 0);
  // Ribbon area plus the two tessellated disks catches folded overlaps despite corrected winding.
  expect(verifyTriangles(bend)).toBeCloseTo(20 * 13.2 + 2 * terminalArea, 3);
  const positions = bend.getAttribute('position');
  expect(Array.from({ length: positions.count }, (_, i) => [positions.getX(i), positions.getZ(i)])
    .some(([x, z]) => Math.abs(x - 16.6) < .001 && Math.abs(z + 6.6) < .001)).toBe(true);
  straight.dispose(); bend.dispose();
});

test('narrow roads preserve ordered opacity bands and upward triangles', () => {
  const geometry = roadSurfaceGeometry([path([[0, 0], [5, 0]], .2)], () => 0);
  verifyTriangles(geometry);
  expect(geometry.boundingBox!.max.z - geometry.boundingBox!.min.z).toBeCloseTo(.3);
  const alpha = geometry.getAttribute('color');
  expect(alpha.itemSize).toBe(4);
  expect(Array.from({ length: alpha.count }, (_, i) => alpha.getW(i))).toContain(0);
  expect(Array.from({ length: alpha.count }, (_, i) => alpha.getW(i))).toContain(1);
  geometry.dispose();
});

test('repeated points, reversed duplicate paths and backtracked segments add no duplicate topology', () => {
  const baseline = roadSurfaceGeometry([path([[0, 0], [10, 0]])], () => 0);
  const noisy = roadSurfaceGeometry([path([[0, 0], [0, 0], [10, 0], [10, 0], [0, 0]]), path([[10, 0], [0, 0]])], () => 0);
  expect(noisy.getAttribute('position').array).toEqual(baseline.getAttribute('position').array);
  expect(noisy.getIndex()!.array).toEqual(baseline.getIndex()!.array);
  verifyTriangles(noisy); baseline.dispose(); noisy.dispose();
});

test('the real 12m/8m/5m Aegis delivery junction rounds its exposed width step with a feathered apron', () => {
  const zone = JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')) as ZoneDefinition;
  const roads = zone.paths!.filter(path => ['aegis_keep_road', 'aegis_support_link', 'aegis_keep_approach'].some(suffix => path.id!.endsWith(suffix)));
  expect(roads.map(road => road.width).sort((a, b) => a - b)).toEqual([5, 8, 12]);
  const geometry = roadSurfaceGeometry(roads, (x, z) => .01 * x + .02 * z);
  verifyTriangles(geometry);
  expect(geometry.userData.roadJunctions).toEqual([{ x: -350, z: -78, width: 12 }]);
  // This lies beyond the wide road's cut end and outside both narrow branches: the old square step left it unpaved.
  const uncappedOpacity = opacityAt(geometry, -353.6, -73.8, geometry.userData.roadRibbonIndexCount);
  expect(uncappedOpacity).toBeLessThan(.01);
  expect(opacityAt(geometry, -353.6, -73.8)).toBeGreaterThan(.99);
  const edgeOpacity = opacityAt(geometry, -354.2, -73.2);
  expect(edgeOpacity).toBeGreaterThan(.05); expect(edgeOpacity).toBeLessThan(.4);
  expect(opacityAt(geometry, -356.5, -71)).toBe(0);
  const positions = geometry.getAttribute('position'), uv = geometry.getAttribute('uv');
  for (let index = 0; index < positions.count; index++) {
    expect(positions.getY(index)).toBeCloseTo(.01 * positions.getX(index) + .02 * positions.getZ(index) + .045, 5);
    expect(uv.getX(index)).toBeCloseTo(positions.getX(index) / 2, 5);
    expect(uv.getY(index)).toBeCloseTo(-positions.getZ(index) / 2, 5);
  }
  geometry.dispose();
});

test('endpoint-on-interior junctions get one cap and duplicate paths add no extra terminal or junction caps', () => {
  const roads = [path([[-10, 0], [0, 0], [10, 0]], 12), path([[0, 0], [0, 10]], 5)];
  const original = structuredClone(roads), geometry = roadSurfaceGeometry(roads, () => 0);
  expect(geometry.userData.roadJunctions).toEqual([{ x: 0, z: 0, width: 12 }]);
  expect(geometry.userData.roadTerminals).toEqual([{ x: -10, z: 0, width: 12 }, { x: 0, z: 10, width: 5 }, { x: 10, z: 0, width: 12 }]);
  const duplicate = roadSurfaceGeometry([...roads, ...roads.map(road => ({ ...road, points: [...road.points].reverse() }))], () => 0);
  expect(duplicate.getAttribute('position').array).toEqual(geometry.getAttribute('position').array);
  expect(duplicate.getIndex()!.array).toEqual(geometry.getIndex()!.array);
  expect(roads).toEqual(original); verifyTriangles(geometry);
  geometry.dispose(); duplicate.dispose();
});

test('degree-one ends extend into rounded opaque interiors and feather without capping interior samples', () => {
  const geometry = roadSurfaceGeometry([path([[0, 0], [10, 0], [20, 0]], 6)], () => 2);
  verifyTriangles(geometry);
  expect(geometry.userData.roadJunctions).toEqual([]);
  expect(geometry.userData.roadTerminals).toEqual([{ x: 0, z: 0, width: 6 }, { x: 20, z: 0, width: 6 }]);
  expect(geometry.boundingBox!.min.x).toBeCloseTo(-3.6); expect(geometry.boundingBox!.max.x).toBeCloseTo(23.6);
  expect(opacityAt(geometry, 22.5, 0, geometry.userData.roadRibbonIndexCount)).toBe(0);
  expect(opacityAt(geometry, 22.5, 0)).toBeGreaterThan(.99);
  expect(opacityAt(geometry, 23.2, 0)).toBeGreaterThan(.2); expect(opacityAt(geometry, 23.2, 0)).toBeLessThan(.6);
  expect(opacityAt(geometry, 23.7, 0)).toBe(0); expect(opacityAt(geometry, 23, 3)).toBe(0);
  const positions = geometry.getAttribute('position');
  for (let index = 0; index < positions.count; index++) expect(positions.getY(index)).toBeCloseTo(2.045);
  geometry.dispose();
});

test('Ashen staging receives exactly one rounded end beyond its authored arrival position', () => {
  const zone = JSON.parse(readFileSync('public/assets/maps/ashen_steppe.json', 'utf8')) as ZoneDefinition;
  const stagingRoad = zone.paths!.find(road => road.id === 'ashen_steppe_aegis_staging_road')!;
  const endpoint = stagingRoad.points.at(-1)!, previous = stagingRoad.points.at(-2)!;
  expect(endpoint).toEqual({ x: -505, z: 80 });
  const length = Math.hypot(endpoint.x - previous.x, endpoint.z - previous.z);
  const forward = (distance: number) => ({ x: endpoint.x + (endpoint.x - previous.x) * distance / length, z: endpoint.z + (endpoint.z - previous.z) * distance / length });
  const geometry = roadSurfaceGeometry(zone.paths!, () => 0);
  expect(geometry.userData.roadTerminals.filter((point: { x: number; z: number }) => point.x === -505 && point.z === 80)).toEqual([{ x: -505, z: 80, width: 7 }]);
  const inside = forward(3), feather = forward(3.8), outside = forward(4.3);
  expect(opacityAt(geometry, inside.x, inside.z, geometry.userData.roadRibbonIndexCount)).toBe(0);
  expect(opacityAt(geometry, inside.x, inside.z)).toBeGreaterThan(.99);
  expect(opacityAt(geometry, feather.x, feather.z)).toBeGreaterThan(.1); expect(opacityAt(geometry, feather.x, feather.z)).toBeLessThan(.5);
  expect(opacityAt(geometry, outside.x, outside.z)).toBe(0);
  const positions = geometry.getAttribute('position'), indices = geometry.getIndex()!;
  let longestCapEdge = 0;
  for (let index = geometry.userData.roadRibbonIndexCount; index < indices.count; index += 3) {
    const vertices = [indices.getX(index), indices.getX(index + 1), indices.getX(index + 2)];
    for (let edge = 0; edge < 3; edge++) {
      const a = vertices[edge], b = vertices[(edge + 1) % 3];
      longestCapEdge = Math.max(longestCapEdge, Math.hypot(positions.getX(a) - positions.getX(b), positions.getZ(a) - positions.getZ(b)));
    }
  }
  expect(longestCapEdge).toBeLessThanOrEqual(2);
  geometry.dispose();
});

test('empty and invalid paths produce a finite empty mesh; invalid terrain height is rejected before allocation', () => {
  const geometry = roadSurfaceGeometry([path([[0, 0], [0, 0]]), path([[0, 0], [1, 0]], Infinity), path([[0, 0], [NaN, 1]])], () => 0);
  expect(geometry.getIndex()!.count).toBe(0); expect(geometry.getAttribute('position').count).toBe(0);
  expect(geometry.boundingSphere!.radius).toBe(0); geometry.dispose();
  expect(() => roadSurfaceGeometry([path([[0, 0], [4, 0]])], () => NaN)).toThrow('Non-finite road terrain height');
});

test('cross-road subdivision follows curved terrain and maintains world-aligned UVs across junctions', () => {
  const height = (x: number, z: number) => .01 * x * x + .005 * z * z;
  const geometry = roadSurfaceGeometry([path([[-10, 0], [10, 0]]), path([[0, 0], [0, 12]], 6)], height);
  const positions = geometry.getAttribute('position'), uv = geometry.getAttribute('uv'), index = geometry.getIndex()!;
  verifyTriangles(geometry);
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i), z = positions.getZ(i);
    expect(positions.getY(i)).toBeCloseTo(height(x, z) + .045, 5);
    expect(uv.getX(i)).toBeCloseTo(x / 2, 5); expect(uv.getY(i)).toBeCloseTo(-z / 2, 5);
  }
  for (let i = 0; i < index.count; i += 3) {
    const vertices = [index.getX(i), index.getX(i + 1), index.getX(i + 2)];
    const average = (component: 'getX' | 'getY' | 'getZ') => vertices.reduce((sum, vertex) => sum + positions[component](vertex), 0) / 3;
    expect(Math.abs(average('getY') - height(average('getX'), average('getZ')) - .045)).toBeLessThan(.03);
  }
  geometry.dispose();
});

test.each(defaultZoneConfigs().filter(zone => zone.kind !== 'city' && zone.id !== 'sunmeadow_march').map(zone => zone.id))('%s renders its real authored curves as finite upward geometry', id => {
  const zone = composeOrvrRoads(JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8'))) as ZoneDefinition;
  const geometry = roadSurfaceGeometry(zone.paths!, (x, z) => x * .01 + z * .02);
  expect(verifyTriangles(geometry)).toBeGreaterThan(15_000);
  expect(geometry.getAttribute('position').count).toBeLessThan(100_000);
  geometry.dispose();
});

test('a steep real zone attaches continuous roads above its rendered terrain triangles', async () => {
  const zone = composeOrvrRoads(JSON.parse(readFileSync('public/assets/maps/obsidian_scar.json', 'utf8'))) as ZoneDefinition;
  const opts = { size: zone.size, segments: zone.segments, orvrTerrain: zone.orvrLayout!.terrain, roads: zone.paths };
  const terrain = new Terrain(opts), ground = await terrain.build(loader(async () => null), opts) as THREE.Mesh;
  const road = ground.children.find(child => child.name === 'authored-road-ribbons') as THREE.Mesh;
  expect(road).toBeDefined();
  const terrainVertices = ground.geometry.getAttribute('position'), rowSize = zone.segments + 1;
  const renderedHeight = (x: number, z: number) => {
    const u = (x / zone.size + .5) * zone.segments, v = (z / zone.size + .5) * zone.segments;
    const ix = Math.floor(u), iz = Math.floor(v), tx = u - ix, tz = v - iz;
    const a = terrainVertices.getY(iz * rowSize + ix), b = terrainVertices.getY((iz + 1) * rowSize + ix);
    const c = terrainVertices.getY((iz + 1) * rowSize + ix + 1), d = terrainVertices.getY(iz * rowSize + ix + 1);
    return tx + tz <= 1 ? a * (1 - tx - tz) + b * tz + d * tx : b * (1 - tx) + c * (tx + tz - 1) + d * (1 - tz);
  };
  const positions = road.geometry.getAttribute('position'), indices = road.geometry.getIndex()!;
  let minimumClearance = Infinity;
  for (let i = 0; i < positions.count; i++) minimumClearance = Math.min(minimumClearance, positions.getY(i) - renderedHeight(positions.getX(i), positions.getZ(i)));
  for (let i = 0; i < indices.count; i += 3) {
    const vertices = [indices.getX(i), indices.getX(i + 1), indices.getX(i + 2)];
    const average = (component: 'getX' | 'getY' | 'getZ') => vertices.reduce((sum, vertex) => sum + positions[component](vertex), 0) / 3;
    minimumClearance = Math.min(minimumClearance, average('getY') - renderedHeight(average('getX'), average('getZ')));
  }
  expect(minimumClearance).toBeGreaterThan(0);
  new ResourceDisposer().object(ground);
}, 30_000);

test('road textures are independent clones and terminal scene cleanup releases each owned resource once', async () => {
  const base = new THREE.Texture(), normal = new THREE.Texture();
  base.repeat.set(12, 12); normal.colorSpace = THREE.SRGBColorSpace;
  const cachedDispose = [vi.spyOn(base, 'dispose'), vi.spyOn(normal, 'dispose')];
  let calls = 0;
  const mesh = await buildRoadSurface([path([[0, 0], [10, 0]])], () => 0, loader(async () => calls++ ? normal : base));
  const material = mesh.material as THREE.MeshStandardMaterial;
  expect(material.map).not.toBe(base); expect(material.normalMap).not.toBe(normal);
  expect(base.repeat.toArray()).toEqual([12, 12]); expect(normal.colorSpace).toBe(THREE.SRGBColorSpace);
  expect(material.map!.repeat.toArray()).toEqual([1, 1]); expect(material.normalMap!.colorSpace).toBe(THREE.NoColorSpace);
  expect(material.side).toBe(THREE.FrontSide); expect(material.depthWrite).toBe(false);
  expect(material.polygonOffset).toBe(true); expect(material.polygonOffsetFactor).toBeLessThan(0);
  expect(material.polygonOffsetUnits).toBeLessThan(0);
  expect(material.vertexColors).toBe(true); expect(mesh.receiveShadow).toBe(true);
  const disposal = [mesh.geometry, material, material.map!, material.normalMap!].map(resource => vi.spyOn(resource, 'dispose'));
  const disposer = new ResourceDisposer(); disposer.object(mesh); disposer.object(mesh);
  for (const spy of disposal) expect(spy).toHaveBeenCalledTimes(1);
  for (const spy of cachedDispose) expect(spy).not.toHaveBeenCalled();
  base.dispose(); normal.dispose();
});

test('missing optional textures retain the custom road geometry and rejected loads clean pending geometry', async () => {
  const mesh = await buildRoadSurface([path([[0, 0], [10, 0]])], () => 0, loader(async () => null));
  expect((mesh.material as THREE.MeshStandardMaterial).map).toBeNull();
  expect(mesh.geometry.getIndex()!.count).toBeGreaterThan(0);
  new ResourceDisposer().object(mesh);
  const disposal = vi.spyOn(THREE.BufferGeometry.prototype, 'dispose');
  await expect(buildRoadSurface([path([[0, 0], [10, 0]])], () => 0, loader(async () => { throw new Error('loader disposed'); }))).rejects.toThrow('loader disposed');
  expect(disposal).toHaveBeenCalledTimes(1);
});
