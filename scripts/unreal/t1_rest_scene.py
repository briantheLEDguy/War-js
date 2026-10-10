"""Flatten unskinned prop hierarchies at their authored rest pose, without sampling animation."""
import copy
import math


def rest_scene(document):
    """Return a static derivative plus provenance; source geometry/material buffers stay exact."""
    if (not isinstance(document, dict) or not isinstance(document.get('asset'), dict)
            or document['asset'].get('version') != '2.0' or document.get('skins')):
        raise ValueError('Rest-scene adaptation requires unskinned glTF 2.0')
    nodes, scenes = document.get('nodes'), document.get('scenes')
    selected = document.get('scene', 0)
    if (not isinstance(nodes, list) or not 1 <= len(nodes) <= 4096 or not isinstance(scenes, list)
            or isinstance(selected, bool) or not isinstance(selected, int) or not 0 <= selected < len(scenes)):
        raise ValueError('Invalid bounded rest-scene inventory')
    if not isinstance(scenes[selected], dict):
        raise ValueError('Invalid selected rest scene')
    roots = scenes[selected].get('nodes', [])
    if (not isinstance(roots, list) or not roots or any(isinstance(i, bool) or not isinstance(i, int)
            or not 0 <= i < len(nodes) for i in roots) or len(roots) != len(set(roots))):
        raise ValueError('Invalid rest-scene roots')
    flat, visiting, visited = [], set(), set()

    def vector(value, width):
        if (not isinstance(value, list) or len(value) != width or any(isinstance(v, bool)
                or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value)):
            raise ValueError('Invalid rest-scene transform')
        return value

    def product(a, b):
        x, y, z, w = a; i, j, k, s = b
        return [w*i+x*s+y*k-z*j, w*j-x*k+y*s+z*i, w*k+x*j-y*i+z*s, w*s-x*i-y*j-z*k]

    def rotate(v, q):
        p = product(product(q, [*v, 0]), [-q[0], -q[1], -q[2], q[3]])
        return p[:3]

    def visit(index, translation, rotation, scale, depth=0):
        if depth > 128:
            raise ValueError('Rest-scene hierarchy exceeds the bounded depth')
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(nodes):
            raise ValueError('Invalid rest-scene node reference')
        if index in visiting or index in visited:
            raise ValueError('Rest-scene hierarchy must have unique acyclic ownership')
        node = nodes[index]
        if not isinstance(node, dict) or 'matrix' in node or 'skin' in node or node.get('weights'):
            raise ValueError('Unsupported rest-scene deformation or matrix')
        t = vector(node.get('translation', [0, 0, 0]), 3)
        q = vector(node.get('rotation', [0, 0, 0, 1]), 4)
        s = vector(node.get('scale', [1, 1, 1]), 3)
        # Uniform positive scales avoid introducing shear during hierarchy flattening.
        if min(s) <= 0 or max(s)-min(s) > 1e-9 or abs(sum(v*v for v in q)-1) > 1e-5:
            raise ValueError('Rest-scene transforms require uniform positive scale and unit rotation')
        offset = rotate([v*scale for v in t], rotation)
        world_t = [a+b for a, b in zip(translation, offset)]
        world_q, world_s = product(rotation, q), scale*s[0]
        if max(abs(v) for v in world_t) > 10000 or not 1e-6 <= world_s <= 10000:
            raise ValueError('Unbounded composed rest-scene transform')
        visiting.add(index)
        if 'mesh' in node:
            mesh = node['mesh']
            if isinstance(mesh, bool) or not isinstance(mesh, int) or not 0 <= mesh < len(document.get('meshes', [])):
                raise ValueError('Invalid rest-scene mesh reference')
            if any(p.get('targets') for p in document['meshes'][mesh].get('primitives', [])):
                raise ValueError('Morph geometry requires a separate reviewed bake')
            flat.append(dict(name=node.get('name', 'node_'+str(index)), mesh=mesh,
                             translation=world_t, rotation=world_q, scale=[world_s]*3))
        children = node.get('children', [])
        if not isinstance(children, list):
            raise ValueError('Invalid rest-scene children')
        for child in children:
            visit(child, world_t, world_q, world_s, depth+1)
        visiting.remove(index); visited.add(index)

    for index in roots:
        visit(index, [0, 0, 0], [0, 0, 0, 1], 1)
    if not flat:
        raise ValueError('Rest scene contains no visible mesh geometry')
    result = copy.deepcopy(document)
    result['nodes'] = flat; result['scenes'] = [dict(nodes=list(range(len(flat))))]; result['scene'] = 0
    result.pop('animations', None); result.pop('skins', None)
    return result, dict(sourceNodes=len(nodes), visitedNodes=len(visited), meshNodes=len(flat),
                        omittedInactiveNodes=len(nodes)-len(visited), animationSampled=False,
                        sourceAnimations=len(document.get('animations', [])), authoredRestPose=True,
                        geometryBuffersPreserved=True, nativeIntegrated=False, appearanceApproved=False,
                        vehicleGameplayAccepted=False)
