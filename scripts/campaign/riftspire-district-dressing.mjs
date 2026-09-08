import { readFileSync } from 'node:fs';
export const RIFTSPIRE_DISTRICT_PROPS = JSON.parse(readFileSync(new URL('./riftspire-district-props.json', import.meta.url),'utf8'));
const TAU=Math.PI*2;
const polar=(r,a,y)=>({x:r*Math.sin(a),y,z:r*Math.cos(a)});
const random=(i,s=0)=>{
  let n=Math.imul(i+191,374761393)^Math.imul(s+73,668265263);
  n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967296;
};
function rectangle(x,z,width,depth,yaw,minY,maxY) {
  return {x,z,hw:width/2,hd:depth/2,c:Math.cos(yaw),s:Math.sin(yaw),r:Math.hypot(width,depth)/2,minY,maxY};
}
function corners(r) {
  return [-1,1].flatMap(a=>[-1,1].map(b=>({x:r.x+a*r.hw*r.c+b*r.hd*r.s,z:r.z-a*r.hw*r.s+b*r.hd*r.c})));
}
function inside(p,r,pad=0) {
  const dx=p.x-r.x,dz=p.z-r.z;
  return Math.abs(dx*r.c-dz*r.s)<=r.hw+pad && Math.abs(dx*r.s+dz*r.c)<=r.hd+pad;
}
function overlaps(a,b,pad=.2) {
  if(a.maxY<b.minY || b.maxY<a.minY || Math.hypot(a.x-b.x,a.z-b.z)>a.r+b.r+pad*2)return false;
  const dx=b.x-a.x,dz=b.z-a.z;
  for(const [x,z] of [[a.c,-a.s],[a.s,a.c],[b.c,-b.s],[b.s,b.c]]) {
    const ra=a.hw*Math.abs(a.c*x-a.s*z)+a.hd*Math.abs(a.s*x+a.c*z);
    const rb=b.hw*Math.abs(b.c*x-b.s*z)+b.hd*Math.abs(b.s*x+b.c*z);
    if(Math.abs(dx*x+dz*z)>ra+rb+pad)return false;
  }
  return true;
}
function worldRect(prop,shape,floor=false) {
  const s=prop.scale??1,sx=s*(prop.scaleX??1),sz=s*(prop.scaleZ??1),sy=s*(prop.scaleY??1),yaw=prop.rotY??0;
  const x=(shape.x??0)*sx,z=(shape.z??0)*sz;
  return rectangle(prop.x+x*Math.cos(yaw)+z*Math.sin(yaw),prop.z-x*Math.sin(yaw)+z*Math.cos(yaw),shape.width*sx,shape.depth*sz,yaw+(shape.rotY??0),
    (prop.y??0)+(floor?(shape.fromY??0):(shape.minY??0))*sy,(prop.y??0)+(floor?(shape.toY??0):(shape.maxY??20))*sy);
}

