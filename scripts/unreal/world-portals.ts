import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { BufferGeometry, PlaneGeometry } from 'three';
import { CAMPAIGN_NODES } from '../../shared/data/campaign.generated';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { roadSurfaceGeometry } from '../../shared/world/RoadSurface';
import { orvrHeightAt } from '../../shared/orvrTerrain';
import { canonicalJson, sha256, sourcePointToUnreal } from './content-contract';
import { isMain, repoRoot } from './toolchain';

// Stable development coordinates; adjacency is defined exclusively by the campaign graph.
export const worldOrigins: Record<string, [number, number, number]> = {
  aegis_capital: [0, 0, 0], brightfen_approach: [200000, 0, 0], sunmeadow_march: [-200000, 0, 0],
};
CAMPAIGN_NODES.map(node => node.id).filter(id => !worldOrigins[id]).sort().forEach((id, index) => {
  worldOrigins[id] = [600000 + (index % 6) * 200000, Math.floor(index / 6) * 200000, 0];
});
export function worldPoint(zone: string, point: { x: number; y?: number; z: number }): number[] {
  const origin = worldOrigins[zone];
  if (!origin) throw new Error(`Unknown zone: ${zone}`);
  const p = sourcePointToUnreal({ ...point, y: point.y ?? 0 });
  return [p.X + origin[0], p.Y + origin[1], p.Z + origin[2]];
}
export function sourceHeight(map: ZoneDefinition, x: number, z: number): number {
  if (map.craterCity || map.cityElevation) throw new Error('Authored city surfaces must be retained');
  if (map.flatTerrain) return 0;
  if (map.orvrLayout?.terrain) return orvrHeightAt(map.orvrLayout.terrain, x, z);
  const u = x / map.size, v = z / map.size;
  const hills = Math.sin(u * 5.2) * 0.6 + Math.cos(v * 4.7) * 0.5 + Math.sin((u + v) * 8.1) * 0.3;
  return (hills - Math.max(0, 1 - Math.hypot(u, v) * 4) * hills * 0.9) * 2;
}
/** Sample the same triangles exported to Unreal, keeping roads on the actual collision surface. */
export function terrainHeight(map: ZoneDefinition, x: number, z: number): number {
  const s = map.segments;
  const fx = Math.max(0, Math.min(s, (x / map.size + 0.5) * s));
  const fz = Math.max(0, Math.min(s, (z / map.size + 0.5) * s));
  const ix = Math.min(s - 1, Math.floor(fx)), iz = Math.min(s - 1, Math.floor(fz));
  const tx = fx - ix, tz = fz - iz;
  const at = (dx: number, dz: number) => Math.fround(sourceHeight(map, (ix + dx) / s * map.size - map.size / 2, (iz + dz) / s * map.size - map.size / 2));
  return tx + tz <= 1 ? at(0, 0) + tx * (at(1, 0) - at(0, 0)) + tz * (at(0, 1) - at(0, 0))
    : at(1, 1) + (1 - tx) * (at(0, 1) - at(1, 1)) + (1 - tz) * (at(1, 0) - at(1, 1));
}
export function portalPlan(maps: ZoneDefinition[]) {
  const zones = new Map(maps.map(map => [map.id, map]));
  if (zones.size !== maps.length) throw new Error('Duplicate zone ID');
  const ids = new Set<string>();
  const routes = maps.flatMap(map => (map.zoneTriggers ?? []).map(trigger => {
    if (!trigger.id || ids.has(trigger.id)) throw new Error('Duplicate or empty route ID');
    ids.add(trigger.id);
    const target = zones.get(trigger.targetZoneId);
    const reverse = target?.zoneTriggers?.filter(candidate => candidate.targetZoneId === map.id);
    if (!target || target.id === map.id || reverse?.length !== 1) throw new Error(`Missing or ambiguous reverse route: ${trigger.id}`);
    if (!Number.isFinite(trigger.radius) || trigger.radius < 1 || trigger.radius > 20) throw new Error('Invalid portal radius');
    if (!trigger.targetSpawn) throw new Error(`Missing arrival: ${trigger.id}`);
    if (Math.abs(trigger.x) > map.size / 2 || Math.abs(trigger.z) > map.size / 2
      || Math.abs(trigger.targetSpawn.x) > target.size / 2 || Math.abs(trigger.targetSpawn.z) > target.size / 2) throw new Error(`Route outside zone: ${trigger.id}`);
    const arrival = { ...trigger.targetSpawn };
    if (!target.craterCity && !target.cityElevation) arrival.y = terrainHeight(target, arrival.x, arrival.z);
    return { id: trigger.id, zoneId: map.id, targetZoneId: target.id, reverseId: reverse[0].id,
      label: target.name, radius: trigger.radius * 100, built: true,
      position: worldPoint(map.id, trigger), arrival: worldPoint(target.id, arrival) };
  }));
  return { schemaVersion: 2, developmentOnly: true, productionTravelAccepted: false,
    zones: maps.map(map => ({ id: map.id, name: map.name, origin: worldOrigins[map.id], size: map.size,
      status: map.id === 'aegis_capital' ? 'existing-capital-sublevel' : map.craterCity ? 'authored-crater' : 'source-terrain',
      palette: map.orvrLayout?.biome.palette ?? map.artDirection?.palette ?? ['#756b59', '#514a3d', '#b4a68a'],
      spawn: worldPoint(map.id, map.spawnPoint!),
      sourceSha256: sha256(canonicalJson(map)) })), routes };
}
function exportGeometry(geometry: BufferGeometry) {
  geometry.computeVertexNormals();
  const pos = geometry.getAttribute('position'), normal = geometry.getAttribute('normal'), uv = geometry.getAttribute('uv');
  const positions: number[][] = [], normals: number[][] = [], uvs: number[][] = [];
  for (let i = 0; i < pos.count; i++) {
    positions.push([pos.getZ(i) * 100, pos.getX(i) * 100, pos.getY(i) * 100]);
    normals.push([normal.getZ(i), normal.getX(i), normal.getY(i)]);
    uvs.push([uv.getX(i), uv.getY(i)]);
  }
  const indices = Array.from(geometry.index!.array);
  for (let i = 0; i < indices.length; i += 3) [indices[i + 1], indices[i + 2]] = [indices[i + 2], indices[i + 1]];
  geometry.dispose();
  return { positions, normals, uvs, indices };
}
export function outdoorTerrain(map: ZoneDefinition) {
  if (!worldOrigins[map.id] || map.craterCity || map.cityElevation) throw new Error('Unsupported heightfield terrain');
  if (!Number.isFinite(map.size) || map.size <= 0 || !Number.isInteger(map.segments) || map.segments < 1 || map.segments > 512) throw new Error('Invalid terrain grid');
  const geometry = new PlaneGeometry(map.size, map.size, map.segments, map.segments).rotateX(-Math.PI / 2);
  const positions = geometry.getAttribute('position'), uv = geometry.getAttribute('uv');
  for (let i = 0; i < positions.count; i++) {
    positions.setY(i, sourceHeight(map, positions.getX(i), positions.getZ(i)));
    uv.setXY(i, uv.getX(i) * map.size / 4, uv.getY(i) * map.size / 4);
  }
  return { zoneId: map.id, ...exportGeometry(geometry) };
}
export function outdoorRoads(map: ZoneDefinition) {
  const geometry = roadSurfaceGeometry(map.paths ?? [], (x, z) => terrainHeight(map, x, z));
  if (!geometry.index?.count) { geometry.dispose(); return null; }
  return { zoneId: map.id, ...exportGeometry(geometry) };
}
if (isMain(import.meta.url)) {
  const maps = CAMPAIGN_NODES.map(node => JSON.parse(readFileSync(path.join(repoRoot, 'public/assets/maps', `${node.id}.json`), 'utf8')) as ZoneDefinition);
  const plan = portalPlan(maps);
  const directory = path.join(repoRoot, 'artifacts/unreal/world-portals');
  mkdirSync(directory, { recursive: true });
  const terrainHashes: Record<string, string> = {};
  for (const map of maps.filter(map => !map.craterCity && map.id !== 'aegis_capital')) {
    for (const [suffix, data] of [['', outdoorTerrain(map)], ['_roads', outdoorRoads(map)]] as const) {
      if (!data) continue;
      const json = JSON.stringify(data), key = map.id + suffix;
      writeFileSync(path.join(directory, `${key}.json`), json);
      terrainHashes[key] = sha256(json);
    }
  }
  const sourceHashes = Object.fromEntries(maps.map(map => [map.id, sha256(readFileSync(path.join(repoRoot, 'public/assets/maps', `${map.id}.json`)))]));
  writeFileSync(path.join(directory, 'plan.json'), canonicalJson({ ...plan, sourceHashes, terrainHashes }));
  console.log(JSON.stringify({ zones: plan.zones.length, routes: plan.routes.length, terrainFiles: Object.keys(terrainHashes).length, nativeBuilt: false }));
}
