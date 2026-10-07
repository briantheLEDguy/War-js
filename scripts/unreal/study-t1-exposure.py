"""Capture controlled exposure alternatives from unchanged native review maps."""
import hashlib
import json
import math
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((DIRECTORY/'native-latest.json').read_text())
output=DIRECTORY/'views'/receipt['planSha256'][:12]/'exposure-study';output.mkdir(parents=True,exist_ok=True)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
diagnostics=[]
for zone in receipt['zones']:
    identity=zone['id']
    if not levels.load_level(zone['map']):raise RuntimeError('Review map missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world);unreal.WarImportLibrary.prepare_world_preview_frame(world)
    source=json.loads((DIRECTORY/(identity+'.json')).read_text());village=source['spawnPoint']
    modules=json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
    closest=min(modules['modules'],key=lambda p:math.hypot(p['entry']['x']-village['x'],p['entry']['z']-village['z']))
    obstacles=[a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in [str(t) for t in a.tags]]
    def floor(p):
        origin=unreal.Vector(p['z']*100,p['x']*100,0)
        hit=unreal.SystemLibrary.line_trace_single(world,origin+unreal.Vector(0,0,20000),origin-unreal.Vector(0,0,20000),unreal.TraceTypeQuery.ECC_VISIBILITY,True,obstacles,unreal.DrawDebugTrace.NONE,True)
        if not hit or not hit.to_tuple()[0]:raise RuntimeError('Study camera has no ground')
        return hit.to_tuple()[5]+unreal.Vector(0,0,170)
    camera=floor({'x':village['x'],'z':village['z']-12});look=floor(closest['entry'])
    capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,camera,unreal.MathLibrary.find_look_at_rotation(camera,look))
    component=capture.capture_component2d
    component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR;component.capture_every_frame=False;component.capture_on_movement=False
    component.always_persist_rendering_state=True;component.fov_angle=75;component.post_process_blend_weight=0
    for phase,seconds,exposures in [('day',1200,[-.5,0,.5]),('night',2700,[.5,1.5,2.5])]:
        if not unreal.WarZoneLightingSubsystem.preview_environment(world,identity,unreal.Vector(),seconds,0):raise RuntimeError('Study environment missing')
        all_actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
        grades=[c for a in all_actors if 'WarLocalZoneEnvironment' in [str(t) for t in a.tags] for c in a.get_components_by_class(unreal.PostProcessComponent)]
        if len(grades)!=1:raise RuntimeError('Study exposure has ambiguous ownership')
        lights=[a.get_component_by_class(unreal.LightComponent) for a in all_actors if isinstance(a,(unreal.DirectionalLight,unreal.WarPracticalLight))]
        diagnostics.append({'zone':identity,'phase':phase,'lights':[{'intensity':c.get_editor_property('intensity'),'color':str(c.get_editor_property('light_color'))} for c in lights if c]})
        for exposure in exposures:
            settings=grades[0].get_editor_property('settings');settings.set_editor_property('auto_exposure_bias',exposure)
            grades[0].set_editor_property('settings',settings)
            for _ in range(64):unreal.WarImportLibrary.prepare_world_preview_frame(world);component.capture_scene()
            unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),identity+'_'+phase+'_'+str(exposure)+'.png')
    actors.destroy_actor(capture)
for package,digest in receipt['packageHashes'].items():
    file=ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError('Exposure study changed a saved map')
(output/'diagnostic.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
unreal.log('WAR_T1_EXPOSURE_STUDY=2')