/** District dressing is deterministic and subordinate to the authored circulation. */
export function dressRiftspireDistricts(zone,levels,add) {
  const city=zone.craterCity;
  const solids=zone.props.flatMap(p=>(p.colliders??[]).map(c=>worldRect(p,c)));
  // Legacy furnishings are not movement blockers, but still occupy visual space.
  const furnitureBounds={table:[5,4.3,1.9],archive:[4,1,4],rack:[4,1.5,3],altar:[4,2,2.5],forge:[4.4,3,7],crate:[2,2,2],bed:[2.2,4.2,2.3],lantern:[.8,1.1,3.5]};
  for(const p of zone.props) {
    const bounds=furnitureBounds[p.kind.replace('riftspire_','')];
    if(bounds&&!p.colliders?.length)solids.push(worldRect(p,{width:bounds[0],depth:bounds[1],minY:0,maxY:bounds[2]}));
  }
  const floors=zone.props.flatMap(p=>(p.walkableSurfaces??[]).filter(f=>(f.fromY??0)===(f.toY??0)).map(f=>worldRect(p,f,true)));
  const protectedAreas=[];
  const protectPoint=(p,r=2)=>protectedAreas.push(rectangle(p.x,p.z,r*2,r*2,0,(p.y??0)-.5,(p.y??0)+3));
  const protectSegment=(a,b,width)=>protectedAreas.push(rectangle((a.x+b.x)/2,(a.z+b.z)/2,width,Math.hypot(b.x-a.x,b.z-a.z)+.8,Math.atan2(b.x-a.x,b.z-a.z),Math.min(a.y,b.y)-1,Math.max(a.y,b.y)+3));
  for(const route of city.routes)for(let i=1;i<route.points.length;i++)protectSegment(route.points[i-1],route.points[i],route.id.startsWith('terrace_')?8.2:route.width+.8);
  for(const p of [zone.spawnPoint,...city.recovery,...zone.npcs,...zone.craftingStations])protectPoint(p,3);
  for(const formation of city.formations)for(const p of formation.teams.flat())protectPoint(p,2);
  for(const objective of zone.rvrObjectives)protectPoint(objective,(objective.captureRadius??12)+2);
  for(const lift of city.lifts)for(const stop of lift.stops)protectPoint({...lift,y:stop.y},8);
  for(const room of city.interiors)protectPoint(room.entry,3);
  for(const home of zone.props.filter(p=>p.id.includes('residence_'))) {
    const yaw=home.rotY,depth=home.walkableSurfaces[0].depth*(home.scaleZ??1)/2;
    const entry={x:home.x+Math.sin(yaw)*(depth+1.5),y:home.y,z:home.z+Math.cos(yaw)*(depth+1.5)};
    const street={x:entry.x+Math.sin(yaw)*8,y:home.y,z:entry.z+Math.cos(yaw)*8};
    protectSegment(entry,street,3.6);
  }
  for(const actor of zone.ambientLife.actors) {
    const route=[actor,...actor.route,actor];
    for(let i=1;i<route.length;i++)protectSegment(route[i-1],route[i],2.2);
  }
  const hasFloor=(p)=>floors.some(f=>Math.abs(f.minY-p.y)<.2 && inside(p,f,.02));
  function place(kind,id,p,yaw=0,scale=1) {
    const profile=RIFTSPIRE_DISTRICT_PROPS[kind];
    const rect=rectangle(p.x,p.z,profile.width*scale,profile.depth*scale,yaw,p.y,p.y+profile.height*scale);
    if(![p,...corners(rect).map(v=>({...v,y:p.y}))].every(hasFloor))return null;
    if(solids.some(r=>overlaps(rect,r)) || protectedAreas.some(r=>overlaps(rect,r)))return null;
    const prop=add(kind,`district_${id}`,p,{rotY:yaw,scale,colliders:[{x:0,z:0,width:profile.width,depth:profile.depth,minY:0,maxY:profile.height}]});
    solids.push(rect);
    if(kind==='war_brazier' || kind==='communal_hearth')city.lights.push({...p,y:p.y+(kind==='war_brazier'?3.5:1.7)*scale,color:'#ed9b4e',intensity:80,distance:14});
    return prop;
  }
  const districts=[
    {id:'ashgate',target:90,kinds:['war_standard','war_brazier','arms_rack','checkpoint','supply_cart','hanging_cage','barrel_stack','ritual_obelisk']},
    {id:'market',target:150,kinds:['market_stall','market_stall','apothecary','provision_stall','supply_cart','barrel_stack','war_brazier','war_standard']},
    {id:'transit',target:100,kinds:['arms_rack','checkpoint','chain_winch','war_brazier','supply_cart','war_standard','barrel_stack']},
    {id:'warrens',target:110,kinds:['laundry_rig','laundry_rig','communal_hearth','provision_stall','barrel_stack','apothecary','war_brazier','war_standard']},
    {id:'works',target:90,kinds:['water_pump','ore_cart','chain_winch','barrel_stack','supply_cart','war_brazier','arms_rack','war_standard']},
  ];
  const landmarkNames=['Ashgate Muster','Blackvein Night Bazaar','Chainward Inspection','Hollowwall Washcourt','Drowned Pumpworks'];
  for(const [li,district] of districts.entries()) {
    const level=levels[li];let accepted=0;
    for(let attempt=0;attempt<district.target*14 && accepted<district.target;attempt++) {
      const angle=random(attempt,li+1)*TAU,inner=random(attempt,li+20)<.36;
      const p=polar(level.radius+(inner?-6.1:6.05),angle,level.y);
      const kind=district.kinds[Math.floor(random(attempt,li+40)*district.kinds.length)];
      const scale=.74+random(attempt,li+80)*.2,yaw=angle+(inner?0:Math.PI);
      const prop=place(kind,`${district.id}_${accepted}`,p,yaw,scale);
      if(!prop)continue;
      if(accepted===0)zone.explorationPlaces.push({name:landmarkNames[li],...polar(level.radius,angle,level.y),yaw});
      accepted++;
    }
  }
  // Central courts have their own perimeter activity, away from formations and lifts.
  for(const [li,y] of [-105,-130,-150].entries()) {
    const kinds=li===0?['war_standard','checkpoint','arms_rack','ritual_obelisk','war_brazier','supply_cart']:['communal_hearth','laundry_rig','barrel_stack','chain_winch','provision_stall','war_brazier','supply_cart'];
    let accepted=0;
    for(let attempt=0;attempt<500 && accepted<32;attempt++) {
      const side=Math.floor(random(attempt,201+li)*4),along=-41+random(attempt,210+li)*82;
      const p=side%2?{x:side===1?43:-43,y,z:along}:{x:along,y,z:side===0?43:-43};
      const prop=place(kinds[attempt%kinds.length],`commons_${li}_${accepted}`,p,side*TAU/4+Math.PI,.84);
      if(prop)accepted++;
    }
  }
  for(const hut of zone.props.filter(p=>p.id.includes('hanging_deck_'))) {
    const yaw=hut.rotY??0;
    const p={x:hut.x-Math.cos(yaw)*5.5,y:hut.y,z:hut.z+Math.sin(yaw)*5.5};
    place(hut.id.endsWith('_0')?'chain_winch':'barrel_stack',`commons_hut_${hut.id}`,p,yaw,.78);
  }
  // Monumental palace side aisles frame the broad central approach and siege court.
  for(let hall=0;hall<3;hall++) {
    for(const sign of [-1,1])for(let bay=0;bay<5;bay++) {
      const kind=['oath_monument','war_standard','war_brazier','ritual_obelisk','arms_rack'][bay];
      place(kind,`crown_${hall}_${sign}_${bay}`,{x:sign*20,y:-105,z:-338-hall*60-bay*11},sign>0?-Math.PI/2:Math.PI/2,.9);
    }
    for(const x of [-12,12])place(hall===1?'hanging_cage':'war_table',`crown_council_${hall}_${x}`,{x,y:-105,z:-366-hall*60},0,.85);
  }
  // Furnished corners distinguish each public room while keeping its doorway and center open.
  const interiorKinds={tavern_ash:['barrel_stack','communal_hearth'],tavern_chain:['barrel_stack','war_standard'],trading:['market_stall','barrel_stack'],forge:['arms_rack','chain_winch'],shrine:['ritual_obelisk','war_standard'],guild:['war_table','arms_rack'],home_west:['barrel_stack','laundry_rig'],home_east:['barrel_stack','war_standard']};
  for(const room of city.interiors) {
    if(!interiorKinds[room.id])continue;
    const shell=zone.props.find(p=>p.id===room.propId),yaw=shell.rotY??0;
    for(const [i,kind] of interiorKinds[room.id].entries()) {
      const x=(i?1:-1)*(shell.walkableSurfaces[0].width/2-1.5),z=-2.3;
      place(kind,`interior_${room.id}_${i}`,{x:shell.x+Math.cos(yaw)*x+Math.sin(yaw)*z,y:shell.y,z:shell.z-Math.sin(yaw)*x+Math.cos(yaw)*z},yaw,.45);
    }
  }
  // More workers and patrols use the reviewed inhabitants and short, tested paths.
  const profiles=['npc_riftspire_chaos','npc_riftspire_greenskin','npc_riftspire_dark_elf'];
  const canWalk=(p)=>hasFloor(p)&&!solids.some(r=>p.y+1.8>=r.minY&&p.y<=r.maxY&&inside(p,r,.8));
  const addResident=(id,route,kind,profile)=>{
    if(!route.every(canWalk))return false;
    for(let i=1;i<route.length;i++)for(let t=0;t<=1;t+=.1)if(!canWalk({x:route[i-1].x+(route[i].x-route[i-1].x)*t,y:route[i].y,z:route[i-1].z+(route[i].z-route[i-1].z)*t}))return false;
    zone.ambientLife.actors.push({id:`riftspire_district_resident_${id}`,kind,...route[0],route:route.slice(1),speed:kind==='guard'?.85:.55,pauseSeconds:kind==='guard'?5:9,characterProfileKey:profile,approvedOnly:true});return true;
  };
  for(const [li,level] of levels.entries()) {
    let count=0,target=[12,24,14,18,14][li];
    for(let attempt=0;attempt<160 && count<target;attempt++) {
      const angle=random(attempt,400+li)*TAU;
      const route=[-.012,0,.016].map(da=>polar(level.radius,angle+da,level.y));
      if(addResident(`${li}_${count}`,route,li===0 || (li===2&&count%3===0)?'guard':'citizen',profiles[(count+(li===4?1:0))%3]))count++;
    }
  }
  for(const y of [-130,-150])for(const sign of [-1,1])for(let i=0;i<4;i++) {
    const x=sign*(15+i*5),z=sign*22;
    addResident(`commons_${y}_${sign}_${i}`,[{x,y,z},{x,y,z:z+3}],i===0?'guard':'citizen',profiles[i%3]);
  }
  for(const x of [-14,14])for(const z of [-350,-390,-450,-490])addResident(`crown_${x}_${z}`,[{x,y:-105,z},{x,y:-105,z:z+4}],'guard',profiles[x<0?0:2]);
  for(const [district,kind,name] of [['ashgate','checkpoint','Ashgate Muster'],['market','market_stall','Blackvein Night Bazaar'],['transit','chain_winch','Chainward Inspection'],['warrens','laundry_rig','Hollowwall Washcourt'],['works','water_pump','Drowned Pumpworks'],['commons','communal_hearth','Chainwake Cookfire'],['crown','oath_monument','Crown Oathguard']]) {
    const prop=zone.props.find(p=>p.id.startsWith(`riftspire_district_${district}_`)&&p.kind===`riftspire_${kind}`);
    if(!prop)continue;
    const yaw=prop.rotY,offset=RIFTSPIRE_DISTRICT_PROPS[kind].depth*(prop.scale??1)/2+3;
    const entry={x:prop.x+Math.sin(yaw)*offset,y:prop.y,z:prop.z+Math.cos(yaw)*offset};
    if(!canWalk(entry))continue;
    const existing=zone.explorationPlaces.find(p=>p.name===name);
    if(existing)Object.assign(existing,entry,{yaw});else zone.explorationPlaces.push({name,...entry,yaw});
  }
}
