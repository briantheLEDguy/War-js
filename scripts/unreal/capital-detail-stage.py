"""Inspect and privately stage authored street fixtures; never execute kit Blueprints."""
import hashlib
import json
from pathlib import Path
import shutil
import unreal

ROOT = Path(__file__).resolve().parents[2]
project = Path(unreal.Paths.project_dir()).resolve()
if project.name != 'CityKitStaging':
    raise RuntimeError('Run in the isolated CityKitStaging project')
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
prefix = '/Game/Medieval_Mod_Town/'
names = {'SM_Torch', 'SM_Wood_Plank_Pillar'}
selected = [a for a in registry.get_assets_by_path(prefix, recursive=True)
            if str(a.asset_name) in names and str(a.asset_class_path.asset_name) == 'StaticMesh']
if len(selected) != len(names):
    raise RuntimeError('Missing or ambiguous authored fixtures')
pending = [str(a.package_name) for a in selected]
packages = set()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True, include_searchable_names=False,
    include_soft_management_references=False, include_hard_management_references=False)
while pending:
    package = pending.pop()
    if package in packages or package.startswith(('/Engine/', '/Script/')):
        continue
    if not package.startswith(prefix):
        raise RuntimeError('Unreviewed dependency: ' + package)
    packages.add(package)
    pending.extend(str(p) for p in registry.get_dependencies(package, options))
files = []
for package in sorted(packages):
    relative = package.removeprefix('/Game/') + '.uasset'
    source = project / 'Content' / relative
    target = ROOT / 'unreal/AegisWar/Content' / relative
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Preserve changed target: ' + relative)
    files.append((source, target, relative, digest))
rows = []
for asset in selected:
    mesh = asset.get_asset()
    bounds = mesh.get_bounds()
    materials = [str(s.material_interface.get_path_name()) if s.material_interface else None
                 for s in mesh.get_editor_property('static_materials')]
    if not all(materials):
        raise RuntimeError('Missing authored fixture material')
    rows.append({'path': mesh.get_path_name(), 'origin': [bounds.origin.x,bounds.origin.y,bounds.origin.z],
                 'extent': [bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z], 'materials': materials,
                 'lodCount': mesh.get_num_lods()})
for source, target, relative, digest in files:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(source, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Stage verification failed')
output = ROOT / 'artifacts/unreal/licensed-kits/capital-detail-staged.json'
output.write_text(json.dumps({'schemaVersion': 1, 'meshes': rows,
    'files': [{'path': p, 'sha256': h} for _, _, p, h in files],
    'runtimeApproved': False, 'licenseReviewed': False}, indent=2) + '\n')
unreal.log('WAR_CAPITAL_DETAIL_STAGED=' + str(output))
