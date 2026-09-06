export function addBattleCitadel(zone) {
  const prop = (id, kind, x, z, extra = {}) => ({ id: `aegis_battle_${id}`, kind: `aegis_${kind}`, assetKey: `aegis_${kind}`, model: `prop_aegis_${kind}.glb`, lodModels: [`prop_aegis_${kind}_lod1.glb`, `prop_aegis_${kind}_lod2.glb`], x, z, rotY: 0, scale: 1, ...extra });
  const keepColliders = [
    ...[-20.5,20.5].map(x => ({ x, z: -48.3, width: 31, depth: 1.4, minY: 0, maxY: 36 })),
    { z: -48.3, width: 10, depth: 1.4, minY: 12, maxY: 36 },
    ...[-7,7].map(x => ({ x, z: -50, width: 2, depth: 3, minY: 0, maxY: 12 })),
    ...[-31,-21,-11,11,21,31].map(x => ({ x, z: -50, width: 2.4, depth: 3, minY: 0, maxY: 39 })),
    ...[-21.5,21.5].map(x => ({ x, z: 12.3, width: 29, depth: 1.4, minY: 0, maxY: 36 })),
    { z: 12.3, width: 14, depth: 1.4, minY: 5.4, maxY: 36 },
    ...[-35.3,35.3].map(x => ({ x, z: -18, width: 1.4, depth: 62, minY: 0, maxY: 36 })),
    ...[-21,21].flatMap(x => [-7.5,7.5].map(z => ({ x, z, width: .8, depth: 7, minY: 0, maxY: 5.5 }))),
    { z: -18, width: 17, depth: 20, minY: 36, maxY: 126 },
    ...[-44,44].flatMap(x => [-46,10].map(z => ({ x, z, width: 11, depth: 11, minY: 0, maxY: 44 }))),
    ...[-16,16].flatMap(x => [-42,-26,-6,6].map(z => ({ x, z, width: 1.8, depth: 1.8, minY: 0, maxY: 34 }))),
    ...[-29,29].map(x => ({ x, z: -18.5, width: .25, depth: 59, minY: 6, maxY: 7.4 })),
    { z: 9.7, width: 46, depth: .25, minY: 6, maxY: 7.4 },
  ];
  // The keep faces south. Encode local offsets in the runtime collider convention.
  zone.props.push(prop('keep', 'citadel', 0, 226, { rotY: Math.PI,
    colliders: keepColliders.map(c => ({ ...c, x: -(c.x ?? 0), z: -(c.z ?? 0) })),
    walkableSurfaces: [
      { z: 18, width: 69, depth: 59, fromY: 0, toY: 0 },
      { z: -10.7, width: 68, depth: 2, fromY: 6, toY: 6 },
      ...[-32,32].map(x => ({ x, z: 18, width: 6, depth: 60, fromY: 6, toY: 6 })),
    ] }));
  const workingGate = (id, label, x, z, width, heightScale = 1.5) => {
    const interactionId = `aegis_battle_${id}_interaction`;
    zone.props.push(prop(id, 'portcullis', x, z, { scaleX: width / 10, scaleY: heightScale,
      interaction: { id: interactionId, type: 'gate', label, maxDistance: 18, startsOpen: false },
      colliders: [{ width: 10, depth: .6, minY: 0, maxY: 8, blocksWhen: 'closed', interactionId }] }));
    return interactionId;
  };
  const keepGate = workingGate('keep_portcullis', 'Crownwatch Great Hall Gate', 0, 176.5, 10);
  for (const x of [-27,27]) zone.props.push(prop(`hall_stairs_${x}`, 'stairs', x, 225.8, { rotY: Math.PI, scaleZ: .875,
    walkableSurfaces: [{ width: 3, depth: 24, fromY: 6, toY: 0 }] }));
  for (const x of [-12,12]) zone.props.push(prop(`war_table_${x}`, 'table', x, 224,
    { scale: 1.5, colliders: [{ width: 2.8, depth: 1.6, minY: 0, maxY: 1.5 }] }));
  zone.props.push(prop('hall_altar', 'altar', -12, 234, { colliders: [{ width: 4, depth: 2, minY: 0, maxY: 3 }] }));
  for (const x of [-23,23]) for (const z of [218,232]) zone.props.push(prop(`hall_light_${x}_${z}`, 'lantern', x, z));
  for (const x of [-84,84]) for (const z of [136,210]) zone.props.push(prop(`bastion_${x}_${z}`, 'citadel_bastion', x, z, { colliders: [{ width: 12, depth: 12, minY: -.5, maxY: 43 }] }));
  for (const x of [-78,78]) zone.props.push(prop(`arcade_${x}`, 'citadel_arcade', x, 174, { colliders: Array.from({ length: 7 }, (_, i) => ({ z: -30 + i * 10, width: 4, depth: 2, minY: -.5, maxY: 18 })) }));
  for (const x of [-62,0,62]) {
    const scale = x ? .7 : 1;
    zone.props.push(prop(`gate_${x}`, 'citadel_gate', x, 132, { scale, colliders: [-12,12].map(x => ({ x, width: 6, depth: 6, minY: -.5, maxY: 26 })) }));
    workingGate(`court_portcullis_${x}`, x < 0 ? 'West Crownwatch Gate' : x > 0 ? 'East Crownwatch Gate' : 'Crownwatch Processional Gate', x, 132, 18 * scale);
  }
  const wall = (side, start, end, fixed, vertical = false) => {
    const count = Math.ceil((end - start) / 12), length = (end - start) / count;
    for (let i = 0; i < count; i++) {
      const mid = start + (i + .5) * length;
      zone.props.push(prop(`enclosure_${side}_${i}`, 'wall', vertical ? fixed : mid, vertical ? mid : fixed,
        { scaleX: length / 12, rotY: vertical ? Math.PI / 2 : 0,
          colliders: [{ width: 12, depth: 3, minY: 0, maxY: 11.9 },
            ...[-1.25,1.25].map(z => ({ z, width: 12, depth: .5, minY: 12, maxY: 15 }))],
          walkableSurfaces: [{ width: 12, depth: 2, fromY: 12, toY: 12 }] }));
    }
  };
  const gaps = [[-68.3,-55.7],[-9,9],[55.7,68.3]];
  let start = -90;
  for (const [i,[a,b]] of [...gaps,[90,90]].entries()) { wall(`front_${i}`,start,a,132); start=b; }
  wall('west',132,246,-90,true); wall('east',132,246,90,true);
  // This inner opening stays inside the connected mountain stronghold.
  wall('rear_west',-90,-9,246); wall('rear_east',9,90,246);
  zone.cityCitadel = { enclosure: { minX: -90, maxX: 90, minZ: 132, maxZ: 246 },
    entranceGateIds: [-62,0,62].map(x => `aegis_battle_court_portcullis_${x}_interaction`), keepGateId: keepGate,
    interior: { name: 'Crownwatch Great Hall', minX: -34, maxX: 34, minZ: 178, maxZ: 237, galleryHeight: 6 } };
  for (const x of [-26,26]) for (const z of [174,186]) zone.props.push(prop(`cover_${x}_${z}`, 'battle_cover', z === 186 ? Math.sign(x) * 55 : x, z, { colliders: [{ width: 5.5, depth: 2.8, minY: -.5, maxY: 4.8 }] }));
  const formation = (front, direction) => Array.from({ length: 18 }, (_, i) => ({ x: (i % 6 - 2.5) * 8, z: front + Math.floor(i / 6) * direction * 5 }));
  zone.cityBattlefield = { name: 'Crownwatch Grand Court', playersPerTeam: 18,
    bounds: { minX: -64, maxX: 64, minZ: 140, maxZ: 174 },
    staging: { south: formation(144, 1), north: formation(170, -1) },
    approaches: [{ x: -62, z: 132, width: 12 }, { x: 0, z: 132, width: 18 }, { x: 62, z: 132, width: 12 }],
  };
}
