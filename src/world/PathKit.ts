import type { PathDefinition, PropSpawn, ZoneDefinition } from './ZoneLoader';

const MAX_PATH_CHUNK_LENGTH = 7.5;
const PATH_VISUAL_Y_OFFSET = 0.018;
const PATH_SURFACE_Y = 0.12;
const PATH_CHUNK_OVERLAP = 0.35;

function segmentToProp(
  path: PathDefinition,
  start: { x: number; z: number },
  end: { x: number; z: number },
  index: number,
): PropSpawn {
  const dx = end.x - start.x;
  const dz = end.z - start.z;
  const length = Math.hypot(dx, dz);
  const styleKind = path.style === 'cobblestone_avenue' ? 'path_cobblestone' : 'path_dirt';
  const depth = length + PATH_CHUNK_OVERLAP;
  const id = `${path.id}_segment_${index}`;

  return {
    kind: styleKind,
    x: start.x + dx * 0.5,
    y: path.y ?? PATH_VISUAL_Y_OFFSET,
    z: start.z + dz * 0.5,
    rotY: Math.atan2(dx, dz),
    scaleX: path.width,
    scaleY: 1,
    scaleZ: depth,
    walkableSurfaces: [
      {
        id: `${id}_walkable`,
        width: path.width,
        depth,
        fromY: PATH_SURFACE_Y,
        toY: PATH_SURFACE_Y,
      },
    ],
    id,
  } as PropSpawn & { id: string };
}

function segmentToChunkProps(
  path: PathDefinition,
  start: { x: number; z: number },
  end: { x: number; z: number },
  segmentIndex: number,
): PropSpawn[] {
  const dx = end.x - start.x;
  const dz = end.z - start.z;
  const length = Math.hypot(dx, dz);
  if (length <= 0.001) return [];

  const chunkCount = Math.max(1, Math.ceil(length / MAX_PATH_CHUNK_LENGTH));
  const props: PropSpawn[] = [];
  for (let i = 0; i < chunkCount; i += 1) {
    const t0 = i / chunkCount;
    const t1 = (i + 1) / chunkCount;
    props.push(segmentToProp(
      path,
      { x: start.x + dx * t0, z: start.z + dz * t0 },
      { x: start.x + dx * t1, z: start.z + dz * t1 },
      segmentIndex * 1000 + i,
    ));
  }
  return props;
}

export function applyZonePaths(zone: ZoneDefinition): ZoneDefinition {
  if (!zone.paths?.length) return zone;

  const generated: PropSpawn[] = [];
  for (const path of zone.paths) {
    for (let i = 0; i < path.points.length - 1; i += 1) {
      generated.push(...segmentToChunkProps(path, path.points[i], path.points[i + 1], i));
    }
  }

  return {
    ...zone,
    props: [...generated, ...zone.props],
  };
}
