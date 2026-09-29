import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/unreal'))
import imported_population as population
from capital_population import records, planned_records


class ImportedPopulationTests(unittest.TestCase):
    def test_all_sources_have_specific_assignments(self):
        data = population.ledger()
        self.assertEqual(len(data['models']), 18)
        self.assertEqual(len({r['source'] for r in data['models']}), 18)
        used = {r['model'] for r in data['capitalReplacements']+data['capitalAdditions']}
        used.update(r['model'] for c in data['camps'] for r in c['members'])
        self.assertEqual(used, set(population.models()))
        self.assertTrue(all(len(r['sha256']) == 64 and r['review'] == 'source-inspected-native-pending' for r in data['models']))

    def test_capitals_preserve_service_identities_and_original_records(self):
        original = records(); before = copy.deepcopy(original)
        result = population.population_records(original)
        self.assertEqual(original, before)
        self.assertEqual(len(planned_records('aegis_capital')), 24)
        self.assertEqual(len(planned_records('riftspire_capital')), 8)
        for row in original:
            updated = next(r for r in result if r['id'] == row['id'])
            for field in ('id','name','role','district','x','z','yaw'):
                self.assertEqual(updated[field], row[field])
        protected = {'quest-1','aegis_capital_quartermaster','aegis_capital_class_trainer','aegis_capital_craft_trainer','aegis_capital_banker','lantern_supply_merchant'}
        for row in original:
            if row['id'] in protected:
                self.assertEqual(next(r for r in result if r['id']==row['id'])['profile'],row['profile'])

    def test_neutral_models_serve_both_camp_types(self):
        camps = population.ledger()['camps']
        self.assertEqual([len(c['members']) for c in camps], [3,3,3,4])
        self.assertEqual([c['allegiance'] for c in camps], ['friendly','hostile','friendly','hostile'])
        used = {r['model'] for c in camps for r in c['members']}
        self.assertEqual(used, {'guard01','guard02','brute','cultist','maw'})
        for camp in camps:
            self.assertTrue(all((r['role']=='enemy') == (camp['allegiance']=='hostile') for r in camp['members']))

    def test_missing_or_stale_review_cannot_admit(self):
        with self.assertRaisesRegex(ValueError,'stale'):
            population.require_review({}, 'native')
        evidence = dict(ledgerSha256=population.digest(population.LEDGER),nativeSha256='native')
        with self.assertRaisesRegex(ValueError,'incomplete'):
            population.require_review(evidence,'native')
        evidence.update(materials=True,equippedMotion=True,nativeVisual=True)
        population.require_review(evidence,'native')
        with self.assertRaisesRegex(ValueError,'stale'):
            population.require_review(evidence,'changed')

    def test_equipped_variants_and_civilian_bodies_are_distinct(self):
        rows=population.models()
        self.assertEqual(rows['paladin_prop']['equipment'],'embedded-review')
        self.assertEqual(rows['archer']['equipment'],'embedded-review')
        self.assertEqual(rows['scout']['equipment'],'none')
        for key in ('guard01','guard02','brute','cultist','maw'):
            self.assertEqual(rows[key]['equipment'],'sword-shield')
        for key in ('scout','archer','retainer','maw'):
            self.assertTrue(all(r['metallic']==0 and r['reason'] for r in rows[key]['materialOverrides'].values()))

    def test_owner_edits_require_approval_and_cannot_change_after_review(self):
        self.assertEqual(population.check_zone_ownership({'zone':'original'},{'zone':'original'},{'zone':'original'}),{})
        with self.assertRaisesRegex(ValueError,'approved'):
            population.check_zone_ownership({'zone':'original'},{'zone':'owner-edit'},{'zone':'owner-edit'})
        changed=population.check_zone_ownership({'zone':'original'},{'zone':'owner-edit'},{'zone':'owner-edit'},True)
        self.assertEqual(changed['zone']['current'],'owner-edit')
        with self.assertRaisesRegex(ValueError,'after review'):
            population.check_zone_ownership({'zone':'original'},{'zone':'owner-edit'},{'zone':'later-edit'},True)

    def test_achromatic_specular_and_unsupported_inputs(self):
        spec=importlib.util.spec_from_file_location('model_import',ROOT/'scripts/unreal/import-models.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.specular_factor({}),.5)
        self.assertEqual(module.specular_factor({'extensions':{'KHR_materials_specular':{'specularColorFactor':[2,2,2]}}}),1)
        for value in ({'specularColorFactor':[1,0,0]}, {'specularTexture':{'index':0}}, {'specularFactor':float('nan')}):
            with self.assertRaises(RuntimeError): module.specular_factor({'extensions':{'KHR_materials_specular':value}})


if __name__ == '__main__': unittest.main()
