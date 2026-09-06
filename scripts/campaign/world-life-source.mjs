export const WORLD_LIFE_VERSION = 'settled-roads-v1';
export const WORLD_LIFE_ZONE_IDS = Object.freeze([
  'aegis_capital', 'riftspire_capital',
  'sunmeadow_march', 'brightfen_approach', 'cinderfen_outskirts', 'ashen_steppe',
]);

// Conservative ground footprints also reserve space for the procedural meshes.
export const WORLD_LIFE_FOOTPRINTS = Object.freeze({
  life_crate_stack: 1.7,
  life_barrels: 1.45,
  life_handcart: 2.5,
  life_bench: 1.7,
  life_lantern: 0.7,
  life_clothesline: 2.6,
  life_signpost: 1.1,
  life_campfire: 1.6,
  life_supply_tent: 3.1,
  life_planter: 1.1,
});

const SCENE_KITS = {
  wayfinding: [
    ['life_signpost', 0, 0], ['life_lantern', 0, -4], ['life_planter', 4, -4],
  ],
  market: [
    ['life_handcart', 0, 0], ['life_crate_stack', -4, -1],
    ['life_barrels', 4, -1], ['life_lantern', -3, 3],
    ['life_signpost', 4, 3], ['life_crate_stack', -7, 1],
  ],
  doorstep: [
    ['life_bench', 0, 0], ['life_planter', -3.5, 0],
    ['life_planter', 3.5, 0], ['life_clothesline', 0, 5],
    ['life_barrels', 5, 4], ['life_lantern', -5, 3],
  ],
  rest: [
    ['life_campfire', 0, 0], ['life_bench', -4, 1],
    ['life_bench', 4, 1], ['life_barrels', -4, -3],
    ['life_lantern', 4, -3], ['life_signpost', 7, 2],
  ],
  supplies: [
    ['life_supply_tent', 0, 0], ['life_crate_stack', -5, -1],
    ['life_barrels', 5, 0], ['life_handcart', -5, 4],
    ['life_lantern', 5, 4], ['life_crate_stack', 0, 6],
  ],
  garden: [
    ['life_bench', 0, 0], ['life_planter', -4, 0],
    ['life_planter', 4, 0], ['life_lantern', -4, 4],
    ['life_planter', 0, 4], ['life_planter', 4, 4],
  ],
};

// Anchors follow the existing street grid. Local placement may move at most 4m
// when a doorway, new quest NPC, or campaign object occupies an authored slot.
const CAPITAL_SCENES = [
  ['gate_rest_west', 'rest', -20, -119],
  ['gate_supplies_east', 'supplies', 23, -120],
  ['avenue_garden_west', 'garden', -13, -48],
  ['avenue_deliveries_east', 'market', 13, -48],
  ['market_west', 'market', -65, -22],
  ['market_east', 'market', 65, -22],
  ['washyard_west', 'doorstep', -68, -51],
  ['washyard_east', 'doorstep', 68, -51],
  ['craft_deliveries', 'supplies', -71, 14],
  ['training_rest', 'rest', 103, 16],
  ['forecourt_garden_west', 'garden', -15, 44],
  ['forecourt_garden_east', 'garden', 15, 44],
  ['barracks_supplies_west', 'supplies', -73, 57],
  ['barracks_supplies_east', 'supplies', 73, 57],
  ['upper_court_west', 'garden', -72, 104],
  ['upper_court_east', 'rest', 72, 104],
];

const ROUTE_SCENES = [
  ['camp_wayfinding', 'wayfinding', 12, -42],
  ['field_kitchen', 'rest', -16, -75],
  ['outfitter', 'supplies', 20, -74],
  ['camp_deliveries', 'market', -32, -28],
  ['field_rest', 'doorstep', 31, -25],
  ['roadside_caravan', 'supplies', 94, 16],
  ['trail_garden', 'garden', -94, -42],
  ['watch_camp', 'rest', -25, 31],
  ['gatherer_camp', 'supplies', 28, 31],
];

const SHIFT_OPTIONS = [
  [0, 0], [0, 2], [0, -2], [2, 0], [-2, 0],
  [2, 2], [-2, 2], [2, -2], [-2, -2],
  [0, 4], [0, -4], [4, 0], [-4, 0],
];

