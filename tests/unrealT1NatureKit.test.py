import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_nature_kit import NATURE_ROOT,NAMES,select_nature_meshes,nature_dependencies

class NatureKitTests(unittest.TestCase):
 def fixture(self):return dict(kit=NATURE_ROOT,meshes=[dict(path=NATURE_ROOT+'/Meshes/'+n+'.'+n,lodCount=2,lodVertices=[300,100],boundsOrigin=[0,0,10],boundsExtent=[20,20,20],materials=[NATURE_ROOT+'/Materials/M_leaf.M_leaf']) for n in NAMES])
 def test_exact_bounded_static_mesh_selection_preserves_inventory(self):
  r=self.fixture();before=copy.deepcopy(r);selected=select_nature_meshes(r)
  self.assertEqual(len(selected),15);self.assertEqual(r,before)
  self.assertEqual([x['path'].rsplit('.',1)[-1] for x in selected],list(NAMES))
 def test_missing_ambiguous_or_unreviewed_material_inventory_fails(self):
  r=self.fixture()
  for bad in [{**r,'meshes':r['meshes'][1:]},{**r,'meshes':r['meshes']+[r['meshes'][0]]},{**r,'kit':'/Game/Other'}]:
   with self.assertRaises(ValueError):select_nature_meshes(bad)
  for key,value in [('materials',['/Game/Other/M.M']),('lodVertices',[1]),('boundsExtent',[20,math.nan,20])]:
   bad=copy.deepcopy(r);bad['meshes'][0][key]=value
   with self.assertRaises(ValueError):select_nature_meshes(bad)
 def test_dependency_cycles_and_engine_script_leaves_are_bounded(self):
  a=NATURE_ROOT+'/Meshes/Oak';b=NATURE_ROOT+'/Materials/Leaves';graph={a:[b,'/Engine/Functions/Wind'],b:[a,'/Script/Engine']}
  self.assertEqual(nature_dependencies([a],lambda p:graph[p]),sorted([a,b]))
 def test_other_kit_path_traversal_and_object_paths_fail(self):
  for root in ['/Game/ParagonProps/Mesh','/Game/Medieval_Environment/../Other','/Game/Medieval_Environment/Mesh.Mesh','/Game/Medieval_Environment//Mesh']:
   with self.assertRaises(ValueError):nature_dependencies([root],lambda p:[])

if __name__=='__main__':unittest.main()
