"""Braced ram operators fitted to literal fixed boards and moving handles."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_common as common

ROOT=common.ROOT
FINGERS=('index','middle','ring','pinky')
GRIP_SOURCE=ROOT.parent/'battle-prelate-reference-rebuild/tools/correct_animation.py'
spec=importlib.util.spec_from_file_location('canonical_hand_fit',GRIP_SOURCE)
grip_helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(grip_helper)


def two_link(start,target,a,b,pole):
    delta=target-start
    distance=delta.length
    if not abs(a-b)+1e-5 < distance < a+b-1e-5:
        raise ValueError(f'Unchanged limb cannot reach target: {distance:.5f}, available {a+b:.5f}')
    axis=delta.normalized()
    bend=pole-start-axis*(pole-start).dot(axis)
    bend.normalize()
    along=(a*a-b*b+distance*distance)/(2*distance)
    return start+axis*along+bend*math.sqrt(max(0,a*a-along*along))


def aim(bone,head,tail):
    rotation=(bone.tail_local-bone.head_local).rotation_difference(tail-head)
    return Matrix.Translation(head) @ rotation.to_matrix().to_4x4() @ bone.matrix_local.to_quaternion().to_matrix().to_4x4()


def inherited(bone,desired):
    return (desired[bone.parent.name] @ bone.parent.matrix_local.inverted() @ bone.matrix_local
            if bone.parent else bone.matrix_local.copy())


def apply_desired(rig,desired):
    for bone in rig.data.bones:
        if bone.name not in desired: desired[bone.name]=inherited(bone,desired)
        args={'parent_matrix':desired[bone.parent.name],'parent_matrix_local':bone.parent.matrix_local} if bone.parent else {}
        basis=bone.convert_local_to_pose(desired[bone.name],bone.matrix_local,invert=True,**args)
        rig.pose.bones[bone.name].matrix_basis=basis
    bpy.context.view_layer.update()


def board_height(body,x,y):
    origin=body.matrix_world.inverted() @ Vector((x,y,1.2))
    hit,point,normal,index=body.ray_cast(origin,Vector((0,0,-1)),distance=.5)
    if not hit: raise ValueError(f'No actual footboard under {(x,y)}')
    point=body.matrix_world @ point
    if not .85 < point.z < 1.0: raise ValueError(f'Unexpected board height {point.z}')
    return point.z


def palm_matrix(rig,side,primary,axis,seat_sign):
    bone=rig.data.bones['hand_'+side]
    bases=[rig.data.bones[f'{f}_01_{side}'].head_local for f in FINGERS]
    rest_axis=(bases[0]-bases[-1]).normalized()
    rest_finger=sum(bases,Vector())/4-bone.head_local
    rest_finger=(rest_finger-rest_axis*rest_finger.dot(rest_axis)).normalized()
    rest_normal=rest_axis.cross(rest_finger).normalized()
    # Spread the hands along the rod with the palm above its outer quadrant.
    target_axis=axis * (1 if side=='L' else -1)
    target_finger=Vector((0,-.8,-.6))
    target_normal=target_axis.cross(target_finger).normalized()
    before=Matrix((rest_axis,rest_finger,rest_normal)).transposed()
    after=Matrix((target_axis,target_finger,target_normal)).transposed()
    turn=after @ before.transposed()
    rest_center=sum(bases,Vector())/4-rest_finger*.055
    # Centre of the palm lies on the exterior of the measured 32mm grip.
    center=primary+Vector((0,.024,.026))
    matrix=Matrix.Translation(center) @ turn.to_4x4() @ Matrix.Translation(-rest_center) @ bone.matrix_local
    return matrix


def pose_operator(rig,seat_sign,origin,board_contacts,striker_delta,finger_pose=None,breath=0):
    for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    desired={}
    hips=rig.data.bones['hips']
    # Fixed feet and a supported half crouch leave useful elbow bend at impact.
    sway=rig.matrix_world.inverted().to_3x3() @ striker_delta
    hip_position=hips.head_local+Vector((sway.x*.70,.015,-.110-abs(sway.x)*.035+breath))
    desired['root']=rig.data.bones['root'].matrix_local.copy()
    desired['hips']=Matrix.Translation(hip_position) @ Matrix.Rotation(.43,4,'X') @ Matrix.Translation(-hips.head_local) @ hips.matrix_local
    for name in ['spine','chest','upper_chest']:
        bone=rig.data.bones[name]
        current=inherited(bone,desired)
        desired[name]=Matrix.Translation(current.translation) @ Matrix.Rotation(.08,4,'X') @ Matrix.Translation(-current.translation) @ current
    inverse=rig.matrix_world.inverted()
    finger_guides={}
    for side,sign in [('L',1),('R',-1)]:
        thigh,shin,foot=(rig.data.bones[n+'_'+side] for n in ['thigh','shin','foot'])
        start=(desired['hips'] @ hips.matrix_local.inverted() @ thigh.matrix_local).translation
        ankle=Vector((sign*.20,.015,board_contacts[side]-origin.z+foot.head_local.z-.000509))
        knee=two_link(start,ankle,thigh.length,shin.length,Vector((sign*.28,-.55,.55)))
        desired[thigh.name]=aim(thigh,start,knee)
        desired[shin.name]=aim(shin,knee,ankle)
        desired[foot.name]=Matrix.Translation(ankle-foot.head_local) @ foot.matrix_local
    for bone in rig.data.bones:
        if bone.name not in desired: desired[bone.name]=inherited(bone,desired)
    for side,sign in [('L',1),('R',-1)]:
        upper,fore,hand=(rig.data.bones[n+'_'+side] for n in ['upper_arm','forearm','hand'])
        start=desired[upper.name].translation
        grip_world=Vector((seat_sign*.53,-.185-seat_sign*sign*.092,1.66))+striker_delta
        primary=inverse @ grip_world
        axis=inverse.to_3x3() @ Vector((0,1,0))
        target=palm_matrix(rig,side,primary,axis,seat_sign)
        wrist=target.translation
        elbow=two_link(start,wrist,upper.length,fore.length,Vector((sign*.46,.12,1.04)))
        desired[upper.name]=aim(upper,start,elbow)
        desired[fore.name]=aim(fore,elbow,wrist)
        desired[hand.name]=target
        finger_guides[side]=(primary,axis)
        # Finger parent matrices must follow this newly solved hand.
        for bone in rig.data.bones:
            if bone.name.endswith('_'+side) and any(bone.name.startswith(f+'_') for f in (*FINGERS,'thumb')):
                desired[bone.name]=inherited(bone,desired)
    apply_desired(rig,desired)
    if finger_pose is None:
        reports={side:grip_helper._close_hand(rig,side,primary,axis,.031)
                 for side,(primary,axis) in finger_guides.items()}
    else:
        for name,basis in finger_pose.items(): rig.pose.bones[name].matrix_basis=basis
        bpy.context.view_layer.update()
        reports={}
    return reports


def main():
    for folder in ['review','masters','runtime']: (ROOT/folder).mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    inputs=[]
    ram=common.imported(common.PUBLIC/'frontier_battering_ram_lod0.glb',inputs,common.RAM_SHA)
    common.pin_clip(ram,'ram_strike')
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    body=next(o for o in ram if o.name=='body')
    striker=next(o for o in ram if o.name=='ram_striker')
    striker_rest=striker.matrix_world.translation.copy()
    actors=[]
    for seat_sign,label in [(-1,'left'),(1,'right')]:
        rig,modules,assembly=common.equipped_actor(inputs)
        rig.name='crew_'+label
        digest=common.rest_digest(rig)
        # Avatar origins are static transforms owned by the siege attachment adapter.
        origin=Vector((seat_sign*.71,-.185,.91))
        rig.matrix_world=Matrix.Translation(origin) @ Matrix.Rotation(-seat_sign*math.pi/2,4,'Z')
        bpy.context.view_layer.update()
        contacts={side:board_height(body,seat_sign*.70,-.185-seat_sign*sign*.20)
                  for side,sign in [('L',1),('R',-1)]}
        finger_fit=pose_operator(rig,seat_sign,origin,contacts,Vector())
        assert common.rest_digest(rig)==digest
        actors.append((rig,modules,seat_sign,origin,contacts))
        assembly.update({'seat':label,'rig_rest_sha256':digest,'origin_blender':list(origin),
            'origin_gltf':[origin.x,origin.z,-origin.y],'yaw_gltf_radians':-seat_sign*math.pi/2,
            'socket_offset_blender':[0,-.035,.08], 'board_heights':contacts,'finger_fit':finger_fit})
        if label=='left': records=[]
        records.append(assembly)
    bpy.context.view_layer.update()
    master=ROOT/'masters/ram_crew_source_assembly.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    report={'status':'source_fit_in_progress','inputs':inputs,'seats':records,
      'master':str(master.relative_to(ROOT)),'master_sha256':common.sha(master),
      'rig_profile':'humanoid_game_v2','root_motion':False,'source_sha256':common.sha(Path(__file__)),
      'hand_helper_sha256':common.sha(GRIP_SOURCE),'images':[]}
    (ROOT/'review/source_fit.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,target,offset,scale in [
        ('source_assembly_front',(0,-.1,1.65),(5,-7,4),6.0),
        ('source_crew_rear',(0,-.15,1.85),(3,6,2.2),3.5)]:
        path=ROOT/'review'/f'{name}.png'
        common.render(path,target,offset,scale)
        report['images'].append({'path':str(path.relative_to(ROOT)),'sha256':common.sha(path)})
        (ROOT/'review/source_fit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('SOURCE_FIT_SAVED',master,flush=True)


if __name__=='__main__': main()
