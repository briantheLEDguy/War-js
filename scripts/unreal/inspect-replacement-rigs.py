"""Record native bind hierarchy before applying any rig-unit correction."""
import json
from pathlib import Path
import unreal
root = Path(__file__).resolve().parents[2]
rows = []
for entry in json.loads((root/"unreal/AegisWar/Content/Migration/visual-imports.json").read_text())["entries"]:
    mesh = unreal.load_asset(entry["skeletalMeshPath"])
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    rows.append(dict(profile=entry["profileKey"],mesh=entry["skeletalMeshPath"],bones=names))
(root/"artifacts/unreal/animation-replacement/native-rigs.json").write_text(json.dumps(rows,indent=2)+"\n")
