import json
import struct
import unittest
from prune_morph_normals import prune_morph_normals


class SparseNormalTests(unittest.TestCase):
    @staticmethod
    def fixture():
        pieces = [struct.pack('<HH', 0, 1), struct.pack('<ffffff', 1e-7, 0, 0, .001, .002, 0), b'EXACT_TEXTURE_BYTES']
        binary = bytearray(); views = []
        for piece in pieces:
            binary.extend(b'\0'*((-len(binary))%4))
            views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(piece)})
            binary.extend(piece)
        doc = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}], 'bufferViews': views,
               'accessors': [{'componentType': 5126, 'count': 2, 'type': 'VEC3', 'sparse': {'count': 2, 'indices': {'bufferView': 0, 'componentType': 5123}, 'values': {'bufferView': 1}}}, {'componentType': 5123, 'count': 2, 'type': 'SCALAR', 'bufferView': 0}],
               'meshes': [{'primitives': [{'targets': [{'NORMAL': 0}]}]}], 'images': [{'bufferView': 2}]}
        text = json.dumps(doc).encode(); text += b' '*((-len(text))%4); binary.extend(b'\0'*((-len(binary))%4))
        return struct.pack('<III', 0x46546C67, 2, 28+len(text)+len(binary))+struct.pack('<II', len(text), 0x4E4F534A)+text+struct.pack('<II', len(binary), 0x004E4942)+binary

    def test_only_noise_is_removed_and_shared_views_are_preserved(self):
        payload, evidence = prune_morph_normals(self.fixture())
        size = struct.unpack_from('<I', payload, 12)[0]
        doc = json.loads(payload[20:20+size]); binary = payload[28+size:]
        self.assertEqual(evidence['removed_normal_noise_vectors'], 1)
        sparse = doc['accessors'][0]['sparse']
        self.assertEqual(sparse['count'], 1)
        def content(index):
            view = doc['bufferViews'][index]
            self.assertEqual(view['byteOffset']%4, 0)
            return binary[view['byteOffset']:view['byteOffset']+view['byteLength']]
        self.assertEqual(content(doc['accessors'][1]['bufferView']), struct.pack('<HH', 0, 1))
        self.assertEqual(content(doc['images'][0]['bufferView']), b'EXACT_TEXTURE_BYTES')
        self.assertEqual(content(sparse['indices']['bufferView']), struct.pack('<H', 1))
        self.assertEqual(content(sparse['values']['bufferView']), struct.pack('<fff', .001, .002, 0))
        second, repeat = prune_morph_normals(payload)
        self.assertEqual(second, payload)
        self.assertEqual(repeat['removed_normal_noise_vectors'], 0)


if __name__ == '__main__':
    unittest.main()
