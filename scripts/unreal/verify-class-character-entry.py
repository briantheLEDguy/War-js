"""Fresh Editor: exercise all 48 main-roster selections through ordinary login RPCs.

Two temporary PIE sessions keep realm identity fixed. Maps and character records
are not saved; the receipt checks real possession, mesh identity and animation.
"""
import configparser
import json
from pathlib import Path
import sys
import time
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from class_character_native import ROOT, OUT, read, sha

installed = read(OUT / 'installed.json')
records = read(OUT / 'model-sources.json')['profiles']
groups = [[key for key, row in records.items() if (row['race'] in ('empire', 'dwarf', 'high_elf')) == aegis]
          for aegis in (True, False)]
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
config = configparser.ConfigParser(strict=False)
config.read(ROOT / 'unreal/AegisWar/Config/DefaultEngine.ini')
if not levels.load_level(config['/Script/EngineSettings.GameMapsSettings']['GameDefaultMap']):
    raise RuntimeError('The configured main startup world is unavailable')
state = dict(group=0, index=0, phase='starting', started=time.monotonic(), rows=[], possessed=None)
output = OUT / 'runtime-entry.json'


def receipt(passed, detail):
    output.write_text(json.dumps(dict(passed=passed, detail=detail, profiles=state['rows'],
        installedSha256=sha(OUT / 'installed.json'), graphicalAcceptance=False,
        method='Ordinary ServerCreateDevelopmentCharacter, two temporary realm-fixed PIE sessions'), indent=2)+'\n', encoding='utf-8')


def finish(passed, detail):
    receipt(passed, detail)
    unreal.unregister_slate_post_tick_callback(handle)
    levels.editor_request_end_play()
    unreal.EditorPythonScripting.set_keep_python_script_alive(False)


def tick(_delta):
    try:
        now = time.monotonic()
        if now-state['started'] > 120:
            finish(False, 'Timed out: ' + state['phase'])
            return
        world = editor.get_game_world()
        if state['phase'] == 'between-realms':
            if world: return
            state.update(index=0, phase='starting', started=now)
            levels.editor_request_begin_play()
            return
        if not world: return
        player = unreal.GameplayStatics.get_player_controller(world, 0)
        if not player: return
        key = groups[state['group']][state['index']]
        row = records[key]
        pawn = player.get_controlled_pawn()
        if state['phase'] in ('starting', 'next-body'):
            if pawn:
                finish(False, 'A pawn existed before this character submission')
                return
            player.call_method('ServerCreateDevelopmentCharacter', args=('Body Review', row['race'], row['classId'], row['bodyVariant']))
            state.update(phase='awaiting-possession', started=now, possessed=None)
            return
        if not pawn: return
        if state['possessed'] is None:
            state['possessed'] = now
            state['initialZ'] = pawn.get_actor_location().z
        if now-state['possessed'] < 1.5: return
        component = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
        expected = unreal.load_asset(installed['profiles'][row['profileKey']]['visual'])
        mesh = component.get_editor_property('skeletal_mesh_asset')
        if mesh != expected.skeletal_mesh or not component.get_anim_instance():
            finish(False, 'The selected own body or native animation instance is missing: ' + key)
            return
        if pawn.get_actor_location().z < state['initialZ']-150:
            finish(False, 'Character fell through the arrival floor: ' + key)
            return
        frontend_class = unreal.load_class(None, '/Script/AegisWar.WarFrontendWidget')
        if any(widget.is_in_viewport() for widget in unreal.WidgetLibrary.get_all_widgets_of_class(world, frontend_class, False)):
            finish(False, 'Login did not close after possession: ' + key)
            return
        state['rows'].append(dict(profile=key, playableProfile=row['profileKey'], mesh=mesh.get_path_name(),
                                  animationInstance=component.get_anim_instance().get_class().get_path_name(), passed=True))
        receipt(False, 'running')
        unreal.log('WAR_CLASS_ENTRY_VERIFIED=' + key)
        player.un_possess()
        pawn.destroy_actor()
        state['index'] += 1
        state.update(phase='next-body', started=now, possessed=None)
        if state['index'] == len(groups[state['group']]):
            if state['group'] == 1:
                finish(len(state['rows']) == 48, 'All 48 main-roster bodies possessed through ordinary development character entry')
            else:
                state.update(group=1, phase='between-realms')
                levels.editor_request_end_play()
    except Exception as error:
        finish(False, str(error))


receipt(False, 'running')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
handle = unreal.register_slate_post_tick_callback(tick)
levels.editor_request_begin_play()
