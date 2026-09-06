import { WORLD_LIFE_FOOTPRINTS } from './world-life-source.mjs';

// Original civic kit. Positions remain map data; gameplay entrances keep their IDs.
export const CIVIC_KINDS = ['streetlight', 'wall_lantern', 'sign_lantern', 'sign_lock',
  'sign_apothecary', 'sign_exchange', 'relief', 'bench', 'orrery', 'waymarker'];

function model(kind) {
  return { kind: `aegis_civic_${kind}`, assetKey: `aegis_civic_${kind}`,
    model: `prop_aegis_civic_${kind}.glb`,
    lodModels: [1, 2].map(level => `prop_aegis_civic_${kind}_lod${level}.glb`) };
}

export function distanceToCivicSegment(p, a, b) {
  const dx = b.x - a.x, dz = b.z - a.z;
  const t = Math.max(0, Math.min(1, ((p.x-a.x)*dx+(p.z-a.z)*dz)/(dx*dx+dz*dz || 1)));
  return Math.hypot(p.x-a.x-t*dx, p.z-a.z-t*dz);
}

// Match CityElevation.ts's triangle interpolation on the baked map grid.
export function civicGroundHeight(zone, x, z) {
  const field = zone.cityElevation;
  if (!field) return 0;
  const s = field.segments;
  const fx = Math.max(0, Math.min(s, (x/zone.size+.5)*s));
  const fz = Math.max(0, Math.min(s, (z/zone.size+.5)*s));
  const ix = Math.min(s-1, Math.floor(fx)), iz = Math.min(s-1, Math.floor(fz));
  const tx = fx-ix, tz = fz-iz;
  const h = (dx,dz) => field.heights[(iz+dz)*(s+1)+ix+dx];
  return tz >= tx ? h(0,0)+tz*(h(0,1)-h(0,0))+tx*(h(1,1)-h(0,1))
    : h(0,0)+tx*(h(1,0)-h(0,0))+tz*(h(1,1)-h(1,0));
}

/** Clearance includes transformed collider offsets, closed gates and invisible
 * water blockers. Radius encloses the whole horizontal decoration footprint. */
export function civicPositionClear(zone, point, radius) {
  if (Math.abs(point.x) > 135-radius || point.z < -135+radius || point.z > 127-radius) return false;
  // Thin feet and plinths need a level plot; do not float them on the ascent.
  const ground = civicGroundHeight(zone,point.x,point.z);
  for (const sx of [-1,-.5,0,.5,1]) for (const sz of [-1,-.5,0,.5,1]) {
    if (Math.abs(civicGroundHeight(zone,point.x+sx*radius,point.z+sz*radius)-ground) > .06) return false;
  }
  if (zone.canals.some(c => Math.abs(point.x-c.x) < c.width/2+radius+.4 &&
      Math.abs(point.z-c.z) < c.depth/2+radius+.4)) return false;
  const protectedPoints = [
    { ...zone.spawnPoint, radius: 8 },
    ...zone.npcs.map(p => ({ ...p, radius: 3 })),
    ...zone.craftingStations.map(p => ({ ...p, radius: 3 })),
    ...zone.resourceNodes.map(p => ({ ...p, radius: 3 })),
    ...zone.rvrObjectives.map(p => ({ ...p, radius: p.captureRadius+1 })),
    ...zone.props.filter(p => p.interaction).map(p => ({ ...p, radius: 3 })),
    ...zone.props.filter(p => WORLD_LIFE_FOOTPRINTS[p.kind]).map(p => ({
      ...p, radius:WORLD_LIFE_FOOTPRINTS[p.kind] * (p.scale ?? 1) + .3,
    })),
  ];
  if (protectedPoints.some(p => Math.hypot(p.x-point.x,p.z-point.z) < p.radius+radius)) return false;
  if (zone.paths.some(path => path.points.slice(1).some((b,i) =>
      distanceToCivicSegment(point,path.points[i],b) < path.width/2+radius+.4))) return false;
  return !zone.props.some(p => (p.colliders ?? []).some(c => {
    const angle = p.rotY ?? 0, sx = (p.scale ?? 1)*(p.scaleX ?? 1), sz = (p.scale ?? 1)*(p.scaleZ ?? 1);
    const cx = p.x+(c.x ?? 0)*sx*Math.cos(angle)-(c.z ?? 0)*sz*Math.sin(angle);
    const cz = p.z+(c.x ?? 0)*sx*Math.sin(angle)+(c.z ?? 0)*sz*Math.cos(angle);
    const a = angle+(c.rotY ?? 0), dx = point.x-cx, dz = point.z-cz;
    return Math.abs(dx*Math.cos(a)+dz*Math.sin(a)) < c.width*sx/2+radius+.25 &&
      Math.abs(-dx*Math.sin(a)+dz*Math.cos(a)) < c.depth*sz/2+radius+.25;
  }));
}

