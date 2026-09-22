"""Record exact, existing development resource bindings without granting release approval."""
import hashlib
import datetime
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_resources import CATALOG, validate_catalog_append
DIRECTORY = ROOT/'artifacts/unreal/world-portals'
receipt = json.loads((DIRECTORY/'build.json').read_text(encoding='utf-8'))
capital = json.loads((ROOT/'unreal/AegisWar/Content/Migration/capital-development.json').read_text(encoding='utf-8'))
content = json.loads((ROOT/'unreal/AegisWar/Content/Migration/content.json').read_text(encoding='utf-8'))
source_maps = {row['id']:row['definition'] for row in content['maps']}
expected = {}
for row in capital['gameplay']['resources']:
    expected[('aegis_capital', row['id'])] = row
for row in receipt['resources']:
    name = Path(row['model']).stem+'_0'
    expected[(row['zone'], row['id'])] = {**row,
        'mesh':row.get('mesh') or receipt.get('assetLayer', receipt['layer']).rsplit('/',1)[0]+'/Meshes/'+name+'.'+name}
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt['map']):
    raise RuntimeError('Main map unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
bindings, packages, seen = [], {}, set()
target = ROOT/'unreal/AegisWar/Content/Migration/world-visuals.json'
if target.exists():
    # This recorder owns resources; preserve exact bindings for training targets and scenery.
    previous = json.loads(target.read_text(encoding='utf-8'))
    bindings.extend(row for row in previous['bindings'] if row['purpose'] != 'resource')
    packages.update(previous['packageHashes'])
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not isinstance(actor, unreal.WarResourceNode): continue
    zone, identity, visual = [str(actor.get_editor_property(key)) for key in ('zone_id','node_id','visual_prop_id')]
    key = (zone, identity)
    if key not in expected or key in seen: raise RuntimeError('Resource has no unique previous placement receipt: '+str(key))
    seen.add(key)
    source = source_maps[zone]
    node = next(row for row in source['resourceNodes'] if row['id']==identity)
    prop = next(row for row in source['props'] if row['id']==node['visualPropId'])
    model = prop.get('model') or expected[key].get('model')
    source_file = ROOT/'public/assets/models'/model
    component = actor.static_mesh_component
    mesh = component.static_mesh
    if visual != node['visualPropId'] or visual != expected[key]['visualPropId'] or not mesh or mesh.get_path_name()!=expected[key]['mesh']:
        raise RuntimeError('Existing resource differs from its source/placement receipt: '+identity)
    materials = [component.get_material(index) for index in range(component.get_num_materials())]
    if not materials or any(material is None for material in materials): raise RuntimeError('Missing resource materials: '+identity)
    for asset in [mesh, *materials]:
        package = asset.get_path_name().split('.')[0]
        if not package.startswith('/Game/'): raise RuntimeError('Unadmitted external or primitive material/mesh')
        file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.uasset')
        packages[package] = hashlib.sha256(file.read_bytes()).hexdigest()
    bindings.append({'purpose':'resource', 'zone':zone, 'entity':identity, 'visualProp':visual,
        'sourceModel':model, 'sourceSha256':hashlib.sha256(source_file.read_bytes()).hexdigest(),
        'mesh':mesh.get_path_name(), 'materials':[m.get_path_name() for m in materials],
        'collision':str(component.get_collision_profile_name()), 'reviewState':'development'})
if seen != set(expected): raise RuntimeError('A previously working resource is absent')
catalog = {'schemaVersion':1, 'sourceContentSha256':content['source']['sha256'],
    'bindings':sorted(bindings,key=lambda row:(row['purpose'],row['zone'],row['entity'])),
    'packageHashes':packages, 'productionAccepted':False}
if target.exists() and json.loads(target.read_text(encoding='utf-8')) != catalog:
    try:
        validate_catalog_append(json.loads(target.read_text(encoding='utf-8')),catalog,json.loads(CATALOG.read_text()))
    except ValueError as error:
        (DIRECTORY/'world-visuals-conflict.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
        raise RuntimeError('Reconcile world-visuals-conflict.json; existing bindings were preserved: '+str(error)) from error
    shutil.copy2(target,DIRECTORY/('world-visuals-before-append-'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json'))
target.write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
(DIRECTORY/'world-visuals.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_WORLD_VISUAL_BINDINGS='+str(len(bindings)))
