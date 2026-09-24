"""Inspect the saved siege map without modifying any map or review flags."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
TARGET = "/Game/Capitals/Siege/AegisCapital_Siege"
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(TARGET):
    raise RuntimeError("Siege draft is missing")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
rows = []
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
    location = actor.get_actor_location()
    rows.append({"name":actor.get_name(), "label":actor.get_actor_label(),
                 "class":actor.get_class().get_name(), "level":actor.get_outer().get_path_name(),
                 "position":[location.x,location.y,location.z],
                 "mesh":mesh.static_mesh.get_path_name() if mesh and mesh.static_mesh else None})
result = {"map":TARGET, "actors":rows}
path = ROOT / "artifacts/unreal/siege/inspection.json"
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(result,indent=2)+"\n")
unreal.log("WAR_SIEGE_INSPECTED="+str(len(rows)))
