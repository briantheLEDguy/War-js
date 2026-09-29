"""Render native draft portals in an unsaved review world; never grants approval."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/portal-models/baked'
native=json.loads((OUT/'native-candidates.json').read_text())
for row in native:
    if hashlib.sha256((OUT/(row['name']+'.glb')).read_bytes()).hexdigest()!=row['sourceSha256']:
        raise RuntimeError('Native candidate does not match the current export')
unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for location,power in [(unreal.Vector(-900,900,1500),10000.),(unreal.Vector(900,300,800),5000.),(unreal.Vector(0,-700,1200),7000.)]:
    light=actors.spawn_actor_from_class(unreal.DirectionalLight,location,
        unreal.MathLibrary.find_look_at_rotation(location,unreal.Vector(0,0,500)))
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_intensity(power)
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,500))
sky.light_component.set_editor_properties(dict(intensity=.5,source_type=unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,
    cubemap=unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')))
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
camera=capture.capture_component2d
camera.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1100,1300,unreal.TextureRenderTargetFormat.RTF_RGBA8)
camera.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
camera.capture_every_frame=False;camera.capture_on_movement=False;camera.always_persist_rendering_state=True;camera.fov_angle=45
settings=camera.get_editor_property('post_process_settings')
settings.set_editor_properties(dict(override_auto_exposure_method=True,auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
    override_auto_exposure_bias=True,auto_exposure_bias=1.5,override_auto_exposure_apply_physical_camera_exposure=True,auto_exposure_apply_physical_camera_exposure=True))
camera.post_process_settings=settings
frames=[]
for row in native:
    meshes=[]
    for part in row['parts'].values():
        mesh=unreal.load_asset(part['asset'])
        if not mesh:raise RuntimeError('Missing candidate mesh')
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.set_actor_enable_collision(False);meshes.append(actor)
    # FBX's handedness conversion reverses the Blender front (-Y) to native +Y.
    for view,location in [('front',unreal.Vector(0,1650,550)),('hero',unreal.Vector(550,1500,850))]:
        capture.set_actor_location_and_rotation(location,unreal.MathLibrary.find_look_at_rotation(location,unreal.Vector(0,0,540)),False,True)
        for _ in range(5):
            unreal.WarImportLibrary.prepare_world_preview_frame(world)
            camera.capture_scene()
        filename=row['name']+'-native-'+view+'.png'
        unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),filename)
        frames.append(filename)
    camera.capture_source=unreal.SceneCaptureSource.SCS_BASE_COLOR
    for _ in range(5):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        camera.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,camera.texture_target,str(OUT),row['name']+'-native-basecolor.png')
    camera.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    for actor in meshes:actors.destroy_actor(actor)
(OUT/'native-frames.json').write_text(json.dumps(dict(frames=frames,reviewed=False,worldInstalled=False),indent=2)+'\n')
unreal.log('WAR_PORTAL_NATIVE_FRAMES='+str(len(frames)))
