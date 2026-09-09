import unittest
from collections import Counter
import numpy as np
from hoof_geometry import add_deer_hoof


class CaptureCage:
    def __init__(self): self.parts = []
    def add(self, name, vertices, faces, coordinates, weights):
        self.parts.append((name, np.asarray(vertices), faces, coordinates, weights))


class HoofGeometryTests(unittest.TestCase):
    def test_each_lod_has_closed_outward_shells_and_a_real_cleft(self):
        counts = []
        for lod in range(3):
            cage = CaptureCage()
            add_deer_hoof(cage, [.13, -.345, .037], 1, 'L', 'front', lod, lambda u, v, tile: (u, v, tile))
            self.assertEqual(len(cage.parts), 2)
            counts.append(sum(len(part[1]) for part in cage.parts))
            negative, positive = cage.parts
            self.assertGreater(positive[1][:, 0].min()-negative[1][:, 0].max(), .0005)
            for _, vertices, faces, coordinates, weights in cage.parts:
                directed = Counter((face[index], face[(index+1)%len(face)]) for face in faces for index in range(len(face)))
                self.assertTrue(all(count == 1 and directed[(b, a)] == 1 for (a, b), count in directed.items()))
                volume = sum(np.dot(vertices[face[0]], np.cross(vertices[face[index]], vertices[face[index+1]]))/6 for face in faces for index in range(1, len(face)-1))
                self.assertGreater(volume, 0)
                self.assertTrue(np.isfinite(vertices).all())
                self.assertGreaterEqual(vertices[:, 2].min(), 0)
                self.assertTrue(all(weight == {'hoof_front_L': 1} for weight in weights))
                self.assertTrue(all(uv[2] == 7 for face in coordinates for uv in face))
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])


if __name__ == '__main__':
    unittest.main()
