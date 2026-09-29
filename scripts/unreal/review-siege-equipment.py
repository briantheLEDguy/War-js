"""Render the actual native engine meshes with fitted Greenskin push poses."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/siege/equipment/review';OUT.mkdir(exist_ok=True)
native=json.loads((OUT.parent/'native.json').read_text())
unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,-2));floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
floor.set_actor_scale3d(unreal.Vector(50,50,1))
for position,power in [(unreal.Vector(-500,400,500),10000.),(unreal.Vector(-400,-500,300),8000.),(unreal.Vector(500,400,500),7000.)]:
    rotation=unreal.MathLibrary.find_look_at_rotation(position,unreal.Vector(0,0,100))
    light=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,600),rotation)
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE);light.light_component.set_intensity(power)
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,400))
sky.light_component.set_editor_properties(dict(intensity=.8,source_type=unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
    cubemap=unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')))
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
camera=capture.capture_component2d
camera.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1100,850,unreal.TextureRenderTargetFormat.RTF_RGBA8)
camera.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
camera.capture_every_frame=False;camera.capture_on_movement=False;camera.always_persist_rendering_state=True;camera.fov_angle=45
settings=camera.get_editor_property('post_process_settings')
settings.set_editor_properties(dict(override_auto_exposure_method=True,auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True,auto_exposure_bias=1.5,override_auto_exposure_apply_physical_camera_exposure=True,auto_exposure_apply_physical_camera_exposure=True))
camera.post_process_settings=settings
visual=unreal.load_asset('/Game/Characters/SiegeStaging/Visual_npc_siege_riftbound_breach_engineer')
frames=[]
for name in ('Ram','Catapult'):
    definition=unreal.load_asset(native['assets'][name]);parts=definition.get_editor_property('parts');crew=[];meshes=[]
    for part in parts:
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
        actor.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        actor.static_mesh_component.set_static_mesh(part.get_editor_property('mesh'));meshes.append(actor)
    for position in definition.get_editor_property('crew_positions'):
        actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,position)
        transform=visual.mesh_transform;transform.translation=position
        actor.set_actor_transform(transform,False,True)
        actor.skeletal_mesh_component.set_skeletal_mesh_asset(visual.skeletal_mesh)
        actor.skeletal_mesh_component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE);crew.append(actor)
    for phase in (0,.25,.5,.75):
        clip=definition.get_editor_property('push_animation')
        for actor in crew:
            actor.skeletal_mesh_component.play_animation(clip,False)
            actor.skeletal_mesh_component.set_position(unreal.AnimationLibrary.get_sequence_length(clip)*phase,False)
            unreal.WarImportLibrary.prepare_preview_frame(actor.skeletal_mesh_component)
        for i,actor in enumerate(meshes):
            poses=parts[i].get_editor_property('roll');actor.set_actor_transform(poses[round(phase*(len(poses)-1))],False,True)
        for view,location,focus in [('rear',unreal.Vector(-850,600,400),unreal.Vector(-80,0,125)),
                                    ('side',unreal.Vector(-200,1050,260),unreal.Vector(-60,0,120))]:
            capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,focus),False,True)
            for _ in range(3):unreal.WarImportLibrary.prepare_world_preview_frame(world);camera.capture_scene()
            filename=f'{name}_{phase}_{view}.png';unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),filename);frames.append(filename)
    if name=='Ram':
        for time in (0,.7,1.5):
            for i,actor in enumerate(meshes):
                poses=parts[i].get_editor_property('strike')
                if poses:actor.set_actor_transform(poses[round(time/1.5*(len(poses)-1))],False,True)
            location=unreal.Vector(750,800,400)
            capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,unreal.Vector(0,0,130)),False,True)
            for _ in range(3):unreal.WarImportLibrary.prepare_world_preview_frame(world);camera.capture_scene()
            filename=f'Ram_strike_{time}.png';unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),filename);frames.append(filename)
    for actor in meshes+crew:actors.destroy_actor(actor)
standard=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
standard.static_mesh_component.set_static_mesh(unreal.load_asset(native['assets']['RiftboundStandard'][0]))
standard.set_actor_scale3d(unreal.Vector(.55,.55,.55))
location=unreal.Vector(850,700,350)
capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,unreal.Vector(0,0,210)),False,True)
for _ in range(3):unreal.WarImportLibrary.prepare_world_preview_frame(world);camera.capture_scene()
unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),'RiftboundStandard.png');frames.append('RiftboundStandard.png')
(OUT/'frames.json').write_text(json.dumps(dict(frames=frames,reviewed=False),indent=2))
