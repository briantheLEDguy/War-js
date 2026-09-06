import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'ember-arcanist-reference-rebuild/tools'))
from validate_source import validate_component


class GuardSourceTests(unittest.TestCase):
    def setUp(self):
        self.sources={f.stem:json.loads(f.read_text()) for f in (ROOT/'source').glob('*.json')}

    def test_all_four_sources_have_valid_topology_and_uvs(self):
        self.assertEqual(set(self.sources),{'standard','halberd','crossbow','captain'})
        for data in self.sources.values(): self.assertTrue(validate_component(data))

    def test_each_specialist_has_its_own_equipment(self):
        required={'standard':'heater_shield_wood','halberd':'halberd_crescent','crossbow':'crossbow_taut_string','captain':'captain_cape'}
        for name,part in required.items():
            self.assertIn(part,{p['id'] for p in self.sources[name]['parts']})
        self.assertNotIn('heater_shield_wood',{p['id'] for p in self.sources['crossbow']['parts']})

    def test_no_inherited_floating_fasteners_or_religious_relics(self):
        for data in self.sources.values():
            for part in data['parts']:
                self.assertFalse(part['id'].startswith(('knee_skull','reliquary_','relic_')))
                self.assertNotIn('pauldron_authored_rivet',part['id'])

    def test_weapon_skin_assignments_are_explicit(self):
        for data in self.sources.values():
            for part in data['parts']:
                if part.get('guard_weapon'):
                    self.assertIn(part['rigid_bone'],{'hand_L','hand_R','hips'})

    def test_guards_share_the_natural_anatomical_source(self):
        natural=json.loads((ROOT/'anatomy/head_refined.json').read_text())['parts'][0]
        for data in self.sources.values():
            head=next(p for p in data['parts'] if p['id']=='head_skin')
            self.assertEqual(head['vertices'],natural['vertices'])
            self.assertEqual(head['faces'],natural['faces'])
        provenance=json.loads((ROOT/'anatomy/provenance.json').read_text())
        self.assertEqual(provenance['source'],'blends/male_base.blend')
        self.assertLessEqual(provenance['output_head_triangles'],11000)


if __name__=='__main__': unittest.main()