/** Decorate a fully built zone before its static hash is calculated. */
export function decorateWorldLife(zone) {
  if (!WORLD_LIFE_ZONE_IDS.includes(zone.id)) return zone;

  const prefix = `${zone.id}_life_`;
  const capital = zone.campaign.nodeRole === 'capital';
  const riftbound = zone.campaign.realm === 'riftbound';
  zone.props = zone.props.filter((prop) => !prop.id?.startsWith(prefix));
  const retainedActors = (zone.ambientLife?.actors ?? []).filter((actor) => !actor.id.startsWith(prefix));
  const retainedEmitters = (zone.ambientLife?.emitters ?? []).filter((emitter) => !emitter.id.startsWith(prefix));
  const sceneProps = [];
  const obstacles = buildObstacles(zone);
  const scenes = capital ? CAPITAL_SCENES : ROUTE_SCENES;
  const maximumProps = capital ? 76 : 38;

  // Alternating sides gives the east and west routes different stopping places.
  const mirror = !capital && zone.campaign.lane.endsWith('_east') ? -1 : 1;
  for (const [sceneId, kit, anchorX, anchorZ] of scenes) {
    for (const [index, [kind, offsetX, offsetZ]] of SCENE_KITS[kit].entries()) {
      if (sceneProps.length >= maximumProps) break;
      const x = (anchorX + offsetX) * mirror;
      const z = anchorZ + offsetZ;
      const radius = WORLD_LIFE_FOOTPRINTS[kind];
      const point = SHIFT_OPTIONS.map(([dx, dz]) => ({ x: x + dx, z: z + dz }))
        .find((candidate) => isClear(zone, candidate, radius, obstacles, true));
      if (!point) continue;
      const prop = {
        id: `${prefix}${sceneId}_${index + 1}`,
        kind,
        ...point,
        rotY: kind === 'life_bench' ? (offsetX < 0 ? Math.PI / 2 : -Math.PI / 2) : (riftbound ? 0.12 : -0.08),
        scale: 1,
      };
      const colliders = lifeColliders(kind);
      if (colliders) {
        prop.colliders = colliders.map((collider, colliderIndex) => ({
          id: `${prop.id}_solid_${colliderIndex + 1}`, ...collider,
        }));
      }
      sceneProps.push(prop);
      obstacles.circles.push({ ...point, radius: radius + 0.35 });
    }
  }
  zone.props.push(...sceneProps);

  const actors = buildActors(zone, obstacles, prefix, capital, mirror);
  const emitters = [];
  for (const prop of sceneProps.filter((entry) => entry.kind === 'life_campfire')) {
    emitters.push(
      { id: `${prop.id}_smoke`, kind: 'smoke', x: prop.x, z: prop.z, y: 0.6, count: 8, radius: 0.8 },
      { id: `${prop.id}_embers`, kind: 'embers', x: prop.x, z: prop.z, y: 0.35, count: 12, radius: 0.65 },
    );
  }
  const moteCenters = capital ? [[-73, 55], [73, 55]] : [[-84 * mirror, -44], [28 * mirror, 28]];
  for (const [index, [x, z]] of moteCenters.entries()) {
    emitters.push({ id: `${prefix}motes_${index + 1}`, kind: 'motes', x, z, y: 1.4, count: 12, radius: 5 });
  }
  zone.ambientLife = { actors: [...retainedActors, ...actors], emitters: [...retainedEmitters, ...emitters] };

  // Vegetation is expanded at load time, after static map generation. Reserve
  // the scene footprints and complete ground routes in every overlapping kit.
  const corridors = sceneProps.map((prop) => ({
    id: `${prop.id}_clearing`,
    points: [{ x: prop.x, z: prop.z }, { x: prop.x, z: prop.z }],
    radius: WORLD_LIFE_FOOTPRINTS[prop.kind] + 3,
  }));
  for (const actor of actors.filter((entry) => entry.kind !== 'bird')) {
    const points = [{ x: actor.x, z: actor.z }, ...(actor.route ?? []), { x: actor.x, z: actor.z }];
    corridors.push({ id: `${actor.id}_clearing`, points, radius: 3 });
  }
  for (const kit of zone.biomeKits ?? []) {
    kit.excludeCorridors = [
      ...(kit.excludeCorridors ?? []).filter((corridor) => !corridor.id.startsWith(prefix)),
      ...corridors.filter((corridor) => corridor.points.some((point) =>
        Math.abs(point.x - kit.x) < kit.width / 2 + corridor.radius + 12
        && Math.abs(point.z - kit.z) < kit.depth / 2 + corridor.radius + 12)),
    ];
  }
  return zone;
}

