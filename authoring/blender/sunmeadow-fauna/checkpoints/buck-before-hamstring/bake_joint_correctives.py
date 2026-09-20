"""Build a separate review candidate from the hash-verified editable buck."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT, resolve
from joint_correctives import JointRelaxation, compact_anatomical_modes, caudal_weight_transfer, fascia_displacement, haunch_detail_retention
from prune_morph_normals import prune_morph_normals
from static_normals import restore_static_normals


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def coordinates(obj):
    data = np.empty(len(obj.data.vertices)*3, dtype=np.float64)
    obj.data.vertices.foreach_get('co', data)
    return data.reshape(-1, 3)


def main():
    key = 'frontier_sunmeadow_roe_deer_buck'
    report_path = ROOT/'review'/f'{key}_build.json'
    report = json.loads(report_path.read_text())
    for file, digest in {**report['source_files'], **report['texture_sources'], report['master']: report['master_sha256']}.items():
        if sha(ROOT/file) != digest:
            raise RuntimeError('Changed candidate input: '+file)
    output = ROOT/'review/candidates/buck_differential'
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/report['master']))
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    actions = {a.name: a for a in bpy.data.actions}
    models = [next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.name.startswith(key+f'_LOD{lod}') and any(mod.type == 'ARMATURE' for mod in obj.modifiers)) for lod in range(3)]
    if any(obj.data.shape_keys for obj in models):
        raise RuntimeError('Corrective baking requires a fresh uncorrected base master')
    rig_slots = {name: a.slots[0] for name, a in actions.items()}
    bone_names = [b.name for b in rig.data.bones]
    inverse_bind = {name: rig.data.bones[name].matrix_local.inverted() for name in bone_names}
    evidence = {'status': 'actual_export_review_required', 'forelimb_corrective_amplitude': .5, 'base_build_sha256': sha(report_path), 'sources': {name: sha(ROOT/'tools'/name) for name in ['bake_joint_correctives.py', 'joint_correctives.py', 'prune_morph_normals.py', 'static_normals.py']}, 'lods': []}
    for level, obj in enumerate(models):
        rig.animation_data.action = None
        for bone in rig.pose.bones: bone.matrix_basis = Matrix.Identity(4)
        obj.hide_set(False); obj.hide_render = False; bpy.context.view_layer.update()
        rest = coordinates(obj)
        geometry_hash = hashlib.sha256(rest.tobytes()).hexdigest()
        changed_weights = 0
        for vertex in obj.data.vertices:
            weights = {obj.vertex_groups[g.group].name: g.weight for g in vertex.groups}
            replacement = caudal_weight_transfer(vertex.co, weights, resolve('roe_deer_buck')['scale'])
            if replacement != weights:
                if len(replacement) > 4: raise RuntimeError('Caudal transfer exceeded four influences')
                changed_weights += 1
                for name, weight in replacement.items():
                    obj.vertex_groups[name].add([vertex.index], weight, 'REPLACE')
        edges = np.array([e.vertices[:] for e in obj.data.edges])
        relaxation = JointRelaxation(rest, edges, resolve('roe_deer_buck')['scale'])
        weighted = []
        for name in bone_names:
            group = obj.vertex_groups.get(name)
            vertices, weights = [], []
            if group:
                for vertex in obj.data.vertices:
                    for assignment in vertex.groups:
                        if assignment.group == group.index and assignment.weight:
                            vertices.append(vertex.index); weights.append(assignment.weight)
            weighted.append((name, np.asarray(vertices, dtype=int), np.asarray(weights)))
        samples, timelines = [], {}
        for name, action in actions.items():
            rig.animation_data.action = action; rig.animation_data.action_slot = rig_slots[name]
            first, last = map(float, action.frame_range)
            step = .5 if name == 'run' else 1 if name == 'walk' else 12
            frames = sorted(set(np.arange(first, last, step).tolist()+[last]))
            timelines[name] = []
            for frame in frames:
                bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame)); bpy.context.view_layer.update()
                posed = coordinates(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
                rotations = np.zeros((len(rest), 3, 3))
                for bone, indices, weights in weighted:
                    if not len(indices): continue
                    matrix = np.asarray((rig.pose.bones[bone].matrix@inverse_bind[bone]).to_3x3())
                    rotations[indices] += weights[:, None, None]*matrix
                carrier = rig.pose.bones['pelvis'].matrix@inverse_bind['pelvis']
                carried_rotation = np.asarray(carrier.to_3x3())
                flexions = {}
                for side, label in [(1, 'L'), (-1, 'R')]:
                    bone = rig.pose.bones['thigh_'+label]
                    resting = np.asarray(bone.bone.tail_local-bone.bone.head_local)
                    direction = np.linalg.solve(carried_rotation, np.asarray(bone.tail-bone.head))
                    flexions[side] = math.atan2(resting[1]*direction[2]-resting[2]*direction[1], resting[1]*direction[1]+resting[2]*direction[2])
                fascia = fascia_displacement(rest, resolve('roe_deer_buck')['scale'], carried_rotation, flexions)
                retention = haunch_detail_retention(rest, resolve('roe_deer_buck')['scale'], flexions)
                delta = relaxation.delta(posed, rotations, fascia, retention, front_blend=.5)
                if not np.isfinite(delta).all(): raise RuntimeError('Nonfinite corrective sample')
                timelines[name].append((frame, len(samples))); samples.append(delta)
            print('JOINT_SAMPLES', level, name, len(frames), 'diffusion', relaxation.iterations, flush=True)
        np.savez_compressed(output/f'lod{level}_sample_cache.npz', samples=np.asarray(samples, dtype=np.float32))
        modes, coefficients, quality = compact_anatomical_modes(samples, rest)
        rig.animation_data.action = None
        for bone in rig.pose.bones: bone.matrix_basis = Matrix.Identity(4)
        obj.shape_key_add(name='Basis')
        keys = []
        for index, delta in enumerate(modes):
            shape = obj.shape_key_add(name=f'joint_volume_{index+1:02}')
            shape.slider_min = -1; shape.slider_max = 1
            shape.data.foreach_set('co', (rest+delta).ravel()); keys.append(shape)
        datablock = obj.data.shape_keys; datablock.animation_data_create()
        for name, action in actions.items():
            datablock.animation_data.action = action
            datablock.animation_data.action_slot = action.slots.new('KEY', datablock.name)
            for frame, sample_index in timelines[name]:
                for index, shape in enumerate(keys):
                    shape.value = coefficients[sample_index, index]
                    shape.keyframe_insert('value', frame=frame)
            track = datablock.animation_data.nla_tracks.new()
            track.name = name
            strip = track.strips.new(name, int(action.frame_range[0]), action)
            strip.action_slot = datablock.animation_data.action_slot
            track.mute = True
        datablock.animation_data.action = None
        for shape in keys: shape.value = 0
        if hashlib.sha256(coordinates(obj).tobytes()).hexdigest() != geometry_hash:
            raise RuntimeError('Corrective authoring changed base anatomy')
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = obj
        target = output/f'{key}_lod{level}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True, export_yup=True, export_normals=True, export_tangents=True, export_texcoords=True, export_skins=True, export_animations=True, export_animation_mode='ACTIONS', export_merge_animation='ACTION', export_anim_single_armature=True, export_force_sampling=True, export_frame_range=False, export_vertex_color='NAME', export_vertex_color_name='AnatomicalTint', export_all_vertex_colors=False, export_try_sparse_sk=True, export_morph_normal=True)
        payload, compression = prune_morph_normals(target.read_bytes())
        payload, preserved_normals = restore_static_normals(payload, (ROOT/'runtime'/target.name).read_bytes())
        target.write_bytes(payload)
        evidence['lods'].append({'level': level, 'model': target.name, 'sha256': sha(target), 'bytes': target.stat().st_size, 'unchanged_rest_geometry_sha256': geometry_hash, 'caudal_weight_vertices': changed_weights, 'samples': len(samples), **quality, 'normal_noise_pruning': compression, 'static_normal_preservation': preserved_normals})
        (output/'candidate.json').write_text(json.dumps(evidence, indent=2)+'\n')
        obj.hide_set(level != 0); obj.hide_render = level != 0
        print('JOINT_CANDIDATE', level, quality, target.stat().st_size, flush=True)
    target = output/f'{key}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True)
    evidence['master'] = target.name; evidence['master_sha256'] = sha(target)
    (output/'candidate.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
