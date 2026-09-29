"""Render staged bodies with their exact proposed equipment; never save the live city."""
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from imported_population import OUT, BASE, LEDGER, digest, models

sets = json.loads((OUT/'presentations.json').read_text())['profiles']
installed = json.loads((OUT/'installed.json').read_text())
catalog = unreal.load_asset(installed['catalog'])
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for rotation,power in [(unreal.Rotator(-35,-90,0),11000.),(unreal.Rotator(-25,40,0),7000.),(unreal.Rotator(-20,180,0),5000.)]:
    light = actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,400),rotation)
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_intensity(power)
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
camera = capture.capture_component2d
camera.texture_target = unreal.RenderingLibrary.create_render_target2d(world,420,600,unreal.TextureRenderTargetFormat.RTF_RGBA8)
camera.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
camera.capture_every_frame=False; camera.capture_on_movement=False; camera.always_persist_rendering_state=True
camera.fov_angle=35
camera.post_process_blend_weight=1
settings=camera.get_editor_property('post_process_settings')
settings.set_editor_properties(dict(override_auto_exposure_method=True,auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True,auto_exposure_bias=2.0,override_auto_exposure_apply_physical_camera_exposure=True,
    auto_exposure_apply_physical_camera_exposure=True))
camera.post_process_settings=settings
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,300))
sky.light_component.set_editor_properties(dict(intensity=.8,source_type=unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
    cubemap=unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')))
actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
component = actor.skeletal_mesh_component
parts = [actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector()) for _ in range(2)]
for part in parts: part.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
frames = []
output = OUT/'review'; output.mkdir(exist_ok=True)
for row in models().values():
    profile = row['profile']; entry = sets[profile]
    component.set_skeletal_mesh_asset(unreal.load_asset(entry['mesh']))
    component.set_collision_profile_name('NoCollision')
    loadout = next((b for b in catalog.get_editor_property('loadouts') if str(b.get_editor_property('profile'))==profile),None)
    attachments = list(loadout.get_editor_property('attachments')) if loadout else []
    for index,part in enumerate(parts):
        part.set_actor_hidden_in_game(index>=len(attachments))
        if index<len(attachments): part.static_mesh_component.set_static_mesh(attachments[index].get_editor_property('mesh'))
    samples = [('civilian_idle',.3),('idle',.3),('walk',.5),('attack_melee',.25),('attack_melee',.5),('attack_melee',.8),('hit_front',.5),('death',.8)]
    for role,fraction in samples:
        for index,part in enumerate(parts):
            part.set_actor_hidden_in_game(role=='civilian_idle' or index>=len(attachments))
        clip = unreal.load_asset(entry['bindings'][role])
        seconds = unreal.AnimationLibrary.get_sequence_length(clip)*fraction
        component.play_animation(clip,False); component.set_position(seconds,False)
        unreal.WarImportLibrary.prepare_preview_frame(component)
        for part,attachment in zip(parts,attachments):
            part.set_actor_transform(attachment.get_editor_property('relative_transform')*component.get_socket_transform(attachment.get_editor_property('bone')),False,True)
        origin,extent,_ = unreal.SystemLibrary.get_component_bounds(component)
        for side,offset in [('front',unreal.Vector(-430,0,130)),('side',unreal.Vector(0,-430,130))]:
            target = unreal.Vector(0,0,105)
            capture.set_actor_location_and_rotation(offset,unreal.MathLibrary.find_look_at_rotation(offset,target),False,True)
            for _ in range(3):
                unreal.WarImportLibrary.prepare_world_preview_frame(world); camera.capture_scene()
            filename = profile+'_'+role+'_'+str(int(fraction*100))+'_'+side+'.png'
            unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(output),filename)
            if not (output/filename).is_file(): raise RuntimeError('Review image missing: '+filename)
            frames.append(dict(profile=profile,role=role,fraction=fraction,view=side,file=filename,
                boundsOrigin=[origin.x,origin.y,origin.z],boundsExtent=[extent.x,extent.y,extent.z]))
(OUT/'review.json').write_text(json.dumps(dict(ledgerSha256=digest(LEDGER),
    technicalSha256=digest(OUT/'technical-verification.json'),frames=frames,approved=False),indent=2)+'\n')
