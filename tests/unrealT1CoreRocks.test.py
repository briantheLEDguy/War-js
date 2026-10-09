import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_rock_clusters import core_rock_parents

class CoreRockTests(unittest.TestCase):
 def fixture(self):return dict(kind='mesh',mesh='rock',scale=[2,3,4],rotation=[0,90,0],location=[1000,2000,500])
 def test_native_pivot_scale_and_rotation_produce_source_reserve(self):
  states={'sunmeadow_march_barrow_ridge_8':self.fixture()};before=copy.deepcopy(states)
  result=core_rock_parents('sunmeadow_march',states,'rock',[10,20,30],[100,200,50]);p=result['placements'][0]
  self.assertEqual(states,before);self.assertAlmostEqual(p['x'],20.2);self.assertAlmostEqual(p['z'],9.4)
  self.assertEqual([p['width'],p['depth'],p['height']],[12,4,4]);self.assertEqual(p['yawDegrees'],90)
 def test_landmarks_cells_and_other_meshes_are_excluded(self):
  source=self.fixture();states={k:copy.deepcopy(source) for k in ['cinderfen_outskirts_landmark','cinderfen_outskirts_cell_basalt_shelf_1','cinderfen_outskirts_basalt_shelf_2']};states['cinderfen_outskirts_basalt_shelf_2']['mesh']='other'
  self.assertEqual(core_rock_parents('cinderfen_outskirts',states,'rock',[0,0,0],[100,100,100])['placements'],[])
 def test_tilted_or_oversized_sources_are_retained_and_invalid_data_fails(self):
  state=self.fixture();state['rotation'][0]=1;label='sunmeadow_march_barrow_ridge_8'
  self.assertEqual(core_rock_parents('sunmeadow_march',{label:state},'rock',[0,0,0],[100,100,100])['retainedIds'],[label])
  state['rotation'][0]=0;state['scale'][1]=100
  self.assertEqual(core_rock_parents('sunmeadow_march',{label:state},'rock',[0,0,0],[100,100,100])['retainedIds'],[label])
  state['location'][0]=math.nan
  with self.assertRaises(ValueError):core_rock_parents('sunmeadow_march',{label:state},'rock',[0,0,0],[100,100,100])

if __name__=='__main__':unittest.main()
