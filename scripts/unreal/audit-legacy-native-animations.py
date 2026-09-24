"""Inventory legacy animation packages and their actual native referencers."""
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import OUT
registry=unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
keep=set()
sets=json.loads((OUT/'retarget.json').read_text())
keep.update(p.split('.')[0] for p in sets['sources'].values())
keep.add('/Game/Characters/AnimationReplacement/'+sets['identity']+'/IK_Source')
for profile in sets['profiles'].values():
    keep.add(profile['retargeter'].split('.')[0]); keep.add(profile['retargeter'].split('/RTG_Target')[0]+'/IK_Target')
    keep.update(c['animation'].split('.')[0] for c in profile['clips'].values())
for profile in json.loads((OUT/'presentations.json').read_text())['profiles'].values():
    keep.update(p.split('.')[0] for p in profile['bindings'].values())
classes={'AnimSequence','AnimBlueprint','BlendSpace','BlendSpace1D','AnimMontage','IKRetargeter','IKRigDefinition'}
rows=[]
for data in registry.get_all_assets():
    path=str(data.package_name); kind=str(data.asset_class_path.asset_name)
    if not path.startswith('/Game/') or kind not in classes: continue
    asset=data.get_asset()
    row=dict(path=path,kind=kind,keep=path in keep,referencers=sorted(str(n) for n in registry.get_referencers(data.package_name,unreal.AssetRegistryDependencyOptions())))
    if kind=='AnimSequence':
        row['skeleton']=asset.get_editor_property('skeleton').get_path_name()
        try: row['sources']=list(asset.get_editor_property('asset_import_data').extract_filenames())
        except Exception: row['sources']=[]
    rows.append(row)
(OUT/'native-animation-removal-plan.json').write_text(json.dumps(rows,indent=2)+'\n')
unreal.log('WAR_NATIVE_ANIMATION_INVENTORY='+str(len(rows)))
