"""Matching campaign/siege city views from the installed shared levels. No map saves."""
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import source_plan

plan = source_plan(ROOT)
out = ROOT / 'artifacts/unreal/shared-cities/views'
out.mkdir(parents=True, exist_ok=True)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
views = [('city', (-37000, -31000, 23500), (12000, 0, 5200)),
         ('avenue', (-11000, 0, 230), (20000, 0, 6800)),
         ('castle', (11000, -8000, 10600), (17800, 0, 5100))]
for mode, package in [('campaign', plan['campaignMap']), ('siege', '/Game/Capitals/Siege/AegisCapital_Siege')]:
    if not levels.load_level(package):
        raise RuntimeError('Missing city consumer: ' + mode)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    if mode == 'campaign':
        # The Editor loads every zone; runtime admits only the current city's layers.
        keep = set(plan['cities'][0]['sceneryLevels'] + plan['cities'][0]['gameplayLevels']) | {package}
        for level in list(unreal.EditorLevelUtils.get_levels(world)):
            name = level.get_outer().get_path_name().split('.')[0]
            if name not in keep:
                if not unreal.EditorLevelUtils.remove_level_from_world(level):
                    raise RuntimeError('Cannot isolate the current city for capture')
    if not unreal.WarZoneLightingSubsystem.preview_world(world, 'aegis_capital', unreal.Vector(*plan['cities'][0]['origin'])):
        raise RuntimeError('Cannot apply the shared city lighting profile')
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
    component = capture.capture_component2d
    target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.texture_target = target
    component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    component.capture_every_frame = False
    component.capture_on_movement = False
    component.always_persist_rendering_state = True
    component.post_process_blend_weight = 0
    component.fov_angle = 65
    for name, eye, target_position in views:
        capture.set_actor_location_and_rotation(unreal.Vector(*eye),
            unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target_position)), False, True)
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        for _ in range(8):
            component.capture_scene()
            unreal.WarImportLibrary.prepare_world_preview_frame(world)
        unreal.RenderingLibrary.export_render_target(world, target, str(out), mode + '-' + name + '.png')
    actors.destroy_actor(capture)
(out / 'receipt.json').write_text(json.dumps(dict(cityRevision=plan['cities'][0]['revision'],
    campaignMap=plan['campaignMap'], views=views, visualApproved=False), indent=2) + '\n')
