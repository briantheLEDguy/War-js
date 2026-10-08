import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_home_shell import refit_shell, part_transform, seam_probes

PREFIX = '/Game/Medieval_Environment/Meshes/'
def path(name): return PREFIX+name+'.'+name
def part(name, z, role): return dict(mesh=path(name), anchor=[0, 225, z], yaw=0, scale=[1, 1.5, 1.5] if role=='roof' else [1, 1, 1], role=role)


class HomeShellTest(unittest.TestCase):
    def setUp(self):
        self.roof = path('SM_MH_02_Slate_Roof_01')
        self.wall = path('SM_MH_02_Stone_Wall_01')
        self.bounds = {self.roof: dict(origin=[150, -150, 155], extent=[150, 150, 165]),
                       self.wall: dict(origin=[150, 5, 150], extent=[150, 23, 150])}
        self.template = dict(kind='home', interior=True, upperFloor=False, roomSize=[600, 900],
            components=[part('SM_MH_02_Stone_Wall_01', 10, 'wall'), part('SM_MH_02_Slate_Roof_01', 310, 'roof')])

    def test_eave_datum_preserved_without_changing_walls(self):
        original = copy.deepcopy(self.template)
        refit = refit_shell(self.template, self.bounds)
        self.assertEqual(self.template, original)
        roof = refit['template']['components'][1]
        self.assertEqual(roof['anchor'][2], 295)
        self.assertEqual(part_transform(roof, self.bounds)[2], 310)
        self.assertEqual(refit['template']['components'][0], original['components'][0])
        self.assertFalse(refit['visualApproved'])

    def test_shared_bed_bounds_preserve_attached_parts(self):
        p = dict(mesh='bed', anchor=[100, 200, 10], yaw=90, scale=[1, 1, 1])
        group = [dict(origin=[50, 60, 20], extent=[40, 50, 20]), dict(origin=[50, 60, 80], extent=[40, 50, 10])]
        self.assertEqual(part_transform(p, {}, group), [160, 150, 10])

    def test_a_second_repair_cannot_lower_an_already_seated_roof(self):
        refit = refit_shell(self.template,self.bounds)
        with self.assertRaises(ValueError): refit_shell(refit['template'],self.bounds)

    def test_bad_or_unmeasured_roofs_fail_closed(self):
        for field, value in [('upperFloor', True), ('kind', 'shop')]:
            with self.assertRaises(ValueError): refit_shell({**self.template, field:value}, self.bounds)
        for z in (155, 250, float('nan')):
            altered = copy.deepcopy(self.bounds); altered[self.roof]['extent'][2] = z
            with self.assertRaises(ValueError): refit_shell(self.template, altered)

    def test_seam_probes_cover_each_eave_bay_above_the_wall(self):
        probes = seam_probes(self.template, self.bounds)
        self.assertEqual(len(probes), 12)
        self.assertEqual({p['side'] for p in probes}, {-1,1})
        self.assertEqual({p['bay'] for p in probes}, {0,1})
        self.assertTrue(all(p['start'][2] > 310 for p in probes))


if __name__ == '__main__': unittest.main()
