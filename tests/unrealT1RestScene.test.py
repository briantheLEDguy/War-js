import copy, math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_rest_scene import rest_scene


def fixture():
    return dict(asset={'version':'2.0'},scene=0,scenes=[{'nodes':[0]}],nodes=[
        dict(name='pivot',translation=[10,0,0],rotation=[0,0,math.sqrt(.5),math.sqrt(.5)],scale=[2,2,2],children=[1,2]),
        dict(name='wheel',mesh=0,translation=[1,0,0]),dict(name='socket',translation=[0,2,0])],
        meshes=[{'primitives':[{'attributes':{'POSITION':0},'material':0}]}],materials=[{'name':'oak'}],
        accessors=[{'bufferView':0}],bufferViews=[{'buffer':0}],buffers=[{'byteLength':12}],
        animations=[{'name':'roll','channels':[{'target':{'node':1,'path':'rotation'}}]}])


class RestSceneTest(unittest.TestCase):
    def test_composes_pivot_rotation_translation_and_scale_without_mutation(self):
        source=fixture(); before=copy.deepcopy(source); result,proof=rest_scene(source)
        wheel=result['nodes'][0]; self.assertEqual(wheel['name'],'wheel'); self.assertAlmostEqual(wheel['translation'][0],10)
        self.assertAlmostEqual(wheel['translation'][1],2); self.assertEqual(wheel['scale'],[2]*3)
        self.assertEqual(result['scenes'],[{'nodes':[0]}]); self.assertEqual(source,before)
        for field in ['meshes','materials','accessors','bufferViews','buffers']:self.assertEqual(result[field],source[field])
        self.assertNotIn('animations',result); self.assertTrue(proof['authoredRestPose']);self.assertFalse(proof['animationSampled'] or proof['vehicleGameplayAccepted'])
        self.assertEqual(proof['visitedNodes'],3);self.assertEqual(proof['meshNodes'],1)

    def test_composed_rotation_preserves_noncommuting_parent_child_order(self):
        source=fixture();source['nodes'][1]['rotation']=[math.sqrt(.5),0,0,math.sqrt(.5)]
        result,_=rest_scene(source);x,y,z,w=result['nodes'][0]['rotation']
        # The child X rotation maps local +Y to +Z; the parent Z rotation leaves +Z unchanged.
        transformed=[2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w)]
        for actual,expected in zip(transformed,[0,0,1]):self.assertAlmostEqual(actual,expected,places=12)

    def test_rejects_cycles_shared_children_and_invalid_references(self):
        for child in [0,99,True]:
            s=fixture();s['nodes'][1]['children']=[child]
            with self.assertRaises(ValueError):rest_scene(s)
        s=fixture();s['nodes'][2]['children']=[1]
        with self.assertRaises(ValueError):rest_scene(s)

    def test_rejects_deformation_shear_matrix_and_nonfinite_transforms(self):
        for update in [dict(skin=0),dict(matrix=[1]*16),dict(scale=[1,2,1]),dict(scale=[-1]*3),dict(translation=[0,math.nan,0]),dict(rotation=[0,0,0,2])]:
            s=fixture();s['nodes'][1].update(update)
            with self.assertRaises(ValueError):rest_scene(s)
        for update in [dict(skins=[{}]),dict(meshes=[{'primitives':[{'targets':[{}]}]}])]:
            s=fixture();s.update(update)
            with self.assertRaises(ValueError):rest_scene(s)

    def test_selected_scene_omits_inactive_nodes_and_rejects_empty_or_unbounded_scenes(self):
        s=fixture();s['nodes'].append(dict(mesh=0,translation=[50,0,0]));r,p=rest_scene(s)
        self.assertEqual(len(r['nodes']),1);self.assertEqual(p['omittedInactiveNodes'],1)
        for mutate in [lambda s:s.update(scene=True),lambda s:s['scenes'][0].update(nodes=[[0]]),lambda s:s['scenes'][0].update(nodes=[0,0]),lambda s:s['nodes'][0].update(translation=[10001,0,0]),lambda s:s['nodes'][1].pop('mesh')]:
            s=fixture();mutate(s)
            with self.assertRaises(ValueError):rest_scene(s)

    def test_bounded_depth_rejects_pathological_hierarchies(self):
        s=fixture();s['nodes']=[dict(children=[i+1]) for i in range(130)]+[dict(mesh=0)];s['scenes']=[{'nodes':[0]}]
        with self.assertRaisesRegex(ValueError,'bounded depth'):rest_scene(s)

if __name__=='__main__':unittest.main()
