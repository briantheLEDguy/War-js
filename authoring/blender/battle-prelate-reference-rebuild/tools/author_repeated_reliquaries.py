"""Record two explicit placements of the newly authored reliquary geometry.

These are copies of inspectable source patches, not generated shapes. The rear
badge and belt buckle use fixed transforms selected against the reference.
"""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/"source/medallion.json").read_text())
parts=[]
PLACEMENTS=[
    ("rear", "back", "upper_chest", [0,.175,1.500], [-.88,-.88,1.02], 180,
     {"reliquary_recessed_backing","reliquary_outer_rim","reliquary_inner_beaded_border","reliquary_skull","reliquary_dental_crowns","reliquary_rim_fasteners","reliquary_lower_pendant"}),
    ("belt", "waist", "hips", [0,-.177,1.171], [.55,.55,.55], 0,
     {"reliquary_recessed_backing","reliquary_outer_rim","reliquary_skull","reliquary_dental_crowns"})]
for prefix,slot,bone,center,scale,rotation,selected in PLACEMENTS:
    for original in source["parts"]:
        if original["id"] not in selected:
            continue
        part=copy.deepcopy(original)
        part["id"]=prefix+"_"+part["id"]
        part["slot"],part["rigid_bone"]=slot,bone
        transforms=[]
        for old in part.get("instances",[part["transform"]]):
            # Composition of the recorded assembly transform with each recorded
            # local instance transform; no vertices or faces are synthesized.
            transforms.append({
                "location":[center[i]+scale[i]*(old["location"][i]-[0,-.216,1.409][i]) for i in range(3)],
                "rotation_degrees":[old["rotation_degrees"][0],(-1 if rotation else 1)*old["rotation_degrees"][1],old["rotation_degrees"][2]+rotation],
                "scale":[abs(scale[i])*old["scale"][i] for i in range(3)]})
        part["transform"]=transforms[0]
        if len(transforms)>1:
            part["instances"]=transforms
        else:
            part.pop("instances",None)
        parts.append(part)
document={"schema_version":1,"component":"repeated_reliquaries","reference_notes":[
    "Explicit copies of newly authored medallion patches only; no previous failed geometry reused.",
    "Rear reliquary position follows the central back ornament; belt skull is independently scaled to the belt width.",
    "Each copied patch and its final vertex coordinates, face topology and instance transforms remain inspectable in this source record."],"parts":parts}
(ROOT/"source/repeated_reliquaries.json").write_text(json.dumps(document,indent=2)+"\n")
