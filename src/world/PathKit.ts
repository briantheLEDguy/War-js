import type { PathDefinition, PropSpawn, ZoneDefinition } from './ZoneLoader';

const MAX_PATH_CHUNK_LENGTH = 7.5;
const PATH_VISUAL_Y_OFFSET = 0.018;
const PATH_CHUNK_OVERLAP = 0.85;
const PATH_JUNCTION_CAP_SCALE = 1.12;
const PATH_ENDPOINT_JOIN_SCALE = 2.6;

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
    id,
  } as PropSpawn & { id: string };
}

function pointToCapProp(path: PathDefinition, point: { x: number; z: number }, index: number): PropSpawn {
  const styleKind = path.style === 'cobblestone_avenue' ? 'path_cobblestone' : 'path_dirt';
  return {
    kind: styleKind,
    x: point.x,
    y: path.y ?? PATH_VISUAL_Y_OFFSET,
    z: point.z,
    rotY: 0,
    scaleX: path.width * PATH_JUNCTION_CAP_SCALE,
    scaleY: 1,
    scaleZ: path.width * PATH_JUNCTION_CAP_SCALE,
    id: `${path.id}_junction_${index}`,
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
    path.points.forEach((point, index) => {
      generated.push(pointToCapProp(path, point, index));
    });
  }

  generated.push(...buildEndpointConnectors(zone.paths));

  return {
    ...zone,
    props: [...generated, ...zone.props],
  };
}

function buildEndpointConnectors(paths: PathDefinition[]): PropSpawn[] {
  const endpoints = paths.flatMap((path) => [
    { path, point: path.points[0], edge: 'start' },
    { path, point: path.points[path.points.length - 1], edge: 'end' },
  ]).filter((endpoint) => endpoint.point);
  const connectors: PropSpawn[] = [];

  for (let i = 0; i < endpoints.length; i += 1) {
    for (let j = i + 1; j < endpoints.length; j += 1) {
      const a = endpoints[i];
      const b = endpoints[j];
      if (a.path.id === b.path.id) continue;

      const distance = Math.hypot(b.point.x - a.point.x, b.point.z - a.point.z);
      const maxJoinDistance = Math.max(a.path.width, b.path.width) * PATH_ENDPOINT_JOIN_SCALE;
      if (distance <= 0.01 || distance > maxJoinDistance) continue;

      const connectorPath: PathDefinition = {
        id: `${a.path.id}_${a.edge}_to_${b.path.id}_${b.edge}`,
        style: a.path.style === 'cobblestone_avenue' || b.path.style === 'cobblestone_avenue'
          ? 'cobblestone_avenue'
          : 'dirt_trail',
        width: Math.max(a.path.width, b.path.width),
        points: [a.point, b.point],
        y: a.path.y ?? b.path.y,
      };
      connectors.push(...segmentToChunkProps(connectorPath, a.point, b.point, connectors.length));
    }
  }

  return connectors;
}
