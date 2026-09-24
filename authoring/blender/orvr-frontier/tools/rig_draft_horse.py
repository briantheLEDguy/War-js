"""Explicit anatomical weights and in-place, planted-foot draft horse actions.

The rig is constructed on the retained anatomy master. Controller-driven motion
is visually baked into bone keys; no controller or scene translation is shipped.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build
import quadruped_rig as shared

ROOT=build.ROOT
ASSET='frontier_draft_horse'


def skeleton():
    bones=[]
    def bone(name,head,tail,parent=None):bones.append({'name':name,'head':head,'tail':tail,'parent':parent})
    bone('root',(0,0,0),(0,-.25,0))
    bone('pelvis',(0,.76,1.30),(0,.40,1.33),'root')
    bone('spine',(0,.40,1.33),(0,-.24,1.36),'pelvis')
    bone('chest',(0,-.24,1.36),(0,-.68,1.50),'spine')
    bone('neck_01',(0,-.68,1.50),(0,-.91,1.85),'chest')
    bone('neck_02',(0,-.91,1.85),(0,-1.16,2.10),'neck_01')
    bone('head',(0,-1.16,2.10),(0,-1.76,1.58),'neck_02')
    bone('jaw',(0,-1.21,1.79),(0,-1.77,1.49),'head')
    for side,label in [(-1,'L'),(1,'R')]:
        x=side*.315
        bone('scapula_'+label,(side*.27,-.40,1.60),(x,-.63,1.48),'chest')
        bone('shoulder_'+label,(x,-.63,1.48),(x,-.65,1.02),'scapula_'+label)
        bone('forearm_'+label,(x,-.65,1.02),(x,-.77,.70),'shoulder_'+label)
        bone('carpal_'+label,(x,-.77,.70),(x,-.78,.24),'forearm_'+label)
        bone('pastern_front_'+label,(x,-.78,.24),(x,-.89,.105),'carpal_'+label)
        bone('hoof_front_'+label,(x,-.89,.105),(x,-.97,.035),'pastern_front_'+label)
        x=side*.33
        bone('thigh_'+label,(x,.75,1.43),(x,.43,1.02),'pelvis')
        bone('shin_'+label,(x,.43,1.02),(x,.96,.60),'thigh_'+label)
        bone('hock_'+label,(x,.96,.60),(x,.87,.23),'shin_'+label)
        bone('pastern_hind_'+label,(x,.87,.23),(x,.77,.105),'hock_'+label)
        bone('hoof_hind_'+label,(x,.77,.105),(x,.70,.035),'pastern_hind_'+label)
        bone('ear_'+label,(side*.10,-1.075,2.18),(side*.16,-1.06,2.43),'head')
    bone('tail_01',(0,1.04,1.49),(.02,1.26,1.14),'pelvis')
    bone('tail_02',(.02,1.26,1.14),(.015,1.38,.68),'tail_01')
    bone('tail_03',(.015,1.38,.68),(0,1.40,.22),'tail_02')
    return bones


def segment_distance(p,bone):
    a=Vector(bone['head']);delta=Vector(bone['tail'])-a
    t=max(0,min(1,(p-a).dot(delta)/delta.length_squared))
    return (p-a-t*delta).length


def skin_weights(obj,bones):
    by_name={bone['name']:bone for bone in bones};result=[]
    region=obj.get('skin_region','continuous_body')
    for vertex in obj.data.vertices:
        x,y,z=vertex.co;side='L' if x<0 else 'R'
        if 'hoof' in obj.name:
            names=[('hoof_front_' if 'front' in obj.name else 'hoof_hind_')+side]
        elif region.startswith('ear_'):names=[region]
        elif region=='head':names=['head']
        elif region=='tail':names=['tail_01','tail_02','tail_03']
        elif region=='neck':names=['neck_01','neck_02','head']
        elif region in ('chest','spine','pelvis'):names=[region]
        else:
            def blend(a,b,value):
                t=max(0,min(1,(value-a)/(b-a)));return t*t*(3-2*t)
            def field(value,centers):
                if value<=centers[0][0]:return {centers[0][1]:1}
                for (a,left),(b,right) in zip(centers,centers[1:]):
                    if value<=b:
                        t=blend(a,b,value);return {left:1-t,right:t}
                return {centers[-1][1]:1}
            trunk=field(y,[(-1.25,'head'),(-1.02,'neck_02'),(-.80,'neck_01'),(-.46,'chest'),(.16,'spine'),(.70,'pelvis')])
            # Ventral rib skin blends toward the proximal shoulder/thigh;
            # distal forearm and shin weights remain below the belly surface.
            front=1-blend(.22,.62,abs(y+.67));hind=1-blend(.22,.62,abs(y-.76))
            terms=([(.17,'pastern_front'),(.40,'carpal'),(.72,'forearm'),(.98,'shoulder'),(1.53,'scapula')] if y<0
                else [(.17,'pastern_hind'),(.40,'hock'),(.69,'shin'),(1.03,'thigh')])
            legs={name+'_'+side:value for name,value in field(z,terms).items()}
            # The broad shoulder/hip transition is a continuous field, avoiding
            # a sharp region switch across shared skin triangles.
            upper=(1-blend(.80,1.59,z))*blend(.025,.31,abs(x))*max(front,hind)
            # Below the lowest belly surface only disconnected distal limbs
            # remain; stop this override before the continuous trunk begins.
            low=1-blend(.64,.72,z)
            limb=low+(1-low)*upper
            weights={name:value*(1-limb) for name,value in trunk.items()}
            weights.update({name:value*limb for name,value in legs.items()})
            selected=[item for item in weights.items() if item[1]>0]
            if len(selected)>4:raise ValueError('Compact anatomical fields must not need top-four truncation')
            total=sum(value for _,value in selected)
            result.append({name:value/total for name,value in selected});continue
        closest=sorted(((segment_distance(vertex.co,by_name[name]),name) for name in names))[:3]
        weights={name:1/max(.018,distance)**4 for distance,name in closest}
        total=sum(weights.values());result.append({name:weight/total for name,weight in weights.items()})
    return result


def prepare_skin(rig,bones):
    sources=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and not obj.hide_render]
    graph=bpy.context.evaluated_depsgraph_get();objects=[]
    for source in sources:
        mesh=bpy.data.meshes.new_from_object(source.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
        bm=bmesh.new();bm.from_mesh(mesh)
        if bm.verts.layers.deform.active:bm.verts.layers.deform.remove(bm.verts.layers.deform.active)
        bm.to_mesh(mesh);bm.free()
        obj=bpy.data.objects.new(source.name+'.weighted',mesh);bpy.context.scene.collection.objects.link(obj)
        obj['skin_region']=source.get('skin_region','continuous_body')
        shared.bind_explicit_weights(obj,rig,skin_weights(obj,bones));objects.append(obj)
        source.hide_render=True;source.hide_set(True)
    return objects










def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters'/f'{ASSET}_anatomy.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    bones=skeleton(); rig=shared.create_rig('draft_horse_rig',bones)
    prepare_skin(rig,bones)
    rig.animation_data_clear()
    if bpy.data.actions:
        raise ValueError('Horse body sources must contain no animation actions')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'masters'/f'{ASSET}_rigged.blend'))


if __name__=='__main__': main()
