"""Measure built Unreal collision against browser-derived capital ground fixtures."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/capitals/aegis_capital"
output = directory / "collision-proof.json"
output.unlink(missing_ok=True)
fixtures = json.loads((directory / "collision-fixtures.json").read_text())
receipt = json.loads((directory / "terrain-import.json").read_text())
source_hash = hashlib.sha256((ROOT / "public/assets/maps/aegis_capital.json").read_bytes()).hexdigest()
if fixtures["sourceSha256"] != source_hash or receipt["sourceSha256"] != source_hash:
    raise RuntimeError("Stale capital collision inputs")
if hashlib.sha256((directory / "terrain.json").read_bytes()).hexdigest() != receipt["terrainInputSha256"]:
    raise RuntimeError("Terrain changed after native construction")
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt["map"]):
    raise RuntimeError("Capital workbench map is missing")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.WarImportLibrary.prepare_preview_frame(None)
results = []
for point in fixtures["points"]:
    x, y = point["sourceZ"] * 100, point["sourceX"] * 100
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 100000), unreal.Vector(x, y, -100000),
        unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
    hit = result
    if not isinstance(hit, unreal.HitResult):
        raise RuntimeError(f"Capital collision missed: {point}")
    parts = hit.to_tuple()
    if not parts[0]:
        raise RuntimeError(f"Capital collision did not block: {point}")
    impact = parts[5]
    if abs(impact.z - point["expectedHeightCm"]) > 0.2:
        raise RuntimeError(f"Capital collision height mismatch: {point}, actual {impact.z}")
    results.append({**point, "actualHeightCm": impact.z})
output.write_text(json.dumps({"schemaVersion": 1, "sourceSha256": source_hash, "passed": True,
    "map": receipt["map"], "samples": results, "toleranceCm": 0.2, "fullTraversalAccepted": False}, indent=2) + "\n")
unreal.log("WAR_CAPITAL_COLLISION_PASSED=" + str(output))
