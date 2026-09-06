// Bake a deterministic elevation field into the map; runtime code only samples it.
export function buildAegisMountainside(zone) {
  // Retain one-metre samples when the playable mountain footprint expands.
  const segments = zone.size, half = zone.size / 2;
  const smooth = t => { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); };
  const profile = [[-half, 0], [40, 0], [62, 11], [76, 11], [112, 35], [123, 42], [half, 42]];
  const base = (x, z) => {
    const upper = profile.findIndex(p => p[0] >= z);
    if (upper <= 0) return 0;
    const a = profile[upper - 1], b = profile[upper];
    let h = a[1] + (b[1] - a[1]) * (z - a[0]) / (b[0] - a[0]);
    return h;
  };
  const pads = zone.props.filter(p => /^aegis_(house_|rowhouse_|lean_to|citadel|chapel|civic_hall|tavern_|shop|apothecary)/.test(p.kind) && p.colliders?.length).map(p => {
    const c = p.colliders[0], publicBuilding = ['chapel', 'civic_hall', 'tavern_1', 'tavern_2', 'shop', 'apothecary'].some(k => p.kind === `aegis_${k}`);
    return { x: p.x, z: p.z, width: c.width + 1, depth: c.depth + 1, door: publicBuilding ? 11 : 0, y: base(p.x, p.z + (publicBuilding ? 8.5 : 0)) };
  });
  const roadGrade = (x, z) => base(x, z);
  const roads = zone.paths.flatMap(path => path.points.slice(1).map((b, i) => {
    const a = path.points[i], dx = b.x - a.x, dz = b.z - a.z;
    const entrance = pads.find(p => p.door && path.id.endsWith('_entrance') && a.x === p.x);
    return { a, b, dx, dz, length2: dx * dx + dz * dz, width: path.width,
      level: (t, x, z) => entrance ? entrance.y : roadGrade(x, z) };
  }));
  const height = (x, z) => {
    let h = base(x, z), total = 0, weighted = 0;
    for (const p of pads) {
      const dx = Math.max(0, Math.abs(x - p.x) - p.width / 2);
      const dz = Math.max(0, p.z - p.depth / 2 - z, z - p.z - Math.max(p.depth / 2, p.door));
      const w = 1 - smooth(Math.hypot(dx, dz) / 4);
      total += w; weighted += p.y * w;
    }
    if (total) h = h * (1 - Math.min(1, total)) + weighted / total * Math.min(1, total);
    // A level military terrace preserves the two connected wall-stair flights.
    const side = smooth((Math.abs(x) - 130) / 7);
    const band = smooth((z - 63) / 15) * (1 - smooth((z - 136) / 10));
    h += (32 - h) * side * band;
    // Grade road beds independently from nearby building pads: no sudden bumps
    // where a level foundation meets a climbing street.
    let nearest = Infinity, roadHeight = h, roadWidth = 0;
    for (const road of roads) {
      const t = Math.max(0, Math.min(1, ((x - road.a.x) * road.dx + (z - road.a.z) * road.dz) / (road.length2 || 1)));
      const distance = Math.hypot(x - road.a.x - road.dx * t, z - road.a.z - road.dz * t);
      if (distance < nearest - .001) { nearest = distance; roadHeight = road.level(t, x, z); roadWidth = road.width; }
    }
    const roadBlend = 1 - smooth((nearest - roadWidth / 2 - 1) / 3);
    h += (roadHeight - h) * roadBlend;
    return h;
  };
  zone.cityElevation = { segments, detailX: [-180, 180], detailZ: [24, 150], heights: [] };
  for (let iz = 0; iz <= segments; iz++) for (let ix = 0; ix <= segments; ix++)
    zone.cityElevation.heights.push(Math.round(height(-half + zone.size * ix / segments, -half + zone.size * iz / segments) * 1000) / 1000);
  // Wall foundations extend below the lowest adjacent grade so stepped pieces seal the perimeter.
  for (const p of zone.props.filter(p => /^aegis_(wall|wall_entry|tower)$/.test(p.kind))) {
    p.colliders[0].minY = -18;
    if (p.z < 40) continue;
    zone.props.push({ id: `${p.id}_foundation`, kind: 'aegis_embankment', assetKey: 'aegis_embankment', model: 'prop_aegis_embankment.glb', lodModels: ['prop_aegis_embankment_lod1.glb', 'prop_aegis_embankment_lod2.glb'], x: p.x, z: p.z, rotY: p.rotY, scale: 1, scaleX: p.kind === 'aegis_tower' ? 1.2 : (p.scaleX ?? 1) * 1.5, scaleY: 6, scaleZ: 2.6 });
  }
  zone.props.push({ id: 'aegis_mountain_massif', kind: 'aegis_mountain_massif', assetKey: 'aegis_mountain_massif', model: 'prop_aegis_mountain_massif.glb', lodModels: ['prop_aegis_mountain_massif_lod1.glb', 'prop_aegis_mountain_massif_lod2.glb'], x: 0, z: 250, scale: 1, rotY: 0 });
}
