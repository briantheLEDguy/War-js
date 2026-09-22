"""Copy and partition the owned campaign; never modify the current main map or source layer."""
import datetime
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_zones import owner_zone, validate_partition, zone_manifest, digest

directory = ROOT/'artifacts/unreal/world-portals'
receipt = json.loads((directory/'build.json').read_text())
plan = json.loads((directory/'plan.json').read_text())
if receipt.get('partitionManifest'):
    raise RuntimeError('World is already partitioned; edit a zone or explicitly rebuild a new candidate')
if hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest() != receipt['planSha256']:
    raise RuntimeError('Source plan changed')
source_maps = {}
for zone, sha in plan['sourceHashes'].items():
    file = ROOT/'public/assets/maps'/(zone+'.json')
    if hashlib.sha256(file.read_bytes()).hexdigest() != sha: raise RuntimeError('Source changed: '+zone)
    source_maps[zone] = json.loads(file.read_text())

stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
folder = '/Game/WorldRebuild/Zones_'+stamp
target = folder+'/CampaignRouting'
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
source_file = ROOT/'unreal/AegisWar/Content'/(receipt['layer'].removeprefix('/Game/')+'.umap')
source_sha = hashlib.sha256(source_file.read_bytes()).hexdigest()
copy = unreal.EditorAssetLibrary.duplicate_asset(receipt['layer'], target)
if not copy or not level.load_level(target): raise RuntimeError('Campaign copy failed')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def transform(value):
    t,r,s = value.translation, value.rotation, value.scale3d
    return [round(v, 6) for v in (t.x,t.y,t.z,r.x,r.y,r.z,r.w,s.x,s.y,s.z)]


def snapshot(actor):
    meshes = []
    for component in actor.get_components_by_class(unreal.MeshComponent):
        mesh = component.static_mesh if isinstance(component, unreal.StaticMeshComponent) else (
            component.get_skeletal_mesh_asset() if isinstance(component, unreal.SkeletalMeshComponent) else None)
        meshes.append({'class':component.get_class().get_name(),
                       'transform':transform(component.get_relative_transform()),
                       'mesh':mesh.get_path_name() if mesh else None,
                       'materials':[component.get_material(i).get_path_name() if component.get_material(i) else None
                                    for i in range(component.get_num_materials())],
                       'collision':str(component.get_collision_profile_name())})
    return {'class':actor.get_class().get_name(), 'label':actor.get_actor_label(),
            'transform':transform(actor.get_actor_transform()), 'tags':sorted(str(t) for t in actor.tags),
            'meshes':meshes}


groups = {zone['id']:[] for zone in plan['zones']}
before = {}
for actor in actors.get_all_level_actors():
    if isinstance(actor, (unreal.WorldSettings, unreal.LevelScriptActor, unreal.Brush,
                          unreal.WarZoneAnchor, unreal.WarZonePortal)): continue
    point = actor.get_actor_location()
    zone = owner_zone(plan['zones'], [point.x, point.y, point.z])
    identity = 'WarZoneObject_'+zone+'_'+actor.get_name()
    if identity in before: raise RuntimeError('Duplicate source actor identity')
    actor.tags = list(actor.tags)+[identity]
    before[identity] = snapshot(actor)
    groups[zone].append(actor)

levels, streamings = {}, []
for zone in groups:
    levels[zone] = {}
    for kind in ('Generated', 'Authored'):
        package = folder+'/'+zone+'/'+zone+'_'+kind
        streaming = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, package, False)
        if not streaming: raise RuntimeError('Could not create '+package)
        streamings.append(streaming)
        levels[zone][kind.lower()] = package
        if kind == 'Generated' and groups[zone]:
            copies = unreal.WarImportLibrary.copy_campaign_actors_to_level(groups[zone], streaming)
            if len(copies) != len(groups[zone]): raise RuntimeError('Incomplete copy: '+zone)
            for old, new in zip(groups[zone], copies):
                if snapshot(old) != snapshot(new):
                    unreal.log_error('WAR_COPY_DIFF='+json.dumps({'old':snapshot(old), 'new':snapshot(new)}))
                    raise RuntimeError('Copied actor changed: '+old.get_actor_label())
            for old in groups[zone]:
                if not actors.destroy_actor(old): raise RuntimeError('Could not remove candidate duplicate')
        unreal.EditorLevelUtils.make_level_current(streaming)
        if not level.save_current_level(): raise RuntimeError('Could not save '+package)
    unreal.log('WAR_ZONE_PARTITIONED='+zone)

after = {}
for actor in actors.get_all_level_actors():
    keys = [str(tag) for tag in actor.tags if str(tag).startswith('WarZoneObject_')]
    if keys:
        if len(keys) != 1 or keys[0] in after: raise RuntimeError('Duplicated partition identity')
        after[keys[0]] = snapshot(actor)
    if isinstance(actor, unreal.WarZoneAnchor):
        zone = str(actor.get_editor_property('zone_id'))
        actor.set_editor_property('content_levels', [] if zone == 'aegis_capital' else list(levels[zone].values()))
validate_partition(before, after)
if not level.set_current_level_by_name('CampaignRouting'): raise RuntimeError('Routing level unavailable')
# Levels are attached as siblings in the main world; nested streaming attachments are not relied on.
for streaming in streamings:
    if not unreal.EditorLevelUtils.remove_level_from_world(streaming.get_loaded_level()): raise RuntimeError('Could not detach candidate child')
if not level.save_current_level(): raise RuntimeError('Could not save routing layer')
if hashlib.sha256(source_file.read_bytes()).hexdigest() != source_sha: raise RuntimeError('Source layer was modified')
manifest = zone_manifest(plan, receipt, levels, {zone:len(rows) for zone,rows in groups.items()}, source_maps)
for zone in manifest['zones']:
    bindings = {}
    for identity, state in before.items():
        if not identity.startswith('WarZoneObject_'+zone['id']+'_'): continue
        for component in state['meshes']:
            if component['mesh']:
                key = digest({k:component[k] for k in ('mesh', 'materials', 'collision')})
                bindings[key] = {k:component[k] for k in ('mesh', 'materials', 'collision')}
    zone['nativeAssetBindings'] = list(bindings.values())
    zone['externalAuthoredCapital'] = zone['id'] == 'aegis_capital'
manifest.update(layer=target, mainMap=receipt['map'], previousLayer=receipt['layer'],
                previousLayerSha256=source_sha, planSha256=receipt['planSha256'],
                preservedActors=len(before), preservedStateSha256=digest(before))
packages = [target]+[package for row in levels.values() for package in row.values()]
manifest['packageHashes'] = {package:hashlib.sha256((ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')).read_bytes()).hexdigest()
                             for package in packages}
(directory/'partition-candidate.json').write_text(json.dumps(manifest, indent=2)+'\n')
(directory/'partition-actors.json').write_text(json.dumps(before, separators=(',', ':'))+'\n')
unreal.log('WAR_WORLD_PARTITION_READY='+str(len(before)))
