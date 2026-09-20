"""Remove sub-microradian float noise from sparse exported morph normals.

Blender emits tiny normal differences even on unchanged faces of a shape key.
Pruning only this numerical residue keeps limb-local targets actually sparse.
Positions, weights, material images and meaningful normal deltas are untouched.
"""
import json
import math
import struct


def prune_morph_normals(payload, tolerance=1e-6):
    magic, version, length = struct.unpack_from('<III', payload)
    if magic != 0x46546C67 or version != 2 or length != len(payload):
        raise ValueError('Expected complete glTF binary')
    json_length = struct.unpack_from('<I', payload, 12)[0]
    doc = json.loads(payload[20:20+json_length])
    binary = payload[28+json_length:]
    views = [binary[view.get('byteOffset', 0):view.get('byteOffset', 0)+view['byteLength']] for view in doc['bufferViews']]
    removed = 0; maximum = 0
    for mesh in doc.get('meshes', []):
        for primitive in mesh['primitives']:
            for target in primitive.get('targets', []):
                if 'NORMAL' not in target:
                    continue
                accessor = doc['accessors'][target['NORMAL']]
                if accessor.get('componentType') != 5126 or accessor.get('type') != 'VEC3' or 'bufferView' in accessor:
                    raise ValueError('Expected sparse float normal delta accessor')
                sparse = accessor.get('sparse')
                if not sparse:
                    continue
                source_indices = views[sparse['indices']['bufferView']]
                source_values = views[sparse['values']['bufferView']]
                fmt, width = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4)}[sparse['indices']['componentType']]
                indices, values = bytearray(), bytearray()
                for index in range(sparse['count']):
                    start = sparse['values'].get('byteOffset', 0)+index*12
                    delta = struct.unpack_from('<fff', source_values, start)
                    magnitude = math.sqrt(sum(value*value for value in delta))
                    if magnitude <= tolerance:
                        removed += 1; maximum = max(maximum, magnitude)
                    else:
                        at = sparse['indices'].get('byteOffset', 0)+index*width
                        indices.extend(source_indices[at:at+width]); values.extend(source_values[start:start+12])
                if not indices:
                    del accessor['sparse']
                else:
                    indices_view = len(views); values_view = indices_view+1
                    views.extend([bytes(indices), bytes(values)])
                    doc['bufferViews'].extend([{'buffer': 0, 'byteLength': len(indices)}, {'buffer': 0, 'byteLength': len(values)}])
                    accessor['sparse'] = {'count': len(indices)//width, 'indices': {'bufferView': indices_view, 'componentType': sparse['indices']['componentType']}, 'values': {'bufferView': values_view}}
                accessor.pop('min', None); accessor.pop('max', None)
    referenced = set()
    def visit(value, mapping=None):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'bufferView':
                    if mapping is None: referenced.add(child)
                    else: value[key] = mapping[child]
                else: visit(child, mapping)
        elif isinstance(value, list):
            for child in value: visit(child, mapping)
    visit(doc)
    mapping = {old: index for index, old in enumerate(sorted(referenced))}
    packed = bytearray(); new_views = []
    for old in sorted(referenced):
        packed.extend(b'\0'*((-len(packed))%4))
        view = dict(doc['bufferViews'][old]); view['byteOffset'] = len(packed)
        packed.extend(views[old]); new_views.append(view)
    visit(doc, mapping)
    doc['bufferViews'] = new_views
    doc['buffers'][0]['byteLength'] = len(packed)
    packed.extend(b'\0'*((-len(packed))%4))
    json_bytes = json.dumps(doc, separators=(',', ':')).encode()
    json_bytes += b' '*((-len(json_bytes))%4)
    result = struct.pack('<III', magic, version, 28+len(json_bytes)+len(packed))+struct.pack('<II', len(json_bytes), 0x4E4F534A)+json_bytes+struct.pack('<II', len(packed), 0x004E4942)+packed
    return result, {'removed_normal_noise_vectors': removed, 'maximum_removed_normal_delta': maximum, 'bytes_saved': len(payload)-len(result)}
