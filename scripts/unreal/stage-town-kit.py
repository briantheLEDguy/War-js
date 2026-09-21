"""Copy a reviewed static town adaptation and dependencies from private staging.

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
output = ROOT / "artifacts/unreal/licensed-kits/town-kit-staged.json"
output.unlink(missing_ok=True)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
receipt = json.loads((ROOT / "artifacts/unreal/licensed-kits/town-kit-adaptation.json").read_text())
reload = json.loads((ROOT / "artifacts/unreal/licensed-kits/town-kit-reload.json").read_text())
if reload["asset"] != receipt["asset"] or not reload["structuralReloadPassed"]:
    raise RuntimeError("Current adaptation has no structural reload evidence")
asset = receipt["asset"]
package_name = asset.split(".")[0]
if not package_name.startswith("/Game/WarKitAdaptations/SM_Town_Building_"):
    raise RuntimeError("Unexpected adaptation identity")
pending = [package_name]
packages = set()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True, include_searchable_names=False,
    include_soft_management_references=False, include_hard_management_references=False)
while pending:
    package = pending.pop()
    if package in packages or package.startswith(("/Engine/", "/Script/")):
        continue
    if package != package_name and not package.startswith("/Game/Medieval_Mod_Town/"):
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
    "meshes": [asset],
    "files": [{"path": relative, "sha256": digest} for _, _, relative, digest in files],
    "runtimeApproved": False, "licenseReviewed": False}, indent=2) + "\n")
unreal.log("WAR_TOWN_KIT_STAGED=" + str(output))
