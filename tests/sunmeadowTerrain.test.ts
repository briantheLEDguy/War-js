import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { Terrain } from '../src/world/Terrain';
import { orvrGridHeightAt } from '../src/shared/orvrTerrain';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { OrvrZoneLayout } from '../src/world/orvrTypes';
import { roadAlphaRange } from '../authoring/blender/sunmeadow-terrain/validate.mjs';

const work = 'authoring/blender/sunmeadow-terrain/';
const source = JSON.parse(readFileSync(work + 'terrain-source.json', 'utf8'));
const report = JSON.parse(readFileSync(work + 'build-report.json', 'utf8')) as Array<{ key: string; x: number; z: number; lods: Array<{ model: string; level: number }> }>;

function surveyHeight(x: number, z: number): number {
  const fx = (x / source.size + .5) * source.segments, fz = (z / source.size + .5) * source.segments;
  const ix = Math.min(source.segments - 1, Math.floor(fx)), iz = Math.min(source.segments - 1, Math.floor(fz));
  const tx = fx - ix, tz = fz - iz;
  const at = (dx: number, dz: number) => source.heights[(iz + dz) * (source.segments + 1) + ix + dx];
  return (at(0,0) * (1-tx) + at(1,0) * tx) * (1-tz) + (at(0,1) * (1-tx) + at(1,1) * tx) * tz;
}

function glb(filename: string, includeSurfaceDetails = true) {
  const bytes = readFileSync(work + 'runtime/' + filename), length = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.subarray(20, 20 + length).toString());
  const accessor = (index: number): number[][] => {
    const a = doc.accessors[index], v = doc.bufferViews[a.bufferView];
    const components = ({ SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 } as Record<string, number>)[a.type];
    const size = a.componentType === 5123 ? 2 : a.componentType === 5121 ? 1 : 4;
    const stride = v.byteStride ?? components * size, start = 28 + length + (v.byteOffset ?? 0) + (a.byteOffset ?? 0);
    return Array.from({ length: a.count }, (_, i) => Array.from({ length: components }, (_, c) => {
      const offset = start + i * stride + c * size;
      const n = a.componentType === 5126 ? bytes.readFloatLE(offset) : size === 2 ? bytes.readUInt16LE(offset) : size === 1 ? bytes.readUInt8(offset) : bytes.readUInt32LE(offset);
      return a.normalized ? n / (size === 2 ? 65535 : 255) : n;
    }));
  };
  const surface = doc.meshes.find((mesh: { name: string }) => mesh.name.includes('_surface_')).primitives[0];
  return { doc, positions: accessor(surface.attributes.POSITION), normals: accessor(surface.attributes.NORMAL),
    colors: includeSurfaceDetails ? accessor(surface.attributes.COLOR_0) : [], indices: includeSurfaceDetails ? accessor(surface.indices).flat() : [] };
}

