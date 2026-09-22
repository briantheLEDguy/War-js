"""Extract the saved Bastion into its authored level, preserving the startup map path.

All affected packages and manifests are backed up before writing. Existing
authored content or changed managed packages abort without replacing them.
"""
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_actor_state import snapshot
from world_zones import digest

def main():
    directory=ROOT/'artifacts/unreal/world-portals'
    receipt=json.loads((directory/'build.json').read_text())
    manifest=json.loads((directory/receipt['partitionManifest']).read_text())
    capital=next(row for row in manifest['zones'] if row['id']=='aegis_capital')
    if capital.get('capitalExtracted'):
        unreal.log('WAR_CAPITAL_ALREADY_PARTITIONED')
        return
    population='/Game/Capitals/crownward/Population/AegisCapital_Population'
    previous_target=capital['levels']['authored']
    target=previous_target


    def file(package):
        if not package.startswith('/Game/'): raise RuntimeError('Invalid content package')
        return ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')


    def sha(package): return hashlib.sha256(file(package).read_bytes()).hexdigest()


    for package in (manifest['layer'],target,capital['levels']['generated']):
        if sha(package)!=manifest['packageHashes'][package]: raise RuntimeError('Managed package changed: '+package)
    before_hashes={p:sha(p) for p in (receipt['map'],manifest['layer'],target,population)}
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=directory/('capital-extraction-backup-'+stamp)
    backup.mkdir()
    for package in before_hashes: shutil.copy2(file(package),backup/(file(package).stem+'.umap'))
    for name in ('build.json',receipt['partitionManifest']): shutil.copy2(directory/name,backup/name)
    (backup/'packages.json').write_text(json.dumps(before_hashes,indent=2)+'\n')
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not level.load_level(receipt['map']): raise RuntimeError('Main world unavailable')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)


    def in_package(package):
        return [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==package]


    source=in_package(receipt['map'])
    if in_package(target): raise RuntimeError('Capital authored layer is not empty; preserve existing edits')
    if not source or any(a.get_attach_parent_actor() for a in source): raise RuntimeError('Unexpected capital actor ownership')
    before={a.get_name():snapshot(a) for a in source}
    population_before={a.get_name():snapshot(a) for a in in_package(population)}
    if not population_before: raise RuntimeError('Capital population is missing')
    destination=unreal.GameplayStatics.get_streaming_level(world,target)
    # Duplicate the complete package: template-spawning brush actors leaves private
    # archetype/model references in the source map. Whole-world duplication remaps them.
    target=previous_target+'_Extracted_'+stamp
    if not unreal.EditorAssetLibrary.duplicate_asset(receipt['map'],target) or not level.load_level(target):
        raise RuntimeError('Could not create authored capital candidate')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    copies=in_package(target)
    after={a.get_name():snapshot(a) for a in copies}
    if before!=after:
        (directory/'capital-copy-diff.json').write_text(json.dumps({'before':before,'after':after},indent=2))
        raise RuntimeError('Capital copy changed authored state; main map has not been saved')
    for actor in copies:
        tags=list(actor.tags)
        if not any(str(t).startswith('WarZoneObject_') for t in tags):
            actor.tags=tags+['WarZoneObject_aegis_capital_'+actor.get_name()]
    for package in list(manifest['packageHashes'])+[population]:
        streaming=unreal.GameplayStatics.get_streaming_level(world,package)
        if streaming and not unreal.EditorLevelUtils.remove_level_from_world(streaming.get_loaded_level()):
            raise RuntimeError('Could not remove nested streaming reference: '+package)
    if not level.set_current_level_by_name(file(target).stem): raise RuntimeError('Candidate capital unavailable')
    if not level.save_current_level(): raise RuntimeError('Authored capital save failed; main map retained')
    # The original source is only removed after its complete candidate has saved.
    if not level.load_level(receipt['map']): raise RuntimeError('Main world unavailable after candidate save')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    source=in_package(receipt['map'])
    if {a.get_name():snapshot(a) for a in source}!=before: raise RuntimeError('Source changed during extraction')
    old_target=unreal.GameplayStatics.get_streaming_level(world,previous_target)
    if not old_target or not unreal.EditorLevelUtils.remove_level_from_world(old_target.get_loaded_level()):
        raise RuntimeError('Could not detach empty capital placeholder')
    destination=unreal.EditorLevelUtils.add_level_to_world(world,target,unreal.LevelStreamingDynamic)
    if not destination: raise RuntimeError('Could not attach extracted capital')
    destination.set_editor_property('initially_loaded',False)
    destination.set_editor_property('initially_visible',False)
    capital['levels']['authored']=target
    for actor in source:
        if not actors.destroy_actor(actor): raise RuntimeError('Could not remove a verified source duplicate')
    old_population=unreal.GameplayStatics.get_streaming_level(world,population)
    if not old_population or not unreal.EditorLevelUtils.remove_level_from_world(old_population.get_loaded_level()):
        raise RuntimeError('Could not detach always-loaded capital population')
    population_stream=unreal.EditorLevelUtils.add_level_to_world(world,population,unreal.LevelStreamingDynamic)
    if not population_stream: raise RuntimeError('Could not attach streamed population')
    population_stream.set_editor_property('initially_loaded',False)
    population_stream.set_editor_property('initially_visible',False)
    unreal.GameplayStatics.flush_level_streaming(world)
    if {a.get_name():snapshot(a) for a in in_package(population)}!=population_before:
        raise RuntimeError('Capital population changed')
    anchor=next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)
                and str(a.get_editor_property('zone_id'))=='aegis_capital')
    anchor.set_editor_property('content_levels',list(capital['levels'].values())+[population])
    if not level.set_current_level_by_name(file(manifest['layer']).stem) or not level.save_current_level():
        raise RuntimeError('Capital routing save failed')
    if in_package(receipt['map']): raise RuntimeError('Persistent capital actors remain')
    if not level.set_current_level_by_name(file(receipt['map']).stem) or not level.save_current_level():
        raise RuntimeError('Persistent shell save failed')
    if sha(population)!=before_hashes[population]: raise RuntimeError('Population package was unexpectedly rewritten')
    capital['levels']['population']=population
    capital.update(capitalExtracted=True,externalAuthoredCapital=False,actorCount=len(copies)+len(population_before))
    for package in (target,manifest['layer'],population): manifest['packageHashes'][package]=sha(package)
    manifest['packageHashes'].pop(previous_target,None)
    manifest['mainSha256']=sha(receipt['map'])
    manifest.pop('traversalEvidence',None)
    capital['acceptance']['traversal']='pending'
    capital['acceptance']['visual']='pending'
    evidence={'before':before_hashes,'after':{p:sha(p) for p in [*before_hashes,target]},'backup':str(backup),
              'preservedPersistentActors':len(copies),'preservedPopulationActors':len(population_before),
              'preservedStateSha256':digest(before),'persistentContentActors':0,'runtimeVerified':False}
    manifest['capitalExtraction']=evidence
    receipt.update(capitalSha256After=manifest['mainSha256'],runtimeTraversalVerified=False)
    (directory/receipt['partitionManifest']).write_text(json.dumps(manifest,indent=2)+'\n')
    (directory/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (directory/'capital-extraction.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (directory/'capital-authored-state.json').write_text(json.dumps(before,separators=(',',':'))+'\n')
    unreal.log('WAR_CAPITAL_PARTITIONED='+str(len(copies))+' POPULATION='+str(len(population_before)))


main()
