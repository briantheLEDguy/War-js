"""Render the actual equipped Prelate with the supplied retargeted clips."""
import json, time
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/two-handed'
receipt=json.loads((OUT/'retarget.json').read_text())
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not editor.new_level('/Game/MigrationProof/PrelateTwoHandedReview_' + time.strftime('%Y%m%d_%H%M%S')):
    raise RuntimeError('Cannot create isolated animation review level')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor_mat=unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
floor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,-2))
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
floor.set_actor_scale3d(unreal.Vector(45,25,1))
floor.set_actor_label('Review ground (technical surface)')
light=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,400),unreal.Rotator(-40,-45,0))
light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
light.light_component.set_editor_property('intensity',15000.0)
fill=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,400),unreal.Rotator(-25,-135,0))
fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fill.light_component.set_editor_property('intensity',9000.)
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,300))
sky.light_component.set_editor_property('intensity',.8)
sky.light_component.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.light_component.set_editor_property('cubemap',unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
component=capture.capture_component2d
component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,640,640,unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame=False
component.capture_on_movement=False
component.always_persist_rendering_state=True
component.fov_angle=40
component.post_process_blend_weight=1
settings=component.get_editor_property('post_process_settings')
settings.set_editor_property('override_auto_exposure_method',True)
settings.set_editor_property('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property('override_auto_exposure_bias',True)
settings.set_editor_property('auto_exposure_bias',0.)
settings.set_editor_property('override_auto_exposure_apply_physical_camera_exposure',True)
settings.set_editor_property('auto_exposure_apply_physical_camera_exposure',True)
component.set_editor_property('post_process_settings',settings)

actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
body=actor.skeletal_mesh_component
body.set_skeletal_mesh_asset(unreal.load_asset(receipt['targetMesh']))
body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
frames=[]
poses={}
for key in receipt['clips']:
    clip=receipt['clips'][key]
    animation=unreal.load_asset(clip['animation'])
    body.play_animation(animation,False)
    poses[key]=[]
    options=unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh',body.skeletal_mesh_asset)
    times = ([min(index / 30, clip['duration']) for index in range(round(clip['duration'] * 30) + 1)]
             if key in ('idle', 'walk', 'slash_alternate') else [clip['duration'] * fraction for fraction in (0, .25, .5, .75)])
    for index,seconds in enumerate(times):
        body.set_position(seconds,False)
        unreal.WarImportLibrary.prepare_preview_frame(body)
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,seconds,options)
        sample={}
        for bone in ['root','hips','head','hand_L','hand_R','foot_L','foot_R']:
            transform=unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD)
            sample[bone]=str(transform)
        poses[key].append(sample)
        for view,location in [('front',unreal.Vector(330,650,215)),('side',unreal.Vector(670,30,215))]:
            capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,unreal.Vector(0,0,100)),False,True)
            for _ in range(3):
                unreal.WarImportLibrary.prepare_world_preview_frame(world)
                component.capture_scene()
            filename=f'{key}_{index:03d}_{view}.png'
            unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(OUT),filename)
            if not (OUT/filename).is_file(): raise RuntimeError('Missing render '+filename)
            frames.append(dict(clip=key,seconds=seconds,file=filename))
(OUT/'frames.json').write_text(json.dumps(frames,indent=2))
(OUT/'poses.json').write_text(json.dumps(poses,indent=2))
unreal.log('WAR_TWO_HANDED_RENDERED')
