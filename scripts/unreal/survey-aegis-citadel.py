"""Read-only native baseline and protected terrain survey. Never saves a level.

Run in a background Unreal Python commandlet after closing editor/game writers.
Only the ignored survey receipt is written; every native package stays unchanged.
"""
import json
import hashlib
import math
import re
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, castle_identity, digest, sha, plan as blueprint_plan
from shared_city_sources import source_plan, package_file, routing
from world_actor_state import snapshot
from aegis_citadel_terrain_readback import native_terrain_policy

OUT.mkdir(parents=True,exist_ok=True)
published=source_plan(ROOT)
city=next(c for c in published['cities'] if c['id']=='aegis_capital')
build,manifest,_=routing(ROOT)
package='/Game/Capitals/Siege/AegisCapital_Siege'
all_hashes={**city['packageHashes'],**city['dependencyHashes'],package:sha(package_file(ROOT,package)),
            **{p:sha(package_file(ROOT,p)) for p in (published['campaignMap'],build['layer'])}}
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(package):raise RuntimeError('Native siege overlay is unavailable')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
field=next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarSiegeBattlefield))
def vector(p):return [p.x,p.y,p.z]
battlefield={key:[vector(p) for p in field.get_editor_property(key)]
             for key in ('objectives','optional_objectives','team_spawns','equipment_spawns')}
battlefield['definition_version']=field.get_editor_property('definition_version')
states={};castle=[];terrain_policies={}
def native_bounds(actor):
    center,extent=actor.get_actor_bounds(False)
    def box(c,e):return [[c.x-e.x,c.y-e.y,c.z-e.z],[c.x+e.x,c.y+e.y,c.z+e.z]]
    components=[]
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        if not component.static_mesh:continue
        c,e,_=unreal.SystemLibrary.get_component_bounds(component)
        components.append(dict(name=component.get_name(),bounds=box(c,e)))
    return dict(bounds=box(center,extent),componentBounds=components)
for scenery in city['sceneryLevels']:
    if not levels.load_level(scenery):raise RuntimeError('Missing published scenery: '+scenery)
    own=[a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==scenery]
    states[scenery]=[dict(actor=a.get_name(),state=snapshot(a),**native_bounds(a)) for a in own]
    for actor in own:
        if actor.get_name()!='StaticMeshActor_306' or actor.get_actor_label()!='Crownward authored mountain massif':continue
        components=[c for c in actor.get_components_by_class(unreal.StaticMeshComponent)
                    if c.get_name()=='StaticMeshComponent0' and c.static_mesh]
        if len(components)!=1:raise RuntimeError('Ambiguous original retained mountain policy source')
        mesh=components[0].static_mesh
        if mesh.get_path_name()!='/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain':
            raise RuntimeError('Original retained mountain source changed')
        terrain_policies[mesh.get_path_name()]=dict(package=scenery,actor=actor.get_name(),
            sourceMeshSha256=all_hashes[mesh.get_path_name().split('.')[0]],
            policy=native_terrain_policy(mesh,unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)))
    castle.extend(dict(package=scenery,actor=a.get_name(),identity=castle_identity(snapshot(a)),stateHash=digest(snapshot(a)))
                  for a in own if castle_identity(snapshot(a)))
if len(castle)!=2267:raise RuntimeError('Expected exact old castle identity set (2267); inspect without deleting anything')
# Capture actual campaign gameplay, including properties absent from scenery snapshots.
service_source=ROOT/'unreal/AegisWar/Source/AegisWar/Private/WarCityServices.cpp'
services=dict(re.findall(r'if \(Npc == TEXT\("([^"]+)"\)\) return TEXT\("([^"]+)"\);',service_source.read_text()))
property_sets={
    'WarCityNpc':('npc_id','display_name','city_role','character_profile'),
    'WarQuestNpc':('zone_id','npc_id','visual'),
    'WarCraftingStation':('station_kind','interaction_radius'),
    'WarResourceNode':('zone_id','node_id','visual_prop_id'),
    'WarZonePortal':('route_id','destination_route_id','destination_label','arrival_location','radius','destination_built'),
    'WarZoneAnchor':('zone_id','zone_name','zone_origin','half_size','content_levels','city_definition')}
