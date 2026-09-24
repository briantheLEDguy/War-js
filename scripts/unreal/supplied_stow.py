"""Bake reachable hand-carried equipment transitions into supplied poses."""
import math
import json
from pathlib import Path
import unreal


def stored_transform(profile,slot,mesh,grip,chest):
    corrections=Path(__file__).parent/'animation-recipes/corrections'
    anchors=json.loads((corrections/'equipment-stow-grips.json').read_text())
    transform=unreal.Transform()
    transform.rotation=unreal.Rotator(0,180,0).quaternion() if slot=='shield' else unreal.Rotator(-25,0,0).quaternion()
    if profile in anchors and slot in anchors[profile]:
        pivot=grip.inverse_transform_location(unreal.Vector())
        desired=unreal.Vector(*anchors[profile][slot])
    else:
        pivot=mesh.get_bounds().origin
        centers=json.loads((corrections/'equipment-stow.json').read_text())
        desired=unreal.Vector(*centers[profile][slot])
    transform.translation=desired-transform.rotation.rotate_vector(pivot)
    return transform*chest.inverse()


def inverse(q):
    return unreal.Quat(-q.x,-q.y,-q.z,q.w)


def unit(v):
    return v/max(v.length(),1e-9)


def between(a,b):
    a,b=unit(a),unit(b)
    cross=a.cross(b); dot=max(-1.,min(1.,a.dot(b)))
    if dot<-.999999:
        cross=unit(a.cross(unreal.Vector(1,0,0) if abs(a.x)<.9 else unreal.Vector(0,1,0)))
        return unreal.Quat(cross.x,cross.y,cross.z,0)
    q=unreal.Quat(cross.x,cross.y,cross.z,1+dot); q.normalize(); return q


def component_pose(row,component):
    world={}
    def transform(bone):
        if bone not in world:
            parent=str(component.get_parent_bone(bone))
            world[bone]=row[bone]*transform(parent) if parent in row else row[bone]
        return world[bone]
    for bone in row: transform(bone)
    return world


def bake_stowing(rows,component,visual,idle,rate):
    ready=component_pose(idle,component); duration=(len(rows)-1)/rate
    maximum_error=0.; worst=None
    for index,row in enumerate(rows):
        time=index/rate
        if .52<time<duration-.4: continue
        world=component_pose(row,component)
        phase=max(0.,min(1.,time/.3,(duration-time)/.3))
        for slot,side in (('weapon','R'),('shield','L')):
            if not visual.get_editor_property(slot+'_mesh'): continue
            hand='hand_'+side; upper='upper_arm_'+side; lower='forearm_'+side
            grip=visual.get_editor_property(slot+'_grip')
            stored=visual.get_editor_property(slot+'_stowed')
            drawn=ready[hand]*ready['upper_chest'].inverse()*world['upper_chest']
            back=grip.inverse()*stored*world['upper_chest']
            target=unreal.MathLibrary.t_lerp(drawn,back,phase)
            # Carry the grip around the same side of the torso. Interpolating
            # mesh origins instead makes off-centre authored shields dip down.
            outward=1 if ready[hand].translation.x>ready['upper_chest'].translation.x else -1
            target.translation=target.translation+unreal.Vector(outward*15*math.sin(math.pi*phase),0,0)
            if .3<time<=.52:
                weight=(time-.3)/.22
                target=unreal.MathLibrary.t_lerp(back,world[hand],weight*weight*(3-2*weight))
            if duration-.4<=time<duration-.3:
                weight=(time-(duration-.4))/.1
                target=unreal.MathLibrary.t_lerp(world[hand],back,weight*weight*(3-2*weight))
            shoulder,elbow,wrist=world[upper],world[lower],world[hand]
            start=shoulder.translation; delta=target.translation-start
            a=(elbow.translation-start).length(); b=(wrist.translation-elbow.translation).length()
            distance=max(abs(a-b)+.01,min(a+b-.01,delta.length()))
            error=abs(distance-delta.length())
            if error>maximum_error:
                maximum_error=error; worst=(time,slot,str(target.translation),str(start),a+b)
            direction=unit(delta); hint=elbow.translation-start
            pole=unit(hint-direction*hint.dot(direction))
            if pole.length()<.5: pole=unit(direction.cross(unreal.Vector(0,0,1)))
            along=(a*a-b*b+distance*distance)/(2*distance)
            joint=start+direction*along+pole*math.sqrt(max(0.,a*a-along*along))
            end=start+direction*distance
            upper_rotation=between(elbow.translation-start,joint-start)*shoulder.rotation
            lower_rotation=between(wrist.translation-elbow.translation,end-joint)*elbow.rotation
            row[upper].rotation=inverse(world['shoulder_'+side].rotation)*upper_rotation
            row[lower].rotation=inverse(upper_rotation)*lower_rotation
            row[hand].rotation=inverse(lower_rotation)*target.rotation
    if maximum_error>1:
        raise RuntimeError('Stow grip exceeds unchanged arm reach: '+str(maximum_error)+' cm '+str(worst))
    return maximum_error
