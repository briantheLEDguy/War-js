"""Exact capital target sources and static rest-pose extraction for their existing models."""
import copy
import json
import struct
from pathlib import Path
from world_static import read_glb, rotate, digest, combine_parts

MODELS = {'aegis_capital': ('dummy', 'prop_training_dummy_t1.glb'),
          'riftspire_capital': ('riftspire_training_dummy', 'prop_riftspire_training_dummy.glb')}


def targets(source):
    key, model = MODELS[source['id']]
    rows = source['enemies']
    expected = {source['id']+'_training_dummy_'+str(i) for i in (1, 2, 3)}
    if len(rows) != 3 or {row['id'] for row in rows} != expected:
        raise ValueError('Capital training target identities changed')
    if any(row.get('assetKey') != key or row.get('model', model) != model
           or row.get('aggroRange') != 0 or row.get('characterProfileKey') or row.get('archetype') for row in rows):
        raise ValueError('Capital target model or passive behavior changed')
    return rows, model


def multiply(a, b):
    x,y,z,w = a; X,Y,Z,W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def rest_scene(document):
    """Bake unskinned object hierarchy transforms, retaining every source mesh/material."""
    doc = copy.deepcopy(document)
    if doc.get('skins'): raise ValueError('A skeletal model cannot be used as a static dummy')
    nodes, flat, visited = doc['nodes'], [], set()

    def visit(index, position, rotation):
        if index in visited: raise ValueError('Duplicate or cyclic source node')
        visited.add(index); node = nodes[index]
        if 'matrix' in node or node.get('scale', [1,1,1]) != [1,1,1]:
            raise ValueError('Unsupported dummy hierarchy transform')
        offset = rotate(node.get('translation', [0,0,0]), rotation)
        point = [position[i]+offset[i] for i in range(3)]
        orientation = multiply(rotation, node.get('rotation', [0,0,0,1]))
        if 'mesh' in node:
            result = {k:v for k,v in node.items() if k != 'children'}
            result.update(translation=point, rotation=orientation)
            flat.append(result)
        for child in node.get('children', []): visit(child, point, orientation)

    for index in doc['scenes'][doc.get('scene',0)]['nodes']: visit(index, [0,0,0], [0,0,0,1])
    if len(visited) != len(nodes): raise ValueError('Unreferenced source nodes')
    doc['nodes'] = flat; doc['scenes'] = [{'nodes':list(range(len(flat)))}]; doc['scene'] = 0
    doc.pop('animations', None)
    return doc


def export_model(source, directory):
    data = source.read_bytes(); size, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4e4f534a: raise ValueError('Missing GLB JSON')
    document = rest_scene(json.loads(data[20:20+size]))
    for image in document.get('images', []):
        if 'uri' in image:
            image['uri'] = str((source.parent/image['uri']).resolve())
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary = data[20+size:]
    flattened = directory/(source.stem+'-rest.glb')
    flattened.write_bytes(struct.pack('<III', 0x46546c67, 2, 20+len(encoded)+len(binary))
                          + struct.pack('<II', len(encoded), 0x4e4f534a)+encoded+binary)
    exported = read_glb(flattened)
    return {'model':source.name, 'sourceSha256':digest(source), 'restPoseOnly':True,
            'surface':combine_parts(exported['parts'])}