def gameplay_row(actor):
    row=dict(actor=actor.get_name(),package=actor.get_outer().get_path_name().split('.')[0],
             point=vector(actor.get_actor_location()),state=snapshot(actor),properties={})
    for key in property_sets.get(actor.get_class().get_name(),()):
        value=actor.get_editor_property(key)
        row['properties'][key]=vector(value) if isinstance(value,unreal.Vector) else (
            value.get_path_name() if isinstance(value,unreal.Object) else str(value))
    row['service']=services.get(row['properties'].get('npc_id'))
    return row
gameplay={}
for layer in city['gameplayLevels']:
    if not levels.load_level(layer):raise RuntimeError('Missing retained gameplay layer: '+layer)
    gameplay[layer]=[gameplay_row(a) for a in actors.get_all_level_actors()
                     if a.get_outer().get_path_name().split('.')[0]==layer]
if not levels.load_level(published['campaignMap']):raise RuntimeError('Active campaign routing world is unavailable')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
campaign=[gameplay_row(a) for a in actors.get_all_level_actors()
          if a.get_class().get_name() in property_sets and (
              a.get_outer().get_path_name().split('.')[0] in city['gameplayLevels'] or
              a.get_class().get_name()=='WarZonePortal' and 'aegis_capital' in str(a.get_editor_property('route_id')) or
              a.get_class().get_name()=='WarZoneAnchor' and str(a.get_editor_property('zone_id'))=='aegis_capital')]
# Sample the actual feet height at the unchanged external approach anchors.
if not levels.load_level(package):raise RuntimeError('Cannot reload survey world')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world);unreal.WarImportLibrary.prepare_world_preview_frame(world)
spawn_surfaces=[]
for index,point in enumerate(battlefield['team_spawns'][:2]):
    samples=[]
    for x in range(-2,3):
        for y in range(-2,3):
            px,py=point[0]+x*129,point[1]+y*129
            hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(px,py,point[2]+1000),
                unreal.Vector(px,py,point[2]-1000),unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],
                unreal.DrawDebugTrace.NONE,True)
            v=hit.to_tuple() if hit else None
            if not v or not v[0] or v[7].z<math.sqrt(.5):
                raise RuntimeError('Retained spawn lacks actual walkable support')
            actor,component=v[9],v[10]
            mesh=component.static_mesh if isinstance(component,unreal.StaticMeshComponent) else None
            if not mesh:raise RuntimeError('Retained spawn support needs an exact native mesh identity')
            mesh_package=mesh.get_path_name().split('.')[0]
            actor_package=actor.get_outer().get_path_name().split('.')[0]
            if mesh_package not in all_hashes or actor_package not in all_hashes:
                raise RuntimeError('Retained spawn support is outside protected native sources')
            center=unreal.Vector(px,py,v[5].z+96-42+42/v[7].z+3)
            obstruction=unreal.SystemLibrary.capsule_trace_single_by_profile(world,center,
                center+unreal.Vector(0,0,.1),42,96,'Pawn',False,[],unreal.DrawDebugTrace.NONE,True)
            blocked=obstruction.to_tuple() if obstruction else None
            samples.append(dict(x=x,y=y,floor=vector(v[5]),normal=vector(v[7]),
                capsuleClear=not bool(blocked and blocked[0]),source=dict(meshPackage=mesh_package,
                    meshSha256=all_hashes[mesh_package],actorPackage=actor_package,
                    actorPath=actor.get_path_name(),componentPath=component.get_path_name(),
                    actorStateSha256=digest(snapshot(actor)))))
    normal=next(s['normal'] for s in samples if s['x']==0 and s['y']==0)
    spawn_surfaces.append(dict(schemaVersion=1,index=index,point=point,widthCm=600,
        groundGradient=[round(-normal[i]/normal[2],6) for i in range(2)],
        capsuleRadiusCm=42,capsuleHalfHeightCm=96,samples=samples,diagnosticOnly=True))

