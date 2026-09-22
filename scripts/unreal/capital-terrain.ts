import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { canalAt, citySurfaceGeometry, type CanalDefinition } from '../../shared/world/CityWater';
import { cityHeightAt, type CityElevation } from '../../shared/world/CityElevation';
import { canonicalJson, sha256, sourcePointToUnreal } from './content-contract';
import { isMain, repoRoot } from './toolchain';

interface CapitalGround {
  id: string;
  size: number;
  canals: CanalDefinition[];
  cityElevation: CityElevation;
}

export function buildCapitalTerrain(map: CapitalGround) {
  if (map.id !== 'aegis_capital') throw new Error('Only authored Aegis ground is supported; Riftspire must retain its crater meshes.');
  if (!Number.isFinite(map.size) || map.size <= 0 || !map.cityElevation || !Array.isArray(map.canals)) throw new Error('Missing capital ground definition.');
  const field = map.cityElevation;
  const count = (field.segments + 1) ** 2;
  if (!Number.isInteger(field.segments) || field.segments < 1 || field.segments > 2048) throw new Error('Invalid elevation resolution.');
  if (field.heights) {
    if (field.heights.length !== count || !field.heights.every(Number.isFinite)) throw new Error('Invalid dense elevation samples.');
  } else {
    let end = 0;
    if (!field.heightRuns?.length) throw new Error('Missing elevation samples.');
    for (const run of field.heightRuns) {
      if (!Array.isArray(run) || run.length !== 2 || !Number.isInteger(run[0]) || run[0] <= end || run[0] > count || !Number.isFinite(run[1])) throw new Error('Invalid elevation runs.');
      end = run[0];
    }
    if (end !== count) throw new Error('Incomplete elevation runs.');
  }
  for (const interval of [field.detailX, field.detailZ]) {
    if (interval && (interval.length !== 2 || !interval.every(Number.isFinite) || interval[0] > interval[1]
      || interval[0] < -map.size / 2 || interval[1] > map.size / 2)) throw new Error('Invalid elevation detail interval.');
  }
  const ids = new Set<string>();
  for (const canal of map.canals) {
    if (!canal.id || ids.has(canal.id) || ![canal.x, canal.z, canal.width, canal.depth, canal.waterY, canal.bedY].every(Number.isFinite)
      || canal.width <= 0 || canal.depth <= 0 || canal.bedY > canal.waterY
      || Math.abs(canal.x) + canal.width / 2 > map.size / 2 || Math.abs(canal.z) + canal.depth / 2 > map.size / 2) throw new Error('Invalid canal definition.');
    ids.add(canal.id);
  }
  const surfaces = (['ground', 'water', 'bed'] as const).map(kind => {
    const geometry = citySurfaceGeometry(map.size, map.canals, kind, kind === 'ground' ? {
      segments: field.segments, detailX: field.detailX, detailZ: field.detailZ,
      heightAt: (x, z) => cityHeightAt(field, map.size, x, z),
    } : undefined);
    try {
      const points = geometry.getAttribute('position'), normal = geometry.getAttribute('normal'), uv = geometry.getAttribute('uv');
      const positions: number[][] = [], normals: number[][] = [], uvs: number[][] = [];
      for (let i = 0; i < points.count; ++i) {
        const p = sourcePointToUnreal({ x: points.getX(i), y: points.getY(i), z: points.getZ(i) });
        positions.push([p.X, p.Y, p.Z]);
        normals.push([normal.getZ(i), normal.getX(i), normal.getY(i)]);
        uvs.push([uv.getX(i) * map.size / 4, uv.getY(i) * map.size / 4]);
      }
      const indices = Array.from(geometry.index!.array);
      // UE front-face winding is clockwise; keep the source triangles and their
      // upward normals, reversing only their winding after the axis conversion.
      for (let i = 0; i < indices.length; i += 3) [indices[i + 1], indices[i + 2]] = [indices[i + 2], indices[i + 1]];
      return { kind, collision: kind !== 'water', positions, normals, uvs, indices };
    } finally { geometry.dispose(); }
  });
  return { schemaVersion: 1, zoneId: map.id, sourceDefinitionSha256: sha256(canonicalJson(map)),
    units: 'centimeters', status: 'terrain-import-input-not-runtime-acceptance', surfaces };
}

if (isMain(import.meta.url)) {
  const source = 'public/assets/maps/aegis_capital.json';
  const bytes = readFileSync(path.join(repoRoot, source));
  const terrain = { ...buildCapitalTerrain(JSON.parse(bytes.toString('utf8'))), source, sourceSha256: sha256(bytes) };
  const map = JSON.parse(bytes.toString('utf8')) as CapitalGround;
  const directory = path.join(repoRoot, 'artifacts/unreal/capitals/aegis_capital');
  mkdirSync(directory, { recursive: true });
  writeFileSync(path.join(directory, 'terrain.json'), JSON.stringify(terrain));
  const points = [[0, -118], [-150, 0], [0, 75], [50, 75], [0, 149], [200, 280],
    ...map.canals.map(canal => [canal.x, canal.z]),
    ...[-160, -80, 0, 80, 160].flatMap(x => [25.25, 49.75, 80.25, 120.75, 149.25].map(z => [x, z]))];
  writeFileSync(path.join(directory, 'collision-fixtures.json'), JSON.stringify({ schemaVersion: 1, sourceSha256: sha256(bytes),
    points: points.map(([x, z]) => ({ sourceX: x, sourceZ: z, expectedHeightCm:
      (canalAt(map.canals, x, z)?.bedY ?? cityHeightAt(map.cityElevation, map.size, x, z)) * 100 })) }, null, 2));
  console.log(JSON.stringify({ zone: terrain.zoneId, surfaces: terrain.surfaces.map(surface => ({ kind: surface.kind,
    vertices: surface.positions.length, triangles: surface.indices.length / 3 })), nativeAcceptance: false }));
}
