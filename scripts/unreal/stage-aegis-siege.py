"""Create an isolated, deliberately launch-blocked siege authoring map.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>. Never promotes
animation, navigation or visual approval. Does not modify the selected capital.
"""
import json
import re
import sys
from pathlib import Path
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capital_geography import point

ROOT = Path(__file__).resolve().parents[2]
TARGET = "/Game/Capitals/Siege/AegisCapital_Siege"
OUTPUT = ROOT / "artifacts/unreal/siege"
OUTPUT.mkdir(parents=True, exist_ok=True)
config = (ROOT / "unreal/AegisWar/Config/DefaultEngine.ini").read_text()
source = re.search(r"^GameDefaultMap=(/Game/Capitals/crownward/[A-Za-z0-9_/]+)\s*$", config, re.M)
if not source:
    raise RuntimeError("A configured Crownward capital is required as the source.")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET):
    raise RuntimeError("Siege draft already exists; preserve authoring edits and inspect it in the Editor.")

world = unreal.EditorAssetLibrary.duplicate_asset(source.group(1), TARGET)
if not world:
    raise RuntimeError("Capital duplication failed; no source map was changed.")
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(TARGET):
    raise RuntimeError("Could not load the isolated siege draft.")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
battlefield = actors.spawn_actor_from_class(unreal.WarSiegeBattlefield, unreal.Vector())
battlefield.set_actor_label("Bastion siege definition — authoring pending")
battlefield.tags = ["WarAegisSiegeDefinitionV1"]

def vectors(rows):
    return [unreal.Vector(*row) for row in rows]

# Source road positions and modular castle floor positions; they remain a draft
# until collision, door clearance and navigation are checked in the native map.
lower = [point({"x": x, "z": z}, 10) for x, z in [(0, -116), (0, -10), (0, 119), (0, 136)]]
battlefield.set_editor_property("objectives", vectors(lower + [[15600,-1200,4210], [16400,1200,4210], [17100,0,4210], [18500,0,4210]]))
battlefield.set_editor_property("optional_objectives", vectors([point({"x":34,"z":-79},10), [16300,-2200,4210], [18000,650,4210]]))
battlefield.set_editor_property("team_spawns", vectors([point({"x":-48,"z":58},10), point({"x":0,"z":-158},10), [18800,2400,4210], [14000,-2400,4210], [20200,0,4210], [16500,0,4210]]))
battlefield.set_editor_property("traversal_reviewed", False)
battlefield.set_editor_property("equipped_roster_reviewed", False)
settings = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
settings.set_editor_property("default_game_mode", unreal.WarSiegeGameMode)

inventory = []
for asset_path in unreal.EditorAssetLibrary.list_assets("/Game/MigrationProof", recursive=True, include_folder=False):
    if "/Visual_" not in asset_path:
        continue
    visual = unreal.load_asset(asset_path)
    if not isinstance(visual, unreal.WarCharacterVisualDefinition):
        continue
    inventory.append({"asset": asset_path, "profile": str(visual.get_editor_property("profile_key")),
                      "career": str(visual.get_editor_property("class_id")), "realm": str(visual.get_editor_property("realm"))})

if not levels.save_current_level():
    raise RuntimeError("Could not save the isolated siege draft.")
report = {"schemaVersion": 1, "sourceMap": source.group(1), "siegeMap": TARGET,
          "draftCreated": True, "nativePlayable": False, "visualApproval": False,
          "availableProofVisuals": inventory,
          "blockers": ["Bind reviewed tank/healer/damage visuals for both realms and distinct encounter visuals.",
                       "Remove inherited campaign actors/streaming population in the isolated map, without editing shared source sublevels.",
                       "Author gate/defense props and verify escort routes, chamber clearance, spawn separation and navigation.",
                       "Complete equipped roster review and actual three-stage multiplayer playtests."]}
(OUTPUT / "authoring.json").write_text(json.dumps(report, indent=2) + "\n")
unreal.log("WAR_SIEGE_DRAFT " + json.dumps(report))
