import type { WorldEditDocument, WorldPropObject } from '../services/types';
import type { PropSpawn, ZoneDefinition } from './ZoneLoader';

/** Project the same editor document used by the world; never mutate the source zone. */
export function resolveMapZone(zone: ZoneDefinition, document: WorldEditDocument | null): ZoneDefinition {
  if (!document || document.zoneId !== zone.id) return zone;
  if (zone.cityLayoutVersion && document.cityLayoutVersion !== zone.cityLayoutVersion) return zone;
  const overrides = new Map(document.objects.map(object => [object.id, object]));
  const props: PropSpawn[] = [];
  const editedPaths = new Set<string>();
  const fromObject = (object: WorldPropObject, original?: PropSpawn): PropSpawn => ({
    ...original,
    id: object.id, label: object.label ?? original?.label, kind: object.kind, model: object.model, assetKey: object.assetKey,
    assetCategory: object.assetCategory, defaultAnimation: object.defaultAnimation,
    modelOffset: object.modelOffset, groundSurface: object.groundSurface,
    x: object.transform.position.x, y: object.transform.position.y, z: object.transform.position.z,
    rotX: object.transform.rotation.x, rotY: object.transform.rotation.y, rotZ: object.transform.rotation.z,
    scale: 1, scaleX: object.transform.scale.x, scaleY: object.transform.scale.y, scaleZ: object.transform.scale.z,
    colliders: object.colliders, walkableSurfaces: object.walkableSurfaces,
    colliderSpace: object.colliderSpace, interaction: object.interaction,
  });
  zone.props.forEach((prop, index) => {
    const id = prop.id ?? `static-prop-${index.toString().padStart(4, '0')}`;
    const override = overrides.get(id);
    if (!override) { props.push(prop); return; }
    overrides.delete(id);
    for (const path of zone.paths ?? []) {
      if (id.startsWith(`${path.id}_segment_`) || id.startsWith(`${path.id}_junction_`)) editedPaths.add(path.id);
    }
    if (!override.hidden && override.type === 'prop') props.push(fromObject(override, prop));
  });
  for (const object of overrides.values()) {
    if (object.type === 'prop' && !object.hidden && object.kind !== 'terrain') props.push(fromObject(object));
  }
  // A modified road chunk replaces its authored centerline with the actual visible strips.
  // Unchanged streets continue to use the continuous path network.
  const paths = zone.paths?.filter(path => !editedPaths.has(path.id));
  const columns = new Map<string, { prop: PropSpawn; height: number }>();
  for (const chunk of document.voxelChunks) for (const [key, cell] of Object.entries(chunk.cells)) {
    if (cell.density <= 0) continue;
    const [x, y, z] = key.split(':').map(Number);
    if (![x, y, z].every(Number.isFinite)) continue;
    const wx = chunk.origin.x + (x + 0.5) * chunk.voxelSize;
    const wz = chunk.origin.z + (z + 0.5) * chunk.voxelSize;
    const height = chunk.origin.y + (y + cell.density) * chunk.voxelSize;
    const columnKey = `${wx}:${wz}`;
    if ((columns.get(columnKey)?.height ?? -Infinity) >= height) continue;
    columns.set(columnKey, { height, prop: {
      id: `map-voxel-${columnKey}`, kind: `map_ground_${cell.material}`, x: wx, y: height, z: wz,
      walkableSurfaces: [{ width: chunk.voxelSize, depth: chunk.voxelSize }],
    } });
  }
  props.push(...Array.from(columns.values(), column => column.prop));
  return { ...zone, props, paths };
}
