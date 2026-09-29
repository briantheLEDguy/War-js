"""Review the portable city export without licensed packages or Unreal installed."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from dutch_city_revision import validate_revision, merge_manifest


class CityRevisionTests(unittest.TestCase):
    def test_activation_preserves_independent_portal_review_metadata(self):
        base=dict(map='old',zones=[dict(id='aegis_capital',levels=['old'],acceptance=dict(traversal='pending'))])
        proposed=copy.deepcopy(base);proposed['map']='new';proposed['zones'][0]['levels']=['new']
        current=copy.deepcopy(base);current['zones'][0]['acceptance']['traversal']='verified';current['traversalEvidence']='portal-report'
        merged=merge_manifest(base,proposed,current)
        self.assertEqual(merged['map'],'new');self.assertEqual(merged['zones'][0]['levels'],['new'])
        self.assertEqual(merged['zones'][0]['acceptance']['traversal'],'verified')
        self.assertEqual(merged['traversalEvidence'],'portal-report')
        self.assertEqual(merge_manifest(base,merged,merged),merged)
        self.assertEqual(merge_manifest(dict(map='old',runtimeTraversalVerified=False),
                         dict(map='new',runtimeTraversalVerified=False),dict(map='old',runtimeTraversalVerified=True)),
                         dict(map='new',runtimeTraversalVerified=True))

    def test_activation_rejects_competing_bindings_and_zone_reorders(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            merge_manifest(dict(map='old'),dict(map='city'),dict(map='other'))
        base=[dict(id='a',value=0),dict(id='b',value=0)]
        proposed=copy.deepcopy(base);proposed[0]['value']=1
        with self.assertRaisesRegex(ValueError,'identities'):
            merge_manifest(base,proposed,list(reversed(base)))

    def test_manifest_merge_preserves_disjoint_additions_and_deletions(self):
        self.assertEqual(merge_manifest(dict(a=1,b=2),dict(a=1,b=3),dict(b=2,c=4)),dict(b=3,c=4))
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            merge_manifest(dict(a=1),dict(a=2),{})

    def setUp(self):
        self.data=json.loads((ROOT/'migration/dutch-bastion-city.json').read_text())

    def test_actual_city_export_keeps_dense_blocks_and_five_districts(self):
        validate_revision(self.data)
        self.assertGreaterEqual(len(self.data['buildings']),900)
        self.assertEqual(len(self.data['gatheringAreas']),5)
        self.assertEqual({r['district'] for r in self.data['buildings']},
                         {'gateward','cinderbank','lantern_quays','bellfound','crownwatch'})
        self.assertTrue(self.data['protectedSites'])
        self.assertFalse(self.data['acceptance']['release'])

    def test_duplicate_actors_and_missing_venues_are_rejected(self):
        duplicate=copy.deepcopy(self.data);duplicate['buildings'].append(duplicate['buildings'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'): validate_revision(duplicate)
        missing=copy.deepcopy(self.data)
        next(r for r in missing['buildings'] if r['publicInterior'])['publicInterior']=None
        with self.assertRaisesRegex(ValueError,'venue'): validate_revision(missing)

    def test_geometry_binding_edits_invalidate_export_signature(self):
        self.data['buildings'][0]['position'][0]+=1
        with self.assertRaisesRegex(ValueError,'Edited'): validate_revision(self.data)

    def test_active_export_cannot_omit_performance_acceptance(self):
        self.data['acceptance'].update(active=True,performance=False)
        with self.assertRaisesRegex(ValueError,'complete architecture acceptance'): validate_revision(self.data)


if __name__=='__main__': unittest.main()
