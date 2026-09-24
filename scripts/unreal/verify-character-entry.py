"""Run with UnrealEditor-Cmd -nullrhi -ExecutePythonScript=<absolute path>.

Exercise the ordinary capital login RPC in a fresh standalone PIE session without
saving maps or creating a persistent character. The JSON receipt is authoritative;
editor process exit alone is not evidence of success.
WAR_ENTRY_CAREER selects battle_prelate (default), sunfire_templar or ember_arcanist.
"""
import configparser
import json
import os
import time
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
CAREER = os.environ.get('WAR_ENTRY_CAREER', 'battle_prelate')
PROFILES = {'battle_prelate': 'civic_battle_prelate_m',
            'sunfire_templar': 'civic_sunfire_templar_m',
            'ember_arcanist': 'civic_ember_arcanist_m'}
if CAREER not in PROFILES:
    raise ValueError('Entry verification requires an installed Aegis career')
OUTPUT = ROOT / 'artifacts/unreal/character-entry' / (
    'runtime-' + CAREER + '.json' if 'WAR_ENTRY_CAREER' in os.environ else 'runtime.json')
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps({'passed': False, 'status': 'running'}))
config = configparser.ConfigParser(strict=False)
config.read(ROOT / 'unreal/AegisWar/Config/DefaultEngine.ini')
map_path = config['/Script/EngineSettings.GameMapsSettings']['GameDefaultMap']
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if not levels.load_level(map_path):
    raise RuntimeError('Could not load the configured capital')
lights = {a.get_actor_label(): a.light_component.get_editor_property('forward_shading_priority')
          for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
          if isinstance(a, unreal.DirectionalLight)}
assert lights.get('Aegis workbench sun') == 1 and lights.get('Crownward soft sky fill') == 0, lights
state = {'started': time.monotonic(), 'submitted': False, 'possessed_at': None}


def finish(passed, detail, **evidence):
    OUTPUT.write_text(json.dumps({'passed': passed, 'detail': detail, 'map': map_path,
                                 'career': CAREER, 'lightPriorities': lights,
                                 'graphicalAcceptance': False, **evidence}, indent=2))
    unreal.unregister_slate_post_tick_callback(handle)
    levels.editor_request_end_play()
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)


def tick(_delta):
    try:
        if time.monotonic() - state['started'] > 60:
            finish(False, 'Timed out waiting for ordinary character entry')
            return
        world = editor.get_game_world()
        if not world:
            return
        player = unreal.GameplayStatics.get_player_controller(world, 0)
        if not player:
            return
        if not state['submitted']:
            if player.get_controlled_pawn():
                finish(False, 'A pawn was present before character submission')
                return
            player.call_method('ServerCreateDevelopmentCharacter',
                               args=('Entry Check', 'empire', CAREER, 'm'))
            state['submitted'] = True
            return
        pawn = player.get_controlled_pawn()
        if not pawn:
            return
        if state['possessed_at'] is None:
            state['possessed_at'] = time.monotonic()
            state['initial_z'] = pawn.get_actor_location().z
        if time.monotonic() - state['possessed_at'] < 3:
            return
        frontend_class = unreal.load_class(None, '/Script/AegisWar.WarFrontendWidget')
        widgets = unreal.WidgetLibrary.get_all_widgets_of_class(world, frontend_class, False)
        if any(widget.is_in_viewport() for widget in widgets):
            finish(False, 'Login stayed open after possession')
            return
        mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent).get_editor_property('skeletal_mesh_asset')
        location = pawn.get_actor_location()
        expected=unreal.load_asset('/Game/MigrationProof/Visual_' + PROFILES[CAREER])
        if not mesh or not expected or mesh!=expected.skeletal_mesh:
            finish(False, 'The selected equipped character mesh was not installed')
            return
        if location.z < state['initial_z'] - 150:
            finish(False, 'The character fell through the arrival floor')
            return
        finish(True, 'Ordinary entry possessed the selected equipped character and closed login',
               mesh=mesh.get_path_name(), pawn=pawn.get_path_name(),
               location=[location.x, location.y, location.z])
    except Exception as error:
        finish(False, str(error))


unreal.EditorPythonScripting.set_keep_python_script_alive(True)
handle = unreal.register_slate_post_tick_callback(tick)
levels.editor_request_begin_play()
