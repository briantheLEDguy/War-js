const point = (x, z) => ({ x: Math.round(x * 1000) / 1000, z: Math.round(z * 1000) / 1000 });
const lengthOf = points => points.slice(1).reduce((sum, p, i) => sum + Math.hypot(p.x - points[i].x, p.z - points[i].z), 0);

/** Sample authored, gently curved road alignments at wagon-scale spacing. */
export function naturalRoadCurve(controls, spacing = 4) {
  const result = [];
  for (let segment = 0; segment < controls.length - 1; segment += 1) {
    const a = controls[Math.max(0, segment - 1)], b = controls[segment];
    const c = controls[segment + 1], d = controls[Math.min(controls.length - 1, segment + 2)];
    const steps = Math.max(2, Math.ceil(Math.hypot(c[0] - b[0], c[1] - b[1]) / spacing));
    for (let sample = 0; sample < steps; sample += 1) {
      const t = sample / steps, t2 = t * t, t3 = t2 * t;
      const at = axis => (2 * t3 - 3 * t2 + 1) * b[axis] + (t3 - 2 * t2 + t) * (c[axis] - a[axis]) * .42
        + (-2 * t3 + 3 * t2) * c[axis] + (t3 - t2) * (d[axis] - b[axis]) * .42;
      result.push(point(at(0), at(1)));
    }
  }
  result.push(point(...controls.at(-1)));
  return result;
}

/** One connected road hierarchy; six supply itineraries reuse its physical roads. */
export function composeSunmeadowRoads(zone) {
  if (zone.id !== 'sunmeadow_march' || !zone.orvrLayout) return zone;
  const paths = [], edges = new Map();
  const road = (name, width, controls, role = 'road') => {
    const points = naturalRoadCurve(controls);
    const path = { id: `${zone.id}_${name}`, style: 'dirt_trail', width, points, autoConnect: false };
    paths.push(path); edges.set(name, points); return path;
  };
  road('march_road_south', 12, [[0,-260],[-12,-206],[16,-133],[20,-65],[0,0]]);
  road('march_road_north', 12, [[0,0],[-16,62],[-25,146],[-9,210],[0,260]]);
  road('aegis_keep_road', 12, [[0,0],[-75,-6],[-148,-38],[-223,-68],[-290,-80],[-350,-78]]);
  road('riftbound_keep_road', 12, [[0,0],[75,12],[136,-28],[215,-71],[282,-83],[350,-78]]);
  road('aegis_keep_approach', 5, [[-350,-78],[-350,-48],[-350,0]]);
  road('riftbound_keep_approach', 5, [[350,-78],[350,-48],[350,0]]);
  road('aegis_support_link', 8, [[-350,-78],[-375,-83],[-395,-92]]);
  road('riftbound_support_link', 8, [[350,-78],[374,-80],[395,-92]]);
  road('settlement_road', 8, [[-395,-92],[-417,-142],[-425,-190],[-435,-245]]);
  road('aegis_staging_road', 7, [[-395,-92],[-432,-62],[-450,5],[-477,52],[-505,80]]);
  road('riftbound_staging_road', 7, [[395,-92],[432,-64],[451,3],[477,55],[505,80]]);
  road('capital_road', 8, [[-435,-245],[-435,-300],[-473,-345],[-530,-370],[-570,-380]]);
  road('greybrook_road', 9, [[0,260],[25,320],[75,360],[132,420],[150,490],[120,570]]);
  road('wardens_hollow_trail', 4, [[-505,80],[-520,125],[-538,165],[-570,220]], 'trail');
  // A narrow farm track permits a southern flank without duplicating the supply highway.
  road('southern_farm_track', 3.5, [[0,-260],[-70,-300],[-174,-296],[-274,-250],[-333,-203],[-395,-92]], 'trail');

  const exits = {
    aegis_capital: { x: -570, z: -380 }, greybrook_crossing: { x: 120, z: 570 }, wardens_hollow: { x: -570, z: 220 },
  };
  for (const trigger of zone.zoneTriggers ?? []) {
    const target = exits[trigger.targetZoneId]; if (!target) continue;
    Object.assign(trigger, target);
    const marker = zone.props.find(p => p.id === `${zone.id}_portal_${trigger.targetZoneId}`);
    if (marker) Object.assign(marker, target);
  }
  // The forager watches the approach from its verge instead of standing in its lane.
  const forager = zone.npcs?.find(npc => npc.id === `${zone.id}_forager`);
  if (forager) forager.x = -446;
  for (const route of zone.orvrLayout.caravanRoutes) {
    const prefix = route.objectiveId.endsWith('_west_objective') ? edges.get('march_road_south')
      : route.objectiveId.endsWith('_east_objective') ? [...edges.get('march_road_north')].reverse() : [point(0,0)];
    route.points = [...prefix, ...edges.get(`${route.realm}_keep_road`).slice(1)];
    route.lengthMetres = Math.round(lengthOf(route.points) * 100) / 100;
  }
  zone.paths = paths;
  zone.orvrLayout.terrain.clearCorridors = paths.map(path => ({
    id: path.id, points: structuredClone(path.points), radius: path.width / 2 + 3, height: 0, feather: 28,
  }));
  return zone;
}
