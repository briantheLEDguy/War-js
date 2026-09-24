"""Replace map NPC idles, remove obsolete reviews, then delete audited animations.

Model, skeleton, material, equipment and environmental packages are never deletion
candidates. Any unexpected live referencer stops the operation before deletion.
"""
import json
from pathlib import Path
import runpy
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import ROOT,OUT
runpy.run_path(str(Path(__file__).with_name('audit-legacy-native-animations.py')))
rows=json.loads((OUT/'native-animation-removal-plan.json').read_text())
legacy={row['path']:row for row in rows if not row['keep']}
sets=json.loads((OUT/'presentations.json').read_text())['profiles']
library=unreal.EditorAssetLibrary
registry=unreal.AssetRegistryHelpers.get_asset_registry()
options=unreal.AssetRegistryDependencyOptions()
maps=set(); reviews=set(); substitutions={}
for path,row in legacy.items():
    if path.startswith(('/Game/Imported/npc_','/Game/Imported/enemy_')) and path.endswith('_Anim_idle'):
        profile=path.split('/')[3]
        if profile not in sets: raise RuntimeError('NPC has no replacement: '+profile)
        substitutions[path]=unreal.load_asset(sets[profile]['bindings']['idle'])
    for reference in row['referencers']:
        if reference in legacy: continue
        if reference.startswith('/Game/MigrationProof/CombatAnimationReview_'): reviews.add(reference)
        elif path in substitutions and reference.startswith(('/Game/WorldRebuild/','/Game/Capitals/')): maps.add(reference)
        else: raise RuntimeError('Unexpected live animation dependency: '+reference+' -> '+path)
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rebound=[]
for path in sorted(maps):
    if not editor.load_level(path): raise RuntimeError('Cannot open NPC map: '+path)
    for actor in actors.get_all_level_actors():
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            data=component.get_editor_property('animation_data')
            old=data.anim_to_play
            key=old.get_path_name().split('.')[0] if old else None
            if key not in substitutions: continue
            replacement=substitutions[key]
            if replacement.get_editor_property('skeleton')!=component.get_skeletal_mesh_asset().skeleton:
                raise RuntimeError('NPC map skeleton mismatch: '+path+':'+actor.get_name())
            data.anim_to_play=replacement; data.saved_playing=True; data.saved_looping=True
            component.set_editor_property('animation_data',data)
            component.play_animation(replacement,True)
            rebound.append(dict(map=path,actor=actor.get_name(),old=key,new=replacement.get_path_name()))
    if not editor.save_current_level(): raise RuntimeError('NPC map save failed: '+path)
cleanup='/Game/Characters/Reviews/ReplacementCleanup'
if not (editor.load_level(cleanup) if library.does_asset_exist(cleanup) else editor.new_level(cleanup)):
    raise RuntimeError('Cannot leave previous map')
for path in sorted(reviews):
    references={str(x) for x in registry.get_referencers(path,options)}-reviews
    if references: raise RuntimeError('Review map is used by '+str(references))
    if library.does_asset_exist(path) and not library.delete_asset(path): raise RuntimeError('Review deletion failed: '+path)
    physical=(ROOT/'unreal/AegisWar/Content'/path.removeprefix('/Game/')).with_suffix('.umap').resolve()
    physical.relative_to(ROOT/'unreal/AegisWar/Content')
    if physical.exists(): raise RuntimeError('Review file remains after deletion: '+path)
registry.scan_paths_synchronous(['/Game/MigrationProof','/Game/WorldRebuild','/Game/Capitals'],True)
for path in legacy:
    references={str(x) for x in registry.get_referencers(path,options)}-set(legacy)-reviews
    if references: raise RuntimeError('Live dependency remains: '+path+' <- '+str(references))
removed=[]
for path,row in sorted(legacy.items(),key=lambda pair:(pair[1]['kind'] not in ('IKRetargeter','AnimBlueprint'),pair[0])):
    physical=(ROOT/'unreal/AegisWar/Content'/path.removeprefix('/Game/')).with_suffix('.uasset').resolve()
    physical.relative_to(ROOT/'unreal/AegisWar/Content')
    if not library.delete_asset(path): raise RuntimeError('Animation deletion failed: '+path)
    if physical.exists() or library.does_asset_exist(path): raise RuntimeError('Deleted package remains: '+path)
    removed.append(dict(path=path,kind=row['kind'],previousSources=row.get('sources',[])))
report=dict(schemaVersion=1,removed=removed,removedReviews=sorted(reviews),reboundNpcActors=rebound)
(OUT/'native-animation-removal.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('WAR_LEGACY_NATIVE_REMOVED='+str(len(removed)))
