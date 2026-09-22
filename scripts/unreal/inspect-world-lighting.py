"""Render each native zone profile and verify previews leave saved packages untouched."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_actor_state import snapshot
directory=ROOT/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'build.json').read_text())
manifest=json.loads((directory/receipt['partitionManifest']).read_text())
packages=[receipt['map'],*manifest['packageHashes']]


def hashes():
    return {p:hashlib.sha256((ROOT/'unreal/AegisWar/Content'/(p.removeprefix('/Game/')+'.umap')).read_bytes()).hexdigest()
            for p in packages}


before=hashes()
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt['map']):
    raise RuntimeError('Saved main map unavailable')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
profiles=json.loads(unreal.WarZoneLightingSubsystem.describe_profiles())
if sorted(p['zone'] for p in profiles['profiles'])!=sorted(receipt['zones']):
    raise RuntimeError('Lighting profiles must match all 32 campaign zones')
anchors={str(a.get_editor_property('zone_id')):a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)}
authored=[a for a in actors.get_all_level_actors() if isinstance(a,(unreal.DirectionalLight,unreal.SkyLight,
          unreal.ExponentialHeightFog,unreal.SkyAtmosphere,unreal.PostProcessVolume))]
authored_before={a.get_path_name():snapshot(a) for a in authored}
capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
component=capture.capture_component2d
component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,960,600,unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame=False
component.capture_on_movement=False
component.always_persist_rendering_state=True
component.fov_angle=75
component.post_process_blend_weight=0
output=directory/'lighting'
output.mkdir(exist_ok=True)
for profile in profiles['profiles']:
    identity=profile['zone']; anchor=anchors[identity]
    if not unreal.WarZoneLightingSubsystem.preview_world(world,identity,anchor.get_editor_property('zone_origin')):
        raise RuntimeError('Lighting preview failed: '+identity)
    # A grounded approach view, rather than only an aerial beauty shot.
    point=anchor.get_actor_location()
    hit=unreal.SystemLibrary.line_trace_single(world,point+unreal.Vector(0,0,100000),point-unreal.Vector(0,0,100000),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[anchor],unreal.DrawDebugTrace.NONE,True)
    if not hit or not hit.to_tuple()[0]: raise RuntimeError('No player-view ground: '+identity)
    point=hit.to_tuple()[5]+unreal.Vector(0,0,170)
    center=anchor.get_editor_property('zone_origin')+unreal.Vector(0,0,point.z)
    if (center-point).length()<100: center=point+unreal.Vector(1000,0,0)
    capture.set_actor_location_and_rotation(point,unreal.MathLibrary.find_look_at_rotation(point,center),False,True)
    for _ in range(8):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),identity+'.png')
if not unreal.WarZoneLightingSubsystem.preview_world(world,'aegis_capital',unreal.Vector()): raise RuntimeError('Capital restoration failed')
if authored_before!={a.get_path_name():snapshot(a) for a in authored}:
    raise RuntimeError('Lighting previews changed authored environment settings')
if hashes()!=before: raise RuntimeError('Lighting preview changed saved map packages')
profiles.update(packageHashes=before,capturedZones=sorted(anchors),authoredLightingRestored=True,visualApproved=False)
(directory/'lighting-verification.json').write_text(json.dumps(profiles,indent=2)+'\n')
unreal.log('WAR_ZONE_LIGHTING_VERIFIED='+str(len(profiles['profiles'])))
