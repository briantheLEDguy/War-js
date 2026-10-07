"""Verify authored exterior-facing surfaces, aperture and side-wall orientation."""
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'scripts/unreal'))
from aegis_citadel_mesh import Mesh, arch, side_arch, blind_bay, MATERIALS


def triangles(mesh,role):
    for ordinal,material in enumerate(mesh.triangle_materials):
        if MATERIALS[material]==role:
            indices=mesh.indices[ordinal*3:ordinal*3+3]
            yield [mesh.positions[i] for i in indices],mesh.normals[indices[0]]


class WindowOrientationTests(unittest.TestCase):
    def test_front_and_back_masonry_faces_point_out_of_arch_volume(self):
        mesh=Mesh('arch');arch(mesh,0,0,0,300,1400,100,40)
        front=[];back=[]
        for points,normal in triangles(mesh,'limestone'):
            if all(p[0]==-50 for p in points):front.append(normal)
            if all(p[0]==50 for p in points):back.append(normal)
        self.assertTrue(front and back)
        self.assertTrue(all(n[0]<-.999 for n in front))
        self.assertTrue(all(n[0]>.999 for n in back))

    def test_inner_reveals_face_open_air_and_outer_reveals_face_masonry_exterior(self):
        mesh=Mesh('arch');arch(mesh,0,0,0,300,1400,100,40)
        directions={}
        for points,normal in triangles(mesh,'limestone'):
            if abs(normal[0])<1e-8 and abs(normal[2])<1e-8:
                directions[points[0][1]]=normal[1]
        self.assertEqual(directions[-150],1)
        self.assertEqual(directions[150],-1)
        self.assertEqual(directions[-190],-1)
        self.assertEqual(directions[190],1)

    def test_lit_and_unlit_front_panes_face_the_approach(self):
        for lit,role in ((True,'glass'),(False,'window_dark')):
            mesh=Mesh('pane');arch(mesh,200,100,6000,300,1400,100,40,glass=True,lit=lit)
            panes=list(triangles(mesh,role));self.assertTrue(panes)
            self.assertTrue(all(n[0]<-.999 for _,n in panes))
            self.assertTrue(all(p[0]==175 for ps,_ in panes for p in ps))

    def test_blind_bay_backing_faces_outward_without_piercing_wall(self):
        mesh=Mesh('blind');blind_bay(mesh,200,0,4300,300,1000)
        panes=list(triangles(mesh,'window_dark'));self.assertTrue(panes)
        self.assertTrue(all(n[0]<-.999 for _,n in panes))
        self.assertTrue(all(p[0]==199.5 for ps,_ in panes for p in ps))

    def test_side_panes_and_trims_project_outward_on_both_wall_sides(self):
        for side in (-1,1):
            mesh=Mesh('side');side_arch(mesh,1000,side*4400,6000,300,1400,100,40,
                glass=True,outward_side=side)
            panes=list(triangles(mesh,'glass'));self.assertTrue(panes)
            self.assertTrue(all(abs(n[1]-side)<1e-8 for _,n in panes))
            self.assertTrue(all(abs(p[1]-(side*4400+side*25))<1e-6 for ps,_ in panes for p in ps))
            trims=list(triangles(mesh,'gold'))
            self.assertTrue(all(side*(p[1]-side*4400)>40 for ps,_ in trims for p in ps))

    def test_ambiguous_or_invalid_glazed_side_is_rejected(self):
        for side in (None,0,2):
            with self.assertRaises(ValueError):
                side_arch(Mesh('bad'),0,0,0,300,1400,outward_side=side)

    def test_open_arch_never_gets_a_pane_or_floor_cap(self):
        mesh=Mesh('open');arch(mesh,0,0,0,1800,2600,160,100)
        self.assertFalse(list(triangles(mesh,'glass')))
        self.assertFalse(list(triangles(mesh,'window_dark')))
        self.assertTrue(all(any(abs(p[1])>=900 or p[2]>1000 for p in points)
            for points,_ in triangles(mesh,'limestone')))


if __name__=='__main__':unittest.main()
