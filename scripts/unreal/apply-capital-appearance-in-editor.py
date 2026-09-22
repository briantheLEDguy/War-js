"""Optional owner-run editor action: tint current city without reloading or saving it."""
import datetime
from pathlib import Path
import sys
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capital_appearance import SOURCE_MAP, apply_appearance
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_path_name().split('.')[0] != SOURCE_MAP:
    raise RuntimeError('Open the main Crownward workbench before applying appearance')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if any(a.get_actor_label()=='Crownward soft sky fill' for a in actors.get_all_level_actors()):
    raise RuntimeError('Appearance already applied; edit its lights/material instances instead')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
with unreal.ScopedEditorTransaction('Apply Crownward appearance'):
    apply_appearance(unreal, actors, '/Game/Capitals/crownward/Appearance_'+stamp)
unreal.log('Crownward appearance applied to current actors. Existing edits retained; review before saving the level.')
