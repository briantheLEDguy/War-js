"""Reload and inspect saved capital additions; render without saving capture actors."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'artifacts/unreal/licensed-kits'
receipt=json.loads((directory/'capital-detail-build.json').read_text())
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(receipt['map']):
    raise RuntimeError('Official capital cannot reload')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
original=list(actors.get_all_level_actors())
details=[a for a in original if 'WarCapitalDetailV1' in [str(t) for t in a.tags]]
if len(details)!=receipt['addedActorCount']:
    raise RuntimeError('Saved detail actor count differs')
if any(isinstance(a,unreal.StaticMeshActor) and not a.static_mesh_component.static_mesh for a in original):
    raise RuntimeError('Saved capital contains missing static meshes')
if len(original)<receipt['preservedActorCount']+len(details):
    raise RuntimeError('Original city actors are missing')
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
component=capture.capture_component2d
component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1600,1000,unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame=False
component.capture_on_movement=False
component.always_persist_rendering_state=True
component.fov_angle=60
component.post_process_blend_weight=0
fixture=min(receipt['fixtures'],key=lambda p:abs(p['position'][0]+11800)+abs(p['position'][1]))
x,y,z=fixture['position']
views=[('fixture',(x-440,y-390,z+215),(x,y,z+160)),
       ('market',(-12600,-3400,580),(-9700,2000,150)),
       ('avenue',(-11400,0,260),(-6500,0,550)),
       ('city',(-32000,-28000,21000),(5000,0,3200))]
records=[]
for name,eye,center in views:
    eye,center=unreal.Vector(*eye),unreal.Vector(*center)
    capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,center),False,True)
    for _ in range(12):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        component.capture_scene()
    filename='capital-detail-'+name+'.png'
    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(directory),filename)
    records.append({'image':filename,'name':name})
(directory/'capital-detail-verified.json').write_text(json.dumps({'map':receipt['map'],
    'totalActors':len(original),'details':len(details),'missingStaticMeshes':0,
    'preservedActorCount':receipt['preservedActorCount'],'savedSceneLighting':True,
    'views':records,'visualApproved':False},indent=2)+'\n')
unreal.log('WAR_CAPITAL_DETAIL_VERIFIED')
