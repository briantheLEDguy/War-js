// Stationary civic cast. Moving ambient actors retain their own locomotion rigs.
export const AEGIS_PEOPLE = [
  ['market_buyer', 'civilian_male', 'Orren Vale', 'Market shopper', -34, -118, 0],
  ['market_weaver', 'civilian_female', 'Tessa Vale', 'Weaver', -32, -117, 2.4],
  ['market_child', 'child', 'Perrin Vale', 'Tessa’s child', -31, -118, 1],
  ['yard_crafter', 'civilian_male', 'Bren Tallow', 'Candlemaker', -67, -94, 1.5],
  ['yard_neighbor', 'civilian_female', 'Mera Tallow', 'Cinderbank resident', -65, -94, -1.5],
  ['quay_worker', 'civilian_male', 'Tovin Reed', 'Quayside porter', 119, -50, 1.5],
  ['quay_resident', 'civilian_female', 'Anwen Reed', 'Quayside resident', 121, -50, -1.5],
  ['cloister_resident', 'civilian_female', 'Sella Wren', 'Vigil visitor', -44, 71, 0],
  ['cloister_child', 'child', 'Robin Wren', 'Sella’s child', -42.5, 71, 0],
  ['garden_courtier', 'courtier', 'Iven Marrow', 'Crownwatch envoy', 67, 128, 1.5],
  ['garden_attendant', 'attendant', 'Neris Penn', 'Court attendant', 69, 128, -1.5],
  ['hall_lord', 'lord', 'Lord Edren Valcrest', 'Keeper of Crownwatch', -3, 230, 0],
  ['hall_lady', 'lady', 'Lady Maelin Valcrest', 'Crownwatch councillor', 0, 230, 0],
  ['hall_courtier', 'courtier', 'Aren Vell', 'Council secretary', 5, 227, .6],
  ['hall_attendant', 'attendant', 'Corin Hale', 'Great Hall attendant', -7, 227, -.6],
];

function ground(zone, x, z) {
  const f = zone.cityElevation;
  if (!f) return 0;
  const s = f.segments, fx = Math.max(0, Math.min(s, (x / zone.size + .5) * s)), fz = Math.max(0, Math.min(s, (z / zone.size + .5) * s));
  const ix = Math.min(s - 1, Math.floor(fx)), iz = Math.min(s - 1, Math.floor(fz)), tx = fx - ix, tz = fz - iz;
  const h = (dx, dz) => f.heights[(iz + dz) * (s + 1) + ix + dx];
  return tz >= tx ? h(0,0) + tz*(h(0,1)-h(0,0)) + tx*(h(1,1)-h(0,1)) : h(0,0) + tx*(h(1,0)-h(0,0)) + tz*(h(1,1)-h(1,0));
}

export function civicPlacementClear(zone, x, z) {
  const radius = .65, y = ground(zone, x, z);
  if ((zone.canals ?? []).some(c => Math.abs(x-c.x)<c.width/2+radius && Math.abs(z-c.z)<c.depth/2+radius)) return false;
  if ((zone.zoneTriggers ?? []).some(t => Math.hypot(x-t.x,z-t.z)<(t.radius ?? 3)+2)) return false;
  return !zone.props.some(p => {
    if (p.interaction && Math.hypot(x-p.x,z-p.z)<2.2) return true;
    const sx=(p.scale??1)*(p.scaleX??1), sz=(p.scale??1)*(p.scaleZ??1), sy=(p.scale??1)*(p.scaleY??1), a=p.rotY??0;
    return (p.colliders??[]).some(c => {
      const base=ground(zone,p.x,p.z)+(p.y??0);
      if (base+(c.minY??-100)*sy>y+1.9 || base+(c.maxY??100)*sy<y+.05) return false;
      const cx=p.x+(c.x??0)*sx*Math.cos(a)-(c.z??0)*sz*Math.sin(a), cz=p.z+(c.x??0)*sx*Math.sin(a)+(c.z??0)*sz*Math.cos(a);
      const r=a+(c.rotY??0), dx=x-cx,dz=z-cz;
      return Math.abs(dx*Math.cos(r)+dz*Math.sin(r))<c.width*sx/2+radius && Math.abs(-dx*Math.sin(r)+dz*Math.cos(r))<c.depth*sz/2+radius;
    });
  });
}

export function addAegisPeople(zone) {
  if (zone.id !== 'aegis_capital') return;
  zone.npcs = zone.npcs.filter(n => !n.id.startsWith('aegis_people_'));
  for (const [id, role, name, title, ax, az, rotY] of AEGIS_PEOPLE) {
    // Search only within the named destination, never relocate to another district.
    const candidates = [{x:ax,z:az}];
    for (const radius of [1,2,3]) for (let i=0;i<16;i++) candidates.push({x:ax+radius*Math.cos(i*Math.PI/8),z:az+radius*Math.sin(i*Math.PI/8)});
    const point=candidates.find(p => civicPlacementClear(zone,p.x,p.z) && zone.npcs.every(n=>Math.hypot(n.x-p.x,n.z-p.z)>1.15));
    if (!point) throw new Error(`No clear civic placement at ${id}`);
    zone.npcs.push({id:'aegis_people_'+id,name,title,role:'ambient',characterProfileKey:'npc_aegis_people_'+role,model:'chr_aegis_people_'+role+'_lod1.glb',...point,y:0,rotY});
  }
}
