"""Keep authored corner normals on vertices untouched by every morph target.

Blender's morph exporter reads Basis.normals_split_get rather than the mesh's
corner normals. These differ on some folded ear/hoof surfaces. Restore only
proven static corners from the matching uncorrected GLB; deformed corners are
never substituted or approximated.
"""
import json
import struct
import numpy as np


def unpack(payload):
    if struct.unpack_from('<III', payload) != (0x46546C67, 2, len(payload)):
        raise ValueError('Expected complete glTF binary')
    size = struct.unpack_from('<I', payload, 12)[0]
    return json.loads(payload[20:20+size]), bytearray(payload[28+size:]), 28+size


def accessor(doc, binary, index):
    item = doc['accessors'][index]
    dtype = np.dtype({5121: '<u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[item['componentType']])
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[item['type']]
    result = np.zeros((item['count'], width), dtype=dtype)
    if 'bufferView' in item:
        view = doc['bufferViews'][item['bufferView']]
        result[:] = np.ndarray(result.shape, dtype=dtype, buffer=binary,
                               offset=view.get('byteOffset', 0)+item.get('byteOffset', 0),
                               strides=(view.get('byteStride', width*dtype.itemsize), dtype.itemsize))
    if 'sparse' in item:
        sparse = item['sparse']; indices = sparse['indices']; values = sparse['values']
        vi = doc['bufferViews'][indices['bufferView']]; vv = doc['bufferViews'][values['bufferView']]
        index_type = {5121: '<u1', 5123: '<u2', 5125: '<u4'}[indices['componentType']]
        locations = np.frombuffer(binary, index_type, sparse['count'], vi.get('byteOffset', 0)+indices.get('byteOffset', 0))
        data = np.frombuffer(binary, dtype, sparse['count']*width, vv.get('byteOffset', 0)+values.get('byteOffset', 0)).reshape(-1, width)
        result[locations] = data
    return result


def restore_static_normals(payload, reference_payload):
    doc, binary, binary_offset = unpack(payload)
    reference, source, _ = unpack(reference_payload)
    names = ['POSITION', 'TEXCOORD_0', 'COLOR_0']
    original = {}
    for mesh in reference['meshes']:
        for primitive in mesh['primitives']:
            values = [accessor(reference, source, primitive['attributes'][name]) for name in names]
            normals = accessor(reference, source, primitive['attributes']['NORMAL'])
            for index, normal in enumerate(normals):
                key = b''.join(value[index].tobytes() for value in values)
                if key in original and not np.array_equal(original[key], normal):
                    raise ValueError('Ambiguous authored corner normal')
                original[key] = normal
    count = 0; maximum = 0; dynamic_difference = 0
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            values = [accessor(doc, binary, primitive['attributes'][name]) for name in names]
            normal_index = primitive['attributes']['NORMAL']
            normals = accessor(doc, binary, normal_index)
            moving = np.zeros(len(normals), dtype=bool)
            for target in primitive.get('targets', []):
                for name in ['POSITION', 'NORMAL', 'TANGENT']:
                    if name in target:
                        moving |= np.any(accessor(doc, binary, target[name]) != 0, axis=1)
            attribute = doc['accessors'][normal_index]; view = doc['bufferViews'][attribute['bufferView']]
            if attribute['componentType'] != 5126 or attribute['type'] != 'VEC3' or 'sparse' in attribute:
                raise ValueError('Expected dense float basis normals')
            for index, normal in enumerate(normals):
                key = b''.join(value[index].tobytes() for value in values)
                if key not in original: raise ValueError('Candidate corner differs from authored base')
                difference = float(np.linalg.norm(original[key]-normal))
                if moving[index]:
                    dynamic_difference = max(dynamic_difference, difference)
                    continue
                if not np.array_equal(original[key], normal):
                    offset = view.get('byteOffset', 0)+attribute.get('byteOffset', 0)+index*view.get('byteStride', 12)
                    binary[offset:offset+12] = original[key].tobytes()
                    count += 1; maximum = max(maximum, difference)
    return payload[:binary_offset]+bytes(binary), {'restored_static_corner_normals': count, 'maximum_original_normal_difference': maximum, 'maximum_untouched_dynamic_normal_difference': dynamic_difference}
