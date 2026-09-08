"""Read exported animation times, including the intervals between authored keys."""
import json
import math
import struct


def animation_times(payload):
    magic, version, total = struct.unpack_from('<III', payload)
    if magic != 0x46546C67 or version != 2 or total != len(payload):
        raise ValueError('Expected a complete glTF 2 binary')
    chunks = {}
    offset = 12
    while offset < total:
        length, kind = struct.unpack_from('<II', payload, offset)
        offset += 8
        chunks[kind] = payload[offset:offset + length]
        offset += length
    doc = json.loads(chunks[0x4E4F534A])
    binary = chunks[0x004E4942]
    result = {}
    for animation in doc.get('animations', []):
        times = set()
        for sampler in animation['samplers']:
            accessor = doc['accessors'][sampler['input']]
            if accessor['componentType'] != 5126 or accessor['type'] != 'SCALAR' or 'sparse' in accessor:
                raise ValueError('Animation times must be dense float scalars')
            view = doc['bufferViews'][accessor['bufferView']]
            if view.get('buffer', 0) != 0:
                raise ValueError('Unsigned animation buffer')
            start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            stride = view.get('byteStride', 4)
            values = [struct.unpack_from('<f', binary, start + i * stride)[0] for i in range(accessor['count'])]
            if any(not math.isfinite(t) or t < 0 for t in values) or any(b <= a for a, b in zip(values, values[1:])):
                raise ValueError('Animation time inputs must increase strictly')
            times.update(values)
        if len(times) < 2:
            raise ValueError('Motion inspection requires at least two exported keys')
        name = animation['name']
        if name in result:
            raise ValueError('Duplicate animation name')
        result[name] = sorted(times)
    return result


def inspection_times(key_times):
    """Every actual key plus each midpoint; never round to the import scene FPS."""
    return sorted(set(key_times) | {(a + b) / 2 for a, b in zip(key_times, key_times[1:])})
