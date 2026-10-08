"""Reassemble measured home roofs in fresh copies of frozen atmosphere candidates."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_home_shell import refit_shell, part_transform, seam_probes
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory, clone

DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
package_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.umap')
asset_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
parent = json.loads((DIRECTORY/'atmosphere-latest.json').read_text())
catalog_file = ROOT/'artifacts/unreal/capital-expansion/assets.json'
catalog = json.loads(catalog_file.read_text())['templates']
if parent['kind'] != 'atmosphere' or parent['activeCampaignChanged']:
    raise RuntimeError('Shells require an isolated atmosphere parent')
if [z['id'] for z in parent['zones']] != ['sunmeadow_march','cinderfen_outskirts'] or any(len(z['homes'])!=2 for z in parent['zones']):
    raise RuntimeError('Shell authoring admits only the four reserved first-batch homes')
for zone in parent['zones']:
    if not zone['map'].startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'+parent['signature'][:12]+'_') or not zone['map'].endswith('/'+zone['id']+'/Review'):
        raise RuntimeError('Shell parent is outside the isolated first-pair namespace')
baseline_homes=json.loads((DIRECTORY/'homes-latest.json').read_text())
if sha(catalog_file)!=baseline_homes['inputs']['catalogSha256'] or any(
    parent['inputs']['parentPackages'].get(p)!=digest for p,digest in baseline_homes['packageHashes'].items()):
    raise RuntimeError('Preserve changed source recipe metadata or reconcile the parent lineage')
if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower(): raise RuntimeError('Mesh merging requires rendering')
for package, digest in {**parent['inputs']['parentPackages'], **parent['packageHashes']}.items():
    if sha(package_file(package)) != digest: raise RuntimeError('Preserve edited parent map')
for file, digest in {**parent['assetHashes'], **parent['inputs']['parentAssetHashes'], **parent['inputs']['tools'], **parent['inputs']['sourceHashes']}.items():
    if sha(ROOT/file) != digest: raise RuntimeError('Parent study implementation or assets changed')
verify_protected(ROOT, parent['inputs']['protectedHashes'])
protected = protected_saved(ROOT)
templates = {h['template']: catalog[h['template']] for z in parent['zones'] for h in z['homes']}
if set(templates)!={realm+'_interior_'+index+'_home' for realm in ('aegis','riftspire') for index in ('00','01')}:
    raise RuntimeError('Shell parent changed its reserved template identities')
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=False, include_soft_management_references=False, include_hard_management_references=False)
dependencies = dict(parent['inputs']['dependencyHashes'])
pending = [p['mesh'].split('.')[0] for t in templates.values() for p in t['components']]
while pending:
    package = pending.pop()
    if package in dependencies: continue
    if not package.startswith(('/Game/Medieval_Environment/', '/Game/Medieval_Mod_Town/')) or '..' in package or len(dependencies)>2048:
        raise RuntimeError('Source assembly dependency is outside the admitted kits')
    dependencies[package] = sha(asset_file(package))
    pending.extend(str(p) for p in registry.get_dependencies(package, options) if str(p).startswith('/Game/'))
staged = json.loads((ROOT/'artifacts/unreal/capital-expansion/staged.json').read_text())
staged_hashes = {row['path']: row['sha256'] for row in staged['files']}
for package, digest in dependencies.items():
    if sha(asset_file(package)) != digest: raise RuntimeError('Preserve changed source dependency')
    if package.startswith(('/Game/Medieval_Environment/', '/Game/Medieval_Mod_Town/')):
        if staged_hashes.get(package.removeprefix('/Game/')+'.uasset') != digest:
            raise RuntimeError('Assembly source differs from the reviewed staging receipt')
bounds = {}; meshes = {}
for template in templates.values():
    if sha(asset_file(template['mesh'])) != template['sha256']: raise RuntimeError('Preserve edited template')
    for part in template['components']:
        path = part['mesh']
        if path in bounds: continue
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh): raise RuntimeError('Assembly part unavailable')
        b = mesh.get_bounds(); meshes[path] = mesh
        bounds[path] = dict(origin=[b.origin.x,b.origin.y,b.origin.z], extent=[b.box_extent.x,b.box_extent.y,b.box_extent.z])
refits = {key: refit_shell(template, bounds) for key, template in templates.items()}
tools = ['scripts/unreal/build-t1-shell-studies.py','scripts/unreal/t1_home_shell.py','scripts/unreal/t1_material_clone.py',
         'scripts/unreal/t1_materials.py','unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
inputs = dict(parentAtmosphereSignature=parent['signature'], parentPlanSha256=parent['inputs']['parentPlanSha256'],
    parentPackages={**parent['inputs']['parentPackages'], **parent['packageHashes']}, dependencyHashes=dependencies,
    protectedHashes=protected, parentAssetHashes={**parent['inputs']['parentAssetHashes'], **parent['assetHashes']},
    sourceHashes={**parent['inputs']['sourceHashes'], catalog_file.relative_to(ROOT).as_posix():sha(catalog_file),
                  'artifacts/unreal/capital-expansion/staged.json':sha(ROOT/'artifacts/unreal/capital-expansion/staged.json')},
    tools={p:sha(ROOT/p) for p in tools}, sourceBounds=bounds, refits=refits)
signature = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
# This remains an atmosphere candidate, admitted by the same narrow first-pair
# runtime fixture. The separate receipt retains its home-shell study identity.
folder = '/Game/WorldRebuild/T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh_tools = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
new_templates = {}; packages = []; zones = []

def assembled_material(template, source, role):
    if role in ('original','furniture'): return source
    matches = []
    for path in template['materials']:
        material = unreal.load_asset(path)
        if material.get_name().startswith('MI_'+role+'_') and isinstance(material,unreal.MaterialInstanceConstant):
            if material.get_editor_property('parent') == source: matches.append(material)
    if len(matches) != 1: raise RuntimeError('Source palette binding is missing or ambiguous')
    return matches[0]

try:
    if not levels.new_level(folder+'/AssemblyWorkspace'): raise RuntimeError('Cannot create isolated assembly workspace')
    for key, refit in refits.items():
        template = refit['template']; instances = []
        for part in template['components']:
            name = part['mesh'].rsplit('.',1)[-1]
            group = None
            if name in ('SM_Bed','SM_Bed_Matress','SM_Bed_Pillow','SM_Bed_Sheet'):
                group = [bounds[p['mesh']] for p in template['components']
                         if p['mesh'].rsplit('.',1)[-1] in ('SM_Bed','SM_Bed_Matress','SM_Bed_Pillow','SM_Bed_Sheet')
                         and p['anchor']==part['anchor'] and p['scale']==part['scale'] and p['yaw']==part['yaw']]
            location = part_transform(part,bounds,group)
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*location),unreal.Rotator(yaw=part['yaw']))
            actor.set_actor_scale3d(unreal.Vector(*part['scale']))
            mesh = meshes[part['mesh']]; actor.static_mesh_component.set_static_mesh(mesh)
            for slot in range(len(mesh.static_materials)):
                actor.static_mesh_component.set_material(slot,assembled_material(template,mesh.get_material(slot),part['role']))
            instances.append(actor)
        settings = unreal.MeshMergingSettings()
        for name,value in dict(lod_selection_type=unreal.MeshLODSelectionType.ALL_LODS,merge_materials=False,
                              merge_equivalent_materials=False,bake_vertex_data_to_mesh=True,generate_light_map_uv=False,
                              pivot_type=unreal.MeshMergePivotType.WORLD_ORIGIN).items(): settings.set_editor_property(name,value)
        options = unreal.MergeStaticMeshActorsOptions()
        options.base_package_name=folder+'/Homes/SM_'+key; options.mesh_merging_settings=settings
        merged = mesh_tools.merge_static_mesh_actors(instances,options)
        mesh = merged.static_mesh_component.static_mesh if merged else None
        if not isinstance(mesh,unreal.StaticMesh): raise RuntimeError('Shell merge failed')
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if mesh.get_num_lods()<3:
            lod = unreal.EditorScriptingMeshReductionOptions(); lod.auto_compute_lod_screen_size=True
            lod.reduction_settings=[unreal.EditorScriptingMeshReductionSettings(percent_triangles=p,screen_size=s)
                                    for p,s in ((1,1),(.5,.5),(.2,.2))]
            mesh_tools.set_lods(mesh,lod)
        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh,False): raise RuntimeError('Cannot save private shell')
        materials = [s.material_interface.get_path_name() for s in mesh.static_materials]
        if materials != template['materials']: raise RuntimeError('Shell reassembly changed material slot bindings')
        b = mesh.get_bounds()
        if abs(b.origin.z-b.box_extent.z-(template['origin'][2]-template['extent'][2])) > .001:
            raise RuntimeError('Shell reassembly changed the floor datum')
        new_templates[key] = dict(mesh=mesh.get_path_name(),sha256=sha(asset_file(mesh.get_path_name())),materials=materials,
            triangles=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())],corrections=refit['corrections'],
            seamProbes=seam_probes(template,bounds))
        for actor in instances+[merged]:
            if unreal.SystemLibrary.is_valid(actor): actors.destroy_actor(actor)
        unreal.log('WAR_T1_SHELL_ASSEMBLED='+key)
    for zone in parent['zones']:
        identity=zone['id']; source=json.loads((DIRECTORY/(identity+'.json')).read_text())
        if not levels.load_level(zone['map']): raise RuntimeError('Parent atmosphere map unavailable')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states=inventory(actors)
        if not same_state(states,zone['actorInventory']): raise RuntimeError('Parent geometry changed')
        effects=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarRegionalAtmosphere)]
        if len(effects)!=1: raise RuntimeError('Parent atmosphere inventory differs')
        original=effects[0]; recipe=zone['atmosphere']
        for name,value in [('zone_id',identity),('audio_gain',recipe['audioGain'])]:
            actual=original.get_editor_property(name)
            if not same_state(str(actual) if name=='zone_id' else actual,value):
                raise RuntimeError('Parent atmosphere setting changed: '+name)
        for name,expected in [('village_centre',recipe['villageCentre']),('military_centres',recipe['militaryCentres']),('steam_sites',recipe['steamSites'])]:
            value=original.get_editor_property(name)
            actual=[value.x,value.y,value.z] if name=='village_centre' else [[v.x,v.y,v.z] for v in value]
            if not same_state(actual,expected): raise RuntimeError('Parent atmosphere sites changed')
        if original.weather_material.get_path_name()!=recipe['material']: raise RuntimeError('Parent weather material changed')
        homes=copy.deepcopy(zone['homes'])
        for home in homes:
            replacement=new_templates[home['template']]; state=states[home['id']]
            state['mesh']=replacement['mesh']; state['materials']=replacement['materials']
            home.update(mesh=replacement['mesh'],sourceSha256=replacement['sha256'])
        destination=folder+'/'+identity
        if not levels.new_level(destination+'/Review'): raise RuntimeError('Cannot create fresh shell review map')
        anchor=actors.spawn_actor_from_class(unreal.WarZoneAnchor,unreal.Vector())
        anchor.set_editor_property('zone_id',identity); anchor.set_editor_property('zone_origin',unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds',True); b=source['spatial']['bounds']
        anchor.set_editor_property('content_min',unreal.Vector2D(b['minZ']*100,b['minX']*100))
        anchor.set_editor_property('content_max',unreal.Vector2D(b['maxZ']*100,b['maxX']*100))
        anchor.set_editor_property('playable_outline',[unreal.Vector2D(p['z']*100,p['x']*100) for p in source['spatial']['playableOutline']])
        generated=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Generated',False)
        if not generated: raise RuntimeError('Cannot create shell generated layer')
        unreal.EditorLevelUtils.make_level_current(generated); clone(actors,states,{})
        effect=actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere,unreal.Vector())
        effect.set_actor_label(identity+'_regional_atmosphere'); effect.set_editor_property('zone_id',identity)
        effect.set_editor_property('village_centre',unreal.Vector(*recipe['villageCentre']))
        for name,key in [('military_centres','militaryCentres'),('steam_sites','steamSites')]:
            effect.set_editor_property(name,[unreal.Vector(*p) for p in recipe[key]])
        effect.set_editor_property('weather_material',unreal.load_asset(recipe['material']))
        effect.set_editor_property('audio_gain',recipe['audioGain'])
        if not same_state(inventory(actors),states): raise RuntimeError('Shell clone changed surrounding scenery or rooms')
        if not levels.save_current_level(): raise RuntimeError('Cannot save shell generated layer')
        authored=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Authored',False)
        if not authored: raise RuntimeError('Cannot reserve owner shell layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save empty owner layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels',[destination+'/Generated',destination+'/Authored'])
        if not levels.save_current_level(): raise RuntimeError('Cannot save shell review map')
        packages.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append({**zone,'map':destination+'/Review','parentMap':zone['map'],'homes':homes,'actorInventory':states,
                      'surroundingsPreserved':True,'geometryPreserved':False})
finally:
    verify_protected(ROOT,protected)
    for package,digest in dependencies.items():
        if sha(asset_file(package))!=digest: raise RuntimeError('Shell authoring changed frozen source assets')
result=dict(signature=signature,kind='atmosphere',study='home-shell-refit',inputs=inputs,zones=zones,templates=new_templates,
    packageHashes={p:sha(package_file(p)) for p in packages},
    assetHashes={p.relative_to(ROOT).as_posix():sha(p) for p in (CONTENT/folder.removeprefix('/Game/')).rglob('*.uasset')},
    parentCandidatesUnchanged=True,activeCampaignChanged=False,visualApproved=False,walkDriveAccepted=False,licensedDistributionApproved=False)
target=DIRECTORY/('shells-'+signature[:12]+'.json')
if target.exists(): raise RuntimeError('Preserve existing shell receipt')
target.write_text(json.dumps(result,indent=2)+'\n'); (DIRECTORY/'shells-latest.json').write_text(target.read_text())
unreal.log('WAR_T1_SHELLS_BUILT='+signature[:12])