export function addAegisCivicDecorations(zone) {
  if (zone.id !== 'aegis_capital') return;
  const props = zone.props;
  const add = (id, kind, x, z, extra = {}) => {
    const p = { id: `aegis_civic_${id}`, ...model(kind), x, z, scale: 1, rotY: 0, ...extra };
    props.push(p);
    return p;
  };
  const nearestDistrict = p => [...zone.cityDistricts].sort((a,b) =>
    Math.hypot(p.x-a.x,p.z-a.z)-Math.hypot(p.x-b.x,p.z-b.z))[0];
  const districtCounts = Object.fromEntries(zone.cityDistricts.map(d => [d.id, { lights:0, artwork:0, furniture:0 }]));
  const count = (p, field) => districtCounts[nearestDistrict(p).id][field]++;

  // Upgrade the real entrance markers, preserving labels, activation distances
  // and portal identities. Signs use their existing ground-relative origin.
  const signKinds = { tavern_1:'lantern', tavern_2:'lock', apothecary:'apothecary', shop:'exchange' };
  for (const [building, sign] of Object.entries(signKinds)) {
    const portal = props.find(p => p.id === `aegis_city_${building}_door`);
    if (portal) Object.assign(portal, model(`sign_${sign}`));
  }

  // Every substantial facade receives a mounted lantern. The six house widths
  // match the authored kit; insets keep the backplate on the front wall.
  const buildings = props.filter(p => /^aegis_(house_[1-6]|tavern_[12]|apothecary|shop|chapel|civic_hall)$/.test(p.kind));
  const facades = { tavern_1:9, tavern_2:6, shop:7, apothecary:8, chapel:10, civic_hall:10 };
  for (const [i, building] of buildings.entries()) {
    const kind = building.kind.slice(6);
    const civic = kind === 'chapel' || kind === 'civic_hall';
    const width = kind.startsWith('house_') ? [8,7,9,8,6,9][Number(kind.at(-1))-1] : facades[kind];
    const angle = building.rotY ?? 0;
    const mount = (id, asset, dx, dz, y) => {
      const x=building.x+dx*Math.cos(angle)+dz*Math.sin(angle);
      const z=building.z-dx*Math.sin(angle)+dz*Math.cos(angle);
      return add(id, asset, x,z, { rotY:angle,
        y:y+civicGroundHeight(zone,building.x,building.z)-civicGroundHeight(zone,x,z) });
    };
    const lamp = mount(`facade_lantern_${i}`, 'wall_lantern', width*.32, civic ? 5.10 : 4.10, 3.0);
    count(lamp, 'lights');
    if (civic || i%7 === 0) {
      const art = mount(`facade_relief_${i}`, 'relief', -width*.27, civic ? 5.16 : 4.16, 4.45);
      count(art, 'artwork');
    }
  }

  // Lamp positions follow road shoulders. Rotate parallel to each segment so
  // the twin lantern arms read as a deliberate avenue rhythm.
  const standing = [];
  for (const path of zone.paths) for (let i=1; i<path.points.length; i++) {
    const a=path.points[i-1], b=path.points[i], dx=b.x-a.x, dz=b.z-a.z, length=Math.hypot(dx,dz);
    for (let along=5; along<length-2; along+=16) for (const side of [-1,1]) {
      const offset=path.width/2+2.0;
      const p={ x:a.x+dx*along/length+side*dz/length*offset,
        z:a.z+dz*along/length-side*dx/length*offset };
      if (!civicPositionClear(zone,p,1.5) || standing.some(q => Math.hypot(q.x-p.x,q.z-p.z)<12)) continue;
      const lamp=add(`streetlight_${standing.length}`, 'streetlight', p.x,p.z,
        { rotY:Math.atan2(-dz,dx), colliders:[{ width:.94,depth:.94,minY:0,maxY:4.6 }] });
      standing.push(lamp);
      count(lamp,'lights');
    }
  }

  // Select small open plots near the street network, balanced per district.
  // Stable coordinate ordering makes regeneration reproducible.
  const furniture = [
    {kind:'orrery', radius:1.5, width:2.1, depth:2.1, height:3.65, field:'artwork'},
    {kind:'bench', radius:1.6, width:2.85, depth:1.1, height:1.5, field:'furniture'},
    {kind:'waymarker', radius:.9, width:1.7, depth:.8, height:3.7, field:'furniture'},
    {kind:'bench', radius:1.6, width:2.85, depth:1.1, height:1.5, field:'furniture'},
  ];
  const placed=[];
  for (const district of zone.cityDistricts) {
    const candidates=[];
    for (let z=-129; z<=125; z+=3) for (let x=-132; x<=132; x+=3) {
      const p={x,z};
      if (nearestDistrict(p).id !== district.id) continue;
      const nearest=zone.paths.flatMap(path => path.points.slice(1).map((b,i) => ({
        distance:distanceToCivicSegment(p,path.points[i],b)-path.width/2,
        angle:Math.atan2(-(b.z-path.points[i].z),b.x-path.points[i].x),
      }))).sort((a,b)=>a.distance-b.distance)[0];
      if (nearest.distance>8) continue;
      candidates.push({...p,...nearest,score:Math.hypot(p.x-district.x,p.z-district.z)});
    }
    candidates.sort((a,b)=>a.score-b.score);
    for (const [i,item] of furniture.entries()) {
      const point=candidates.find(p => civicPositionClear(zone,p,item.radius) &&
        placed.every(q => Math.hypot(p.x-q.x,p.z-q.z)>5));
      if (!point) continue;
      const p=add(`${district.id}_${item.kind}_${i}`,item.kind,point.x,point.z,
        // Collider authoring rotates clockwise; Three.js mesh yaw is opposite.
        {rotY:point.angle,colliders:[{width:item.width,depth:item.depth,rotY:-2*point.angle,minY:0,maxY:item.height}]});
      placed.push(p);
      count(p,item.field);
    }
  }
  zone.cityCivicDecorations = { version:1, districtCounts,
    mountedLanterns:buildings.length, streetlights:standing.length,
    publicArt:props.filter(p => p.kind==='aegis_civic_relief' || p.kind==='aegis_civic_orrery').length,
    tradeSigns:props.filter(p => p.kind.startsWith('aegis_civic_sign_')).length,
    furniture:placed.filter(p => ['aegis_civic_bench','aegis_civic_waymarker'].includes(p.kind)).length };
}