function lifeColliders(kind) {
  const minY = -0.05;
  switch (kind) {
    case 'life_crate_stack': return [{ x: 0, z: 0.1, width: 1.7, depth: 0.95, minY, maxY: 1.5 }];
    case 'life_barrels': return [{ x: 0, z: 0.3, width: 1.4, depth: 1.35, minY, maxY: 0.9 }];
    case 'life_handcart': return [
      { x: 0, z: 0, width: 1.7, depth: 1.75, minY, maxY: 1.4 },
      ...[-0.43, 0.43].map((x) => ({ x, z: 1.3, width: 0.14, depth: 1.86, minY: 0.4, maxY: 0.9 })),
    ];
    case 'life_bench': return [{ x: 0, z: 0, width: 2.05, depth: 0.65, minY, maxY: 1.15 }];
    case 'life_supply_tent': return [{ x: 0, z: 0, width: 3.05, depth: 2.9, minY, maxY: 2.3 }];
    default: return undefined;
  }
}

function buildActors(zone, obstacles, prefix, capital, mirror) {
  const cast = capital ? [
    ['gate_sentry_west', 'guard', -10, -108, 0, 10],
    ['gate_sentry_east', 'guard', 10, -108, 0, 10],
    ['arriving_traveler', 'citizen', -10, -131, 0, 8],
    ['supply_worker', 'citizen', 19, -110, 3, 0],
    ['avenue_walker', 'citizen', -10, -48, 0, 10],
    ['avenue_messenger', 'citizen', 10, -48, 0, 10],
    ['market_porter_west', 'citizen', -72, -21, 6, 0],
    ['market_porter_east', 'citizen', 72, -21, -6, 0],
    ['neighbor_west', 'citizen', -65, -51, 5, 0],
    ['neighbor_east', 'citizen', 65, -51, -5, 0],
    ['craft_worker', 'citizen', -66, 9, 5, 0],
    ['training_sentry', 'guard', 102, 23, 5, 0],
    ['courtyard_walker', 'citizen', -12, 37, 0, 8],
    ['barracks_sentry', 'guard', 70, 64, 7, 0],
    ['garden_keeper', 'citizen', -72, 101, 5, 0],
    ['upper_court_neighbor', 'citizen', 72, 101, 5, 0],
  ] : [
    ['kitchen_worker', 'citizen', -12, -80, 5, 0],
    ['supply_worker', 'citizen', 27, -69, 4, 0],
    ['camp_guard', 'guard', -12, -22, 0, 8],
    ['trail_patrol', 'guard', 35, -13, 10, 0],
    ['caravan_traveler', 'citizen', 92, 9, 8, 0],
    ['gatherer', 'citizen', -84, -44, 4, 0],
    ['meadow_deer_1', 'deer', -61, -83, -8, 3],
    ['meadow_deer_2', 'deer', -54, -71, -6, -3],
    ['meadow_deer_3', 'deer', 85, -58, 8, 4],
    ['camp_resting_guard', 'guard', 26, 25, 0, 5],
  ];
  const actors = [];
  for (const [index, [name, kind, x, z, dx, dz]] of cast.entries()) {
    const radius = kind === 'deer' ? 1.15 : 0.75;
    let route;
    for (const [shiftX, shiftZ] of SHIFT_OPTIONS) {
      const start = { x: x * mirror + shiftX, z: z + shiftZ };
      const end = { x: (x + dx) * mirror + shiftX, z: z + dz + shiftZ };
      if (clearSegment(zone, start, end, radius, obstacles)) {
        route = [start, end];
        break;
      }
    }
    if (!route) {
      // A newly authored building or quest NPC may invalidate a walking route;
      // retain a nearby idle worker only when their standing point is clear.
      const point = SHIFT_OPTIONS.map(([sx, sz]) => ({ x: x * mirror + sx, z: z + sz }))
        .find((candidate) => isClear(zone, candidate, radius, obstacles, false));
      if (!point) continue;
      route = [point];
    }
    const actor = {
      id: `${prefix}${name}`, kind, ...route[0],
      ...(route.length > 1 ? { route } : {}),
      speed: kind === 'guard' ? 1.25 : kind === 'deer' ? 1.1 : 0.85,
      pauseSeconds: kind === 'guard' ? 2 : 4 + index % 4,
      scale: kind === 'deer' ? 0.85 + (index % 3) * 0.08 : 0.94 + (index % 4) * 0.035,
      variant: index % 4,
    };
    actors.push(actor);
    // Keep independently authored actors from sharing an idle position.
    obstacles.circles.push({ x: actor.x, z: actor.z, radius: 1 });
  }
  for (let index = 0; index < (capital ? 3 : 2); index += 1) {
    const x = (capital ? -35 : -45) + index * 30;
    const z = capital ? -42 : -42 - index * 18;
    actors.push({
      id: `${prefix}bird_${index + 1}`, kind: 'bird', x, z,
      route: [{ x, z }, { x: x + 18, z: z + 10 }, { x: x - 5, z: z + 20 }],
      speed: 3.4 + index * 0.3, pauseSeconds: 0, scale: 0.7 + index * 0.1, variant: index,
    });
  }
  return actors;
}

