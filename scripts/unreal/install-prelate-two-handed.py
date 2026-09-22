"""Install the supplied two-handed set on the live Prelate, retaining other roles."""
import hashlib
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from prelate_two_handed import CLIPS, LIVE_ROLES, merge_bindings

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/unreal/two-handed"
(OUT / "installed.json").unlink(missing_ok=True)
receipt = json.loads((OUT / "retarget.json").read_text())
grips = json.loads((OUT / "grip-fit.json").read_text())
source = json.loads((OUT / "weapon.json").read_text())
library = unreal.EditorAssetLibrary
visual_path = "/Game/MigrationProof/Visual_civic_battle_prelate_m"
visual = unreal.load_asset(visual_path)
if not visual or str(visual.profile_key) != "civic_battle_prelate_m" or str(visual.class_id) != "battle_prelate":
    raise RuntimeError("Expected the existing Battle Prelate visual")
if visual.animation_blueprint is not None:
    raise RuntimeError("Existing animation blueprint requires explicit role integration")
mesh = unreal.load_asset(receipt["targetMesh"])
imported = {key: clip["animation"] for key, clip in receipt["clips"].items()}
for key, clip in receipt["clips"].items():
    path = ROOT / "unreal/AegisWar/AnimationImport/Two-handed" / CLIPS[key]
    if hashlib.sha256(path.read_bytes()).hexdigest() != clip["sourceSha256"]:
        raise RuntimeError("Source FBX changed since retarget: " + key)
    animation = unreal.load_asset(clip["animation"])
    if not animation or animation.get_editor_property("skeleton") != mesh.skeleton:
        raise RuntimeError("Missing or incompatible animation: " + key)
    if library.get_metadata_tag(animation, "WarPrelateGrip") != "v1":
        raise RuntimeError("Grip adaptation has not run: " + key)
existing = {str(key): value.get_path_name() for key, value in visual.imported_animations.items()}
merged = merge_bindings(existing, imported, grips)
registry_path = ROOT / "unreal/AegisWar/Content/Migration/visual-imports.json"
registry = json.loads(registry_path.read_text())
binding = next(entry for entry in registry["entries"] if entry["profileKey"] == "civic_battle_prelate_m")
backup = receipt["retargeter"].rsplit("/", 1)[0] + "/BeforeTwoHanded"
if not library.does_asset_exist(backup):
    if not library.duplicate_asset(visual_path, backup):
        raise RuntimeError("Cannot back up the original visual")
    (OUT / "original-binding.json").write_text(json.dumps(binding, indent=2) + "\n")
source_path = "artifacts/unreal/two-handed/prelate-two-handed.fbx"
if hashlib.sha256((ROOT / source_path).read_bytes()).hexdigest() != source["fbxSha256"]:
    raise RuntimeError("Grip mesh changed since import")
visual.set_editor_properties(dict(skeletal_mesh=mesh, source_model=source_path, source_sha256=source["fbxSha256"],
    idle_animation=unreal.load_asset(imported["idle"]),
    imported_animations={key: unreal.load_asset(path) for key, path in merged.items()}))
error = visual.validate_for_spawn(visual.realm)
if error != "":
    raise RuntimeError("Native spawn validation rejected the set: " + str(error))
binding.update(sourceModel=source_path, sourceSha256=source["fbxSha256"], skeletalMeshPath=mesh.get_path_name(),
    animationPaths=sorted(set(merged.values()) | {imported["idle"]}), artApproval=False, developmentOnly=True)
library.set_metadata_tag(visual, "WarPrelateTwoHanded", receipt["identity"])
if not library.save_loaded_asset(visual, False):
    raise RuntimeError("Could not save the live visual")
# Re-read at the last possible moment so independent profile imports survive.
latest = json.loads(registry_path.read_text())
latest["entries"] = [binding if row["profileKey"] == binding["profileKey"] else row for row in latest["entries"]]
temporary = registry_path.with_suffix(".twohand.tmp")
temporary.write_text(json.dumps(latest, indent=2) + "\n")
temporary.replace(registry_path)
(OUT / "installed.json").write_text(json.dumps(dict(schemaVersion=1, visual=visual_path, mesh=mesh.get_path_name(),
    liveRoles=LIVE_ROLES, registeredClips=len(CLIPS), preservedRoles=sorted(key for key in existing if key not in LIVE_ROLES and not key.startswith("two_handed_")),
    nativeSpawnValidation=True, artApproval=False, backupVisual=backup), indent=2) + "\n")
unreal.log("WAR_PRELATE_TWO_HANDED_INSTALLED")
