"""Attach the population layer to the saved city; run only with the interactive editor closed."""
import hashlib,json,re,runpy,sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_population import official_map
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level(official_map())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
file=ROOT/'unreal/AegisWar/Content'/(official_map().removeprefix('/Game/')+'.umap')
before=hashlib.sha256(file.read_bytes()).hexdigest()
def persistent_state():
 state=[]
 for actor in actors.get_all_level_actors():
  if not actor.get_outer().get_path_name().startswith(official_map()+'.'):continue
  p,r,s=actor.get_actor_location(),actor.get_actor_rotation(),actor.get_actor_scale3d()
  row=[actor.get_path_name(),actor.get_actor_label(),[p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]]
  if isinstance(actor,unreal.StaticMeshActor):
   c=actor.static_mesh_component
   row.append([c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())])
  if isinstance(actor,unreal.Light):
   row.append(str(actor.light_component.get_editor_property('intensity')))
  if isinstance(actor,unreal.PostProcessVolume): row.append(re.sub(r'0x[0-9A-Fa-f]+','address',str(actor.get_editor_property('settings'))))
  state.append(row)
 return sorted(state,key=lambda r:r[0])
original=persistent_state()
runpy.run_path(str(Path(__file__).with_name('attach-capital-population.py')))
if original!=persistent_state():raise RuntimeError('Persistent city actors changed unexpectedly')
if before!=hashlib.sha256(file.read_bytes()).hexdigest():raise RuntimeError('Owner saved concurrently; attachment remains unsaved')
if not unreal.EditorLoadingAndSavingUtils.save_map(world,official_map()):raise RuntimeError('Population attachment save failed')
(ROOT/'artifacts/unreal/population/attachment.json').write_text(json.dumps({'map':official_map(),'persistentActorsUnchanged':len(original),'before':before,'after':hashlib.sha256(file.read_bytes()).hexdigest()},indent=2))
