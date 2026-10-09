import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_canopy import leaf_slots,canopy_sources

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
    def test_actual_source_admission_pins_all_regional_leaf_channels(self):
        rows,inputs=canopy_sources(Path(__file__).resolve().parents[1]);self.assertEqual(len(rows),3)
        self.assertIn('public/assets/models/asset-index.json',inputs)
        for row in rows.values():self.assertEqual(row['leafSlots'],[1]);self.assertEqual(row['materialCount'],2);self.assertEqual(len(row['sourceSha256']),64)

if __name__=='__main__':unittest.main()
