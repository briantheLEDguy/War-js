import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment } from '../../shared/worldSpatial';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';

export interface BattlefieldPlacement {
  id: string; sourceLabel: string; x: number; z: number; yawDegrees: number; scale: number;
  width: number; depth: number; height: number; grounding: 'root' | 'embed';
  scaleAxes: [number, number, number]; tiltDegrees: [number, number];
}
export interface BattlefieldScene {
  id: string; purpose: string; placements: BattlefieldPlacement[]; rejectedSockets: number;
  visualApproved: false; combatCoverAccepted: false;
}
interface SceneSpec { id: string; purpose: string; x: number; z: number; reach: number; density: number }
function scatter(seed: number, index: number): number {
  let n = Math.imul(seed ^ index, 1597334677); n ^= n >>> 15;
  return (Math.imul(n, 3812015801) >>> 0) / 4294967296;
}
/** Landscape neighborhoods retain open battle bowls and corridors, using admitted parent models. */
export function battlefieldScenes(zone: ZoneDefinition): BattlefieldScene[] {
  if (!zone.spatial || !zone.orvrLayout?.terrain.naturalField) throw new Error('Scene cells need battlefield terrain');
  const sun = zone.id === 'sunmeadow_march';
  if (!sun && zone.id !== 'cinderfen_outskirts') throw new Error('Scene cells admit the first pair only');
  const height = createOrvrGridHeightSampler(zone.orvrLayout.terrain, zone.size, zone.segments, zone.spatial);
  const specifications: SceneSpec[] = sun ? [
    { id: 'western_scarp_foot', purpose: 'Broken limestone and oak screen the exposed scarp foot; both ends and the graded rotation remain open', x: -155, z: 15, reach: 38, density: 38 },
    { id: 'eastern_reverse_slope', purpose: 'Loose field-edge cover gives the eastern push a contestable reverse slope without blocking the advance', x: 110, z: -40, reach: 40, density: 34 },
    { id: 'barrow_finger', purpose: 'Broken oak cover above the western field; both counterclimbs remain open', x: -220, z: 85, reach: 72, density: 76 },
    { id: 'field_back_slope', purpose: 'Limestone and hawthorn on the lee side, with open meadow toward the advance', x: 15, z: -105, reach: 70, density: 62 },
    { id: 'north_barrow_wood', purpose: 'Branching upland grove follows drainage around a clear woodland pocket', x: -280, z: 290, reach: 100, density: 92 },
    { id: 'oak_watershed', purpose: 'Oak groups and limestone feet break the middle watershed silhouette', x: 95, z: 315, reach: 103, density: 86 },
    { id: 'eastern_downs', purpose: 'Scattered trees on folded downs frame the eastern counterpush', x: 405, z: 235, reach: 100, density: 78 },
    { id: 'southern_field_edge', purpose: 'Low scrub and exposed limestone follow the southern field rise', x: -20, z: -320, reach: 100, density: 66 },
    { id: 'eastern_farm_edge', purpose: 'Small oak copses and broken field-edge cover leave broad grazing lanes', x: 345, z: -320, reach: 105, density: 74 },
    { id: 'village_woodland_edge', purpose: 'Oak and thorn clusters transition working outskirts to the barrow woods', x: -470, z: 155, reach: 74, density: 58 },
  ] : [
    { id: 'western_fault_foot', purpose: 'Fractured basalt frames the fault face, with open approaches around both ends', x: -170, z: -95, reach: 40, density: 40 },
    { id: 'east_counter_shelf', purpose: 'Low basalt and sedge frame a counterpush between advance and outer flank', x: 150, z: -140, reach: 42, density: 36 },
    { id: 'fractured_shelf', purpose: 'Bedded basalt beside the basin advance; the climb and open bowl remain clear', x: -215, z: -85, reach: 76, density: 74 },
    { id: 'dyke_edge', purpose: 'Reeds collect in lower pockets beside exposed rock, leaving the peat crossing open', x: 10, z: -210, reach: 74, density: 72 },
    { id: 'west_vent_shoulder', purpose: 'Broken basalt talus grades down from the western shelf', x: -355, z: 150, reach: 80, density: 66 },
    { id: 'inner_basin_shelf', purpose: 'Layered outcrops and reed pockets make the interior shelf legible', x: 65, z: 290, reach: 105, density: 90 },
    { id: 'east_basalt_shoulder', purpose: 'Broad fractured slabs mark the eastern skyline above the counterclimb', x: 335, z: 255, reach: 105, density: 84 },
    { id: 'southern_peat_margin', purpose: 'Sparse peat vegetation and low rocks frame a dry cross-country lane', x: -150, z: -430, reach: 90, density: 70 },
    { id: 'eastern_mineral_margin', purpose: 'Low mineral outcrops and rust reeds transition basin to settlement', x: 235, z: -405, reach: 80, density: 64 },
    { id: 'basin_reed_pockets', purpose: 'Reed islands surround small open marsh pockets behind the lower flank', x: -365, z: -360, reach: 70, density: 58 },
  ];
  const occupied: BattlefieldPlacement[] = [];
  return specifications.map((spec, cellIndex) => {
    const seed = (sun ? 4751 : 7193) + cellIndex * 821;
    const scene: BattlefieldScene = { id: zone.id + '_cell_' + spec.id, purpose: spec.purpose, placements: [], rejectedSockets: 0, visualApproved: false, combatCoverAccepted: false };
    for (let i = 0; i < spec.density; i++) {
      // Unequal clumps with interior gaps avoid rings, rows and uniformly random woodland.
      const clump = i % 3, centreAngle = clump * 2.094 + scatter(seed, 900) * 2;
      const distance = Math.sqrt(scatter(seed, i * 9)) * spec.reach * .64;
      const angle = scatter(seed, i * 9 + 1) * Math.PI * 2;
      const x = spec.x + Math.cos(centreAngle) * spec.reach * .38 + Math.cos(angle) * distance;
      const z = spec.z + Math.sin(centreAngle) * spec.reach * .32 + Math.sin(angle) * distance * .78;
      const large = i % 5 === 0, tree = sun && i % 5 < 3;
      const rock = sun ? !tree && i % 2 === 1 : large || i % 4 === 1;
      const scale = sun ? (tree ? .78 + scatter(seed, i * 9 + 2) * .65 : .7 + scatter(seed, i * 9 + 2) * 1.15)
        : (rock ? 1.1 + scatter(seed, i * 9 + 2) * 2.2 : .7 + scatter(seed, i * 9 + 2) * .65);
      const scaleAxes: [number, number, number] = rock ? [scale * (1.1 + scatter(seed, i * 9 + 3) * .5), scale, scale * (.65 + scatter(seed, i * 9 + 4) * .35)] : [scale, scale, scale];
      const sourceLabel = sun ? (tree ? 'advance_hedgerow_0' : rock ? 'barrow_ridge_8' : 'advance_hedgerow_8') : (rock ? 'basalt_shelf_1' : i % 2 ? 'peat_dyke_0' : 'peat_dyke_16');
      const dimensions = sun ? (tree ? [8, 7, 14] : rock ? [7, 5, 3] : [6, 2, 3]) : (rock ? [6, 5, 3] : [5, 4, 4]);
      const p: BattlefieldPlacement = { id: scene.id + '_' + i, sourceLabel: zone.id + '_' + sourceLabel, x, z, scale, scaleAxes,
        yawDegrees: scatter(seed, i * 9 + 5) * 360,
        tiltDegrees: rock ? [(scatter(seed, i * 9 + 6) - .5) * 14, (scatter(seed, i * 9 + 7) - .5) * 12] : [0, 0],
        width: dimensions[0] * scaleAxes[0], depth: dimensions[1] * scaleAxes[1], height: dimensions[2] * scaleAxes[2],
        grounding: rock ? 'embed' : 'root' };
      const radius = Math.hypot(p.width, p.depth) / 2;
      const clear = containsSpatialPoint(zone.spatial!, p, radius + 3)
        && zone.orvrLayout!.terrain.clearCorridors.every(c => c.points.slice(1).every((b, j) => distanceToSpatialSegment(p, c.points[j], b) > radius + Math.max(12, c.radius)))
        && zone.paths!.every(path => path.points.slice(1).every((b, j) => distanceToSpatialSegment(p, path.points[j], b) > radius + path.width / 2 + 3))
        && !zone.orvrLayout!.terrain.flattenAreas.some(a => (a.preserveFooting || a.id.endsWith('_scarp_overlook')) && Math.hypot(a.x-x,a.z-z) < radius+a.radius+8)
        && ![...(zone.npcs ?? []), ...zone.enemies, ...(zone.resourceNodes ?? []), ...(zone.craftingStations ?? []), ...(zone.zoneTriggers ?? [])].some(a => Math.hypot(a.x-x,a.z-z) < radius+12)
        && !zone.orvrLayout!.keeps.some(k => Math.hypot(k.x - x, k.z - z) < radius + 64)
        && !zone.orvrLayout!.battlefieldObjectives.some(k => Math.hypot(k.x - x, k.z - z) < radius + 42)
        && !zone.orvrLayout!.stagingCamps.some(k => Math.hypot(k.x - x, k.z - z) < radius + 40)
        && !occupied.some(p2 => Math.hypot(p2.x - x, p2.z - z) < radius + Math.hypot(p2.width, p2.depth) / 2 + 2);
      const dx = (height(x + 2, z) - height(x - 2, z)) / 4, dz = (height(x, z + 2) - height(x, z - 2)) / 4;
      if (!clear || Math.hypot(dx, dz) > (p.grounding === 'root' ? .48 : 1.1)) { scene.rejectedSockets++; continue; }
      occupied.push(p); scene.placements.push(p);
    }
    return scene;
  });
}
