/** Deterministic, metre-scale authoring source. Fronts face +Z after Blender export. */
import { readFileSync } from 'node:fs';
import { dressRiftspireDistricts } from './riftspire-district-dressing.mjs';
const residenceProfiles = JSON.parse(readFileSync(new URL('./riftspire-residence-profiles.json', import.meta.url), 'utf8'));
const districtVariants = [[3,4,5,6,8], [1,2,2,4,7,8], [1,3,4,5,6,8], [1,1,3,6,7,8], [1,2,2,5,7,7]];
export const RIFTSPIRE_VERSION = 'riftspire-crater-v3';
const TAU = Math.PI * 2;
const round = n => Math.round(n * 10000) / 10000;
const point = (r, a, y) => ({ x: round(r * Math.sin(a)), y, z: round(r * Math.cos(a)) });
export const RIFTSPIRE_LEVELS = [
  { id: 'rim', name: 'Ashgate Rim', y: 0, radius: 400 },
  { id: 'market', name: 'Blackvein Market', y: -50, radius: 364 },
  { id: 'transit', name: 'Hollowwall Warrens / Chainwake Commons', y: -105, radius: 324 },
  { id: 'lower', name: 'Hollowwall Warrens', y: -175, radius: 269 },
  { id: 'works', name: 'Drowned Works', y: -245, radius: 209 },
];
export const RIFTSPIRE_PORTALS = {
  rift_gate_fortress: { trigger: {x:0,z:440}, spawn:{x:0,z:421} },
  ashen_steppe: { trigger: {x:440,z:0}, spawn:{x:421,z:0} },
  cinderfen_outskirts: { trigger: {x:-440,z:0}, spawn:{x:-421,z:0} },
};
const floor = (width, depth, extra={}) => ({ width, depth, fromY: 0, toY: 0, ...extra });
const wall = (x,z,width,depth,height=15) => ({x,z,width,depth,minY:0,maxY:height});
const houseWalls = (width=13,depth=9,height=17) => [wall(-width/2,0,.65,depth,height),wall(width/2,0,.65,depth,height),wall(0,-depth/2,width,.65,height),
  wall(-(width+2.8)/4,depth/2,(width-2.8)/2,.65,height),wall((width+2.8)/4,depth/2,(width-2.8)/2,.65,height)];
const noise = (level, slot, salt=0) => {
  let n = Math.imul(level+17, 374761393) ^ Math.imul(slot+31, 668265263) ^ Math.imul(salt+7, 1274126177);
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
};

