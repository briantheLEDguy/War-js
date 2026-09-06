"""Keep the source constraints that resolved the observed motion-fit failures."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class NovitiateFitSourceTests(unittest.TestCase):
    def test_compact_cap_and_overlapping_lame_share_rigid_attachment(self):
        parts=json.loads((ROOT/'source/pauldron.json').read_text())['parts']
        attachment={part['id']:(part.get('rigid_bone'),part.get('mirror_bone')) for part in parts}
        cap=attachment['left_pauldron_main_shell']
        for name in ('left_pauldron_upper_lame','left_pauldron_upper_lame_brass_hem',
                     'left_pauldron_lame_fasteners','novitiate_pauldron_front_hinge_tab',
                     'novitiate_pauldron_rear_hinge_tab'):
            self.assertEqual(attachment[name],cap,name)

    def test_leather_toe_rand_preserves_accepted_contact_coordinates(self):
        accepted=json.loads((ROOT.parent/'battle-prelate-reference-rebuild/source/feet.json').read_text())
        current=json.loads((ROOT/'source/feet.json').read_text())
        original=next(p for p in accepted['parts'] if p['id']=='sabaton_brass_toe_rim')
        rand=next(p for p in current['parts'] if p['id']=='novitiate_boot_leather_toe_rand')
        for field in ('vertices','modifiers','transform','rigid_bone','mirror_bone'):
            self.assertEqual(rand[field],original[field],field)
        self.assertEqual({f['material'] for f in rand['faces']},{'leather'})


if __name__=='__main__':
    unittest.main()
