import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from siege_review import current_review
from shared_city_sources import can_preserve_siege_review


class SiegeReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.map = self.root/'siege.umap'
        self.map.write_bytes(b'current overlay')
        self.city = dict(id='aegis_capital', revision='current-city')
        self.review = dict(cityRevision='current-city', mapSha256=self.sha(self.map),
                           visualReviewed=True, visualNotes='Reviewed the four current rendered landmarks.', frames=[])
        walk = dict(passed=True, routesCompleted=7, walkers=[dict(jumped=True, distanceCm=30000) for _ in range(12)])
        convoy = dict(passed=True, checkpoints=3, vehicles=[dict(travelCm=26000), dict(travelCm=25000)],
                      stoppedWithoutEscort=True, stoppedWithoutCrew=True, overlapRecoveredWithoutDamage=True,
                      ramStrikeAdvanced=True, gateCollisionVerified=True)
        client = dict(passed=True, gateCollisionVerified=True, ownershipStandards=4, engineersReady=4, captures=4)
        self.reports = dict(traversal=walk, convoy=convoy, client=client)
        for value in self.reports.values():
            value.update({k:self.review[k] for k in ('cityRevision', 'mapSha256')})
        for i in range(4):
            file = self.root/f'frame{i}.png'; file.write_bytes(bytes([i]))
            self.review['frames'].append(dict(path=file.name, sha256=self.sha(file)))
        directory = self.root/'artifacts/unreal/shared-cities'; directory.mkdir(parents=True)
        self.file = directory/'siege-review.json'
        self.addCleanup(patch.stopall)
        patch('siege_review.source_plan', return_value=dict(cities=[self.city])).start()
        patch('siege_review.package_file', return_value=self.map).start()
        self.save()

    @staticmethod
    def sha(file):
        return hashlib.sha256(file.read_bytes()).hexdigest()

    def save(self):
        for name, value in self.reports.items():
            file = self.root/(name+'.json'); file.write_text(json.dumps(value))
            self.review[name] = dict(path=file.name, sha256=self.sha(file))
        self.file.write_text(json.dumps(self.review))

    def test_current_complete_evidence(self):
        self.assertEqual(current_review(self.root)[0], self.city)

    def test_sync_does_not_reapprove_an_edited_overlay(self):
        city = dict(revision='city', sceneryLevels=['shared'])
        review = dict(revision='city', layers=['shared'], mapSha256='reviewed')
        self.assertTrue(can_preserve_siege_review(city, city, review, 'reviewed'))
        self.assertFalse(can_preserve_siege_review(city, city, review, 'edited'))
        self.assertFalse(can_preserve_siege_review(city, dict(city, revision='new'), review, 'reviewed'))
        self.assertFalse(can_preserve_siege_review(city, city, dict(review, layers=['copy']), 'reviewed'))

    def test_city_activation_invalidates_intact_old_proofs(self):
        self.city['revision'] = 'new-city'
        with self.assertRaisesRegex(ValueError, 'different city'):
            current_review(self.root)

    def test_map_edit_invalidates_review(self):
        self.map.write_bytes(b'changed geometry')
        with self.assertRaises(ValueError): current_review(self.root)

    def test_old_physical_report_cannot_approve_current_receipt(self):
        self.reports['convoy']['cityRevision'] = 'old-city'; self.save()
        with self.assertRaisesRegex(ValueError, 'obsolete'): current_review(self.root)

    def test_missing_gate_and_incomplete_crowd_fail(self):
        self.reports['convoy']['gateCollisionVerified'] = False; self.save()
        with self.assertRaises(ValueError): current_review(self.root)
        self.reports['convoy']['gateCollisionVerified'] = True
        self.reports['traversal']['walkers'].pop(); self.save()
        with self.assertRaises(ValueError): current_review(self.root)

    def test_changed_visual_evidence_fails(self):
        (self.root/'frame0.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'visual review frame'): current_review(self.root)


if __name__ == '__main__': unittest.main()
