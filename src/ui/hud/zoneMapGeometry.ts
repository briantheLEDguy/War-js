import type { PropSpawn, ZoneDefinition } from '../../world/ZoneLoader';

export type MapFeatureRole = 'ground' | 'wall' | 'building' | 'landmark' | 'nature' | 'detail' | 'hidden';
export interface MapFeature {
  prop: PropSpawn;
  role: MapFeatureRole;
  corners: Array<{ x: number; z: number }>;
  center: { x: number; z: number };
  width: number;
  depth: number;
}

/** Classify kit families, not zone IDs. New placements inherit their kind's presentation. */
export function mapFeatureRole(prop: PropSpawn): MapFeatureRole {
  const kind = prop.kind;
  if (prop.visible === false || /collision|^terrain$/.test(kind)) return 'hidden';
  if (/lantern|streetlight|chain|railing|embankment|barrel|crate|bench|cart|tapestry|chandelier|(?:^|_)rack(?:_|$)|washing|laundry|brazier|banner|war_standard|bed|table|noticeboard|waymarker|relief|awning|planter|supplies/.test(kind)) return 'detail';
  if (/^path_|^map_ground_|paving|deck|bridge|dock|stairs|landing|platform|plaza/.test(kind)) return 'ground';
  if (/wall|fence|portcullis|gate/.test(kind)) return 'wall';
  if (/house|hut|building|hall|citadel$|castle$|keep|tower|bastion|palace|temple|forge|inn$|bank|chapel|market|warehouse|workshop|room|shop/.test(kind)) return 'building';
  if (/fountain|statue|monument|altar|obelisk|orrery/.test(kind)) return 'landmark';
  if (/tree|shrub|garden|cypress|linden|flower|rock|boulder|mountain|cliff|grass|fern|log/.test(kind)) return 'nature';
  if (prop.interaction?.type === 'house_portal') return 'building';
  if (prop.colliders?.some(box => Math.max(box.width, box.depth) >= 8)) return 'building';
  if (prop.walkableSurfaces?.length) return 'ground';
  return 'detail';
}

export function mapFeature(prop: PropSpawn): MapFeature {
  const role = mapFeatureRole(prop);
  const boxes = [...(prop.colliders ?? []), ...(prop.walkableSurfaces ?? [])];
  const fallback = role === 'building' ? [12, 10] : role === 'wall' ? [12, 2] : role === 'nature' ? [5, 5] : [3, 3];
  if (!boxes.length) boxes.push({ width: prop.kind.startsWith('path_') ? 1 : fallback[0], depth: prop.kind.startsWith('path_') ? 1 : fallback[1] });
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
  for (const box of boxes) for (const x of [-box.width / 2, box.width / 2]) for (const z of [-box.depth / 2, box.depth / 2]) {
    const c = Math.cos(box.rotY ?? 0), s = Math.sin(box.rotY ?? 0);
    const lx = (box.x ?? 0) + x * c + z * s, lz = (box.z ?? 0) - x * s + z * c;
    minX = Math.min(minX, lx); maxX = Math.max(maxX, lx); minZ = Math.min(minZ, lz); maxZ = Math.max(maxZ, lz);
  }
  const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1), sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
  const c = Math.cos(prop.rotY ?? 0), s = Math.sin(prop.rotY ?? 0);
  const world = (x: number, z: number) => ({ x: prop.x + x * sx * c + z * sz * s, z: prop.z - x * sx * s + z * sz * c });
  return {
    prop, role, corners: [world(minX, minZ), world(maxX, minZ), world(maxX, maxZ), world(minX, maxZ)],
    center: world((minX + maxX) / 2, (minZ + maxZ) / 2),
    width: (maxX - minX) * Math.abs(sx), depth: (maxZ - minZ) * Math.abs(sz),
  };
}

const geometryCache = new WeakMap<ZoneDefinition, MapFeature[]>();
export function zoneMapFeatures(zone: ZoneDefinition): MapFeature[] {
  const cached = geometryCache.get(zone);
  if (cached) return cached;
  const features = zone.props.filter(prop => {
    if (!prop.kind.startsWith('path_')) return true;
    return !(zone.paths ?? []).some(path => prop.id?.startsWith(`${path.id}_`));
  }).map(mapFeature).filter(feature => feature.role !== 'hidden');
  geometryCache.set(zone, features);
  return features;
}

export function mapFeatureVisible(feature: MapFeature, pixelsPerMetre: number): boolean {
  const size = Math.max(feature.width, feature.depth) * pixelsPerMetre;
  return feature.role !== 'hidden' && (feature.role !== 'detail' || (pixelsPerMetre >= 1.5 && size >= 4));
}

export interface MapGeometryProjection {
  scale: number;
  screenScale: number;
  toCanvas: (p: { x: number; z: number }) => { x: number; y: number };
}

export function drawMapFeatures(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: MapGeometryProjection, roles: MapFeatureRole[]) {
  const palette: Record<MapFeatureRole, string> = {
    ground: '#656451', wall: '#959485', building: '#77796d', landmark: '#b4a075', nature: '#354e40', detail: '#656b60', hidden: '#000',
  };
  const terrainColors: Record<string, string> = { grass: '#354e40', dirt: '#786145', cobblestone: '#77796d', stone: '#85817a', wood: '#76512d', water: '#31585e' };
  for (const role of roles) for (const feature of zoneMapFeatures(zone)) {
    if (feature.role !== role || !mapFeatureVisible(feature, projection.scale * projection.screenScale)) continue;
    ctx.fillStyle = feature.prop.kind.startsWith('map_ground_')
      ? terrainColors[feature.prop.kind.slice('map_ground_'.length)] ?? palette[role]
      : palette[role];
    ctx.beginPath();
    if (role === 'nature') {
      const center = projection.toCanvas(feature.center);
      ctx.ellipse(center.x, center.y, feature.width * projection.scale / 2, feature.depth * projection.scale / 2, -(feature.prop.rotY ?? 0), 0, Math.PI * 2);
    } else feature.corners.forEach((corner, i) => {
      const p = projection.toCanvas(corner);
      if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    });
    ctx.closePath(); ctx.fill();
    if (role === 'building' || role === 'landmark') {
      ctx.lineWidth = 0.75 / projection.screenScale;
      ctx.strokeStyle = '#202c29'; ctx.stroke();
    }
  }
}

export function drawMapWater(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: MapGeometryProjection) {
  ctx.fillStyle = '#31585e';
  for (const canal of zone.canals ?? []) {
    const p = projection.toCanvas({ x: canal.x - canal.width / 2, z: canal.z - canal.depth / 2 });
    ctx.fillRect(p.x, p.y, canal.width * projection.scale, canal.depth * projection.scale);
  }
}
