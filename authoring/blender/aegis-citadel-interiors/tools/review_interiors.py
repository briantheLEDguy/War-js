"""Render the delivered GLBs, not the retained high resolution masters."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

WORK=Path(__file__).resolve().parents[1]
report=json.loads((WORK/'build-report.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.world=bpy.data.worlds.new('neutral_export_review_world')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.39,.46,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.render.engine='CYCLES'
scene.cycles.samples=20
scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'


def light(pos,target,energy,size):
    bpy.ops.object.light_add(type='AREA',location=pos)
    ob=bpy.context.object;ob.data.energy=energy;ob.data.shape='DISK';ob.data.size=size
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()


def camera(pos,target,scale):
    bpy.ops.object.camera_add(location=pos)
    ob=bpy.context.object
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    ob.data.type='ORTHO';ob.data.ortho_scale=scale;scene.camera=ob


def floor(size,xy=(0,0)):
    bpy.ops.mesh.primitive_plane_add(size=1,location=(*xy,-.05))
    bpy.context.object.scale=(size,size,1)
    mat=bpy.data.materials.get('review_floor') or bpy.data.materials.new('review_floor')
    mat.diffuse_color=(.10,.12,.14,1)
    mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.065,.08,.10,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.92
    bpy.context.object.data.materials.append(mat)


def label(body,pos,size=.29):
    curve=bpy.data.curves.new(body,'FONT');curve.body=body;curve.size=size;curve.align_x='CENTER'
    ob=bpy.data.objects.new(body,curve);bpy.context.collection.objects.link(ob);ob.location=pos
    ob.rotation_euler=(math.pi/2,0,0)
    mat=bpy.data.materials.get('review_type') or bpy.data.materials.new('review_type')
    mat.diffuse_color=(.78,.80,.74,1)
    mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.78,.80,.74,1)
    curve.materials.append(mat)


heroes=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--heroes=')),['throne','oath_statue','reliquary','tapestry'])
if '--contact-only' not in sys.argv:
    for name in heroes:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        asset=next(a for a in report if a['kind']=='citadel_'+name)
        bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/asset['lods'][0]['model']))
        e=asset['envelope'];span=max(e['width'],e['depth'],e['height']);h=e['height']
        floor(span*4)
        light((-span*.5,-span*.7,span*1.6),(0,0,h*.4),span*span*36,span)
        light((span,span*.3,span),(0,0,h*.5),span*span*27,span*.7)
        camera((span*.83,-span*1.75,span*.83),(0,0,h*.43),span*1.24)
        scene.render.resolution_x=1500;scene.render.resolution_y=1500
        scene.render.filepath=str(WORK/'review'/f'{name}.png')
        bpy.ops.render.render(write_still=True)
        print('REVIEWED_EXPORT_RENDER',name,flush=True)

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for i,asset in enumerate(report):
    bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/asset['lods'][0]['model']))
    e=asset['envelope'];scale=6/max(e['width'],e['depth'],e['height'])
    x=(i%5)*8-16;y=(i//5)*10
    for ob in bpy.context.selected_objects:
        if ob.parent:continue
        ob.scale*=scale;ob.location*=scale;ob.location.x+=x;ob.location.y+=y
    label(asset['kind'].replace('citadel_','').replace('_',' ').upper(),(x,y-3.7,.1),.36)
floor(80,(0,10))
light((-14,-10,29),(0,9,1.8),19000,24)
light((18,17,21),(0,9,1.8),14000,22)
camera((9,-44,39),(0,10,1.5),45)
scene.render.resolution_x=3600;scene.render.resolution_y=2500
scene.render.filepath=str(WORK/'review/all-exports.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'review/all-exports.blend'))
