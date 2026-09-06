/** A continuous mountain stronghold with a working vault and reserved crypt branch. */
export function addAegisMountainRedoubt(zone) {
  const prop = (id, kind, x, z, extra = {}) => ({
    id: `aegis_mountain_${id}`, kind: `aegis_${kind}`, assetKey: `aegis_${kind}`,
    model: `prop_aegis_${kind}.glb`, lodModels: [1, 2].map(lod => `prop_aegis_${kind}_lod${lod}.glb`),
    x, z, rotY: 0, scale: 1, ...extra,
  });
  const passage = (id, x, z, extra = {}) => prop(id, 'mountain_passage', x, z, {
    colliders: [
      ...[-9.5,9.5].map(x => ({ x, width: 1, depth: 24, minY: 0, maxY: 18 })),
      { width: 20, depth: 24, minY: 18, maxY: 20 },
    ],
    walkableSurfaces: [{ width: 18, depth: 24, fromY: 0, toY: 0 }], ...extra,
  });
  zone.props.push(passage('keep_connection', 0, 258, { rotY: Math.PI, scaleZ: 40 / 24 }));
  const internalGateId = 'aegis_mountain_threshold_gate_interaction';
  zone.props.push(prop('threshold_gate', 'portcullis', 0, 250, {
    scaleX: 1.8, scaleY: 1.5,
    interaction: { id: internalGateId, type: 'gate', label: 'Mountain Redoubt Gate', maxDistance: 18, startsOpen: false },
    colliders: [{ width: 10, depth: .6, minY: 0, maxY: 8, blocksWhen: 'closed', interactionId: internalGateId }],
  }));

  // Author in world-facing coordinates, then convert to the keep's south-facing convention.
  const hallColliders = [
    ...[-35,35].map(x => ({ x, z: -47.5, width: 50, depth: 1, minY: 0, maxY: 32 })),
    { z: -47.5, width: 20, depth: 1, minY: 14, maxY: 32 },
    { z: 47.2, width: 120, depth: 1.6, minY: 0, maxY: 32 },
    ...[-59.5,59.5].flatMap(x => [
      { x, z: -32.5, width: 1, depth: 31, minY: 0, maxY: 32 },
      ...(x < 0 ? [{ x, z: 20.5, width: 1, depth: 55, minY: 0, maxY: 32 }] : [
        { x, z: 9.5, width: 1, depth: 33, minY: 0, maxY: 32 },
        { x, z: 41, width: 1, depth: 14, minY: 0, maxY: 32 },
        { x, z: 30, width: 1, depth: 8, minY: 10, maxY: 32 },
      ]),
      { x, z: -12, width: 1, depth: 10, minY: 10, maxY: 32 },
      ...[-37,1,36].map(z => ({ x, z, width: 1.7, depth: 3, minY: 0, maxY: 32 })),
    ]),
    ...[-42,42].flatMap(x => [-28,8,28].map(z => ({ x, z, width: 3, depth: 3, minY: 0, maxY: 32 }))),
    ...[[-60,-40],[-28,-9],[9,28],[40,60]].map(([a,b]) => ({ x: (a+b)/2, z: -4, width: b-a, depth: 1, minY: 0, maxY: 28 })),
    { z: -4, width: 120, depth: 1, minY: 12, maxY: 28 },
    { width: 120, depth: 96, minY: 32, maxY: 34 },
  ];
  zone.props.push(prop('redoubt_hall', 'mountain_redoubt', 0, 326, {
    rotY: Math.PI,
    colliders: hallColliders.map(c => ({ ...c, x: -(c.x ?? 0), z: -(c.z ?? 0) })),
    walkableSurfaces: [{ width: 118, depth: 94, fromY: 0, toY: 0 }],
  }));

  const futureConnections = [-1].map(side => {
    const id = side < 0 ? 'crypts' : 'vault';
    const name = `Crownwatch ${side < 0 ? 'Crypts' : 'Vault'}`;
    zone.props.push(passage(`${id}_approach`, side * 72, 314, { rotY: Math.PI / 2, scaleX: .5, scaleZ: 26 / 24 }));
    const seal = prop(`${id}_seal`, 'mountain_seal', side * 86, 314, {
      rotY: -side * Math.PI / 2,
      colliders: [{ width: 14, depth: 3.2, minY: 0, maxY: 14 }],
    });
    zone.props.push(seal);
    return { id, name, status: 'sealed', portalPropId: seal.id,
      approach: { x: side * 80, y: 42, z: 314 },
      reservedBounds: { minX: side < 0 ? -138 : 90, maxX: side < 0 ? -90 : 138, minZ: 290, maxZ: 374 } };
  });

  const vaultColliders = [
    ...[-41.5,41.5].map(z => ({ z, width: 48, depth: 1, minY: 0, maxY: 20 })),
    { x: 23.5, width: 1, depth: 84, minY: 0, maxY: 20 },
    ...[[-42,-23],[-13,20],[28,42]].map(([a,b]) => ({ x: -23.5, z: (a+b)/2, width: 1, depth: b-a, minY: 0, maxY: 20 })),
    ...[[-18,10],[24,8]].map(([z,depth]) => ({ x: -23.5, z, width: 1, depth, minY: 10, maxY: 20 })),
    ...[-16,16].flatMap(x => [-28,28].map(z => ({ x, z, width: 3, depth: 3, minY: 0, maxY: 20 }))),
    { width: 48, depth: 84, minY: 20, maxY: 22 },
  ];
  zone.props.push(prop('vault_chamber', 'mountain_vault', 114, 332, { rotY: Math.PI, colliderSpace: 'model',
    colliders: vaultColliders.map(c => ({ ...c, x: -(c.x ?? 0), z: -(c.z ?? 0) })),
    walkableSurfaces: [{ width: 46, depth: 82, fromY: 0, toY: 0 }],
  }));
  const gate = (id, label, x, z, width, rotY = 0, heightScale = 1.5) => {
    const interactionId = `aegis_mountain_${id}_interaction`;
    zone.props.push(prop(id, 'portcullis', x, z, { rotY, scaleX: width / 10, scaleY: heightScale,
      interaction: { id: interactionId, type: 'gate', label, maxDistance: 18, startsOpen: false },
      colliders: [{ width: 10, depth: .6, minY: 0, maxY: 8, blocksWhen: 'closed', interactionId }],
    }));
    return interactionId;
  };
  zone.props.push(passage('vault_approach', 74.5, 314, { rotY: Math.PI / 2, scaleX: .5, scaleZ: 31 / 24 }),
    passage('vault_service_approach', 74.5, 356, { rotY: Math.PI / 2, scaleX: .4, scaleZ: 31 / 24 }));
  const vaultGateIds = [gate('vault_gate', 'Crownwatch Vault Gate', 86, 314, 9, Math.PI / 2, 1.25),
    gate('vault_service_gate', 'Vault Royal Passage Gate', 86, 356, 7.2, Math.PI / 2, 1.25)];
  const throneGateIds = [-34,0,34].map(x => gate(`throne_gate_${x}`, x ? `${x < 0 ? 'West' : 'East'} Throne Guard Gate` : 'Throne Processional Gate', x, 322, x ? 12 : 18));

  // Cover interrupts long diagonal sightlines while keeping a broad central lane and flanks.
  for (const x of [-26,26]) for (const z of [306]) zone.props.push(prop(`cover_${x}_${z}`, 'battle_cover', x, z,
    { colliders: [{ width: 5.5, depth: 2.8, minY: 0, maxY: 4.8 }] }));
  for (const x of [-49,49]) for (const z of [286]) {
    zone.props.push(prop(`supplies_${x}_${z}`, z === 342 ? 'barrel_cluster' : 'crate_stack', x, z,
      { colliders: [{ width: 3.5, depth: 3.5, minY: 0, maxY: 3.5 }] }));
  }
  for (const x of [-56,56]) for (const z of [286,302,326,342,364]) zone.props.push(prop(`hall_lantern_${x}_${z}`, 'lantern', x, z));
  for (const z of [242,264,274]) for (const x of [-7,7]) zone.props.push(prop(`passage_lantern_${x}_${z}`, 'lantern', x, z));
  for (const x of [-78,78]) zone.props.push(prop(`branch_lantern_${x}`, 'lantern', x, 310.5));

  const route = (id, name, width, coords) => ({ id, name, width, points: coords.map(([x,z]) => ({ x,z })) });
  const routes = [
    route('processional', 'Mountain Processional', 8, [[0,228],[0,258],[0,284],[0,344],[0,358]]),
    route('west_flank', 'West Redoubt Aisle', 6, [[0,286],[-34,286],[-34,342],[-34,360],[0,360]]),
    route('east_flank', 'East Redoubt Aisle', 6, [[0,286],[34,286],[34,342],[34,360],[0,360]]),
    route('crypts', 'Crypts Approach', 6, [[0,314],[-58,314],[-80,314]]),
    route('vault', 'Vault Approach', 6, [[0,314],[58,314],[114,314],[114,332]]),
    route('vault_royal', 'Vault Royal Passage', 5, [[114,332],[114,356],[50,356],[50,344],[0,344]]),
  ];
  for (const { id, width, points } of routes) zone.paths.push({ id: `aegis_mountain_${id}`, style: 'brick_walkway', autoConnect: false, width, points });
  const formation = (front, direction) => Array.from({ length: 18 }, (_, i) => ({ x: (i % 6 - 2.5) * 8, z: front + Math.floor(i / 6) * direction * 5 }));
  zone.cityCitadel.mountainExtension = {
    name: 'Crownwatch Inner Citadel', bounds: { minX: -88, maxX: 138, minZ: 238, maxZ: 374 }, internalGateId,
    battleHall: { minX: -58, maxX: 58, minZ: 280, maxZ: 348 },
    commandChamber: { minX: -58, maxX: 58, minZ: 324, maxZ: 372 },
    vault: { minX: 91, maxX: 137, minZ: 291, maxZ: 373, gateIds: vaultGateIds }, throneGateIds,
    staging: { south: formation(290, 1), north: formation(338, -1) }, routes, futureConnections,
  };
  zone.explorationPlaces.push({ name: 'Citadel Garrison Hall', x: 0, z: 300 }, { name: 'Crownwatch Throne Room', x: 0, z: 350 },
    { name: 'Crownwatch Vault', x: 114, z: 332 },
    ...futureConnections.map(c => ({ name: `${c.name} — Sealed`, x: c.approach.x, z: c.approach.z })));
}