function buildObstacles(zone) {
  const circles = [
    { ...zone.spawnPoint, radius: 8 },
    ...(zone.npcs ?? []).map((entry) => ({ ...entry, radius: 4 })),
    ...(zone.craftingStations ?? []).map((entry) => ({ ...entry, radius: entry.radius + 1 })),
    ...(zone.resourceNodes ?? []).map((entry) => ({ ...entry, radius: 3 })),
    ...(zone.enemies ?? []).map((entry) => ({ ...entry, radius: Math.max(4, entry.aggroRange ?? 0) })),
    ...(zone.rvrObjectives ?? []).map((entry) => ({ ...entry, radius: entry.captureRadius + 1 })),
    ...(zone.zoneTriggers ?? []).map((entry) => ({ ...entry, radius: entry.radius + 5 })),
  ];
  const rectangles = [];
  for (const prop of zone.props) {
    const scaleX = (prop.scale ?? 1) * (prop.scaleX ?? 1);
    const scaleZ = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
    const angle = prop.rotY ?? 0;
    for (const collider of prop.colliders ?? []) {
      const x = (collider.x ?? 0) * scaleX;
      const z = (collider.z ?? 0) * scaleZ;
      rectangles.push({
        x: prop.x + x * Math.cos(angle) - z * Math.sin(angle),
        z: prop.z + x * Math.sin(angle) + z * Math.cos(angle),
        width: collider.width * scaleX,
        depth: collider.depth * scaleZ,
        angle: angle + (collider.rotY ?? 0),
      });
    }
    if (!prop.colliders?.length && prop.visible !== false) {
      const baseRadius = /vendor_stall|fountain|statue|brazier|obelisk|tree|rock/.test(prop.kind) ? 3 : 1.5;
      circles.push({ x: prop.x, z: prop.z, radius: baseRadius * Math.max(scaleX, scaleZ) });
    }
  }
  return { circles, rectangles };
}

function isClear(zone, point, radius, obstacles, keepRoadsClear) {
  if (Math.abs(point.x) + radius > zone.size / 2 - 8 || Math.abs(point.z) + radius > zone.size / 2 - 8) return false;
  if (obstacles.circles.some((circle) => Math.hypot(point.x - circle.x, point.z - circle.z) < radius + circle.radius)) return false;
  if (obstacles.rectangles.some((rectangle) => {
    const dx = point.x - rectangle.x;
    const dz = point.z - rectangle.z;
    const x = dx * Math.cos(rectangle.angle) + dz * Math.sin(rectangle.angle);
    const z = -dx * Math.sin(rectangle.angle) + dz * Math.cos(rectangle.angle);
    return Math.hypot(Math.max(0, Math.abs(x) - rectangle.width / 2), Math.max(0, Math.abs(z) - rectangle.depth / 2)) < radius + 1;
  })) return false;
  if (keepRoadsClear && (zone.paths ?? []).some((path) => path.points.slice(1).some((end, index) =>
    distanceToSegment(point, path.points[index], end) < path.width / 2 + radius + 0.75))) return false;
  return true;
}

function clearSegment(zone, start, end, radius, obstacles) {
  const samples = Math.max(1, Math.ceil(Math.hypot(end.x - start.x, end.z - start.z) * 2));
  for (let index = 0; index <= samples; index += 1) {
    const t = index / samples;
    if (!isClear(zone, { x: start.x + (end.x - start.x) * t, z: start.z + (end.z - start.z) * t }, radius + 0.25, obstacles, false)) return false;
  }
  return true;
}

function distanceToSegment(point, start, end) {
  const dx = end.x - start.x;
  const dz = end.z - start.z;
  const lengthSq = dx * dx + dz * dz;
  const t = lengthSq === 0 ? 0 : Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.z - start.z) * dz) / lengthSq));
  return Math.hypot(point.x - start.x - dx * t, point.z - start.z - dz * t);
}
