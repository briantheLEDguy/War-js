export const CITADEL_DECORATIONS = {
  throne: [10,8,10], oath_statue: [4,4,8], war_table: [6,4,2], arms_rack: [5,2,3.5],
  provision_rack: [5,2,3], bunk: [3,5,3], hearth: [6,3,6], feast_table: [7,3,1.7],
  archive: [5,1.5,5], counting_desk: [4,2.5,2], treasury: [5,4,3.5], reliquary: [3,3,5],
  chandelier: [8,8,3], tapestry: [5,.4,8],
};

/** Furnish according to service routes and room purpose, retaining wide siege lanes. */
export function furnishAegisCitadel(zone) {
  const props = zone.props;
  const add = (id, kind, x, z, extra = {}) => {
    const [width,depth,height] = CITADEL_DECORATIONS[kind];
    const p = { id: `aegis_interior_${id}`, kind: `aegis_citadel_${kind}`, assetKey: `aegis_citadel_${kind}`,
      model: `prop_aegis_citadel_${kind}.glb`, lodModels: [1,2].map(lod => `prop_aegis_citadel_${kind}_lod${lod}.glb`),
      x, z, rotY: 0, scale: 1, colliderSpace: 'model',
      ...(!['chandelier','tapestry','throne'].includes(kind) ? {
        colliders: [{ width: width - .15, depth: depth - .15, minY: 0, maxY: height }],
      } : {}), ...extra };
    props.push(p);
    return p;
  };
  const rooms = [];
  const room = (id, name, purpose, x, z, eastEntry) => {
    const angle = eastEntry ? Math.PI/2 : -Math.PI/2;
    const front = eastEntry ? 6 : -6;
    const colliders = [
      { z:-6, width:12, depth:.3 },
      ...[-6,6].map(x => ({ x, width:.3, depth:12 })),
      ...[-3.7,3.7].map(x => ({ x, z:6, width:4.6, depth:.3 })),
    ];
    // Model-space collision keeps the doorway aligned when a GM rotates this room.
    props.push({ id: `aegis_interior_${id}_room`, kind: 'aegis_room', assetKey: 'aegis_room', model: 'prop_aegis_room.glb',
      lodModels: ['prop_aegis_room_lod1.glb','prop_aegis_room_lod2.glb'], x,z,y:.02,rotY:angle,scale:1,colliderSpace:'model',
      colliders: colliders.map(c => ({ ...c,minY:0,maxY:5 })),
      walkableSurfaces: [{ width:12,depth:12,fromY:0,toY:0 }],
    });
    rooms.push({ id, name, purpose, bounds:{minX:x-6,maxX:x+6,minZ:z-6,maxZ:z+6},
      entry:{x:x+front,z}, floorY:42.02 });
    add(`${id}_lamp`, 'chandelier', x,z,{scale:.45,y:3.47});
  };

  // Guard quarters and the cookhouse sit near deliveries, away from the royal rooms.
  room('barracks','Watch Barracks','Off-duty guards, weapon storage and personal lockers.',-49,287,true);
  room('mess','Garrison Cookhouse','A hearth and communal mess table next to the watch quarters.',-49,304,true);
  room('stores','Quartermaster Stores','Rations and equipment unloaded before entering the secure palace.',49,287,false);
  room('counting','Treasury Counting Office','Ledgers and seals checked before goods enter the vault.',49,304,false);
  // Remove temporary military furnishings replaced by the dedicated interior kit.
  const replaced = new Set(['aegis_battle_war_table_-12','aegis_battle_war_table_12',
    'aegis_mountain_supplies_-49_286','aegis_mountain_supplies_49_286']);
  props.splice(0,props.length,...props.filter(p => !replaced.has(p.id)));
  for (const z of [284,290]) add(`barracks_bunk_${z}`,'bunk',-52,z,{y:.02});
  add('barracks_weapons','arms_rack',-46,282.8,{y:.02});
  add('mess_hearth','hearth',-51,308.2,{y:.02,scale:.7,rotY:Math.PI});
  add('mess_table','feast_table',-49,301.8,{y:.02});
  for (const z of [284,290]) add(`stores_rack_${z}`,'provision_rack',52,z,{y:.02,rotY:-Math.PI/2});
  add('counting_desk','counting_desk',49,307,{y:.02,rotY:Math.PI});
  add('counting_archive','archive',53.7,303,{y:.02,rotY:-Math.PI/2,scale:.86});

  // Admission hall: watch officers to the west, clerks and petitions to the east.
  add('admission_war_table','war_table',-9,230,{rotY:Math.PI});
  add('admission_desk','counting_desk',9,230,{rotY:Math.PI});
  add('admission_archive','archive',10,235,{rotY:Math.PI,scale:.9});
  for (const x of [-8,8]) add(`entry_sentinel_${x}`,'oath_statue',x,180.5,{scale:.7,rotY:Math.PI});
  for (const x of [-10,10]) add(`admission_chandelier_${x}`,'chandelier',x,226,{y:11,scale:1});
  for (const x of [-30,30]) add(`gallery_tapestry_${x}`,'tapestry',x,237.3,{y:11,rotY:Math.PI});
  rooms.push({id:'admission',name:'Citadel Admission Hall',purpose:'Guard officers and clerks screen visitors before the mountain passage.',
    bounds:{minX:-34,maxX:34,minZ:178,maxZ:237},entry:{x:0,z:176.5},floorY:42});

  // The broad courtyard remains the muster ground; decorative cover stays outside its staging rows.
  for (const x of [-39,39]) for (const z of [158,194]) add(`court_statue_${x}_${z}`,'oath_statue',x,z,{rotY:Math.PI});
  for (const x of [-71,71]) for (const z of [156,186]) add(`court_arms_${x}_${z}`,'arms_rack',x,z,{rotY:x<0?Math.PI/2:-Math.PI/2});
  for (const x of [-22,22]) add(`keep_facade_tapestry_${x}`,'tapestry',x,176.65,{y:16,rotY:Math.PI});

  // A ceremonial approach has legible cover and a clear capture ring before the dais.
  for (const x of [-26,26]) for (const z of [334,354]) add(`throne_sentinel_${x}_${z}`,'oath_statue',x,z,{rotY:Math.PI});
  for (const x of [-55,55]) for (const z of [332,346,366]) add(`royal_archive_${x}_${z}`,'archive',x,z,{rotY:x<0?Math.PI/2:-Math.PI/2});
  for (const x of [-14,14]) add(`royal_relic_${x}`,'reliquary',x,368,{rotY:Math.PI});
  const throne=add('sovereign_throne','throne',0,365,{rotY:Math.PI,
    colliders:[{z:-1.6,width:5,depth:3.5,minY:.9,maxY:10},
      ...[-3.3,3.3].map(x=>({x,z:-2.6,width:.6,depth:.6,minY:.9,maxY:10}))],
    walkableSurfaces:[{z:2.5,width:10,depth:3,fromY:.9,toY:0}, {z:-1.5,width:10,depth:5,fromY:.9,toY:.9}],
  });
  for (const x of [-44,-22,0,22,44]) add(`royal_tapestry_${x}`,'tapestry',x,372.15,{y:7,rotY:Math.PI});
  for (const x of [-24,24]) for (const z of [340,362]) add(`royal_chandelier_${x}_${z}`,'chandelier',x,z,{y:29});
  add('garrison_chandelier','chandelier',0,299,{y:29});

  // Treasury aisles put valuables against secure walls and leave the center available for battle.
  for (const x of [100,128]) for (const z of [320,344,368]) add(`vault_hoard_${x}_${z}`,'treasury',x,z,{rotY:x<114?Math.PI/2:-Math.PI/2});
  for (const x of [100,128]) add(`vault_reliquary_${x}`,'reliquary',x,332,{rotY:x<114?Math.PI/2:-Math.PI/2});
  for (const x of [108,120]) add(`vault_ledger_${x}`,'archive',x,293,{rotY:0});
  add('vault_inspection_desk','counting_desk',114,369,{rotY:Math.PI});
  for (const z of [311,332,353]) add(`vault_chandelier_${z}`,'chandelier',114,z,{y:17});
  for (const z of [319,345]) add(`vault_wall_tapestry_${z}`,'tapestry',136.8,z,{y:6,rotY:-Math.PI/2});

  const objectiveIds=['aegis_capital_courtyard','aegis_capital_vault','aegis_capital_throne_room'];
  zone.rvrObjectives=[
    {id:objectiveIds[0],type:'battle_objective',label:'1 · Crownwatch Courtyard',x:0,z:158,captureRadius:12,defaultRealm:'aegis'},
    {id:objectiveIds[1],type:'battle_objective',label:'2 · Crownwatch Vault',x:114,z:332,captureRadius:10,defaultRealm:'aegis',requiresObjectiveIds:[objectiveIds[0]]},
    {id:objectiveIds[2],type:'battle_objective',label:'3 · Crownwatch Throne Room',x:0,z:350,captureRadius:10,defaultRealm:'aegis',requiresObjectiveIds:objectiveIds.slice(0,2)},
  ];
  for (const [i,o] of zone.rvrObjectives.entries()) {
    // A standard is visible at the edge of each ring, leaving its center unobstructed.
    props.push({id:`${o.id}_standard`,kind:'banner_post',x:o.x+o.captureRadius+(i===1?1:2),z:o.z-(i===1?6:0),rotY:0,scale:1.1,
      colliders:[{width:.5,depth:.5,minY:0,maxY:4}]});
    rooms.push({id:['courtyard','vault','throne_room'][i],name:o.label.slice(4),
      purpose:['Muster, inspection and first siege objective.','Secured treasury, reliquaries and second siege objective.','Royal audience and final siege objective.'][i],
      bounds:i===0?zone.cityBattlefield.bounds:i===1?{minX:91,maxX:137,minZ:291,maxZ:373}:zone.cityCitadel.mountainExtension.commandChamber,
      entry:i===0?{x:0,z:132}:i===1?{x:86,z:314}:{x:0,z:322},floorY:42});
  }
  const vaultStaging=front=>Array.from({length:18},(_,i)=>({x:109+(i%3)*5,z:front+(Math.floor(i/3))*5*(front<332?1:-1)}));
  zone.cityCitadel.siege={objectiveOrder:objectiveIds,rooms,thronePropId:throne.id,
    vaultStaging:{south:vaultStaging(301),north:vaultStaging(363)},
    decorationKinds:Object.keys(CITADEL_DECORATIONS).map(k=>`aegis_citadel_${k}`),
    decorationCount:props.filter(p=>p.id.startsWith('aegis_interior_')&&p.kind.startsWith('aegis_citadel_')).length};
}
