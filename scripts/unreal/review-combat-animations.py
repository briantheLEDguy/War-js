"""Build a playable native choreography gallery and render timed review frames.

UnrealEditor-Cmd ... -run=pythonscript -script=<this file> (requires rendering).
"""
import json
import time
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/combat-animation'
(OUT/'review.json').unlink(missing_ok=True)
receipt=json.loads((OUT/'native-import.json').read_text())
contract=json.loads(Path(__file__).with_name('combat-motions.json').read_text())
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
map_path='/Game/MigrationProof/CombatAnimationReview_'+time.strftime('%Y%m%d_%H%M%S')
if not editor.new_level(map_path): raise RuntimeError('Could not create isolated combat review level')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',unreal.WarCombatReviewGameMode)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets=unreal.AssetToolsHelpers.get_asset_tools()
library=unreal.MaterialEditingLibrary
def connect(source,output,target,pin):
    if not library.connect_material_expressions(source,output,target,pin):
        raise RuntimeError('Effect material connection failed: '+output+' -> '+pin)
def material_output(node,output,prop):
    if not library.connect_material_property(node,output,prop):
        raise RuntimeError('Effect material output failed: '+str(prop))
package='/Game/Imported/ThematicCombat'
path=package+'/M_ContactFilaments'
material=unreal.load_asset(path)
if not material:
    material=assets.create_asset('M_ContactFilaments',package,unreal.Material,unreal.MaterialFactoryNew())
library.delete_all_material_expressions(material)
material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('two_sided',True)
vertex=library.create_material_expression(material,unreal.MaterialExpressionVertexColor)
intensity=library.create_material_expression(material,unreal.MaterialExpressionConstant)
intensity.set_editor_property('r',12000.)
emission=library.create_material_expression(material,unreal.MaterialExpressionMultiply)
connect(vertex,'',emission,'A')
connect(intensity,'',emission,'B')
material_output(emission,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
uv=library.create_material_expression(material,unreal.MaterialExpressionTextureCoordinate)
center=library.create_material_expression(material,unreal.MaterialExpressionConstant2Vector)
center.set_editor_property('r',.5)
center.set_editor_property('g',.5)
mask=library.create_material_expression(material,unreal.MaterialExpressionSphereMask)
mask.set_editor_property('attenuation_radius',.5)
mask.set_editor_property('hardness_percent',0.)
connect(uv,'',mask,'A')
connect(center,'',mask,'B')
opacity=library.create_material_expression(material,unreal.MaterialExpressionMultiply)
connect(vertex,'A',opacity,'A')
connect(mask,'',opacity,'B')
material_output(opacity,'',unreal.MaterialProperty.MP_OPACITY)
library.recompile_material(material)
unreal.EditorAssetLibrary.save_loaded_asset(material,False)
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
reviews=[]
for index,motion in enumerate(contract['motions']):
    character=receipt['characters'][motion['character']]
    sequence=next(row['path'] for row in character['animations'] if row['sourceClipName']==motion['id'])
    actor=actors.spawn_actor_from_class(unreal.WarCombatPresentation,unreal.Vector((index%3-1)*310,(index//3)*-400,0))
    actor.set_actor_label(motion['id'])
    actor.body.set_skeletal_mesh_asset(unreal.load_asset(character['mesh']))
    actor.set_editor_property('effect_material',material)
    cue=unreal.WarCombatPresentationCue()
    cue.set_editor_property('animation',unreal.load_asset(sequence))
    cue.set_editor_property('theme',{'gold':unreal.WarMagicTheme.GOLD,'fire':unreal.WarMagicTheme.FIRE,'violet':unreal.WarMagicTheme.VIOLET}[motion['theme']])
    cue.set_editor_property('emitter_bone','vfx_weapon_tip' if motion['gesture']=='hammer' else 'hand_L' if motion['character']=='prelate' else 'hand_R')
    for field,key in [('release_seconds','release'),('trail_start','trailStart'),('trail_end','trailEnd')]: cue.set_editor_property(field,motion[key])
    cue.set_editor_property('weapon',motion['gesture']=='hammer')
    cue.set_editor_property('projectile',motion['gesture']=='bolt')
    actor.set_editor_property('cue',cue)
    if not actor.review_at_time(0): raise RuntimeError('Invalid review cue: '+motion['id'])
    reviews.append((actor,motion))
gallery_camera=actors.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(650,1150,580))
gallery_camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(gallery_camera.get_actor_location(),unreal.Vector(0,-180,100)),False)
gallery_camera.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
gallery_camera.camera_component.set_editor_property('field_of_view',55.)
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
component=capture.capture_component2d
component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,960,960,unreal.TextureRenderTargetFormat.RTF_RGBA8)
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
frames=[]
for actor,motion in reviews:
    for other,_ in reviews:
        other.body.set_visibility(other==actor,True)
        other.effects.set_visibility(other==actor,True)
    origin=actor.get_actor_location()
    camera=origin+unreal.Vector(235,480,200)
    capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,origin+unreal.Vector(0,0,105)),False,True)
    phases=[('load',motion['release']*.60),('release',motion['release']),('follow',motion['release']+.10),('recover',motion['duration']-.12),('side',motion['release']+.10)]
    if motion['id']=='prelate_sunfall':
        phases += [('side_load',.70),('side_crest',.94)]
        phases += [(view+'_%03d'%index,index/30) for view in ('motion','side_motion')
                   for index in range(round(motion['duration']*30)+1)]
    for phase,seconds in phases:
        camera=origin+(unreal.Vector(620,30,205) if phase.startswith('side') else unreal.Vector(280,580,225))
        capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,origin+unreal.Vector(0,0,105)),False,True)
        if not actor.review_at_time(seconds): raise RuntimeError('Cannot evaluate '+motion['id'])
        unreal.WarImportLibrary.prepare_preview_frame(actor.body)
        unreal.log('COMBAT_FRAME '+motion['id']+' '+phase+' '+str(actor.body.get_position())+' '+str(actor.effects.get_num_sections())+' '+str(unreal.SystemLibrary.get_component_bounds(actor.effects)))
        for _ in range(3):
            unreal.WarImportLibrary.prepare_world_preview_frame(world)
            component.capture_scene()
        filename=motion['id']+'_'+phase+'.png'
        (OUT/filename).unlink(missing_ok=True)
        unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(OUT),filename)
        if not (OUT/filename).is_file(): raise RuntimeError('Render failed: '+filename+'; use -AllowCommandletRendering')
        frames.append({'motion':motion['id'],'phase':phase,'seconds':seconds,'file':filename})
    actor.review_at_time(0)
for actor,_ in reviews:
    actor.body.set_visibility(True,True)
    actor.effects.set_visibility(True,True)
actors.destroy_actor(capture)
if not editor.save_current_level(): raise RuntimeError('Combat review level was not saved')
(OUT/'review.json').write_text(json.dumps({'map':map_path,'frames':frames,'playbackFps':30,'visualApproval':False},indent=2)+'\n')
unreal.log('COMBAT_REVIEW_RENDERED')
