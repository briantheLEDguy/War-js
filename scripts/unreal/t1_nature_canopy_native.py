"""Exact staged installed-oak bindings in fresh private T1 candidates; no license or gameplay approval."""
import copy,json
from pathlib import Path
import unreal
from t1_materials import sha
from t1_nature_kit import select_nature_meshes
from t1_nature_canopy import MAPPING,canopy_transform,canopy_identities


def nature_sources(root):
    base=root/'artifacts/unreal/licensed-kits';inventory=base/'nature-kit-inventory.json';staged=base/'nature-kit-staged.json'
    source=json.loads(inventory.read_text());receipt=json.loads(staged.read_text());rows=select_nature_meshes(source)
    if sha(inventory)!=receipt['inventorySha256'] or receipt['meshes']!=rows:raise RuntimeError('Installed nature selection differs from exact inventory')
    files={p.relative_to(root).as_posix():sha(p) for p in (inventory,staged)}
    for row in receipt['files']:
        file=root/'unreal/AegisWar/Content'/row['path']
        if sha(file)!=row['sha256']:raise RuntimeError('Staged nature package changed: '+str(file))
        files[file.relative_to(root).as_posix()]=row['sha256']
    return {r['path'].rsplit('.',1)[-1]:r for r in rows},files


def adapt_nature_canopies(assets,states,sources):
    if not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'):raise RuntimeError('Installed nature study requires fresh private T1 atmosphere candidates')
    expected=canopy_identities(states);result=copy.deepcopy(states);adapted=[]
    for label,state in result.items():
        if state['kind']!='mesh':continue
        name=state['mesh'].rsplit('/',1)[-1].split('.')[0]
        if name not in MAPPING:continue
        recipe=sources[MAPPING[name]];original=unreal.load_asset(state['mesh']);replacement=unreal.load_asset(recipe['path'])
        if not isinstance(original,unreal.StaticMesh) or not isinstance(replacement,unreal.StaticMesh):raise RuntimeError('Canopy study requires exact static mesh bindings')
        old=original.get_bounds();new=replacement.get_bounds();bounds=lambda b:[[b.origin.x,b.origin.y,b.origin.z],[b.box_extent.x,b.box_extent.y,b.box_extent.z]]
        if bounds(new)!=[recipe['boundsOrigin'],recipe['boundsExtent']]:raise RuntimeError('Staged canopy native bounds differ from inspection')
        materials=[slot.material_interface.get_path_name() if slot.material_interface else None for slot in replacement.get_editor_property('static_materials')]
        if materials!=recipe['materials'] or replacement.get_num_lods()!=recipe['lodCount']:raise RuntimeError('Staged canopy materials or LOD inventory changed')
        placement=canopy_transform(bounds(old),bounds(new),state['scale'],state['location'],state['rotation'])
        before=dict(mesh=state['mesh'],materials=state['materials'],scale=state['scale'],location=state['location'])
        state.update(mesh=replacement.get_path_name(),materials=materials,scale=placement['scale'],location=placement['location'])
        state['tags']+=['WarT1PrivateInstalledNatureStudy']
        adapted.append(dict(id=label,original=before,mesh=state['mesh'],materials=materials,placement=placement,lodCount=recipe['lodCount'],sourceGeometryPreserved=False,collisionAccepted=False))
    if tuple(sorted(row['id'] for row in adapted))!=expected:raise RuntimeError('Installed oak study changed its exact source canopy identities')
    return result,dict(actors=adapted,sourceCanopyIds=expected,meshes=3,installedSourcePackagesPreserved=True,sourceGeometryPreserved=False,licenseReviewed=False,distributionApproved=False,collisionAccepted=False,appearanceApproved=False,performanceAccepted=False)
