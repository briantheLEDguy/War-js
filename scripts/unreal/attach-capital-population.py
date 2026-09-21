"""Owner-run editor script: attach population without reloading or saving the city."""
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_population import POPULATION_MAP, official_map
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_path_name().split('.')[0] != official_map():
    raise RuntimeError('Open the official FinalAppearance city first')
if not unreal.EditorAssetLibrary.does_asset_exist(POPULATION_MAP): raise RuntimeError('Build the population layer first')
if not unreal.GameplayStatics.get_streaming_level(world,POPULATION_MAP):
    with unreal.ScopedEditorTransaction('Attach capital population'):
        world.modify()
        unreal.EditorLevelUtils.add_level_to_world(world,POPULATION_MAP,unreal.LevelStreamingAlwaysLoaded)
unreal.log('Capital population attached (or already present). Review and save your city when ready.')
