"""Fresh-process preservation and single-owner checks for the extracted capital."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_actor_state import snapshot
directory=ROOT/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'build.json').read_text())
manifest=json.loads((directory/receipt['partitionManifest']).read_text())
expected=json.loads((directory/'capital-authored-state.json').read_text())
capital=next(z for z in manifest['zones'] if z['id']=='aegis_capital')
if not capital.get('capitalExtracted'): raise RuntimeError('Capital has not been extracted')
for package,sha in {receipt['map']:manifest['mainSha256'],**manifest['packageHashes']}.items():
    file=ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=sha: raise RuntimeError('Saved package changed: '+package)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt['map']): raise RuntimeError('Main world unavailable')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
actual={}
gm_ids=set()
for actor in actors:
    package=actor.get_outer().get_path_name().split('.')[0]
    if package==receipt['map']: raise RuntimeError('Persistent capital actor remains: '+actor.get_name())
    for tag in actor.tags:
        if str(tag).startswith('WarWorldObject_'):
            if str(tag) in gm_ids: raise RuntimeError('Duplicate GM identity: '+str(tag))
            gm_ids.add(str(tag))
    if package==capital['levels']['authored']:
        state=snapshot(actor)
        added='WarZoneObject_aegis_capital_'+actor.get_name()
        if added not in expected[actor.get_name()]['tags']: state['tags'].remove(added)
        actual[actor.get_name()]=state
if actual!=expected:
    (directory/'capital-saved-diff.json').write_text(json.dumps({'expected':expected,'actual':actual},indent=2))
    raise RuntimeError('Saved capital differs from original authored state')
anchor=next(a for a in actors if isinstance(a,unreal.WarZoneAnchor) and str(a.get_editor_property('zone_id'))=='aegis_capital')
if sorted(str(p) for p in anchor.get_editor_property('content_levels'))!=sorted(capital['levels'].values()):
    raise RuntimeError('Capital runtime dependencies differ from manifest')
proof={'preservedActors':len(actual),'uniqueGmIds':len(gm_ids),'persistentContentActors':0,
       'savedStatePreserved':True,'sourceState':'capital-authored-state.json','packageHashes':manifest['packageHashes']}
(directory/'capital-preservation.json').write_text(json.dumps(proof,indent=2)+'\n')
unreal.log('WAR_SAVED_CAPITAL_PRESERVED='+str(len(actual)))
