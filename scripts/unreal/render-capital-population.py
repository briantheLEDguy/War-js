import json,sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from capital_population import official_map,POPULATION_MAP
(ROOT/'artifacts/unreal/population/render.json').unlink(missing_ok=True)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(official_map())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not unreal.GameplayStatics.get_streaming_level(world,POPULATION_MAP):
    unreal.EditorLevelUtils.add_level_to_world(world,POPULATION_MAP,unreal.LevelStreamingAlwaysLoaded)
unreal.GameplayStatics.flush_level_streaming(world)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# Game nameplates initialize in BeginPlay; hide editor-only default text in model captures.
for actor in actors.get_all_level_actors():
 if isinstance(actor,unreal.WarCityNpc):
  text=actor.get_component_by_class(unreal.TextRenderComponent)
  if text: text.set_visibility(False)
# Temporary inspection fill is never saved; these images review characters, not city lighting.
fill=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,20000),unreal.Rotator(pitch=-40,yaw=120))
fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fill.light_component.set_intensity(12500)
fill.light_component.set_editor_property('atmosphere_sun_light',False)
fill.light_component.set_cast_shadows(False)
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
c=capture.capture_component2d
c.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
c.capture_every_frame=False;c.capture_on_movement=False;c.always_persist_rendering_state=True;c.fov_angle=65
c.post_process_blend_weight=0
r=json.loads((ROOT/'artifacts/unreal/population/population-build.json').read_text())
for district in ['gateward','cinderbank','lantern_quays','bellfound','crownwatch']:
 row=next(a for a in r['actors'] if a['district']==district)
 x,y,z=row['position'];center=unreal.Vector(x,y,z+100)
 eye=None
 for dx,dy in [(500,500),(-500,500),(500,-500),(-500,-500),(350,0),(-350,0),(0,350),(0,-350)]:
  candidate=unreal.Vector(x+dx,y+dy,z+170)
  obstruction=unreal.SystemLibrary.line_trace_single(world,center,candidate,unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE)
  if not obstruction:
   eye=candidate
   break
 if eye is None: raise RuntimeError('No clear inspection camera for '+district)
 capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,center),False,True)
 for _ in range(5):
  unreal.WarImportLibrary.prepare_world_preview_frame(world);c.capture_scene()
 output=ROOT/'artifacts/unreal/population'/(district+'.png')
 output.unlink(missing_ok=True)
 unreal.RenderingLibrary.export_render_target(world,c.texture_target,str(output.parent),output.name)
 if not output.exists() or output.stat().st_size<1000:
  raise RuntimeError('District image was not rendered; use -AllowCommandletRendering: '+district)
(ROOT/'artifacts/unreal/population/render.json').write_text(json.dumps({'map':official_map(),'population':POPULATION_MAP,'temporaryInspectionFillLux':12500,'savedLightingChanged':False,'views':5}))
