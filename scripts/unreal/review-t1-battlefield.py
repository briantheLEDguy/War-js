"""Native ground/grade/arrival verification and player-height views of the battlefield prototype."""
import json
import math
import re
from pathlib import Path
import sys
import unreal
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(Path(__file__).parent))
from t1_battlefield import Surface
from t1_materials import protected_saved,verify_protected,sha,same_state
from t1_material_clone import inventory
from t1_population_native import GroundReview,population_actor
from t1_render_log import validate_render_log
from t1_battlefield_views import neighborhood_views
from t1_ecology_native import cover_inventory

BASE=ROOT/'artifacts/unreal/t1-redesign'; CONTENT=ROOT/'unreal/AegisWar/Content'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
scene_cells='-wart1battlefieldscenes' in unreal.SystemLibrary.get_command_line().lower()
receipt=read(BASE/('battlefield-scenes-latest.json' if scene_cells else 'battlefield-latest.json'))
if receipt['study']!='battlefield-landscape' or '-nullrhi' in unreal.SystemLibrary.get_command_line().lower(): raise RuntimeError('Battlefield review requires its rendered native candidate')
bindings={**receipt['inputs']['sourceHashes'],**receipt['inputs']['tools'],**receipt['assetHashes']}
packages={**receipt['inputs']['parentPackages'],**receipt['packageHashes']}
def verify_bindings():
    for p,h in bindings.items():
        if sha(ROOT/p)!=h: raise RuntimeError('Changed battlefield binding: '+p)
    for p,h in packages.items():
        if sha(CONTENT/(p.removeprefix('/Game/')+'.umap'))!=h: raise RuntimeError('Changed battlefield package: '+p)
