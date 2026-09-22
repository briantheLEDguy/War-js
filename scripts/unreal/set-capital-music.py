"""Run in the open official capital: configure and save its default music."""
import configparser
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
config = configparser.ConfigParser(strict=False)
config.read(ROOT / 'unreal/AegisWar/Config/DefaultEngine.ini')
map_path = config['/Script/EngineSettings.GameMapsSettings']['GameDefaultMap']
content_level = map_path
world_receipt = ROOT/'artifacts/unreal/world-portals/build.json'
if world_receipt.exists():
    build = json.loads(world_receipt.read_text())
    if build.get('map') == map_path and build.get('partitionManifest'):
        manifest = json.loads((world_receipt.parent/build['partitionManifest']).read_text())
        capital = next(row for row in manifest['zones'] if row['id']=='aegis_capital')
        if capital.get('capitalExtracted'): content_level = capital['levels']['authored']
sound_path = '/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/Rec_9-21-2026-8-50-35-PM-Unreal-Loop'
label = 'Aegis capital background music'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = editor.get_editor_world()
if not world or world.get_path_name().split('.')[0] != map_path:
    raise RuntimeError('Open the official capital before configuring its music')
if editor.get_game_world():
    raise RuntimeError('Stop Play In Editor before configuring music')
sound = unreal.load_asset(sound_path)
if not isinstance(sound, unreal.SoundWave):
    raise RuntimeError('The imported capital loop is missing or is not a SoundWave')
matches = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
if len(matches) > 1 or (matches and not isinstance(matches[0], unreal.AmbientSound)):
    raise RuntimeError('Ambiguous capital music actor; resolve duplicates first')

with unreal.ScopedEditorTransaction('Set default Aegis capital music'):
    sound.modify()
    sound.set_editor_property('looping', True)
    sound.set_editor_property('virtualization_mode', unreal.VirtualizationMode.PLAY_WHEN_SILENT)
    # Music must unload with the capital instead of persisting into other zones.
    if matches and matches[0].get_outer().get_path_name().split('.')[0] != content_level:
        raise RuntimeError('Capital music is in an unexpected level; reconcile before editing')
    if not levels.set_current_level_by_name(content_level.rsplit('/', 1)[-1]):
        raise RuntimeError('Could not select the authored capital level')
    actor = matches[0] if matches else actors.spawn_actor_from_class(unreal.AmbientSound, unreal.Vector())
    if not actor:
        raise RuntimeError('Could not create the capital music actor')
    actor.modify()
    actor.set_actor_label(label)
    component = actor.get_component_by_class(unreal.AudioComponent)
    component.modify()
    component.set_sound(sound)
    component.set_editor_property('auto_activate', True)
    component.set_editor_property('allow_spatialization', False)
    component.set_editor_property('override_attenuation', True)
    attenuation = unreal.SoundAttenuationSettings()
    attenuation.set_editor_property('attenuate', False)
    attenuation.set_editor_property('spatialize', False)
    component.set_editor_property('attenuation_overrides', attenuation)
    component.set_editor_property('volume_multiplier', 0.5)

assert sound.get_editor_property('looping')
assert component.get_editor_property('sound') == sound
assert component.get_editor_property('auto_activate')
assert not component.get_editor_property('allow_spatialization')
assert not component.get_editor_property('attenuation_overrides').get_editor_property('attenuate')
assert len([a for a in actors.get_all_level_actors() if a.get_actor_label() == label]) == 1
if not unreal.EditorAssetLibrary.save_loaded_asset(sound):
    raise RuntimeError('Could not save the looping SoundWave')
if not levels.save_current_level():
    raise RuntimeError('Could not save the capital music actor')
receipt = ROOT / 'artifacts/unreal/capital-music.json'
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps({'map': map_path, 'contentLevel': content_level, 'sound': sound_path, 'actor': label,
    'looping': True, 'autoActivate': True, 'spatialized': False, 'attenuated': False,
    'volume': 0.5, 'saved': True, 'listeningVerified': False}, indent=2))
unreal.log('WAR_CAPITAL_MUSIC_SAVED')
