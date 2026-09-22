"""Install exact catalog-reviewed resource visuals without changing source gameplay."""
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_resources import resource_bindings, CATALOG
from world_level_access import WorldLevelAccess
from world_build_assets import WorldAssets, ground
from world_static import read_glb, combine_parts

directory = ROOT/'artifacts/unreal/world-portals'
receipt = json.loads((directory/'build.json').read_text())
plan = json.loads((directory/'plan.json').read_text())
registry = json.loads((ROOT/'public/assets/models/asset-index.json').read_text())['staticProps']
reviews = json.loads((ROOT/'migration/visual-reviews.json').read_text())['reviews']
if hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest()!=receipt['planSha256']:
    raise RuntimeError('Stale campaign source plan')
ready, pending, definitions = [], [], {}
for zone in plan['zones']:
    if zone['id']=='aegis_capital': continue
    file = ROOT/'public/assets/maps'/(zone['id']+'.json')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=plan['sourceHashes'][zone['id']]:
        raise RuntimeError('Source map changed')
    rows, missing = resource_bindings(json.loads(file.read_text()),registry)
    ready.extend(rows); pending.extend(missing); definitions[zone['id']] = zone
for row in ready:
    if hashlib.sha256((ROOT/'public/assets/models'/row['model']).read_bytes()).hexdigest()!=row['sourceSha256']:
        raise RuntimeError('Resource model changed')
    if any(r['status']=='rejected' and r['sourceSha256']==row['sourceSha256'] for r in reviews):
        raise RuntimeError('Resource source failed visual review')

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(receipt['map']): raise RuntimeError('Main map unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
access = WorldLevelAccess(ROOT,receipt)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = actors.get_all_level_actors()
previous = {(r['zone'],r['id']):r for r in receipt.get('resources',[])}
native, additions = {}, []
for row in ready:
    identity = (row['zone'],row['node']['id'])
    tag = 'WarWorldObject_'+row['zone']+'_'+row['prop']['id']+'_0'
    matches = [a for a in all_actors if tag in [str(t) for t in a.tags]]
    if len(matches)>1: raise RuntimeError('Ambiguous resource scenery: '+tag)
    if matches:
        actor = matches[0]
        old = previous.get(identity)
        if not old or not isinstance(actor,unreal.WarResourceNode):
            raise RuntimeError('Existing scenery has no managed resource receipt: '+tag)
        expected = old.get('mesh') or (receipt.get('assetLayer',receipt['layer']).rsplit('/',1)[0]
            +'/Meshes/'+Path(row['model']).stem+'_0.'+Path(row['model']).stem+'_0')
        mesh = actor.static_mesh_component.static_mesh
        if (not mesh or mesh.get_path_name()!=expected or str(actor.get_editor_property('node_id'))!=identity[1]
                or str(actor.get_editor_property('zone_id'))!=identity[0]
                or str(actor.get_editor_property('visual_prop_id'))!=row['prop']['id']):
            raise RuntimeError('Existing resource binding changed: '+tag)
        native[identity] = actor
    elif identity in previous:
        raise RuntimeError('A previously installed resource disappeared: '+tag)
    else: additions.append(row)

assets = WorldAssets(ROOT,'Resources_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
meshes = {}
for row in additions:
    # Check and back up every destination before generating or placing content.
    access.select(row['zone'])
for row in additions:
    if row['model'] not in meshes:
        data = read_glb(ROOT/'public/assets/models'/row['model'])
        meshes[row['model']] = assets.composite(Path(row['model']).stem,combine_parts(data['parts']),False)
for row in additions:
    access.select(row['zone'])
    node, prop = row['node'], row['prop']
    origin = definitions[row['zone']]['origin']
    point = unreal.Vector(origin[0]+node['z']*100,origin[1]+node['x']*100,origin[2]+node.get('y',0)*100)
    floor = point if prop.get('heightMode')=='absolute' else ground(world,point,5000)
    mesh = meshes[row['model']]
    scale = float(prop.get('scale',1))
    if not math.isfinite(scale) or scale<=0: raise RuntimeError('Invalid source resource scale')
    actor = actors.spawn_actor_from_class(unreal.WarResourceNode,floor,
        unreal.Rotator(yaw=prop.get('rotY',0)*180/math.pi))
    if not actor: raise RuntimeError('Resource placement failed')
    actor.set_actor_label(node['label'])
    actor.tags = ['WarCampaignWorld','WarCampaignResource',
        'WarWorldObject_'+row['zone']+'_'+prop['id']+'_0',
        'WarZoneObject_'+row['zone']+'_Resource_'+node['id'], 'WarModelSha256_'+row['sourceSha256']]
    actor.set_folder_path('Campaign/'+row['zone']+'/Resources')
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    actor.set_actor_scale3d(unreal.Vector(scale,scale,scale))
    for key,value in {'zone_id':row['zone'],'node_id':node['id'],'visual_prop_id':prop['id']}.items():
        actor.set_editor_property(key,value)
    center, extent, _ = unreal.SystemLibrary.get_component_bounds(actor.static_mesh_component)
    actor.set_actor_location(floor+unreal.Vector(0,0,floor.z-(center.z-extent.z)),False,True)
    native[(row['zone'],node['id'])] = actor
if additions: access.save({row['zone'] for row in additions})

installed = []
for row in ready:
    actor = native[(row['zone'],row['node']['id'])]
    component = actor.static_mesh_component
    installed.append({'zone':row['zone'],'id':row['node']['id'],'visualPropId':row['prop']['id'],
        'model':row['model'],'sourceSha256':row['sourceSha256'],'mesh':component.static_mesh.get_path_name(),
        'materials':[component.get_material(i).get_path_name() for i in range(component.get_num_materials())],
        'collision':str(component.get_collision_profile_name()),'sourceCatalogSha256':hashlib.sha256(CATALOG.read_bytes()).hexdigest()})
receipt['resources'] = installed
receipt['pendingResources'] = pending
if additions:
    ids = {(r['zone'],r['prop']['id']) for r in additions}
    receipt['pendingScenery'] = [r for r in receipt['pendingScenery'] if (r['zone'],r['id']) not in ids]
    receipt['scenery'] += [{'zone':r['zone'],'id':r['prop']['id'],'parts':1,'resourceVisual':True} for r in additions]
    receipt['runtimeTraversalVerified'] = False
(directory/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
unreal.log('WAR_WORLD_RESOURCES_ENABLED='+str(len(ready))+' ADDED='+str(len(additions)))
