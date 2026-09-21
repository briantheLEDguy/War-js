"""Copy a bounded house-kit pilot and dependencies from private staging.

Original package paths are preserved so material references remain valid. The
destination is explicitly Git-ignored; no downloaded Blueprint is executed.
"""
import hashlib
import json
from pathlib import Path
import shutil
import unreal

ROOT = Path(__file__).resolve().parents[2]
project = Path(unreal.Paths.project_dir()).resolve()
if project.name != "CityKitStaging":
    raise RuntimeError("Run in CityKitStaging")
output = ROOT / "artifacts/unreal/licensed-kits/capital-kit-staged.json"
output.unlink(missing_ok=True)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
prefix = "/Game/Medieval_Environment/"
names = {"SM_MH_02_House_01", "SM_MH_02_House_02", "SM_MH_02_House_03",
         "SM_MH_02_House_04a", "SM_MH_02_House_04b", "SM_MH_02_House_04c",
         "SM_MH_02_Stone_Floor_01", "SM_MH_02_Stone_Wall_01",
         "SM_MH_02_Stone_Wall_Window_01", "SM_MH_02_Stone_Wall_Door_01",
         "SM_MH_02_Stone_Wall_Half_V_01", "SM_MH_02_Stone_Wall_Buttress_01",
         "SM_MH_02_Stone_Stairs_02"}
selected = [data for data in registry.get_assets_by_path(prefix, recursive=True)
            if str(data.asset_name) in names and str(data.asset_class_path.asset_name) == "StaticMesh"]
if len(selected) != len(names):
    raise RuntimeError("Pilot mesh selection is missing or ambiguous")
pending = [str(data.package_name) for data in selected]
packages = set()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True, include_searchable_names=False,
    include_soft_management_references=False, include_hard_management_references=False)
while pending:
    package = pending.pop()
    if package in packages or package.startswith(("/Engine/", "/Script/")):
        continue
    if not package.startswith(prefix):
        raise RuntimeError("Unreviewed kit dependency: " + package)
    packages.add(package)
    pending.extend(str(path) for path in registry.get_dependencies(package, options))
destination = ROOT / "unreal/AegisWar/Content"
files = []
for package in sorted(packages):
    relative = package.removeprefix("/Game/") + ".uasset"
    source = project / "Content" / relative
    target = destination / relative
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Refusing to overwrite changed kit asset: " + relative)
    files.append((source, target, relative, digest))
for source, target, relative, digest in files:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(source, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Kit changed during staging: " + relative)
output.write_text(json.dumps({"schemaVersion": 1,
    "meshes": [str(data.package_name) + "." + str(data.asset_name) for data in selected],
    "files": [{"path": relative, "sha256": digest} for _, _, relative, digest in files],
    "runtimeApproved": False, "licenseReviewed": False}, indent=2) + "\n")
unreal.log("WAR_CAPITAL_KIT_STAGED=" + str(output))
