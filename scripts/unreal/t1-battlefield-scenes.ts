import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment } from '../../shared/worldSpatial';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';

export interface BattlefieldPlacement {
  id: string; sourceLabel: string; x: number; z: number; yawDegrees: number; scale: number;
  width: number; depth: number; height: number; grounding: 'root' | 'embed';
}
export interface BattlefieldScene {
  id: string; purpose: string; placements: BattlefieldPlacement[]; rejectedSockets: number;
  visualApproved: false; combatCoverAccepted: false;
}
/** Small camera-review cells, built only from models already admitted in the retained parent. */
export function battlefieldScenes(zone: ZoneDefinition): BattlefieldScene[] {
  if (!zone.spatial || !zone.orvrLayout?.terrain.naturalField) throw new Error('Scene cells need battlefield terrain');
  const sun = zone.id === 'sunmeadow_march';
  if (!sun && zone.id !== 'cinderfen_outskirts') throw new Error('Scene cells admit the first pair only');
  const height = createOrvrGridHeightSampler(zone.orvrLayout.terrain, zone.size, zone.segments, zone.spatial);
  const specifications = sun ? [
    { id: 'barrow_finger', purpose: 'Broken grove screens the climb; meadow and both counterapproaches remain open', x: -220, z: 85 },
    { id: 'field_back_slope', purpose: 'Low limestone and scrub mark a lee side for a counterpush', x: 15, z: -105 },
  ] : [
    { id: 'fractured_shelf', purpose: 'Embedded basalt breaks the smooth shelf silhouette beside the open basin advance', x: -215, z: -85 },
    { id: 'dyke_edge', purpose: 'Rock and reed clusters frame the peat crossing without sealing it', x: 10, z: -210 },
  ];
  const occupied: BattlefieldPlacement[] = [];
  return specifications.map(spec => {
    const scene: BattlefieldScene = { id: zone.id + '_cell_' + spec.id, purpose: spec.purpose, placements: [], rejectedSockets: 0, visualApproved: false, combatCoverAccepted: false };
    for (let i = 0; i < 52; i++) {
      const angle = i * 2.3999632297, distance = 11 + Math.sqrt(i / 52) * 65;
      const x = spec.x + Math.cos(angle) * distance, z = spec.z + Math.sin(angle) * distance * .8;
      const large = i % 4 === 0, tree = sun && i % 3 !== 0;
      const scale = sun ? (tree ? .85 + i % 5 * .13 : .8 + i % 4 * .3) : (large ? 2.7 + i % 3 * .3 : .85 + i % 4 * .32);
      const sourceLabel = sun ? (tree ? 'advance_hedgerow_0' : i % 2 ? 'barrow_ridge_8' : 'advance_hedgerow_8') : (large || i % 3 === 0 ? 'basalt_shelf_1' : 'peat_dyke_0');
      const dimensions = sun ? (tree ? [8, 7, 14] : i % 2 ? [7, 5, 3] : [6, 2, 3]) : (large || i % 3 === 0 ? [6, 5, 3] : [5, 4, 4]);
      const p: BattlefieldPlacement = { id: scene.id + '_' + i, sourceLabel: zone.id + '_' + sourceLabel, x, z, scale,
        yawDegrees: angle * 180 / Math.PI, width: dimensions[0] * scale, depth: dimensions[1] * scale, height: dimensions[2] * scale,
        grounding: tree || !large && !sun && i % 3 !== 0 ? 'root' : 'embed' };
      const radius = Math.hypot(p.width, p.depth) / 2;
      const clear = containsSpatialPoint(zone.spatial!, p, radius + 3)
        && zone.orvrLayout!.terrain.clearCorridors.every(c => c.points.slice(1).every((b, j) => distanceToSpatialSegment(p, c.points[j], b) > radius + 12))
        && !zone.orvrLayout!.keeps.some(k => Math.hypot(k.x - x, k.z - z) < radius + 64)
        && !zone.orvrLayout!.battlefieldObjectives.some(k => Math.hypot(k.x - x, k.z - z) < radius + 34)
        && !zone.orvrLayout!.stagingCamps.some(k => Math.hypot(k.x - x, k.z - z) < radius + 40)
        && !occupied.some(p2 => Math.hypot(p2.x - x, p2.z - z) < radius + Math.hypot(p2.width, p2.depth) / 2 + 2);
      const dx = (height(x + 2, z) - height(x - 2, z)) / 4, dz = (height(x, z + 2) - height(x, z - 2)) / 4;
      if (!clear || Math.hypot(dx, dz) > (p.grounding === 'root' ? .5 : .85)) { scene.rejectedSockets++; continue; }
      occupied.push(p); scene.placements.push(p);
    }
    return scene;
  });
}
