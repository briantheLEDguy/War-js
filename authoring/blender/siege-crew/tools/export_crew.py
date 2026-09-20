"""Bake seat-specific motion against the literal ram clip; export no geometry."""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_common as common
import author_crew as author

ROOT=common.ROOT
CLIPS=[('ram_crew_idle',240,True,None),('ram_crew_drive',96,True,None),('ram_crew_strike',90,False,.7)]


def capture(rig):
    result={}
    for bone in rig.pose.bones:
        if bone.name=='root':
            result[bone.name]=((0,0,0),(1,0,0,0),(1,1,1))
        else:
            matrix=bone.matrix_basis
            result[bone.name]=(tuple(matrix.to_translation()),tuple(matrix.to_quaternion()),tuple(matrix.to_scale()))
    return result


def key_action(rig,name,poses):
    rig.animation_data_create()
    action=bpy.data.actions.new(name)
    rig.animation_data.action=action
    action.use_fake_user=True
    action['motion_space']='in_place'
    action['skeleton_id']='humanoid_game_v2'
    previous={}
    for frame,pose in poses:
        for name,(location,rotation,scale) in pose.items():
            bone=rig.pose.bones[name]
            bone.rotation_mode='QUATERNION'
            bone.location=location
            bone.rotation_quaternion=rotation
            if name in previous and bone.rotation_quaternion.dot(previous[name]) < 0:
                bone.rotation_quaternion.negate()
            previous[name]=bone.rotation_quaternion.copy()
            bone.scale=scale
            for channel in ['location','rotation_quaternion','scale']:
                bone.keyframe_insert(data_path=channel,frame=frame)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points: point.interpolation='LINEAR'
    rig.animation_data.action=None
    return action


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/ram_crew_source_hinge.blend'))
    bpy.context.scene.render.fps=30
    report=json.loads((ROOT/'review/source_fit.json').read_text())
    ram=[o for o in bpy.context.scene.objects if o.name in ['ram_striker','suspension_front','suspension_rear']]
    common.pin_clip(ram,'ram_strike')
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    striker=bpy.data.objects['ram_striker']
    rest=striker.matrix_world.translation.copy()
    # Pose solving needs only the skeleton. Restore every modifier before saving.
    modifiers=[]
    for obj in bpy.context.scene.objects:
        for modifier in obj.modifiers:
            if modifier.type=='ARMATURE':
                modifiers.append((modifier,modifier.show_viewport))
                modifier.show_viewport=False
    actors=[]
    for label,sign in [('left',-1),('right',1)]:
        rig=bpy.data.objects['crew_'+label]
        seat=next(s for s in report['seats'] if s['seat']==label)
        fingers={b.name:b.matrix_basis.copy() for b in rig.pose.bones
                 if any(b.name.startswith(f+'_') for f in (*author.FINGERS,'thumb'))}
        actors.append((label,sign,rig,seat,fingers))
    outputs=[]
    for label,sign,rig,seat,fingers in actors:
        digest=common.rest_digest(rig)
        actions=[]
        expected=[]
        for clip,last,loop,event in CLIPS:
            poses=[]
            for frame in range(last+1):
                ram_frame=frame/2 if clip=='ram_crew_strike' else 0
                bpy.context.scene.frame_set(int(ram_frame),subframe=ram_frame%1)
                bpy.context.view_layer.update()
                delta=striker.matrix_world.translation-rest if clip=='ram_crew_strike' else Vector()
                breath=0 if clip=='ram_crew_strike' else (.0025 if clip=='ram_crew_idle' else .004)*math.sin(frame/last*math.tau)
                author.pose_operator(rig,sign,Vector(seat['origin_blender']),seat['board_heights'],delta,fingers,breath)
                poses.append((frame,capture(rig)))
                expected.append({'clip':clip,'frame':frame,'striker_delta':list(delta),
                  'bone_world_matrices':{n:[list(row) for row in rig.matrix_world @ rig.pose.bones[n].matrix]
                    for n in ['hips','hand_L','hand_R','foot_L','foot_R']}})
            actions.append((clip,key_action(rig,clip,poses)))
            print('BAKED',label,clip,len(poses),flush=True)
        assert common.rest_digest(rig)==digest
        rig.animation_data.action=None
        for i,(clip,action) in enumerate(actions):
            track=rig.animation_data.nla_tracks.new()
            track.name=clip
            strip=track.strips.new(clip,1+i*300,action)
            strip.extrapolation='NOTHING'
            strip.action_slot=action.slots[0]
        for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
        world=rig.matrix_world.copy()
        rig.matrix_world=Matrix.Identity(4)
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        rig.select_set(True)
        bpy.context.view_layer.objects.active=rig
        output=ROOT/'runtime'/f'frontier_ram_crew_{label}_animations.glb'
        bpy.context.scene.render.fps=60
        bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,
            export_animations=True,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True,
            export_frame_range=False,export_skins=True,export_def_bones=True)
        rig.matrix_world=world
        record={'seat':label,'path':str(output.relative_to(ROOT)),'sha256':common.sha(output),
                'rig_rest_sha256':digest,'origin_gltf':seat['origin_gltf'],'yaw_gltf_radians':seat['yaw_gltf_radians'],
                'socket_offset_blender':seat['socket_offset_blender'],'board_heights':seat['board_heights'],
                'clips':[{'name':c,'duration_seconds':n/60,'loop':l,'event_seconds':e,'root_motion':False}
                         for c,n,l,e in CLIPS]}
        outputs.append(record)
        (ROOT/'review'/f'{label}_expected_pose.json').write_text(json.dumps(expected,separators=(',',':'))+'\n')
    for modifier,visible in modifiers: modifier.show_viewport=visible
    # Save the fitted editable assembly with all six original authored actions.
    for label,sign,rig,seat,fingers in actors:
        for track in rig.animation_data.nla_tracks: track.mute=True
        rig.animation_data.action=None
        author.pose_operator(rig,sign,Vector(seat['origin_blender']),seat['board_heights'],Vector(),fingers)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    master=ROOT/'masters/frontier_ram_crew_animations.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    contract={'status':'exported_pending_actual_contact_verification','asset_id':'frontier_ram_crew',
      'skeleton_id':'humanoid_game_v2','profile_key':'civic_battle_prelate_m',
      'equipment':'literal approved male Battle Prelate novitiate set',
      'inputs':report['inputs'],'master':str(master.relative_to(ROOT)),'master_sha256':common.sha(master),
      'outputs':outputs,'source_sha256':{p.name:common.sha(p) for p in [Path(__file__),ROOT/'tools/author_crew.py',ROOT/'tools/crew_common.py']},
      'authority':'Avatar origins and ram travel are external transforms. No clip changes the root bone.',
      'timing':'Play matching crew strike and published ram_strike together at t=0. Shared impact is t=0.7s. Drive loops at siege_roll duration 1.6s.'}
    (ROOT/'review/crew_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    print('CREW_EXPORTS_SAVED',flush=True)


if __name__=='__main__': main()
