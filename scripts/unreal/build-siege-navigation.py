"""Build and probe navigation in the isolated siege, without granting review flags."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/unreal/siege"
TARGET = "/Game/Capitals/Siege/AegisCapital_Siege"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(TARGET):
    raise RuntimeError("Create and isolate the siege map first")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
battlefields = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarSiegeBattlefield)]
if len(battlefields) != 1:
    raise RuntimeError("Expected one siege definition")
battlefield = battlefields[0]
if not levels.set_current_level_by_name("AegisCapital_Siege"):
    raise RuntimeError("Cannot select the owned siege persistent level")
if not unreal.WarSiegeAuthoringLibrary.build_navigation(world, unreal.Vector(3000,0,3500), unreal.Vector(25000,18000,6000)):
    raise RuntimeError("Navigation build could not start")
points = list(battlefield.get_editor_property("objectives")) + list(battlefield.get_editor_property("optional_objectives")) + list(battlefield.get_editor_property("team_spawns"))
report = {"map":TARGET, "busy":unreal.WarSiegeAuthoringLibrary.navigation_busy(world),
          "probe":unreal.WarSiegeAuthoringLibrary.probe_navigation(world, points),
          "traversalReviewed":False}
report["anchorsReachable"] = len(points) == 17 and all("projected=1 connected=1" in line for line in report["probe"].splitlines())
if report["busy"]:
    raise RuntimeError("Navigation is still building; do not save incomplete navigation")
if not levels.save_current_level():
    raise RuntimeError("Cannot save siege navigation")
(OUTPUT / "navigation.json").write_text(json.dumps(report, indent=2)+"\n")
unreal.log("WAR_SIEGE_NAVIGATION " + json.dumps(report))
if not report["anchorsReachable"]:
    raise RuntimeError("A siege anchor is not reachable; inspect navigation.json")
