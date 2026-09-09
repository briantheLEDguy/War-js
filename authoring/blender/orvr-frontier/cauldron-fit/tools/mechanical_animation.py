"""In-place authored mechanism clips; world motion and impact outcomes stay authoritative."""
from __future__ import annotations
import math
import bpy


def add_track(obj, name, poses, start=1):
    obj.animation_data_create()
    rest_location=obj.location.copy(); rest_rotation=obj.rotation_euler.copy();rest_scale=obj.scale.copy()
    action=bpy.data.actions.new(obj.name+'.'+name)
    obj.animation_data.action=action
    for pose in poses:
        frame,translation,rotation=pose[:3];scale=pose[3] if len(pose)>3 else (1,1,1)
        obj.location=[rest_location[i]+translation[i] for i in range(3)]
        obj.rotation_euler=[rest_rotation[i]+rotation[i] for i in range(3)]
        obj.scale=[rest_scale[i]*scale[i] for i in range(3)]
        obj.keyframe_insert(data_path='location',frame=frame+start)
        obj.keyframe_insert(data_path='rotation_euler',frame=frame+start)
        obj.keyframe_insert(data_path='scale',frame=frame+start)
    # Linear sampled motion prevents Bezier overshoot into stops and wheel reversals.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points: point.interpolation='LINEAR'
    track=obj.animation_data.nla_tracks.new();track.name=name
    strip=track.strips.new(name,start,action);strip.extrapolation='NOTHING';strip.blend_type='REPLACE'
    obj.animation_data.action=None
    obj.location=rest_location;obj.rotation_euler=rest_rotation;obj.scale=rest_scale


def author_mechanical_actions(objects, asset_id):
    bpy.context.scene.render.fps=30
    by_name={obj.name:obj for obj in objects}
    clips=[]
    def record(name,frames,loop=False,event=None):
        clips.append({'name':name,'duration_seconds':frames/30,'loop':loop,'event_seconds':event,'root_motion':False})
    wheels=[obj for obj in objects if obj.name.startswith('wheel_')]
    if wheels:
        radius=.79 if asset_id=='frontier_supply_wagon' else .79*.86
        frames=48
        for obj in wheels:
            add_track(obj,'caravan_roll' if asset_id=='frontier_supply_wagon' else 'siege_roll',
                      [(frame,(0,0,0),(2*math.pi*frame/frames,0,0)) for frame in range(0,frames+1,4)])
        record('caravan_roll' if asset_id=='frontier_supply_wagon' else 'siege_roll',frames,True)
        clips[-1]['distance_per_cycle_metres']=2*math.pi*radius
    if asset_id=='frontier_battering_ram':
        poses=[(0,0),(9,.23),(15,.28),(21,-.34),(24,-.30),(30,.07),(39,-.025),(45,0)]
        add_track(by_name['ram_striker'],'ram_strike',[(frame,(0,y,1.26-math.sqrt(1.26**2-y*y)),(0,0,0)) for frame,y in poses],70)
        for name in ('suspension_front','suspension_rear'):
            add_track(by_name[name],'ram_strike',[(frame,(0,0,0),(math.asin(y/1.26),0,0)) for frame,y in poses],70)
        record('ram_strike',45,event=.7)
    elif asset_id=='frontier_oil_cauldron':
        poses=[(0,0),(12,-.08),(28,.72),(43,1.02),(63,1.02),(88,.24),(105,0)]
        add_track(by_name['tipping_cauldron'],'oil_pour',[(frame,(0,0,0),(angle,0,0)) for frame,angle in poses],130)
        record('oil_pour',105,event=28/30)
    elif asset_id=='frontier_field_catapult':
        # Cocked arm leans toward the rear; a rapid forward release meets its
        # padded stop, with restrained elastic recoil before reload.
        fire=[(0,-1.10),(5,-1.10),(9,-.22),(12,.42),(15,.33),(19,.39),(24,.37)]
        reload=[(0,.37),(20,.25),(48,-.21),(74,-.66),(100,-1.10),(108,-1.10)]
        for name,start,poses in [('catapult_fire',250,fire),('catapult_reload',300,reload)]:
            add_track(by_name['throwing_assembly'],name,[(frame,(0,0,0),(angle,0,0)) for frame,angle in poses],start)
            rope=[];drum=[]
            for frame,angle in poses:
                dy=.1*math.cos(angle)-1.02*math.sin(angle)-1.05
                dz=.88+.1*math.sin(angle)+1.02*math.cos(angle)-.98
                length=math.hypot(dy,dz)
                rope.append((frame,(0,0,0),(math.atan2(-dy,dz)-math.atan2(.95,.92),0,0),(1,1,length/math.hypot(.95,.92))))
                drum.append((frame,(0,0,0),(-length/.12,0,0)))
            add_track(by_name['haul_rope'],name,rope,start)
            add_track(by_name['winding_drum'],name,drum,start)
            record(name,poses[-1][0],event=.30 if name=='catapult_fire' else None)
    elif asset_id=='frontier_keep_gate':
        for name,sign in [('gate_leaf_left',1),('gate_leaf_right',-1)]:
            for clip,start,angles in [('gate_open',430,(0,math.pi/2)),('gate_close',480,(math.pi/2,0))]:
                add_track(by_name[name],clip,[(0,(0,0,0),(0,0,sign*angles[0])),(9,(0,0,0),(0,0,sign*(angles[0]*.93+angles[1]*.07))),
                    (30,(0,0,0),(0,0,sign*(angles[0]*.07+angles[1]*.93))),(39,(0,0,0),(0,0,sign*angles[1]))],start)
        record('gate_open',39);record('gate_close',39)
    bpy.context.scene.frame_set(0)
    return clips
