"""Verify UV/weight-preserving tangent preparation on the actual baked modules."""
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from tessellate_runtime import prepare_tangents

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "battle_prelate_game_master.blend"))
results = []
for lod in (0, 1, 2):
    for obj in bpy.data.collections[f"RUNTIME_LOD{lod}"].objects:
        if obj.type != 'MESH':
            continue
        def corners(mesh):
            uv = mesh.uv_layers.active
            return {(loop.vertex_index, tuple(uv.data[loop.index].uv)) for loop in mesh.loops}
        previous = corners(obj.data)
        result = prepare_tangents(obj)
        assert corners(obj.data) == previous, f"UV corners changed: {obj.name}"
        assert all(abs(loop.tangent.length - 1) < 1e-4 for loop in obj.data.loops), obj.name
        assert prepare_tangents(obj)["authored_ngons_tessellated"] == 0, "Preparation is not idempotent"
        results.append(dict(result, lod=lod, slot=obj["slot"], uv_corners_unchanged=True))
assert len(results) == 33
path = ROOT / "review/tessellation_probe.json"
path.write_text(json.dumps({"status": "passed", "modules": results}, indent=2) + "\n")
print("TESSELLATION_PROBE_PASSED", len(results))
