"""Fresh-process registry, visual and world-component checks after deletion."""
import json
from pathlib import Path
import runpy
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import ROOT,OUT
runpy.run_path(str(Path(__file__).with_name('audit-legacy-native-animations.py')))
rows=json.loads((OUT/'native-animation-removal-plan.json').read_text())
if any(not row['keep'] for row in rows): raise RuntimeError('Unexpected superseded native animation remains')
keep={row['path'] for row in rows if row['kind']=='AnimSequence'}
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
worlds=[]
maps=['/Game/Capitals/crownward/Population/AegisCapital_Population']
registry=unreal.AssetRegistryHelpers.get_asset_registry()
# Discover the authored population sublevels from the registry rather than
# guessing revision-specific package names.
for data in registry.get_assets_by_class(unreal.TopLevelAssetPath('/Script/Engine','World'),True):
    name=str(data.package_name)
    if name.startswith('/Game/WorldRebuild/') and (any(k in name.lower() for k in ('sunmeadow','cinderfen')) or name.endswith('/CampaignTravel')): maps.append(name)
for path in sorted(set(maps)):
    if not unreal.EditorAssetLibrary.does_asset_exist(path): continue
    if not editor.load_level(path): raise RuntimeError('Could not validate NPC world: '+path)
    count=0
    for actor in actors.get_all_level_actors():
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            animation=component.get_editor_property('animation_data').anim_to_play
            if not animation: continue
            if animation.get_path_name().split('.')[0] not in keep: raise RuntimeError('Legacy NPC animation: '+path+':'+actor.get_name())
            if animation.get_editor_property('skeleton')!=component.get_skeletal_mesh_asset().skeleton: raise RuntimeError('NPC rig mismatch')
            count+=1
    worlds.append(dict(map=path,animatedCharacters=count))
old={r['path'] for r in json.loads((OUT/'native-animation-removal.json').read_text())['removed']}
if not any(row['animatedCharacters'] for row in worlds): raise RuntimeError('NPC animation fixtures were not exercised')
for data in registry.get_assets_by_class(unreal.TopLevelAssetPath('/Script/CoreUObject','ObjectRedirector'),True):
    dependencies={str(name) for name in registry.get_dependencies(data.package_name,unreal.AssetRegistryDependencyOptions())}
    if dependencies & old: raise RuntimeError('Redirector to retired character motion: '+str(data.package_name))
(OUT/'native-animation-removal-verification.json').write_text(json.dumps(dict(passed=True,remainingCurrentAnimationAssets=len(rows),supersededAssets=0,npcWorlds=worlds),indent=2)+'\n')
