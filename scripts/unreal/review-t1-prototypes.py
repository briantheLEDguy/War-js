"""Render saved candidates at player height and sample road support without saving maps."""
import hashlib
import json
import math
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((DIRECTORY/'native-latest.json').read_text())
plan=json.loads((DIRECTORY/'plan.json').read_text())
output=DIRECTORY/'views'/receipt['planSha256'][:12];output.mkdir(parents=True,exist_ok=True)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def package_file(package):return ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
def point(p):return unreal.Vector(p['z']*100,p['x']*100,0)
checks=[]
for zone in receipt['zones']:
    identity=zone['id']
    if not levels.load_level(zone['map']):raise RuntimeError('Saved prototype unavailable')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    source_file=DIRECTORY/(identity+'.json')
    if sha(source_file)!=plan['candidateHashes'][identity]:raise RuntimeError('Review source differs from the saved terrain candidate')
    source=json.loads(source_file.read_text())
    terrain=[a for a in actors.get_all_level_actors() if 'WarT1PrototypeTerrain' in [str(t) for t in a.tags]]
    if len(terrain)!=2:raise RuntimeError('Prototype surfaces absent')
    obstacles=[a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in [str(t) for t in a.tags]]
    def floor(p):
        hit=unreal.SystemLibrary.line_trace_single(world,p+unreal.Vector(0,0,20000),p-unreal.Vector(0,0,20000),unreal.TraceTypeQuery.ECC_VISIBILITY,True,obstacles,unreal.DrawDebugTrace.NONE,True)
        if not hit or not hit.to_tuple()[0]:raise RuntimeError('Road ground is absent: '+str(p))
        return hit.to_tuple()[5]
    samples,max_grade=0,0
    # Full-width support on both shoulders, not just the centreline. This is not a drive playtest.
    for path in source['paths']:
        for a,b in zip(path['points'],path['points'][1:]):
            start,end=point(a),point(b);delta=end-start;distance=delta.length();normal=unreal.Vector(-delta.y,delta.x,0)/max(distance,1)
            for side in [-path['width']*50,0,path['width']*50]:
                previous=None
                count=max(1,math.ceil(distance/200))
                for i in range(count+1):
                    p=floor(start+delta*(i/count)+normal*side);samples+=1
                    if previous is not None:
                        grade=abs(p.z-previous.z)/max(math.hypot(p.x-previous.x,p.y-previous.y),1)
                        max_grade=max(max_grade,grade)
                    previous=p
    capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
    component=capture.capture_component2d
    component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR;component.capture_every_frame=False;component.capture_on_movement=False
    component.always_persist_rendering_state=True;component.fov_angle=75;component.post_process_blend_weight=0
    main=source['paths'][0]['points'];village=source['spawnPoint']
    modules=json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
    closest=min(modules['modules'],key=lambda p:math.hypot(p['entry']['x']-village['x'],p['entry']['z']-village['z']))
    views=[('advance',main[1],main[5]),('village',{'x':village['x'],'z':village['z']-12},closest['entry']),('ridge',source['paths'][1]['points'][2],main[4])]
    scenes=json.loads((DIRECTORY/(identity+'_scenes.json')).read_text())
    for label,scene in zip(['working_outskirts','regional_cover'],scenes[:2]):
        placements=scene['placements']
        if not placements:continue
        target={'x':sum(p['x'] for p in placements)/len(placements),'z':sum(p['z'] for p in placements)/len(placements)}
        camera=None
        for index in range(16):
            candidate={'x':target['x']+math.cos(index*math.pi/8)*48,'z':target['z']+math.sin(index*math.pi/8)*48}
            if all(math.hypot(candidate['x']-p['x'],candidate['z']-p['z'])>math.hypot(p['reservation']['width'],p['reservation']['depth'])/2+2 for p in placements):
                camera=candidate;break
        if camera is None:raise RuntimeError('No clear scenery-study camera')
        views.append((label,camera,target))
    for phase,seconds,weather in [('dawn',150,0),('day',1200,0),('dusk',2250,0),('night',2700,0),('weather',1200,.8)]:
        if not unreal.WarZoneLightingSubsystem.preview_environment(world,identity,unreal.Vector(),seconds,weather):raise RuntimeError('Regional atmosphere failed')
        for _ in range(64):unreal.WarImportLibrary.prepare_world_preview_frame(world);component.capture_scene()
        for label,location,target in views:
            camera=floor(point(location))+unreal.Vector(0,0,170)
            look=floor(point(target))+unreal.Vector(0,0,170)
            capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,look),False,True)
            for _ in range(12):unreal.WarImportLibrary.prepare_world_preview_frame(world);component.capture_scene()
            unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),identity+'_'+label+'_'+phase+'.png')
    if not unreal.WarZoneLightingSubsystem.preview_world(world,'aegis_capital',unreal.Vector()):raise RuntimeError('Capital restoration failed')
    checks.append({'zone':identity,'fullWidthGroundSamples':samples,'maximumSampledGrade':max_grade,'routeGradeWithinTarget':max_grade<=.22,
        'playerHeightCaptures':len(views)*5,'walkDriveAccepted':False,'visualApproved':False})
    actors.destroy_actor(capture)
for package,digest in receipt['packageHashes'].items():
    if sha(package_file(package))!=digest:raise RuntimeError('Read-only review changed a saved candidate')
(DIRECTORY/'review.json').write_text(json.dumps({'planSha256':receipt['planSha256'],'pictureDirectory':output.relative_to(ROOT).as_posix(),
    'zones':checks,'savedCandidatesUnchanged':True,'visualApproved':False,'performanceAccepted':False},indent=2)+'\n')
if any(not row['routeGradeWithinTarget'] for row in checks):raise RuntimeError('Native road grade exceeds the authoring target')
unreal.log('WAR_T1_PROTOTYPES_REVIEWED=2')
