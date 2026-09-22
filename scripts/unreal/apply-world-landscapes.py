"""Install complete authored landscape sectors into the first pair's generated levels."""
import datetime
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_build_assets import WorldAssets
from world_level_access import WorldLevelAccess
from world_landscapes import surface_kind

directory = ROOT/'artifacts/unreal/world-portals'
input_dir = directory/'landscapes'
receipt = json.loads((directory/'build.json').read_text())
plan = json.loads((input_dir/'plan.json').read_text())
world_plan = json.loads((directory/'plan.json').read_text())
if not receipt.get('partitionManifest'): raise RuntimeError('Partition the world before installing landscapes')


def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest()


plan_sha = sha(input_dir/'plan.json')
if receipt.get('landscapePlanSha256'):
    if receipt['landscapePlanSha256'] != plan_sha: raise RuntimeError('Landscape inputs changed; reconcile existing zone work first')
    manifest = json.loads((directory/receipt['partitionManifest']).read_text())
    for zone in manifest['zones']:
        if not zone.get('landscape'): continue
        package = zone['levels']['generated']
        if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')) != manifest['packageHashes'][package]:
            raise RuntimeError('Zone was edited after landscape installation; preserve and reconcile changes: '+zone['id'])
        for row in zone['landscape']['surfaces']:
            if not unreal.EditorAssetLibrary.does_asset_exist(row['mesh']): raise RuntimeError('Landscape mesh is missing: '+row['mesh'])
    unreal.log('WAR_LANDSCAPES_ALREADY_INSTALLED')
else:
    if sha(ROOT/'public/assets/models/asset-index.json') != plan['registrySha256']: raise RuntimeError('Asset registry changed')
    inputs = []
    for zone in plan['zones']:
        if sha(ROOT/'public/assets/maps'/(zone['id']+'.json')) != zone['sourceSha256']: raise RuntimeError('Zone source changed')
        for chunk in zone['chunks']:
            file = input_dir/chunk['file']
            if sha(file) != chunk['sha256'] or sha(ROOT/'public/assets/models'/chunk['model']) != chunk['sourceSha256']:
                raise RuntimeError('Terrain model changed')
            data = json.loads(file.read_text())
            for part in data['parts']:
                if surface_kind(part) != part['kind']: raise RuntimeError('Terrain collision metadata changed')
            inputs.append((zone['id'],chunk,data))
    collection = 'Landscape_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    assets = WorldAssets(ROOT,collection)
    surfaces = []
    for zone,chunk,data in inputs:
        for part in data['parts']:
            material_key = hashlib.sha256(json.dumps(part['material'],sort_keys=True).encode()).hexdigest()[:20]
            material = assets.material(material_key,part['material'])
            key = chunk['id']+'_'+str(part['index'])
            mesh = assets.mesh(key,part,material,part['kind']=='ground')
            surfaces.append((zone,chunk,part,mesh))
        unreal.log('WAR_LANDSCAPE_IMPORTED='+chunk['id'])
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(receipt['map']): raise RuntimeError('Main map unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_subsystem.get_all_level_actors()
    access = WorldLevelAccess(ROOT,receipt)
    replaced, placed = {}, []
    for zone in plan['zones']:
        identity = zone['id']
        old = [a for a in all_actors if a.get_actor_label() in (identity,identity+'_roads')
               and 'WarCampaignWorld' in [str(t) for t in a.tags] and isinstance(a,unreal.StaticMeshActor)]
        if len(old) != 2: raise RuntimeError('Expected exactly the generated ground and road surfaces: '+identity)
        replaced[identity] = old
        access.select(identity)
    origins = {z['id']:z['origin'] for z in world_plan['zones']}
    for zone,chunk,part,mesh in surfaces:
        access.select(zone)
        origin = origins[zone]
        position = unreal.Vector(origin[0]+chunk['z']*100,origin[1]+chunk['x']*100,origin[2])
        actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor,position)
        key = chunk['id']+'_'+str(part['index'])
        actor.set_actor_label(key+' '+part['kind'])
        actor.tags = ['WarCampaignWorld','WarAuthoredLandscape','WarZoneObject_'+zone+'_Landscape_'+key]
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name('BlockAll' if part['kind']=='ground' else 'NoCollision')
        actor.static_mesh_component.set_editor_property('cast_shadow',False)
        actor.set_folder_path('World/'+zone+'/Landscape')
        placed.append({'zone':zone,'id':key,'kind':part['kind'],'mesh':mesh.get_path_name(),
                       'sourceModel':chunk['model'],'sourceSha256':chunk['sourceSha256']})
    for old_actors in replaced.values():
        for actor in old_actors:
            if not actor_subsystem.destroy_actor(actor): raise RuntimeError('Could not remove superseded generated surface')
    access.save(set(replaced))
    # Update coverage without implying visual, gameplay or native LOD acceptance.
    for zone in access.manifest['zones']:
        rows = [row for row in placed if row['zone']==zone['id']]
        if rows:
            zone['landscape'] = {'sectors':16,'surfaces':rows,'lodsAccepted':False,'visualApproved':False}
    (directory/receipt['partitionManifest']).write_text(json.dumps(access.manifest,indent=2)+'\n')
    receipt.update(landscapePlanSha256=plan_sha,landscapeSurfaces=placed,runtimeTraversalVerified=False)
    (directory/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
    unreal.log('WAR_LANDSCAPES_INSTALLED='+str(len(placed)))
