"""Stage only recipe-selected purchased static meshes and dependency closures."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import recipes, digest, admit_mesh


def main():
    project=Path(unreal.Paths.project_dir()).resolve()
    if project.name!='CityKitStaging': raise RuntimeError('Use private kit staging')
    directory=ROOT/'artifacts/unreal/capital-expansion'
    inventory=json.loads((directory/'kit-inventory.json').read_text())
    names={p['mesh'] for r in recipes() for p in r['components'] if p['mesh'].startswith('SM_')}
    names.update(('SM_Barrel','SM_Crate','SM_Bench','SM_Market_Table','SM_Bookshelf','SM_Torch'))
    names.update(('SM_Bed_Matress','SM_Bed_Pillow','SM_Bed_Sheet'))
    selected={}
    for name in sorted(names):
        selected[name]=admit_mesh(inventory,name)
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    options=unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
        include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
    pending=[r['path'].split('.')[0] for r in selected.values()]; packages=set()
    while pending:
        package=pending.pop()
        if package in packages or package.startswith(('/Engine/','/Script/')): continue
        if not package.startswith(('/Game/Medieval_Environment/','/Game/Medieval_Mod_Town/')):
            raise RuntimeError('Unreviewed dependency: '+package)
        packages.add(package)
        pending.extend(str(p) for p in registry.get_dependencies(package,options))
    files=[]
    for package in sorted(packages):
        relative=package.removeprefix('/Game/')+'.uasset'
        source=project/'Content'/relative; target=ROOT/'unreal/AegisWar/Content'/relative
        sha=hashlib.sha256(source.read_bytes()).hexdigest()
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
            raise RuntimeError('Preserve changed destination: '+relative)
        files.append((source,target,relative,sha))
    for source,target,relative,sha in files:
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): shutil.copyfile(source,target)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=sha or hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
            raise RuntimeError('Source changed during staging: '+relative)
    receipt={'schemaVersion':1,'recipesSha256':digest(recipes()),'meshes':selected,
             'files':[{'path':r,'sha256':s} for _,_,r,s in files],
             'licenseReviewed':False,'runtimeApproved':False}
    (directory/'staged.json').write_text(json.dumps(receipt,indent=2)+'\n')
    unreal.log('WAR_EXPANSION_STAGED='+str(len(selected)))


main()
