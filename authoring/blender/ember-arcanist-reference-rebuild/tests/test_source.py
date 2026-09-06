import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from validate_source import validate_component
from validate_runtime import model_name


class EmberSourceTests(unittest.TestCase):
    def test_all_components_validate(self):
        for path in (ROOT/'source').glob('*.json'):
            if path.name!='scene.json':
                with self.subTest(component=path.name):
                    self.assertTrue(validate_component(json.loads(path.read_text())))

    def test_staff_has_emissive_core_and_separate_iron(self):
        parts=json.loads((ROOT/'source/staff.json').read_text())['parts']
        core=next(p for p in parts if p['id']=='ember_heart')
        self.assertTrue(all(face['material']=='ember' for face in core['faces']))
        ribs=next(p for p in parts if p['id']=='brazier_iron_rib')
        self.assertEqual(len(ribs['instances']),6)
        self.assertTrue(all(face['material']=='dark_steel' for face in ribs['faces']))

    def test_export_names_are_class_specific(self):
        for slot in ('body','head','shoulders','chest','hands','waist','legs','feet','back','tabard','weapon'):
            self.assertIn('ember_arcanist',model_name(slot,0))
            self.assertTrue(model_name(slot,2).endswith('_lod2.glb'))

    def test_invalid_authored_face_is_rejected(self):
        data=json.loads((ROOT/'source/staff.json').read_text())
        data=copy.deepcopy(data)
        face=data['parts'][0]['faces'][0]
        face['vertices'][1]=face['vertices'][0]
        with self.assertRaises(ValueError):validate_component(data)

    def test_head_module_does_not_mask_face(self):
        template=json.loads((ROOT/'manifest_templates/arm_civic_ember_arcanist_head_t1_m.approved.json').read_text())
        self.assertEqual(template['compatibility']['coveredRegions'],[])
        self.assertEqual(template['compatibility']['skeletonId'],'humanoid_game_v2')


if __name__=='__main__':unittest.main()
