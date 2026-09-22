"""Read-only inventory of the persistent capital before extracting its authored level."""
import hashlib
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'build.json').read_text())
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(receipt['map']): raise RuntimeError('Main map unavailable')
actors=[]
layers={}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    package=actor.get_outer().get_path_name().split('.')[0]
    row=layers.setdefault(package,{'actors':0,'classes':{}})
    row['actors']+=1
    cls=actor.get_class().get_name()
    row['classes'][cls]=row['classes'].get(cls,0)+1
    if actor.get_outer().get_path_name().split('.')[0]!=receipt['map']: continue
    parent=actor.get_attach_parent_actor()
    row={'name':actor.get_name(),'class':actor.get_class().get_name(),'label':actor.get_actor_label(),
         'parent':parent.get_name() if parent else None,'tags':[str(t) for t in actor.tags]}
    if isinstance(actor,unreal.PostProcessVolume):
        settings=actor.get_editor_property('settings')
        row['exposure']={key:str(settings.get_editor_property(key)) for key in ('auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias')}
    actors.append(row)
file=ROOT/'unreal/AegisWar/Content'/(receipt['map'].removeprefix('/Game/')+'.umap')
(directory/'capital-partition-inspection.json').write_text(json.dumps({'map':receipt['map'],'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'actors':actors,'layers':layers},indent=2)+'\n')
unreal.log('WAR_CAPITAL_PARTITION_INSPECTED='+str(len(actors)))