verify_bindings(); protected=protected_saved(ROOT)
output=BASE/'battlefield-views'/receipt['signature'][:12]; output.mkdir(parents=True,exist_ok=True)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
pictures=[]; reports=[]
try:
    for zone in receipt['zones']:
        source=read(ROOT/zone['sourceDirectory']/(zone['id']+'.json')); surface=Surface(source,read(ROOT/zone['sourceDirectory']/(zone['id']+'_terrain.json')))
        if not levels.load_level(zone['map']): raise RuntimeError('Cannot load battlefield candidate')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        if not same_state(inventory(actors),zone['actorInventory']): raise RuntimeError('Battlefield inventory changed')
        if zone.get('groundCover') and not same_state(cover_inventory(actors),zone['groundCover']): raise RuntimeError('Saved native ground cover differs from its admitted batch')
        road_source=read(ROOT/zone['sourceDirectory']/(zone['id']+'_roads.json'))
        road_mesh=unreal.load_asset(zone['actorInventory'][zone['id']+'_roads']['mesh'])
        road_native=json.loads(unreal.WarImportLibrary.describe_static_mesh_source_data(road_mesh,0))
        expected_colors=[road_source['colors'][i] for i in road_source['indices']]
        if not road_native.get('valid') or not same_state(road_native['data'].get('vertexColors'),expected_colors):
            raise RuntimeError('Native road lost its source verge fade')
        for row in zone['population']:
            actor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==row['id'])
            if not same_state(population_actor(actor),row['savedState']): raise RuntimeError('Battlefield population bindings changed')
        ground=GroundReview(world,actors,zone['id'],source['spatial']['playableOutline'])
        maximum_grade=0; maximum_error=0; route_samples=0; route_grades=[]
        paths=source['paths']+source['orvrLayout']['caravanRoutes']
        existing={p['id'] for p in source['paths']}
        paths += [dict(id=c['id'],points=c['points'],width=6 if '_pocket_' in c['id'] else 12) for c in source['orvrLayout']['terrain']['clearCorridors'] if c['id'] not in existing]
        for path in paths:
            path_grade=0
            for a,b in zip(path['points'],path['points'][1:]):
                dx,dz=b['x']-a['x'],b['z']-a['z']; length=math.hypot(dx,dz); count=max(1,math.ceil(length/2))
                lanes=math.ceil(path['width']/2)
                for lane in range(lanes+1):
                    side=-path['width']/2+lane/lanes*path['width']
                    previous=None
                    for i in range(count+1):
                        x=a['x']+dx*i/count-dz/length*side; z=a['z']+dz*i/count+dx/length*side
                        p=ground.ground([z*100,x*100,0]); route_samples+=1
                        if p is None: raise RuntimeError('Native route lacks walkable full-width support: '+json.dumps(ground.failures))
                        maximum_error=max(maximum_error,abs(p[2]-surface.height_cm(x,z)))
                        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(z*100,x*100,20000),unreal.Vector(z*100,x*100,-20000),
                            unreal.TraceTypeQuery.ECC_VISIBILITY,True,ground.ignored,unreal.DrawDebugTrace.NONE,True)
                        parts=hit.to_tuple() if hit else None
                        if not parts or not parts[0] or parts[9]!=ground.terrain: raise RuntimeError('Route normal lacks native ground')
                        normal=parts[7]; grade=math.hypot(normal.x,normal.y)/max(normal.z,.001)
                        maximum_grade=max(maximum_grade,grade); path_grade=max(path_grade,grade)
                        if previous: maximum_grade=max(maximum_grade,abs(p[2]-previous[2])/max(math.hypot(p[0]-previous[0],p[1]-previous[1]),1))
                        previous=p
            route_grades.append(dict(id=path['id'],maximumSurfaceGrade=path_grade))
        if maximum_grade>.22 or maximum_error>1: raise RuntimeError('Native terrain/source grade or triangle correspondence failed: '+str((maximum_grade,maximum_error)))
        arrivals=[]
        for name,p in [(zone['id']+'_spawn',source['spawnPoint'])]+[(t['id'],t['arrivalPoint']) for t in source['zoneTriggers']]:
            supported=ground.center([p['z']*100,p['x']*100,0])
            if not supported: raise RuntimeError('Blocked terrain-aware arrival: '+json.dumps(ground.failures))
            arrivals.append(name)
        capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector()); component=capture.capture_component2d
        component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1440,900,unreal.TextureRenderTargetFormat.RTF_RGBA8)
        component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR; component.capture_every_frame=False
        component.capture_on_movement=False; component.always_persist_rendering_state=True; component.fov_angle=75; component.post_process_blend_weight=0
        main=source['paths'][0]['points']; upper=source['paths'][1]['points']; village=source['spawnPoint']
        views=[('west_battle_space',main[1],main[4]),('middle_saddle',main[3],main[6]),
               ('eastern_counterpush',main[7],main[3]),('ridge_back_slope',upper[3],main[4]),
               ('village_outskirts',dict(x=village['x'],z=village['z']+35),main[0] if zone['id']=='sunmeadow_march' else main[8]),
               ('off_road_shoulder',dict(x=-250,z=-145 if zone['id']=='sunmeadow_march' else -260),main[4])]
        if scene_cells:
            views += [('regional_cell',dict(x=-280,z=-70 if zone['id']=='sunmeadow_march' else -190),dict(x=-220,z=85 if zone['id']=='sunmeadow_march' else -85)),
                      ('counterpush_cell',dict(x=-65,z=-170 if zone['id']=='sunmeadow_march' else -290),dict(x=15,z=-105 if zone['id']=='sunmeadow_march' else -210))]
        if scene_cells: views += neighborhood_views(source['paths'], zone['sceneCells'][2:])
        for pocket in zone.get('landscapePockets',[]):
            p=pocket['approach'][-2]
            views.append(('pocket_'+pocket['id'].split('_pocket_')[-1],p,dict(x=pocket['x'],z=pocket['z'])))
        effects=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarRegionalAtmosphere)]
        if len(effects)!=1 or str(effects[0].zone_id)!=zone['id']: raise RuntimeError('Regional effect owner differs from candidate')
        for phase,seconds,strength in [('dawn',150,0),('day',1200,0),('dusk',2250,0),('night',2700,0),('strong_weather',1200,.8)]:
            if not unreal.WarZoneLightingSubsystem.preview_environment(world,zone['id'],unreal.Vector(),seconds,strength): raise RuntimeError('Regional clock lighting unavailable')
            for label,p,target in views:
                if label.startswith(('landscape_','pocket_')) and phase!='day': continue
                floor=ground.ground([p['z']*100,p['x']*100,0]); target_floor=ground.ground([target['z']*100,target['x']*100,0])
                if floor is None or target_floor is None: raise RuntimeError('Camera point lacks native terrain')
                eye=unreal.Vector(*floor)+unreal.Vector(0,0,170); aim=unreal.Vector(*target_floor)+unreal.Vector(0,0,20 if label.startswith('pocket_') else 170)
                capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
                for frame in range(48):
                    if not effects[0].preview_frame(eye, capture.get_actor_forward_vector(), seconds+frame/60, strength): raise RuntimeError('Regional effect preview failed')
                    unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
                file=output/(zone['id']+'_'+label+'_'+phase+'.png')
                unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),file.name)
                if not file.exists() or file.stat().st_size<10000: raise RuntimeError('Native view did not export')
                pictures.append(dict(file=file.relative_to(ROOT).as_posix(),sha256=sha(file),zone=zone['id'],view=label,phase=phase,
                                     eye=[eye.x,eye.y,eye.z],target=[aim.x,aim.y,aim.z],playerHeightMetres=1.7,weatherStrength=strength,visibleWeatherParticles=effects[0].get_particle_count(),prototype=True,visualApproved=False))
        actors.destroy_actor(capture); unreal.WarZoneLightingSubsystem.preview_world(world,'aegis_capital',unreal.Vector())
        reports.append(dict(zone=zone['id'],fullWidthSamples=route_samples,maximumNativeGrade=maximum_grade,
                            maximumSourceErrorCm=maximum_error,routeGrades=route_grades,nativeRoadAlphaCornersVerified=len(expected_colors),
                            clearArrivals=arrivals,groundCoverInstances=sum(r['count'] for r in zone.get('groundCover',{}).values()),groundCoverReloadVerified=True,waterSurfaces=zone.get('waterSurfaces',[]),bindingsVerified=True,drivingAccepted=False,visualApproved=False))
        unreal.log('WAR_T1_BATTLEFIELD_REVIEWED_ZONE='+zone['id'])