tie_ins={}
for key,(x,y) in {'west_approach':(12000,-5100),'east_approach':(11300,5900)}.items():
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,6000),unreal.Vector(x,y,1000),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else None
    if not values or not values[0] or values[7].z<.65:raise RuntimeError('Missing stable lower-city tie-in ground: '+key)
    tie_ins[key]=[x,y,values[5].z+2]
# Terrain/scenery beneath the proposed precinct remains after the old castle is retired.
# Ignore only exact castle identities and gameplay overlay actors, never terrain or mountains.
ignore=[a for a in actors.get_all_level_actors() if castle_identity(dict(tags=[str(t) for t in a.tags])) or
        a.get_outer().get_path_name().split('.')[0] in [package,*city['gameplayLevels']]]
probes={}
for x in range(14600,26000,800):
    for y in range(-6800,6801,800):probes[('court',x,y,4210)]=None
for x in range(26200,33400,800):
    for y in range(-4000,4001,800):probes[('hall',x,y,6010)]=None
for x in range(29000,33000,800):
    for y in (-6200,-5400,5400,6200):probes[('chamber',x,y,6010)]=None
graph=blueprint_plan(dict(battlefield=battlefield,approachTieIns=tie_ins))
from aegis_citadel_surfaces import profile_height,profile_capsule_offset,SURFACE_CAPSULE_POSE_METHOD
profiles={p['routeId']:p for p in graph['routeSurfaceProfiles']}
profile_labels={label:p for key,p in profiles.items() for label in (key,'corridor_'+key,'corridor_turn_'+key)}
def authored_feet(route,point):
    if route['id'] in profiles:point[2]=round(profile_height(profiles[route['id']],point[0]),3)
    return point
from aegis_citadel_terrain import hall_terrain_probe_points
for row in hall_terrain_probe_points():probes[(row['id'],*row['point'])]=None
for formation in graph['performanceFormations']:
    for point in formation['positions']:probes[(formation['id'],*point)]=None
for route in graph['routes']:
    for a,b in zip(route['points'],route['points'][1:]):
        steps=max(1,math.ceil(math.dist(a,b)/400))
        for i in range(steps+1):
            p=[round(a[j]+(b[j]-a[j])*i/steps,3) for j in range(3)]
            probes[(route['id'],*authored_feet(route,p))]=None
    normals=[];half=route['width']/2-42
    for a,b in zip(route['points'],route['points'][1:]):
        length=math.dist(a[:2],b[:2]);dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
        normal=[-dy,dx,0];normals.append(normal);steps=max(1,math.ceil(length/400))
        for i in range(steps+1):
            for lane in (-1,-.5,0,.5,1):
                point=[round(a[j]+(b[j]-a[j])*i/steps+normal[j]*half*lane,3) for j in range(3)]
                probes[('corridor_'+route['id'],*authored_feet(route,point))]=None
    for i,p in enumerate(route['points'][1:-1],1):
        for lane in (-1,-.5,0,.5,1):
            for t in (0,.25,.5,.75,1):
                point=[round(p[j]+((1-t)*normals[i-1][j]+t*normals[i][j])*half*lane,3) for j in range(3)]
                probes[('corridor_turn_'+route['id'],*authored_feet(route,point))]=None
terrain=[]
blockers={}
def hit_identity(values):
    actor=values[9] if values and values[0] else None
    component=values[10] if values and values[0] else None
    if actor and actor.get_path_name() not in blockers:
        blockers[actor.get_path_name()]=dict(actor=actor.get_name(),path=actor.get_path_name(),
            package=actor.get_outer().get_path_name().split('.')[0],state=snapshot(actor),**native_bounds(actor))
    return dict(actor=actor.get_path_name() if actor else None,component=component.get_path_name() if component else None)
