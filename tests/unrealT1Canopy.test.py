import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_canopy import leaf_slots,canopy_sources,softened_leaf_normals,retained_native_canopy

class CanopyTests(unittest.TestCase):
    def test_leaf_selection_preserves_bark_and_rejects_unreviewed_slot_topology(self):
        materials=[dict(doubleSided=False,alphaMode='OPAQUE'),dict(doubleSided=True,alphaMode='OPAQUE',textures=dict(color=dict(path='reviewed')))]
        before=copy.deepcopy(materials);self.assertEqual(leaf_slots(materials),[1]);self.assertEqual(materials,before)
        for corrupt in ('bark','alpha','missing','extra'):
            bad=copy.deepcopy(materials)
            if corrupt=='bark':bad[0]['doubleSided']=True
            elif corrupt=='alpha':bad[1]['alphaMode']='BLEND'
            elif corrupt=='missing':bad[1]['textures']={}
            else:bad.append(bad[-1])
            with self.assertRaises(ValueError):leaf_slots(bad)
    def test_leaf_normals_preserve_all_geometry_attributes_and_bark(self):
        data=dict(positions=[[-1,0,0],[1,0,0],[0,0,1],[-2,0,3],[2,0,3],[0,1,4]],normals=[[0,0,1] for _ in range(6)],indices=list(range(6)),triangleMaterials=[0,1],uvs=[[0,0] for _ in range(6)],colors=[[1,1,1,1] for _ in range(6)])
        before=copy.deepcopy(data);result=softened_leaf_normals(data,[1]);self.assertEqual(data,before)
        for key in data:
            if key!='normals':self.assertEqual(result[key],data[key])
        self.assertEqual(result['normals'][:3],data['normals'][:3]);self.assertNotEqual(result['normals'][3:],data['normals'][3:])
        for n in result['normals']:self.assertAlmostEqual(sum(v*v for v in n),1)
        self.assertTrue(retained_native_canopy(dict(valid=True,data=data),dict(valid=True,data=result),[1]))
        bad=copy.deepcopy(data);bad['indices'][3]=0
        with self.assertRaises(ValueError):softened_leaf_normals(bad,[1])
    def test_native_readback_rejects_changed_geometry_uvs_and_bark_normals(self):
        data=dict(positions=[[0,0,0]]*6,normals=[[0,0,1]]*6,indices=list(range(6)),triangleMaterials=[0,1],uvs=[[0,0]]*6)
        for key in ('positions','uvs','normals'):
            bad=copy.deepcopy(data);bad[key][0]=[1,1,1] if key!='uvs' else [1,1]
            with self.assertRaises(ValueError):retained_native_canopy(dict(valid=True,data=data),dict(valid=True,data=bad),[1])
    def test_actual_source_admission_pins_all_regional_leaf_channels(self):
        rows,inputs=canopy_sources(Path(__file__).resolve().parents[1]);self.assertEqual(len(rows),3)
        self.assertIn('public/assets/models/asset-index.json',inputs)
        for row in rows.values():self.assertEqual(row['leafSlots'],[1]);self.assertEqual(row['materialCount'],2);self.assertEqual(len(row['sourceSha256']),64)

if __name__=='__main__':unittest.main()