finally:
    verify_bindings(); verify_protected(ROOT,protected)
log_argument=re.search(r'-abslog=(?:"([^"]+)"|\x27([^\x27]+)\x27|(\S+))',unreal.SystemLibrary.get_command_line(),re.IGNORECASE)
if not log_argument: raise RuntimeError('Rendered review requires an explicit native log')
native_log=Path(next(v for v in log_argument.groups() if v is not None))
validate_render_log(native_log.read_text(encoding='utf-8-sig',errors='replace'))
result=dict(signature=receipt['signature'],checks=reports,pictures=pictures,verificationTools={p:sha(ROOT/p) for p in ('scripts/unreal/review-t1-battlefield.py','scripts/unreal/t1_battlefield_views.py','scripts/unreal/t1_ecology_native.py','scripts/unreal/t1_render_log.py')},savedCandidatesUnchanged=True,
            ownerDocumentsPreserved=True,materialShaderCompilationPassed=True,appearanceApproved=False,drivingAccepted=False,eighteenVersusEighteenAccepted=False)
prefix='battlefield-scenes' if scene_cells else 'battlefield'
(BASE/(prefix+'-review-'+receipt['signature'][:12]+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(BASE/(prefix+'-review.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_BATTLEFIELD_REVIEWED='+str(len(pictures)))
