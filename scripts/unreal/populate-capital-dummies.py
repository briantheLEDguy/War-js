"""Add six exact source training targets to owned generated capital levels."""
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from capital_training_dummies import MODELS, targets, export_model
from world_build_assets import WorldAssets, ground
from world_level_access import WorldLevelAccess
from world_actor_state import snapshot

directory = ROOT/'artifacts/unreal/capital-dummies'
directory.mkdir(parents=True, exist_ok=True)
world_dir = ROOT/'artifacts/unreal/world-portals'
build = json.loads((world_dir/'build.json').read_text())
plan = json.loads((world_dir/'plan.json').read_text())
if hashlib.sha256((world_dir/'plan.json').read_bytes()).hexdigest() != build['planSha256']:
    raise RuntimeError('World plan changed')
sources, exports = {}, {}
for zone in MODELS:
    path = ROOT/'public/assets/maps'/(zone+'.json')
    if hashlib.sha256(path.read_bytes()).hexdigest() != plan['sourceHashes'][zone]:
        raise RuntimeError('Capital source changed')
    rows, model = targets(json.loads(path.read_text()))
    sources[zone] = rows
    exports[zone] = export_model(ROOT/'public/assets/models'/model, directory)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(build['map']): raise RuntimeError('Main capital map unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
access = WorldLevelAccess(ROOT, build)
existing = {}
for actor in actors.get_all_level_actors():
    if isinstance(actor, unreal.WarEnemy):
        key = (str(actor.get_editor_property('zone_id')), str(actor.get_editor_property('enemy_id')))
        if key in existing: raise RuntimeError('Duplicate enemy identity')
        existing[key] = actor
record_file = directory/'placement.json'
catalog_path = ROOT/'unreal/AegisWar/Content/Migration/world-visuals.json'
catalog = json.loads(catalog_path.read_text())
content = json.loads((ROOT/'unreal/AegisWar/Content/Migration/content.json').read_text())
if catalog['sourceContentSha256'] != content['source']['sha256']:
    raise RuntimeError('World visual catalog is stale')
if record_file.exists():
    previous = json.loads(record_file.read_text())
    for row in previous['actors']:
        actor = existing.get((row['zone'],row['id']))
        if actor is None or snapshot(actor) != row['state']:
            raise RuntimeError('Existing training target changed; preserve owner edits')
        if row['sourceSha256'] != exports[row['zone']]['sourceSha256']:
            raise RuntimeError('Training target source changed')
        if row['binding'] not in catalog['bindings']: raise RuntimeError('Training target binding changed')
        for asset in [row['binding']['mesh'],*row['binding']['materials']]:
            package = asset.split('.')[0]
            file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.uasset')
            if hashlib.sha256(file.read_bytes()).hexdigest() != catalog['packageHashes'][package]:
                raise RuntimeError('Training target mesh/material package changed')
    if len(previous['actors']) != 6: raise RuntimeError('Incomplete target receipt')
    unreal.log('WAR_CAPITAL_DUMMIES_UNCHANGED=6')
else:
    # Validate both packages and all identities/landings before mutating saved content.
    points = {}
    for zone, rows in sources.items():
        access.select(zone)
        origin = next(z['origin'] for z in plan['zones'] if z['id']==zone)
        for row in rows:
            if (zone,row['id']) in existing or any(b['zone']==zone and b['entity']==row['id'] for b in catalog['bindings']):
                raise RuntimeError('Existing target has no owned placement receipt')
            point = unreal.Vector(origin[0]+row['z']*100, origin[1]+row['x']*100, origin[2]+row.get('y',0)*100)
            points[(zone,row['id'])] = ground(world,point,250)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    assets = WorldAssets(ROOT,'CapitalDummies_'+stamp)
    placed = []
    for zone, rows in sources.items():
        access.select(zone)
        source = exports[zone]
        mesh = assets.composite(Path(source['model']).stem,source['surface'],False)
        for row in rows:
            floor = points[(zone,row['id'])]
            actor = actors.spawn_actor_from_class(unreal.WarEnemy,floor+unreal.Vector(0,0,98))
            actor.set_editor_property('zone_id',zone); actor.set_editor_property('enemy_id',row['id'])
            actor.set_actor_label(row['name']+' - '+zone)
            actor.tags = ['WarCampaignWorld','WarTrainingDummy','WarZoneObject_'+zone+'_Enemy_'+row['id']]
            component = actor.get_editor_property('training_mesh')
            component.set_static_mesh(mesh)
            center, extent, _ = unreal.SystemLibrary.get_component_bounds(component)
            if not 100 < extent.z*2 < 260 or abs(center.z-extent.z-floor.z) > 10:
                raise RuntimeError('Dummy model scale/grounding failed: '+row['id'])
            materials = [component.get_material(i) for i in range(component.get_num_materials())]
            if not materials or any(m is None for m in materials): raise RuntimeError('Dummy material missing')
            for asset in [mesh,*materials]:
                package = asset.get_path_name().split('.')[0]
                file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.uasset')
                catalog['packageHashes'][package] = hashlib.sha256(file.read_bytes()).hexdigest()
            binding = {'purpose':'training_dummy','zone':zone,'entity':row['id'],'visualProp':row['id'],
                'sourceModel':source['model'],'sourceSha256':source['sourceSha256'],'mesh':mesh.get_path_name(),
                'materials':[m.get_path_name() for m in materials], 'collision':str(component.get_collision_profile_name()),
                'reviewState':'development'}
            catalog['bindings'].append(binding)
            placed.append({'zone':zone,'id':row['id'],'sourceSha256':source['sourceSha256'],
                           'state':snapshot(actor),'binding':binding})
    access.save(set(sources))
    shutil.copy2(catalog_path,directory/('world-visuals-before-'+stamp+'.json'))
    catalog_path.write_text(json.dumps(catalog,indent=2)+'\n')
    record_file.write_text(json.dumps({'schemaVersion':1,'actors':placed,'visualApproved':False},indent=2)+'\n')
    unreal.log('WAR_CAPITAL_DUMMIES_ADDED=6')

for zone, rows in sources.items():
    for row in rows:
        entry = {'zone':zone,'id':row['id'],'kind':'training-dummy','model':exports[zone]['model'],
                 'behavior':'passive-strike-target','acceptance':'development-only'}
        existing_entry = next((g for g in build['gameplay'] if g['zone']==zone and g['id']==row['id']),None)
        if existing_entry is not None and existing_entry != entry: raise RuntimeError('Gameplay receipt conflict')
        if existing_entry is None: build['gameplay'].append(entry)
build['runtimeTraversalVerified'] = False
(world_dir/'build.json').write_text(json.dumps(build,indent=2)+'\n')