describe('authored Sunmeadow terrain exports', () => {
  it('keeps the generated live roads and terrain controls aligned with the accepted survey', () => {
    const live = JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8'));
    const geometryControls = (terrain: typeof source.terrain) => {
      const copy = structuredClone(terrain);
      for (const chunk of copy.chunks) delete chunk.status;
      return copy;
    };
    expect({ zoneId: live.id, size: live.size, segments: live.segments }).toEqual({ zoneId: source.zoneId, size: source.size, segments: source.segments });
    expect(live.paths).toEqual(source.paths);
    expect(geometryControls(live.orvrLayout.terrain)).toEqual(geometryControls(source.terrain));
  });

  it('exports road shoulder opacity through the color channel used by glTF renderers', () => {
    let checked = 0;
    for (const asset of report) for (const lod of asset.lods) {
      const bytes = readFileSync(work + 'runtime/' + lod.model), length = bytes.readUInt32LE(12);
      const doc = JSON.parse(bytes.subarray(20, 20 + length).toString());
      for (const mesh of doc.meshes) for (const primitive of mesh.primitives) {
        const material = doc.materials[primitive.material];
        if (material.name !== 'Sunmeadow_limestone_road') continue;
        const alpha = roadAlphaRange(bytes, doc, primitive);
        expect(material.alphaMode).toBe('BLEND');
        expect(alpha?.min).toBeLessThanOrEqual(.01); expect(alpha?.max).toBeGreaterThanOrEqual(.99);
        checked += 1;
      }
    }
    expect(checked).toBeGreaterThan(0);
  });

  it('matches the shared Float32 ground surface and keeps close-range triangle interpolation within 15 cm', () => {
    let maximumError = 0;
    let vertexError = 0, colorError = 0;
    for (let i = 0; i < source.heights.length; i += 19) {
      const x = (i % (source.segments + 1)) / source.segments * source.size - source.size / 2;
      const z = Math.floor(i / (source.segments + 1)) / source.segments * source.size - source.size / 2;
      expect(surveyHeight(x,z)).toBeCloseTo(orvrGridHeightAt(source.terrain, source.size, source.segments, x,z), 6);
    }
    for (const asset of report) {
      const { positions, indices, colors } = glb(asset.lods[0].model);
      for (let index = 0; index < positions.length; index += 1) {
        const [x, y, z] = positions[index];
        vertexError = Math.max(vertexError, Math.abs(y - surveyHeight(x + asset.x, z + asset.z)));
        const color = colors[index];
        colorError = Math.max(colorError, .7 - color[0], color[0] - 1, Math.abs(color[1] - color[0]), Math.abs(color[2] - color[0] * .96), Math.abs(color[3] - 1));
      }
      for (let i = 0; i < indices.length; i += 3) {
        const tri = indices.slice(i, i + 3).map(index => positions[index]);
        const x = tri.reduce((n, p) => n + p[0], 0) / 3 + asset.x, z = tri.reduce((n, p) => n + p[2], 0) / 3 + asset.z;
        const y = tri.reduce((n, p) => n + p[1], 0) / 3;
        maximumError = Math.max(maximumError, Math.abs(y - surveyHeight(x, z)));
      }
    }
    expect(maximumError).toBeLessThan(.15);
    expect(vertexError).toBeLessThan(.0001); expect(colorError).toBeLessThan(.0001);
  }, 30_000);

  it('retains every border sample and identical shared normals across all sector LODs', () => {
    const borders = new Map<string, number[]>();
    let maximumNormalDifference = 0, maximumHeightDifference = 0;
    for (const asset of report) for (const lod of asset.lods) {
      const { positions, normals } = glb(lod.model, false);
      const edges = [new Set<string>(), new Set<string>(), new Set<string>(), new Set<string>()];
      positions.forEach(([x, y, z], index) => {
        if (Math.abs(x) !== 150 && Math.abs(z) !== 150) return;
        const key = `${x + asset.x}:${z + asset.z}`;
        const current = [y, ...normals[index]];
        const previous = borders.get(key);
        if (previous) {
          maximumHeightDifference = Math.max(maximumHeightDifference, Math.abs(y - previous[0]));
          current.slice(1).forEach((value, i) => { maximumNormalDifference = Math.max(maximumNormalDifference, Math.abs(value - previous[i + 1])); });
        }
        else borders.set(key, current);
        if (x === -150) edges[0].add(key); if (x === 150) edges[1].add(key);
        if (z === -150) edges[2].add(key); if (z === 150) edges[3].add(key);
      });
      expect(edges.map(edge => edge.size)).toEqual([193, 193, 193, 193]);
    }
    expect(maximumHeightDifference).toBeLessThan(.00001);
    // Blender encodes custom loop normals at finite precision during export.
    expect(maximumNormalDifference).toBeLessThan(.001);
  });

  it('uses approved chunks while keeping authoritative grounding, and recovers a complete surface if a chunk is unavailable', async () => {
    const chunks = source.terrain.chunks.map((chunk: OrvrZoneLayout['terrain']['chunks'][number]) => ({ ...chunk, status: 'approved' as const }));
    const opts = { size: source.size, segments: source.segments, orvrTerrain: source.terrain, authoredChunks: chunks };
    const land = new THREE.MeshStandardMaterial({ name: 'Sunmeadow_short_grass' });
    const road = new THREE.MeshStandardMaterial({ name: 'Sunmeadow_limestone_road', transparent: true });
    const loader = {
      resolveApprovedAssetModels: async () => ['terrain.glb'],
      loadModel: async () => new THREE.Mesh(new THREE.BufferGeometry(), [land, road]),
    } as unknown as AssetLoader;
    const terrain = new Terrain(opts), mesh = await terrain.build(loader, opts);
    expect(mesh.userData.authoredTerrain).toBe(true); expect(mesh.children).toHaveLength(16);
    // Exported road decals must survive distant depth quantization while opaque ground still writes depth.
    expect(road.polygonOffset).toBe(true); expect(road.polygonOffsetFactor).toBeLessThan(0);
    expect(road.polygonOffsetUnits).toBeLessThan(0); expect(road.depthWrite).toBe(false);
    expect(land.polygonOffset).toBe(false); expect(land.depthWrite).toBe(true);
    expect(terrain.heightAt(180, 470)).toBeCloseTo(orvrGridHeightAt(source.terrain, source.size, source.segments, 180, 470), 6);
    loader.resolveApprovedAssetModels = async key => key === chunks[4].assetKey ? [] : ['terrain.glb'];
    const recovered = new Terrain(opts), fallback = await recovered.build(loader, opts);
    expect(fallback instanceof THREE.Mesh).toBe(true);
    expect(recovered.heightAt(180, 470)).toBeCloseTo(terrain.heightAt(180, 470), 6);
  }, 15_000); // Two full survey builds exercise hundreds of authored road samples.
});
