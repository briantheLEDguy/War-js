"""Read-only native asset checks; run in a separate Python commandlet."""
import configparser
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
config = configparser.ConfigParser(strict=False)
config.read(ROOT / 'unreal/AegisWar/Config/DefaultEngine.ini')
map_path = config['/Script/EngineSettings.GameMapsSettings']['GameDefaultMap']
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(map_path)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
music = [a for a in actors if a.get_actor_label() == 'Aegis capital background music']
assert len(music) == 1 and isinstance(music[0], unreal.AmbientSound)
content_level = map_path
world_receipt = ROOT/'artifacts/unreal/world-portals/build.json'
if world_receipt.exists():
    build = json.loads(world_receipt.read_text())
    if build.get('map') == map_path and build.get('partitionManifest'):
        manifest = json.loads((world_receipt.parent/build['partitionManifest']).read_text())
        capital = next(row for row in manifest['zones'] if row['id']=='aegis_capital')
        if capital.get('capitalExtracted'): content_level = capital['levels']['authored']
assert music[0].get_outer().get_path_name().split('.')[0] == content_level
audio = music[0].get_component_by_class(unreal.AudioComponent)
sound = audio.get_editor_property('sound')
assert isinstance(sound, unreal.SoundWave)
assert sound.get_name() == 'Rec_9-21-2026-8-50-35-PM-Unreal-Loop'
assert sound.get_editor_property('looping')
assert sound.get_editor_property('virtualization_mode') == unreal.VirtualizationMode.PLAY_WHEN_SILENT
assert audio.get_editor_property('auto_activate')
assert not audio.get_editor_property('allow_spatialization')
assert audio.get_editor_property('override_attenuation')
assert not audio.get_editor_property('attenuation_overrides').get_editor_property('attenuate')
assert not audio.get_editor_property('attenuation_overrides').get_editor_property('spatialize')
assert audio.get_editor_property('volume_multiplier') == 0.5
(ROOT / 'artifacts/unreal/capital-music-verification.json').write_text(json.dumps({
    'map': map_path, 'contentLevel': content_level, 'savedAssetChecksPassed': True, 'musicActors': len(music),
    'listeningVerified': False}, indent=2))
unreal.log('WAR_CAPITAL_MUSIC_VERIFIED')
