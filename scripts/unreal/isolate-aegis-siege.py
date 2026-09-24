"""Give the siege its own city geometry; retain every source campaign package."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/unreal/siege"
TARGET = "/Game/Capitals/Siege/AegisCapital_Siege"
GEOMETRY = "/Game/Capitals/Siege/AegisCityGeometry"
inspection = json.loads((OUTPUT / "inspection.json").read_text())
packages = sorted({row["level"].split(".")[0] for row in inspection["actors"]})
sources = [p for p in packages if "/aegis_capital/aegis_capital_Authored_" in p]
if len(sources) != 1:
    raise RuntimeError("Expected one inspected authored capital layer")

def file(package):
    if not package.startswith("/Game/"):
        raise RuntimeError("Only project content packages are supported")
    path = (ROOT / "unreal/AegisWar/Content" / (package[6:] + ".umap")).resolve()
    path.relative_to(ROOT / "unreal/AegisWar/Content")
    return path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

source_hashes = {p:digest(file(p)) for p in packages if p != TARGET}
if unreal.EditorAssetLibrary.does_asset_exist(GEOMETRY):
    raise RuntimeError("Owned siege geometry already exists; preserve edits and inspect the isolation receipt")
shutil.copy2(file(TARGET), OUTPUT / "before-isolation.umap")
if not unreal.EditorAssetLibrary.duplicate_asset(sources[0], GEOMETRY):
    raise RuntimeError("Capital geometry duplication failed")
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(GEOMETRY):
    raise RuntimeError("Cannot load duplicated city geometry")
removed = []
gameplay = (unreal.WarEnemy, unreal.WarQuestNpc, unreal.WarCityNpc, unreal.WarResourceNode,
            unreal.WarCraftingStation, unreal.WarZonePortal, unreal.WarZoneAnchor)
for actor in list(actors.get_all_level_actors()):
    if actor.get_outer().get_path_name().split(".")[0] != GEOMETRY:
        continue
    if isinstance(actor, gameplay):
        removed.append(actor.get_actor_label())
        if not actors.destroy_actor(actor):
            raise RuntimeError("Failed to remove copied campaign actor")
if not levels.save_current_level():
    raise RuntimeError("Cannot save isolated city geometry")
if not levels.load_level(TARGET):
    raise RuntimeError("Cannot load siege definition")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
for package in packages:
    if package == TARGET:
        continue
    streaming = unreal.GameplayStatics.get_streaming_level(world, package)
    if streaming and not unreal.EditorLevelUtils.remove_level_from_world(streaming.get_loaded_level()):
        raise RuntimeError("Cannot unlink campaign layer: " + package)
if not unreal.EditorLevelUtils.add_level_to_world(world, GEOMETRY, unreal.LevelStreamingAlwaysLoaded):
    raise RuntimeError("Cannot attach private siege geometry")
unreal.GameplayStatics.flush_level_streaming(world)
actual_levels = {actor.get_outer().get_path_name().split(".")[0] for actor in actors.get_all_level_actors()}
if actual_levels != {TARGET, GEOMETRY}:
    raise RuntimeError("Unexpected remaining streaming levels: " + str(actual_levels))
if not levels.set_current_level_by_name("AegisCapital_Siege") or not levels.save_current_level():
    raise RuntimeError("Cannot save isolated siege world")
if any(digest(file(package)) != sha for package, sha in source_hashes.items()):
    raise RuntimeError("A source package changed unexpectedly; inspect preserved hashes")
result = {"schemaVersion":1,"map":TARGET,"geometry":GEOMETRY,"source":sources[0],
          "sourcePackagesUnchanged":True,"sourceHashes":source_hashes,"removedCopiedGameplayActors":removed,
          "levels":sorted(actual_levels),"nativePlayable":False}
(OUTPUT / "isolation.json").write_text(json.dumps(result,indent=2)+"\n")
unreal.log("WAR_SIEGE_ISOLATED="+str(len(removed)))
