"""Compare real committed clone readbacks to the exact source-derived clip.

This module has no Unreal dependency or mutation. Calling it with test documents
is a portable comparison test, never native evidence or physical approval.
"""
import hashlib
import json
import math
import struct
from collections import Counter

SOURCE_POLICY = 'committed_mesh_description_bulk_data_no_working_copy'
CORNER_POLICY = 'all_stored_vertex_instances_in_native_id_order_including_unused'


def _f32(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Committed attribute must be finite numeric data')
    result = struct.unpack('f', struct.pack('f', value))[0]
    if not math.isfinite(result):
        raise ValueError('Committed attribute exceeds native float32 storage')
    return result


def _stored(values):
    return [_stored(value) if isinstance(value, list) else _f32(value) for value in values]


def checked_committed_carve(wrapper, referenced, stored, target_mesh, original_stored):
    """Verify all stored corners (unused included), oriented faces and material groups."""
    if (wrapper.get('schemaVersion') != 1 or referenced.get('mesh') != target_mesh
            or stored.get('mesh') != target_mesh or stored.get('schemaVersion') != 1
            or any(row.get('readOnly') is not True or row.get('available') is not True
                   or row.get('valid') is not True or row.get('sourcePolicy') != SOURCE_POLICY
                   for row in (referenced, stored))
            or stored.get('cornerPolicy') != CORNER_POLICY or stored.get('invalidValues') != 0):
        raise ValueError('Actual committed native source/stored-corner readback is incomplete')
    payload = wrapper['sourceExportPayload']
    if hashlib.sha256(payload.encode()).hexdigest() != wrapper['sourceExportSha256']:
        raise ValueError('Actual raw original source payload SHA changed')
    original = json.loads(payload)
    if (original_stored.get('mesh') != original['mesh'] or original_stored.get('schemaVersion') != 1
            or any(original_stored.get(key) is not True for key in ('available','valid','readOnly'))
            or original_stored.get('sourcePolicy') != SOURCE_POLICY
            or original_stored.get('cornerPolicy') != CORNER_POLICY):
        raise ValueError('Actual complete original native topology is required')
    source, expected = original['data'], wrapper['data']
    attribute_keys = set(expected) - {'indices', 'triangleMaterials'}
    if set(stored['data']) != attribute_keys or set(expected) != set(source):
        raise ValueError('Stored native registered attribute set changed')
    count, prefix = len(expected['positions']), len(source['positions'])
    old_ids=original_stored['instanceIds'];old_count=len(old_ids)
    if len(set(old_ids))!=old_count or old_ids!=sorted(old_ids) or not old_ids:
        raise ValueError('Original native instance identities are invalid')
    boundary_ids=list(range(max(old_ids)+1,max(old_ids)+1+count-prefix))
    expected_ids=old_ids+boundary_ids
    if (stored['instanceIds']!=expected_ids or stored['sourceVertexInstanceCount']!=len(expected_ids)
            or referenced['sourceVertexInstanceCount']!=len(expected_ids)):
        raise ValueError('Original native instances or appended boundary identities changed')
    old_index={value:index for index,value in enumerate(old_ids)}
    new_index={value:index for index,value in enumerate(expected_ids)}
    prefix_map=original['cornerVertexInstanceIds']
    if len(prefix_map)!=prefix or len(original['cornerVertexIds'])!=prefix:
        raise ValueError('Original expanded corner-to-native topology is incomplete')
    mapped=prefix_map+boundary_ids
    for key in attribute_keys:
        before=original_stored['data'][key];after=stored['data'][key]
        expected_boundary=expected[key]
        if key=='uvChannels':
            if len(after)!=len(before) or any(a[:old_count]!=b or a[old_count:]!=_stored(e[prefix:]) for a,b,e in zip(after,before,expected_boundary)):
                raise ValueError('All original stored UVs and boundary UVs must survive')
            expanded=[[channel[old_index[value]] for value in prefix_map] for channel in before]
        else:
            if after[:old_count]!=before or after[old_count:]!=_stored(expected_boundary[prefix:]):
                raise ValueError('Committed original/boundary stored attribute changed: '+key)
            expanded=[before[old_index[value]] for value in prefix_map]
        if expanded!=_stored(source[key]):
            raise ValueError('Raw original expansion differs from complete stored attributes: '+key)
        if key == 'uvChannels':
            if len(expected[key]) != len(source[key]) or any(channel[:prefix] != old for channel, old in zip(expected[key], source[key])):
                raise ValueError('Original source UV prefix changed')
        elif expected[key][:prefix] != source[key]:
            raise ValueError('Original source attribute prefix changed: ' + key)
    indices = expected['indices']
    if len(indices) % 3 or any(type(index) is not int or not 0 <= index < count for index in indices):
        raise ValueError('Clipped face indices are invalid')
    actual = referenced['data']
    if set(actual) != set(expected) or actual['indices'] != list(range(len(indices))):
        raise ValueError('Referenced source face expansion changed')
    for key in attribute_keys:
        values=stored['data'][key];ids=referenced['cornerVertexInstanceIds']
        expanded=[[channel[new_index[index]] for index in ids] for channel in values] if key=='uvChannels' else [values[new_index[index]] for index in ids]
        if actual[key]!=expanded:raise ValueError('Referenced face attributes differ from stored native instances: '+key)
    triangles = len(indices)//3
    if (referenced['sourceTriangleCount'] != triangles or stored['sourceTriangleCount'] != triangles
            or referenced['materialSlots'] != original['materialSlots']
            or referenced['polygonGroups'] != original['polygonGroups']):
        raise ValueError('Native triangle count/material slots/polygon groups changed')
    boundary = {row['index']: row['sourceIndices'][0]//3 for row in wrapper['carveReceipt']['addedBoundaryVertices']}
    origins = []
    for offset in range(0, len(indices), 3):
        faces = {index//3 if index < prefix else boundary[index] for index in indices[offset:offset+3]}
        if len(faces) != 1:
            raise ValueError('Clipped face crosses original corner/material seams')
        origins.append(next(iter(faces)))
    expected_groups = [original['trianglePolygonGroupIds'][index] for index in origins]
    expected_faces=Counter((tuple(mapped[index] for index in indices[offset:offset+3]),expected_groups[offset//3],expected['triangleMaterials'][offset//3]) for offset in range(0,len(indices),3))
    actual_faces=Counter((tuple(referenced['cornerVertexInstanceIds'][offset:offset+3]),referenced['trianglePolygonGroupIds'][offset//3],actual['triangleMaterials'][offset//3]) for offset in range(0,len(indices),3))
    if expected_faces!=actual_faces:raise ValueError('Actual native oriented face/instance/group multiset differs')
    old_topology=original_stored['topology'];topology=stored['topology']
    old_vertices={row['id']:row for row in old_topology['vertices']};vertices={row['id']:row for row in topology['vertices']}
    if len(vertices)!=stored['sourceVertexCount'] or stored['sourceVertexCount']!=referenced['sourceVertexCount']:
        raise ValueError('All stored native vertex identities are required')
    if any(vertices.get(key)!=row for key,row in old_vertices.items()):
        raise ValueError('Original native vertex or orphan position changed')
    if stored['vertexIds'][:old_count]!=original_stored['vertexIds']:
        raise ValueError('Original shared corner-to-vertex connectivity changed')
    for index,value in enumerate(prefix_map):
        if original_stored['vertexIds'][old_index[value]]!=original['cornerVertexIds'][index]:
            raise ValueError('Original raw native vertex identity changed')
    original_edges={row['id']:row for row in old_topology['edges']};edges={row['id']:row for row in topology['edges']}
    if any(edges.get(key)!=row for key,row in original_edges.items()):
        raise ValueError('Original edge identity, connectivity or hardness changed')
    vertex_by_instance=dict(zip(expected_ids,stored['vertexIds']))
    created={};next_vertex=max(old_vertices)+1
    boundary_rows=sorted(wrapper['carveReceipt']['addedBoundaryVertices'],key=lambda row:row['index'])
    for row in boundary_rows:
        index=row['index'];weights=row['weights'];support=tuple(sorted({original['cornerVertexIds'][i] for i,w in zip(row['sourceIndices'],weights) if w>1e-12}))
        point=tuple(_stored(expected['positions'][index]))
        if len(support)==1:vertex=support[0]
        else:
            key=(('edge',support) if len(support)==2 else ('face',row['sourceIndices'][0]//3))+point
            if key not in created:created[key]=next_vertex;next_vertex+=1
            vertex=created[key]
        if vertex_by_instance[mapped[index]]!=vertex or vertices[vertex]['position']!=list(point):
            raise ValueError('Boundary native vertex weld crossed a source seam or changed position')
    if set(vertices)!=set(old_vertices)|set(created.values()):
        raise ValueError('Unexpected native boundary vertices were added or dropped')
    source_triangles={row['id']:row for row in old_topology['triangles']};native_triangles={row['id']:row for row in topology['triangles']}
    outside=wrapper['carveReceipt']['outsidePreservation']['sourceTriangleIds']
    for ordinal in outside:
        triangle=original['triangleIds'][ordinal]
        if native_triangles.get(triangle)!=source_triangles[triangle]:
            raise ValueError('An untouched native triangle/polygon/edge identity changed')
    if Counter((tuple(row['instances']),row['groupId']) for row in native_triangles.values())!=Counter((face[0],face[1]) for face in expected_faces.elements()):
        raise ValueError('Complete stored triangle topology differs from referenced faces')
    for offset,instance in enumerate(referenced['cornerVertexInstanceIds']):
        if referenced['cornerVertexIds'][offset]!=vertex_by_instance[instance]:
            raise ValueError('Referenced native vertex mapping differs from stored topology')
    supports={vertex:set() for vertex in vertices};edge_by_pair={}
    for edge in original_edges.values():
        for vertex in edge['vertices']:supports[vertex].add(edge['id'])
        edge_by_pair[tuple(sorted(edge['vertices']))]=edge['id']
    for key,vertex in created.items():
        if key[0]=='edge':supports[vertex].add(edge_by_pair[key[1]])
    for edge in topology['edges']:
        if edge['id'] in original_edges:continue
        a,b=edge['vertices'];common=supports[a]&supports[b]
        expected_hard=any(original_edges[value]['hard'] for value in common)
        if edge['hard']!=expected_hard:raise ValueError('Split native edge hardness changed')
    unused = len(expected_ids)-len(set(referenced['cornerVertexInstanceIds']))
    return dict(version=1, comparisonPolicy='actual_committed_all_stored_attributes_and_oriented_faces',
        sourcePrefixCorners=prefix, addedBoundaryCorners=count-prefix, storedCorners=len(expected_ids),
        unusedStoredCorners=unused, referencedTriangles=triangles, uvChannels=len(expected['uvChannels']),
        attributes=sorted(attribute_keys), nativeSourcePrefixPreserved=True,
        nativeReferencedCornersPreserved=True, nativeMaterialGroupsPreserved=True,
        nativeSharedTopologyPreserved=True,nativeOriginalVerticesPreserved=len(old_vertices),
        nativeOriginalEdgesPreserved=len(original_edges),nativeUnusedOriginalVerticesPreserved=len(set(old_vertices)-set(original_stored['vertexIds'])),
        nativeCollisionVerified=False, visualApproved=False, published=False)


def checked_native_policy(payload, mesh_path):
    """Accept complete native accessor/reflection readback without protected-property defaults."""
    row=json.loads(payload)
    if (row.get('schemaVersion')!=1 or row.get('mesh')!=mesh_path
            or any(row.get(key) is not True for key in ('available','valid','readOnly'))
            or row.get('policySource')!='native_persistent_accessors_and_full_reflected_source_structs'):
        raise ValueError('Actual native terrain policy is unavailable or incomplete')
    policy=row.get('policy',{})
    if set(policy)!={'sourceLods','buildSettings','reductionSettings','mesh','bodySetup'}:
        raise ValueError('Actual native terrain policy fields changed')
    lods=policy['sourceLods']
    if type(lods) is not int or not 1<=lods<=8:
        raise ValueError('Actual source LOD count unavailable')
    for key in ('buildSettings','reductionSettings'):
        values=policy[key]
        if not isinstance(values,list) or len(values)!=lods or any(not isinstance(v,dict) or not v for v in values):
            raise ValueError('Actual full source LOD settings are missing: '+key)
    if (set(policy['mesh'])!={'allow_cpu_access','auto_compute_lod_screen_size','light_map_coordinate_index',
                            'light_map_resolution','lod_for_collision','lod_group','nanite_settings'}
            or set(policy['bodySetup'])!={'collision_trace_flag','double_sided_geometry','physics_type','collision_reponse',
                                        'generate_mirrored_collision','generate_non_mirrored_collision','build_scale3d',
                                        'walkable_slope_override','phys_material'}
            or not isinstance(policy['mesh']['nanite_settings'],dict) or not policy['mesh']['nanite_settings']
            or not isinstance(policy['bodySetup']['build_scale3d'],dict) or not policy['bodySetup']['build_scale3d']
            or not isinstance(policy['bodySetup']['walkable_slope_override'],dict) or not policy['bodySetup']['walkable_slope_override']):
        raise ValueError('Actual persistent mesh/collision policy is missing')
    json.dumps(policy,allow_nan=False)
    return policy


def native_terrain_policy(mesh, tools=None):
    """Read protected UE properties through the read-only native API, never invented Python names."""
    import unreal
    return checked_native_policy(unreal.WarImportLibrary.describe_static_mesh_native_policy(mesh),mesh.get_path_name())
