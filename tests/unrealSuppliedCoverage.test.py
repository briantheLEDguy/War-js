"""Coverage cannot be satisfied by imports, previews or only one executor type."""
import importlib.util
import copy
from pathlib import Path
import sys
import unittest

TOOLS=Path(__file__).resolve().parents[1]/'scripts/unreal'
sys.path.insert(0,str(TOOLS))
spec=importlib.util.spec_from_file_location('coverage_report',TOOLS/'publish-animation-coverage.py')
report=importlib.util.module_from_spec(spec); spec.loader.exec_module(report)


class CoverageTest(unittest.TestCase):
    def test_identical_rerun_can_reuse_hash_bound_captures(self):
        receipts={key:dict(path=key,sha256='verified-'+key) for key in ('gameplay','captures','presentations')}
        images=[dict(path='frame.png',sha256='verified-frame')]
        previous=dict(gameplayVerified=True,evidence=copy.deepcopy(receipts),gameplayImages=copy.deepcopy(images))
        self.assertTrue(report.published_capture_matches(previous,receipts,images))
        for key in receipts:
            changed=copy.deepcopy(receipts); changed[key]['sha256']='changed'
            self.assertFalse(report.published_capture_matches(previous,changed,images))
        self.assertFalse(report.published_capture_matches(previous,receipts,[dict(path='frame.png',sha256='changed')]))
        self.assertFalse(report.published_capture_matches({},receipts,images))

    def fixture(self):
        scenarios=[]; presentations={}
        for profile,(career,style) in report.PROFILES.items():
            recipes={}
            for suffix,keys,choreography,*_ in report.RECIPES[career]:
                ability=career+'.'+suffix
                roles=[ability+'__'+str(i) for i in range(len(keys) if choreography=='smash' else 1)]
                recipes[ability]=dict(variantRoles=roles,suppliedSources=keys,choreography=choreography)
                for role in roles:
                    for executor in ('player','participant_bot'):
                        scenarios.append(dict(profile=profile,role=role,scenario=executor+'_ability'))
            presentations[profile]=dict(presentations=recipes)
            for role in report.locomotion(style):
                for executor in ('player','participant_bot'):
                    scenarios.append(dict(profile=profile,role=role,scenario=executor+'_locomotion'))
        return scenarios,presentations

    def test_all_sources_and_distinct_smash_variants(self):
        scenarios,presentations=self.fixture()
        clips,abilities=report.build_coverage(scenarios,presentations)
        self.assertEqual(len(clips),44); self.assertEqual(len(abilities),40)
        self.assertTrue(all(row['role'].endswith('__0') for row in clips['two.jump_attack']))
        self.assertTrue(all(row['role'].endswith('__1') for row in clips['two.spin']))

    def test_preview_only_and_player_only_cannot_pass(self):
        scenarios,presentations=self.fixture()
        for rows in ([],[row for row in scenarios if row['scenario'].startswith('player_')]):
            with self.assertRaisesRegex(ValueError,'lacks both'):
                report.build_coverage(rows,presentations)

    def test_missing_second_smash_variant_fails(self):
        scenarios,presentations=self.fixture()
        rows=[row for row in scenarios if row['role']!='battle_prelate.reliquary_smash__1']
        with self.assertRaisesRegex(ValueError,'two.spin'):
            report.build_coverage(rows,presentations)

    def test_shared_source_does_not_hide_a_missing_ability_executor(self):
        scenarios,presentations=self.fixture()
        rows=[row for row in scenarios if not (row['role']=='battle_prelate.sanctified_blow__0' and row['scenario']=='player_ability')]
        with self.assertRaisesRegex(ValueError,'Ability lacks both'):
            report.build_coverage(rows,presentations)


if __name__=='__main__': unittest.main()
