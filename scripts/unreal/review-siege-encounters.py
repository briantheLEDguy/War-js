"""Render the exact staged encounter bodies, equipment and idol; never admit them."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/siege/encounter-review'
OUT.mkdir(exist_ok=True)
rows = json.loads((OUT.parent/'encounter-staging.json').read_text())['encounters']
unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,-2))
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
floor.set_actor_scale3d(unreal.Vector(30,30,1))
for rotation, power in [(unreal.Rotator(-35,-90,0),12000.),(unreal.Rotator(-25,40,0),8000.),(unreal.Rotator(-20,180,0),7000.)]:
    light = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,400), rotation)
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_intensity(power)
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,300))
sky.light_component.set_editor_properties(dict(intensity=.8, source_type=unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
    cubemap=unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')))
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
camera = capture.capture_component2d
camera.texture_target = unreal.RenderingLibrary.create_render_target2d(world,720,860,unreal.TextureRenderTargetFormat.RTF_RGBA8)
camera.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
camera.capture_every_frame=False; camera.capture_on_movement=False; camera.always_persist_rendering_state=True
camera.fov_angle=32; camera.post_process_blend_weight=1
settings=camera.get_editor_property('post_process_settings')
settings.set_editor_properties(dict(override_auto_exposure_method=True,auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True,auto_exposure_bias=1.5,override_auto_exposure_apply_physical_camera_exposure=True,
    auto_exposure_apply_physical_camera_exposure=True))
camera.post_process_settings=settings
frames=[]
def photograph(name, location, focus):
    capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,focus),False,True)
    for _ in range(3): unreal.WarImportLibrary.prepare_world_preview_frame(world); camera.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),name+'.png')
    if not (OUT/(name+'.png')).is_file(): raise RuntimeError('Missing native capture '+name)
    frames.append(name+'.png')

for row in rows:
    visual=unreal.load_asset(row['visual'])
    if visual.validate_for_spawn(visual.realm): raise RuntimeError('Invalid staged encounter: '+row['profile'])
    actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
    body=actor.skeletal_mesh_component; body.set_skeletal_mesh_asset(visual.skeletal_mesh)
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    transform=visual.mesh_transform; transform.translation=unreal.Vector()
    actor.set_actor_transform(transform,False,True)
    parts=[]
    for slot,bone in (('weapon','hand_R'),('shield','hand_L')):
        mesh=visual.get_editor_property(slot+'_mesh')
        if mesh:
            part=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
            part.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            part.static_mesh_component.set_static_mesh(mesh); parts.append((slot,bone,part))
    for role in ('idle','walk','attack_melee','death'):
        clip=visual.imported_animations[role]
        body.play_animation(clip,False); body.set_position(unreal.AnimationLibrary.get_sequence_length(clip)*.5,False)
        unreal.WarImportLibrary.prepare_preview_frame(body)
        for slot,bone,part in parts:
            part.set_actor_transform(visual.get_editor_property(slot+'_grip')*body.get_socket_transform(bone),False,True)
        # Keep the commander's extended two-handed hammer inside both views.
        distance = 1000 if row['role'] == 'commander_visual' and role == 'attack_melee' else 570
        for view,location in (('front',unreal.Vector(distance,0,160)),('side',unreal.Vector(0,distance,160))):
            photograph(row['profile']+'_'+role+'_'+view,location,unreal.Vector(0,0,105))
    for _,_,part in parts: actors.destroy_actor(part)
    actors.destroy_actor(actor)
idol=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
idol.static_mesh_component.set_static_mesh(unreal.load_asset('/Game/Characters/Equipment/WarpIdol'))
if not idol.static_mesh_component.static_mesh: raise RuntimeError('Native idol missing')
photograph('WarpIdol_native',unreal.Vector(200,240,150),unreal.Vector(0,0,28))
(OUT/'frames.json').write_text(json.dumps(dict(frames=frames,artApproval=False,gameplayVerified=False),indent=2)+'\n')
unreal.log('WAR_SIEGE_ENCOUNTER_REVIEW='+str(len(frames)))
