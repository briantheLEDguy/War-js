import importlib,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))

class Mesh:
 def get_bounds(self):return types.SimpleNamespace(origin=types.SimpleNamespace(z=10),box_extent=types.SimpleNamespace(z=15))
 def get_path_name(self):return '/private/grass'
class Actor:
 def __init__(self,ok=True,label=''):self.ok=ok;self.label=label;self.details=self
 def get_actor_label(self):return self.label
 def set_actor_label(self,label):self.label=label
 def configure(self,mesh,transforms):self.transforms=transforms;return self.ok
 def get_instance_count(self):return len(self.transforms)
 def get_collision_enabled(self):return 0
 def set_cull_distances(self,start,end):self.culls=(start,end)
 def get_editor_property(self,name):return self.culls[0 if name=='instance_start_cull_distance' else 1]
class Actors:
 def __init__(self,fail=False,existing=None):self.spawned=[];self.destroyed=[];self.fail=fail;self.existing=existing or []
 def get_all_level_actors(self):return self.existing
 def spawn_actor_from_class(self,*args):a=Actor(not(self.fail and len(self.spawned)==1));self.spawned.append(a);return a
 def destroy_actor(self,a):self.destroyed.append(a)

class NativeMeadowTest(unittest.TestCase):
 def setUp(self):
  self.fake=types.SimpleNamespace(StaticMesh=Mesh,WarLandscapeDetail=Actor,Vector=lambda *v:v,Rotator=lambda **k:k,Transform=lambda **k:k,CollisionEnabled=types.SimpleNamespace(NO_COLLISION=0),load_asset=lambda p:Mesh())
  self.world=types.SimpleNamespace(path='/Game/WorldRebuild/T1Redesign_Atmosphere_Test/sunmeadow_march/Review.Review');self.world.get_path_name=lambda:self.world.path
  self.fake.UnrealEditorSubsystem=object;self.fake.get_editor_subsystem=lambda kind:types.SimpleNamespace(get_editor_world=lambda:self.world)
  self.modules=patch.dict(sys.modules,{'unreal':self.fake});self.modules.start()
  for name in ('t1_meadow_native','t1_nature_canopy_native','t1_understorey_native'):sys.modules.pop(name,None)
  self.m=importlib.import_module('t1_meadow_native')
  self.sources=patch.object(self.m,'nature_sources',return_value=({n:{'path':'/private/'+n} for n in self.m.NAMES},{'package':'hash'}));self.source_mock=self.sources.start()
  self.inventory=patch.object(self.m,'installed_detail_inventory',return_value={'verified':True});self.inventory_mock=self.inventory.start()
  self.rows=[dict(x=3,z=4,y=200,scale=1,yaw=10,mesh=n) for n in self.m.NAMES]
  self.layout=patch.object(self.m,'meadow_layout',return_value=dict(rows=self.rows,instances=2));self.layout_mock=self.layout.start()
  self.assets=types.SimpleNamespace(folder='/Game/WorldRebuild/T1Redesign_Atmosphere_Test')
 def tearDown(self):
  self.layout.stop();self.inventory.stop();self.sources.stop();self.modules.stop()
  for name in ('t1_meadow_native','t1_nature_canopy_native','t1_understorey_native'):sys.modules.pop(name,None)
 def test_ground_units_exact_inventory_cosmetic_culling_and_transactional_rollback(self):
  actors=Actors();spawned,proof=self.m.spawn_meadows(self.assets,actors,{'id':'sunmeadow_march'},lambda x,z:0,[])
  self.assertEqual(len(spawned),2);self.assertEqual(spawned[0].transforms[0]['location'],(400,300,204));self.assertEqual(proof['cullMetres'],[80,180]);self.assertEqual(self.inventory_mock.call_count,2);self.assertFalse(proof['nativeIntegrated'] or proof['ordinaryPersistenceAccepted'])
  failed=Actors(fail=True)
  with self.assertRaises(RuntimeError):self.m.spawn_meadows(self.assets,failed,{'id':'sunmeadow_march'},lambda x,z:0,[])
  self.assertEqual(failed.destroyed,list(reversed(failed.spawned)))
 def test_owner_actor_and_wrong_destination_preserved_before_spawning(self):
  existing=Actor(label='sunmeadow_march_meadow_SM_Grass_01');actors=Actors(existing=[existing])
  with self.assertRaises(RuntimeError):self.m.spawn_meadows(self.assets,actors,{'id':'sunmeadow_march'},None,[])
  self.assertEqual(actors.spawned,[]);self.assertEqual(actors.destroyed,[]);self.source_mock.assert_not_called()
  with self.assertRaises(ValueError):self.m.spawn_meadows(types.SimpleNamespace(folder='/Game/AcceptedCapital'),Actors(),{'id':'sunmeadow_march'},None,[])
 def test_native_species_limit_is_checked_before_spawning(self):
  self.layout_mock.return_value=dict(rows=[self.rows[0]]*12001,instances=12001);actors=Actors()
  with self.assertRaises(ValueError):self.m.spawn_meadows(self.assets,actors,{'id':'sunmeadow_march'},None,[])
  self.assertEqual(actors.spawned,[])
 def test_unrelated_loaded_owner_world_rejected_before_asset_reads_or_spawns(self):
  self.world.path='/Game/AcceptedCapital.OwnerMap';actors=Actors()
  with self.assertRaises(ValueError):self.m.spawn_meadows(self.assets,actors,{'id':'sunmeadow_march'},None,[])
  self.source_mock.assert_not_called();self.assertEqual(actors.spawned,[])
if __name__=='__main__':unittest.main()
