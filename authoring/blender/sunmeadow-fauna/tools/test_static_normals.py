import json
import struct
import unittest
import numpy as np
from static_normals import restore_static_normals, unpack, accessor


def fixture(morph=False):
    doc = {'asset': {'version': '2.0'}, 'bufferViews': [], 'accessors': [], 'meshes': []}
    binary = bytearray()
    def add(values, kind):
        data = np.asarray(values, dtype='<f4')
        index = len(doc['accessors'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': data.nbytes})
        doc['accessors'].append({'bufferView': index, 'componentType': 5126, 'count': len(data), 'type': kind})
        binary.extend(data.tobytes())
        return index
    attributes = {'POSITION': add([[0, 0, 0], [1, 0, 0]], 'VEC3'),
                  'TEXCOORD_0': add([[0, 0], [1, 0]], 'VEC2'),
                  'COLOR_0': add([[1]*4, [1]*4], 'VEC4'),
                  'TANGENT': add([[1, 0, 0, 1], [.9999, .0001, 0, 1]] if morph else [[1, 0, 0, 1]]*2, 'VEC4'),
                  'NORMAL': add([[0, .1, .995], [1, 0, 0]] if morph else [[0, 0, 1]]*2, 'VEC3')}
    primitive = {'attributes': attributes}
    if morph: primitive['targets'] = [{'POSITION': add([[0, 0, .05], [0, 0, 0]], 'VEC3')}]
    doc['meshes'] = [{'primitives': [primitive]}]
    doc['buffers'] = [{'byteLength': len(binary)}]
    encoded = json.dumps(doc).encode(); encoded += b' '*((-len(encoded))%4)
    payload = struct.pack('<III', 0x46546C67, 2, 28+len(encoded)+len(binary))
    return payload+struct.pack('<II', len(encoded), 0x4E4F534A)+encoded+struct.pack('<II', len(binary), 0x004E4942)+binary


class StaticNormalTests(unittest.TestCase):
    def test_restores_only_static_normals_and_preserves_dynamic_bytes(self):
        original = fixture(True)
        output, evidence = restore_static_normals(original, fixture())
        before, old, _ = unpack(original); after, new, _ = unpack(output)
        self.assertEqual(before, after)
        self.assertEqual(evidence['restored_static_corner_normals'], 1)
        attrs = before['meshes'][0]['primitives'][0]['attributes']
        np.testing.assert_array_equal(accessor(before, old, attrs['NORMAL'])[0], accessor(after, new, attrs['NORMAL'])[0])
        np.testing.assert_array_equal(accessor(after, new, attrs['NORMAL'])[1], [0, 0, 1])
        for name in ['POSITION', 'TANGENT', 'TEXCOORD_0', 'COLOR_0']:
            np.testing.assert_array_equal(accessor(before, old, attrs[name]), accessor(after, new, attrs[name]))
        second, second_evidence = restore_static_normals(output, fixture())
        self.assertEqual(second, output)
        self.assertEqual(second_evidence['restored_static_corner_normals'], 0)

    def test_missing_corresponding_corner_is_rejected(self):
        source = bytearray(fixture()); doc, binary, start = unpack(source)
        struct.pack_into('<f', source, start, 10)
        with self.assertRaisesRegex(ValueError, 'differs from authored base'):
            restore_static_normals(fixture(True), bytes(source))


if __name__ == '__main__': unittest.main()
