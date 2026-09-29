"""Numerical coverage and native-mesh contracts, independent of visual approval."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from dutch_bastion import area, block, frontage_widths, pilot_plan, validate
from dutch_architecture import house, facade, Mesh


class DutchBastionTests(unittest.TestCase):
    def test_brick_courses_stay_horizontal_on_rotated_walls(self):
        for points in ([[0,0,0],[0,3,0],[0,3,4],[0,0,4]],
                       [[0,0,0],[3,0,0],[3,0,4],[0,0,4]]):
            mesh=Mesh();mesh.face(points,'brick')
            for position,uv in zip(mesh.positions,mesh.uvs):
                self.assertAlmostEqual(uv[1],-position[2]/1.6)

    def test_frontage_solver_has_no_remainder_gap(self):
        for length in (8.03,17.11,29.7,51.23,100.001):
            for opening in (True,False):
                widths,index=frontage_widths(length,31,opening)
                self.assertAlmostEqual(sum(widths),length,places=12)
                self.assertTrue(all(4<=w<=8 for i,w in enumerate(widths) if i!=index))
                if opening: self.assertEqual(widths[index],2.8)

    def test_full_perimeter_equals_houses_plus_declared_passage(self):
        p=pilot_plan();b=p['blocks'][0]
        self.assertEqual(len(b['openings']),1)
        self.assertAlmostEqual(sum(area(r['polygon']) for r in b['lots']+b['openings']),
                               area(b['boundary'])-area(b['court']),places=8)
        self.assertEqual(p,pilot_plan())

    def test_missing_lot_and_one_centimetre_seam_are_rejected(self):
        p=pilot_plan();p.pop('signature');p['blocks'][0]['lots'].pop(2)
        with self.assertRaises(ValueError): validate(p)
        p=pilot_plan();p.pop('signature');p['blocks'][0]['lots'][1]['polygon'][0][0]+=.01
        with self.assertRaises(ValueError): validate(p)

    def test_stale_plan_cannot_be_admitted(self):
        p=pilot_plan();p['blocks'][0]['lots'][0]['storeys']=4
        with self.assertRaisesRegex(ValueError,'fingerprint'): validate(p)

    def test_stable_unique_ids_and_public_venues(self):
        p=pilot_plan();lots=p['blocks'][0]['lots']
        self.assertEqual(len(lots),len({l['actorId'] for l in lots}))
        venues=[l['publicInterior'] for l in lots if l['publicInterior']]
        self.assertEqual({v['kind'] for v in venues},{'inn','cafe','shop'})
        self.assertTrue(all(v['service']=='atmosphere_only' for v in venues))
        self.assertFalse(any(p['acceptance'].values()))

    def test_mesh_is_finite_nondegenerate_and_material_bound(self):
        for lot in pilot_plan()['blocks'][0]['lots']:
            m=house(lot)['mesh']
            self.assertEqual(len(m['positions']),len(m['normals']))
            self.assertEqual(len(m['positions']),len(m['uvs']))
            self.assertEqual(len(m['indices'])//3,len(m['triangleMaterials']))
            self.assertTrue(all(0<=s<8 for s in m['triangleMaterials']))
            self.assertTrue(all(math.isfinite(v) for p in m['positions'] for v in p))
            self.assertTrue(all(abs(sum(v*v for v in n)-1)<1e-8 for n in m['normals']))
            for i in range(0,len(m['indices']),3):
                a,b,c=[m['positions'][j] for j in m['indices'][i:i+3]]
                u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
                cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                self.assertLess(sum(cross[j]*m['normals'][m['indices'][i]][j] for j in range(3)),0)

    def test_corner_boundaries_are_shared_without_rectangular_fillers(self):
        b=block('angled','cinderbank',[[0,0],[36,0],[42,31],[17,44],[-5,29]],7)
        for i in range(len(b['boundary'])):
            left=sorted([r for r in b['lots']+b['openings'] if r['edge']==i],key=lambda r:r['id'])[-1]
            right=sorted([r for r in b['lots']+b['openings'] if r['edge']==(i+1)%len(b['boundary'])],key=lambda r:r['id'])[0]
            self.assertEqual(left['polygon'][1],right['polygon'][0])
            self.assertEqual(left['polygon'][2],right['polygon'][3])

    def test_public_doorway_has_no_crossing_plinth_or_hidden_wall(self):
        mesh=Mesh();door=facade(mesh,6,9,3,True,0)
        # At the door's centreline, any triangle spanning the entrance from
        # floor to head height is a collision blocker, including decorative trim.
        for i in range(0,len(mesh.indices),3):
            pts=[mesh.positions[j] for j in mesh.indices[i:i+3]]
            xs=[p[0] for p in pts];zs=[p[2] for p in pts]
            if min(xs)<door<max(xs) and max(zs)>.1 and min(zs)<2.35:
                self.fail('Geometry crosses the public entrance')


if __name__=='__main__': unittest.main()
