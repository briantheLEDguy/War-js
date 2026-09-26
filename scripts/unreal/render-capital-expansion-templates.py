"""Isolated studio views of authored assemblies; not city lighting acceptance."""
import json
from pathlib import Path
import uuid
import unreal

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/capital-expansion'
templates=json.loads((OUT/'assets.json').read_text())['templates']
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.new_level('/Game/LicensedKits/CapitalExpansion/Review_'+uuid.uuid4().hex): raise RuntimeError('Scratch map failed')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,10000),unreal.Rotator(pitch=-40,yaw=-65))
sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
sun.light_component.set_editor_property('intensity',24000)
fill=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,10000),unreal.Rotator(pitch=-20,yaw=130))
fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fill.light_component.set_editor_property('intensity',9000)
fill.light_component.set_editor_property('cast_shadows',False)
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
c=capture.capture_component2d
c.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,900,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
c.capture_every_frame=False;c.capture_on_movement=False;c.always_persist_rendering_state=True;c.fov_angle=70
s=c.post_process_settings
s.override_auto_exposure_method=True;s.auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL
s.override_auto_exposure_bias=True;s.auto_exposure_bias=0
c.post_process_settings=s
for key in ('aegis_interior_00_home','aegis_interior_03_home','riftspire_interior_08_inn','riftspire_residence_03'):
    t=templates[key]
    actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
    actor.static_mesh_component.set_static_mesh(unreal.load_asset(t['mesh']))
    radius=max(t['extent'][:2]);center=unreal.Vector(*t['origin'])
    for suffix,eye,target in [('outside',unreal.Vector(radius*2,-radius*2,radius*1.5),center)]:
        capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target),False,True)
        for _ in range(8): unreal.WarImportLibrary.prepare_world_preview_frame(world);c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world,c.texture_target,str(OUT),key+'_'+suffix+'.png')
    if t['interior']:
        eye=unreal.Vector(t['entrance'][0],t['entrance'][1]+280,175)
        target=unreal.Vector(0,t['roomSize'][1]/2-70,140)
        capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target),False,True)
        for _ in range(8): unreal.WarImportLibrary.prepare_world_preview_frame(world);c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world,c.texture_target,str(OUT),key+'_inside.png')
    actors.destroy_actor(actor)
unreal.log('WAR_EXPANSION_TEMPLATES_RENDERED')
