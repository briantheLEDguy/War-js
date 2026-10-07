"""Rebuild owned source architecture in fresh private assets, without Unreal calls.

Source face ordinals are meaningful only against their exact source byte hash.
They never select native render indices. Original actors remain the collision,
navigation and GM owners; native import and complete new proofs remain separate.
"""
import copy
import hashlib
import json
import math
import re

SOURCE_IDS = frozenset(('stairs_and_balconies', 'curtain_gatehouses',
                        'gothic_facade_and_spires', 'ribbed_interiors'))
MAX_VERTICES = 3_000_000
MAX_TRIANGLES = 1_500_000
MAX_SOURCE_BYTES = 1_000_000_000
MAX_DECLARED_MATERIAL_ROLES = 64
MAX_USED_MATERIAL_ROLES = 16


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite_vector(value, size):
    return (isinstance(value, list) and len(value) == size
            and all(type(v) in (int, float) and math.isfinite(v) for v in value))


def _validate_mesh(mesh, *, addition=False):
    _require(isinstance(mesh, dict), 'Source mesh object required')
    if addition:
        _require(mesh.get('coordinateSpace') == 'final_unreal_world_cm',
                 'New architecture requires final Unreal centimetres')
        _require(mesh.get('sourceTriangleWinding') == 'counter_clockwise_cross_aligned_with_normals',
                 'Explicit new source winding required; native conversion belongs to import')
        _require(mesh.get('collision') is False and mesh.get('navigation') is False,
                 'New details must be render-only')
    else:
        _require(mesh.get('id') in SOURCE_IDS, 'Only the four owned architectural sources are admitted')
    _require(isinstance(mesh.get('id'), str)
             and re.fullmatch('[a-z][a-z0-9_]{0,95}', mesh['id']), 'Bounded source identity required')
    positions, normals, uvs = (mesh.get(k) for k in ('positions', 'normals', 'uvs'))
    _require(isinstance(positions, list) and 3 <= len(positions) <= MAX_VERTICES,
             'Bounded source position array required')
    _require(isinstance(normals, list) and isinstance(uvs, list)
             and len(normals) == len(uvs) == len(positions), 'Complete source corner attributes required')
    _require(all(_finite_vector(p, 3) for p in positions)
             and all(_finite_vector(n, 3) and abs(sum(v*v for v in n)-1) <= .0001 for n in normals)
             and all(_finite_vector(uv, 2) for uv in uvs), 'Finite positions/UVs and unit normals required')
    materials, indices, slots = (mesh.get(k) for k in ('materials', 'indices', 'triangleMaterials'))
    _require(isinstance(materials, list) and 1 <= len(materials) <= MAX_DECLARED_MATERIAL_ROLES
             and all(isinstance(m, str) and re.fullmatch('[a-z][a-z0-9_]{0,95}', m) for m in materials)
             and len(set(materials)) == len(materials),
             'Unique bounded material roles required')
    _require(isinstance(indices, list) and 3 <= len(indices) <= MAX_TRIANGLES*3
             and len(indices) % 3 == 0 and all(type(i) is int and 0 <= i < len(positions) for i in indices),
             'Complete bounded source triangle indices required')
    _require(isinstance(slots, list) and len(slots)*3 == len(indices)
             and all(type(i) is int and 0 <= i < len(materials) for i in slots), 'Complete triangle materials required')
    _require(len(set(slots)) <= MAX_USED_MATERIAL_ROLES, 'Used material-role bound exceeded')
    # This source protocol owns UV0 only. Unknown per-corner arrays must not be
    # silently truncated or synthesized during appended authoring geometry.
    _require(not any(k in mesh for k in ('uvChannels', 'lightmapUvs', 'colors', 'tangents', 'binormals')),
             'Additional source channels require a separately reviewed transport policy')
    for offset in range(0, len(indices), 3):
        a, b, c = (positions[i] for i in indices[offset:offset+3])
        u, v = ([p[j]-a[j] for j in range(3)] for p in (b, c))
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        _require(sum(component*component for component in cross) > 1e-12,
                 'Degenerate source triangle cannot be imported')
        if addition:
            average = [sum(normals[i][j] for i in indices[offset:offset+3]) for j in range(3)]
            _require(sum(cross[j]*average[j] for j in range(3)) > 0,
                     'New triangle winding disagrees with outward source normals')
    return len(slots)


