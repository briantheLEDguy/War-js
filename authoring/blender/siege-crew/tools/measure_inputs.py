"""Read literal published fitting surfaces and canonical source rest geometry."""
import hashlib
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
PUBLIC = PROJECT / 'public/assets/models'
SOURCE = ROOT.parent / 'battle-prelate-novitiate-set/battle_prelate_novitiate_game_master.blend'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


def main():
    (ROOT/'review').mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    path = PUBLIC/'frontier_battering_ram_lod0.glb'
    bpy.ops.import_scene.gltf(filepath=str(path))
    ram = list(bpy.context.scene.objects)
    for obj in ram:
        if obj.animation_data:
            obj.animation_data.action = None
            for track in obj.animation_data.nla_tracks: track.mute = True
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    report = {'ram': {'path': str(path.relative_to(PROJECT)), 'sha256':sha(path)},
              'coordinates':'Blender Z-up; glTF = (x,z,-y)', 'objects':[], 'ram_strike_samples':[]}
    for obj in ram:
        record = {'name':obj.name,'type':obj.type,'parent':obj.parent.name if obj.parent else None,
                  'world_origin':list(obj.matrix_world.translation)}
        if obj.type == 'MESH': record.update(bounds=bounds(obj), vertices=len(obj.data.vertices))
        if obj.animation_data:
            record['tracks'] = [{'name':t.name, 'start':t.strips[0].frame_start,
                                 'end':t.strips[0].frame_end} for t in obj.animation_data.nla_tracks]
        report['objects'].append(record)
    for obj in ram:
        if obj.animation_data:
            for track in obj.animation_data.nla_tracks:
                track.mute = True
                if track.name == 'ram_strike':
                    action = track.strips[0].action
                    slot = track.strips[0].action_slot
                    obj.animation_data.action = action
                    obj.animation_data.action_slot = slot
    striker = next(o for o in ram if o.name == 'ram_striker')
    for sec in [0,.3,.5,.7,.8,1,1.3,1.5]:
        bpy.context.scene.frame_set(int(sec*30), subframe=sec*30-int(sec*30))
        bpy.context.view_layer.update()
        report['ram_strike_samples'].append({'seconds':sec, 'striker_origin':list(striker.matrix_world.translation)})
    assert max(s['striker_origin'][1] for s in report['ram_strike_samples']) > .27
    assert min(s['striker_origin'][1] for s in report['ram_strike_samples']) < -.33
    # Source geometry gives the unchanged pose matrices and equipped sole bounds.
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
        for constraint in list(bone.constraints): bone.constraints.remove(constraint)
    rig.location = (0,0,0)
    bpy.context.view_layer.update()
    report['canonical'] = {'path':str(SOURCE.relative_to(PROJECT)), 'sha256':sha(SOURCE),
      'rig_name':rig.name, 'matrix_world':[list(row) for row in rig.matrix_world],
      'bones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local), 'parent':b.parent.name if b.parent else None,
                       'matrix':[list(row) for row in b.matrix_local]} for b in rig.data.bones},
      'modules':[{'name':o.name,'bounds':bounds(o),'vertices':len(o.data.vertices)} for o in bpy.context.scene.objects
                 if o.type=='MESH' and o.parent==rig and o.name.endswith('_lod0')]}
    out = ROOT/'review/input_measurements.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(out),'ram_objects':report['objects'],'samples':report['ram_strike_samples'],
                      'modules':report['canonical']['modules'], 'bones':{k:v for k,v in report['canonical']['bones'].items()
                         if k in ['hips','spine','chest','head','thigh_L','shin_L','foot_L','upper_arm_L','forearm_L','hand_L']}}))


if __name__=='__main__': main()
