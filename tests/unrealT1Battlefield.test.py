import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_battlefield import Surface,terrain_sampling_bounds,rebase_inventory,rebase_population,rebase_homes


class BattlefieldTests(unittest.TestCase):
    def setup_surface(self,height):
        source={'id':'sunmeadow_march','spatial':{'bounds':dict(minX=0,maxX=20,minZ=0,maxZ=10),'terrainGrid':dict(segmentsX=2,segmentsZ=1)}}
        mesh={'zoneId':source['id'],'positions':[[z*100,x*100,height(x,z)] for z in (0,10) for x in (0,10,20)]}
        return source,Surface(source,mesh),mesh

    def test_rectangular_native_triangle_ground_and_bounds(self):
        _,surface,_=self.setup_surface(lambda x,z:x*100+z*20)
        self.assertEqual(surface.height_cm(7,4),780)
        self.assertEqual(surface.height_cm(20,10),2200)
        with self.assertRaises(ValueError): surface.height_cm(-1,0)

    def test_expanded_ownership_retains_the_exact_rectangular_sampling_grid(self):
        source, local, mesh = self.setup_surface(lambda x,z: x*100+z*20)
        source['spatial']['terrainBounds'] = copy.deepcopy(source['spatial']['bounds'])
        source['spatial']['bounds'] = dict(minX=-3600,maxX=3600,minZ=-3400,maxZ=3400)
        expanded = Surface(source,mesh)
        for x,z in [(0,0),(7,4),(20,10)]: self.assertEqual(expanded.height_cm(x,z),local.height_cm(x,z))
        with self.assertRaises(ValueError): expanded.height_cm(500,500)

    def test_malformed_sampling_and_escaped_playable_outline_fail(self):
        source,_,mesh = self.setup_surface(lambda x,z: 0)
        for bounds in [None,{},dict(minX=0,maxX=float('nan'),minZ=0,maxZ=10),dict(minX=-1,maxX=20,minZ=0,maxZ=10)]:
            bad=copy.deepcopy(source);bad['spatial']['terrainBounds']=bounds
            with self.assertRaises(ValueError): Surface(bad,mesh)
        source['spatial']['terrainBounds']=dict(minX=0,maxX=10,minZ=0,maxZ=10)
        source['spatial']['playableOutline']=[dict(x=15,z=5)]
        with self.assertRaises(ValueError): terrain_sampling_bounds(source['spatial'])

    def test_nonplanar_ground_uses_the_native_diagonal_not_bilinear_interpolation(self):
        _,surface,_=self.setup_surface(lambda x,z:10000 if x==10 and z==10 else 0)
        self.assertEqual(surface.height_cm(5,2),0)
        self.assertAlmostEqual(surface.height_cm(9,6),5000)

    def test_duplicate_missing_and_nonfinite_vertices_fail(self):
        source,_,mesh=self.setup_surface(lambda x,z:0)
        for positions in (mesh['positions'][:-1],mesh['positions']+[mesh['positions'][0]],[[0,0,float('nan')]]):
            with self.assertRaises(ValueError): Surface(source,{**mesh,'positions':positions})

    def test_complete_assemblies_rebase_together_without_changing_inputs(self):
        source,old,_=self.setup_surface(lambda x,z:0); _,new,_=self.setup_surface(lambda x,z:x*10)
        before={**source,'orvrLayout':{'keeps':[dict(objectiveId='keep',y=8)]}}
        after={**source,'orvrLayout':{'keeps':[dict(objectiveId='keep',y=12)]}}
        states={label:dict(kind='mesh',location=[0,x*100,25],mesh='exact',collision='BlockAll') for label,x in [('keep_gate',1),('keep_commander',15),('tree',5)]}
        original=copy.deepcopy(states); result,receipt=rebase_inventory(states,before,after,old,new)
        self.assertEqual(states,original)
        self.assertEqual(result['keep_gate']['location'][2],425)
        self.assertEqual(result['keep_commander']['location'][2],425)
        self.assertEqual(result['tree']['location'][2],75)
        self.assertTrue(receipt['xyAndBindingsPreserved'])
        for key in states: self.assertEqual(result[key]['location'][:2],states[key]['location'][:2])

    def test_population_identity_offsets_and_approaches_follow_new_ground(self):
        _,old,_=self.setup_surface(lambda x,z:100); _,new,_=self.setup_surface(lambda x,z:500)
        rows=[dict(id='same',savedState=dict(location=[0,500,142],identity={'npc_id':'same'}),approach=[[0,500,100],[0,900,100]])]
        original=copy.deepcopy(rows); result=rebase_population(rows,old,new)
        self.assertEqual(rows,original); self.assertEqual(result[0]['point'][2],542)
        self.assertEqual(result[0]['savedState']['identity'],rows[0]['savedState']['identity'])
        self.assertEqual(result[0]['approach'],[[0,500,500],[0,900,500]])

    def test_home_approach_targets_use_actual_new_ground_and_interior_moves_rigidly(self):
        _,old,_=self.setup_surface(lambda x,z:100); _,new,_=self.setup_surface(lambda x,z:500)
        row=dict(id='home',approachPoints=2,route=[[0,500,0],[0,900,0],[0,950,120]],interiorRoute=[[0,950,120]],location=[0,950,100])
        result=rebase_homes([row],{'home':400},old,new)[0]
        self.assertEqual(result['route'],[[0,500,500],[0,900,500],[0,950,520]])
        self.assertEqual(result['interiorRoute'],[[0,950,520]]); self.assertEqual(result['location'][2],500)

if __name__=='__main__': unittest.main()
