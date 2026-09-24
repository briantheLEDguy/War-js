"""Shared anatomy/equipment review helpers; character animation is native-only."""
import bpy
from mathutils import Matrix
import build_collection as build

PROJECT=build.ROOT.parents[2]
PUBLIC=PROJECT/'public/assets/models'


def imported(path):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def snapshots(objects):
    graph=bpy.context.evaluated_depsgraph_get()
    result=[]
    for obj in objects:
        if obj.type!='MESH' or obj.hide_render or not obj.visible_get(): continue
        evaluated=obj.evaluated_get(graph)
        mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=graph)
        for vertex in mesh.vertices: vertex.co=obj.matrix_world @ vertex.co
        proof=bpy.data.objects.new('review.'+obj.name,mesh)
        bpy.context.scene.collection.objects.link(proof)
        result.append(proof)
    return result


def equipped_actor(catalog,load):
    record=catalog['characterProfiles']['civic_battle_prelate_m']
    body=load(PUBLIC/record['model'],record['modelSha256'])
    rig=next(obj for obj in body if obj.type=='ARMATURE')
    rig.animation_data_clear()
    for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    hidden=set(); equipment=[]
    for key in sorted(catalog['equipment']):
        if not key.startswith('novitiate_civic_battle_prelate_'): continue
        definition=catalog['equipment'][key]['variants']['m']
        if definition['approvalState']!='approved': raise ValueError('Unreviewed equipment in model proof')
        objects=load(PUBLIC/definition['model'],definition['modelSha256'])
        overlay=next(obj for obj in objects if obj.type=='ARMATURE')
        if any(b.name not in rig.data.bones for b in overlay.data.bones): raise ValueError('Equipment skeleton mismatch')
        for obj in objects:
            if obj.type!='MESH' or obj.hide_render: continue
            matrix=obj.matrix_world.copy(); obj.parent=rig; obj.matrix_world=matrix
            for modifier in obj.modifiers:
                if modifier.type=='ARMATURE': modifier.object=rig
            equipment.append(obj)
        hidden.update(definition.get('coveredRegions',[]))
        bpy.data.objects.remove(overlay,do_unlink=True)
    for obj in body:
        if obj.get('bodyRegion') in hidden: obj.hide_render=True; obj.hide_set(True)
    return rig,body,equipment,hidden
