"""Upper-roof geometry controls; these do not grant native visual acceptance."""
import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_crown import _CrownMesh
from aegis_citadel_mesh import MATERIALS, cross
from aegis_citadel_spire_detail import articulated_spire


class CitadelSpireTests(unittest.TestCase):
    def test_upper_roofs_fit_existing_cap_envelope_and_retain_height(self):
        for width, bottom, peak in ((820,14290,16680), (670,13590,15780),
                                    (1160,14910,17200), (350,14970,16280)):
            mesh=_CrownMesh('roof')
            receipt=articulated_spire(mesh,31200,0,bottom,peak,width)
            self.assertGreaterEqual(min(p[2] for p in mesh.positions),bottom-7)
            self.assertEqual(max(p[2] for p in mesh.positions),peak)
            # Rod radii are included explicitly in the source envelope.
            for p in mesh.positions:
                self.assertLessEqual(abs(p[0]-31200),width*.5175+8)
                self.assertLessEqual(abs(p[1]),width*.5175+8)
            self.assertEqual(len(receipt['dormers']),4)
            self.assertTrue(all(d['topCm']<peak-110 for d in receipt['dormers']))
            self.assertTrue(receipt['freshNativeEvidenceRequired'])
            self.assertFalse(receipt['visualApproval'])

    def test_roof_faces_have_valid_normals_and_float32_texture_areas(self):
        mesh=_CrownMesh('roof');articulated_spire(mesh,30050,-2610,13650,15780,670)
        f32=lambda v:struct.unpack('f',struct.pack('f',v))[0]
        self.assertGreater(len(mesh.indices),1000)
        for offset in range(0,len(mesh.indices),3):
            ids=mesh.indices[offset:offset+3];a,b,c=[mesh.positions[i] for i in ids]
            n=cross([b[k]-a[k] for k in range(3)],[c[k]-a[k] for k in range(3)])
            length=math.sqrt(sum(v*v for v in n));self.assertGreater(length,1e-5)
            for index in ids:
                self.assertGreater(sum(n[k]*mesh.normals[index][k] for k in range(3))/length,.999999)
            uv=[[f32(v) for v in mesh.uvs[i]] for i in ids]
            area=(uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0])
            self.assertGreater(abs(area),1e-10)
        self.assertIn(MATERIALS.index('window_dark'),mesh.triangle_materials)

    def test_lower_geometry_and_invalid_inputs_cannot_use_upper_roof_helper(self):
        for args in ((0,0,9000,13000,650),(0,0,9001,13000,650),(0,0,12000,12500,650),
                     (0,0,12000,15000,100),(float('nan'),0,12000,15000,650)):
            mesh=_CrownMesh('roof')
            with self.assertRaises(ValueError):articulated_spire(mesh,*args)
            self.assertFalse(mesh.positions)

    def test_roof_source_is_deterministic(self):
        a,b=_CrownMesh('roof'),_CrownMesh('roof')
        self.assertEqual(articulated_spire(a,30000,0,13590,15780,670),
                         articulated_spire(b,30000,0,13590,15780,670))
        self.assertEqual(a.export(),b.export())


if __name__=='__main__':unittest.main()
