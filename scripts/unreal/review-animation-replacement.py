"""Native equipped contact sheets under one camera and lighting setup."""
import json
from pathlib import Path
import time
import unreal
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"artifacts/unreal/animation-replacement/review"
OUT.mkdir(exist_ok=True)
definitions=json.loads((OUT.parent/"presentations.json").read_text())["profiles"]
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not editor.new_level("/Game/Characters/Reviews/SuppliedAnimations_"+time.strftime("%Y%m%d_%H%M%S")): raise RuntimeError("Review level creation failed")
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,-2))
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
floor.set_actor_scale3d(unreal.Vector(30,30,1))
floor.set_actor_label('Technical review ground')
for rotation,power in [(unreal.Rotator(-35,-90,0),12000.),(unreal.Rotator(-25,40,0),8000.),(unreal.Rotator(-20,180,0),7000.)]:
    light=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,400),rotation)
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE); light.light_component.set_editor_property("intensity",power)
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,300))
sky.light_component.set_editor_properties(dict(intensity=.8,source_type=unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
    cubemap=unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")))
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
camera=capture.capture_component2d
camera.texture_target=unreal.RenderingLibrary.create_render_target2d(world,720,860,unreal.TextureRenderTargetFormat.RTF_RGBA8)
camera.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
camera.capture_every_frame=False; camera.capture_on_movement=False; camera.always_persist_rendering_state=True
camera.fov_angle=32; camera.post_process_blend_weight=1
settings=camera.get_editor_property("post_process_settings")
settings.set_editor_properties(dict(override_auto_exposure_method=True,auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True,auto_exposure_bias=1.5,override_auto_exposure_apply_physical_camera_exposure=True,
    auto_exposure_apply_physical_camera_exposure=True))
camera.post_process_settings=settings
actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
body=actor.skeletal_mesh_component; body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
weapon=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
shield=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
for part in (weapon,shield): part.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
frames=[]
for profile,entry in definitions.items():
    if not entry["presentations"]: continue
    visual=unreal.load_asset("/Game/MigrationProof/Visual_"+profile)
    body.set_skeletal_mesh_asset(visual.skeletal_mesh)
    weapon.static_mesh_component.set_static_mesh(visual.weapon_mesh)
    shield.static_mesh_component.set_static_mesh(visual.shield_mesh)
    samples=[("idle",0,1. if entry["style"]=="spell" else 0.,"")]
    for ability,recipe in entry["presentations"].items():
        samples.extend((role,recipe["contactSeconds"],1. if recipe["stowEquipment"] else 0.,"") for role in recipe["variantRoles"])
        if recipe['stowEquipment'] and entry['style']!='spell':
            samples.extend((role,seconds,.5,phase) for role in recipe['variantRoles']
                for seconds,phase in ((.15,'stowing'),(recipe['duration']-.15,'retrieving')))
    for role,seconds,stow,phase in samples:
        body.play_animation(unreal.load_asset(entry["bindings"][role]),False); body.set_position(seconds,False)
        unreal.WarImportLibrary.prepare_preview_frame(body)
        for slot,part,hand in (("weapon",weapon,"hand_R"),("shield",shield,"hand_L")):
            drawn=visual.get_editor_property(slot+'_grip')*body.get_socket_transform(hand)
            stored=visual.get_editor_property(slot+'_stowed')*body.get_socket_transform('upper_chest')
            transform=stored if stow>=1 else drawn
            part.set_actor_transform(transform,False,True)
        for view,location in (("front",unreal.Vector(0,570,160)),("side",unreal.Vector(570,0,160))):
            capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,unreal.Vector(0,0,105)),False,True)
            for _ in range(3): unreal.WarImportLibrary.prepare_world_preview_frame(world); camera.capture_scene()
            filename=profile+"_"+role.replace(".","_")+('_'+phase if phase else '')+"_"+view+".png"
            unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),filename)
            if not (OUT/filename).exists(): raise RuntimeError("Missing render: "+filename)
            frames.append(dict(profile=profile,role=role,seconds=seconds,phase=phase or 'contact',view=view,file=filename))
(OUT/"frames.json").write_text(json.dumps(frames,indent=2)+"\n")
unreal.log("WAR_NATIVE_EQUIPPED_REVIEW="+str(len(frames)))
