"""Literal equipped assembly, evaluated geometry and selected-slot playback."""
import hashlib
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
PUBLIC = PROJECT/'public/assets/models'
RAM_SHA = 'b5e79265f4cd65759c6c1c0f60c10f21f11ffe095d4d5e5124ffc742ecb905ef'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def imported(path, inputs, expected=None):
    actual = sha(path)
    if expected and actual != expected: raise ValueError(f'Input changed: {path}')
    inputs.append({'path':str(path.relative_to(PROJECT)).replace('\\','/'), 'sha256':actual})
    prior = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o not in prior]


def equipped_actor(inputs):
    catalog = json.loads((PUBLIC/'asset-index.json').read_text())
    body_record = catalog['characterProfiles']['civic_battle_prelate_m']
    body = imported(PUBLIC/body_record['model'], inputs, body_record['modelSha256'])
    rig = next(o for o in body if o.type == 'ARMATURE')
    rig.animation_data_clear()
    for bone in rig.pose.bones: bone.matrix_basis = Matrix.Identity(4)
    equipment, hidden = [], set()
    maximum_error = 0
    for key in sorted(catalog['equipment']):
        if not key.startswith('novitiate_civic_battle_prelate_'): continue
        definition = catalog['equipment'][key]['variants']['m']
        if definition['approvalState'] != 'approved': raise ValueError(f'Unapproved equipment: {key}')
        objects = imported(PUBLIC/definition['model'], inputs, definition['modelSha256'])
        overlay = next(o for o in objects if o.type == 'ARMATURE')
        if set(overlay.data.bones.keys()) != set(rig.data.bones.keys()): raise ValueError('Skeleton names differ')
        error = max(abs(n) for bone in overlay.data.bones
                    for row in bone.matrix_local-rig.data.bones[bone.name].matrix_local for n in row)
        maximum_error = max(maximum_error,error)
        if error > .00001: raise ValueError(f'Equipment rest matrices differ: {error}')
        for obj in objects:
            if obj.type != 'MESH' or not any(m.type=='ARMATURE' and m.object==overlay for m in obj.modifiers): continue
            world = obj.matrix_world.copy()
            obj.parent = rig
            obj.matrix_world = world
            for modifier in obj.modifiers:
                if modifier.type=='ARMATURE': modifier.object=rig
            equipment.append(obj)
        hidden.update(definition.get('coveredRegions',[]))
        bpy.data.objects.remove(overlay,do_unlink=True)
    for obj in body:
        if obj.get('bodyRegion') in hidden:
            obj.hide_render=True
            obj.hide_set(True)
    visible = [o for o in body+equipment if o.type=='MESH' and not o.hide_render
               and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
    return rig, visible, {'hidden_body_regions':sorted(hidden), 'equipment_rest_matrix_max_error':maximum_error}


def pin_clip(objects,name):
    found=False
    for obj in objects:
        if not obj.animation_data: continue
        obj.animation_data.action=None
        for track in obj.animation_data.nla_tracks:
            track.mute=True
            if track.name==name:
                action,slot=track.strips[0].action,track.strips[0].action_slot
                obj.animation_data.action=action
                obj.animation_data.action_slot=slot
                found=True
    if not found: raise ValueError(f'Missing literal clip: {name}')


def rest_digest(rig):
    data={b.name:{'parent':b.parent.name if b.parent else None, 'matrix':[list(r) for r in b.matrix_local]}
          for b in rig.data.bones}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def render(path, target, offset, scale, resolution=(1400,1100)):
    for obj in list(bpy.context.scene.objects):
        if obj.type in {'CAMERA','LIGHT'}: bpy.data.objects.remove(obj,do_unlink=True)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x,scene.render.resolution_y=resolution
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    if not scene.world: scene.world=bpy.data.worlds.new('crew_review_world')
    scene.world.color=(.25,.25,.25)
    camera=bpy.data.objects.new('review_camera',bpy.data.cameras.new('review_camera'))
    scene.collection.objects.link(camera)
    center=Vector(target)
    camera.location=center+Vector(offset)
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'
    camera.data.ortho_scale=scale
    scene.camera=camera
    for name,location,energy,size,color in [('key',(-4,-4,7),2100,5,(1,.88,.75)),
        ('fill',(5,0,5),1750,4,(.78,.88,1)),('rim',(0,5,6),1800,3,(1,.93,.84))]:
        light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'))
        scene.collection.objects.link(light)
        light.location=location
        light.data.energy=energy
        light.data.size=size
        light.data.color=color
        light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX'
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
