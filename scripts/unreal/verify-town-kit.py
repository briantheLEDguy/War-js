"""Fresh-process structural verification of a private static town adaptation."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
project = Path(unreal.Paths.project_dir()).resolve()
if project.name != "CityKitStaging":
    raise RuntimeError("Verify in the private staging project")
directory = ROOT / "artifacts/unreal/licensed-kits"
result_path = directory / "town-kit-reload.json"
result_path.unlink(missing_ok=True)
receipt = json.loads((directory / "town-kit-adaptation.json").read_text())
for relative, expected in receipt["sourceFiles"].items():
    path = project / "Content/Medieval_Mod_Town" / relative
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Source changed since adaptation: " + relative)
mesh = unreal.load_asset(receipt["asset"])
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Adaptation did not reload")
materials = sorted({slot.material_interface.get_path_name() for slot in mesh.static_materials
                    if slot.material_interface})
triangles = [mesh.get_num_triangles(index) for index in range(mesh.get_num_lods())]
if materials != receipt["materials"] or triangles != receipt["trianglesPerLod"]:
    raise RuntimeError("Material or LOD geometry changed on reload")
if mesh.get_editor_property("body_setup").get_editor_property("collision_trace_flag") != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
    raise RuntimeError("Interior triangle collision configuration did not persist")
result_path.write_text(json.dumps({"asset": receipt["asset"], "structuralReloadPassed": True,
    "materials": len(materials), "trianglesPerLod": triangles,
    "collisionTraversalVerified": False, "runtimeApproved": False, "visualApproved": False}, indent=2) + "\n")
unreal.log("WAR_TOWN_KIT_RELOAD_VERIFIED")
