"""Stage exact installed nature-package bytes into ignored private content; no approval or Blueprint execution."""
import hashlib,json,shutil,sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from t1_nature_kit import select_nature_meshes,nature_dependencies
project=Path(unreal.Paths.project_dir()).resolve()
if project.name!='CityKitStaging':raise RuntimeError('Nature staging requires isolated CityKitStaging')
receipt_file=ROOT/'artifacts/unreal/licensed-kits/nature-kit-inventory.json';receipt=json.loads(receipt_file.read_text());selected=select_nature_meshes(receipt)
registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
options=unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
roots=[r['path'].split('.',1)[0] for r in selected];packages=nature_dependencies(roots,lambda p:[str(q) for q in registry.get_dependencies(p,options)])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();destination=ROOT/'unreal/AegisWar/Content';files=[]
for row in selected:
 source=project/'Content'/(row['path'].split('.',1)[0].removeprefix('/Game/')+'.uasset')
 if sha(source)!=row['sourceSha256']:raise RuntimeError('Installed nature mesh changed after inspection')
for package in packages:
 relative=package.removeprefix('/Game/');found=False
 for suffix in ('.uasset','.uexp','.ubulk'):
  source=project/'Content'/(relative+suffix)
  if not source.exists():continue
  found=True;target=destination/(relative+suffix);digest=sha(source)
  if target.exists() and sha(target)!=digest:raise RuntimeError('Preserve changed private destination: '+str(target))
  files.append((source,target,digest))
 if not found:raise RuntimeError('Missing installed dependency package: '+package)
for source,target,digest in files:
 target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():shutil.copy2(source,target)
 if sha(source)!=digest or sha(target)!=digest:raise RuntimeError('Nature package bytes changed during staging')
output=ROOT/'artifacts/unreal/licensed-kits/nature-kit-staged.json';output.write_text(json.dumps(dict(inventorySha256=sha(receipt_file),meshes=selected,packages=packages,files=[dict(path=t.relative_to(destination).as_posix(),sha256=h) for _,t,h in files],runtimeApproved=False,licenseReviewed=False,distributionApproved=False,activeMapsChanged=False),indent=2)+'\n')
unreal.log('WAR_NATURE_KIT_STAGED='+str(len(packages)))