def rebuild_private_source(source_bytes, expected_sha256, selected_indices, additions, target_id):
    """Filter exact bound source faces and append authored geometry in one source space.

All original position/normal/UV arrays remain byte-value-equivalent prefixes,
including unused source entries. Each unselected oriented index/material
occurrence is retained. FBX/native packing, generated UV1 and reduced LODs are
explicitly not covered by that source guarantee.
    """
    _require(isinstance(source_bytes, bytes) and 0 < len(source_bytes) <= MAX_SOURCE_BYTES,
             'Bounded immutable source bytes required')
    _require(isinstance(expected_sha256, str) and re.fullmatch('[a-f0-9]{64}', expected_sha256)
             and hashlib.sha256(source_bytes).hexdigest() == expected_sha256,
             'Source hash changed; source ordinals cannot be reinterpreted')
    _require(isinstance(target_id, str) and re.fullmatch('private_[a-z0-9_]{1,87}', target_id),
             'Fresh private source target identity required')
    try:
        source = json.loads(source_bytes)
    except (ValueError, UnicodeError) as error:
        raise ValueError('Valid source JSON required') from error
    source_triangles = _validate_mesh(source)
    _require(isinstance(selected_indices, list) and len(selected_indices) < source_triangles
             and all(type(i) is int and 0 <= i < source_triangles for i in selected_indices)
             and len(set(selected_indices)) == len(selected_indices),
             'Unique in-range source selections must retain some original geometry')
    _require(isinstance(additions, list) and len(additions) <= 64
             and (selected_indices or additions), 'Bounded explicit change required')
    _require(all(isinstance(m, dict) for m in additions), 'Complete addition mesh objects required')
    _require(all(isinstance(m.get('id'), str) for m in additions), 'Bounded addition identities required')
    _require(len({m.get('id') for m in additions}) == len(additions), 'Duplicate addition identity')
    new_triangles = sum(_validate_mesh(m, addition=True) for m in additions)
    _require(source_triangles-len(selected_indices)+new_triangles <= MAX_TRIANGLES
             and len(source['positions'])+sum(len(m['positions']) for m in additions) <= MAX_VERTICES,
             'Rebuilt source exceeds the reviewed bound')

    result = copy.deepcopy(source)
    result.update(id=target_id, collision=False, navigation=False,
                  coordinateSpace='final_unreal_world_cm',
                  sourceTriangleWinding='counter_clockwise_cross_aligned_with_normals')
    removed = set(selected_indices)
    retained = [i for i in range(source_triangles) if i not in removed]
    result['indices'] = [index for i in retained for index in source['indices'][i*3:i*3+3]]
    result['triangleMaterials'] = [source['triangleMaterials'][i] for i in retained]
    addition_ledger = []
    for addition in additions:
        role_map = []
        for role in addition['materials']:
            if role not in result['materials']:
                result['materials'].append(role)
            role_map.append(result['materials'].index(role))
        _require(len(result['materials']) <= MAX_DECLARED_MATERIAL_ROLES, 'Rebuilt declared role bound exceeded')
        start_vertex, start_triangle = len(result['positions']), len(result['triangleMaterials'])
        for attribute in ('positions', 'normals', 'uvs'):
            result[attribute].extend(copy.deepcopy(addition[attribute]))
        result['indices'].extend(start_vertex+i for i in addition['indices'])
        result['triangleMaterials'].extend(role_map[i] for i in addition['triangleMaterials'])
        _require(len(set(result['triangleMaterials'])) <= MAX_USED_MATERIAL_ROLES,
                 'Rebuilt used material-role bound exceeded')
        addition_ledger.append(dict(id=addition['id'], sourcePayloadSha256=digest(addition),
                                    targetFirstTriangle=start_triangle, triangles=len(addition['triangleMaterials'])))

    for attribute in ('positions', 'normals', 'uvs'):
        assert result[attribute][:len(source[attribute])] == source[attribute]
    assert all(result['indices'][target*3:target*3+3] == source['indices'][old*3:old*3+3]
               and result['triangleMaterials'][target] == source['triangleMaterials'][old]
               for target, old in enumerate(retained))
    receipt = dict(schemaVersion=1, diagnosticOnly=True,
                   sourceId=source['id'], sourceFileSha256=expected_sha256,
                   sourceTriangles=source_triangles, selectedSourceTriangles=len(selected_indices),
                   selectedSourceIndicesSha256=digest(sorted(selected_indices)),
                   retainedSourceTriangles=len(retained), retainedSourceIndices=retained,
                   retainedSourceAttributesExact=True, retainedSourceOccurrencesExact=True,
                   sourceDeclaredMaterialRoles=len(source['materials']),
                   outputDeclaredMaterialRoles=len(result['materials']),
                   outputUsedMaterialRoles=len(set(result['triangleMaterials'])),
                   additions=addition_ledger, outputTriangles=len(result['triangleMaterials']),
                   outputPayloadSha256=digest(result), originalCollisionActorRequired=True,
                   originalSourceWriteAllowed=False, nativeIndexSelectionAllowed=False,
                   coordinateSpace='final_unreal_world_cm', repeatedUpperCompressionAllowed=False,
                   generatedNativeUV1RequiresReview=True, reducedNativeLodsRequireReview=True,
                   nativePackedBufferPreservationClaimed=False, nativeCorrespondenceVerified=False,
                   nativeCollisionVerified=False, visualApproved=False,
                   populatedPerformanceVerified=False, sharedAdoptionAllowed=False,
                   releaseAcceptance=False)
    return result, receipt