export function rebuildRiftspireCity(zone) {
  if (zone.id !== 'riftspire_capital') return zone;
  const services = zone.npcs.filter(n => !n.id.includes('life_') && n.role !== 'ambient');
  const training = zone.enemies.filter(e => e.id.includes('_training_dummy_'));
  zone.size = 1024; zone.segments = 32; zone.flatTerrain = true;
  delete zone.terrainTexture; delete zone.terrainModel; delete zone.cityElevation; delete zone.skybox;
  zone.cityLayoutVersion = RIFTSPIRE_VERSION;
  zone.props = []; zone.paths = []; zone.biomeKits = []; zone.enemies = []; zone.ambientLife = undefined;
  zone.atmosphere = { fogColor:'#343641',sunColor:'#e7d4bb',sunIntensity:2.2 };
  zone.spawnPoint = {x:0,y:0,z:421};
  zone.zoneTriggers = zone.zoneTriggers.map(t => ({...t,y:0}));
  const city = zone.craterCity = {version:RIFTSPIRE_VERSION,basinY:-300,levels:[...RIFTSPIRE_LEVELS,
    {id:'upper commons',name:'Upper Chainwake Commons',y:-130,radius:50},{id:'lower commons',name:'Lower Chainwake Commons',y:-150,radius:50}].sort((a,b)=>b.y-a.y),
    recovery:[],routes:[],lifts:[],interiors:[],formations:[],lights:[]};
  const add = (kind,id,p,extra={}) => {
    const prop = {id:`riftspire_${id}`,kind:`riftspire_${kind}`,model:`prop_riftspire_${kind}.glb`,assetKey:`riftspire_${kind}`,
      lodModels:[1,2].map(l=>`prop_riftspire_${kind}_lod${l}.glb`),...p,rotY:0,scale:1,heightMode:'absolute',colliderSpace:'model',...extra};
    zone.props.push(prop);return prop;
  };
  const route = (id,a,b,width=18,kind='bridge') => {
    const length=Math.hypot(b.x-a.x,b.z-a.z),count=Math.ceil(length/24),yaw=Math.atan2(b.x-a.x,b.z-a.z);
    for(let i=0;i<count;i++) {
      const t=(i+.5)/count;
      add(kind,`${id}_${i}`,{x:round(a.x+(b.x-a.x)*t),y:a.y,z:round(a.z+(b.z-a.z)*t)},
        {rotY:yaw,scaleZ:length/count/24,walkableSurfaces:[floor(width,24)],colliders:[wall(-width/2+.25,0,.35,24,1.5),wall(width/2-.25,0,.35,24,1.5)]});
    }
    city.routes.push({id,width,points:[a,b]});
  };
  // Each sector has five authored recesses aligned with its inward-facing homes.
  for(let i=0;i<64;i++) add(i===31?'rock_palace_left':i===32?'rock_palace_right':i%16===15?'rock_gate_left':i%16===0?'rock_gate_right':'rock_sector',`cliff_${i}`,{x:0,y:0,z:0},{rotY:(i+.5)*TAU/64+Math.PI});
  add('basin','basin',{x:0,y:0,z:0});
  const stairPlans=[];
  for(let side=0;side<4;side++) for(let li=0;li<4;li++) {
    const top=RIFTSPIRE_LEVELS[li],bottom=RIFTSPIRE_LEVELS[li+1],drop=top.y-bottom.y;
    const base=side*TAU/4+.20,sweep=2*drop/((top.radius+bottom.radius)/2);
    const quantize=(a,r)=>Math.round(a*Math.ceil(TAU*r/22)/TAU)*TAU/Math.ceil(TAU*r/22);
    stairPlans.push({side,li,top,bottom,drop,from:quantize(base,top.radius),to:quantize(base+sweep,bottom.radius)});
  }
  for(const [li,level] of RIFTSPIRE_LEVELS.entries()) {
    const count = Math.ceil(TAU*level.radius/22);
    const points=[];
    for(let i=0;i<count;i++) {
      const a=i*TAU/count,p=point(level.radius,a,level.y);points.push(p);
      const stairMouth=stairPlans.some(s=>
        (s.li===li && Math.abs(Math.atan2(Math.sin(a-s.from),Math.cos(a-s.from)))*level.radius<24)
        || (s.li+1===li && Math.abs(Math.atan2(Math.sin(a-s.to),Math.cos(a-s.to)))*level.radius<24));
      const liftCrossing=Math.abs(Math.sin(a*2))<.11,crossing=liftCrossing || stairMouth;
      if (!(li===4 && liftCrossing)) add(crossing?'deck_open':'deck',`terrace_${li}_${i}`,p,{rotY:a+Math.PI,walkableSurfaces:[floor(24,18)],
        colliders:crossing?[]:[wall(0,8.7,24,.3,1.35)]});
    }
    city.routes.push({id:`terrace_${li}`,width:18,points:[...points,points[0]]});
    for(let i=0;i<64;i++) {
      if(li===2 && (i===31 || i===32))continue;
      const a=(i+.5)*TAU/64,publicRoom=li===2 && i%8===3;
      // Correlated occupancy makes streets grow in neighborhoods, with quiet rock
      // stretches between them. Recess boundaries constrain every footprint.
      const density=[.56,.76,.66,.52,.38][li];
      const occupied=publicRoom || noise(li,Math.floor((i+li*3)/4),1)*.65+noise(li,i,2)*.35<density;
      const pair=occupied && !publicRoom && noise(li,i,3)<[.18,.34,.22,.30,.08][li];
      if(!occupied) add('rock_infill',`uncut_cliff_${li}_${i}`,point(level.radius+11,a,level.y),{rotY:a+Math.PI});
      else for(let unit=0;unit<(pair?2:1);unit++) {
        const pool=districtVariants[li];
        const variant=publicRoom?[4,2,4,2,5,4,8,3][Math.floor(i/8)]:pair?1:pool[Math.floor(noise(li,i,4)*pool.length)];
        const {width,depth,height}=residenceProfiles[variant-1];
        const scaleX=publicRoom?1:pair?.78+noise(li,i,5+unit)*.08:.86+noise(li,i,5)*.22;
        const scaleY=publicRoom?1:.86+noise(li,i,7+unit)*.22;
        const scaleZ=publicRoom?1:.87+noise(li,i,9+unit)*.18;
        const clearance=Math.max(0,9.5-(width/2+.9)*scaleX);
        const offset=pair?(unit?4.35:-4.35):(noise(li,i,11)-.5)*Math.min(2.8,clearance*2);
        const p=point(level.radius+9.8+depth*scaleZ/2,a,level.y);
        p.x=round(p.x+Math.cos(a)*offset);p.z=round(p.z-Math.sin(a)*offset);
        add(`house_${variant}`,`residence_${li}_${i}${unit?'_annex':''}`,p,{rotY:a+Math.PI,scaleX,scaleY,scaleZ,
          walkableSurfaces:[floor(width,depth),floor(width+1,2.3,{z:depth/2+1.1})],colliders:houseWalls(width,depth,height)});
      }
      if(li===0 && i%4===2)add('palace',`rim_belfry_${i}`,point(430,a,0),{rotY:a+Math.PI,scale:.35});
    }
    for(let side=0;side<4;side++) {
      const a=side*TAU/4,landing=point(200,a,level.y);
      route(`landing_${li}_${side}`,point(212,a,level.y),point(Math.max(222,level.radius),a,level.y));
      city.recovery.push(point(217,a,level.y));
      add('lift_landing',`landing_deck_${li}_${side}`,landing,{rotY:a,
        walkableSurfaces:[floor(6.75,24,{x:-8.625}),floor(6.75,24,{x:8.625}),floor(10.5,6.75,{z:-8.625}),floor(10.5,6.75,{z:8.625})],
        colliders:[-5.5,5.5].map(x=>wall(x,0,.25,10,1.4))});
      if(li===0) {
        route(`gate_approach_${side}`,point(400,a,0),point(456,a,0));
        add('palace',`rim_gate_${side}`,point(439,a,0),{rotY:a+Math.PI,scale:.48,colliders:[wall(-20,0,26,12,36),wall(20,0,26,12,36)]});
      }
    }
  }
  // The main transit court stays clear for two independent 18-person formations.
  const hubFloors=[floor(76.75,100,{x:-11.625}),floor(12.75,100,{x:43.625}),floor(10.5,44.75,{x:32,z:-27.625}),floor(10.5,44.75,{x:32,z:27.625})];
  const hubRails=[wall(-30,49,38,.4,1.35),wall(30,49,38,.4,1.35),wall(-30,-49,38,.4,1.35),wall(30,-49,38,.4,1.35),wall(-49,-30,.4,38,1.35),wall(-49,30,.4,38,1.35),wall(49,-30,.4,38,1.35),wall(49,30,.4,38,1.35)];
  add('hub','transit_hub',{x:0,y:-105,z:0},{walkableSurfaces:hubFloors,colliders:hubRails});
  for(let side=0;side<4;side++) {
    const a=side*TAU/4;
    route(`transit_arm_${side}`,point(50,a,-105),point(188,a,-105));
    add('anchor',`bridge_anchor_${side}`,point(310,a,-105),{rotY:a+Math.PI});
    const p=point(200,a,-105),prop=add('lift',`wall_lift_${side}`,p,{rotY:a,walkableSurfaces:[floor(10.5,10.5)],colliders:[wall(-4.7,0,.3,10,4),wall(4.7,0,.3,10,4)]});
    city.lifts.push({id:`wall_${side}`,name:['Ashgate Hoist','East Chain Hoist','Crown Hoist','West Chain Hoist'][side],propId:prop.id,x:p.x,z:p.z,stops:RIFTSPIRE_LEVELS.map(l=>({name:l.name,y:l.y}))});
    for(let y=-245;y<-4;y+=20) add('chain',`wall_hoist_chain_${side}_${y}`,{...p,y});
    for(const sign of [-1,1]) {
      const offset={x:Math.cos(a)*12*sign,z:-Math.sin(a)*12*sign};
      const anchor=point(396,a,0);add('anchor',`rim_tension_anchor_${side}_${sign}`,{...anchor,x:anchor.x+offset.x,z:anchor.z+offset.z},{rotY:a+Math.PI});
      const chainPoints=Array.from({length:25},(_,i)=>{const t=i/24,q=point(40+356*t,a,-107+119*t-25*Math.sin(Math.PI*t));return {...q,x:q.x+offset.x,z:q.z+offset.z};});
      for(let i=0;i<24;i++) {
        const from=chainPoints[i],to=chainPoints[i+1],dx=to.x-from.x,dy=to.y-from.y,dz=to.z-from.z;
        add('chain',`main_suspension_${side}_${sign}_${i}`,from,{scaleY:Math.hypot(dx,dy,dz)/20,rotX:side%2?0:Math.atan2(dz,dy),rotZ:side%2?-Math.atan2(dx,dy):0});
      }
    }
  }
  // Four stair spirals provide two independent clockwise/counterclockwise routes.
  for(const {side,li,top,bottom,drop,from,to} of stairPlans) {
    const steps=Math.ceil(drop/10),startRadius=top.radius-9,endRadius=bottom.radius-9;
    const ps=Array.from({length:steps+1},(_,i)=>point(startRadius+(endRadius-startRadius)*i/steps,from+(to-from)*i/steps,top.y-drop*i/steps));
    for(let i=0;i<steps;i++) {
      const a=ps[i],b=ps[i+1],length=Math.hypot(b.x-a.x,b.z-a.z),yaw=Math.atan2(b.x-a.x,b.z-a.z);
      add('stairs',`stair_${side}_${li}_${i}`,{x:(a.x+b.x)/2,y:b.y,z:(a.z+b.z)/2},{rotY:yaw,scaleZ:length/20,scaleY:(a.y-b.y)/9.75,
        walkableSurfaces:[floor(6,20,{fromY:9.75,toY:0})],colliders:[wall(-2.9,0,.15,20,11.5),wall(2.9,0,.15,20,11.5)]});
    }
    city.routes.push({id:`stairs_${side}_${li}`,width:6,points:ps});
  }
  // Suspended neighborhoods hang from the permanent bridge structure.
  for(let side=0;side<4;side++) for(let i=0;i<6;i++) {
    const a=side*TAU/4,r=70+i*22,y=i%2?-150:-130,p=point(r,a,y);
    add('deck_open',`hanging_deck_${side}_${i}`,p,{rotY:a,scaleX:.75,scaleZ:.8,walkableSurfaces:[floor(24,18)]});
    add('hut',`suspended_hut_${side}_${i}`,{...p,x:p.x+Math.cos(a)*5,z:p.z-Math.sin(a)*5},{rotY:a+Math.PI/2,walkableSurfaces:[floor(8,7)],colliders:houseWalls(8,7,9)});
    for(const sign of [-1,1]) {
      const q={x:p.x+Math.cos(a)*6*sign,z:p.z-Math.sin(a)*6*sign};
      const length=-108-y;
      for(let segment=0;segment<Math.ceil(length/20);segment++) add('chain',`suspension_${side}_${i}_${sign}_${segment}`,{...q,y:y+segment*20},{scaleY:Math.min(20,length-segment*20)/20});
    }
  }
  // Two lower communal decks connect all huts, with optional narrow cross-links.
  for(const y of [-130,-150]) {
    add('hub',`commons_${-y}`,{x:0,y,z:0},{walkableSurfaces:hubFloors,colliders:hubRails});
    for(let side=0;side<4;side++) route(`commons_arm_${-y}_${side}`,point(40,side*TAU/4,y),point(190,side*TAU/4,y),5,'rope_bridge');
  }
  const central=add('lift','central_lift',{x:32,y:-105,z:0},{walkableSurfaces:[floor(10.5,10.5)],colliders:[wall(-4.7,0,.3,10,4),wall(4.7,0,.3,10,4)]});
  city.lifts.push({id:'central',name:'Chainwake Settlement Lift',propId:central.id,x:32,z:0,stops:[{name:'Transit',y:-105},{name:'Upper Commons',y:-130},{name:'Lower Commons',y:-150}]});
  for(let y=-150;y<-106;y+=20)add('chain',`central_chain_${y}`,{x:32,y,z:0});
  // Public interiors are physical rooms at their actual entrances, not remote boxes.
  const rooms=[['tavern_ash','The Ashen Cup','table'],['tavern_chain','The Hanging Lantern','table'],['trading','Blackvein Trading Hall','rack'],['forge','Ironwake Forge','forge'],['shrine','Shrine of the Last Ember','altar'],['guild','Chainwright Guild','archive'],['home_west','Hollowwall Home','bed'],['home_east','Lanternkeeper Home','bed']];
  for(let i=0;i<rooms.length;i++) {
    const [id,name,furnishing]=rooms[i],a=(i+.5)*TAU/8,p=point(337,a,-105);
    // Use the existing recessed residential shells, with distinct furnished room addresses.
    const propId=`riftspire_residence_2_${i*8+3}`;
    const shell=zone.props.find(p=>p.id===propId),yaw=shell.rotY;
    const toWorld=(x,z)=>({x:shell.x+Math.cos(yaw)*x+Math.sin(yaw)*z,y:shell.y,z:shell.z-Math.sin(yaw)*x+Math.cos(yaw)*z});
    for(const [n,x,z] of [['main',-3,-1],['side',3,-2]]) add(furnishing,`${id}_${n}`,toWorld(x,z),{rotY:yaw,scale:.65});
    add('lantern',`${id}_light`,toWorld(3,2),{rotY:yaw});
    city.lights.push({...toWorld(0,0),y:-101,color:'#ffc582',intensity:100,distance:16});
    const profile=residenceProfiles[Number(shell.kind.slice(-1))-1];
    city.interiors.push({id,name,propId,entry:toWorld(0,profile.depth/2+1.7)});
  }
  // Northern stronghold: three connected walk-in halls in the crater wall.
  route('palace_approach',{x:0,y:-105,z:-324},{x:0,y:-105,z:-336});
  add('palace','crown_facade',{x:0,y:-105,z:-336},{colliders:[wall(-20,0,26,12,36),wall(20,0,26,12,36)]});
  for(const [i,name] of ['Admission Hall','Blackvein Vault','Riftspire Throne Room'].entries()) {
    const z=-360-i*60,prop=add('hall',`palace_room_${i}`,{x:0,y:-105,z},{walkableSurfaces:[floor(70,60)],colliders:[wall(-34.5,0,1,60,24),wall(34.5,0,1,60,24),...[-29.5,29.5].flatMap(z=>[wall(-20,z,30,1,24),wall(20,z,30,1,24)])]});
    city.interiors.push({id:`palace_${i}`,name,propId:prop.id,entry:{x:0,y:-105,z:z+29}});
    for(const x of [-30,30])for(const dz of [-22,0,22])add(i===1?'archive':'banner',`palace_detail_${i}_${x}_${dz}`,{x,y:-105,z:z+dz});
    if(i===0)for(const x of [-20,20])add('table',`admission_table_${x}`,{x,y:-105,z});
    for(const x of [-26,26])for(const dz of [-18,18])add('lantern',`palace_lamp_${i}_${x}_${dz}`,{x,y:-105,z:z+dz});
    for(const dz of [-16,16])city.lights.push({x:0,y:-96,z:z+dz,color:'#f3ba83',intensity:1900,distance:48});
  }
  add('throne','throne',{x:0,y:-105,z:-498});
  const order=['riftspire_capital_city_gate','riftspire_capital_vault','riftspire_capital_plaza'];
  zone.rvrObjectives=[{id:order[0],label:'Chainwake Bridgehead',x:0,y:-105,z:12,type:'city_gate',captureRadius:12,defaultRealm:'riftbound'},
    {id:order[1],label:'Blackvein Vault',x:0,y:-105,z:-420,type:'battle_objective',captureRadius:12,defaultRealm:'riftbound',requiresObjectiveIds:[order[0]]},
    {id:order[2],label:'Riftspire Throne',x:0,y:-105,z:-480,type:'battle_objective',captureRadius:12,defaultRealm:'riftbound',requiresObjectiveIds:order.slice(0,2)}];
  for(const [id,z] of [['bridgehead',0],['palace',-420]])city.formations.push({id,teams:[-1,1].map(sign=>Array.from({length:18},(_,i)=>({x:(i%6-2.5)*3,y:-105,z:z+sign*(15+Math.floor(i/6)*3)})))});
  const profiles=['npc_riftspire_chaos','npc_riftspire_greenskin','npc_riftspire_dark_elf'];
  zone.npcs=services.map((npc,i)=>({...npc,x:(i%4-1.5)*8,y:-105,z:30+Math.floor(i/4)*7,rotY:Math.PI,heightMode:'absolute',approvedOnly:true,characterProfileKey:profiles[i%profiles.length]}));
  zone.enemies=training.map((e,i)=>({...e,x:-30+i*9,y:-105,z:-32,heightMode:'absolute',approvedOnly:true,assetKey:'riftspire_training_dummy',model:'prop_riftspire_training_dummy.glb'}));
  zone.ambientLife={actors:[],emitters:[]};
  for(let i=0;i<40;i++) {
    // Keep patrols within a street bay, clear of the quarter-turn stair mouths.
    const level=RIFTSPIRE_LEVELS[i%5],angle=Math.floor(i/10)*TAU/4+.76+(i%10)*.055,p=point(level.radius,angle,level.y);
    zone.ambientLife.actors.push({id:`riftspire_inhabitant_${i}`,kind:i%3?'citizen':'guard',...p,
      route:[point(level.radius,angle+.018,level.y),point(level.radius,angle+.035,level.y)],
      speed:.7,pauseSeconds:4,characterProfileKey:profiles[i%3],approvedOnly:true});
  }
  zone.craftingStations=(zone.craftingStations??[]).map((s,i)=>({...s,x:20,y:-105,z:-25+i*8}));
  zone.resourceNodes=(zone.resourceNodes??[]).map((s,i)=>{
    const p={x:215,y:-245,z:(i-2)*3},visual=add('crate',`works_resource_${i}`,p,{scale:.6});
    return {...s,...p,visualPropId:visual.id};
  });
  for(const [i,s] of zone.craftingStations.entries())add(s.kind==='forge'?'forge':'table',`service_station_${i}`,{x:s.x+2,y:s.y,z:s.z},{scale:.6});
  zone.cityDistricts=[{id:'ashgate',name:'Ashgate Rim',x:0,y:0,z:400},{id:'market',name:'Blackvein Market',x:364,y:-50,z:0},{id:'warrens',name:'Hollowwall Warrens',x:-269,y:-175,z:0},{id:'commons',name:'Chainwake Commons',x:0,y:-130,z:0},{id:'works',name:'Drowned Works',x:0,y:-245,z:209},{id:'crown',name:'Riftspire Crown',x:0,y:-105,z:-376}];
  zone.explorationPlaces=[...zone.cityDistricts.map(({name,x,y,z})=>({name,x,y,z})),...city.interiors.map(r=>({name:r.name,...r.entry}))];
  dressRiftspireDistricts(zone,RIFTSPIRE_LEVELS,add);
  return zone;
}
