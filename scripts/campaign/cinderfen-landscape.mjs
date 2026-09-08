/** Cinderfen's peat basins and basalt shoulders preserve the connected campaign roads. */
import { naturalRoadCurve } from './sunmeadow-road-network.mjs';
export const CINDERFEN_TERRAIN_RELEASE = false;

function villagePaths(zone) {
  const prefix = `${zone.id}_village_`;
  const loop = naturalRoadCurve([[435,-245],[417,-249],[406,-266],[410,-284],[447,-291],
    [469,-281],[472,-258],[467,-235],[444,-221],[422,-224],[416,-235],[435,-245]], 2);
  const paths = [{ id: prefix + 'lane', width: 3.6, style: 'dirt_trail', autoConnect: false, points: loop }];
  for (const [name,x,z] of [['west_home',397.5,-275],['north_home',419,-218.5],['east_home',474.5,-230],
    ['south_home',480.5,-281],['workshop',477,-255]]) {
    const start = [...loop].sort((a,b) => Math.hypot(a.x-x,a.z-z)-Math.hypot(b.x-x,b.z-z))[0];
    paths.push({ id: prefix + name, width: 2.2, style: 'dirt_trail', autoConnect: false,
      points: naturalRoadCurve([[start.x,start.z],[x,z]], 1) });
  }
  paths.push({ id: prefix + 'apothecary', width: 2.4, style: 'dirt_trail', autoConnect: false,
    points: naturalRoadCurve([[435,-245],[437,-257],[436,-268.25]], 1) });
  zone.paths = zone.paths.filter(path => !path.id?.startsWith(prefix)).concat(paths);
  const terrain = zone.orvrLayout.terrain;
  terrain.clearCorridors = terrain.clearCorridors.filter(path => !path.id.startsWith(prefix)).concat(paths.map(path => ({
    id: path.id, points: structuredClone(path.points), radius: path.width / 2 + 1, height: 0, feather: 8,
  })));
}

export function composeCinderfenLandscape(zone, released = CINDERFEN_TERRAIN_RELEASE) {
  if (zone.id !== 'cinderfen_outskirts' || !zone.orvrLayout) return zone;
  const terrain = zone.orvrLayout.terrain;
  terrain.sourceVersion = 'cinderfen-peat-basin-v3';
  villagePaths(zone);
  terrain.landforms = [
    { id: 'north_basalt_watershed', kind: 'ridge', x: -180, z: 488, radiusX: 305, radiusZ: 98, height: 23 },
    { id: 'western_cinder_shoulder', kind: 'ridge', x: -535, z: -265, radiusX: 75, radiusZ: 245, height: 29 },
    { id: 'eastern_steam_ridge', kind: 'ridge', x: 525, z: 285, radiusX: 83, radiusZ: 245, height: 25 },
    { id: 'southern_slag_rise', kind: 'ridge', x: 150, z: -510, radiusX: 270, radiusZ: 95, height: 19 },
    { id: 'western_peat_basin', kind: 'basin', x: -205, z: 235, radiusX: 160, radiusZ: 140, height: -2.4 },
    { id: 'eastern_peat_basin', kind: 'basin', x: 195, z: 205, radiusX: 150, radiusZ: 120, height: -2.0 },
    { id: 'southern_mineral_basin', kind: 'basin', x: 45, z: -365, radiusX: 260, radiusZ: 60, height: -1.8 },
    { id: 'west_fen_northern_inlet', kind: 'basin', x: -270, z: 340, radiusX: 62, radiusZ: 115, height: -1.8 },
    { id: 'west_fen_southern_inlet', kind: 'basin', x: -255, z: 125, radiusX: 75, radiusZ: 84, height: -1.2 },
    { id: 'west_fen_reed_headland', kind: 'terrace', x: -302, z: 250, radiusX: 66, radiusZ: 55, height: 3.5 },
    { id: 'west_fen_peat_islet', kind: 'terrace', x: -179, z: 279, radiusX: 37, radiusZ: 28, height: 3.4 },
    { id: 'west_fen_eastern_tongue', kind: 'basin', x: -89, z: 206, radiusX: 66, radiusZ: 48, height: -1.2 },
    { id: 'east_fen_north_inlet', kind: 'basin', x: 169, z: 295, radiusX: 76, radiusZ: 78, height: -1.5 },
    { id: 'east_fen_south_inlet', kind: 'basin', x: 241, z: 109, radiusX: 78, radiusZ: 73, height: -1.4 },
    { id: 'east_fen_basalt_headland', kind: 'terrace', x: 289, z: 225, radiusX: 71, radiusZ: 57, height: 2.8 },
    { id: 'east_fen_peat_islet', kind: 'terrace', x: 170, z: 196, radiusX: 32, radiusZ: 41, height: 3.2 },
    { id: 'mineral_fen_southern_pocket', kind: 'basin', x: 104, z: -406, radiusX: 95, radiusZ: 61, height: -1.7 },
    { id: 'mineral_fen_northern_pocket', kind: 'basin', x: -67, z: -332, radiusX: 91, radiusZ: 48, height: -1.1 },
    { id: 'mineral_fen_cinder_spit', kind: 'terrace', x: 21, z: -394, radiusX: 56, radiusZ: 42, height: 2.8 },
    { id: 'west_scout_bank', kind: 'terrace', x: -200, z: -230, radiusX: 125, radiusZ: 120, height: 5.5 },
    { id: 'north_east_scout_bank', kind: 'terrace', x: 235, z: 380, radiusX: 140, radiusZ: 85, height: 8 },
  ];
  // Broad shoulders make the zero-height causeways emerge gradually from the fen.
  for (const corridor of terrain.clearCorridors) corridor.feather = 24;
  const village = terrain.flattenAreas.find(area => area.id.endsWith('_settlement'));
  if (village) village.radius = 83;
  const pads = [[-184,48],[184,48],[0,104],[533,-189]].map(([x,z], index) => ({
    id: `${zone.id}_supply_pad_${index}`, x, z, radius: 7, height: 0, feather: 8,
  }));
  const ids = new Set(pads.map(pad => pad.id));
  terrain.flattenAreas = terrain.flattenAreas.filter(area => !ids.has(area.id)).concat(pads);
  for (const chunk of terrain.chunks) {
    chunk.status = released ? 'approved' : 'planned';
    chunk.lodDistances = [0, 390, 630];
  }
  return zone;
}