for key in probes:
    label,x,y,z=key
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,25000),unreal.Vector(x,y,-1000),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignore,unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else None
    row=dict(id=label,point=[x,y,z],hit=bool(values and values[0]),underlyingHeightCm=None,
             floorIntrusion=False,normal=None)
    if row['hit']:
        row.update(underlyingHeightCm=values[5].z,normal=vector(values[7]),floorIntrusion=values[5].z>z+15)
    row['floorHit']=hit_identity(values)
    normal_z=max(.7,min(1,row['normal'][2])) if row['normal'] and abs(row['underlyingHeightCm']-z)<15 else 1
    offset=96+42*(1/normal_z-1)+5
    if label in profile_labels:
        legacy_center=unreal.Vector(x,y,z+offset)
        legacy_hit=unreal.SystemLibrary.capsule_trace_single(world,legacy_center,legacy_center+unreal.Vector(0,0,1),42,96,
            unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignore,unreal.DrawDebugTrace.NONE,True)
        legacy=legacy_hit.to_tuple() if legacy_hit else None
        row['rayDerivedCapsulePose']=dict(capsuleCenterOffsetCm=offset,capsuleRadiusCm=42,capsuleHalfHeightCm=96,
            capsuleBlocked=bool(legacy and legacy[0]),capsuleHit=hit_identity(legacy))
        profile=profile_labels[label]
        offset=profile_capsule_offset(profile,x)
        row['surfaceCapsulePose']=dict(method=SURFACE_CAPSULE_POSE_METHOD,routeId=profile['routeId'],
            profileSha256=digest(profile),floorMarginCm=5)
    center=unreal.Vector(x,y,z+offset)
    obstruction=unreal.SystemLibrary.capsule_trace_single(world,center,center+unreal.Vector(0,0,1),42,96,
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignore,unreal.DrawDebugTrace.NONE,True)
    blocked=obstruction.to_tuple() if obstruction else None
    row.update(capsuleRadiusCm=42,capsuleHalfHeightCm=96,capsuleCenterOffsetCm=offset,
               capsuleBlocked=bool(blocked and blocked[0]),capsuleHit=hit_identity(blocked))
    terrain.append(row)
for p,h in all_hashes.items():
    if sha(package_file(ROOT,p))!=h:raise RuntimeError('Native package changed during read-only survey: '+p)
file=OUT/'baseline.json'
report=dict(schemaVersion=2,file=file.relative_to(ROOT).as_posix(),city=city,sourceSiegeMap=package,
    packageHashes=all_hashes,battlefield=battlefield,actors=states,castleActors=castle,spawnPadSurfaces=spawn_surfaces,
    approachTieIns=tie_ins,campaignMap=published['campaignMap'],gameplayActors=gameplay,campaignConnections=campaign,
    serviceCatalog=dict(file=service_source.relative_to(ROOT).as_posix(),sha256=sha(service_source),services=services),
    terrainProbes=terrain,terrainIntrusions=[row for row in terrain if row['floorIntrusion'] or row['capsuleBlocked']],
    blockerMetadata=blockers,
    terrainSourcePolicies=terrain_policies,
    terrainSurveyGraphSignature=graph['signature'],terrainSurveyRoutesSha256=digest(graph['routes']),
    terrainSurveyPerformanceSha256=digest(graph['performanceFormations']),
    terrainSurveySurfaceProfilesSha256=digest(graph['routeSurfaceProfiles']),
    terrainSurveyCorridorPolicy=dict(lanes=[-1,-.5,0,.5,1],maximumSpacingCm=400,
        edgeInsetCm=42,turnBlendSteps=[0,.25,.5,.75,1],nativeTraversalApproved=False,
        surfaceCapsulePoseMethod=SURFACE_CAPSULE_POSE_METHOD),
    readOnly=True,nativeGeometryApproved=False)
payload=(json.dumps(report,indent=2)+'\n').encode('utf-8')
file.write_bytes(payload)
# Preserve the exact read-only policy witness when a later survey replaces the
# convenience baseline path. Its content hash avoids a revision/path cycle.
immutable=OUT/'surveys'/(hashlib.sha256(payload).hexdigest()+'.json')
immutable.parent.mkdir(exist_ok=True)
if immutable.exists() and immutable.read_bytes()!=payload:
    raise RuntimeError('Immutable native survey witness differs from its content hash')
immutable.write_bytes(payload)
unreal.log('WAR_CITADEL_BASELINE='+str(file))
