import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { PropSpawn } from '../../src/world/ZoneLoader';
import { cityHeightAt, type CityElevation } from '../../src/world/CityElevation';
import { sourcePointToUnreal, sourceYawToUnrealDegrees, sha256 } from './content-contract';
import { isMain, repoRoot } from './toolchain';

interface CapitalProps { id: string; size: number; cityElevation: CityElevation; props: PropSpawn[] }
export const CAPITAL_BUILDING_PROFILES = ['aegis_house_1', 'aegis_house_2', 'aegis_house_3',
  'aegis_house_4', 'aegis_house_5', 'aegis_house_6', 'aegis_rowhouse_1', 'aegis_rowhouse_2', 'aegis_wall'];

/** FBX imports use (source X, source Z, source Y); world uses (Z, X, Y).
 * A quarter turn with negative local Y scale performs that reflection. */
export function capitalPropPlacement(prop: PropSpawn, terrainHeight: number) {
  if (!prop.id || prop.rotY === undefined || (prop.rotX ?? 0) !== 0 || (prop.rotZ ?? 0) !== 0)
    throw new Error('Capital prop requires a stable identity and supported explicit yaw.');
  const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1);
  const sy = (prop.scale ?? 1) * (prop.scaleY ?? 1);
  const sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
  if (![sx, sy, sz].every(value => Number.isFinite(value) && value > 0)) throw new Error('Invalid capital scale.');
  const y = (prop.heightMode === 'absolute' ? 0 : terrainHeight) + (prop.y ?? 0);
  const position = sourcePointToUnreal({ x: prop.x, y, z: prop.z });
  const sign = prop.colliderSpace === 'model' ? -1 : 1;
  const surfaces = (prop.walkableSurfaces ?? []).map(surface => {
    const height = surface.fromY ?? 0;
    if (!Number.isFinite(height) || height !== (surface.toY ?? 0))
      throw new Error('Sloped walkable surfaces require a native ramp implementation.');
    // A technical slab ends exactly at the browser floor height. Its thickness
    // stays below the surface; it never replaces visible authored geometry.
    return { x: surface.x, z: surface.z, rotY: surface.rotY, width: surface.width,
      depth: surface.depth, minY: height - 0.01, maxY: height };
  });
  const originalColliderCount = prop.colliders?.length ?? 0;
  const colliders = [...(prop.colliders ?? []), ...surfaces].map((collider, index) => {
    if (collider.minY === undefined || collider.maxY === undefined || collider.maxY <= collider.minY
      || ![collider.width, collider.depth].every(value => Number.isFinite(value) && value > 0))
      throw new Error(`Capital collider requires finite explicit vertical bounds: ${prop.id}/${index}`);
    const x = (collider.x ?? 0) * sx, z = (collider.z ?? 0) * sz;
    const cos = Math.cos(prop.rotY!), sin = Math.sin(sign * prop.rotY!);
    const center = sourcePointToUnreal({ x: prop.x + x * cos - z * sin,
      y: y + (collider.minY + collider.maxY) * sy / 2, z: prop.z + x * sin + z * cos });
    return { index, source: collider, walkableSurface: index >= originalColliderCount, center,
      halfSize: [collider.depth * sz * 50, collider.width * sx * 50, (collider.maxY - collider.minY) * sy * 50],
      yawDegrees: -sourceYawToUnrealDegrees(sign * (prop.rotY! + (collider.rotY ?? 0))) };
  });
  return { id: prop.id, profileKey: prop.assetKey ?? prop.kind, source: prop, position,
    yawDegrees: sourceYawToUnrealDegrees(prop.rotY) + 90, scale: [sx, -sz, sy], colliders };
}

export function buildCapitalProps(map: CapitalProps) {
  if (map.id !== 'aegis_capital' || !map.cityElevation) throw new Error('Only authored Aegis placements are supported.');
  const ids = new Set<string>();
  // Keep every authored definition in the document. Only admitted profiles are
  // instantiated by the editor importer; all remaining identities stay pending.
  const objects = map.props.map(prop => {
    if (!prop.id || ids.has(prop.id)) throw new Error('Missing or duplicate capital prop identity.');
    ids.add(prop.id);
    return { id: prop.id, source: prop };
  });
  // Preserve the version-one field name used by existing native import receipts.
  const housePlacements = map.props.filter(prop => CAPITAL_BUILDING_PROFILES.includes(prop.assetKey ?? prop.kind) && prop.visible !== false)
    .map(prop => capitalPropPlacement(prop, cityHeightAt(map.cityElevation, map.size, prop.x, prop.z)));
  return { schemaVersion: 1, zoneId: map.id, objects, housePlacements, capitalReady: false };
}

if (isMain(import.meta.url)) {
  const source = 'public/assets/maps/aegis_capital.json';
  const bytes = readFileSync(path.join(repoRoot, source));
  const document = { ...buildCapitalProps(JSON.parse(bytes.toString('utf8'))), source, sourceSha256: sha256(bytes) };
  const directory = path.join(repoRoot, 'artifacts/unreal/capitals/aegis_capital');
  mkdirSync(directory, { recursive: true });
  writeFileSync(path.join(directory, 'props.json'), JSON.stringify(document, null, 2));
  console.log(JSON.stringify({ identities: document.objects.length, housePlacements: document.housePlacements.length, capitalReady: false }));
}
