"""Focused bounded-carve tests; real native terrain readback remains required."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'unreal'))
from aegis_citadel_terrain import (HALL_CARVE_WORLD, MOUNTAIN_ACTOR_TRANSFORM, carve_terrain,
                                   hall_terrain_probe_points, checked_native_terrain_source)


def source_triangle(points=None, reverse=False):
    points = points or [[0, 0, 6000], [20, 0, 6000], [0, 20, 6000]]
    return dict(id='actual_source_fixture', positions=points, indices=[0, 2, 1] if reverse else [0, 1, 2],
                normals=[[0, 0, 1], [0.2, 0, math.sqrt(0.96)], [0, 0.3, math.sqrt(0.91)]],
                uvs=[[0, 0], [1, 0], [0, 1]], triangleMaterials=[4], collision=True)


def volume(x0, y0, x1, y1, identity='hall', z0=5990, z1=6010):
    return dict(id=identity, coordinateSpace='world_cm', bounds=[[25000 + x0, y0, z0], [25000 + x1, y1, z1]])


def carve(source, volumes):
    return carve_terrain(source, volumes, actor_transform=MOUNTAIN_ACTOR_TRANSFORM,
                         source_provenance={'nativeReadback': False, 'fixture': 'portable_geometry_only'})


def area(mesh):
    result = 0
    for offset in range(0, len(mesh['indices']), 3):
        a, b, c = [mesh['positions'][i] for i in mesh['indices'][offset:offset + 3]]
        u, v = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        result += math.sqrt(sum(q * q for q in n)) / 2
    return result


class CitadelTerrainCarveTests(unittest.TestCase):
    def test_reduction_order_is_fixed_across_native_and_newer_python_versions(self):
        from aegis_citadel_terrain import _sum
        self.assertEqual(_sum([1e16, 1.0, -1e16]), 0.0)
        self.assertEqual(_sum([1e16, -1e16, 1.0]), 1.0)
        self.assertEqual(_sum([]), 0)

    def test_outside_face_and_buffers_are_bitwise_identical(self):
        source = source_triangle(); before = deepcopy(source)
        result, receipt = carve(source, [volume(30, 30, 40, 40)])
        self.assertEqual(result, source)
        self.assertEqual(source, before)
        self.assertEqual(receipt['outsidePreservation']['sourceTriangleIds'], [0])
        self.assertEqual(receipt['sourceMeshSha256'], receipt['outputMeshSha256'])

    def test_triangle_crossing_box_survives_outside_with_exact_area_and_attributes(self):
        source = source_triangle(); before = deepcopy(source)
        # All source vertices lie outside the box, yet the face crosses it.
        result, receipt = carve(source, [volume(5, 5, 10, 10)])
        self.assertAlmostEqual(area(result), 175)
        self.assertAlmostEqual(receipt['discardedSurfaceAreaCm2'], 25)
        self.assertEqual(source, before)
        for key in ('positions', 'normals', 'uvs'):
            self.assertEqual(result[key][:3], source[key])
        for witness in receipt['addedBoundaryVertices']:
            ids, weights = witness['sourceIndices'], witness['weights']
            expected_uv = [sum(weights[j] * source['uvs'][ids[j]][k] for j in range(3)) for k in range(2)]
            n = [sum(weights[j] * source['normals'][ids[j]][k] for j in range(3)) for k in range(3)]
            length = math.sqrt(sum(q * q for q in n)); n = [q / length for q in n]
            self.assertEqual(witness['uv'], expected_uv)
            # This independently computed mathematical normal can round one ULP
            # differently on newer Python; native receipt reproduction stays exact.
            for actual, expected in zip(witness['normal'], n):
                self.assertAlmostEqual(actual, expected, places=15)
        self.assertEqual(set(result['triangleMaterials']), {4})

    def test_overlapping_volumes_remove_union_once(self):
        result, receipt = carve(source_triangle(), [volume(5, -1, 10, 21, 'first'), volume(8, -1, 12, 21, 'second')])
        self.assertAlmostEqual(area(result), 119.5)
        self.assertAlmostEqual(receipt['discardedSurfaceAreaCm2'], 80.5)

    def test_input_winding_is_preserved_for_both_conventions(self):
        for reverse in (False, True):
            result, _ = carve(source_triangle(reverse=reverse), [volume(5, 5, 10, 10)])
            for offset in range(0, len(result['indices']), 3):
                a, b, c = [result['positions'][i] for i in result['indices'][offset:offset + 3]]
                signed = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                self.assertLess(signed, 0) if reverse else self.assertGreater(signed, 0)

    def test_native_corner_colors_tangents_handedness_and_uv_channels_are_preserved(self):
        source = source_triangle()
        source['vertexColors'] = [[1, 0.4, 0.2, 1], [0.1, 0.8, 0.3, 0.8], [0.2, 0.1, 0.9, 0.5]]
        source['tangents'] = [[1, 0, 0], [math.sqrt(0.96), 0, -0.2], [1, 0, 0]]
        source['binormalSigns'] = [1, 1, 1]
        source['uvChannels'] = [deepcopy(source['uvs']), [[0.1, 0.2], [0.3, 0.2], [0.1, 0.6]]]
        source['materialSlots'] = ['Outside_mountain', 'Unused_source_slot']
        before = deepcopy(source)
        result, receipt = carve(source, [volume(5, 5, 10, 10)])
        self.assertEqual(source, before)
        for key in ('positions', 'normals', 'uvs', 'vertexColors', 'tangents', 'binormalSigns'):
            self.assertEqual(result[key][:3], source[key])
            self.assertEqual(len(result[key]), len(result['positions']))
        self.assertEqual(result['materialSlots'], source['materialSlots'])
        for channel, old in zip(result['uvChannels'], source['uvChannels']):
            self.assertEqual(channel[:3], old)
            self.assertEqual(len(channel), len(result['positions']))
        self.assertEqual(result['uvChannels'][0], result['uvs'])
        for witness in receipt['addedBoundaryVertices']:
            index, ids, weights = witness['index'], witness['sourceIndices'], witness['weights']
            colors = [sum(weights[j] * source['vertexColors'][ids[j]][k] for j in range(3)) for k in range(4)]
            for actual, expected in zip(result['vertexColors'][index], colors):
                self.assertAlmostEqual(actual, expected, places=15)
            tangent = result['tangents'][index]
            self.assertAlmostEqual(sum(v * v for v in tangent), 1)
            self.assertAlmostEqual(sum(tangent[k] * result['normals'][index][k] for k in range(3)), 0)
            self.assertEqual(result['binormalSigns'][index], 1)

    def test_native_corner_hard_and_uv_seams_remain_separate(self):
        source = source_triangle()
        # Same geometric face twice, with different per-corner attributes. Native
        # readback intentionally expands corners instead of losing this seam.
        source['positions'] += deepcopy(source['positions'])
        source['normals'] += [[0, 0, -1]] * 3
        source['uvs'] += [[2, 2], [3, 2], [2, 3]]
        source['indices'] += [3, 4, 5]
        source['triangleMaterials'] += [7]
        result, receipt = carve(source, [volume(5, 5, 10, 10)])
        vertices = receipt['addedBoundaryVertices']
        self.assertTrue(vertices)
        left = [v for v in vertices if max(v['sourceIndices']) < 3]
        right = [v for v in vertices if min(v['sourceIndices']) >= 3]
        self.assertEqual(len(left), len(right))
        by_point = {tuple(v['position']): v for v in left}
        for vertex in right:
            other = by_point[tuple(vertex['position'])]
            self.assertNotEqual(vertex['index'], other['index'])
            self.assertNotEqual(vertex['uv'], other['uv'])
            self.assertNotEqual(vertex['normal'], other['normal'])
        self.assertEqual(set(result['triangleMaterials']), {4, 7})

    def test_ambiguous_attributes_and_crossing_handedness_seams_fail_closed(self):
        for key, values in (('vertexColors', [[1, 1, 1, 1]]), ('tangents', [[0, 0, 0]]),
                            ('binormalSigns', [1, float('nan'), 1]), ('uvChannels', [[[0, 0]] * 3]),
                            ('cornerAttributes', [])):
            source = source_triangle(); source[key] = values
            with self.assertRaises(ValueError): carve(source, [volume(5, 5, 10, 10)])
        source = source_triangle(); source['binormalSigns'] = [1, -1, 1]
        with self.assertRaises(ValueError): carve(source, [volume(5, 5, 10, 10)])
        # An unchanged face is preserved verbatim even if its native sign varies.
        result, _ = carve(source, [volume(30, 30, 40, 40)])
        self.assertEqual(result, source)

    def test_registered_zero_tangent_and_sign_defaults_remain_stored_zeros(self):
        source = source_triangle(); source['tangents'] = [[0,0,0]] * 3; source['binormalSigns'] = [0,0,0]
        result, receipt = carve(source, [volume(5,5,10,10)])
        self.assertEqual(result['tangents'][:3], source['tangents'])
        self.assertEqual(result['binormalSigns'][:3], source['binormalSigns'])
        self.assertTrue(all(v == [0,0,0] for v in result['tangents']))
        self.assertEqual(set(result['binormalSigns']), {0})
        self.assertTrue(receipt['addedBoundaryVertices'])

    def test_face_exactly_on_closed_volume_boundary_is_not_duplicated(self):
        result, receipt = carve(source_triangle(), [volume(-1, -1, 21, 21, z0=6000)])
        self.assertEqual(result['indices'], [])
        self.assertEqual(receipt['fullyRemovedSourceTriangles'], [0])
        self.assertAlmostEqual(receipt['discardedSurfaceAreaCm2'], 200)

    def test_real_hall_volume_binds_local_translation_and_missed_probe_strip(self):
        source = source_triangle([[7800, 0, 6064.583587646484], [8450, 0, 6948.417663574219],
                                  [8450, 945.4545021057129, 6895.5108642578125]])
        result, receipt = carve(source, [HALL_CARVE_WORLD])
        self.assertEqual(result['indices'], [])
        self.assertEqual(receipt['localVolumeBounds'], [[[960.0, -4260.0, 5980.0], [8460.0, 4260.0, 24000.0]]])
        probes = hall_terrain_probe_points()
        for point in ([33286, 0, 6010], [33400, 0, 6010], [33460, 4210, 6010], [33460, -4210, 6010]):
            self.assertIn(point, [p['point'] for p in probes])
        for flag in ('nativeSourceVerified', 'nativeCollisionVerified', 'visualApproved'):
            self.assertIs(receipt[flag], False)

    def test_invalid_coordinate_transform_volume_and_source_fail_closed(self):
        source = source_triangle()
        transform = deepcopy(MOUNTAIN_ACTOR_TRANSFORM); transform['scale'][0] = 2
        with self.assertRaises(ValueError):
            carve_terrain(source, [HALL_CARVE_WORLD], actor_transform=transform, source_provenance={})
        bad = volume(5, 5, 10, 10); bad['coordinateSpace'] = 'actor_local_cm'
        with self.assertRaises(ValueError): carve(source, [bad])
        bad = volume(5, 5, 10, 10); bad['bounds'][1][0] = 50000
        with self.assertRaises(ValueError): carve(source, [bad])
        bad = source_triangle(); bad['indices'][0] = 999
        with self.assertRaises(ValueError): carve(bad, [HALL_CARVE_WORLD])
        bad = source_triangle(); bad['uvs'][0][0] = float('nan')
        with self.assertRaises(ValueError): carve(bad, [HALL_CARVE_WORLD])

    def test_committed_native_export_requires_actual_corner_order_channels_and_material_mapping(self):
        source = source_triangle(); source['uvChannels'] = [deepcopy(source['uvs'])]
        mesh = '/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain'
        report = dict(schemaVersion=1, readOnly=True, available=True, valid=True, lod=0, mesh=mesh,
            invalidValues=0, sourcePolicy='committed_mesh_description_bulk_data_no_working_copy',
            coordinateSpace='mesh_local_cm', triangleOrder='native_triangle_ids_and_corner_order',
            optionalAttributePolicy='stored_registered_values_authorship_not_inferred', data=source,
            sourceTriangleCount=1, sourceVertexCount=3, sourceVertexInstanceCount=3,
            triangleIds=[11], trianglePolygonIds=[4], trianglePolygonGroupIds=[2],
            cornerVertexIds=[0,1,2], cornerVertexInstanceIds=[0,1,2],
            materialSlots=[dict(index=i, slotName='slot'+str(i), importedSlotName='slot'+str(i),
                material='/Game/Materials/M.M') for i in range(5)],
            polygonGroups=[dict(id=2, slotName='slot4', materialIndex=4)])
        result = checked_native_terrain_source(report, mesh)
        self.assertEqual(result, source)
        self.assertIsNot(result, source)
        for mutate in (
            lambda r:r.update(sourcePolicy='working_editor_mesh_description'),
            lambda r:r.update(readOnly=False), lambda r:r.update(valid=False),
            lambda r:r.update(schemaVersion=True), lambda r:r.update(lod=False),
            lambda r:r.update(invalidValues=1), lambda r:r.update(mesh=mesh+'_other'),
            lambda r:r.update(sourceTriangleCount=2), lambda r:r['data'].update(indices=[0,2,1]),
            lambda r:r['data'].pop('uvChannels'), lambda r:r['polygonGroups'][0].update(materialIndex=3),
            lambda r:r['materialSlots'][4].update(material=None), lambda r:r.update(cornerVertexIds=[0,1]),
        ):
            altered = deepcopy(report); mutate(altered)
            with self.assertRaises(ValueError): checked_native_terrain_source(altered, mesh)


if __name__ == '__main__': unittest.main()
