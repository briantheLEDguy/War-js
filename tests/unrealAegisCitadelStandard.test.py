import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_standard_detail import build_central_standard


class CentralStandardTests(unittest.TestCase):
    def test_cloth_clears_real_archivolts_and_wall_in_final_coordinates(self):
        masonry, cloth, receipt = build_central_standard()
        self.assertGreater(receipt['minimumRollClearanceCm'], 300)
        self.assertGreater(receipt['minimumClothWallGapCm'], 30)
        self.assertAlmostEqual(receipt['actualHemBottomCm'], 9732)
        self.assertGreater((12400-receipt['actualHemBottomCm'])/1200, 2)
        self.assertLess(min(p[2] for p in masonry.positions), receipt['retainedWallTopCm'])
        self.assertGreater(min(p[2] for p in masonry.positions), 11000)
        self.assertFalse(receipt['nativeApproved'])

    def test_authored_support_and_cloth_have_valid_normals_and_nonzero_triangles(self):
        masonry, cloth, _ = build_central_standard()
        for mesh in (masonry, cloth):
            self.assertTrue(mesh.positions)
            for normal in mesh.normals:
                self.assertTrue(all(math.isfinite(v) for v in normal))
                self.assertAlmostEqual(sum(v*v for v in normal), 1, places=6)
            for i in range(0,len(mesh.indices),3):
                a,b,c=[mesh.positions[j] for j in mesh.indices[i:i+3]]
                u=[b[j]-a[j] for j in range(3)]; v=[c[j]-a[j] for j in range(3)]
                cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                self.assertGreater(sum(x*x for x in cross), 1e-12)


if __name__ == '__main__':
    unittest.main()
