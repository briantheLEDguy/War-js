import math
import unittest
from road_junctions import connected_junctions, transition_polygons


def road(points, width=8):
    return {'points': [{'x':x,'z':z} for x,z in points], 'width':width}


class RoundedRoadJunctions(unittest.TestCase):
    def test_shared_endpoint_uses_widest_touching_route(self):
        nodes=connected_junctions([road([(-20,0),(0,0)],12),road([(0,0),(0,20)],5),road([(0,0),(20,0)],8)])
        self.assertEqual(len(nodes),1)
        self.assertEqual(nodes[0]['inner_radius'],5.65)
        self.assertEqual(nodes[0]['outer_radius'],6.6)

    def test_endpoint_on_segment_interior_is_joined(self):
        nodes=connected_junctions([road([(-20,0),(20,0)]),road([(0,0),(0,20)])])
        self.assertEqual([(p['x'],p['z']) for p in nodes],[(0,0)])

    def test_isolated_and_reversed_duplicate_alignments_have_no_caps(self):
        self.assertEqual(connected_junctions([road([(-20,0),(20,0)]),road([(20,0),(-20,0)])]),[])
        self.assertEqual(connected_junctions([road([(-20,0),(20,0)]),road([(0,2),(0,20)])]),[])

    def test_explicit_tessellation_has_opaque_core_feather_and_bounded_spacing(self):
        node=connected_junctions([road([(-20,0),(0,0)],12),road([(0,0),(0,20)])])[0]
        polygons=list(transition_polygons(node));area=0
        for polygon in polygons:
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                self.assertLessEqual(math.hypot(a[0]-b[0],a[1]-b[1]),2.001)
                area+=(a[0]*b[1]-a[1]*b[0])/2
                radius=math.hypot(a[0],a[1]);self.assertLessEqual(radius,node['outer_radius']+1e-8)
                self.assertEqual(a[2],0 if abs(radius-node['outer_radius'])<1e-8 else 1)
        self.assertGreater(area,math.pi*node['outer_radius']**2*.99)


if __name__=='__main__':unittest.main()
