/** Second-pair source studies. Native buildout and every acceptance gate remain separate. */
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { validateTerrainField, type TerrainField, type FieldPoint } from '../../shared/terrainField';
import { validateT1 } from './t1-layouts';

const points=(rows:number[][]):FieldPoint[]=>rows.map(([x,z,width,height])=>({x,z,width,height}));
export function secondPairField(id:string):TerrainField {
  if(id==='brightfen_approach') return {
    version:1,baseHeight:-3,seed:39173,
    weathering:{warpMetres:17,warpScale:88,detailScale:39,detailAmplitude:2.6,terraceHeight:5,terraceStrength:.18},
    rolls:[{scale:146,amplitude:.8},{scale:54,amplitude:.35}],
    ridges:[
      {id:'west_limestone_islands',profile:'shelf',points:points([[-820,-190,140,15],[-650,-155,140,18],[-490,-85,110,14],[-375,20,80,12]])},
      {id:'central_reed_islands',profile:'shelf',points:points([[-260,-110,90,12],[-145,0,110,15],[-40,100,110,20],[100,130,100,17],[200,40,80,11]])},
      {id:'east_watch_islands',profile:'shelf',points:points([[260,-60,120,16],[430,-110,130,18],[570,-30,110,13],[715,80,110,19]])},
      {id:'north_island_chain',profile:'rounded',points:points([[-410,205,76,20],[-225,260,83,25],[-30,280,95,29],[160,255,75,23],[365,205,90,24]])},
      {id:'south_reed_islands',profile:'rounded',points:points([[-380,-285,72,16],[-200,-240,76,12],[40,-245,78,13],[270,-290,85,17],[455,-265,68,20]])},
      {id:'outer_limestone_bluffs',profile:'shelf',points:points([[-780,280,80,53],[-650,345,85,46]])},
      {id:'east_limestone_bluff',profile:'shelf',points:points([[745,320,75,49],[815,230,70,42]])},
      {id:'mireglass_limestone',profile:'shelf',points:points([[490,230,94,21],[580,285,82,32],[700,305,95,25]])},
    ],
    channels:[
      {id:'west_reflective_channel',points:points([[-520,-340,34,7],[-425,-180,30,8],[-345,30,26,7],[-270,380,44,8]])},
      {id:'east_reed_channel',points:points([[190,-380,32,8],[195,-160,30,8],[215,10,26,7],[255,175,30,8],[280,390,42,7]])},
    ],
  };
  if(id==='ashen_steppe') return {
    version:1,baseHeight:13,seed:50149,
    weathering:{warpMetres:29,warpScale:105,detailScale:47,detailAmplitude:7,terraceHeight:9,terraceStrength:.74},
    rolls:[{scale:190,amplitude:2},{scale:73,amplitude:1.2},{scale:29,amplitude:.35}],
    ridges:[
      {id:'north_sandstone_plateau',profile:'shelf',points:points([[-1040,420,170,109],[-740,350,140,90],[-405,385,155,124],[-100,355,140,109],[225,425,170,139],[560,360,150,106],[1000,430,175,120]])},
      {id:'south_sandstone_plateau',profile:'shelf',points:points([[-1050,-475,160,96],[-680,-395,145,118],[-355,-455,150,101],[-30,-395,145,116],[360,-465,170,126],[690,-410,145,98],[1050,-450,160,123]])},
      {id:'western_wash_buttress',profile:'rounded',points:points([[-565,320,88,72],[-495,170,72,43],[-420,40,74,24]])},
      {id:'middle_wash_buttress',profile:'shelf',points:points([[40,365,84,82],[15,230,75,54],[-45,100,65,28]])},
      {id:'eastern_wash_buttress',profile:'rounded',points:points([[420,-390,84,78],[350,-250,76,43],[270,-130,70,25]])},
    ],
    channels:[
      {id:'bending_dry_wash',points:points([[-1000,-190,75,10],[-650,-160,88,12],[-350,-110,85,11],[-110,-20,85,10],[105,80,90,11],[390,-15,85,10],[690,-90,92,12],[1000,-155,105,10]])},
      {id:'western_side_gully',points:points([[-670,410,33,24],[-620,235,35,22],[-550,95,43,15],[-420,-65,63,8]])},
      {id:'eastern_side_gully',points:points([[520,-460,33,26],[485,-290,38,22],[420,-135,48,17],[350,-25,62,8]])},
      {id:'ashfang_recess',points:points([[-730,340,29,21],[-690,230,33,19],[-590,130,48,12]])},
    ],
  };
  throw new Error('Second-pair terrain requires Brightfen or Ashen');
}

export function secondPairLandscape(original:ZoneDefinition):ZoneDefinition {
  if(!original.spatial||!original.orvrLayout||!original.paths) throw new Error('Second-pair study requires retained regional topology');
  const zone=structuredClone(original),terrain=zone.orvrLayout!.terrain,b=zone.spatial!.bounds,field=secondPairField(zone.id);
  if(zone.id==='brightfen_approach'){
    for(const ridge of field.ridges) for(const p of ridge.points)p.width*=.7;
    field.channels.push(
      {id:'western_island_divide',points:points([[-100,-410,35,20],[-65,-130,34,20],[-60,60,32,20],[-105,390,38,20]])},
      {id:'eastern_island_divide',points:points([[105,-410,35,20],[85,-130,34,20],[75,70,32,20],[125,390,38,20]])},
    );
  }
  validateTerrainField(field);
  const old=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
  terrain.naturalField=field;terrain.landforms=[];terrain.sourceVersion='t1-second-pair-source-v3';
  zone.spatial!.terrainGrid={segmentsX:Math.min(512,Math.ceil((b.maxX-b.minX)/4)),segmentsZ:Math.min(512,Math.ceil((b.maxZ-b.minZ)/4))};
  zone.orvrLayout!.spatial=zone.spatial;
  for(const area of terrain.flattenAreas){
    area.preserveFooting=area.id==='village'||area.id.includes('_village_');
    area.feather=zone.id==='brightfen_approach'?Math.max(area.feather,area.preserveFooting?100:24):Math.max(area.feather,area.preserveFooting?100:65);
  }
  terrain.clearCorridors=zone.paths!.map(p=>({id:p.id,points:p.points.map(p=>({...p})),radius:p.width/2+7,height:0,feather:zone.id==='brightfen_approach'?16:76}));
  const height=createOrvrGridHeightSampler(terrain,zone.size,zone.segments,zone.spatial);
  for(const prop of zone.props??[]) if(prop.heightMode==='absolute')prop.y=(prop.y??0)+height(prop.x,prop.z)-old(prop.x,prop.z);
  zone.spawnPoint!.y=height(zone.spawnPoint!.x,zone.spawnPoint!.z);
  for(const t of zone.zoneTriggers??[]){t.y=height(t.x,t.z);t.arrivalPoint!.y=height(t.arrivalPoint!.x,t.arrivalPoint!.z);}
  validateT1(zone);return zone;
}
